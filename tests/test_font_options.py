"""
tests/test_font_options.py
Unit and integration tests for ClipVault font family, style, and size options.
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QModelIndex, QRect, QSettings
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication, QStyleOptionViewItem

from ui.clipboard_delegate import ClipboardItemDelegate
from ui.font_dialog import FontOptionsDialog
from ui.main_window import MainWindow
from ui.styles import (
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_STYLE,
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    build_stylesheet,
    clamp_font_size,
    normalize_font_style,
    sanitize_font_family,
)


class TestFontHelpersAndStylesheet(unittest.TestCase):
    """Verify font sanitization, clamping, normalization, and QSS generation."""

    def test_sanitize_font_family(self):
        self.assertEqual(sanitize_font_family(None), DEFAULT_FONT_FAMILY)
        self.assertEqual(sanitize_font_family("   "), DEFAULT_FONT_FAMILY)
        self.assertEqual(sanitize_font_family("monospace"), "Monospace")
        self.assertEqual(sanitize_font_family("DejaVu Sans"), "DejaVu Sans")
        self.assertEqual(
            sanitize_font_family("Ubuntu'; color: red; /* */"),
            "Ubuntu color: red",
        )
        self.assertEqual(len(sanitize_font_family("A" * 200)), 128)
        self.assertEqual(sanitize_font_family("'\";{}\n"), DEFAULT_FONT_FAMILY)

    def test_normalize_font_style(self):
        self.assertEqual(normalize_font_style("regular"), "Regular")
        self.assertEqual(normalize_font_style("BOLD"), "Bold")
        self.assertEqual(normalize_font_style("Italic"), "Italic")
        self.assertEqual(normalize_font_style("bold italic"), "Bold Italic")
        self.assertEqual(normalize_font_style("unknown"), DEFAULT_FONT_STYLE)
        self.assertEqual(normalize_font_style(None), DEFAULT_FONT_STYLE)

    def test_clamp_font_size(self):
        self.assertEqual(clamp_font_size(13), 13)
        self.assertEqual(clamp_font_size("16"), 16)
        self.assertEqual(clamp_font_size(4), MIN_FONT_SIZE)
        self.assertEqual(clamp_font_size(99), MAX_FONT_SIZE)
        self.assertEqual(clamp_font_size("invalid"), DEFAULT_FONT_SIZE)
        self.assertEqual(clamp_font_size(None), DEFAULT_FONT_SIZE)

    def test_build_stylesheet_applies_font_options(self):
        qss = build_stylesheet(
            "dark",
            font_family="Monospace",
            font_size=16,
            font_style="Bold Italic",
        )
        self.assertIn("'Ubuntu Mono', 'DejaVu Sans Mono', monospace", qss)
        self.assertIn("font-size: 16px;", qss)
        self.assertIn("font-weight: bold;", qss)
        self.assertIn("font-style: italic;", qss)


class TestDelegateFontRendering(unittest.TestCase):
    """Verify ClipboardItemDelegate scales fonts, layout hints, and paints cleanly."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_delegate_size_hint_scales_with_font_size(self):
        delegate = ClipboardItemDelegate()
        option = QStyleOptionViewItem()
        option.rect = QRect(0, 0, 400, 64)

        self.assertEqual(delegate.sizeHint(option, QModelIndex()).height(), 64)

        delegate.set_font("Monospace", 18, "Bold")
        self.assertGreater(delegate.sizeHint(option, QModelIndex()).height(), 64)

        delegate.set_font("Ubuntu", 10, "Regular")
        self.assertEqual(delegate.sizeHint(option, QModelIndex()).height(), 64)

    def test_delegate_build_font_and_paint(self):
        delegate = ClipboardItemDelegate()
        delegate.set_font("Serif", 16, "Bold Italic")

        font = delegate._build_font()
        self.assertEqual(font.family(), "Serif")
        self.assertTrue(font.bold())
        self.assertTrue(font.italic())
        self.assertEqual(font.pointSize(), 13)

        image = QImage(420, 80, QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        option = QStyleOptionViewItem()
        option.rect = QRect(0, 0, 420, 73)

        from ui.clipboard_model import ClipboardModel

        model = ClipboardModel()
        model.add_item("id1", "Line 1\nLine 2\nLine 3", 1000.0, pinned=True)
        delegate.paint(painter, option, model.index(0, 0))
        painter.end()


class TestMainWindowAndDialogFontOptions(unittest.TestCase):
    """Verify MainWindow persistence, theme preservation, and FontOptionsDialog."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="clipvault_font_test_")
        self.env_patch = patch.dict(os.environ, {"SNAP_USER_DATA": self.temp_dir})
        self.env_patch.start()
        QSettings("ClipVault", "App").clear()
        self.windows: list[MainWindow] = []

    def tearDown(self):
        for w in self.windows:
            try:
                w._service.stop()
                w.close()
            except RuntimeError as exc:
                self._cleanup_error = exc
        self.app.processEvents()
        self.env_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_window(self) -> MainWindow:
        w = MainWindow()
        self.windows.append(w)
        return w

    def test_main_window_font_persistence_and_theme_toggle(self):
        window = self._create_window()
        self.assertEqual(window._font_family, DEFAULT_FONT_FAMILY)
        self.assertEqual(window._font_size, DEFAULT_FONT_SIZE)
        self.assertEqual(window._font_style, DEFAULT_FONT_STYLE)
        self.assertTrue(hasattr(window, "_font_btn"))
        self.assertEqual(window._font_btn.text(), "Aa")

        window.set_font_options(font_family="Monospace", font_size=16, font_style="Bold")

        self.assertEqual(window._font_family, "Monospace")
        self.assertEqual(window._font_size, 16)
        self.assertEqual(window._font_style, "Bold")
        self.assertEqual(window._delegate._font_family, "Monospace")
        self.assertEqual(window._delegate._font_size, 16)
        self.assertEqual(window._delegate._font_style, "Bold")
        self.assertIn("font-size: 16px;", self.app.styleSheet())

        # Toggling theme must keep font settings intact
        window._on_toggle_theme()
        self.assertEqual(window._theme, "light")
        self.assertIn("font-size: 16px;", self.app.styleSheet())
        self.assertIn("'Ubuntu Mono', 'DejaVu Sans Mono', monospace", self.app.styleSheet())

        # New MainWindow restores persisted font settings from QSettings
        window2 = self._create_window()
        self.assertEqual(window2._font_family, "Monospace")
        self.assertEqual(window2._font_size, 16)
        self.assertEqual(window2._font_style, "Bold")
        self.assertEqual(window2._delegate._font_size, 16)

    def test_font_options_dialog_updates_and_resets(self):
        dialog = FontOptionsDialog(
            font_family="Ubuntu",
            font_size=14,
            font_style="Italic",
        )
        emissions = []
        dialog.font_changed.connect(lambda fam, sz, st: emissions.append((fam, sz, st)))

        self.assertEqual(dialog._family_combo.currentText(), "Ubuntu")
        self.assertEqual(dialog._style_combo.currentText(), "Italic")
        self.assertEqual(dialog._size_spin.value(), 14)

        dialog._family_combo.setCurrentText("Monospace")
        dialog._style_combo.setCurrentText("Bold")
        dialog._size_spin.setValue(18)

        self.assertEqual(emissions[-1], ("Monospace", 18, "Bold"))
        self.assertTrue(dialog._preview_text.font().bold())
        self.assertEqual(dialog._preview_text.font().pixelSize(), 18)

        dialog._on_reset()
        self.assertEqual(
            emissions[-1],
            (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, DEFAULT_FONT_STYLE),
        )
        self.assertEqual(dialog._family_combo.currentText(), DEFAULT_FONT_FAMILY)
        self.assertEqual(dialog._style_combo.currentText(), DEFAULT_FONT_STYLE)
        self.assertEqual(dialog._size_spin.value(), DEFAULT_FONT_SIZE)
        dialog.close()


if __name__ == "__main__":
    unittest.main()

