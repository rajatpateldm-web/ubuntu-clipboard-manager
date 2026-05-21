"""
services/clipboard_service.py
------------------------------
Performance-optimized three-tier clipboard monitoring.
Spawns subprocesses off the main thread to prevent GUI lag and dock flickering.

THE PROBLEM:
~~~~~~~~~~~~
On Wayland/Ubuntu, standard Qt clipboard signals do not work when the window
is unfocused. Previously, calling `wl-paste` via `subprocess.run` every 300ms
on the main GUI thread caused periodic blocking, CPU overhead, and dock/taskbar
flickering due to repeated process spawning on the GUI thread.

THE SOLUTION:
~~~~~~~~~~~~─
1. **Off-Thread Worker (QThread)**: All subprocess clipboard reads (`wl-paste` or `xclip`)
   are offloaded to a background thread. The GUI thread remains 100% free and responsive.
2. **Focus-Aware Polling Control**: If the ClipVault window is active/focused, the background
   worker thread is **completely paused**. We use standard Qt `QClipboard.text()` which is
   instant and uses 0% CPU. The background thread is only active when ClipVault is unfocused.
3. **Copy-Back Feedback Protection**: We use a `_ignore_next` flag to prevent clipboard
   re-entry loops when copying items from the history list back into the system clipboard.
4. **History Cap**: Capped at 100 items with automatic trimming.
"""

import logging
import os
import shutil
import subprocess
import time
import uuid

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

log = logging.getLogger("ClipVault.clipboard")

MAX_HISTORY = 100


def _detect_session_type() -> str:
    """Detect 'wayland' or 'x11' from the environment."""
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    return "wayland" if "wayland" in session else "x11"


def _find_clipboard_command() -> list[str] | None:
    """Find the best available clipboard CLI tool."""
    # Prioritize xclip and xsel on GNOME Wayland because wl-paste creates a
    # transparent surface that causes the GNOME dock (Dash to Dock) to flicker.
    # xclip/xsel run over XWayland and do not cause dock flickering.
    if shutil.which("xclip"):
        return ["xclip", "-selection", "clipboard", "-o"]
    if shutil.which("xsel"):
        return ["xsel", "--clipboard", "--output"]
    if shutil.which("wl-paste"):
        return ["wl-paste", "--no-newline"]
    return None


