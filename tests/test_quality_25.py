"""Release 2.5 regression tests: integrity, public files, install bootstrap, publication safety."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from release_manifest import APP_FILES, SOURCE_FILES
from studio_core import APP_VERSION
from tools.bootstrap import installation_is_current, requirements_digest, write_stamp
from tools.github_publish import repo_name, origin_matches_repo, selected_uploads, main as publish_main
from tools.verify_repository import audit_repository
from upgrade_existing import verify_package, UpgradeError, upgrade, version_at
from tools.build_release import zip_files, update_manifest

ROOT = Path(__file__).resolve().parents[1]


class Release25Tests(unittest.TestCase):
    def test_central_manifest_matches_program_files(self):
        self.assertEqual(audit_repository(), [])
        self.assertTrue(set(APP_FILES).issubset(set(SOURCE_FILES)))
        self.assertIn('tools/bootstrap.py', APP_FILES)

    def test_sha256_manifest_is_complete(self):
        data = json.loads(update_manifest())
        self.assertEqual(data['version'], APP_VERSION)
        self.assertEqual(set(data['files']), set(APP_FILES))
        self.assertEqual(data['files']['studio_core.py'], hashlib.sha256((ROOT / 'studio_core.py').read_bytes()).hexdigest())

    def test_archive_has_manifest_and_no_private_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            zpath = Path(tmp) / 'update.zip'
            zip_files(zpath, APP_FILES, 'PinHarbor', integrity=True)
            with ZipFile(zpath) as zipfile:
                names = zipfile.namelist()
                self.assertIn('PinHarbor/update-manifest.json', names)
                self.assertFalse(any('__pycache__' in f or '.pinterest-studio' in f for f in names))
                extracted = Path(tmp) / 'unpacked'
                zipfile.extractall(extracted)
            self.assertTrue(verify_package(extracted / 'PinHarbor'))

    def test_integrity_detects_tampering_before_upgrading(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            zip_files(folder / 'update.zip', APP_FILES, 'PinHarbor', integrity=True)
            with ZipFile(folder / 'update.zip') as archive:
                archive.extractall(folder / 'unpack')
            source = folder / 'unpack' / 'PinHarbor'
            old = folder / 'old'
            old.mkdir()
            (old / 'studio_core.py').write_text('APP_NAME="Pinterest Board Studio"\nAPP_VERSION = "2.3.0"', encoding='utf-8')
            (old / 'pinterest_studio.py').write_text('# old', encoding='utf-8')
            (old / 'media.jpg').write_bytes(b'private media')
            (source / 'ui_theme.py').write_text('modified', encoding='utf-8')
            with self.assertRaises(UpgradeError):
                upgrade(source, old)
            self.assertEqual(version_at(old), '2.3.0')
            self.assertEqual((old / 'media.jpg').read_bytes(), b'private media')
            self.assertFalse((old / 'download_runtime.py').exists())

    def test_integrity_rejects_invalid_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'update-manifest.json').write_text('{bad json', encoding='utf-8')
            with self.assertRaises(UpgradeError):
                verify_package(root)

    def test_bootstrap_detects_changes_and_records_only_after_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            req = Path(tmp) / 'requirements.txt'
            req.write_text('mock>=1\n', encoding='utf-8')
            stamp = Path(tmp) / 'stamp'
            self.assertFalse(installation_is_current(req, stamp))
            with patch('tools.bootstrap.modules_present', return_value=True):
                write_stamp(req, stamp)
                self.assertTrue(installation_is_current(req, stamp))
                req.write_text('mock>=2\n', encoding='utf-8')
                self.assertFalse(installation_is_current(req, stamp))

    def test_bootstrap_refuses_marking_missing_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            req = Path(tmp) / 'requirements.txt'
            req.write_text('fake dependency')
            stamp = Path(tmp) / 'stamp'
            with patch('tools.bootstrap.modules_present', return_value=False):
                with self.assertRaises(RuntimeError):
                    write_stamp(req, stamp)
            self.assertFalse(stamp.exists())

    def test_publish_dry_run_has_no_git_operations(self):
        with patch('tools.github_publish.execute') as mocked:
            self.assertEqual(publish_main(['--repo','pinharbor']), 0)
            mocked.assert_not_called()

    def test_publisher_rejects_bad_slugs(self):
        for slug in ('../x', 'https://evil.invalid/a', 'abc?x', '-bad/a', 'x/other/third', ''):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                repo_name(slug)

    def test_publisher_validates_origin(self):
        self.assertTrue(origin_matches_repo('git@github.com:myuser/pinharbor.git', 'myuser/pinharbor'))
        self.assertFalse(origin_matches_repo('git@github.com:another/pinharbor.git', 'myuser/pinharbor'))
        self.assertFalse(origin_matches_repo('https://somewhere.invalid/myuser/pinharbor', 'myuser/pinharbor'))

    def test_publisher_selects_only_curated_files(self):
        selections = selected_uploads()
        self.assertIn('README.md', selections)
        self.assertFalse(any(f.lower().endswith(('.sqlite3', '.part', '.db', 'cookies.txt')) for f in selections))

    def test_gallery_excludes_brand_art_only_at_program_root(self):
        from studio_core import list_media_files
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'app_icon.png').write_bytes(b'icon')
            (root / 'photo.jpg').write_bytes(b'user content')
            (root / 'assets').mkdir()
            (root / 'assets' / 'brand.png').write_bytes(b'internal')
            (root / 'downloaded').mkdir()
            (root / 'downloaded' / 'pin.png').write_bytes(b'user content')
            with patch('studio_core.default_output_directory', return_value=root):
                paths = {p.relative_to(root).as_posix() for p in list_media_files(root)}
            self.assertEqual(paths, {'photo.jpg', 'downloaded/pin.png'})
            with patch('studio_core.default_output_directory', return_value=root / 'elsewhere'):
                paths = {p.relative_to(root).as_posix() for p in list_media_files(root)}
            self.assertIn('assets/brand.png', paths)

    def test_windows_archive_includes_license_and_notices(self):
        from tools.build_release import zip_windows
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / 'dist'
            dist.mkdir()
            (dist / 'PinHarbor.exe').write_bytes(b'fake binary for archive test')
            (dist / '_internal').mkdir()
            (dist / '_internal' / 'library.dll').write_bytes(b'test fixture')
            target = root / 'windows.zip'
            zip_windows(target, dist)
            with ZipFile(target) as archive:
                names = set(archive.namelist())
            self.assertIn('PinHarbor/LICENSE', names)
            self.assertIn('PinHarbor/NOTICE.md', names)
            self.assertIn('PinHarbor/THIRD-PARTY.md', names)
            self.assertIn('PinHarbor/_internal/library.dll', names)

    def test_migration_from_real_24_install_and_restore(self):
        from upgrade_existing import rollback
        previous = ROOT.parent / 'PinHarbor-v2.4.0'
        if not previous.is_dir():
            self.skipTest('Prior source package not mounted in this environment')
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            prior = Path(tmp) / 'PinHarbor-old'
            shutil.copytree(previous, prior,
                            ignore=shutil.ignore_patterns('__pycache__', 'release'))
            archive = prior / '.pinterest-studio' / 'download_archive.sqlite3'
            archive.parent.mkdir(exist_ok=True)
            archive.write_bytes(b'private user archive')
            (prior / 'my-photo.jpg').write_bytes(b'user file')
            upgraded = upgrade(ROOT, prior)
            self.assertEqual(version_at(prior), APP_VERSION)
            self.assertEqual(archive.read_bytes(), b'private user archive')
            self.assertEqual((prior / 'my-photo.jpg').read_bytes(), b'user file')
            rollback(prior)
            self.assertEqual(version_at(prior), '2.4.0')
            self.assertEqual(archive.read_bytes(), b'private user archive')

    @unittest.skipIf(__import__('os').name == 'nt', 'POSIX process group handling only')
    def test_cancel_escalates_for_sigterm_ignoring_process(self):
        import os, sys, threading, time
        from download_runtime import ProcessController
        controller = ProcessController()
        active = threading.Event()
        stop = threading.Event()
        results = []
        def work():
            source = ("import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                      "print('ready',flush=True); time.sleep(30)")
            results.append(controller.run([sys.executable, '-u', '-c', source], os.environ.copy(),
                                          lambda kind, msg, *_: active.set() if msg == 'ready' else None,
                                          should_cancel=stop.is_set))
        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        try:
            self.assertTrue(active.wait(12), 'Child did not start')
        finally:
            stop.set()
            controller.cancel()
        thread.join(timeout=12)
        self.assertFalse(thread.is_alive(), 'SIGKILL fallback failed')
        self.assertEqual(len(results), 1)
        self.assertNotEqual(results[0].returncode, 0)

    def test_gui_close_duplicate_regression(self):
        source = (ROOT / 'pinterest_studio.py').read_text(encoding='utf-8')
        self.assertNotIn('self._finish_close_when_idle()\n            self._finish_close_when_idle()', source)
        self.assertIn('def update_link_preview(self)', source)
        self.assertIn('def show_preflight(self)', source)


if __name__ == '__main__':
    unittest.main()
