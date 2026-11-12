"""
tests/test_color_options.py
Unit and integration tests for ClipVault clipboard color schemes and ColorOptionsDialog.
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QRect, QSettings, Qt, QTimer
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QStyleOptionViewItem

from ui.clipboard_delegate import ClipboardItemDelegate
from ui.clipboard_model import ClipboardModel
from ui.color_dialog import ColorOptionsDialog
from ui.main_window import MainWindow
from ui.styles import (
    COLOR_SCHEMES,
    DEFAULT_COLOR_SCHEME,
    DELEGATE_PALETTES,
    build_stylesheet,
    get_delegate_palette,
    get_scheme_swatches,
    get_theme_colors,
    normalize_color_scheme,
)


class TestColorSchemesAndStylesheet(unittest.TestCase):
    """Verify color scheme definitions, normalization, and stylesheet generation."""

    def test_expected_schemes_exist(self):
        expected = {
            "Classic",
            "Cyan",
            "One Dark",
            "Dracula",
            "Nord",
            "Tokyo Night",
            "Monokai",
            "Gruvbox",
            "Solarized",
            "Catppuccin",
        }
        self.assertTrue(expected.issubset(set(COLOR_SCHEMES.keys())))

    def test_normalize_color_scheme(self):
        self.assertEqual(normalize_color_scheme("cyan"), "Cyan")
        self.assertEqual(normalize_color_scheme("tokyo night"), "Tokyo Night")
        self.assertEqual(normalize_color_scheme("DRACULA"), "Dracula")
        self.assertEqual(normalize_color_scheme("nonexistent"), DEFAULT_COLOR_SCHEME)
        self.assertEqual(normalize_color_scheme(None), DEFAULT_COLOR_SCHEME)

    def test_all_schemes_have_required_qss_and_delegate_keys(self):
        qss_keys = set(get_theme_colors("dark", "Classic").keys())
        delegate_keys = set(DELEGATE_PALETTES["dark"].keys())

        for scheme_name in COLOR_SCHEMES:
            for mode in ("dark", "light"):
                qss = get_theme_colors(mode, scheme_name)
                delegate_pal = get_delegate_palette(mode, scheme_name)
                self.assertEqual(set(qss.keys()), qss_keys, f"{scheme_name}/{mode} QSS keys mismatch")
                self.assertEqual(
                    set(delegate_pal.keys()),
                    delegate_keys,
                    f"{scheme_name}/{mode} delegate keys mismatch",
                )
                swatches = get_scheme_swatches(mode, scheme_name)
                self.assertEqual(len(swatches), 4)
                for color in swatches:
                    self.assertTrue(color.startswith("#"), f"Invalid swatch {color}")

    def test_build_stylesheet_uses_selected_scheme_colors(self):
        cyan_qss = build_stylesheet("dark", color_scheme="Cyan")
        dracula_qss = build_stylesheet("dark", color_scheme="Dracula")
        self.assertIn("#22D3EE", cyan_qss)
        self.assertIn("#BD93F9", dracula_qss)
        self.assertNotEqual(cyan_qss, dracula_qss)


class TestDelegateAndMainWindowColorOptions(unittest.TestCase):
    """Verify ClipboardItemDelegate, MainWindow persistence, and ColorOptionsDialog."""

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="clipvault_color_test_")
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

    def test_delegate_renders_all_color_schemes(self):
        delegate = ClipboardItemDelegate()
        model = ClipboardModel()
        model.add_item("id1", "Sample Item\nLine 2", 1000.0, pinned=True)
        model.add_item("id2", "Unpinned Item", 900.0, pinned=False)

        option = QStyleOptionViewItem()
        option.rect = QRect(0, 0, 420, 64)
        image = QImage(420, 64, QImage.Format.Format_ARGB32)

        for scheme in COLOR_SCHEMES:
            for mode in ("dark", "light"):
                delegate.set_theme(mode, scheme)
                self.assertEqual(delegate._color_scheme, scheme)
                self.assertEqual(delegate._palette, get_delegate_palette(mode, scheme))

                painter = QPainter(image)
                delegate.paint(painter, option, model.index(0, 0))
                delegate.paint(painter, option, model.index(1, 0))
                painter.end()

    def test_main_window_color_scheme_persistence_and_theme_toggle(self):
        window = self._create_window()
        self.assertEqual(window._color_scheme, DEFAULT_COLOR_SCHEME)
        self.assertTrue(hasattr(window, "_color_btn"))

        window.set_color_scheme("Tokyo Night")
        self.assertEqual(window._color_scheme, "Tokyo Night")
        self.assertEqual(window._delegate._color_scheme, "Tokyo Night")
        self.assertIn("#7AA2F7", self.app.styleSheet())

        # Toggling light/dark preserves selected color scheme
        window._on_toggle_theme()
        self.assertEqual(window._theme, "light")
        self.assertEqual(window._color_scheme, "Tokyo Night")
        self.assertEqual(window._delegate._color_scheme, "Tokyo Night")
        self.assertIn("#2467CC", self.app.styleSheet())

        # New window restores persisted color scheme and theme
        window2 = self._create_window()
        self.assertEqual(window2._theme, "light")
        self.assertEqual(window2._color_scheme, "Tokyo Night")
        self.assertEqual(window2._delegate._color_scheme, "Tokyo Night")

    def test_color_options_dialog_selection_and_reset(self):
        dialog = ColorOptionsDialog(theme_name="dark", color_scheme="Classic")
        emissions = []
        dialog.color_scheme_changed.connect(emissions.append)

        self.assertEqual(
            dialog._scheme_buttons["Classic"].property("selected"),
            "true",
        )

        QTest.mouseClick(dialog._scheme_buttons["Cyan"], Qt.MouseButton.LeftButton)
        self.assertEqual(emissions[-1], "Cyan")
        self.assertEqual(dialog._scheme_buttons["Cyan"].property("selected"), "true")
        self.assertEqual(dialog._scheme_buttons["Classic"].property("selected"), "false")

        QTest.mouseClick(dialog._scheme_buttons["Dracula"], Qt.MouseButton.LeftButton)
        self.assertEqual(emissions[-1], "Dracula")

        QTest.mouseClick(dialog._reset_btn, Qt.MouseButton.LeftButton)
        self.assertEqual(emissions[-1], DEFAULT_COLOR_SCHEME)
        self.assertEqual(dialog._scheme_buttons["Classic"].property("selected"), "true")
        dialog.close()

    def test_color_options_centered_in_window_overlay(self):
        window = self._create_window()
        window.show()
        self.app.processEvents()

        captured = {}

        def _capture_and_close():
            dlg = window._active_modal_dialog
            if dlg is not None:
                captured["dlg_rect"] = dlg.geometry()
                captured["win_rect"] = window.rect()
                dlg.accept()

        QTimer.singleShot(50, _capture_and_close)
        window._on_open_color_options()

        dlg_rect = captured["dlg_rect"]
        win_rect = captured["win_rect"]
        self.assertTrue(win_rect.contains(dlg_rect))
        self.assertLessEqual(abs(dlg_rect.center().y() - win_rect.center().y()), 12)
        self.assertIsNone(window._active_modal_dialog)


if __name__ == "__main__":
    unittest.main()
