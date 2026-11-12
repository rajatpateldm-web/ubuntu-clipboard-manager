"""
main.py
Entry point for ClipVault, the Ubuntu clipboard manager.

Run from the project root (with the venv active):
    python main.py
"""

import logging
import sys

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from ui.main_window import MainWindow
from ui.styles import (
    DEFAULT_COLOR_SCHEME,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_STYLE,
    build_stylesheet,
    clamp_font_size,
    normalize_color_scheme,
    normalize_font_style,
    sanitize_font_family,
)

SERVER_NAME = "ClipVaultLocalServer"
_MAX_IPC_BYTES = 64


def parse_ipc_command(raw_data: bytes) -> str:
    """Decode and bound an incoming IPC command payload."""
    return raw_data[:_MAX_IPC_BYTES].decode("utf-8", errors="ignore").strip()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Check if ClipVault is already running by attempting a local socket connection
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)

    # If connection succeeds, another instance is already running
    if socket.waitForConnected(200):
        # Notify the running instance to toggle/focus the window and exit
        socket.write(b"toggle\n")
        socket.flush()
        socket.disconnectFromServer()
        sys.exit(0)

    # Otherwise, this is the primary instance. Create the Qt application.
    app = QApplication(sys.argv)
    app.setApplicationName("ClipVault")

    # Load saved theme, color scheme, and font preferences from QSettings
    settings = QSettings("ClipVault", "App")
    saved_theme = settings.value("theme", "dark")
    saved_color_scheme = normalize_color_scheme(settings.value("color_scheme", DEFAULT_COLOR_SCHEME))
    saved_font_family = sanitize_font_family(settings.value("font_family", DEFAULT_FONT_FAMILY))
    saved_font_size = clamp_font_size(settings.value("font_size", DEFAULT_FONT_SIZE))
    saved_font_style = normalize_font_style(settings.value("font_style", DEFAULT_FONT_STYLE))
    app.setStyleSheet(
        build_stylesheet(
            saved_theme,
            font_family=saved_font_family,
            font_size=saved_font_size,
            font_style=saved_font_style,
            color_scheme=saved_color_scheme,
        )
    )

    # Create the main window
    window = MainWindow()

    # Create the local server for IPC restricted to the current user
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    server.removeServer(SERVER_NAME)  # Clean up any stale sockets from crashes

    if server.listen(SERVER_NAME):
        def handle_new_connection():
            client_socket = server.nextPendingConnection()
            if client_socket is None:
                return
            if client_socket.waitForReadyRead(200):
                raw_data = client_socket.read(_MAX_IPC_BYTES)
                if parse_ipc_command(raw_data) == "toggle":
                    window.toggle_window()
            client_socket.disconnectFromServer()
            client_socket.close()
            client_socket.deleteLater()

        server.newConnection.connect(handle_new_connection)

    # Show the window on startup
    window.show()

    # Enter the Qt event loop
    exit_code = app.exec()

    # Clean up the server on close
    server.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
