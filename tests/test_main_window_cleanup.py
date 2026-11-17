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
            def fake_modal(dialog):
                dialog.select_preset("all_unpinned")
                return QDialog.DialogCode.Accepted

            mock_modal.side_effect = fake_modal
            self.window._on_open_cleanup()
            mock_modal.assert_called_once()

        self.assertEqual(self.window._model.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()
