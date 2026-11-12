"""
tests/test_x11_helper.py
Unit and integration tests for X11ClipboardWatcher and ClipboardWorker X11 helper mode.
"""

import io
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from services.clipboard_service import ClipboardService, ClipboardWorker, _can_use_x11_helper
from services.x11_clipboard_helper import X11ClipboardWatcher


class TestX11ClipboardWatcher(unittest.TestCase):
    """Verify X11ClipboardWatcher sensitivity checks, deduplication, and JSON emission."""

    def _make_watcher(self, initial_text="", initial_sensitive=False):
        mock_app = MagicMock()
        mock_clipboard = MagicMock()
        mock_mime = MagicMock()
        mock_mime.formats.return_value = (
            ["text/plain", "x-kde-passwordManagerHint"] if initial_sensitive else ["text/plain"]
        )
        mock_mime.hasFormat.side_effect = lambda f: initial_sensitive and f == "x-kde-passwordManagerHint"
        mock_mime.data.return_value = b"1"

        mock_clipboard.mimeData.return_value = mock_mime
        mock_clipboard.text.return_value = initial_text
        mock_app.clipboard.return_value = mock_clipboard

        with patch("services.x11_clipboard_helper.QTimer"):
            watcher = X11ClipboardWatcher(mock_app, os.getpid())
        return watcher, mock_clipboard, mock_mime

    def test_emits_new_safe_text_and_deduplicates(self):
        watcher, mock_cb, mock_mime = self._make_watcher(initial_text="Initial")
        mock_mime.formats.return_value = ["text/plain"]
        mock_mime.hasFormat.return_value = False
        mock_cb.text.return_value = "Copied from Chrome\nLine 2"

        out = io.StringIO()
        with patch("sys.stdout", out):
            watcher._check_clipboard()
            # Calling again with identical text must not emit duplicate
            watcher._check_clipboard()

        lines = [line for line in out.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0]), {"text": "Copied from Chrome\nLine 2"})

    def test_ignores_sensitive_mime_data(self):
        watcher, mock_cb, mock_mime = self._make_watcher(initial_text="")
        mock_mime.formats.return_value = ["text/plain", "x-kde-passwordManagerHint"]
        mock_mime.hasFormat.side_effect = lambda f: f == "x-kde-passwordManagerHint"
        mock_mime.data.return_value = b"secret"
        mock_cb.text.return_value = "MySecretPassword"

        out = io.StringIO()
        with patch("sys.stdout", out):
            watcher._check_clipboard()

        self.assertEqual(out.getvalue(), "")


class TestClipboardWorkerX11Helper(unittest.TestCase):
    """Verify ClipboardWorker integrates with the X11 helper subprocess."""

    @patch("services.clipboard_service.time.sleep")
    @patch("services.clipboard_service.subprocess.Popen")
    def test_worker_streams_json_lines_from_helper(self, mock_popen_cls, _mock_sleep):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.stdout.readline.side_effect = [
            json.dumps({"text": "Background Copy 1"}) + "\n",
            "not-json\n",
            json.dumps({"text": "Background Copy 2"}) + "\n",
            "",
        ]
        mock_popen_cls.return_value = mock_proc

        worker = ClipboardWorker(
            cmd=None,
            interval_ms=500,
            use_watch_mode=False,
            use_x11_helper=True,
        )
        detected = []
        worker.text_detected.connect(detected.append)

        worker._run_x11_helper(os.environ.copy())

        self.assertEqual(detected, ["Background Copy 1", "Background Copy 2"])
        mock_proc.terminate.assert_called_once()

    def test_can_use_x11_helper_respects_offscreen_and_display(self):
        with patch.dict(os.environ, {"DISPLAY": ":0", "QT_QPA_PLATFORM": "offscreen"}):
            self.assertFalse(_can_use_x11_helper())
        with patch.dict(os.environ, {"DISPLAY": "", "QT_QPA_PLATFORM": "wayland"}):
            self.assertFalse(_can_use_x11_helper())
        with patch.dict(os.environ, {"DISPLAY": ":0", "QT_QPA_PLATFORM": "wayland"}):
            self.assertTrue(_can_use_x11_helper())

    @patch("services.clipboard_service.DatabaseService")
    @patch("services.clipboard_service.QApplication")
    def test_service_uses_x11_helper_when_cli_tools_missing(self, mock_qapp, mock_db_cls):
        mock_db = MagicMock()
        mock_db.load_history.return_value = []
        mock_db_cls.return_value = mock_db

        with (
            patch("services.clipboard_service._find_clipboard_command", return_value=None),
            patch("services.clipboard_service._can_use_x11_helper", return_value=True),
        ):
            service = ClipboardService()
            self.assertTrue(service._use_x11_helper)
            self.assertTrue(service._worker.use_x11_helper)
            self.assertTrue(service._worker._enabled)
            service.stop()


if __name__ == "__main__":
    unittest.main()

