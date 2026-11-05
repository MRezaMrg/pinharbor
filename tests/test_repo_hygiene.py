"""No-network checks for minimal public repository and safe legacy cleanup."""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from release_manifest import APP_FILES, SOURCE_FILES, OBSOLETE_TRACKED_FILES
from tools.github_publish import obsolete_tracked_paths, ensure_staging_safe, repo_name
from tools.build_release import main as build_main
from tools.verify_repository import audit_repository

ROOT = Path(__file__).resolve().parents[1]


class RepositoryHygieneTests(unittest.TestCase):
    def test_manifest_disjoint_and_files_present(self):
        self.assertEqual(audit_repository(), [])
        self.assertFalse(set(SOURCE_FILES) & set(OBSOLETE_TRACKED_FILES))
        self.assertTrue(set(APP_FILES) < set(SOURCE_FILES))
        self.assertNotIn('tests/test_core.py', APP_FILES)
        self.assertNotIn('Publish to GitHub.bat', APP_FILES)

    def test_cleanup_only_whitelisted_paths(self):
        tracked = {'docs/QA-REPORT.md', 'README-EN.md', 'release/PinHarbor-v2.5.0-source.zip',
                   'release/SHA256SUMS.txt', 'tests/__pycache__/test_core.cpython-313.pyc',
                   'docs/my-private-notes.md', 'release/custom.zip', 'media.jpg', 'assets/custom.png'}
        outdated = set(obsolete_tracked_paths(tracked))
        self.assertIn('README-EN.md', outdated)
        self.assertIn('docs/QA-REPORT.md', outdated)
        self.assertIn('release/PinHarbor-v2.5.0-source.zip', outdated)
        self.assertIn('release/SHA256SUMS.txt', outdated)
        self.assertIn('tests/__pycache__/test_core.cpython-313.pyc', outdated)
        self.assertFalse(outdated & {'docs/my-private-notes.md', 'release/custom.zip', 'media.jpg', 'assets/custom.png'})

    def test_only_two_zip_packages_without_windows_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ['tools/build_release.py', '--out', tmp]
            with patch.object(sys, 'argv', args):
                build_main()
            outputs = sorted(p.name for p in Path(tmp).iterdir())
            self.assertEqual(outputs, ['PinHarbor-v2.6.0-source.zip',
                                       'PinHarbor-v2.6.0-update.zip', 'SHA256SUMS.txt'])
            src = Path(tmp) / outputs[0]
            upd = Path(tmp) / outputs[1]
            with ZipFile(src) as z:
                self.assertTrue(any('README-FA.md' in a for a in z.namelist()))
                self.assertFalse(any('README-EN.md' in a for a in z.namelist()))
                self.assertFalse(any('release/' in a for a in z.namelist()))
            with ZipFile(upd) as z:
                self.assertTrue(any('update-manifest.json' in a for a in z.namelist()))
                self.assertFalse(any('/tests/' in a for a in z.namelist()))
            for row in (Path(tmp) / 'SHA256SUMS.txt').read_text().splitlines():
                digest, filename = row.split('  ',1)
                self.assertEqual(hashlib.sha256((Path(tmp) / filename).read_bytes()).hexdigest(), digest)

    def test_git_staging_guard_rejects_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            (root / 'README.md').write_text('safe')
            (root / 'private.txt').write_text('not for GitHub')
            subprocess.run(['git', 'add', '--', 'private.txt'], cwd=root, check=True, capture_output=True)
            with patch('tools.github_publish.ROOT', root):
                with self.assertRaisesRegex(RuntimeError, 'Unrelated files already staged'):
                    ensure_staging_safe({'README.md'})

    def test_slug_rejects_urls_and_traversal(self):
        for value in ('../secrets', 'https://github.com/o/r', 'my/repo/three'):
            with self.assertRaises(ValueError):
                repo_name(value)

    def test_gitignore_excludes_private_and_legacy(self):
        ignored = (ROOT / '.gitignore').read_text()
        for term in ('.pinterest-studio/', 'release/', '*.sqlite3', 'README-EN.md'):
            self.assertIn(term, ignored)


if __name__ == '__main__':
    unittest.main()
