import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from studio_core import (
    APP_VERSION, QueueEntry, URLValidationError, board_title, build_command,
    build_gallery_config, default_output_directory, dump_queue,
    export_manifest_csv, format_size, list_media_files, load_queue,
    media_kind, normalize_board_url, parse_boards, parse_output_event,
    save_config, validate_proxy,
)


class BoardUrlTests(unittest.TestCase):
    def test_normalize_common_urls(self):
        cases = {
            "pinterest.com/reza/graphic/": "https://pinterest.com/reza/graphic/",
            "https://www.pinterest.com/reza/graphic/?utm_source=x#hi": "https://www.pinterest.com/reza/graphic/",
            "HTTP://pinterest.de/Reza/Type/Section/": "https://pinterest.de/Reza/Type/Section/",
            "  <https://www.pinterest.com/reza/art/>  ": "https://www.pinterest.com/reza/art/",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(normalize_board_url(url), expected)

    def test_reject_unsafe_urls(self):
        cases = [
            "", "https://pinterest.com.evil.test/u/board/", "file:///etc/passwd",
            "http://localhost/u/b/", "https://www.pinterest.com/u/",
            "https://www.pinterest.com/pin/12345/", "https://www.pinterest.com/search/pins/",
            "https://www.pinterest.com/u/board/extra/page/",
            "https://user:password@pinterest.com/u/board/",
            "https://pinterest.com:99999/u/board/", "https://pinterest.com:443/u/board/",
            "https://pinterest.com/a/%2e%2e/", "https://pinterest.com/a/%2f/",
            "https://pinterest.com/a/%5c/", "https://pinterest.com/a/%3f/",
        ]
        for url in cases:
            with self.subTest(url=url), self.assertRaises(URLValidationError):
                normalize_board_url(url)

    def test_deduplicate_and_line_error(self):
        value = "https://pinterest.com/u/a/\n\npinterest.com/u/a/\npinterest.com/u/b/"
        self.assertEqual(len(parse_boards(value)), 2)
        with self.assertRaisesRegex(URLValidationError, "خط 2"):
            parse_boards("pinterest.com/u/a/\nnot-a-url")

    def test_title(self):
        self.assertEqual(board_title("pinterest.com/reza/boards/segment"), "reza / boards / segment")


class QueueTests(unittest.TestCase):
    def test_queue_round_trip(self):
        jobs = [QueueEntry("pinterest.com/a/first"), QueueEntry("pinterest.com/a/second")]
        jobs[0].status = "error"
        jobs[0].last_error = "secret internal status"
        data = dump_queue(jobs)
        self.assertNotIn("secret internal status", data)
        self.assertEqual([x.url for x in load_queue(data)], [x.url for x in jobs])
        self.assertTrue(all(x.status == "pending" for x in load_queue(data)))

    def test_queue_dedup_on_load(self):
        content = json.dumps({"format": "PBS-queue", "boards": ["pinterest.com/a/board", "pinterest.com/a/board"]})
        self.assertEqual(len(load_queue(content)), 1)

    def test_import_errors(self):
        for invalid in ("{}", "garbage", '[]', '{"format":"PBS-queue", "boards":"str"}',
                        json.dumps({"format": "PBS-queue", "boards": [3]}),
                        json.dumps({"format": "PBS-queue", "boards": ["pinterest.com/a/b"] * 1001})):
            with self.subTest(invalid=invalid[:35]), self.assertRaises(ValueError):
                load_queue(invalid)


class CommandTests(unittest.TestCase):
    def test_config_produces_sane_output_events(self):
        c = build_gallery_config()
        self.assertTrue(c["extractor"]["pinterest"]["sections"])
        self.assertTrue(c["extractor"]["pinterest"]["videos"])
        self.assertEqual(c["output"]["mode"]["success"], "PBS_OK|{}\n")
        self.assertEqual(c["output"]["mode"]["skip"], "PBS_SKIP|{}\n")
        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname) / "gallery.json"
            save_config(path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), c)

    def test_command_options(self):
        with tempfile.TemporaryDirectory() as dirname:
            base = Path(dirname)
            cmd = build_command("pinterest.com/u/b/", base, base / "settings.json",
                                media_mode="videos", folders=False, metadata=True,
                                browser="edge", throttle=False,
                                limit=40, rate="1M", abort_skips=12,
                                proxy="socks5h://127.0.0.1:1080")
            self.assertIn("-D", cmd)
            self.assertNotIn("--sleep-request", cmd)
            self.assertIn("--write-metadata", cmd)
            self.assertEqual(cmd[cmd.index("--range") + 1], "1-40")
            self.assertEqual(cmd[cmd.index("--limit-rate") + 1], "1M")
            self.assertEqual(cmd[cmd.index("--abort") + 1], "12")
            self.assertEqual(cmd[cmd.index("--cookies-from-browser") + 1], "edge")
            self.assertIn("m3u8", cmd[cmd.index("--filter") + 1])
            self.assertEqual(cmd[-1], "https://pinterest.com/u/b/")
            self.assertTrue((base / ".pinterest-studio").is_dir())

    def test_default_command(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            cmd = build_command("pinterest.com/a/b", root, root / "a.json")
            self.assertIn("-d", cmd)
            self.assertIn("--sleep-request", cmd)
            self.assertNotIn("--range", cmd)
            self.assertNotIn("--proxy", cmd)
            self.assertTrue(any("download_archive.sqlite3" in s for s in cmd))

    def test_command_rejects_malformed_settings(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            opts = [
                {"browser": "opera"}, {"media_mode": "anything"}, {"limit": -1},
                {"limit": 100001}, {"limit": "10"}, {"abort_skips": -5},
                {"rate": "veryfast"}, {"proxy": "file:///etc/passwd"},
            ]
            for kw in opts:
                with self.subTest(kw=kw), self.assertRaises(ValueError):
                    build_command("pinterest.com/a/b", root, root / "a.json", **kw)

    def test_proxy_validity(self):
        for valid in ("", "http://localhost:7890", "https://localhost:8080", "socks5h://127.0.0.1:1080"):
            self.assertEqual(validate_proxy(valid), valid)
        for invalid in ("localhost:7000", "file:///tmp/socket", "ftp://x:21", "http://", "http://x:999999", "http://x/y"):
            with self.subTest(proxy=invalid), self.assertRaises(ValueError):
                validate_proxy(invalid)

    def test_log_events(self):
        self.assertEqual(parse_output_event("PBS_OK|pin.jpg\n"), ("ok", "pin.jpg"))
        self.assertEqual(parse_output_event("PBS_SKIP|pin.jpg\n"), ("skip", "pin.jpg"))
        self.assertEqual(parse_output_event("[pinterest][error] denied\n"), ("error", "[pinterest][error] denied"))
        self.assertEqual(parse_output_event("message\n"), ("log", "message"))


class LocalGalleryTests(unittest.TestCase):
    def test_filters_and_order(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            (root / "board").mkdir()
            (root / ".pinterest-studio").mkdir()
            files = ["board/01.jpg", "board/02.MP4", "board/03.webp", "board/04.jpg.part", "board/05.json",
                     ".pinterest-studio/a.jpg", ".hidden.png"]
            for name in files:
                f = root / name
                f.write_bytes(b"test")
            found = list_media_files(root)
            self.assertEqual({f.name for f in found}, {"01.jpg", "02.MP4", "03.webp"})
            self.assertEqual(media_kind(root / "01.jpg"), "image")
            self.assertEqual(media_kind(root / "02.MP4"), "video")
            self.assertIsNone(media_kind(root / "05.json"))

    def test_csv_manifest(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            a = root / "one.jpg"
            b = root / "movie.mp4"
            a.write_bytes(b"image")
            b.write_bytes(b"video-long")
            manifest = root / "manifest.csv"
            count = export_manifest_csv(root, manifest, [a, b])
            self.assertEqual(count, 2)
            with manifest.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual({r["type"] for r in rows}, {"image", "video"})
            self.assertEqual({r["path"] for r in rows}, {"one.jpg", "movie.mp4"})
            self.assertTrue(all(r["modified_iso"] for r in rows))

    def test_default_folder_is_current_working_directory(self):
        self.assertEqual(default_output_directory(), Path.cwd().resolve())

    def test_size_format(self):
        self.assertEqual(format_size(100), "100 B")
        self.assertEqual(format_size(2048), "2.0 KB")
        self.assertEqual(format_size(5 * 1024 ** 2), "5.0 MB")


if __name__ == "__main__":
    unittest.main()
