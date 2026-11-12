"""
tests/test_sensitive_clipboard_service.py
-----------------------------------------
Integration tests for ClipboardService and ClipboardWorker sensitive content handling.
"""

import unittest
from unittest.mock import MagicMock, patch

from services.clipboard_service import ClipboardService, ClipboardWorker


class TestClipboardServiceSensitivity(unittest.TestCase):
    """Verify ClipboardService suppresses sensitive password manager data."""

    def setUp(self):
        # Patch QApplication so QObject instantiation works in headless test environment
        self.app_patcher = patch("services.clipboard_service.QApplication")
        self.mock_qapp = self.app_patcher.start()

        # Mock clipboard
        self.mock_clipboard = MagicMock()
        self.mock_qapp.clipboard.return_value = self.mock_clipboard
        self.mock_qapp.activeWindow.return_value = MagicMock()  # Simulate focused window

        # Patch DatabaseService to prevent disk writes during tests
        self.db_patcher = patch("services.clipboard_service.DatabaseService")
        self.mock_db_cls = self.db_patcher.start()
        self.mock_db = MagicMock()
        self.mock_db.load_history.return_value = []
        self.mock_db_cls.return_value = self.mock_db

    def tearDown(self):
        self.db_patcher.stop()
        self.app_patcher.stop()

    def test_qt_signal_ignores_sensitive_password_hint(self):
        """When x-kde-passwordManagerHint is present, _on_qt_signal must drop the text."""
        service = ClipboardService()
        new_item_mock = MagicMock()
        service.new_item.connect(new_item_mock)

        # Configure mock mime data with password hint
        mock_mime = MagicMock()
        mock_mime.formats.return_value = ["text/plain", "x-kde-passwordManagerHint"]
        mock_mime.hasFormat.side_effect = lambda f: f == "x-kde-passwordManagerHint"
        mock_mime.data.return_value = b"secret"

        self.mock_clipboard.mimeData.return_value = mock_mime
        self.mock_clipboard.text.return_value = "SuperSecretPassword123!"

        # Trigger Qt signal handler
        service._on_qt_signal()

        # Verify nothing was stored or emitted
        self.assertEqual(len(service.history), 0)
        self.mock_db.save_item.assert_not_called()
        new_item_mock.assert_not_called()
        service.stop()

    def test_qt_signal_processes_normal_text(self):
        """Normal text without password hints must be saved and emitted."""
        service = ClipboardService()
        new_item_mock = MagicMock()
        service.new_item.connect(new_item_mock)

        mock_mime = MagicMock()
        mock_mime.formats.return_value = ["text/plain"]
        mock_mime.hasFormat.return_value = False

        self.mock_clipboard.mimeData.return_value = mock_mime
        self.mock_clipboard.text.return_value = "Normal Copied Text"

        service._on_qt_signal()

        self.assertEqual(len(service.history), 1)
        self.assertEqual(service.history[0]["text"], "Normal Copied Text")
        self.mock_db.save_item.assert_called_once()
        new_item_mock.assert_called_once()
        service.stop()

    def test_qt_poll_tick_ignores_sensitive_content(self):
        """Tier 3 Qt poll fallback must drop sensitive content."""
        service = ClipboardService()
        service._clip_cmd = None  # Force fallback path

        mock_mime = MagicMock()
        mock_mime.formats.return_value = ["text/plain", "application/x-password-manager-hint"]
        mock_mime.hasFormat.side_effect = lambda f: f == "application/x-password-manager-hint"
        mock_mime.data.return_value = b"secret"

        self.mock_clipboard.mimeData.return_value = mock_mime
        self.mock_clipboard.text.return_value = "SecretFromPolling"

        service._on_qt_poll_tick()

        self.assertEqual(len(service.history), 0)
        self.mock_db.save_item.assert_not_called()
        service.stop()


    def test_subsequent_normal_clip_captured_after_sensitive_clip(self):
        """A normal clip arriving after a rejected sensitive clip must be captured cleanly."""
        service = ClipboardService()
        new_item_mock = MagicMock()
        service.new_item.connect(new_item_mock)

        # 1. First event: sensitive password
        secret_mime = MagicMock()
        secret_mime.formats.return_value = ["text/plain", "x-kde-passwordManagerHint"]
        secret_mime.hasFormat.side_effect = lambda f: f == "x-kde-passwordManagerHint"
        secret_mime.data.return_value = b"secret"

        self.mock_clipboard.mimeData.return_value = secret_mime
        self.mock_clipboard.text.return_value = "Password123!"
        service._on_qt_signal()

        self.assertEqual(len(service.history), 0)
        new_item_mock.assert_not_called()

        # 2. Second event: safe text
        safe_mime = MagicMock()
        safe_mime.formats.return_value = ["text/plain"]
        safe_mime.hasFormat.return_value = False

        self.mock_clipboard.mimeData.return_value = safe_mime
        self.mock_clipboard.text.return_value = "Public URL or Note"
        service._on_qt_signal()

        self.assertEqual(len(service.history), 1)
        self.assertEqual(service.history[0]["text"], "Public URL or Note")
        new_item_mock.assert_called_once()
        service.stop()

    def test_mime_data_none_handled_gracefully(self):
        """When mimeData() returns None, service should safely process text without error."""
        service = ClipboardService()
        self.mock_clipboard.mimeData.return_value = None
        self.mock_clipboard.text.return_value = "Text With None Mime"

        service._on_qt_signal()
        self.assertEqual(len(service.history), 1)
        service.stop()


