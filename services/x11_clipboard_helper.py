"""
services/x11_clipboard_helper.py
Lightweight persistent X11/XWayland clipboard monitor helper.

Runs under QT_QPA_PLATFORM=xcb without creating any visible window so ClipVault
can capture clipboard updates from other applications on Wayland/X11 even when
the main ClipVault window is unfocused and external CLI tools (xclip/wl-paste)
are not installed.
"""

import json
import logging
import os
import signal
import sys

# Ensure project root is importable when invoked as a script
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from services.sensitive_detector import is_sensitive_mime_data  # noqa: E402

MAX_TEXT_LENGTH = 1_000_000
log = logging.getLogger("ClipVault.x11_helper")


class X11ClipboardWatcher:
    """Monitors QClipboard on X11/XWayland and writes JSON lines to stdout."""

    def __init__(self, app: QApplication, parent_pid: int):
        self._app = app
        self._parent_pid = parent_pid
        self._clipboard = app.clipboard()
        self._last_text = ""

        # Seed initial clipboard without emitting historical pre-launch text
        try:
            if not is_sensitive_mime_data(self._clipboard.mimeData()):
                self._last_text = (self._clipboard.text() or "")[:MAX_TEXT_LENGTH]
        except (RuntimeError, AttributeError) as exc:
            log.debug("Initial clipboard seed skipped: %s", exc)
            self._last_text = ""

        self._clipboard.dataChanged.connect(self._check_clipboard)

        self._timer = QTimer()
        self._timer.setInterval(400)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def _on_tick(self):
        # Exit automatically if the parent ClipVault process has terminated
        if os.getppid() != self._parent_pid:
            self._app.quit()
            return
        self._check_clipboard()

    def _check_clipboard(self):
        try:
            mime_data = self._clipboard.mimeData()
            if is_sensitive_mime_data(mime_data):
                return
            text = self._clipboard.text()
        except (RuntimeError, AttributeError) as exc:
            log.debug("Clipboard read failed in helper: %s", exc)
            return

        if not text:
            return
        text = text[:MAX_TEXT_LENGTH]
        if text == self._last_text:
            return

        self._last_text = text
        try:
            sys.stdout.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except BrokenPipeError:
            self._app.quit()


def main() -> int:
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    signal.signal(signal.SIGTERM, lambda *_args: sys.exit(0))

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    parent_pid = os.getppid()
    _watcher = X11ClipboardWatcher(app, parent_pid)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
