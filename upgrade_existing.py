"""Safe in-place upgrade of a source-based PinHarbor / Pinterest Board Studio installation.

This updater uses only the Python standard library. It NEVER removes media,
settings (Qt QSettings), or the download archive. It also creates a local
rollback snapshot before writing application files.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid

from release_manifest import APP_FILES

IDENTITY = "Pinterest Board Studio"
BACKUP_FOLDER = Path(".pinterest-studio") / "app-backups"
VERSION_RE = re.compile(r'^APP_VERSION\s*=\s*[\'\"](\d+\.\d+\.\d+)[\'\"]', re.M)


class UpgradeError(ValueError):
    pass


def version_at(folder: Path) -> str:
    core = Path(folder) / "studio_core.py"
    app = Path(folder) / "pinterest_studio.py"
    if not core.is_file() or not app.is_file():
        raise UpgradeError("پوشه انتخاب‌شده نصب برنامه نیست (studio_core.py / pinterest_studio.py پیدا نشد).")
    txt = core.read_text(encoding="utf-8-sig")
    if IDENTITY not in txt and "PinHarbor" not in txt:
        raise UpgradeError("پوشه انتخاب‌شده نصب سازگار PinHarbor / Pinterest Board Studio نیست.")
    match = VERSION_RE.search(txt)
    if not match:
        raise UpgradeError("نسخه نصب فعلی مشخص نیست؛ بروزرسانی خودکار لغو شد.")
    return match.group(1)


def parse_version(value: str) -> tuple[int, int, int]:
    return tuple(int(v) for v in value.split("."))  # type: ignore[return-value]


def backup_root(target: Path) -> Path:
    return target / BACKUP_FOLDER


def snapshot_name(previous: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"before-{previous}-{stamp}-{uuid.uuid4().hex[:6]}"


def safe_relative(name: str) -> Path:
    p = Path(name)
    if p.is_absolute() or not p.parts or any(x in ("..", ".") for x in p.parts):
        raise UpgradeError("مسیر فایل بکاپ ناامن است.")
    return p


def verify_package(source: Path) -> bool:
    """Verify update archive checksums before touching the old installation.

    A local source checkout may omit the generated manifest. A distributed
    update ZIP always includes it; SHA256 detects corruption, not authenticity.
    """
    manifest = source / "update-manifest.json"
    if not manifest.exists():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UpgradeError("فایل بررسی صحت بسته آپدیت نامعتبر است.") from exc
    expected = data.get("files") if isinstance(data, dict) else None
    if not isinstance(expected, dict) or set(expected) != set(APP_FILES):
        raise UpgradeError("فهرست فایل‌های بسته آپدیت با نسخه برنامه تطابق ندارد.")
    if data.get("version") != version_at(source):
        raise UpgradeError("نسخه فایل سلامت آپدیت با نسخه سورس مطابقت ندارد.")
    for name in APP_FILES:
        digest = expected[name]
        if not isinstance(digest, str) or len(digest) != 64:
            raise UpgradeError("اثر انگشت فایل آپدیت نامعتبر است: " + name)
        actual = hashlib.sha256((source / name).read_bytes()).hexdigest()
        if actual != digest.lower():
            raise UpgradeError("فایل آپدیت آسیب دیده یا تغییر کرده است: " + name)
    return True


def _reject_symlink_parents(root: Path, rel: Path) -> None:
    """Do not let an installed symlink redirect writes outside the app folder."""
    current = root
    for part in rel.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise UpgradeError("مسیر مقصد دارای پیوند ناامن است: " + str(rel))


def select_target() -> Path:
    try:
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        result = filedialog.askdirectory(title="پوشه نسخه قبلی Pinterest Board Studio را انتخاب کنید")
        root.destroy()
        if result:
            return Path(result)
    except Exception:
        pass
    raw = input("مسیر پوشه نسخه قبلی را وارد کنید: ").strip().strip('"')
    if not raw:
        raise UpgradeError("هیچ پوشه‌ای انتخاب نشد.")
    return Path(raw)


def upgrade(source: Path, target: Path, *, allow_same: bool = False) -> dict:
    source = source.resolve()
    target = target.resolve()
    if source == target and not allow_same:
        raise UpgradeError("فایل آپدیت را در پوشه‌ای جدا از نصب فعلی استخراج و اجرا کنید.")
    if not target.is_dir():
        raise UpgradeError("پوشه نصب قبلی وجود ندارد.")
    incoming = version_at(source)
    previous = version_at(target)
    if parse_version(incoming) < parse_version(previous):
        raise UpgradeError(f"نسخه موجود {previous} جدیدتر از بسته {incoming} است؛ نصب نسخه قدیمی مجاز نیست.")
    if any(not (source / rel).is_file() for rel in APP_FILES):
        missing = [name for name in APP_FILES if not (source / name).is_file()]
        raise UpgradeError("بسته آپدیت ناقص است: " + ", ".join(missing))
    verify_package(source)
    for name in APP_FILES:
        _reject_symlink_parents(target, safe_relative(name))
    if incoming == previous:
        import filecmp
        # Repair interrupted/manual installs instead of silently accepting mixed files.
        if all((target / rel).is_file() and filecmp.cmp(source / rel, target / rel, shallow=False)
               for rel in APP_FILES):
            return {"status": "up-to-date", "version": incoming, "target": str(target)}

    # staging is on the same volume as the destination for atomic replacements.
    staging = Path(tempfile.mkdtemp(prefix=".pbs-upgrade-", dir=target))
    backup = backup_root(target) / snapshot_name(previous)
    existed: list[str] = []
    installed: list[str] = list(APP_FILES)
    changed: list[str] = []
    try:
        for name in APP_FILES:
            rel = safe_relative(name)
            dest = target / rel
            if dest.exists() and (dest.is_symlink() or not dest.is_file()):
                raise UpgradeError(f"فایل مقصد قابل جایگزینی نیست: {name}")
            stage_file = staging / rel
            stage_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / rel, stage_file)
        backup.mkdir(parents=True, exist_ok=False)
        for name in APP_FILES:
            rel = safe_relative(name)
            path = target / rel
            if path.exists():
                destination = backup / "files" / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                existed.append(name)
        manifest = {"format": "PBS-upgrade-backup", "from_version": previous,
                    "to_version": incoming, "previous_files": existed, "installed_files": installed,
                    "created_utc": datetime.now(timezone.utc).isoformat()}
        (backup / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        for name in APP_FILES:
            rel = safe_relative(name)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging / rel, dest)
            changed.append(name)
    except Exception:
        # Restore earlier files if a copy/replacement failed partway through.
        for name in reversed(changed):
            rel = safe_relative(name)
            dest = target / rel
            if name in existed:
                saved = backup / "files" / rel
                if saved.exists():
                    shutil.copy2(saved, dest)
            elif dest.is_file():
                dest.unlink()
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {"status": "upgraded", "from": previous, "to": incoming,
            "backup": str(backup), "target": str(target), "files": len(installed)}


def latest_backup(target: Path) -> Path:
    root = backup_root(target)
    if not root.is_dir():
        raise UpgradeError("بکاپی از نسخه قبلی در این پوشه وجود ندارد.")
    backups = sorted((x for x in root.iterdir() if (x / "manifest.json").is_file()),
                     key=lambda x: x.name, reverse=True)
    if not backups:
        raise UpgradeError("بکاپ معتبری وجود ندارد.")
    return backups[0]


def rollback(target: Path) -> dict:
    target = target.resolve()
    backup = latest_backup(target)
    obj = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    if obj.get("format") != "PBS-upgrade-backup":
        raise UpgradeError("فرمت بکاپ ناشناخته است.")
    original = obj.get("previous_files", [])
    installed = obj.get("installed_files", [])
    if not isinstance(original, list) or not isinstance(installed, list):
        raise UpgradeError("محتوای بکاپ معتبر نیست.")
    original = [str(safe_relative(v)) for v in original]
    installed = [str(safe_relative(v)) for v in installed]
    if any(name not in APP_FILES for name in (*original, *installed)):
        raise UpgradeError("فهرست بکاپ شامل فایل غیرمجاز است.")
    if (backup / "ROLLED_BACK.txt").exists():
        raise UpgradeError("این بکاپ قبلاً بازگردانده شده است.")
    for name in (*original, *installed):
        _reject_symlink_parents(target, safe_relative(name))
    # Reject a stale rollback if a different app version has since been installed.
    current = version_at(target)
    if current != obj.get("to_version"):
        raise UpgradeError(f"نسخه کنونی ({current}) با نسخه این بکاپ مطابقت ندارد؛ بازگشت لغو شد.")
    with tempfile.TemporaryDirectory(prefix=".pbs-rollback-", dir=target) as tmp:
        staged = Path(tmp)
        for name in original:
            src = backup / "files" / name
            if not src.is_file():
                raise UpgradeError("یک فایل مورد نیاز در بکاپ وجود ندارد: " + name)
            dest = staged / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        for name in original:
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged / name, dest)
    for name in installed:
        # Leave recovery launcher in place so the running Windows batch remains intact.
        if name not in original and name not in {"upgrade_existing.py", "Rollback Last Update.bat", "Upgrade Existing Installation.bat"}:
            path = target / name
            if path.is_file():
                path.unlink()
    (backup / "ROLLED_BACK.txt").write_text("Rollback completed.\n", encoding="utf-8")
    return {"status": "rolled-back", "from": current,
            "to": obj["from_version"], "backup": str(backup)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="PinHarbor source updater with rollback")
    parser.add_argument("--target", type=Path, help="Path to existing installation")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args(argv)
    try:
        target = args.target if args.target else select_target()
        if args.rollback:
            outcome = rollback(target)
        else:
            outcome = upgrade(args.source, target)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0
    except (UpgradeError, OSError, ValueError, json.JSONDecodeError) as exc:
        print("UPDATE ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