class TestClipboardWorkerSensitivity(unittest.TestCase):
    """Verify ClipboardWorker ignores clipboard when CLI targets contain sensitive hints."""

    @patch("services.clipboard_service.subprocess.run")
    def test_worker_polling_checks_targets_before_emitting(self, mock_subproc_run):
        """ClipboardWorker polling should check targets/MIME types and skip secrets."""
        # Simulate xclip returning TARGETS with x-kde-passwordManagerHint
        mock_targets_result = MagicMock()
        mock_targets_result.returncode = 0
        mock_targets_result.stdout = "TARGETS\ntext/plain\nx-kde-passwordManagerHint\n"

        mock_subproc_run.return_value = mock_targets_result

        worker = ClipboardWorker(
            cmd=["xclip", "-selection", "clipboard", "-o"],
            interval_ms=100,
            use_watch_mode=False
        )
        worker.set_enabled(True)

        detected_mock = MagicMock()
        worker.text_detected.connect(detected_mock)

        # Execute one poll check
        worker._check_clipboard_poll(clean_env={})

        detected_mock.assert_not_called()

    @patch("services.clipboard_service.subprocess.run")
    def test_worker_polling_emits_when_not_sensitive(self, mock_subproc_run):
        """When targets are normal, worker proceeds to read clipboard text and emit."""
        mock_targets = MagicMock()
        mock_targets.returncode = 0
        mock_targets.stdout = "TARGETS\ntext/plain\nUTF8_STRING\n"

        mock_text = MagicMock()
        mock_text.returncode = 0
        mock_text.stdout = "Harmless Text From CLI"

        mock_subproc_run.side_effect = [mock_targets, mock_text]

        worker = ClipboardWorker(
            cmd=["xclip", "-selection", "clipboard", "-o"],
            interval_ms=100,
            use_watch_mode=False
        )
        worker.set_enabled(True)

        detected_mock = MagicMock()
        worker.text_detected.connect(detected_mock)

        worker._check_clipboard_poll(clean_env={})

        detected_mock.assert_called_once_with("Harmless Text From CLI")

    @patch("services.clipboard_service.subprocess.run")
    def test_worker_handles_subproc_exception_gracefully(self, mock_subproc_run):
        """Worker should handle subprocess exceptions without crashing."""
        mock_subproc_run.side_effect = Exception("Subprocess failure")

        worker = ClipboardWorker(
            cmd=["wl-paste", "--no-newline"],
            interval_ms=100,
            use_watch_mode=False
        )

        # Should not raise exception
        worker._check_clipboard_poll(clean_env={})


if __name__ == "__main__":
    unittest.main()
