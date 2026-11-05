"""Version 2.2 URL identities, destination persistence, and safe output checks."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from studio_core import (
    board_identity, parse_boards, choose_destination, check_destination_writable,
    dump_session, load_session, QueueEntry,
)


class ImprovedUrlTests(unittest.TestCase):
    def test_equivalent_host_aliases_not_added_twice(self):
        links = "\n".join([
            "https://www.pinterest.com/user/art/",
            "https://pinterest.com/user/art",
            "https://m.pinterest.com/user/ART/",
            "https://pinterest.de/user/art/",
        ])
        found = parse_boards(links)
        self.assertEqual(len(found), 2)
        self.assertEqual(board_identity(found[0]), board_identity("pinterest.com/user/art"))

    def test_session_duplicate_aliases_collapse(self):
        entries = [QueueEntry("pinterest.com/u/b"), QueueEntry("www.pinterest.com/u/b")]
        self.assertEqual(len(load_session(dump_session(entries))), 1)


class DestinationTests(unittest.TestCase):
    def test_default_location_follows_app_folder_after_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = base / "old"
            second = base / "new"
            first.mkdir()
            second.mkdir()
            self.assertEqual(choose_destination("", second), second.resolve())
            self.assertEqual(choose_destination(str(first), second), first.resolve())
            self.assertEqual(choose_destination(str(first / "nonexistent"), second), second.resolve())

    def test_writable_destination_and_reject_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            check_destination_writable(root)
            self.assertFalse(list(root.glob(".pbs-test-*")))
            with self.assertRaises(ValueError):
                check_destination_writable(root / "not-a-dir")

    def test_permission_failure_returns_useful_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("tempfile.NamedTemporaryFile", side_effect=PermissionError("blocked")):
                with self.assertRaisesRegex(ValueError, "نوشتن"):
                    check_destination_writable(Path(tmp))


if __name__ == "__main__":
    unittest.main()
