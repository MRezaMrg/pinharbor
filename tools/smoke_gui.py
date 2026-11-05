"""Basic, offline Qt widget smoke test for GitHub's Windows runner.

No browser launches, credentials, downloads or Pinterest network requests.
"""
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import QApplication
    from pinterest_studio import MainWindow
    with tempfile.TemporaryDirectory(prefix="pinharbor-qt-") as tmp:
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tmp)
        app = QApplication([])
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        window = MainWindow()
        window.show()
        app.processEvents()
        assert window.tabs.count() == 3
        assert window.quick_btn.isEnabled()
        assert window.worker is None
        window.close()
        app.processEvents()
    print("PASS: PySide6 MainWindow, tabs, and clean shutdown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
