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

import json
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid

from services.database_service import DatabaseService
from services.sensitive_detector import (
    is_sensitive_mime_data,
    is_sensitive_targets,
)

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

log = logging.getLogger("ClipVault.clipboard")

MAX_HISTORY = 100
MAX_TEXT_LENGTH = 1_000_000


def sort_history_items(items: list[dict]) -> None:
    """Sort history items in place: pinned first (newest-first), then unpinned."""
    items.sort(
        key=lambda x: (x.get("pinned", False), x.get("timestamp", 0.0)),
        reverse=True,
    )


def _terminate_process(proc: subprocess.Popen | None) -> None:
    """Safely terminate and reap a child subprocess."""
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=1)
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("Subprocess cleanup warning: %s", exc)


def normalize_text(text: str) -> str:
    """
    Normalize clipboard text to guarantee robust multi-line duplicate prevention
    and consistent comparison by standardizing line endings, removing null bytes,
    and stripping leading/trailing whitespace.
    """
    if not text:
        return ""
    # Standardize line endings to standard Unix LF (\n)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove null bytes (often returned by CLI clipboard watchers or tools)
    text = text.replace("\0", "")
    # Guard against unbounded memory consumption by capping massive payloads
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]
    # Strip trailing and leading whitespace/newlines for clean storage & comparison
    return text.strip()



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


def _find_targets_command(clip_cmd: list[str] | None) -> list[str] | None:
    """Find the CLI command to query clipboard targets / MIME types."""
    if not clip_cmd:
        return None
    tool = clip_cmd[0]
    if "xclip" in tool:
        return ["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"]
    if "xsel" in tool:
        return ["xsel", "--clipboard", "-t", "TARGETS"]
    if "wl-paste" in tool:
        return ["wl-paste", "--list-types"]
    return None


def _can_use_x11_helper() -> bool:
    """Return True when the persistent X11/XWayland Python helper can be used."""
    if not os.environ.get("DISPLAY"):
        return False
    if os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
        return False
    helper_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "x11_clipboard_helper.py",
    )
    return os.path.isfile(helper_path)


