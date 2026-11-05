"""Design tokens & Qt styles for PBS 2.3 — burgundy × rose glass.

No bundled font files: use an installed Persian typeface when available.
The 'glass' surfaces are translucent gradients; they do not invoke a
per-widget backdrop blur, to protect scrolling responsiveness.
"""
from __future__ import annotations

PALETTE = {
    "ink": "#0E090F",
    "black": "#120A11",
    "burgundy": "#721F43",
    "burgundy_deep": "#3B1028",
    "rose": "#F0B6CB",
    "rose_hover": "#FFCBDE",
    "rose_muted": "#DDA5B9",
    "text": "#FFF2F7",
    "muted": "#D0B4C1",
    "border": "#694052",
    "success": "#ABE6C9",
    "error": "#FFABB3",
}

# In priority order: installed fonts only. Vazirmatn is opt-in via an external install.
FONT_PREFERENCE = (
    "Vazirmatn", "Vazirmatn FD", "Estedad", "IRANSansX", "Yekan Bakh FaNum",
    "Noto Sans Arabic UI", "Noto Sans Arabic", "Tahoma", "Segoe UI", "Arial",
)


def choose_font(available: list[str] | tuple[str, ...], selected: str = "auto") -> str:
    """Return a font that actually exists; never silently select a missing font."""
    present = {family.casefold(): family for family in available}
    if selected != "auto" and selected.casefold() in present:
        return present[selected.casefold()]
    for family in FONT_PREFERENCE:
        if family.casefold() in present:
            return present[family.casefold()]
    return available[0] if available else "Tahoma"


def available_fonts(available: list[str] | tuple[str, ...]) -> list[str]:
    present = {f.casefold(): f for f in available}
    return [present[f.casefold()] for f in FONT_PREFERENCE if f.casefold() in present]


