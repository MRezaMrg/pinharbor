"""Subprocess runtime separated from Qt so it can be tested without the GUI.

All commands are argument arrays, never joined into a shell string.
This module does not contact Pinterest or collect credentials.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import signal
import subprocess
import threading
from typing import Callable

from studio_core import parse_output_event


@dataclass(frozen=True)
class BoardRunResult:
    returncode: int
    ok: int
    skipped: int
    last_error: str = ""


def kill_process_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=8,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if proc.poll() is None:
                proc.kill()
        else:
            # Most extractors shut down gracefully on SIGTERM. Escalate if a
            # child/ffmpeg process ignores termination, preventing hung threads.
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError, ProcessLookupError):
        try:
            proc.kill()
        except OSError:
            pass


class ProcessController:
    """One active child. Requests to stop never block the UI thread."""

    def __init__(self):
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None

    def is_active(self) -> bool:
        with self._lock:
            return self._process is not None

    def cancel(self) -> None:
        """Non-blocking cancellation, safe to invoke from a UI callback."""
        with self._lock:
            proc = self._process
        if proc and proc.poll() is None:
            threading.Thread(target=kill_process_tree, args=(proc,), daemon=True,
                             name="pbstudio-process-killer").start()

    def run(self, argv: list[str], env: dict[str, str],
            on_event: Callable[[str, str, int, int], None],
            should_cancel: Callable[[], bool] = lambda: False) -> BoardRunResult:
        opts = dict(stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, bufsize=1,
                    encoding="utf-8", errors="replace", env=env)
        if os.name == "nt":
            opts["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            opts["start_new_session"] = True
        proc = subprocess.Popen(argv, **opts)
        with self._lock:
            self._process = proc
        ok = skipped = 0
        error = ""
        try:
            if should_cancel():
                self.cancel()
            assert proc.stdout is not None
            for raw in proc.stdout:
                kind, message = parse_output_event(raw)
                if kind == "ok":
                    ok += 1
                elif kind == "skip":
                    skipped += 1
                elif kind == "error":
                    error = message[:500]
                on_event(kind, message, ok, skipped)
            code = proc.wait()
            return BoardRunResult(code, ok, skipped, error)
        finally:
            if proc.poll() is None:
                kill_process_tree(proc)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
            try:
                if proc.stdout:
                    proc.stdout.close()
            finally:
                with self._lock:
                    if self._process is proc:
                        self._process = None
