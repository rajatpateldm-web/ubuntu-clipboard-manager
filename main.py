"""
main.py
--------
Entry point for ClipVault — the Ubuntu clipboard manager.

Run from the project root (with the venv active):
    python main.py
"""

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QSizePolicy

from ui.main_window import MainWindow
from ui.styles import DARK_THEME


def main():
    # Create the Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("ClipVault")

    # Apply the global dark stylesheet
    app.setStyleSheet(DARK_THEME)

    # Create and show the main window
    window = MainWindow()
    window.show()

    # Enter the Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
