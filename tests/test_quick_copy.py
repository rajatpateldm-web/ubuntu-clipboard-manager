"""
tests/test_quick_copy.py
Unit and integration tests for Quick Copy keyboard shortcuts and window lifecycle.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from ui.clipboard_model import FullTextRole, ItemIdRole
from ui.main_window import MainWindow


class TestQuickCopy(unittest.TestCase):
    """Test keyboard shortcuts, delegate badges, and window lifecycle for quick copy."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_quick_copy_")
        self._orig_snap_data = os.environ.get("SNAP_USER_DATA")
        os.environ["SNAP_USER_DATA"] = self.tmp_dir

        self.window = MainWindow()
        self.window._model.load_items([
            {"id": "1", "text": "First Item", "timestamp": 1000.0, "pinned": True},
            {"id": "2", "text": "Second Item", "timestamp": 2000.0, "pinned": False},
            {"id": "3", "text": "Third Item", "timestamp": 3000.0, "pinned": False},
        ])
        self.window.show()

    def tearDown(self):
        self.window.close()
        if hasattr(self.window, "_service"):
            self.window._service.stop()
        if self._orig_snap_data is not None:
            os.environ["SNAP_USER_DATA"] = self._orig_snap_data
        else:
            os.environ.pop("SNAP_USER_DATA", None)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_quick_copy_row_valid(self):
        """Calling _on_quick_copy_row with valid row copies text and hides window."""
        success = self.window._on_quick_copy_row(0)
        self.assertTrue(success)
        self.assertEqual(QApplication.clipboard().text(), "First Item")
        self.assertFalse(self.window.isVisible())

    def test_quick_copy_row_out_of_bounds(self):
        """Calling _on_quick_copy_row with out of bounds row returns False and keeps window visible."""
        self.window.show()
        success = self.window._on_quick_copy_row(8)
        self.assertFalse(success)
        self.assertTrue(self.window.isVisible())

    def test_enter_key_activation_hides_window(self):
        """Activating an item in list view via Enter copies text and hides window."""
        self.window.show()
        second_index = self.window._proxy_model.index(1, 0)
        self.window._on_item_activated(second_index)
        self.assertEqual(QApplication.clipboard().text(), "Third Item")
        self.assertFalse(self.window.isVisible())

    def test_enter_key_in_search_bar_does_not_hide_window(self):
        """Pressing Enter in search bar does not trigger quick copy or hide window."""
        self.window.show()
        self.window._search_bar.setText("test query")
        enter_event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier,
            "\r",
        )
        handled = self.window.eventFilter(self.window._search_bar, enter_event)
        self.assertIn(handled, (False, None))
        self.assertTrue(self.window.isVisible())

    def test_manual_copy_leaves_window_visible(self):
        """Clicking manual copy button copies text and leaves window open."""
        self.window.show()
        self.window._on_copy_item("2", "Second Item")
        self.assertEqual(QApplication.clipboard().text(), "Second Item")
        self.assertTrue(self.window.isVisible())

    def test_ctrl_number_from_search_bar(self):
        """Pressing Ctrl+2 in search bar quick-copies second item and hides window."""
        self.window.show()
        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_2,
            Qt.KeyboardModifier.ControlModifier,
            "2",
        )
        handled = self.window.eventFilter(self.window._search_bar, event)
        self.assertTrue(handled)
        self.assertEqual(QApplication.clipboard().text(), "Third Item")
        self.assertFalse(self.window.isVisible())

    def test_ctrl_number_from_list_view(self):
        """Pressing Ctrl+1 when list view is focused quick-copies first item and hides window."""
        self.window.show()
        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_1,
            Qt.KeyboardModifier.ControlModifier,
            "1",
        )
        handled = self.window.eventFilter(self.window._list_view, event)
        self.assertTrue(handled)
        self.assertEqual(QApplication.clipboard().text(), "First Item")
        self.assertFalse(self.window.isVisible())

    def test_quick_copy_does_not_create_duplicate_history_entry(self):
        """Quick copy calls set_ignore_next to prevent clipboard echo duplicate."""
        initial_count = self.window._model.rowCount()
        self.window._on_quick_copy_row(0)
        self.assertTrue(self.window._service._ignore_next)
        self.assertEqual(self.window._service._ignore_text, "First Item")
        self.assertEqual(self.window._model.rowCount(), initial_count)

    def test_delegate_shortcut_badge_computation(self):
        """Delegate returns ^1 through ^9 for rows 0 through 8, and None for row >= 9."""
        delegate = self.window._delegate
        self.assertEqual(delegate._get_shortcut_badge_text(0), "^1")
        self.assertEqual(delegate._get_shortcut_badge_text(1), "^2")
        self.assertEqual(delegate._get_shortcut_badge_text(8), "^9")
        self.assertIsNone(delegate._get_shortcut_badge_text(9))
        self.assertIsNone(delegate._get_shortcut_badge_text(-1))

    def test_search_filtering_remaps_quick_copy(self):
        """Typing a search query dynamically remaps Ctrl+1 to the first filtered item."""
        self.window.show()
        self.window._search_bar.setText("Third")
        self.assertEqual(self.window._proxy_model.rowCount(), 1)
        success = self.window._on_quick_copy_row(0)
        self.assertTrue(success)
        self.assertEqual(QApplication.clipboard().text(), "Third Item")
        self.assertFalse(self.window.isVisible())

    def test_pinned_item_priority_in_quick_copy(self):
        """Pinned items appear first and receive top shortcut indices."""
        first_index = self.window._proxy_model.index(0, 0)
        self.assertEqual(first_index.data(ItemIdRole), "1")
        success = self.window._on_quick_copy_row(0)
        self.assertTrue(success)
        self.assertEqual(QApplication.clipboard().text(), "First Item")

    def test_background_service_persists_when_window_hidden(self):
        """Clipboard monitoring and model ingestion remain fully operational when window is hidden."""
        self.window.show()
        self.window.hide()
        self.assertFalse(self.window.isVisible())

        # Simulate new incoming clip while window is hidden
        self.window._on_new_clip("4", "Background Item", 4000.0)
        self.assertEqual(self.window._model.rowCount(), 4)

        # Re-showing the window reflects the updated model
        self.window.show()
        self.assertEqual(self.window._proxy_model.rowCount(), 4)
        self.assertEqual(self.window._proxy_model.index(1, 0).data(FullTextRole), "Background Item")

    def test_toggle_window_repeated_cycles(self):
        """Toggling window repeatedly preserves service state and focus."""
        for _ in range(3):
            self.window.toggle_window()
            self.window.toggle_window()
        self.assertGreaterEqual(self.window._model.rowCount(), 3)

    def test_ctrl_number_from_window_keypress(self):
        """Pressing Ctrl+1 directly on the window dispatches quick copy."""
        self.window.show()
        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_1,
            Qt.KeyboardModifier.ControlModifier,
            "1",
        )
        self.window.keyPressEvent(event)
        self.assertEqual(QApplication.clipboard().text(), "First Item")
        self.assertFalse(self.window.isVisible())

    def test_quick_copy_ignored_when_modal_dialog_is_active(self):
        """Quick copy does not trigger or dismiss window when an in-window modal dialog is active."""
        self.window.show()
        self.window._active_modal_dialog = MagicMock()
        success = self.window._on_quick_copy_row(0)
        self.assertFalse(success)
        self.assertTrue(self.window.isVisible())

    def test_ctrl_number_with_keypad_modifier(self):
        """Pressing Ctrl+1 with KeypadModifier also triggers quick copy."""
        self.window.show()
        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_1,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.KeypadModifier,
            "1",
        )
        handled = self.window.eventFilter(self.window._search_bar, event)
        self.assertTrue(handled)
        self.assertEqual(QApplication.clipboard().text(), "First Item")
        self.assertFalse(self.window.isVisible())

    def test_footer_displays_version_and_removes_active_monitor_text(self):
        """Footer displays the application version and removes the active monitor status text."""
        self.assertIn("1.1.0", self.window._footer.text())
        self.assertNotIn("Active:", self.window._footer.text())
        self.assertNotIn("Smooth background monitoring", self.window._footer.text())


if __name__ == "__main__":
    unittest.main()