class ClipboardWorker(QThread):
    """
    Background worker thread to perform safe, off-thread subprocess monitoring.
    Prevents the main thread from blocking or lagging.
    """
    text_detected = pyqtSignal(str)

    def __init__(self, cmd: list[str], interval_ms: int, use_watch_mode: bool, parent=None):
        super().__init__(parent)
        self.cmd = cmd
        self.interval_ms = interval_ms
        self.use_watch_mode = use_watch_mode
        self._running = True
        self._enabled = use_watch_mode  # Always enabled initially in watch mode
        self._last_text = ""
        self._proc = None

    def set_enabled(self, enabled: bool):
        """Enable or disable the background subprocess polling loop."""
        if self.use_watch_mode:
            # Watch mode is persistent and lightweight; we keep it enabled
            # throughout the app lifecycle to avoid process spawn overhead on focus toggle.
            self._enabled = True
        else:
            self._enabled = enabled

    def run(self):
        # Copy and clean the environment to prevent GNOME from showing startup/launch
        # feedback (flickering dock icon) for our background CLI polling/watch subprocesses.
        clean_env = os.environ.copy()
        clean_env.pop("DESKTOP_STARTUP_ID", None)
        clean_env.pop("XDG_ACTIVATION_TOKEN", None)

        while self._running:
            if self.use_watch_mode:
                # ── Wayland Watch Mode ────────────────────────────────
                try:
                    self._proc = subprocess.Popen(
                        ["wl-paste", "-t", "text", "--watch", "sh", "-c", 'cat; printf "\\0"'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        errors="replace",
                        env=clean_env,
                        bufsize=1
                    )
                    # Verify if it starts successfully or crashes immediately
                    time.sleep(0.2)
                    if self._proc.poll() is not None:
                        stderr_msg = self._proc.stderr.read()
                        log.warning(f"wl-paste watch mode unsupported: {stderr_msg.strip()}")
                        self.use_watch_mode = False
                        self._enabled = False
                        continue
                except Exception as e:
                    log.warning(f"Failed to start wl-paste watch: {e}")
                    self.use_watch_mode = False
                    self._enabled = False
                    continue

                accumulated = ""
                try:
                    while self._running:
                        # Read in blocks to be efficient and handle large clipboards
                        chunk = self._proc.stdout.read(4096)
                        if not chunk:
                            break  # Process exited or EOF
                        accumulated += chunk
                        while "\0" in accumulated:
                            text, accumulated = accumulated.split("\0", 1)
                            # Emit the detected text
                            if text:
                                self.text_detected.emit(text)
                except Exception:
                    pass
                finally:
                    try:
                        self._proc.terminate()
                        self._proc.wait(timeout=1)
                    except Exception:
                        pass

                if self._running:
                    time.sleep(1)  # Throttle restarts
            else:
                # ── Standard Polling Fallback ─────────────────────────────
                if self._enabled and self.cmd:
                    try:
                        result = subprocess.run(
                            self.cmd,
                            capture_output=True,
                            text=True,
                            errors="replace",
                            env=clean_env,
                            timeout=0.4  # Ultra-short timeout
                        )
                        if result.returncode == 0:
                            text = result.stdout
                            if text and text != self._last_text:
                                self._last_text = text
                                self.text_detected.emit(text)
                    except Exception:
                        pass
                time.sleep(self.interval_ms / 1000.0)

    def stop(self):
        self._running = False
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
        self.wait()


class ClipboardService(QObject):
    """
    Performance-optimized three-tier clipboard service with off-thread worker.
    Tracks clipboard history using unique IDs to ensure precise UI deletion sync.
    """
    # Emits (item_id, text)
    new_item = pyqtSignal(str, str)
    # Emits item_id of the trimmed item
    item_trimmed = pyqtSignal(str)

    POLL_INTERVAL_MS = 500  # Highly optimized check rate

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── State ─────────────────────────────────────────────────────
        # Holds list of dicts: [{"id": str, "text": str}]
        self.history: list[dict] = []
        self._last_text: str = ""
        self._ignore_next: bool = False
        self._ignore_text: str | None = None

        # ── Session & Tool detection ──────────────────────────────────
        self._session_type = _detect_session_type()
        self._clip_cmd = _find_clipboard_command()
        self._use_watch_mode = (
            self._session_type == "wayland"
            and self._clip_cmd
            and "wl-paste" in self._clip_cmd[0]
        )

        # ── Tier 1: QClipboard Signal ─────────────────────────────────
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_qt_signal)

        # ── Tier 2: Dedicated Polling/Watch Thread ────────────────────
        self._worker = ClipboardWorker(
            self._clip_cmd,
            self.POLL_INTERVAL_MS,
            self._use_watch_mode,
            self
        )
        self._worker.text_detected.connect(self._process_text)
        self._worker.start()

        # ── Tier 3: Qt Polling Fallback (Only active when CLI tools missing) ──
        self._qt_timer = QTimer(self)
        self._qt_timer.setInterval(self.POLL_INTERVAL_MS)
        self._qt_timer.timeout.connect(self._on_qt_poll_tick)

        # ── Smart Focus Monitoring Timer ──────────────────────────────
        self._focus_timer = QTimer(self)
        self._focus_timer.setInterval(1000)
        self._focus_timer.timeout.connect(self._check_focus_state)
        self._focus_timer.start()

        # Initial check
        self._check_focus_state()

    def start(self):
        """Start standard timers/threads."""
        if not self._clip_cmd:
            self._qt_timer.start()

    def stop(self):
        """Clean shutdown to avoid dangling threads or memory leaks."""
        self._focus_timer.stop()
        self._qt_timer.stop()
        self._worker.stop()
        try:
            self._clipboard.dataChanged.disconnect(self._on_qt_signal)
        except RuntimeError:
            pass

    def remove_item(self, item_id: str):
        """Remove item from history using its unique ID."""
        self.history = [item for item in self.history if item["id"] != item_id]

    def clear_ignore_text(self):
        """Clear the ignore filter state."""
        self._ignore_next = False
        self._ignore_text = None

    def set_ignore_next(self, text: str = ""):
        """Ignore next clipboard update (used for copy-back operation)."""
        self._ignore_next = True
        self._ignore_text = text
        QTimer.singleShot(500, self.clear_ignore_text)

    def _check_focus_state(self):
        """
        Dynamically toggle off-thread polling based on active window focus.
        If active, disable thread. If inactive, enable thread.
        """
        is_focused = QApplication.activeWindow() is not None
        if is_focused:
            self._worker.set_enabled(False)
        else:
            self._worker.set_enabled(True)

    def _on_qt_signal(self):
        """Tier 1 callback: Instant when focused."""
        # Under Wayland/Ubuntu, calling QClipboard.text() while unfocused blocks
        # the main GUI thread, causing typing lag and taskbar flickering.
        is_focused = QApplication.activeWindow() is not None
        if not is_focused:
            return

        if self._ignore_next or (self._ignore_text and self._clipboard.text() == self._ignore_text):
            return
        self._process_text(self._clipboard.text())

    def _on_qt_poll_tick(self):
        """Tier 3 callback: Standard Qt polling fallback."""
        if not self._clip_cmd:
            is_focused = QApplication.activeWindow() is not None
            if is_focused:
                self._process_text(self._clipboard.text())

    def _process_text(self, text: str):
        """Central deduplication gate."""
        if not text or not text.strip():
            return

        if text == self._last_text:
            return

        if self._ignore_next or (self._ignore_text and text == self._ignore_text):
            return

        self._last_text = text
        # Synchronize back to the worker thread to prevent duplicate events on focus shift
        if hasattr(self, "_worker"):
            self._worker._last_text = text

        item_id = uuid.uuid4().hex
        self.history.insert(0, {"id": item_id, "text": text})
        self.new_item.emit(item_id, text)

        # Enforce history limit
        self._trim_history()

    def _trim_history(self):
        """Silently discard old items and notify UI."""
        while len(self.history) > MAX_HISTORY:
            removed = self.history.pop()
            self.item_trimmed.emit(removed["id"])

