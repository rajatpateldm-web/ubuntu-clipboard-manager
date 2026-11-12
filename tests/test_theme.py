"""
tests/test_theme.py
Unit and integration tests for ClipVault Light Mode, theme persistence,
palette dynamic switching, and keyboard navigation.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from PyQt6.QtCore import Qt, QSettings, QEvent
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from ui.styles import DARK_THEME, LIGHT_THEME, DELEGATE_PALETTES
from ui.clipboard_delegate import ClipboardItemDelegate
from ui.main_window import MainWindow
from ui.clipboard_model import ItemIdRole


class TestThemeAndKeyboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="clipvault_theme_test_")
        self.env_patch = patch.dict(os.environ, {"SNAP_USER_DATA": self.temp_dir})
        self.env_patch.start()
        QSettings("ClipVault", "App").clear()
        self.windows: list[MainWindow] = []

    def tearDown(self):
        for w in self.windows:
            try:
                w._service.stop()
                w.close()
            except Exception:
                pass
        self.app.processEvents()
        self.env_patch.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_window(self) -> MainWindow:
        w = MainWindow()
        self.windows.append(w)
        return w

    def test_theme_stylesheets_defined(self):
        """Verify both DARK_THEME and LIGHT_THEME stylesheets are defined and distinct."""
        self.assertIsInstance(DARK_THEME, str)
        self.assertIsInstance(LIGHT_THEME, str)
        self.assertTrue(len(DARK_THEME) > 100)
        self.assertTrue(len(LIGHT_THEME) > 100)
        self.assertNotEqual(DARK_THEME, LIGHT_THEME)

    def test_delegate_palettes_structure(self):
        """Verify DELEGATE_PALETTES contains all required keys for dark and light modes."""
        self.assertIn("dark", DELEGATE_PALETTES)
        self.assertIn("light", DELEGATE_PALETTES)

        required_keys = [
            "unpinned_bg",
            "unpinned_bg_hover",
            "unpinned_border",
            "pinned_bg",
            "pinned_border",
            "text_primary",
            "text_secondary",
            "badge_bg",
            "badge_text",
            "pin_active",
            "copy_bg",
            "copy_fg",
            "del_fg",
        ]
        for theme_name in ("dark", "light"):
            palette = DELEGATE_PALETTES[theme_name]
            for key in required_keys:
                self.assertIn(key, palette, f"Key '{key}' missing from '{theme_name}' palette")

    def test_delegate_theme_switching(self):
        """Verify ClipboardItemDelegate updates its active palette when switching themes."""
        delegate = ClipboardItemDelegate()
        self.assertEqual(delegate._theme_name, "dark")
        self.assertEqual(delegate._palette["unpinned_bg"], DELEGATE_PALETTES["dark"]["unpinned_bg"])

        delegate.set_theme("light")
        self.assertEqual(delegate._theme_name, "light")
        self.assertEqual(delegate._palette["unpinned_bg"], DELEGATE_PALETTES["light"]["unpinned_bg"])

        # Unknown theme should safely fall back to dark
        delegate.set_theme("unknown_mode")
        self.assertEqual(delegate._theme_name, "dark")

    def test_main_window_theme_toggle_and_persistence(self):
        """Verify MainWindow theme toggling switches button icon, delegate palette, and persists state."""
        window = self._create_window()
        window.show()

        # Default is dark
        self.assertEqual(window._theme, "dark")
        self.assertEqual(window._theme_btn.text(), "☀️")
        self.assertEqual(window._delegate._theme_name, "dark")

        # Toggle to light mode
        window._on_toggle_theme()
        self.assertEqual(window._theme, "light")
        self.assertEqual(window._theme_btn.text(), "🌙")
        self.assertEqual(window._delegate._theme_name, "light")
        self.assertEqual(QSettings("ClipVault", "App").value("theme"), "light")

        # Toggle back to dark mode
        window._on_toggle_theme()
        self.assertEqual(window._theme, "dark")
        self.assertEqual(window._theme_btn.text(), "☀️")
        self.assertEqual(window._delegate._theme_name, "dark")
        self.assertEqual(QSettings("ClipVault", "App").value("theme"), "dark")

        # Set to light and verify new instance restores light mode from QSettings
        window.set_theme("light")

        window2 = self._create_window()
        self.assertEqual(window2._theme, "light")
        self.assertEqual(window2._theme_btn.text(), "🌙")
        self.assertEqual(window2._delegate._theme_name, "light")

    def test_keyboard_navigation_escape_dismiss(self):
        """Verify pressing Escape dismisses (hides) the window."""
        window = self._create_window()
        window.show()
        self.assertTrue(window.isVisible())

        # Synthesize Escape key event
        escape_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(escape_event)

        self.assertFalse(window.isVisible())

    def test_keyboard_navigation_down_arrow_from_search(self):
        """Verify pressing Down Arrow in search bar shifts focus to list view row 0."""
        window = self._create_window()
        window.show()

        window._on_new_clip("clip_test_1", "Test Content 1", 1000.0)
        window._on_new_clip("clip_test_2", "Test Content 2", 2000.0)

        # Focus search bar
        window._search_bar.setFocus()
        self.app.processEvents()

        down_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
        handled = window.eventFilter(window._search_bar, down_event)

        self.assertTrue(handled)
        self.assertTrue(window._list_view.hasFocus())
        self.assertEqual(window._list_view.currentIndex().row(), 0)

    def test_keyboard_navigation_delete_item(self):
        """Verify pressing Delete on selected list item removes it."""
        window = self._create_window()
        window.show()

        window._on_new_clip("clip_del_test", "Delete Me", 1000.0)
        self.assertIsNotNone(window._model.get_item_by_id("clip_del_test"))

        # Select the item in list view
        first_index = window._proxy_model.index(0, 0)
        window._list_view.setCurrentIndex(first_index)

        del_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
        handled = window.eventFilter(window._list_view, del_event)

        self.assertTrue(handled)
        self.assertIsNone(window._model.get_item_by_id("clip_del_test"))


if __name__ == "__main__":
    unittest.main()
