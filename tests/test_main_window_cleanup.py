"""
tests/test_main_window_cleanup.py
---------------------------------
Integration tests for bulk cleanup in MainWindow.
"""

import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QDialog

from ui.main_window import MainWindow


class TestMainWindowCleanup(unittest.TestCase):
    """Test header cleanup button, modal overlay flow, and cleanup execution in MainWindow."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_main_cleanup_")
        self._orig_snap_data = os.environ.get("SNAP_USER_DATA")
        os.environ["SNAP_USER_DATA"] = self.tmp_dir

        self.window = MainWindow()
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

    def test_header_has_cleanup_button(self):
        """Header contains cleanup history button with proper tooltip and object name."""
        self.assertTrue(hasattr(self.window, "_cleanup_btn"))
        self.assertEqual(self.window._cleanup_btn.objectName(), "cleanupHistoryBtn")
        self.assertEqual(self.window._cleanup_btn.text(), "🧹")
        self.assertEqual(self.window._cleanup_btn.toolTip(), "Clear Old History")

    def test_execute_cleanup_deletes_unpinned_and_preserves_pinned(self):
        """_execute_cleanup removes matching unpinned items from both service and model."""
        now = time.time()
        # Prepopulate items
        self.window._service._db.save_item("p1", "Pinned clip", now - 300, pinned=True)
        self.window._service._db.save_item("u1", "Old unpinned", now - 200, pinned=False)
        self.window._service._db.save_item("u2", "Recent unpinned", now - 10, pinned=False)

        # Sync service history and model
        self.window._service.history = [
            {"id": "p1", "text": "Pinned clip", "timestamp": now - 300, "pinned": True},
            {"id": "u1", "text": "Old unpinned", "timestamp": now - 200, "pinned": False},
            {"id": "u2", "text": "Recent unpinned", "timestamp": now - 10, "pinned": False},
        ]
        self.window._model.load_items(self.window._service.history)
        self.window._update_empty_state()

        self.assertEqual(self.window._model.rowCount(), 3)
        self.assertFalse(self.window._empty_label.isVisible())

        # Clean items older than 50 seconds
        deleted = self.window._execute_cleanup(now - 50)
        self.assertEqual(deleted, 1)

        # Model should now have 2 items (p1 and u2)
        self.assertEqual(self.window._model.rowCount(), 2)
        remaining_ids = [self.window._model._items[i]["id"] for i in range(self.window._model.rowCount())]
        self.assertEqual(remaining_ids, ["p1", "u2"])

        # Service history should match
        service_ids = [item["id"] for item in self.window._service.history]
        self.assertEqual(service_ids, ["p1", "u2"])

    def test_execute_cleanup_all_unpinned_updates_empty_state_when_no_items_remain(self):
        """Cleaning all unpinned items when none are pinned triggers the empty state label."""
        now = time.time()
        self.window._service._db.save_item("u1", "Only item", now - 10, pinned=False)
        self.window._service.history = [
            {"id": "u1", "text": "Only item", "timestamp": now - 10, "pinned": False},
        ]
        self.window._model.load_items(self.window._service.history)
        self.window._update_empty_state()
        self.assertFalse(self.window._empty_label.isVisible())

        self.window._execute_cleanup(None)
        self.assertEqual(self.window._model.rowCount(), 0)
        self.assertTrue(self.window._empty_label.isVisible())

    def test_on_open_cleanup_triggers_modal_overlay(self):
        """_on_open_cleanup opens CleanupDialog in _run_modal_overlay and processes acceptance."""
        now = time.time()
        self.window._service._db.save_item("u1", "Unpinned 1", now - 200, pinned=False)
        self.window._service.history = [
            {"id": "u1", "text": "Unpinned 1", "timestamp": now - 200, "pinned": False},
        ]
        self.window._model.load_items(self.window._service.history)

        with patch.object(self.window, "_run_modal_overlay") as mock_modal:
            # Simulate user accepting the dialog
            def fake_modal(dialog, *args, **kwargs):
                dialog.select_preset("all_unpinned")
                return QDialog.DialogCode.Accepted

            mock_modal.side_effect = fake_modal
            self.window._on_open_cleanup()
            mock_modal.assert_called_once()

        self.assertEqual(self.window._model.rowCount(), 0)

    def test_count_unpinned_queries_sqlite_exceeding_model_window(self):
        """Count preview queries persistent SQLite storage rather than the capped in-memory model."""
        now = time.time()
        # Save 150 items to SQLite database
        for i in range(150):
            self.window._service._db.save_item(f"hist_{i}", f"Item {i}", now - 1000, pinned=False)

        # In-memory model only loads the top 50 items
        self.window._model.load_items([
            {"id": f"hist_{i}", "text": f"Item {i}", "timestamp": now - 1000, "pinned": False}
            for i in range(50)
        ])
        self.assertEqual(self.window._model.rowCount(), 50)

        # Count preview must return 150 from SQLite, not 50 from model
        count = self.window._count_unpinned_items(None)
        self.assertEqual(count, 150)

    def test_backdrop_scrim_click_ignores_for_cleanup_dialog(self):
        """Clicking the backdrop outside CleanupDialog must NOT accept or trigger deletion."""
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from ui.cleanup_dialog import CleanupDialog
        from ui.main_window import _ModalBackdrop

        cleanup_dialog = CleanupDialog(count_callback=lambda cutoff: 10, parent=self.window)
        backdrop = _ModalBackdrop(
            self.window,
            cleanup_dialog,
            dismiss_action=getattr(cleanup_dialog, "scrim_dismiss_action", "ignore"),
        )
        backdrop.resize(500, 700)
        cleanup_dialog.resize(380, 300)
        # Position cleanup_dialog inside backdrop
        cleanup_dialog.move(60, 200)

        # Click at top-left padding (10, 10), which is on the backdrop outside the dialog card
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10.0, 10.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        backdrop.mousePressEvent(event)

        # Must not be accepted
        self.assertNotEqual(cleanup_dialog.result(), QDialog.DialogCode.Accepted)

    def test_backdrop_scrim_click_accepts_for_default_dialog(self):
        """Clicking the backdrop for standard settings dialogs still accepts for live preview."""
        from PyQt6.QtCore import QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from ui.color_dialog import ColorOptionsDialog
        from ui.main_window import _ModalBackdrop

        color_dialog = ColorOptionsDialog(parent=self.window)
        backdrop = _ModalBackdrop(self.window, color_dialog, dismiss_action="accept")
        backdrop.resize(500, 700)
        color_dialog.resize(380, 300)
        color_dialog.move(60, 200)

        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10.0, 10.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        backdrop.mousePressEvent(event)

        self.assertEqual(color_dialog.result(), QDialog.DialogCode.Accepted)


if __name__ == "__main__":
    unittest.main()
