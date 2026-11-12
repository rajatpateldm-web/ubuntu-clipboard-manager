"""
tests/test_sensitive_detector.py
---------------------------------
Unit tests for password manager hint and sensitive clipboard detection.
"""

import unittest
from unittest.mock import MagicMock

# Import from services.sensitive_detector (which does not exist yet -> RED)
from services.sensitive_detector import (
    is_sensitive_format,
    is_sensitive_targets,
    is_sensitive_mime_data,
    SENSITIVE_MIME_FORMATS,
)


class TestSensitiveDetector(unittest.TestCase):
    """Tests for sensitive clipboard content detection."""

    def test_sensitive_formats_defined(self):
        """Verify standard password manager MIME formats are included."""
        self.assertIn("x-kde-passwordManagerHint", SENSITIVE_MIME_FORMATS)
        self.assertIn("application/x-password-manager-hint", SENSITIVE_MIME_FORMATS)
        self.assertIn("application/x-copyq-secret", SENSITIVE_MIME_FORMATS)

    def test_is_sensitive_format_detects_kde_hint(self):
        """Verify x-kde-passwordManagerHint is detected in various casings."""
        self.assertTrue(is_sensitive_format("x-kde-passwordManagerHint"))
        self.assertTrue(is_sensitive_format("X-KDE-PasswordManagerHint"))
        self.assertTrue(is_sensitive_format("x-kde-passwordmanagerhint"))

    def test_is_sensitive_format_detects_other_known_hints(self):
        """Verify other common sensitive clipboard formats are detected."""
        self.assertTrue(is_sensitive_format("application/x-password-manager-hint"))
        self.assertTrue(is_sensitive_format("x-password-manager-hint"))
        self.assertTrue(is_sensitive_format("application/x-nspasteboard-concealed-type"))
        self.assertTrue(is_sensitive_format("application/x-copyq-secret"))
        self.assertTrue(is_sensitive_format("text/x-moz-secret"))
        self.assertTrue(is_sensitive_format("x-secret"))

    def test_is_sensitive_format_normal_text(self):
        """Standard text/html/image MIME formats must not be flagged as sensitive."""
        self.assertFalse(is_sensitive_format("text/plain"))
        self.assertFalse(is_sensitive_format("text/html"))
        self.assertFalse(is_sensitive_format("image/png"))
        self.assertFalse(is_sensitive_format("UTF8_STRING"))
        self.assertFalse(is_sensitive_format(""))
        self.assertFalse(is_sensitive_format(None))

    def test_is_sensitive_targets_list(self):
        """Verify detecting sensitive format in list of target strings."""
        targets = ["text/plain", "text/plain;charset=utf-8", "x-kde-passwordManagerHint"]
        self.assertTrue(is_sensitive_targets(targets))

        normal_targets = ["text/plain", "text/plain;charset=utf-8", "UTF8_STRING"]
        self.assertFalse(is_sensitive_targets(normal_targets))

    def test_is_sensitive_targets_raw_cli_output(self):
        """Verify detecting sensitive format from raw stdout string (wl-paste or xclip)."""
        raw_output = "text/plain\nx-kde-passwordManagerHint\nSTRING\n"
        self.assertTrue(is_sensitive_targets(raw_output))

        normal_output = "TARGETS\ntext/plain\nUTF8_STRING\nSTRING\n"
        self.assertFalse(is_sensitive_targets(normal_output))

    def test_is_sensitive_targets_empty_or_none(self):
        """Empty or None targets should safely return False."""
        self.assertFalse(is_sensitive_targets([]))
        self.assertFalse(is_sensitive_targets(""))
        self.assertFalse(is_sensitive_targets(None))

    def test_is_sensitive_mime_data_none(self):
        """None QMimeData should safely return False."""
        self.assertFalse(is_sensitive_mime_data(None))

    def test_is_sensitive_mime_data_with_secret_hint(self):
        """QMimeData with x-kde-passwordManagerHint should be flagged as sensitive."""
        mock_mime = MagicMock()
        mock_mime.formats.return_value = ["text/plain", "x-kde-passwordManagerHint"]
        mock_mime.hasFormat.side_effect = lambda f: f == "x-kde-passwordManagerHint"
        mock_mime.data.return_value = b"secret"

        self.assertTrue(is_sensitive_mime_data(mock_mime))

    def test_is_sensitive_mime_data_with_plain_text_only(self):
        """QMimeData with only normal text formats should not be flagged."""
        mock_mime = MagicMock()
        mock_mime.formats.return_value = ["text/plain", "UTF8_STRING"]
        mock_mime.hasFormat.return_value = False

        self.assertFalse(is_sensitive_mime_data(mock_mime))

    def test_is_sensitive_mime_data_explicit_negative_value(self):
        """If hint format has value explicitly set to false/0, it should not be sensitive."""
        mock_mime = MagicMock()
        mock_mime.formats.return_value = ["text/plain", "x-kde-passwordManagerHint"]
        mock_mime.hasFormat.side_effect = lambda f: f == "x-kde-passwordManagerHint"
        mock_mime.data.return_value = b"0"

        self.assertFalse(is_sensitive_mime_data(mock_mime))


if __name__ == "__main__":
    unittest.main()