# QColor with alpha in Qt stylesheets is rgba(r,g,b,a) where a is 0..255.
# Translucency + a painted ambient canvas create the frosted-glass effect.
STYLE_SHEET = """
QWidget {
    color: #FFF2F7;
    font-size: 13px;
}
QMainWindow, QDialog, QMessageBox { background: #0E090F; }
QWidget#ambientCanvas, QWidget#glassPage, QWidget#scrollBody,
QWidget#qt_scrollarea_viewport { background: transparent; }
QScrollArea { background: transparent; border: 0; }
QScrollArea > QWidget > QWidget { background: transparent; }

QFrame#hero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(142, 45, 84, 140), stop:0.48 rgba(72, 29, 52, 135),
        stop:1 rgba(39, 21, 37, 185));
    border: 1px solid rgba(253, 199, 221, 80);
    border-radius: 20px;
}
QFrame#panel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(72, 35, 58, 176), stop:0.52 rgba(44, 25, 42, 185),
        stop:1 rgba(26, 16, 29, 204));
    border: 1px solid rgba(243, 181, 209, 51);
    border-radius: 17px;
}
QFrame#stat {
    background: qlineargradient(x1:0, y1:0, x2:0.9, y2:1,
        stop:0 rgba(133, 55, 86, 135), stop:0.45 rgba(63, 30, 51, 170),
        stop:1 rgba(36, 23, 35, 190));
    border: 1px solid rgba(245, 179, 208, 54);
    border-radius: 14px;
}
QFrame#statusStrip {
    background: rgba(47, 27, 42, 185);
    border: 1px solid rgba(235, 175, 200, 45);
    border-radius: 11px;
}
QLabel { background: transparent; }
QLabel#monogram {
    color: #FFE5EE;
    font-size: 25px;
    font-weight: 800;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
      stop:0 #9F426C, stop:1 #581A3C);
    border: 1px solid rgba(255, 213, 231, 106);
    border-radius: 13px;
}
QLabel#eyebrow { color: #F6BDD1; font-size: 10px; font-weight: 700; }
QLabel#versionChip {
    color: #FFD9E7;
    background: rgba(255, 220, 234, 24);
    border: 1px solid rgba(254, 198, 222, 82);
    border-radius: 11px;
    padding: 7px 12px;
    font-size: 11px;
}
QLabel#title { color: #FFF4F8; font-size: 22px; font-weight: 750; }
QLabel#subtitle, QLabel#muted { color: #D0B4C1; }
QLabel#heading { color: #FFEAF2; font-size: 15px; font-weight: 700; }
QLabel#number { color: #FFD0E1; font-size: 23px; font-weight: 750; }
QLabel#label { color: #D8B9C7; font-size: 12px; }
QLabel#notice { color: #FFD0E2; font-size: 13px; }
QLabel#empty {
    background: rgba(89, 43, 65, 100);
    color: #E0BECF; border: 1px dashed rgba(234, 178, 202, 80);
    border-radius: 10px; padding: 17px; font-size: 13px;
}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QTableWidget, QListWidget {
    background: rgba(18, 10, 21, 204);
    color: #FFF2F7;
    border: 1px solid rgba(220, 155, 183, 75);
    border-radius: 10px;
    padding: 8px 11px;
    selection-background-color: #8C3B61;
    selection-color: #FFFFFF;
}
QLineEdit:hover, QPlainTextEdit:hover, QComboBox:hover,
QSpinBox:hover { border-color: rgba(246, 176, 207, 126); }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus { border: 1px solid #EFAEC8; }
QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled,
QSpinBox:disabled { color: #957C8B; background: rgba(24, 16, 26, 145); }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView {
    background: #261624;
    color: #FFF2F7;
    selection-background-color: #7A3456;
    border: 1px solid #65394E;
}
QTableWidget, QListWidget { alternate-background-color: rgba(58, 29, 48, 110); }
QTableWidget::item { padding: 8px 7px; }
QTableWidget::item:selected, QListWidget::item:selected {
    background: #71344F; color: #FFFFFF;
}
QHeaderView::section {
    background: rgba(103, 44, 69, 210);
    color: #FCE0EC; border: none;
    border-bottom: 1px solid rgba(250, 185, 209, 70);
    padding: 10px 8px; font-weight: 700;
}
QPushButton {
    color: #FBE6EF;
    background: rgba(106, 52, 77, 155);
    border: 1px solid rgba(242, 175, 204, 65);
    border-radius: 10px; padding: 10px 14px;
    font-weight: 650;
    min-height: 16px;
}
QPushButton:hover {
    background: rgba(132, 65, 97, 205);
    border-color: rgba(255, 201, 223, 145);
}
QPushButton:pressed { background: rgba(86, 37, 65, 230); }
QPushButton:focus { border: 2px solid #FFC4DA; }
QPushButton:disabled {
    color: #9A8290; background: rgba(50, 34, 47, 120);
    border-color: rgba(182, 137, 161, 35);
}
QPushButton#primary {
    color: #2B1022;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #FFD5E4, stop:0.5 #F3B5CD, stop:1 #E9A0BC);
    border: 1px solid #FFD8E7;
    font-weight: 800;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #FFE3ED, stop:1 #F4B9D0);
}
QPushButton#primary:pressed { background: #E59AB7; }
QPushButton#primary:disabled { color: #876A77; background: #8F7582; border-color: #A58B99; }
QPushButton#quiet { background: rgba(43, 24, 39, 80); }
QPushButton#quiet:hover { background: rgba(111, 46, 76, 165); }
QPushButton#expand {
    background: rgba(79, 35, 57, 118);
    border: 1px solid rgba(235, 170, 200, 60);
    color: #EAD0DC; text-align: right;
    padding: 11px 15px;
}
QPushButton#expand:hover { background: rgba(114, 47, 78, 170); }
QPushButton#danger {
    background: rgba(109, 39, 51, 145);
    border-color: rgba(255, 162, 175, 93);
    color: #FFD7DC;
}
QPushButton#danger:hover { background: rgba(147, 49, 69, 190); }
QTabWidget::pane { border: none; margin-top: 8px; background: transparent; }
QTabBar { background: transparent; }
QTabBar::tab {
    color: #D0B3C0;
    background: rgba(81, 43, 63, 122);
    border: 1px solid rgba(222, 160, 184, 46);
    border-bottom: 2px solid rgba(0, 0, 0, 0);
    padding: 12px 19px; min-width: 110px;
    font-weight: 700;
}
QTabBar::tab:first { border-top-right-radius: 11px; border-bottom-right-radius: 11px; }
QTabBar::tab:last { border-top-left-radius: 11px; border-bottom-left-radius: 11px; }
QTabBar::tab:selected {
    background: rgba(136, 60, 91, 195);
    color: #FFE1EC;
    border-color: rgba(255, 204, 222, 95);
    border-bottom: 2px solid #F4B5CD;
}
QTabBar::tab:hover { color: #FFF6FA; background: rgba(112, 53, 79, 187); }
QCheckBox { color: #EBD6E0; spacing: 9px; }
QCheckBox::indicator {
    width: 18px; height: 18px; background: #2C1A2B;
    border: 1px solid #9B6B82; border-radius: 5px;
}
QCheckBox::indicator:checked { background: #F0B6CB; border-color: #FFDAE8; }
QCheckBox::indicator:hover { border-color: #FFD1E2; }
QProgressBar {
    height: 9px; background: rgba(30, 17, 28, 218);
    border: 1px solid rgba(238, 182, 205, 60);
    border-radius: 5px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #9B416A, stop:1 #F2B4CC);
    border-radius: 4px;
}
QSplitter::handle { background: rgba(244, 181, 206, 75); width: 2px; }
QScrollBar:vertical { background: rgba(30, 17, 30, 170); width: 10px; }
QScrollBar::handle:vertical {
    background: #77506A; border-radius: 4px; min-height: 26px;
}
QScrollBar::handle:vertical:hover { background: #B87894; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #221521; height: 9px; }
QScrollBar::handle:horizontal { background: #77506A; border-radius: 4px; min-width: 28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QToolTip {
    background: #44263A; color: #FFF1F8;
    border: 1px solid #9B6079; padding: 7px;
}
QMessageBox QLabel { color: #FFE9F2; }
"""
