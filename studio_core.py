"""Platform-neutral, testable application logic for PinHarbor 2.5.

Legacy product identity: Pinterest Board Studio (for safe in-place migration).

Only Pinterest boards / sections are accepted as external inputs. The program
never assembles a shell command from user-provided values.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Iterable, Iterator
from urllib.parse import unquote, urlsplit

APP_NAME = "PinHarbor"
APP_VERSION = "2.6.0"
IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp", ".tif", ".tiff"})
VIDEO_EXTS = frozenset({".mp4", ".webm", ".mov", ".m4v", ".mkv", ".avi", ".flv", ".ts"})
MEDIA_IMAGES = tuple(sorted(s.removeprefix(".") for s in IMAGE_EXTS))
MEDIA_VIDEOS = tuple(sorted(s.removeprefix(".") for s in VIDEO_EXTS)) + ("m3u8",)
ALLOWED_BROWSERS = {"none", "chrome", "edge", "firefox", "brave"}
KNOWN_PINTEREST_DOMAINS = frozenset({
    "pinterest.com", "pinterest.co.uk", "pinterest.com.au", "pinterest.com.br",
    "pinterest.com.mx", "pinterest.ca", "pinterest.de", "pinterest.fr",
    "pinterest.it", "pinterest.es", "pinterest.nl", "pinterest.pt",
    "pinterest.at", "pinterest.ch", "pinterest.se", "pinterest.dk",
    "pinterest.no", "pinterest.be", "pinterest.ie", "pinterest.co.nz",
    "pinterest.jp", "pinterest.in", "pinterest.ru", "pinterest.com.tr",
    "pinterest.co.kr",
})
RESERVED_FIRST_SEGMENTS = {"pin", "search", "ideas", "explore", "today", "business", "settings", "_saved", "_created", "login", "about", "privacy", "terms"}


class URLValidationError(ValueError):
    pass


def normalize_board_url(raw: str) -> str:
    """Validate / normalize a board or section URL; strip query and fragment."""
    raw = raw.strip().strip('<>\"\'')
    if not raw:
        raise URLValidationError("آدرس بورد خالی است.")
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    try:
        u = urlsplit(raw)
        host = (u.hostname or "").casefold().rstrip(".")
    except ValueError as exc:
        raise URLValidationError("ساختار آدرس نامعتبر است.") from exc
    if u.scheme.lower() not in ("http", "https") or host not in KNOWN_PINTEREST_DOMAINS and not any(host.endswith("." + d) for d in KNOWN_PINTEREST_DOMAINS):
        raise URLValidationError("فقط لینک‌های رسمی Pinterest پشتیبانی می‌شوند.")
    try:
        contains_auth_port = bool(u.username or u.password or u.port is not None)
    except ValueError as exc:
        raise URLValidationError("شماره پورت در آدرس نامعتبر است.") from exc
    if contains_auth_port:
        raise URLValidationError("لینک بورد نباید اطلاعات ورود یا شماره پورت داشته باشد.")
    parts = [p for p in u.path.split("/") if p]
    if not 2 <= len(parts) <= 3:
        raise URLValidationError("لینک باید مربوط به بورد یا بخش داخلی بورد باشد.")
    decoded = [unquote(p) for p in parts]
    if decoded[0].casefold() in RESERVED_FIRST_SEGMENTS:
        raise URLValidationError("لینک پین، پروفایل یا صفحه جست‌وجو، لینک بورد محسوب نمی‌شود.")
    for s in decoded:
        if not s or s in (".", "..") or any(c in s for c in "/\\?#:\x00\r\n"):
            raise URLValidationError("مسیر بورد معتبر نیست.")
    return "https://" + host + "/" + "/".join(parts) + "/"


def board_identity(url: str) -> str:
    """Deduplicate equivalent www/m subdomains without changing displayed URLs."""
    parsed = urlsplit(normalize_board_url(url))
    host = parsed.hostname or ""
    if host.startswith(("www.", "m.")):
        host = host.split(".", 1)[1]
    return host.casefold() + parsed.path.casefold()


def choose_destination(saved_custom: str, app_folder: Path) -> Path:
    """Restore only explicitly selected folders; defaults follow the installed app."""
    if saved_custom:
        selected = Path(saved_custom).expanduser()
        if selected.is_dir():
            return selected.resolve()
    return Path(app_folder).resolve()


def check_destination_writable(folder: Path) -> None:
    """Fail before starting a large download if output cannot be written."""
    import tempfile
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("پوشه خروجی وجود ندارد.")
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix=".pbs-test-", delete=True):
            pass
    except OSError as exc:
        raise ValueError("امکان نوشتن در پوشه انتخاب‌شده وجود ندارد؛ پوشه دیگری انتخاب کنید.") from exc


def parse_boards(text: str) -> list[str]:
    """Accept one board per line; ignore blank lines, deduplicate in order."""
    result: list[str] = []
    seen = set()
    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        try:
            address = normalize_board_url(raw)
        except URLValidationError as exc:
            raise URLValidationError(f"خط {lineno}: {exc}") from exc
        key = board_identity(address)
        if key not in seen:
            result.append(address)
            seen.add(key)
    if not result:
        raise URLValidationError("حداقل یک لینک بورد وارد کنید.")
    return result


def board_title(url: str) -> str:
    u = urlsplit(normalize_board_url(url))
    return " / ".join(unquote(s) for s in u.path.split("/") if s)


@dataclass
class QueueEntry:
    url: str
    status: str = "pending"
    discovered: int = 0
    expected: int = 0
    new: int = 0
    skipped: int = 0
    last_error: str = ""

    def __post_init__(self):
        self.url = normalize_board_url(self.url)


def dump_queue(entries: Iterable[QueueEntry]) -> str:
    """Portable JSON queue; intentionally exports no passwords/proxy/cookies."""
    data = {"format": "PBS-queue", "version": 2, "boards": [e.url for e in entries]}
    return json.dumps(data, ensure_ascii=False, indent=2)


def load_queue(data: str) -> list[QueueEntry]:
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError("فایل صف JSON معتبر نیست.") from exc
    if not isinstance(parsed, dict) or parsed.get("format") != "PBS-queue" or not isinstance(parsed.get("boards"), list):
        raise ValueError("فرمت فایل صف شناسایی نشد.")
    urls = parsed["boards"]
    if len(urls) > 1000 or not all(isinstance(v, str) for v in urls):
        raise ValueError("تعداد لینک‌ها یا ساختار فایل صف معتبر نیست.")
    return [QueueEntry(url) for url in parse_boards("\n".join(urls))]


# Session is separate from the portable export (which intentionally has URLs only).
# No cookie data, proxy, token or browser profile details are stored here.
SESSION_STATES = frozenset({"pending", "running", "done", "partial", "error", "skipped", "stopped", "empty"})


def dump_session(entries: Iterable[QueueEntry]) -> str:
    rows = [{"url": e.url, "status": e.status, "discovered": e.discovered, "expected": e.expected, "new": e.new,
             "skipped": e.skipped, "last_error": e.last_error[:350]}
            for e in entries]
    return json.dumps({"format": "PBS-session", "version": 1, "boards": rows}, ensure_ascii=False)


def load_session(data: str) -> list[QueueEntry]:
    try:
        obj = json.loads(data)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("اطلاعات نشست معتبر نیست.") from exc
    if not isinstance(obj, dict) or obj.get("format") != "PBS-session" or not isinstance(obj.get("boards"), list):
        raise ValueError("فرمت نشست شناسایی نشد.")
    rows = obj["boards"]
    if len(rows) > 1000:
        raise ValueError("صف ذخیره‌شده بیش از حد بزرگ است.")
    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("url"), str):
            raise ValueError("رکوردهای نشست معتبر نیستند.")
        entry = QueueEntry(row["url"])
        key = board_identity(entry.url)
        if key in seen:
            continue
        seen.add(key)
        state = row.get("status", "pending")
        entry.status = ("stopped" if state == "running" else state) if state in SESSION_STATES else "pending"
        for key in ("new", "skipped", "discovered", "expected"):
            count = row.get(key, 0)
            setattr(entry, key, count if type(count) is int and 0 <= count <= 100000000 else 0)
        err = row.get("last_error", "")
        entry.last_error = err[:350] if isinstance(err, str) else ""
        result.append(entry)
    return result


def redact_secrets(message: str, proxy: str = "") -> str:
    """Redact proxy URL and common password/token variants from surfaced logs."""
    if not proxy:
        return message
    result = message.replace(proxy, "[proxy hidden]")
    try:
        parts = urlsplit(proxy)
        for secret in (parts.password, unquote(parts.password or "")):
            if secret:
                result = result.replace(secret, "[hidden]")
    except ValueError:
        pass
    return result


def default_output_directory() -> Path:
    # A compiled .exe started in Explorer must use its own folder, not C:\Windows\System32.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def get_tools_status() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("gallery-dl", "yt-dlp", "imageio-ffmpeg"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "نصب نشده"
    return versions


def ensure_ffmpeg_bin() -> str | None:
    if shutil.which("ffmpeg"):
        return None
    try:
        import imageio_ffmpeg
        binary = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if not binary.is_file():
            return None
        base = os.getenv("LOCALAPPDATA") or os.getenv("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        target_dir = Path(base) / "PinterestBoardStudio" / "bin"
        target_dir.mkdir(parents=True, exist_ok=True)
        name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        dest = target_dir / name
        if not dest.exists() or dest.stat().st_size != binary.stat().st_size:
            staging = target_dir / (name + ".tmp")
            shutil.copy2(binary, staging)
            staging.chmod(staging.stat().st_mode | 0o111)
            staging.replace(dest)
        return str(target_dir)
    except (ImportError, OSError):
        return None


def build_gallery_config() -> dict:
    # Keep extractor defaults (archive IDs and default directory templates)
    # instead of referring to possibly absent metadata fields.
    return {
        "extractor": {"pinterest": {"videos": True, "stories": True, "sections": True}},
        "downloader": {"progress": None},
        "output": {
            "mode": {"start": "", "success": "PBS_OK|{}\n", "skip": "PBS_SKIP|{}\n", "progress": "", "progress-total": ""},
            "shorten": False,
            "stdout": {"encoding": "utf-8", "errors": "replace", "line_buffering": True},
        },
    }


def save_config(path: Path) -> None:
    path.write_text(json.dumps(build_gallery_config(), ensure_ascii=False, indent=2), encoding="utf-8")


def engine_prefix() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--engine"]
    return [sys.executable, "-m", "gallery_dl"]


def validate_proxy(raw: str) -> str:
    s = raw.strip()
    if not s:
        return ""
    try:
        u = urlsplit(s)
        port = u.port
    except ValueError as exc:
        raise ValueError("پراکسی معتبر نیست.") from exc
    if u.scheme not in ("http", "https", "socks5", "socks5h") or not u.hostname or u.path not in ("", "/") or u.query or u.fragment or (port is not None and port == 0):
        raise ValueError("پراکسی باید مانند http://127.0.0.1:7890 باشد.")
    return s


def build_command(board: str, destination: Path, config_file: Path, *,
                  media_mode: str = "all", folders: bool = True,
                  metadata: bool = False, browser: str = "none",
                  throttle: bool = True, proxy: str = "", limit: int = 0,
                  rate: str = "unlimited", abort_skips: int = 0) -> list[str]:
    """Build subprocess argv safely; never invoke a shell to interpret it."""
    board = normalize_board_url(board)
    if media_mode not in {"all", "images", "videos"}:
        raise ValueError("نوع رسانه معتبر نیست.")
    if browser not in ALLOWED_BROWSERS:
        raise ValueError("مرورگر معتبر نیست.")
    if type(limit) is not int or not 0 <= limit <= 100000:
        raise ValueError("حداکثر فایل باید صفر تا ۱۰۰٬۰۰۰ باشد.")
    if type(abort_skips) is not int or not 0 <= abort_skips <= 1000:
        raise ValueError("محدودیت تکراری نامعتبر است.")
    if rate not in {"unlimited", "250k", "500k", "1M", "2M", "5M"}:
        raise ValueError("محدودیت سرعت نامعتبر است.")
    proxy = validate_proxy(proxy)
    dest = Path(destination).resolve()
    archive_dir = dest / ".pinterest-studio"
    archive_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        *engine_prefix(), "--config-ignore", "--config-json", str(config_file),
        "-d" if folders else "-D", str(dest),
        "--download-archive", str(archive_dir / "download_archive.sqlite3"),
        "--windows-filenames", "--no-input", "--no-colors", "--http-timeout", "35",
        "--retries", "4", "--sleep-429", "30",
        # Track unique pin IDs, even when files already exist in the archive.
        # This is an observed count, NOT a claim of complete board coverage.
        "--Print", "prepare:PINHARBOR_SEEN|{id}",
    ]
    if throttle:
        cmd.extend(["--sleep-request", "0.8-1.5"])
    if metadata:
        cmd.append("--write-metadata")
    if media_mode != "all":
        allowed = MEDIA_IMAGES if media_mode == "images" else MEDIA_VIDEOS
        cmd.extend(["--filter", f"extension in {repr(allowed)}"])
    if browser != "none":
        cmd.extend(["--cookies-from-browser", browser])
    if proxy:
        cmd.extend(["--proxy", proxy])
    if limit:
        cmd.extend(["--range", f"1-{limit}"])
    if rate != "unlimited":
        cmd.extend(["--limit-rate", rate])
    if abort_skips:
        cmd.extend(["--abort", str(abort_skips)])
    cmd.append(board)
    return cmd


def assess_board_coverage(discovered: int, expected: int, new: int, skipped: int) -> str:
    """Never present an unverifiable count as proof a board was fully captured.

    ``discovered`` counts unique PIN IDs emitted by the engine. ``expected``
    is an optional human-entered reference from Pinterest. Neither is an API
    assertion. Counting files cannot substitute for counting pins; a pin can
    contain more than one media item or no downloadable item.
    """
    if min(discovered, expected, new, skipped) < 0:
        raise ValueError("Counts must be nonnegative")
    if new + skipped == 0:
        return "empty"
    if expected and discovered < expected:
        return "partial"
    return "done"


def parse_output_event(line: str) -> tuple[str, str]:
    """Distinguish successful media from archive skips and ordinary log lines."""
    s = line.rstrip("\r\n")
    if s.startswith("PINHARBOR_SEEN|"):
        return "seen", s[len("PINHARBOR_SEEN|"):]
    if s.startswith("PBS_OK|"):
        return "ok", s[7:]
    if s.startswith("PBS_SKIP|"):
        return "skip", s[9:]
    if "[error]" in s.casefold() or "[critical]" in s.casefold():
        return "error", s
    return "log", s


def diagnose_error(message: str) -> str:
    """Actionable Persian hint; original engine detail stays in the log."""
    s = message.casefold()
    if "429" in s or "too many requests" in s or "rate limit" in s:
        return "محدودیت تعداد درخواست (429): زمان بدهید و مکث بین درخواست‌ها را فعال بگذارید."
    if "403" in s or "forbidden" in s or "unauthorized" in s or "401" in s:
        return "دسترسی رد شد: ورود به حساب پینترست و انتخاب مرورگر را بررسی کنید."
    if "cookies" in s or "cookie" in s or "database is locked" in s:
        return "خواندن کوکی مرورگر ناموفق بود؛ مرورگر را ببندید یا حالت عمومی را امتحان کنید."
    if "ffmpeg" in s:
        return "ابزار FFmpeg در دسترس نیست؛ نصب موتورهای دانلود را بررسی کنید."
    if "no module named" in s or "modulenotfounderror" in s:
        return "یکی از وابستگی‌ها نصب نیست؛ فایل اجرای ویندوز یا به‌روزرسانی موتور را اجرا کنید."
    if "connection" in s or "timeout" in s or "timed out" in s:
        return "ارتباط شبکه قطع یا کند است؛ اینترنت و تنظیمات پراکسی را بررسی کنید."
    if "permission denied" in s or "access is denied" in s:
        return "اجازه نوشتن یا دسترسی وجود ندارد؛ پوشه ذخیره‌سازی را بررسی کنید."
    return "جزئیات خطا در گزارش زنده ثبت شده است؛ لینک و دسترسی بورد را بررسی کنید."


def media_kind(file: Path) -> str | None:
    ext = file.suffix.casefold()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return None


def iter_media_files(root: Path) -> Iterator[Path]:
    """Index local media only, avoiding internal databases, partial and metadata files."""
    root = Path(root)
    if not root.is_dir():
        return
    # The default destination is the app's own folder; don't list app icons,
    # branding samples, or Python/packaging assets as downloaded media.
    # Explicit user destinations elsewhere are *never* subjected to this filter.
    is_application_root = root.resolve() == default_output_directory().resolve()
    app_directories = {"assets", "docs", "tests", "build", "dist", "venv", "__pycache__"}
    app_images = {"app_icon.png", "app_icon.ico"}
    for parent, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".pinterest-studio" and not d.startswith(".")]
        if is_application_root and Path(parent).resolve() == root.resolve():
            dirs[:] = [d for d in dirs if d not in app_directories]
        for filename in files:
            if is_application_root and Path(parent).resolve() == root.resolve() and filename in app_images:
                continue
            p = Path(parent) / filename
            if filename.startswith(".") or filename.lower().endswith(".part") or not media_kind(p):
                continue
            if p.is_symlink():
                continue
            yield p


def list_media_files(root: Path) -> list[Path]:
    found = list(iter_media_files(root))
    # Stable sorting across platforms: recent files first, then filename.
    def key(p: Path):
        try:
            return -p.stat().st_mtime, str(p).casefold()
        except OSError:
            return 0, str(p).casefold()
    return sorted(found, key=key)


def format_size(n: int) -> str:
    num = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            return f"{num:,.1f} {unit}" if unit != "B" else f"{int(num):,} B"
        num /= 1024
    return f"{num:.1f} TB"


def export_manifest_csv(root: Path, target: Path, files: Iterable[Path]) -> int:
    """CSV contains local path data only and is Excel friendly (UTF-8 BOM)."""
    root = root.resolve()
    count = 0
    with target.open("w", newline="", encoding="utf-8-sig") as stream:
        out = csv.writer(stream)
        out.writerow(["path", "type", "extension", "bytes", "modified_iso"])
        from datetime import datetime
        for item in files:
            try:
                stat = item.stat()
                rel = item.resolve().relative_to(root)
            except (OSError, ValueError):
                continue
            out.writerow([str(rel), media_kind(item) or "unknown", item.suffix.lower(), stat.st_size,
                         datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")])
            count += 1
    return count
