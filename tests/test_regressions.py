"""Additional offline regressions for v2.1, including real child processes."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

from studio_core import (
    QueueEntry, dump_session, load_session, dump_queue, load_queue,
    list_media_files, redact_secrets, build_command, normalize_board_url,
)
from download_runtime import ProcessController


class SessionPersistenceTests(unittest.TestCase):
    def test_status_counts_and_crash_recovery(self):
        jobs = [QueueEntry("pinterest.com/user/my-board"), QueueEntry("pinterest.com/user/another")]
        jobs[0].status = "running"
        jobs[0].new = 38
        jobs[0].skipped = 7
        jobs[1].status = "error"
        jobs[1].last_error = "permission denied"
        restored = load_session(dump_session(jobs))
        self.assertEqual(restored[0].status, "stopped")
        self.assertEqual((restored[0].new, restored[0].skipped), (38, 7))
        self.assertEqual((restored[1].status, restored[1].last_error), ("error", "permission denied"))

    def test_session_rejects_malformed_and_dedups(self):
        bad = ['{}', '[]', 'garbage', '{"format":"PBS-session","boards":"x"}',
               '{"format":"PBS-session","boards":[3]}',
               json.dumps({"format": "PBS-session", "boards": [{"url": "https://evil.tld/a/b"}]})]
        for payload in bad:
            with self.subTest(payload=payload[:30]), self.assertRaises(ValueError):
                load_session(payload)
        payload = json.dumps({"format": "PBS-session", "boards": [
            {"url": "pinterest.com/u/b", "status": "done", "new": True},
            {"url": "pinterest.com/u/b", "status": "error"},
            {"url": "pinterest.com/u/c", "status": "unexpected", "skipped": -1},
        ]})
        entries = load_session(payload)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].new, 0)  # bool must not be accepted as int
        self.assertEqual(entries[1].status, "pending")
        self.assertEqual(entries[1].skipped, 0)

    def test_portable_queue_excludes_session_and_credentials(self):
        e = QueueEntry("pinterest.com/u/b")
        e.last_error = "secret"
        self.assertNotIn("secret", dump_queue([e]))
        self.assertEqual(len(load_queue(dump_queue([e]))), 1)

    def test_redact_proxy_password(self):
        value = "http://u:Hello%40Secret@127.0.0.1:7890"
        msg = "failed: " + value + "; Hello@Secret in log."
        cleaned = redact_secrets(msg, value)
        self.assertNotIn(value, cleaned)
        self.assertNotIn("Hello@Secret", cleaned)


class ScannerSecurityTests(unittest.TestCase):
    def test_symlinks_are_ignored(self):
        if not hasattr(os, "symlink"):
            self.skipTest("no symlinks available")
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root / "internal.jpg").write_bytes(b"internal")
            outside = root.parent / (root.name + "-outside.png")
            outside.write_bytes(b"outside")
            try:
                link = root / "link.png"
                link.symlink_to(outside)
                items = list_media_files(root)
                self.assertEqual([p.name for p in items], ["internal.jpg"])
            except OSError:
                self.skipTest("Symlink permission not available")
            finally:
                outside.unlink(missing_ok=True)


class ChildProcessTests(unittest.TestCase):
    def test_real_subprocess_counts_and_error(self):
        source = "import sys; print('PBS_OK|a.jpg', flush=True); print('PBS_SKIP|b.jpg', flush=True); print('[error] fail', flush=True); sys.exit(6)"
        events = []
        controller = ProcessController()
        result = controller.run([sys.executable, "-u", "-c", source], os.environ.copy(),
                                lambda *args: events.append(args))
        self.assertEqual((result.returncode, result.ok, result.skipped), (6, 1, 1))
        self.assertIn("fail", result.last_error)
        self.assertFalse(controller.is_active())
        self.assertEqual([e[0] for e in events], ["ok", "skip", "error"])

    def test_cancel_does_not_block_ui(self):
        controller = ProcessController()
        output = []
        child_code = "import time; print('start',flush=True); time.sleep(25)"
        def work():
            output.append(controller.run([sys.executable, "-u", "-c", child_code],
                                         os.environ.copy(), lambda *_: None))
        worker = threading.Thread(target=work, daemon=True)
        worker.start()
        for _ in range(100):
            if controller.is_active():
                break
            time.sleep(0.01)
        self.assertTrue(controller.is_active())
        t0 = time.monotonic()
        controller.cancel()
        self.assertLess(time.monotonic() - t0, 0.8)
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive(), "child survived cancellation")
        self.assertEqual(len(output), 1)
        self.assertNotEqual(output[0].returncode, 0)

    def test_filter_never_executes_user_content_as_shell(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            url = "https://pinterest.com/user/normal-board/"
            cmd = build_command(url, root, root / "config.json", media_mode="images")
            self.assertIsInstance(cmd, list)
            self.assertEqual(cmd[-1], normalize_board_url(url))
            self.assertIn("--filter", cmd)
            self.assertNotIn("--cookies-from-browser", cmd)


if __name__ == "__main__":
    unittest.main()
