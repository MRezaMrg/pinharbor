"""PinHarbor v2.6 — bilingual local Qt desktop application.

No Pinterest credentials are collected. gallery-dl uses the optional locally
selected browser session. Download subprocesses run without shell=True.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from collections import deque, OrderedDict
import time

from PySide6.QtCore import Qt, QSettings, QThread, QTimer, Signal, QSize, QUrl
from PySide6.QtGui import (
    QDesktopServices, QFont, QIcon, QImageReader, QKeySequence,
    QPainter, QPen, QPixmap, QShortcut, QColor, QPolygon, QImage,
)
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
)
from PySide6.QtCore import QPoint
from ui_language import tr, set_language, language
# Localized Qt wrappers. The QSettings application identity is unchanged.
from ui_qt import (QLabel, QPushButton, QCheckBox, QComboBox, QSpinBox,
                   QPlainTextEdit, QLineEdit, QTableWidget, QTableWidgetItem,
                   QTabWidget, QMessageBox)

from studio_core import (
    APP_VERSION, QueueEntry, URLValidationError, board_title, build_command,
    default_output_directory, dump_queue, ensure_ffmpeg_bin,
    export_manifest_csv, format_size, get_tools_status, list_media_files,
    load_queue, load_session, dump_session, media_kind, normalize_board_url, parse_boards,
    save_config, validate_proxy, redact_secrets, diagnose_error,
    board_identity, choose_destination, check_destination_writable, assess_board_coverage,
)
from download_runtime import ProcessController


from ui_theme import STYLE_SHEET, choose_font, available_fonts, PALETTE
from PySide6.QtCore import QRectF
from PySide6.QtGui import QFontDatabase, QLinearGradient, QRadialGradient


class AmbientCanvas(QWidget):
    """Cached ambient glow; repaint is a cheap blit during normal UI activity."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache: QPixmap | None = None

    def paintEvent(self, event):
        if self.width() < 1 or self.height() < 1:
            return
        if self._cache is None or self._cache.size() != self.size():
            self._cache = QPixmap(self.size())
            self._cache.fill(Qt.GlobalColor.transparent)
            painter = QPainter(self._cache)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            rect = QRectF(self.rect())
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor("#1D0D1A"))
            gradient.setColorAt(0.47, QColor("#130B14"))
            gradient.setColorAt(1, QColor("#09080D"))
            painter.fillRect(rect, gradient)
            w, h = max(self.width(), 1), max(self.height(), 1)
            for x, y, r, color in (
                (0.13*w, 0.08*h, 0.76*w, QColor(147, 40, 84, 70)),
                (0.92*w, 0.65*h, 0.59*w, QColor(223, 105, 151, 34)),
                (0.5*w, 1.16*h, 0.58*w, QColor(107, 36, 83, 34)),
            ):
                glow = QRadialGradient(x, y, max(r, 1))
                glow.setColorAt(0, color)
                glow.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
                painter.fillRect(rect, glow)
            painter.end()
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cache)
        painter.end()



def panel(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(19, 17, 19, 18)
    layout.setSpacing(12)
    heading = QLabel(title)
    heading.setObjectName("heading")
    layout.addWidget(heading)
    return frame, layout


def muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    label.setWordWrap(True)
    return label


def row(*widgets) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(9)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


class Metric(QFrame):
    def __init__(self, label: str):
        super().__init__()
        self.setObjectName("stat")
        lay = QVBoxLayout(self)
        lay.setSpacing(5)
        lay.setContentsMargins(15, 12, 15, 12)
        self.value = QLabel("0")
        self.value.setObjectName("number")
        self.value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel(label)
        title.setObjectName("label")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.value)
        lay.addWidget(title)

    def set_count(self, value: int):
        self.value.setText(f"{value:,}")


class DownloadWorker(QThread):
    message = Signal(str)
    board_started = Signal(int)
    board_stats = Signal(int, int, int)
    board_done = Signal(int, str, str)
    board_discovered = Signal(int, int)
    all_done = Signal(bool, bool, int, int, int)

    def __init__(self, entries: list[QueueEntry], dest: Path, opts: dict):
        super().__init__()
        self.entries = [QueueEntry(e.url) for e in entries]
        self.dest = dest
        self.opts = dict(opts)
        self.expected_count = int(self.opts.pop("expected_count", 0)) if len(entries) == 1 else 0
        self._stop = threading.Event()
        self._skip = threading.Event()
        self._active_index: int | None = None
        self._guard = threading.Lock()
        self._runner = ProcessController()

    def stop_all(self):
        self._stop.set()
        self._runner.cancel()  # child termination is dispatched in a helper thread

    def skip_current(self):
        with self._guard:
            active = self._active_index is not None
        if active:
            self._skip.set()
            self._runner.cancel()

    def run(self):
        total_ok = total_skip = failures = 0
        try:
            ffmpeg_dir = ensure_ffmpeg_bin()
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8:replace"
            env["PYTHONUNBUFFERED"] = "1"
            if ffmpeg_dir:
                env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
                self.message.emit("FFmpeg آماده استفاده است.")
            elif not shutil.which("ffmpeg"):
                self.message.emit("هشدار: FFmpeg پیدا نشد؛ امکان دریافت برخی ویدیوها محدود است.")
            with tempfile.TemporaryDirectory(prefix="pbstudio_") as work:
                cfg = Path(work) / "gallery.json"
                save_config(cfg)
                for idx, entry in enumerate(self.entries):
                    if self._stop.is_set():
                        break
                    self._skip.clear()
                    with self._guard:
                        self._active_index = idx
                    self.board_started.emit(idx)
                    self.message.emit(f"\n— بورد {idx + 1}/{len(self.entries)} | {entry.url}")
                    try:
                        cmd = build_command(entry.url, self.dest, cfg, **self.opts)
                        last_stats_emitted = 0.0
                        current_ok = current_skip = 0
                        current_pin_ids: set[str] = set()
                        def on_event(kind, msg, ok, skipped):
                            nonlocal total_ok, total_skip, last_stats_emitted, current_ok, current_skip
                            current_ok, current_skip = ok, skipped
                            if kind == "seen":
                                current_pin_ids.add(msg)
                                if len(current_pin_ids) <= 3 or len(current_pin_ids) % 10 == 0:
                                    self.board_discovered.emit(idx, len(current_pin_ids))
                            elif kind == "ok":
                                total_ok += 1
                                if ok <= 8 or ok % 20 == 0:
                                    self.message.emit("✓ " + msg)
                            elif kind == "skip":
                                total_skip += 1
                                if skipped <= 3 or skipped % 50 == 0:
                                    self.message.emit("↷ موجود یا ردشده: " + msg)
                            elif msg:
                                self.message.emit(msg[:700])
                            now = time.monotonic()
                            if kind in ("ok", "skip") and (now - last_stats_emitted >= 0.22 or ok + skipped <= 3):
                                self.board_stats.emit(idx, ok, skipped)
                                last_stats_emitted = now
                        result = self._runner.run(
                            cmd, env, on_event,
                            should_cancel=lambda: self._stop.is_set() or self._skip.is_set(),
                        )
                        self.board_stats.emit(idx, result.ok, result.skipped)
                        self.board_discovered.emit(idx, result.discovered)
                        if self._stop.is_set():
                            self.board_done.emit(idx, "stopped", "فرایند متوقف شد")
                            break
                        if self._skip.is_set():
                            self.board_done.emit(idx, "skipped", "به درخواست کاربر رد شد")
                            self.message.emit("بورد رد شد و صف ادامه یافت.")
                            continue
                        if result.returncode != 0:
                            failures += 1
                            reason = result.last_error or f"کد خروج موتور: {result.returncode}"
                            reason = redact_secrets(reason, self.opts.get("proxy", ""))
                            self.board_done.emit(idx, "error", reason)
                            self.message.emit(f"خطا در پردازش بورد: {reason}")
                        else:
                            coverage = assess_board_coverage(result.discovered, self.expected_count,
                                                             result.ok, result.skipped)
                            if coverage == "empty":
                                self.board_done.emit(idx, "empty", "هیچ فایل قابل‌دسترسی گزارش نشد؛ لینک یا دسترسی حساب را بررسی کنید")
                            elif coverage == "partial":
                                reason = (f"فقط {result.discovered} پین شناسایی شد؛ انتظار {self.expected_count} پین بود. "
                                          "با حساب مرورگر واردشده دوباره بررسی کنید."
                                          if result.discovered else
                                          "شمارش پین‌ها از موتور دریافت نشد؛ تعداد کامل بورد قابل تأیید نیست. "
                                          "برای بررسی دوباره از حساب مرورگر واردشده استفاده کنید.")
                                self.board_done.emit(idx, "partial", reason)
                            else:
                                self.board_done.emit(idx, "done", "دریافت موارد شناسایی‌شده پایان یافت؛ تعداد واقعی بورد ممکن است بیشتر باشد.")
                    except Exception as exc:
                        failures += 1
                        reason = redact_secrets(f"{type(exc).__name__}: {exc}", self.opts.get("proxy", ""))
                        self.board_done.emit(idx, "error", reason)
                        self.message.emit(f"خطای پردازش: {reason}")
                    finally:
                        with self._guard:
                            self._active_index = None
        except Exception as exc:
            failures += 1
            self.message.emit(f"خطای اجرای صف: {type(exc).__name__}: {exc}")
        self.all_done.emit(not self._stop.is_set() and failures == 0,
                           self._stop.is_set(), total_ok, total_skip, failures)


class ScanWorker(QThread):
    ready = Signal(object, str)

    def __init__(self, folder: Path):
        super().__init__()
        self.folder = folder

    def run(self):
        try:
            self.ready.emit(list_media_files(self.folder), "")
        except Exception as exc:
            self.ready.emit([], str(exc))


