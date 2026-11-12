"""
main.py
Entry point for ClipVault, the Ubuntu clipboard manager.

Run from the project root (with the venv active):
    python main.py
"""

import sys

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from ui.main_window import MainWindow
from ui.styles import DARK_THEME, LIGHT_THEME

SERVER_NAME = "ClipVaultLocalServer"


def main():
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

    # Load saved theme preference from QSettings
    settings = QSettings("ClipVault", "App")
    saved_theme = settings.value("theme", "dark")
    app.setStyleSheet(LIGHT_THEME if saved_theme == "light" else DARK_THEME)

    # Create the main window
    window = MainWindow()

    # Create the local server for IPC restricted to the current user
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    server.removeServer(SERVER_NAME)  # Clean up any stale sockets from crashes

    if server.listen(SERVER_NAME):
        def handle_new_connection():
            client_socket = server.nextPendingConnection()
            if client_socket.waitForReadyRead(200):
                data = client_socket.readAll().data()
                if b"toggle" in data:
                    window.toggle_window()
            client_socket.disconnectFromServer()

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
