"""Fast, offline dependency preflight for the Windows source launcher.

No network activity. A stamp is only recorded after pip succeeds; editing
requirements.txt causes a re-check and a reinstall on the next app launch.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

REQUIRED_IMPORTS = ("PySide6", "gallery_dl", "yt_dlp", "imageio_ffmpeg", "socks")
ROOT = Path(__file__).resolve().parents[1]


def requirements_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def modules_present() -> bool:
    return all(importlib.util.find_spec(module) is not None for module in REQUIRED_IMPORTS)


def installation_is_current(requirements: Path, stamp: Path) -> bool:
    if not requirements.is_file() or not stamp.is_file():
        return False
    return stamp.read_text(encoding="ascii").strip() == requirements_digest(requirements) and modules_present()


def write_stamp(requirements: Path, stamp: Path) -> None:
    if not modules_present():
        raise RuntimeError("Required Python modules are missing after installation.")
    stamp.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="pinharbor-", suffix=".tmp", dir=stamp.parent)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as handle:
            handle.write(requirements_digest(requirements) + "\n")
        os.replace(name, stamp)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "record"))
    parser.add_argument("--requirements", type=Path, default=ROOT / "requirements.txt")
    parser.add_argument("--stamp", type=Path, default=Path(sys.prefix) / ".pinharbor-deps.sha256")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        print("PinHarbor requires Python 3.10 or newer.", file=sys.stderr)
        return 3
    try:
        if args.command == "check":
            return 0 if installation_is_current(args.requirements, args.stamp) else 1
        write_stamp(args.requirements, args.stamp)
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"Dependency check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
