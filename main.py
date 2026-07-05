from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def resource_path(relative: str) -> Path:
    """
    Gibt den richtigen Pfad für normale Starts und PyInstaller/AppImage zurück.

    Normal:
        Audioforge Mp3 Magic 2.0/assets/icon.png

    PyInstaller/AppImage:
        temporärer Bundle-Pfad/assets/icon.png
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative

    return Path(__file__).resolve().parent / relative


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AudioForge")
    app.setApplicationDisplayName("AudioForge MP3 Magic")

    icon_path = resource_path("assets/icon.png")
    icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()

    if not icon.isNull():
        app.setWindowIcon(icon)

    window = MainWindow()

    if not icon.isNull():
        window.setWindowIcon(icon)

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
