"""Real-filesystem upgrade, rollback, failed-upgrade and backwards compatibility tests."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from upgrade_existing import UpgradeError, APP_FILES, upgrade, rollback, version_at

SOURCE = Path(__file__).resolve().parent.parent
PREVIOUS = SOURCE.parent / "PinterestBoardStudio-v2.1"


class InPlaceUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old = Path(self.tmp.name) / "old-install"
        self.old.mkdir()
        self.old_bytes = {}
        for name in ("studio_core.py", "pinterest_studio.py", "download_runtime.py", "Run on Windows.bat", "README-FA.md"):
            if PREVIOUS.is_dir() and (PREVIOUS / name).is_file():
                content = (PREVIOUS / name).read_bytes()
            else:
                # A self-contained v2.1 fixture when the original repo is not installed.
                fake = {
                    "studio_core.py": 'APP_NAME = "Pinterest Board Studio"\nAPP_VERSION = "2.1.0"\n',
                    "pinterest_studio.py": '# legacy v2.1 desktop app\n',
                }
                content = fake.get(name, "old version test fixture\n").encode("utf-8")
            (self.old / name).write_bytes(content)
            self.old_bytes[name] = content
        self.old_version = version_at(self.old)
        self.archive = self.old / ".pinterest-studio" / "download_archive.sqlite3"
        self.archive.parent.mkdir()
        self.archive.write_bytes(b"test archive bytes do not overwrite")
        (self.old / "user-image.jpg").write_bytes(b"private media")
        (self.old / "my-extra-file.txt").write_text("custom", encoding="utf-8")

    def test_upgrade_preserves_media_archive_and_backup(self):
        result = upgrade(SOURCE, self.old)
        self.assertEqual(result["status"], "upgraded")
        self.assertEqual(version_at(self.old), "2.5.0")
        self.assertEqual(self.archive.read_bytes(), b"test archive bytes do not overwrite")
        self.assertEqual((self.old / "user-image.jpg").read_bytes(), b"private media")
        self.assertEqual((self.old / "my-extra-file.txt").read_text(), "custom")
        saved = Path(result["backup"])
        self.assertEqual((saved / "files/studio_core.py").read_bytes(), self.old_bytes["studio_core.py"])
        self.assertTrue((self.old / "Upgrade Existing Installation.bat").is_file())
        self.assertEqual(upgrade(SOURCE, self.old)["status"], "up-to-date")

    def test_same_version_with_missing_program_file_repairs_installation(self):
        upgrade(SOURCE, self.old)
        (self.old / "download_runtime.py").unlink()
        result = upgrade(SOURCE, self.old)
        self.assertEqual(result["status"], "upgraded")
        self.assertTrue((self.old / "download_runtime.py").is_file())
        self.assertEqual(version_at(self.old), "2.5.0")
        self.assertEqual(self.archive.read_bytes(), b"test archive bytes do not overwrite")

    def test_rollback_restores_previous_version_and_media(self):
        upgrade(SOURCE, self.old)
        result = rollback(self.old)
        self.assertEqual(result["status"], "rolled-back")
        self.assertEqual(version_at(self.old), self.old_version)
        self.assertEqual(self.archive.read_bytes(), b"test archive bytes do not overwrite")
        self.assertEqual((self.old / "user-image.jpg").read_bytes(), b"private media")
        self.assertEqual((self.old / "studio_core.py").read_bytes(), self.old_bytes["studio_core.py"])

    def test_incorrect_installation_rejected(self):
        not_installed = Path(self.tmp.name) / "not-installed"
        not_installed.mkdir()
        with self.assertRaises(UpgradeError):
            upgrade(SOURCE, not_installed)
        self.assertEqual(version_at(self.old), self.old_version)

    def test_cannot_run_update_inside_same_directory(self):
        with self.assertRaises(UpgradeError):
            upgrade(SOURCE, SOURCE)

    def test_partial_copy_failure_restores_all_original_program_files(self):
        original_replace = os.replace
        counter = [0]
        def sometimes_fail(a, b):
            counter[0] += 1
            if counter[0] == 3:
                raise OSError("simulated locked Windows file")
            return original_replace(a, b)
        with patch("upgrade_existing.os.replace", side_effect=sometimes_fail):
            with self.assertRaises(OSError):
                upgrade(SOURCE, self.old)
        self.assertEqual(version_at(self.old), self.old_version)
        self.assertEqual(self.archive.read_bytes(), b"test archive bytes do not overwrite")
        self.assertFalse((self.old / "requirements.txt").exists())

    def test_incomplete_update_package_does_nothing(self):
        source = Path(self.tmp.name) / "broken-new-release"
        source.mkdir()
        shutil.copy2(SOURCE / "studio_core.py", source / "studio_core.py")
        shutil.copy2(SOURCE / "pinterest_studio.py", source / "pinterest_studio.py")
        with self.assertRaises(UpgradeError):
            upgrade(source, self.old)
        self.assertEqual(version_at(self.old), self.old_version)


if __name__ == "__main__":
    unittest.main()