class ClipboardWorker(QThread):
    """
    Background worker thread to perform safe, off-thread subprocess monitoring.
    Prevents the main thread from blocking or lagging.
    """
    text_detected = pyqtSignal(str)

    def __init__(
        self,
        cmd: list[str] | None,
        interval_ms: int,
        use_watch_mode: bool,
        targets_cmd: list[str] | None = None,
        parent=None,
        use_x11_helper: bool = False,
    ):
        super().__init__(parent)
        self.cmd = cmd
        self.targets_cmd = targets_cmd or _find_targets_command(cmd)
        self.interval_ms = interval_ms
        self.use_watch_mode = use_watch_mode
        self.use_x11_helper = use_x11_helper
        self._running = True
        self._enabled = use_watch_mode or use_x11_helper
        self._last_text = ""
        self._proc = None

    def set_enabled(self, enabled: bool):
        """Enable or disable the background subprocess polling loop."""
        if self.use_watch_mode or self.use_x11_helper:
            # Watch and helper modes are persistent and lightweight; keep enabled
            # throughout the app lifecycle to avoid process spawn overhead on focus toggle.
            self._enabled = True
        else:
            self._enabled = enabled

    def _is_sensitive_cli(self, clean_env: dict) -> bool:
        """Check CLI targets/MIME types to see if current clipboard holds sensitive content."""
        if not self.targets_cmd:
            return False
        try:
            res = subprocess.run(
                self.targets_cmd,
                capture_output=True,
                text=True,
                errors="replace",
                env=clean_env,
                timeout=0.4,
            )
            if res.returncode == 0 and res.stdout:
                return is_sensitive_targets(res.stdout)
        except (subprocess.SubprocessError, OSError) as exc:
            log.debug("Target inspection failed: %s", exc)
        return False

    def _check_clipboard_poll(self, clean_env: dict):
        """Perform a single poll iteration, checking sensitivity before capturing text."""
        if not (self._enabled and self.cmd):
            return

        # Check targets/MIME types first for sensitive password manager hints
        if self._is_sensitive_cli(clean_env):
            return

        try:
            result = subprocess.run(
                self.cmd,
                capture_output=True,
                text=True,
                errors="replace",
                env=clean_env,
                timeout=0.4,
            )
            if result.returncode == 0:
                text = result.stdout[:MAX_TEXT_LENGTH]
                if text and text != self._last_text:
                    self._last_text = text
                    self.text_detected.emit(text)
        except (subprocess.SubprocessError, OSError) as exc:
            log.debug("Clipboard poll failed: %s", exc)

    def run(self):
        # Copy and clean the environment to prevent GNOME from showing startup/launch
        # feedback (flickering dock icon) for our background CLI polling/watch subprocesses.
        clean_env = os.environ.copy()
        clean_env.pop("DESKTOP_STARTUP_ID", None)
        clean_env.pop("XDG_ACTIVATION_TOKEN", None)

        while self._running:
            if self.use_x11_helper:
                self._run_x11_helper(clean_env)
                if self._running:
                    time.sleep(1)
            elif self.use_watch_mode:
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
                except (OSError, subprocess.SubprocessError) as exc:
                    log.warning("Failed to start wl-paste watch: %s", exc)
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
                            # Emit the detected text only if not sensitive
                            if text:
                                if self._is_sensitive_cli(clean_env):
                                    log.info("Dropped sensitive clipboard event from wl-paste watch")
                                else:
                                    self.text_detected.emit(text[:MAX_TEXT_LENGTH])
                except (OSError, ValueError) as exc:
                    log.debug("wl-paste watch stream ended: %s", exc)
                finally:
                    _terminate_process(self._proc)

                if self._running:
                    time.sleep(1)  # Throttle restarts
            else:
                # ── Standard Polling Fallback ─────────────────────────────
                self._check_clipboard_poll(clean_env)
                time.sleep(self.interval_ms / 1000.0)

    def _run_x11_helper(self, clean_env: dict):
        """Run persistent X11/XWayland clipboard helper and stream JSON clipboard lines."""
        helper_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "x11_clipboard_helper.py",
        )
        helper_env = clean_env.copy()
        helper_env["QT_QPA_PLATFORM"] = "xcb"

        try:
            self._proc = subprocess.Popen(
                [sys.executable, helper_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                env=helper_env,
                bufsize=1,
            )
            time.sleep(0.2)
            if self._proc.poll() is not None:
                stderr_msg = self._proc.stderr.read() if self._proc.stderr else ""
                log.warning("X11 clipboard helper exited early: %s", stderr_msg.strip())
                self.use_x11_helper = False
                self._enabled = False
                return
        except (OSError, subprocess.SubprocessError) as exc:
            log.warning("Failed to start X11 clipboard helper: %s", exc)
            self.use_x11_helper = False
            self._enabled = False
            return

        try:
            while self._running and self._proc.stdout:
                line = self._proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    text = payload.get("text", "")
                except (ValueError, TypeError):
                    continue
                if text:
                    text = text[:MAX_TEXT_LENGTH]
                    if text != self._last_text:
                        self._last_text = text
                        self.text_detected.emit(text)
        except (OSError, ValueError) as exc:
            log.debug("X11 helper stream ended: %s", exc)
        finally:
            _terminate_process(self._proc)

    def stop(self):
        self._running = False
        _terminate_process(self._proc)
        self.wait()


class ClipboardService(QObject):
    """
    Performance-optimized three-tier clipboard service with off-thread worker.
    Tracks clipboard history using unique IDs to ensure precise UI deletion sync.
    """
    # Emits (item_id, text, timestamp)
    new_item = pyqtSignal(str, str, float)
    # Emits item_id of the trimmed item
    item_trimmed = pyqtSignal(str)

    POLL_INTERVAL_MS = 500  # Highly optimized check rate

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Database Service ──────────────────────────────────────────
        self._db = DatabaseService()

        # ── State ─────────────────────────────────────────────────────
        # Holds list of dicts: [{"id": str, "text": str, "timestamp": float}]
        self.history: list[dict] = self._db.load_history()
        self._last_text: str = ""
        if self.history:
            self._last_text = self.history[0]["text"]
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
        self._use_x11_helper = (
            self._clip_cmd is None and _can_use_x11_helper()
        )

        # ── Tier 1: QClipboard Signal ─────────────────────────────────
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_qt_signal)

        # ── Tier 2: Dedicated Polling/Watch Thread ────────────────────
        self._targets_cmd = _find_targets_command(self._clip_cmd)
        self._worker = ClipboardWorker(
            self._clip_cmd,
            self.POLL_INTERVAL_MS,
            self._use_watch_mode,
            self._targets_cmd,
            self,
            use_x11_helper=self._use_x11_helper,
        )
        self._worker.text_detected.connect(self._process_text)

        # ── Tier 3: Qt Polling Fallback (Only active when CLI tools missing) ──
        self._qt_timer = QTimer(self)
        self._qt_timer.setInterval(self.POLL_INTERVAL_MS)
        self._qt_timer.timeout.connect(self._on_qt_poll_tick)

        # ── Smart Focus Monitoring Timer ──────────────────────────────
        self._focus_timer = QTimer(self)
        self._focus_timer.setInterval(1000)
        self._focus_timer.timeout.connect(self._check_focus_state)

        # Initial check
        self._check_focus_state()

    def start(self):
        """Start standard timers/threads."""
        if not self._worker.isRunning():
            self._worker.start()
        if not self._focus_timer.isActive():
            self._focus_timer.start()
        if not self._clip_cmd and not self._use_x11_helper:
            self._qt_timer.start()

    def _run_x11_helper(self, clean_env: dict):
        """Run persistent X11/XWayland clipboard helper and stream JSON clipboard lines."""
        helper_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "x11_clipboard_helper.py",
        )
        helper_env = clean_env.copy()
        helper_env["QT_QPA_PLATFORM"] = "xcb"

        try:
            self._proc = subprocess.Popen(
                [sys.executable, helper_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                env=helper_env,
                bufsize=1,
            )
            time.sleep(0.2)
            if self._proc.poll() is not None:
                stderr_msg = self._proc.stderr.read() if self._proc.stderr else ""
                log.warning(f"X11 clipboard helper exited early: {stderr_msg.strip()}")
                self.use_x11_helper = False
                self._enabled = False
                return
        except Exception as e:
            log.warning(f"Failed to start X11 clipboard helper: {e}")
            self.use_x11_helper = False
            self._enabled = False
            return

        try:
            while self._running and self._proc.stdout:
                line = self._proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    text = payload.get("text", "")
                except (ValueError, TypeError):
                    continue
                if text and text != self._last_text:
                    self._last_text = text
                    self.text_detected.emit(text)
        except (OSError, ValueError) as exc:
            log.debug("X11 helper stream ended: %s", exc)
        finally:
            _terminate_process(self._proc)

    def stop(self):
        """Clean shutdown to avoid dangling threads or memory leaks."""
        self._focus_timer.stop()
        self._qt_timer.stop()
        if hasattr(self, "_worker") and self._worker.isRunning():
            self._worker.stop()
        try:
            self._clipboard.dataChanged.disconnect(self._on_qt_signal)
        except (RuntimeError, TypeError):
            pass

    def remove_item(self, item_id: str):
        """Remove item from history using its unique ID."""
        removed_text = None
        for item in self.history:
            if item["id"] == item_id:
                removed_text = item["text"]
                break

        self.history = [item for item in self.history if item["id"] != item_id]
        self._db.delete_item(item_id)

        # If the deleted item is the active one in the system clipboard, clear or update the system clipboard
        if removed_text:
            current_clipboard_text = normalize_text(self._clipboard.text())
            if current_clipboard_text == normalize_text(removed_text):
                next_text = ""
                if self.history:
                    next_text = self.history[0]["text"]

                self.set_ignore_next(next_text)
                if next_text:
                    self._clipboard.setText(next_text)
                else:
                    self._clipboard.clear()

                self._last_text = next_text
                if hasattr(self, "_worker"):
                    self._worker._last_text = next_text

    def clear_ignore_text(self):
        """Clear the ignore filter state."""
        self._ignore_next = False
        self._ignore_text = None

    def set_ignore_next(self, text: str = ""):
        """Ignore next clipboard update (used for copy-back operation)."""
        self._ignore_next = True
        self._ignore_text = text
        if hasattr(self, "_worker"):
            self._worker._last_text = text
        QTimer.singleShot(1200, self.clear_ignore_text)

    def set_item_pinned(self, item_id: str, pinned: bool):
        """Update the pinned state of an item in service history and database."""
        for item in self.history:
            if item["id"] == item_id:
                item["pinned"] = pinned
                break

        # Keep history sorted: pinned items first (newest-first), then unpinned items (newest-first)
        sort_history_items(self.history)

        # Update SQLite database
        self._db.set_pinned(item_id, pinned)

        # Enforce history limit in case unpinning caused unpinned items to exceed limit
        if not pinned:
            self._trim_history()

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

    def _capture_active_qt_clipboard(self):
        """Safely inspect MIME hints and read Qt clipboard only while window is focused."""
        if QApplication.activeWindow() is None:
            return
        if is_sensitive_mime_data(self._clipboard.mimeData()):
            log.info("Ignored sensitive clipboard text (password manager hint detected)")
            return
        self._process_text(self._clipboard.text())

    def _on_qt_signal(self):
        """Tier 1 callback: Instant when focused."""
        # Under Wayland/Ubuntu, calling QClipboard.text() while unfocused blocks
        # the main GUI thread, causing typing lag and taskbar flickering.
        self._capture_active_qt_clipboard()

    def _on_qt_poll_tick(self):
        """Tier 3 callback: Standard Qt polling fallback."""
        if not self._clip_cmd:
            self._capture_active_qt_clipboard()

    def _process_text(self, text: str):
        """Central deduplication gate."""
        # Safeguard: if activeWindow is focused, verify mime data is not sensitive
        if QApplication.activeWindow() is not None:
            try:
                if is_sensitive_mime_data(self._clipboard.mimeData()):
                    log.info("Ignored sensitive clipboard text in _process_text")
                    return
            except (RuntimeError, AttributeError) as exc:
                log.debug("Failed to inspect active MIME data: %s", exc)

        normalized = normalize_text(text)
        if not normalized:
            return

        if normalized == normalize_text(self._last_text):
            return

        if self._ignore_next or (self._ignore_text and normalized == normalize_text(self._ignore_text)):
            return

        self._last_text = normalized
        # Synchronize back to the worker thread to prevent duplicate events on focus shift
        if hasattr(self, "_worker"):
            self._worker._last_text = normalized

        item_id = uuid.uuid4().hex
        timestamp = time.time()
        # New items are always unpinned initially
        self.history.insert(0, {"id": item_id, "text": normalized, "timestamp": timestamp, "pinned": False})
        # Keep history sorted: pinned items first (newest-first), then unpinned items (newest-first)
        sort_history_items(self.history)

        self._db.save_item(item_id, normalized, timestamp, pinned=False)
        self.new_item.emit(item_id, normalized, timestamp)

        # Enforce history limit
        self._trim_history()

    def _trim_history(self):
        """Silently discard old unpinned items and notify UI."""
        unpinned_items = [item for item in self.history if not item.get("pinned", False)]
        while len(unpinned_items) > MAX_HISTORY:
            # Find the oldest unpinned item. Since self.history is ordered,
            # we iterate backwards to find the last (oldest) unpinned item.
            oldest_unpinned = None
            for item in reversed(self.history):
                if not item.get("pinned", False):
                    oldest_unpinned = item
                    break

            if oldest_unpinned:
                self.history.remove(oldest_unpinned)
                self._db.delete_item(oldest_unpinned["id"])
                self.item_trimmed.emit(oldest_unpinned["id"])
                unpinned_items = [item for item in self.history if not item.get("pinned", False)]
            else:
                break

