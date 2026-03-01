"""VLCShow — multi-display video projection manager.

Entry point.  Run with:
    python main.py
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from vlcshow.ui.main_window import MainWindow
from vlcshow.ui.styles import APP_STYLESHEET


def main() -> None:
    # Smooth fractional-DPI rendering on high-DPI screens
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("VLCShow")
    app.setOrganizationName("VLCShow")
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
