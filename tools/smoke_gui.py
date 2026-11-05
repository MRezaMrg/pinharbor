"""Offline Windows CI smoke test for both GUI languages and core controls.

No network, browser credentials or Pinterest requests are used. Runs with
QT_QPA_PLATFORM=offscreen on CI. Actual visible desktop QA is still required.
"""
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import QApplication
    from pinterest_studio import MainWindow
    from ui_language import set_language

    with tempfile.TemporaryDirectory(prefix='pinharbor-qt-') as tmp:
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tmp)
        app = QApplication([])
        for lang, first_tab in (('fa', 'صف دانلود'), ('en', 'Downloads')):
            set_language(lang)
            app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang == 'fa' else Qt.LayoutDirection.LeftToRight)
            settings = QSettings('PinterestBoardStudio', 'Desktop')
            settings.setValue('language', lang)
            settings.sync()
            window = MainWindow()
            window.show()
            app.processEvents()
            assert window.tabs.count() == 3, 'Unexpected tab count'
            assert window.tabs.tabText(0) == first_tab, f'Wrong tab translation for {lang}'
            assert window.expected_box.value() == 0, 'New expected count should default to unknown'
            assert window.quick_btn.isEnabled(), 'Start control disabled'
            assert window.worker is None, 'Unexpected download worker'
            assert not window.advanced_network_panel.isVisible(), 'Advanced controls visible by default'
            window.close()
            app.processEvents()
    print('PASS: Persian/English Qt controls, hidden advanced settings and clean shutdown')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