class ImageBatchWorker(QThread):
    ready = Signal(str, object, int)

    def __init__(self, files: list[Path], generation: int):
        super().__init__()
        self.files = files
        self.generation = generation

    def run(self):
        for path in self.files:
            if self.isInterruptionRequested():
                return
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            natural = reader.size()
            if natural.isValid():
                reader.setScaledSize(natural.scaled(QSize(158, 118), Qt.AspectRatioMode.KeepAspectRatio))
            image = reader.read()
            if not image.isNull() and not self.isInterruptionRequested():
                self.ready.emit(str(path), image, self.generation)


class ImagePreviewWorker(QThread):
    ready = Signal(str, int, object, object)

    def __init__(self, path: Path, generation: int):
        super().__init__()
        self.path = path
        self.generation = generation

    def run(self):
        if self.isInterruptionRequested():
            return
        reader = QImageReader(str(self.path))
        reader.setAutoTransform(True)
        natural = reader.size()
        if natural.isValid():
            reader.setScaledSize(natural.scaled(QSize(520, 520), Qt.AspectRatioMode.KeepAspectRatio))
        image = reader.read()
        if not self.isInterruptionRequested():
            self.ready.emit(str(self.path), self.generation, image, natural)


class VideoThumbnailWorker(QThread):
    ready = Signal(str, bytes)

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def cancel(self):
        self.requestInterruption()
        with self._lock:
            proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()  # does not wait for the process on the UI thread
            except OSError:
                pass

    def run(self):
        exe = shutil.which("ffmpeg")
        if not exe:
            try:
                import imageio_ffmpeg
                exe = imageio_ffmpeg.get_ffmpeg_exe()
            except (ImportError, OSError):
                return
        if self.isInterruptionRequested():
            return
        for seek in ("1", "0"):
            if self.isInterruptionRequested():
                return
            try:
                proc = subprocess.Popen(
                    [exe, "-nostdin", "-loglevel", "error", "-ss", seek, "-i", str(self.path),
                     "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
                )
                with self._lock:
                    self._proc = proc
                if self.isInterruptionRequested():
                    self.cancel()
                try:
                    data, _ = proc.communicate(timeout=7)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    data, _ = proc.communicate()
                if not self.isInterruptionRequested() and proc.returncode == 0 and 0 < len(data) < 12_000_000:
                    self.ready.emit(str(self.path), data)
                    return
            except (subprocess.SubprocessError, OSError):
                return
            finally:
                with self._lock:
                    self._proc = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"PinHarbor · v{APP_VERSION}")
        self.resize(1130, 850)
        self.setMinimumSize(790, 620)
        self.settings = QSettings("PinterestBoardStudio", "Desktop")
        self.jobs: list[QueueEntry] = []
        self.worker: DownloadWorker | None = None
        self.scan_worker: ScanWorker | None = None
        self.video_workers: list[VideoThumbnailWorker] = []
        self.gallery_scanned_once = False
        self._gallery_scan_path: Path | None = None
        self._pending_scan = False
        self._thumb_generation = 0
        self._thumb_pending: deque[Path] = deque()
        self._thumb_worker: ImageBatchWorker | None = None
        self._thumb_items: dict[str, QListWidgetItem] = {}
        self._thumb_cache: OrderedDict[str, QImage] = OrderedDict()
        self._preview_workers: list[ImagePreviewWorker] = []
        self._preview_generation = 0
        self._pending_preview_path: Path | None = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(140)
        self._preview_timer.timeout.connect(self._start_image_preview)
        self._close_requested = False
        self._finish_result: tuple | None = None
        self._run_started = 0.0
        self._gallery_change_timer = QTimer(self)
        self._gallery_change_timer.setSingleShot(True)
        self._gallery_change_timer.setInterval(400)
        self._gallery_change_timer.timeout.connect(self.refresh_gallery)
        self.all_files: list[Path] = []
        self.gallery_filtered: list[Path] = []
        self.gallery_loaded = 0
        self._preview_path: str = ""
        self._folder = default_output_directory()
        self.build_ui()
        self.restore_settings()
        self.render_queue()
        geom = self.settings.value("window_geometry")
        if geom:
            self.restoreGeometry(geom)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.start_from_shortcut)
        QShortcut(QKeySequence("Ctrl+Shift+V"), self, activated=self.paste_board)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.link_input.setFocus)
        self.delete_shortcut = QShortcut(QKeySequence("Delete"), self.queue)
        self.delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.delete_shortcut.activated.connect(self.remove_selected)
        QShortcut(QKeySequence("F5"), self, activated=self.refresh_gallery)
        self._checkpoint_timer = QTimer(self)
        self._checkpoint_timer.setInterval(4000)
        self._checkpoint_timer.timeout.connect(self.save_settings)
        self._link_validation_timer = QTimer(self)
        self._link_validation_timer.setSingleShot(True)
        self._link_validation_timer.setInterval(240)
        self._link_validation_timer.timeout.connect(self.update_link_preview)
        self.link_input.textChanged.connect(self._link_validation_timer.start)
        self._queue_filter_timer = QTimer(self)
        self._queue_filter_timer.setSingleShot(True)
        self._queue_filter_timer.setInterval(160)
        self._queue_filter_timer.timeout.connect(self.filter_queue)
        self._gallery_search_timer = QTimer(self)
        self._gallery_search_timer.setSingleShot(True)
        self._gallery_search_timer.setInterval(220)
        self._gallery_search_timer.timeout.connect(self.filter_gallery)

    def build_ui(self):
        central = AmbientCanvas()
        central.setObjectName("ambientCanvas")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(19, 18, 19, 14)
        outer.setSpacing(12)
        hero = QFrame()
        hero.setObjectName("hero")
        header = QHBoxLayout(hero)
        header.setContentsMargins(22, 15, 22, 15)
        header.setSpacing(15)
        symbol = QLabel()
        symbol.setObjectName("brandIcon")
        symbol.setFixedSize(55, 55)
        symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "app_icon.png"
        if brand_path.is_file():
            from PySide6.QtGui import QPixmap
            symbol.setPixmap(QPixmap(str(brand_path)).scaled(55, 55, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            symbol.setText("P")
        header.addWidget(symbol)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        heading = QLabel("PinHarbor")
        heading.setObjectName("title")
        heading.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        eyebrow = QLabel("YOUR BOARD MEDIA LIBRARY")
        eyebrow.setObjectName("eyebrow")
        eyebrow.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        titles.addWidget(eyebrow)
        titles.addWidget(heading)
        titles.addWidget(muted("دانلود تصاویر و ویدیوها، مدیریت بوردها و مرور فایل‌ها — همه در یک‌جا"))
        header.addLayout(titles, 1)
        self.version_label = QLabel(f"VERSION {APP_VERSION}")
        self.version_label.setObjectName("versionChip")
        self.version_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        header.addWidget(self.version_label)
        help_btn = QPushButton("راهنما")
        help_btn.setObjectName("quiet")
        help_btn.setToolTip("آموزش سریع استفاده از PinHarbor")
        help_btn.clicked.connect(self.show_quick_guide)
        header.addWidget(help_btn)
        outer.addWidget(hero)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        self.tabs.addTab(self.build_download_tab(), "صف دانلود")
        self.tabs.addTab(self.build_gallery_tab(), "کتابخانه رسانه‌ها")
        self.tabs.addTab(self.build_settings_tab(), "تنظیمات")
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.set_running(False)
        status_frame = QFrame()
        status_frame.setObjectName("statusStrip")
        status_bar = QHBoxLayout(status_frame)
        status_bar.setContentsMargins(13, 9, 13, 9)
        self.status = muted("آماده · لینک بورد را بچسبانید و «دانلود از لینک‌ها» را بزنید.")
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        status_bar.addWidget(self.status, 1)
        self.elapsed_label = muted("")
        status_bar.addWidget(self.elapsed_label)
        outer.addWidget(status_frame)
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self.update_elapsed)

    def build_download_tab(self):
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("scrollBody")
        sc.setWidget(body)
        root = QVBoxLayout(body)
        root.setContentsMargins(2, 4, 8, 10)
        root.setSpacing(13)
        frame, p = panel("افزودن بورد به صف")
        p.addWidget(muted("لینک یک بورد را بچسبانید و مستقیم دانلود کنید؛ برای چند بورد، هر لینک را در یک خط بنویسید."))
        self.link_input = QPlainTextEdit()
        self.link_input.setPlaceholderText("https://www.pinterest.com/username/board-name/\nhttps://www.pinterest.com/username/other-board/")
        self.link_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.link_input.setMinimumHeight(78)
        self.link_input.setMaximumHeight(112)
        p.addWidget(self.link_input)
        self.link_preview = muted("لینک بورد را وارد کنید؛ برای چند بورد، هر لینک در یک خط باشد.")
        p.addWidget(self.link_preview)
        self.quick_btn = QPushButton("دانلود از لینک‌ها")
        self.quick_btn.setObjectName("primary")
        self.quick_btn.setToolTip("فقط لینک‌های همین کادر را اجرا می‌کند، نه تمام بوردهای صف. میانبر: Ctrl+Enter")
        self.quick_btn.clicked.connect(self.quick_download)
        self.add_btn = QPushButton("فقط افزودن به صف")
        self.add_btn.clicked.connect(self.add_boards)
        paste = QPushButton("جای‌گذاری")
        paste.clicked.connect(self.paste_board)
        buttons = row(self.quick_btn, self.add_btn, paste)
        buttons.addStretch(1)
        p.addLayout(buttons)
        root.addWidget(frame)

        frame, p = panel("بوردهای من")
        self.queue_search = QLineEdit()
        self.queue_search.setPlaceholderText("جست‌وجوی نام بورد...")
        self.queue_search.textChanged.connect(lambda *_: self._queue_filter_timer.start() if hasattr(self, "_queue_filter_timer") else self.filter_queue())
        self.queue_state = QComboBox()
        for label, val in (("همه وضعیت‌ها", "all"), ("در انتظار", "pending"),
                           ("تکمیل‌شده", "done"), ("نیازمند بررسی", "problem")):
            self.queue_state.addItem(label, val)
        self.queue_state.currentIndexChanged.connect(self.filter_queue)
        p.addLayout(row(self.queue_search, self.queue_state))
        self.queue = QTableWidget(0, 6)
        self.queue.setHorizontalHeaderLabels(["نام بورد", "وضعیت", "پین کشف‌شده", "جدید", "تکراری", "جزئیات"])
        self.queue.setAlternatingRowColors(True)
        self.queue.setSortingEnabled(False)
        self.queue.setToolTip("روی نام بورد دوبار کلیک کنید تا در مرورگر باز شود.")
        self.queue.cellDoubleClicked.connect(self.open_board_in_browser)
        self.queue.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.queue.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.queue.setMinimumHeight(200)
        self.queue.setShowGrid(False)
        self.queue.verticalHeader().hide()
        h = self.queue.horizontalHeader()
        h.setStretchLastSection(True)
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        p.addWidget(self.queue)
        self.queue_empty = QLabel("هنوز بوردی اضافه نشده. لینک را در بالای صفحه وارد کنید.")
        self.queue_empty.setObjectName("empty")
        self.queue_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p.addWidget(self.queue_empty)
        self.queue_count = muted("۰ بورد")
        p.addWidget(self.queue_count)
        self.remove_btn = QPushButton("حذف انتخاب‌شده")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.up_btn = QPushButton("بالا")
        self.up_btn.clicked.connect(lambda: self.move_selected(-1))
        self.down_btn = QPushButton("پایین")
        self.down_btn.clicked.connect(lambda: self.move_selected(1))
        self.import_btn = QPushButton("واردکردن صف")
        self.import_btn.clicked.connect(self.import_queue)
        self.export_btn = QPushButton("خروجی صف")
        self.export_btn.clicked.connect(self.export_queue)
        self.select_btn = QPushButton("دانلود انتخاب‌شده‌ها")
        self.select_btn.clicked.connect(self.start_selected)
        self.clear_btn = QPushButton("حذف تکمیل‌شده‌ها")
        self.clear_btn.clicked.connect(self.clear_completed)
        tools = row(self.remove_btn, self.up_btn, self.down_btn)
        tools.addWidget(self.clear_btn)
        tools.addStretch(1)
        tools.addWidget(self.import_btn)
        tools.addWidget(self.export_btn)
        p.addLayout(tools)
        p.addWidget(muted("انتخاب چندگانه: Ctrl / Shift  ·  بازکردن لینک: دوبار کلیک  ·  حذف: Delete"))
        root.addWidget(frame)

        frame, p = panel("محل ذخیره‌سازی و شروع عملیات")
        self.dest_input = QLineEdit(str(self._folder))
        self.dest_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.dest_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        browse = QPushButton("انتخاب پوشه")
        browse.clicked.connect(self.browse_destination)
        self.browse_btn = browse
        reset = QPushButton("پوشه اجرا")
        reset.clicked.connect(lambda: self.dest_input.setText(str(default_output_directory())))
        open_output = QPushButton("بازکردن پوشه")
        open_output.clicked.connect(self.open_output_folder)
        path_row = row(self.dest_input, browse, reset, open_output)
        p.addLayout(path_row)
        opts = QHBoxLayout()
        opts.addWidget(QLabel("نوع فایل"))
        self.media_box = QComboBox()
        for label, val in (("تصویر و ویدیو", "all"), ("فقط تصاویر", "images"), ("فقط ویدیوها", "videos")):
            self.media_box.addItem(label, val)
        opts.addWidget(self.media_box, 2)
        opts.addWidget(QLabel("مرورگر حساب"))
        self.browser_box = QComboBox()
        for label, val in (("بدون حساب (عمومی)", "none"), ("Google Chrome", "chrome"),
                           ("Microsoft Edge", "edge"), ("Firefox", "firefox"), ("Brave", "brave")):
            self.browser_box.addItem(label, val)
        opts.addWidget(self.browser_box, 2)
        p.addLayout(opts)
        p.addWidget(muted("اگر تعداد فایل‌ها کمتر از پین‌های بورد است، مرورگری را انتخاب کنید که در آن وارد Pinterest شده‌اید و بورد را دوباره دانلود کنید."))
        expected_row = QHBoxLayout()
        expected_row.addWidget(QLabel("تعداد پین‌های بورد (اختیاری)"))
        self.expected_box = QSpinBox()
        self.expected_box.setRange(0, 1000000)
        self.expected_box.setSpecialValueText("نامشخص")
        self.expected_box.setToolTip("برای یک بورد، تعداد نمایش‌داده‌شده در پینترست را وارد کنید تا نتیجه کمتر از انتظار مشخص شود.")
        expected_row.addWidget(self.expected_box)
        expected_row.addWidget(muted("برای یک بورد؛ شمارنده تقریبی و قابل‌تغییر است."), 1)
        p.addLayout(expected_row)
        self.limit_notice = muted("")
        p.addWidget(self.limit_notice)
        self.limit_clear_btn = QPushButton("برداشتن محدودیت دریافت")
        self.limit_clear_btn.clicked.connect(self.clear_download_limits)
        p.addWidget(self.limit_clear_btn)
        self.start_btn = QPushButton("شروع دانلود همه بوردها")
        self.start_btn.setToolTip("تمام بوردها دوباره بررسی می‌شوند؛ آرشیو از دریافت تکراری فایل‌های موفق جلوگیری می‌کند.")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self.start_all)
        self.retry_btn = QPushButton("اجرای دوباره موارد ناموفق")
        self.retry_btn.clicked.connect(self.retry_failed)
        self.skip_btn = QPushButton("ردکردن بورد جاری")
        self.skip_btn.clicked.connect(self.skip_current)
        self.stop_btn = QPushButton("توقف کل صف")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self.stop_all)
        p.addLayout(row(self.start_btn, self.select_btn, self.retry_btn))
        p.addLayout(row(self.skip_btn, self.stop_btn))
        self.busy = QProgressBar()
        self.busy.setRange(0, 100)
        self.busy.setValue(0)
        self.busy.setTextVisible(False)
        p.addWidget(self.busy)
        self.progress_caption = muted("پیشرفت بر اساس بوردهای تکمیل‌شده نمایش داده می‌شود، نه تعداد نامشخص پین‌ها.")
        p.addWidget(self.progress_caption)
        root.addWidget(frame)

        stats = QHBoxLayout()
        stats.setSpacing(11)
        self.stat_boards = Metric("بورد پردازش‌شده")
        self.stat_ok = Metric("فایل جدید")
        self.stat_skip = Metric("تکراری / ردشده")
        self.stat_err = Metric("نیازمند بررسی")
        for stat in (self.stat_boards, self.stat_ok, self.stat_skip, self.stat_err):
            stats.addWidget(stat, 1)
        root.addLayout(stats)
        self.log_toggle = QPushButton("نمایش گزارش فنی و جزئیات دانلود")
        self.log_toggle.setObjectName("expand")
        self.log_toggle.clicked.connect(self.toggle_logs)
        root.addWidget(self.log_toggle)
        frame, p = panel("گزارش رویدادها")
        self.log_frame = frame
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.logs.document().setMaximumBlockCount(1200)
        self.logs.setMinimumHeight(155)
        p.addWidget(self.logs)
        logbuttons = QHBoxLayout()
        save = QPushButton("ذخیره گزارش TXT")
        save.clicked.connect(self.export_logs)
        logbuttons.addWidget(save)
        clear = QPushButton("پاک‌کردن نمایش گزارش")
        clear.clicked.connect(self.logs.clear)
        logbuttons.addWidget(clear)
        logbuttons.addStretch(1)
        p.addLayout(logbuttons)
        root.addWidget(frame)
        self.log_frame.setVisible(False)
        # Completeness reference is a user-supplied number, not a scraper promise.
        self.active_only_controls = [self.skip_btn, self.stop_btn]
        self.queue_mod_controls = [self.quick_btn, self.add_btn, self.remove_btn, self.up_btn, self.down_btn,
                                   self.import_btn, self.export_btn, self.browse_btn, self.clear_btn, self.select_btn]
        self.dest_input.textChanged.connect(self.mark_gallery_dirty)
        return sc

    def build_gallery_tab(self):
        page = QWidget()
        page.setObjectName("glassPage")
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(3, 3, 3, 6)
        controls = QHBoxLayout()
        self.gallery_search = QLineEdit()
        self.gallery_search.setPlaceholderText("جست‌وجو در نام و مسیر فایل‌ها ...")
        self.gallery_search.textChanged.connect(lambda *_: self._gallery_search_timer.start() if hasattr(self, "_gallery_search_timer") else self.filter_gallery())
        controls.addWidget(self.gallery_search, 3)
        self.gallery_mode = QComboBox()
        for name, value in (("همه رسانه‌ها", "all"), ("فقط تصاویر", "image"), ("فقط ویدیوها", "video")):
            self.gallery_mode.addItem(name, value)
        self.gallery_mode.currentIndexChanged.connect(self.filter_gallery)
        controls.addWidget(self.gallery_mode, 1)
        self.gallery_sort = QComboBox()
        for label, value in (("جدیدترین", "recent"), ("نام: الف تا ی", "name"), ("نام: معکوس", "name_desc")):
            self.gallery_sort.addItem(label, value)
        self.gallery_sort.currentIndexChanged.connect(self.filter_gallery)
        controls.addWidget(self.gallery_sort, 1)
        refresh = QPushButton("بازخوانی پوشه")
        refresh.clicked.connect(self.refresh_gallery)
        controls.addWidget(refresh)
        export = QPushButton("CSV فیلتر فعلی")
        export.clicked.connect(self.export_csv)
        controls.addWidget(export)
        layout.addLayout(controls)
        self.gallery_total = muted("برای نمایش فایل‌های موجود، «بازخوانی پوشه» را بزنید.")
        layout.addWidget(self.gallery_total)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.gallery = QListWidget()
        self.gallery.setViewMode(QListView.ViewMode.IconMode)
        self.gallery.setResizeMode(QListView.ResizeMode.Adjust)
        self.gallery.setFlow(QListView.Flow.LeftToRight)
        self.gallery.setMovement(QListView.Movement.Static)
        self.gallery.setIconSize(QSize(162, 124))
        self.gallery.setGridSize(QSize(186, 181))
        self.gallery.setSpacing(8)
        self.gallery.setUniformItemSizes(True)
        self.gallery.setWordWrap(True)
        self.gallery.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.gallery.itemDoubleClicked.connect(lambda _: self.open_selected_file())
        self.gallery.currentItemChanged.connect(self.show_preview)
        self.gallery.verticalScrollBar().valueChanged.connect(self.on_gallery_scroll)
        split.addWidget(self.gallery)
        preview, p = panel("پیش‌نمایش فایل")
        self.preview_art = QLabel("یک فایل را انتخاب کنید")
        self.preview_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_art.setMinimumSize(280, 280)
        self.preview_art.setMaximumHeight(370)
        self.preview_art.setStyleSheet("background:rgba(25, 14, 25, 215);border:1px dashed rgba(243, 174, 202, 100);border-radius:12px;")
        p.addWidget(self.preview_art)
        self.preview_name = muted("—")
        self.preview_name.setWordWrap(True)
        self.preview_name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        p.addWidget(self.preview_name)
        self.preview_details = muted("")
        p.addWidget(self.preview_details)
        open_file = QPushButton("بازکردن فایل")
        open_file.clicked.connect(self.open_selected_file)
        open_dir = QPushButton("بازکردن پوشه فایل")
        open_dir.clicked.connect(self.open_selected_parent)
        copy_path = QPushButton("کپی مسیر")
        copy_path.clicked.connect(self.copy_selected_path)
        p.addLayout(row(open_file, open_dir, copy_path))
        p.addStretch(1)
        self.gallery_preview_buttons = (open_file, open_dir, copy_path)
        for btn in self.gallery_preview_buttons:
            btn.setEnabled(False)
        split.addWidget(preview)
        split.setSizes([700, 345])
        layout.addWidget(split, 1)
        load_more = QPushButton("نمایش فایل‌های بیشتر")
        load_more.clicked.connect(self.load_more_gallery)
        self.gallery_more = load_more
        load_more.setToolTip("هر بار حداکثر ۵۵ فایل به گالری اضافه می‌شود.")
        load_more.setEnabled(False)
        layout.addWidget(load_more)
        return page

    def build_settings_tab(self):
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        container = QWidget()
        container.setObjectName("scrollBody")
        sc.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 5, 8, 15)
        layout.setSpacing(14)
        language_panel, language_layout = panel("زبان / Language")
        self.language_box = QComboBox()
        self.language_box.addItem("فارسی", "fa")
        self.language_box.addItem("English", "en")
        selected_language = str(self.settings.value("language", "fa"))
        self.language_box.setCurrentIndex(max(0, self.language_box.findData(selected_language)))
        language_layout.addWidget(self.language_box)
        language_layout.addWidget(muted("Language changes take effect after restarting the app. / تغییر زبان پس از اجرای مجدد برنامه اعمال می‌شود."))
        self.language_box.currentIndexChanged.connect(self.change_language)
        layout.addWidget(language_panel)
        font_panel, font_layout = panel("ظاهر و تایپوگرافی")
        font_layout.addWidget(muted("تم زرشکی، صورتی پاستلی و مشکی با پنل‌های شیشه‌ای فعال است. فونت‌ها فقط از میان فونت‌های نصب‌شده انتخاب می‌شوند."))
        font_layout.addWidget(QLabel("فونت رابط کاربری"))
        self.ui_font_box = QComboBox()
        families = QFontDatabase.families()
        recommended = choose_font(families)
        self.ui_font_box.addItem(f"Automatic · {recommended}" if language() == "en" else f"خودکار · {recommended}", "auto")
        for family in available_fonts(families):
            self.ui_font_box.addItem(family, family)
        self.ui_font_box.currentIndexChanged.connect(self.update_ui_font)
        font_layout.addWidget(self.ui_font_box)
        font_help = QPushButton("صفحه رسمی فونت وزیرمتن")
        font_help.setObjectName("quiet")
        font_help.setToolTip("در صورت تمایل، فونت وزیرمتن را از منبع رسمی نصب کنید و برنامه را دوباره باز کنید.")
        font_help.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/rastikerdar/vazirmatn")))
        font_layout.addWidget(font_help)
        font_layout.addWidget(muted("برای استفاده از وزیرمتن، آن را جداگانه روی ویندوز نصب و برنامه را مجدداً اجرا کنید. فایل فونت داخل آپدیت قرار ندارد."))
        layout.addWidget(font_panel)
        frame, p = panel("حالت دریافت")
        self.group_check = QCheckBox("ساخت فولدر جداگانه برای هر بورد و بخش")
        self.group_check.setChecked(True)
        self.meta_check = QCheckBox("ذخیره فایل JSON فراداده کنار رسانه")
        self.slow_check = QCheckBox("مکث بین درخواست‌ها؛ کاهش احتمال محدودسازی")
        self.slow_check.setChecked(True)
        for check in (self.group_check, self.meta_check, self.slow_check):
            p.addWidget(check)
        p.addWidget(muted("آرشیو دانلود در ‎.pinterest-studio‎ نگهداری می‌شود و با آپدیت برنامه پاک نمی‌شود."))
        layout.addWidget(frame)
        frame, p = panel("محدودیت‌ها و کنترل شبکه")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.addWidget(QLabel("حداکثر رسانه از هر بورد"), 0, 0)
        self.limit_box = QSpinBox()
        self.limit_box.setRange(0, 100000)
        self.limit_box.setValue(0)
        self.limit_box.setSpecialValueText("نامحدود")
        self.limit_box.valueChanged.connect(self.update_limit_notice)
        grid.addWidget(self.limit_box, 1, 0)
        grid.addWidget(QLabel("محدودیت سرعت دانلود"), 0, 1)
        self.rate_box = QComboBox()
        for label, val in (("بدون محدودیت", "unlimited"), ("250 KB/s", "250k"),
                           ("500 KB/s", "500k"), ("1 MB/s", "1M"),
                           ("2 MB/s", "2M"), ("5 MB/s", "5M")):
            self.rate_box.addItem(label, val)
        grid.addWidget(self.rate_box, 1, 1)
        grid.addWidget(QLabel("توقف زودهنگام بعد از فایل‌های تکراریِ متوالی"), 2, 0)
        self.abort_box = QSpinBox()
        self.abort_box.setRange(0, 1000)
        self.abort_box.setSpecialValueText("غیرفعال (پیشنهادی)")
        self.abort_box.valueChanged.connect(self.update_limit_notice)
        grid.addWidget(self.abort_box, 3, 0)
        p.addLayout(grid)
        p.addWidget(muted("اگر گزینه توقف زودهنگام را فعال کنید، ممکن است پین‌های جدیدِ عقب‌تر از موارد قدیمی بررسی نشوند؛ پیش‌فرض غیرفعال است."))
        p.addWidget(QLabel("پراکسی (اختیاری، فقط در حافظه همین اجرا)"))
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://127.0.0.1:7890  |  socks5h://127.0.0.1:1080")
        self.proxy_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        p.addWidget(self.proxy_input)
        layout.addWidget(frame)
        self.advanced_network_panel = frame
        self.advanced_network_panel.setVisible(False)
        frame, p = panel("درباره موتور")
        self.engine_info = muted("")
        p.addWidget(self.engine_info)
        verify = QPushButton("بررسی بسته‌های نصب‌شده")
        verify.clicked.connect(self.show_engine_status)
        preflight_btn = QPushButton("آزمایش آمادگی دانلود")
        preflight_btn.clicked.connect(self.show_preflight)
        report = QPushButton("کپی گزارش فنی (بدون اطلاعات ورود)")
        report.clicked.connect(self.copy_diagnostics)
        p.addLayout(row(verify, preflight_btn, report))
        p.addWidget(muted("ورود فقط با کوکی ذخیره‌شده در مرورگر خودتان انجام می‌شود. برنامه رمز عبور پینترست را درخواست یا ذخیره نمی‌کند."))
        layout.addWidget(frame)
        self.advanced_diagnostics_panel = frame
        self.advanced_diagnostics_panel.setVisible(False)
        self.advanced_button = QPushButton("نمایش گزینه‌های بیشتر")
        self.advanced_button.setObjectName("quiet")
        self.advanced_button.clicked.connect(self.toggle_advanced_settings)
        layout.insertWidget(2, self.advanced_button)
        layout.addStretch(1)
        self.show_engine_status()
        return sc

    def clear_download_limits(self):
        self.limit_box.setValue(0)
        self.abort_box.setValue(0)
        self.save_settings()

    def update_limit_notice(self, *_):
        if not hasattr(self, "limit_notice"):
            return
        limit = self.limit_box.value()
        early = self.abort_box.value()
        active = bool(limit or early)
        if language() == "en":
            text = (f"Active download limit: max {limit} items per board. " if limit else "") + \
                   (f"Early stop after {early} consecutive duplicates is on." if early else "")
        else:
            text = (f"محدودیت فعال: حداکثر {limit} مورد از هر بورد بررسی می‌شود. " if limit else "") + \
                   (f"توقف زودهنگام پس از {early} مورد تکراری متوالی فعال است." if early else "")
        self.limit_notice.setText(text)
        self.limit_clear_btn.setVisible(active)
        self.limit_notice.setVisible(active)

    def change_language(self, *_):
        selected = self.language_box.currentData()
        if selected == str(self.settings.value("language", "fa")):
            return
        self.settings.setValue("language", selected)
        self.settings.sync()
        QMessageBox.information(self,
            "Language / زبان", "Language saved. Restart PinHarbor to apply English or Persian.\nزبان ذخیره شد؛ برای اعمال تغییر، برنامه را ببندید و دوباره باز کنید.")

    def toggle_advanced_settings(self):
        visible = not self.advanced_network_panel.isVisible()
        self.advanced_network_panel.setVisible(visible)
        self.advanced_diagnostics_panel.setVisible(visible)
        self.advanced_button.setText("پنهان‌کردن گزینه‌های بیشتر" if visible else "نمایش گزینه‌های بیشتر")

    # --- Queue controls ---
    def restore_settings(self):
        def index_by_value(combo, key, default):
            i = combo.findData(self.settings.value(key, default))
            if i >= 0:
                combo.setCurrentIndex(i)
        index_by_value(self.ui_font_box, "ui_font", "auto")
        index_by_value(self.media_box, "media", "all")
        index_by_value(self.browser_box, "browser", "none")
        index_by_value(self.rate_box, "rate", "unlimited")
        self.group_check.setChecked(self.settings.value("group", True, type=bool))
        self.meta_check.setChecked(self.settings.value("meta", False, type=bool))
        self.slow_check.setChecked(self.settings.value("slow", True, type=bool))
        self.limit_box.setValue(self.settings.value("limit", 0, type=int))
        self.expected_box.setValue(self.settings.value("expected_count", 0, type=int))
        self.abort_box.setValue(self.settings.value("abort", 0, type=int))
        self.update_limit_notice()
        try:
            session = str(self.settings.value("session", ""))
            self.jobs = load_session(session) if session else load_queue(str(self.settings.value("queue", "")))
        except (ValueError, URLValidationError):
            self.jobs = []
        # Explicit custom paths survive restart; default follows the launch folder after a move/update.
        restored = choose_destination(str(self.settings.value("custom_destination", "") or ""), default_output_directory())
        self.dest_input.setText(str(restored))
        self.log_frame.setVisible(self.settings.value("logs_open", False, type=bool))
        self.log_toggle.setText("پنهان‌کردن گزارش فنی" if self.log_frame.isVisible() else "نمایش گزارش فنی و جزئیات دانلود")

    def update_ui_font(self, *_):
        """Apply the selected installed font without changing the theme/queue."""
        app = QApplication.instance()
        if app is None:
            return
        family = choose_font(QFontDatabase.families(), self.ui_font_box.currentData() or "auto")
        app.setFont(QFont(family, 10))
        if hasattr(self, "settings"):
            self.settings.setValue("ui_font", self.ui_font_box.currentData())

    def save_settings(self):
        self.settings.setValue("ui_font", self.ui_font_box.currentData())
        self.settings.setValue("media", self.media_box.currentData())
        self.settings.setValue("browser", self.browser_box.currentData())
        self.settings.setValue("rate", self.rate_box.currentData())
        self.settings.setValue("group", self.group_check.isChecked())
        self.settings.setValue("meta", self.meta_check.isChecked())
        self.settings.setValue("slow", self.slow_check.isChecked())
        self.settings.setValue("limit", self.limit_box.value())
        self.settings.setValue("expected_count", self.expected_box.value())
        self.settings.setValue("abort", self.abort_box.value())
        self.settings.setValue("session", dump_session(self.jobs))
        self.settings.setValue("queue", dump_queue(self.jobs))
        chosen = self.dest_input.text().strip()
        default = str(default_output_directory())
        self.settings.setValue("custom_destination", chosen if chosen and Path(chosen).expanduser() != Path(default) else "")
        self.settings.setValue("logs_open", self.log_frame.isVisible())
        self.settings.sync()

    def render_queue(self):
        self.queue.setRowCount(len(self.jobs))
        for index in range(len(self.jobs)):
            self.render_job(index)
        self.filter_queue()

    def filter_queue(self, *_):
        query = self.queue_search.text().strip().casefold()
        state = self.queue_state.currentData()
        self.queue.clearSelection()  # never remove a hidden previously selected row
        shown = 0
        for i, item in enumerate(self.jobs):
            matches_state = (state == "all" or item.status == state or
                             (state == "problem" and item.status in ("error", "partial", "empty", "stopped")))
            visible = matches_state and (not query or query in board_title(item.url).casefold() or query in item.url.casefold())
            self.queue.setRowHidden(i, not visible)
            shown += bool(visible)
        self.queue_empty.setVisible(shown == 0)
        self.queue_empty.setText("هنوز بوردی اضافه نشده. لینک را در بالای صفحه وارد کنید." if not self.jobs
                                 else "موردی با این فیلتر پیدا نشد؛ فیلتر را تغییر دهید.")
        self.queue_count.setText(f"{shown:,} board(s) shown · {len(self.jobs):,} queued" if language() == "en" else
                                 f"{shown:,} بورد نمایش داده می‌شود · {len(self.jobs):,} بورد در صف")

    def toggle_logs(self):
        expanded = not self.log_frame.isVisible()
        self.log_frame.setVisible(expanded)
        self.log_toggle.setText("پنهان‌کردن گزارش فنی" if expanded else "نمایش گزارش فنی و جزئیات دانلود")
        self.save_settings()

    def render_job(self, idx: int):
        if idx >= len(self.jobs):
            return
        entry = self.jobs[idx]
        states = {"pending": "در انتظار", "running": "در حال دانلود", "done": "تکمیل‌شده",
                  "error": "خطا", "skipped": "با درخواست کاربر رد شد", "stopped": "متوقف‌شده",
                  "empty": "بدون رسانه", "partial": "نیازمند بررسی"}
        values = [board_title(entry.url), states.get(entry.status, entry.status),
                  str(entry.discovered) if entry.discovered else "—",
                  str(entry.new), str(entry.skipped), entry.last_error or "—"]
        for col, value in enumerate(values):
            cell = self.queue.item(idx, col)
            if cell is None:
                cell = QTableWidgetItem()
                self.queue.setItem(idx, col, cell)
            cell.setText(value)
            if col == 0:
                cell.setToolTip(entry.url)
            if col == 5 and entry.last_error:
                cell.setToolTip(entry.last_error)
            if col in (2, 3, 4):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if entry.status in ("error", "partial"):
            self.queue.item(idx, 1).setForeground(QColor(PALETTE["error"]))
        elif entry.status == "done":
            self.queue.item(idx, 1).setForeground(QColor(PALETTE["success"]))
        elif entry.status == "running":
            self.queue.item(idx, 1).setForeground(QColor(PALETTE["rose"]))
        else:
            self.queue.item(idx, 1).setForeground(QColor(PALETTE["muted"]))

    def _insert_links(self) -> list[int] | None:
        if self.worker is not None:
            return None
        try:
            incoming = parse_boards(self.link_input.toPlainText())
        except URLValidationError as exc:
            QMessageBox.warning(self, "آدرس نامعتبر", str(exc))
            self.link_input.setFocus()
            return None
        known = {board_identity(e.url): i for i, e in enumerate(self.jobs)}
        if len(known) + sum(board_identity(u) not in known for u in incoming) > 1000:
            QMessageBox.warning(self, "صف بیش از حد بزرگ", "حداکثر ۱۰۰۰ بورد در یک صف پشتیبانی می‌شود.")
            return None
        selected = []
        fresh = 0
        for u in incoming:
            key = board_identity(u)
            if key not in known:
                known[key] = len(self.jobs)
                self.jobs.append(QueueEntry(u))
                fresh += 1
            selected.append(known[key])
        self.link_input.clear()
        self.render_queue()
        self.save_settings()
        self.status.setText(f"{fresh} بورد جدید افزوده شد؛ {len(selected)-fresh} لینک از قبل در صف بود.")
        return selected

    def add_boards(self):
        self._insert_links()

    def quick_download(self):
        indices = self._insert_links()
        if indices:
            self.start_jobs(indices)

    def update_link_preview(self):
        raw = self.link_input.toPlainText().strip()
        if not raw:
            self.link_preview.setText("لینک بورد را وارد کنید؛ برای چند بورد، هر لینک در یک خط باشد.")
            return
        try:
            boards = parse_boards(raw)
            self.link_preview.setText(f"{len(boards):,} بورد معتبر شناسایی شد · می‌توانید مستقیم دانلود کنید یا به صف اضافه کنید.")
        except URLValidationError as exc:
            self.link_preview.setText(f"نیاز به اصلاح لینک: {exc}")

    def show_quick_guide(self):
        if language() == "en":
            QMessageBox.information(self, "PinHarbor quick guide",
                "1. Paste one board URL per line.\n"
                "2. Click Download now. Open Library to browse your media.\n"
                "3. For fewer pins than expected, enter the Pinterest board count, "
                "select a browser where you are signed in, and retry.\n"
                "4. Change the language in Settings; restart to apply.\n\n"
                "Only download content you have the right to access and use.")
            return
        QMessageBox.information(
            self, "راهنمای سریع PinHarbor",
            "۱. لینک بورد را در کادر بالای صفحه وارد کنید.\n"
            "۲. روی «دانلود از لینک‌ها» بزنید. برای چند بورد، هر لینک را در یک خط بگذارید.\n"
            "۳. در تب کتابخانه رسانه‌ها، فایل‌های ذخیره‌شده را جست‌وجو کنید.\n"
            "۴. برای بوردهای محدود، از مرورگر حساب استفاده کنید.\n\n"
            "محتوای خصوصی یا غیرقابل‌دسترسی تضمین نمی‌شود؛ فقط محتوایی را دریافت کنید که اجازه استفاده دارید."
        )

    def show_preflight(self):
        versions = get_tools_status()
        packaged = bool(getattr(sys, "frozen", False))
        engine = packaged or versions.get("gallery-dl") != "نصب نشده"
        try:
            target = self.current_destination()
            check_destination_writable(target)
            folder = "پوشه خروجی قابل نوشتن است."
        except (ValueError, OSError) as exc:
            folder = f"پوشه خروجی مشکل دارد: {exc}"
        ffmpeg = bool(shutil.which("ffmpeg"))
        if not ffmpeg:
            try:
                import imageio_ffmpeg
                ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe()).is_file()
            except (ImportError, OSError):
                ffmpeg = False
        QMessageBox.information(
            self, "وضعیت آمادگی دانلود",
            f"موتور دانلود: {'آماده' if engine else 'نصب نشده'}\n"
            f"FFmpeg: {'در دسترس' if ffmpeg else 'پیدا نشد؛ بعضی ویدیوها ممکن است دانلود نشوند'}\n"
            f"{folder}\n\n"
            "این بررسی آفلاین است و اتصال به پینترست را آزمایش نمی‌کند."
        )

    def start_from_shortcut(self):
        if self.link_input.toPlainText().strip():
            self.quick_download()
        else:
            self.start_all()

    def paste_board(self):
        clip = QApplication.clipboard().text().strip()
        if clip:
            if self.link_input.toPlainText().strip():
                self.link_input.appendPlainText(clip)
            else:
                self.link_input.setPlainText(clip)

    def selected_job_indices(self) -> list[int]:
        return sorted({i.row() for i in self.queue.selectedIndexes()})

    def remove_selected(self):
        if self.tabs.currentIndex() != 0:
            return
        if self.worker is not None:
            return
        for idx in reversed(self.selected_job_indices()):
            self.jobs.pop(idx)
        self.render_queue()
        self.save_settings()

    def move_selected(self, delta: int):
        selected = self.selected_job_indices()
        if len(selected) != 1:
            return
        a = selected[0]
        b = a + delta
        if not 0 <= b < len(self.jobs):
            return
        self.jobs[a], self.jobs[b] = self.jobs[b], self.jobs[a]
        self.render_queue()
        self.queue.selectRow(b)
        self.save_settings()

    def start_selected(self):
        selected = self.selected_job_indices()
        if not selected:
            QMessageBox.information(self, "انتخاب بورد", "ابتدا یک یا چند بورد را از جدول انتخاب کنید.")
            return
        self.start_jobs(selected)

    def clear_completed(self):
        if self.worker is not None:
            return
        completed = sum(e.status in ("done", "skipped") for e in self.jobs)
        if not completed:
            self.status.setText("هیچ بورد تکمیل‌شده یا ردشده‌ای برای حذف از صف وجود ندارد.")
            return
        self.jobs = [e for e in self.jobs if e.status not in ("done", "skipped")]
        self.render_queue()
        self.save_settings()
        self.status.setText(f"{completed} بورد از صف پاک شد. فایل‌های دانلودشده حفظ شده‌اند.")

    def open_board_in_browser(self, row_index: int, column: int):
        if 0 <= row_index < len(self.jobs):
            QDesktopServices.openUrl(QUrl(self.jobs[row_index].url))

    def mark_gallery_dirty(self):
        self.gallery_scanned_once = False
        if self.tabs.currentIndex() == 1:
            self.all_files = []
            self.filter_gallery()
            self.gallery_total.setText("مسیر تغییر کرده؛ در حال بررسی پوشه جدید...")
            self._gallery_change_timer.start()

    def update_elapsed(self):
        elapsed = int(time.monotonic() - self._run_started)
        self.elapsed_label.setText(f"زمان اجرا: {elapsed // 60:02d}:{elapsed % 60:02d}")

    def import_queue(self):
        name, _ = QFileDialog.getOpenFileName(self, "واردکردن فایل صف", str(default_output_directory()), "JSON (*.json)")
        if not name:
            return
        try:
            incoming = load_queue(Path(name).read_text(encoding="utf-8-sig"))
            known = {board_identity(job.url) for job in self.jobs}
            for entry in incoming:
                identity = board_identity(entry.url)
                if identity not in known:
                    if len(self.jobs) >= 1000:
                        raise ValueError("حداکثر ۱۰۰۰ بورد پشتیبانی می‌شود.")
                    self.jobs.append(entry)
                    known.add(identity)
            self.render_queue()
            self.save_settings()
            self.status.setText(f"صف خوانده شد: {len(self.jobs)} بورد در فهرست.")
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "خطای واردکردن", str(exc))

    def export_queue(self):
        name, _ = QFileDialog.getSaveFileName(self, "ذخیره صف", str(default_output_directory() / "pinterest-boards.json"), "JSON (*.json)")
        if name:
            try:
                Path(name).write_text(dump_queue(self.jobs), encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "خطای خروجی", str(exc))

    def browse_destination(self):
        d = QFileDialog.getExistingDirectory(self, "پوشه رسانه‌ها", self.dest_input.text().strip() or str(default_output_directory()))
        if d:
            self.dest_input.setText(d)

    def open_output_folder(self):
        try:
            location = self.current_destination()
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "پوشه نامعتبر", str(exc))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(location)))

    def current_destination(self, create: bool = False) -> Path:
        value = self.dest_input.text().strip()
        if not value:
            raise ValueError("مسیر ذخیره‌سازی نمی‌تواند خالی باشد.")
        p = Path(value).expanduser().resolve()
        if create:
            p.mkdir(parents=True, exist_ok=True)
        if not p.is_dir():
            raise ValueError("پوشه خروجی وجود ندارد.")
        return p

    def current_options(self):
        return dict(media_mode=self.media_box.currentData(), browser=self.browser_box.currentData(),
                    folders=self.group_check.isChecked(), metadata=self.meta_check.isChecked(),
                    throttle=self.slow_check.isChecked(), proxy=validate_proxy(self.proxy_input.text()),
                    limit=self.limit_box.value(), rate=self.rate_box.currentData(),
                    abort_skips=self.abort_box.value())

    def start_all(self):
        self.start_jobs(list(range(len(self.jobs))))

    def retry_failed(self):
        indices = [i for i, e in enumerate(self.jobs) if e.status in ("error", "partial", "stopped", "empty")]
        if not indices:
            QMessageBox.information(self, "صف بدون خطا", "هیچ بورد ناموفق یا متوقف‌شده‌ای در صف نیست.")
            return
        self.start_jobs(indices)

    def start_jobs(self, indices: list[int]):
        # Keep this guard until finished() has been processed, not merely isRunning()==False.
        if self.worker is not None:
            return
        if not indices:
            QMessageBox.information(self, "صف خالی", "ابتدا لینک یک یا چند بورد را وارد صف کنید.")
            return
        if not getattr(sys, "frozen", False) and get_tools_status()["gallery-dl"] == "نصب نشده":
            QMessageBox.warning(self, "موتور دانلود نصب نیست", "ابتدا فایل Run on Windows.bat را اجرا کنید تا وابستگی‌های لازم نصب شوند.")
            return
        try:
            target = self.current_destination(create=True)
            check_destination_writable(target)
            opts = self.current_options()
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "تنظیمات نادرست", str(exc))
            return
        if len(indices) == 1:
            opts["expected_count"] = self.expected_box.value()
        self.save_settings()
        self._active_indices = indices
        subset: list[QueueEntry] = []
        for idx in indices:
            self.jobs[idx].status = "pending"
            self.jobs[idx].new = self.jobs[idx].skipped = self.jobs[idx].discovered = 0
            self.jobs[idx].expected = self.expected_box.value() if len(indices) == 1 else 0
            self.jobs[idx].last_error = ""
            self.render_job(idx)
            subset.append(QueueEntry(self.jobs[idx].url))
        self.save_settings()
        self.worker = DownloadWorker(subset, target, opts)
        self.worker.message.connect(self.append_log)
        self.worker.board_started.connect(self.on_board_started)
        self.worker.board_stats.connect(self.on_board_stats)
        self.worker.board_discovered.connect(self.on_board_discovered)
        self.worker.board_done.connect(self.on_board_done)
        self._finish_result = None
        self.worker.all_done.connect(self.remember_finish)
        self.worker.finished.connect(self.on_worker_finished)
        self._completed = 0
        for metric in (self.stat_boards, self.stat_ok, self.stat_skip, self.stat_err):
            metric.set_count(0)
        self.busy.setRange(0, len(indices))
        self.busy.setValue(0)
        self._run_started = time.monotonic()
        if len(indices) != 1 and self.expected_box.value():
            self.append_log("Expected pin count is checked for one board at a time; this run includes several boards.")
        self.elapsed_label.setText("زمان اجرا: 00:00")
        self._elapsed_timer.start()
        self._checkpoint_timer.start()
        self.set_running(True)
        self.status.setText(f"پردازش {len(indices)} بورد آغاز شد؛ تعداد کل فایل‌ها هنوز مشخص نیست.")
        self.append_log("\n===== شروع اجرای صف =====")
        self.append_log(f"مسیر: {target} | تعداد بورد: {len(indices)}")
        self.worker.start()

    def on_board_started(self, idx: int):
        actual = self._active_indices[idx]
        self.jobs[actual].status = "running"
        self.render_job(actual)
        self.filter_queue()
        self.queue.scrollToItem(self.queue.item(actual, 0))
        self.status.setText(f"در حال پردازش {idx + 1} از {len(self._active_indices)}: {board_title(self.jobs[actual].url)}")

    def on_board_discovered(self, idx: int, discovered: int):
        actual = self._active_indices[idx]
        self.jobs[actual].discovered = discovered
        self.render_job(actual)

    def on_board_stats(self, idx: int, ok: int, skipped: int):
        actual = self._active_indices[idx]
        entry = self.jobs[actual]
        entry.new = ok
        entry.skipped = skipped
        self.render_job(actual)
        self.stat_ok.set_count(sum(self.jobs[i].new for i in self._active_indices))
        self.stat_skip.set_count(sum(self.jobs[i].skipped for i in self._active_indices))

    def on_board_done(self, idx: int, state: str, message: str):
        actual = self._active_indices[idx]
        entry = self.jobs[actual]
        entry.status = state
        entry.last_error = (diagnose_error(message) if state == "error"
                            else message if state in ("empty", "partial") else "")
        self.render_job(actual)
        self.filter_queue()
        self._completed += 1
        self.busy.setValue(self._completed)
        self.progress_caption.setText(f"{self._completed} بورد از {len(self._active_indices)} بررسی شد؛ تعداد کل فایل‌های قابل دریافت ممکن است مشخص نباشد.")
        self.stat_boards.set_count(self._completed)
        self.stat_err.set_count(sum(self.jobs[i].status in ("error", "partial", "empty") for i in self._active_indices))
        self.save_settings()

    def remember_finish(self, success: bool, stopped: bool, ok: int, skipped: int, failed: int):
        self._finish_result = (success, stopped, ok, skipped, failed)

    def on_worker_finished(self):
        # This runs after QThread.finished, so a fresh job cannot overwrite a live QThread.
        result = self._finish_result or (False, False, 0, 0, 1)
        self._elapsed_timer.stop()
        self._checkpoint_timer.stop()
        self.on_all_done(*result)
        old = self.worker
        self.worker = None
        if old is not None:
            old.deleteLater()
        if self._close_requested:
            QTimer.singleShot(0, self._finish_close_when_idle)

    def on_all_done(self, success: bool, stopped: bool, ok: int, skipped: int, failed: int):
        self.set_running(False)
        if stopped:
            msg = ("Downloads stopped. Retry to continue without redownloading saved files."
                   if language() == "en" else
                   "عملیات متوقف شد. برای ادامه، اجرای دوباره صف از آرشیو استفاده می‌کند.")
        else:
            attention = sum(self.jobs[i].status in ("error", "partial", "empty") for i in self._active_indices)
            if attention:
                msg = (f"Finished checking: {ok} new files, {skipped} skipped. {attention} board(s) need review."
                       if language() == "en" else
                       f"صف بررسی شد: {ok} فایل جدید، {skipped} مورد موجود/ردشده؛ "
                       f"{attention} بورد نیازمند بررسی یا اجرای مجدد است.")
            else:
                msg = (f"Finished: {ok} new files, {skipped} already saved/skipped. Full Pinterest coverage is not guaranteed."
                       if language() == "en" else
                       f"صف پایان یافت: {ok} فایل جدید، {skipped} رسانه تکراری یا ازقبل دریافت‌شده.")
        self.status.setText(msg)
        self.append_log("===== " + msg + " =====")
        self.save_settings()
        self.filter_queue()
        self.gallery_scanned_once = False
        if self.tabs.currentIndex() == 1:
            self.refresh_gallery()

    def set_running(self, running: bool):
        for widget in self.queue_mod_controls:
            widget.setEnabled(not running)
        for widget in (self.link_input, self.dest_input, self.media_box, self.browser_box,
                       self.group_check, self.meta_check, self.slow_check, self.proxy_input,
                       self.limit_box, self.rate_box, self.abort_box, self.expected_box, self.limit_clear_btn):
            widget.setEnabled(not running)
        self.start_btn.setEnabled(not running)
        self.retry_btn.setEnabled(not running)
        self.skip_btn.setEnabled(running)
        self.stop_btn.setEnabled(running)

    def skip_current(self):
        if self.worker and self.worker.isRunning():
            self.worker.skip_current()
            self.status.setText("در حال ردکردن بورد فعلی و رفتن به مورد بعدی...")

    def stop_all(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop_all()
            self.stop_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
            self.status.setText("در حال توقف امن فرایند دانلود...")

    def append_log(self, message: str):
        if not message:
            return
        # Avoid exposing a proxy password in saved or displayed logs.
        message = redact_secrets(message, self.proxy_input.text().strip())
        self.logs.appendPlainText(message)
        scrollbar = self.logs.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def export_logs(self):
        filename, _ = QFileDialog.getSaveFileName(self, "گزارش", str(default_output_directory() / "pinterest-log.txt"), "Text (*.txt)")
        if filename:
            try:
                Path(filename).write_text(self.logs.toPlainText(), encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "خطای ذخیره گزارش", str(exc))

    # --- Media library controls ---
    def on_tab_changed(self, index: int):
        if index == 1 and not self.gallery_scanned_once:
            try:
                self.current_destination()
            except (ValueError, OSError):
                return
            self.refresh_gallery()

    def refresh_gallery(self):
        try:
            root = self.current_destination(create=False)
        except (ValueError, OSError) as exc:
            self.gallery_total.setText(f"پوشه قابل بررسی نیست: {exc}")
            return
        if self.scan_worker and self.scan_worker.isRunning():
            self._pending_scan = True
            self.gallery_total.setText("پوشه تغییر کرده؛ پس از پایان بررسی قبلی دوباره بررسی می‌شود...")
            return
        self._pending_scan = False
        self._gallery_scan_path = root
        self.gallery_total.setText("در حال فهرست‌کردن رسانه‌ها...")
        job = ScanWorker(root)
        self.scan_worker = job
        job.ready.connect(lambda files, error, source=root: self.on_gallery_scanned(source, files, error))
        job.finished.connect(lambda completed=job: self.on_scan_finished(completed))
        job.start()

    def on_scan_finished(self, job: ScanWorker):
        if self.scan_worker is job:
            self.scan_worker = None
        job.deleteLater()
        if self._pending_scan and not self._close_requested:
            self.refresh_gallery()
        if self._close_requested:
            self._finish_close_when_idle()

    def on_gallery_scanned(self, source: Path, files: list[Path], error: str):
        try:
            current = self.current_destination(create=False)
        except (ValueError, OSError):
            return
        if source != current or self._pending_scan:
            return  # never show a stale result from a previously selected folder
        if error:
            self.gallery_total.setText("خطای بررسی پوشه: " + error)
            return
        self.all_files = files
        self.gallery_scanned_once = True
        self.filter_gallery()

    def filter_gallery(self, *_):
        query = self.gallery_search.text().strip().casefold()
        kind = self.gallery_mode.currentData()
        self.gallery_filtered = [p for p in self.all_files
                                 if (kind == "all" or media_kind(p) == kind)
                                 and (not query or query in str(p).casefold())]
        if hasattr(self, "_gallery_search_timer"):
            self._gallery_search_timer.stop()
        sort = self.gallery_sort.currentData()
        if sort in ("name", "name_desc"):
            self.gallery_filtered.sort(key=lambda p: (p.name.casefold(), str(p).casefold()), reverse=sort == "name_desc")
        self._thumb_generation += 1
        self._thumb_pending.clear()
        for previous in self._preview_workers:
            previous.requestInterruption()
        self._preview_generation += 1
        self._pending_preview_path = None
        self._preview_timer.stop()
        if self._thumb_worker and self._thumb_worker.isRunning():
            self._thumb_worker.requestInterruption()
        self._thumb_items.clear()
        self.gallery.clear()
        self.gallery_loaded = 0
        self._preview_path = ""
        self.preview_art.setPixmap(QPixmap())
        self.preview_art.setText("یک فایل را انتخاب کنید")
        self.preview_name.setText("—")
        self.preview_details.setText("")
        for btn in self.gallery_preview_buttons:
            btn.setEnabled(False)
        self.gallery_total.setText(f"{len(self.gallery_filtered):,} مورد مطابق فیلتر | مجموع پوشه: {len(self.all_files):,} فایل")
        self.load_more_gallery()

    def thumb_icon(self, path: Path) -> QIcon:
        size = QSize(158, 118)
        canvas = QPixmap(size)
        canvas.fill(QColor("#1B2B3E" if media_kind(path) == "image" else "#193A45"))
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#74D9D1"), 2))
        if media_kind(path) == "video":
            painter.setBrush(QColor("#74D9D1"))
            painter.drawPolygon(QPolygon([QPoint(67, 42), QPoint(67, 82), QPoint(102, 62)]))
        else:
            painter.drawRoundedRect(57, 39, 44, 37, 5, 5)
            painter.drawLine(61, 70, 75, 55)
            painter.drawLine(75, 55, 84, 63)
        painter.end()
        return QIcon(canvas)

    def load_more_gallery(self):
        batch = self.gallery_filtered[self.gallery_loaded:self.gallery_loaded + 55]
        for path in batch:
            item = QListWidgetItem(self.thumb_icon(path), path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.gallery.addItem(item)
            self._thumb_items[str(path)] = item
            if media_kind(path) == "image":
                key = self._thumbnail_cache_key(path)
                cached = self._thumb_cache.get(key)
                if cached is None:
                    self._thumb_pending.append(path)
                else:
                    self._thumb_cache.move_to_end(key)
                    self.on_thumbnail_ready(str(path), cached, self._thumb_generation)
        self.gallery_loaded += len(batch)
        self.gallery_more.setEnabled(self.gallery_loaded < len(self.gallery_filtered))
        self.gallery_more.setText(f"نمایش بیشتر ({self.gallery_loaded:,} از {len(self.gallery_filtered):,})")
        self.launch_thumbnails()

    @staticmethod
    def _thumbnail_cache_key(path: Path) -> str:
        try:
            stat = path.stat()
            return f"{path}|{stat.st_mtime_ns}|{stat.st_size}"
        except OSError:
            return str(path)

    def launch_thumbnails(self):
        if self._thumb_worker is not None or not self._thumb_pending:
            return
        batch = []
        while self._thumb_pending and len(batch) < 30:
            batch.append(self._thumb_pending.popleft())
        job = ImageBatchWorker(batch, self._thumb_generation)
        self._thumb_worker = job
        job.ready.connect(self.on_thumbnail_ready)
        job.finished.connect(lambda j=job: self.on_thumbnails_finished(j))
        job.start()

    def on_thumbnail_ready(self, path: str, image, generation: int):
        if generation != self._thumb_generation:
            return
        item = self._thumb_items.get(path)
        if item is None:
            return
        if not image.isNull():
            key = self._thumbnail_cache_key(Path(path))
            self._thumb_cache[key] = image
            self._thumb_cache.move_to_end(key)
            while len(self._thumb_cache) > 220:
                self._thumb_cache.popitem(last=False)
        canvas = QPixmap(QSize(158, 118))
        canvas.fill(QColor("#182639"))
        pixmap = QPixmap.fromImage(image)
        painter = QPainter(canvas)
        painter.drawPixmap((158 - pixmap.width()) // 2, (118 - pixmap.height()) // 2, pixmap)
        painter.end()
        item.setIcon(QIcon(canvas))

    def on_thumbnails_finished(self, job: ImageBatchWorker):
        if self._thumb_worker is job:
            self._thumb_worker = None
        job.deleteLater()
        if not self._close_requested:
            self.launch_thumbnails()
        else:
            self._finish_close_when_idle()

    def on_gallery_scroll(self, value: int):
        bar = self.gallery.verticalScrollBar()
        if bar.maximum() > 0 and value >= bar.maximum() - 110 and self.gallery_more.isEnabled():
            # Queue to the event loop instead of recursively adding items during a scrollbar event.
            self.gallery_more.setEnabled(False)
            QTimer.singleShot(0, self.load_more_gallery)

    def selected_path(self) -> Path | None:
        item = self.gallery.currentItem()
        if not item:
            return None
        return Path(item.data(Qt.ItemDataRole.UserRole))

    def show_preview(self, current, previous):
        path = self.selected_path()
        if not path:
            self._preview_timer.stop()
            self._pending_preview_path = None
            self._preview_generation += 1
            self._preview_path = ""
            for job in self._preview_workers:
                job.requestInterruption()
            for job in self.video_workers:
                job.cancel()
            self.preview_art.setPixmap(QPixmap())
            self.preview_art.setText("یک فایل را انتخاب کنید")
            self.preview_name.setText("—")
            self.preview_details.setText("")
            for btn in self.gallery_preview_buttons:
                btn.setEnabled(False)
            return
        self._preview_path = str(path)
        for old in self.video_workers:
            old.cancel()
        try:
            size = format_size(path.stat().st_size)
        except OSError:
            size = "اندازه نامشخص"
        kind = media_kind(path)
        self.preview_name.setText(path.name)
        display_kind = ("Video" if kind == "video" else "Image") if language() == "en" else ("ویدیو" if kind == "video" else "تصویر")
        self.preview_details.setText(f"{display_kind} | {size} | {path.suffix.lower()}")
        for b in self.gallery_preview_buttons:
            b.setEnabled(True)
        self.preview_art.setPixmap(QPixmap())
        self.preview_art.setText("در حال ساخت پیش‌نمایش ویدیو ..." if kind == "video" else "پیش‌نمایش تصویر")
        self._preview_timer.stop()
        if kind == "image":
            self._preview_generation += 1
            self._pending_preview_path = path
            self.preview_art.setText("در حال آماده‌سازی تصویر...")
            self._preview_timer.start()
        elif kind == "video":
            self._pending_preview_path = None
            self.preview_video_frame(path)

    def _start_image_preview(self):
        path = self._pending_preview_path
        if not path or self._close_requested or str(path) != self._preview_path:
            return
        for job in self._preview_workers:
            job.requestInterruption()
        job = ImagePreviewWorker(path, self._preview_generation)
        self._preview_workers.append(job)
        job.ready.connect(self.on_image_preview_ready)
        job.finished.connect(lambda j=job: self.on_image_preview_finished(j))
        job.start()

    def on_image_preview_ready(self, path: str, generation: int, image: QImage, size: QSize):
        if path != self._preview_path or generation != self._preview_generation:
            return
        if size.isValid():
            self.preview_details.setText(self.preview_details.text() + f" | {size.width()}×{size.height()}")
        if image.isNull():
            self.preview_art.setText("این تصویر قابل پیش‌نمایش نیست؛ فایل را باز کنید.")
        else:
            self.set_preview_pixmap(QPixmap.fromImage(image))

    def on_image_preview_finished(self, job):
        if job in self._preview_workers:
            self._preview_workers.remove(job)
        job.deleteLater()
        if self._close_requested:
            self._finish_close_when_idle()

    def set_preview_pixmap(self, pixmap: QPixmap):
        if not pixmap.isNull():
            self.preview_art.setPixmap(pixmap.scaled(QSize(365, 365),
                                       Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation))

    def preview_video_frame(self, path: Path):
        # Extract one representative frame with the locally installed ffmpeg.
        # This work is off the UI thread and never plays or uploads the video.
        for old in self.video_workers:
            old.cancel()
        job = VideoThumbnailWorker(path)
        self.video_workers.append(job)
        job.ready.connect(self.video_frame_ready)
        job.finished.connect(lambda j=job: self.finish_video_worker(j))
        job.start()

    def finish_video_worker(self, job: VideoThumbnailWorker):
        if job in self.video_workers:
            self.video_workers.remove(job)
        job.deleteLater()
        shown = self.preview_art.pixmap()
        if self._preview_path == str(job.path) and (shown is None or shown.isNull()):
            self.preview_art.setText("برای پخش ویدیو، «بازکردن فایل» را بزنید.")
        if self._close_requested:
            self._finish_close_when_idle()

    def video_frame_ready(self, path: str, data: bytes):
        if path != self._preview_path:
            return
        pic = QPixmap()
        if pic.loadFromData(data):
            self.set_preview_pixmap(pic)

    def open_selected_file(self):
        p = self.selected_path()
        if p and p.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def open_selected_parent(self):
        p = self.selected_path()
        if p and p.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.parent)))

    def copy_selected_path(self):
        p = self.selected_path()
        if p:
            QApplication.clipboard().setText(str(p))

    def export_csv(self):
        try:
            root = self.current_destination()
        except ValueError as exc:
            QMessageBox.warning(self, "پوشه نامعتبر", str(exc))
            return
        name, _ = QFileDialog.getSaveFileName(self, "خروجی CSV", str(root / "media-manifest.csv"), "CSV (*.csv)")
        if not name:
            return
        try:
            count = export_manifest_csv(root, Path(name), self.gallery_filtered)
            QMessageBox.information(self, "خروجی فهرست", f"فهرست {count:,} فایل مطابق فیلتر جاری ذخیره شد.")
        except OSError as exc:
            QMessageBox.warning(self, "خطای خروجی", str(exc))

    def show_engine_status(self):
        versions = get_tools_status()
        self.engine_info.setText("  |  ".join(f"{name}: {version}" for name, version in versions.items()))

    def copy_diagnostics(self):
        # Never place proxy/cookie/token/path/board URLs into diagnostic clipboard text.
        import platform
        versions = get_tools_status()
        report = [f"PinHarbor {APP_VERSION}",
                  f"OS: {platform.system()} {platform.release()}",
                  f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                  f"Packaged: {bool(getattr(sys, 'frozen', False))}",
                  *[f"{key}: {value}" for key, value in versions.items()]]
        QApplication.clipboard().setText("\n".join(report))
        self.status.setText("گزارش فنی بدون مشخصات حساب و مسیرهای شخصی کپی شد.")

    def _has_running_background_work(self):
        return bool((self.worker and self.worker.isRunning()) or
                    (self.scan_worker and self.scan_worker.isRunning()) or
                    (self._thumb_worker and self._thumb_worker.isRunning()) or
                    any(w.isRunning() for w in self.video_workers) or
                    any(w.isRunning() for w in self._preview_workers))

    def _finish_close_when_idle(self):
        if not self._close_requested:
            return
        if self._has_running_background_work():
            QTimer.singleShot(180, self._finish_close_when_idle)
        else:
            self.close()

    def closeEvent(self, event):
        if self._has_running_background_work():
            if self.worker and self.worker.isRunning() and not self._close_requested:
                answer = QMessageBox.question(
                    self, "دانلود فعال است", "دانلود متوقف شود و برنامه بسته شود؟",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
            self._close_requested = True
            if self.worker:
                self.worker.stop_all()
            if self._thumb_worker:
                self._thumb_worker.requestInterruption()
            for job in self.video_workers:
                job.cancel()
            for job in self._preview_workers:
                job.requestInterruption()
            self._preview_timer.stop()
            self.status.setText("در حال پایان‌دادن امن به پردازش‌ها و بستن برنامه...")
            self._finish_close_when_idle()
            event.ignore()
            return
        self._checkpoint_timer.stop()
        self._elapsed_timer.stop()
        self.save_settings()
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.sync()
        event.accept()


def app_main():
    app = QApplication(sys.argv)
    saved_language = str(QSettings("PinterestBoardStudio", "Desktop").value("language", "fa"))
    set_language(saved_language)
    app.setApplicationName("PinHarbor")
    app.setApplicationVersion(APP_VERSION)
    app.setLayoutDirection(Qt.LayoutDirection.LeftToRight if language() == "en" else Qt.LayoutDirection.RightToLeft)
    preference = str(QSettings("PinterestBoardStudio", "Desktop").value("ui_font", "auto"))
    installed = QFontDatabase.families()
    if language() == "en" and preference == "auto":
        family = next((f for f in ("Segoe UI", "Inter", "Arial") if f in installed), choose_font(installed))
    else:
        family = choose_font(installed, preference)
    app.setFont(QFont(family, 10))
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE_SHEET)
    icon_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon_file = icon_root / "app_icon.png"
    if icon_file.is_file():
        app.setWindowIcon(QIcon(str(icon_file)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def main():
    # When packaged with PyInstaller, subprocesses run the same executable
    # in engine mode; there is no dependency on a system-installed Python.
    if len(sys.argv) >= 2 and sys.argv[1] == "--engine":
        from gallery_dl import main as gallery_main
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        raise SystemExit(gallery_main())
    app_main()


if __name__ == "__main__":
    main()
