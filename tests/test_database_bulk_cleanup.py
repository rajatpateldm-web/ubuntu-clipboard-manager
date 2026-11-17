"""
tests/test_database_bulk_cleanup.py
------------------------------------
Tests for bulk cleanup and counting of unpinned clipboard items.
"""

import os
import time
import unittest
from PyQt6.QtWidgets import QApplication

from services.database_service import DatabaseService
from services.clipboard_service import ClipboardService


class TestDatabaseBulkCleanup(unittest.TestCase):
    """Test bulk deletion and counting methods in DatabaseService and ClipboardService."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.test_db = "test_bulk_cleanup.db"
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.test_db_path = os.path.join(project_root, self.test_db)
        self._cleanup_files()
        self.db = DatabaseService(db_filename=self.test_db)

    def tearDown(self):
        self._cleanup_files()

    def _cleanup_files(self):
        for ext in ["", "-wal", "-shm"]:
            path = getattr(self, "test_db_path", "") + ext
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def test_count_unpinned_older_than(self):
        """Verify accurate counting of unpinned items with and without timestamp cutoff."""
        now = time.time()
        # Item 1: unpinned, 100 seconds old
        self.db.save_item("item-1", "Old item 1", now - 100, pinned=False)
        # Item 2: unpinned, 50 seconds old
        self.db.save_item("item-2", "Old item 2", now - 50, pinned=False)
        # Item 3: unpinned, 10 seconds old
        self.db.save_item("item-3", "Recent item", now - 10, pinned=False)
        # Item 4: pinned, 200 seconds old
        self.db.save_item("item-4", "Pinned item", now - 200, pinned=True)

        # Count older than 30 seconds: items 1 and 2 (item 4 is pinned, item 3 is newer)
        count_older = self.db.count_unpinned_older_than(now - 30)
        self.assertEqual(count_older, 2)

        # Count all unpinned: items 1, 2, 3
        count_all_unpinned = self.db.count_unpinned_older_than(None)
        self.assertEqual(count_all_unpinned, 3)

        # Count older than 500 seconds: 0 items
        count_none = self.db.count_unpinned_older_than(now - 500)
        self.assertEqual(count_none, 0)

    def test_delete_unpinned_older_than_with_cutoff(self):
        """Verify deletion of unpinned items older than cutoff while preserving newer unpinned items."""
        now = time.time()
        self.db.save_item("u1", "Delete me 1", now - 200, pinned=False)
        self.db.save_item("u2", "Delete me 2", now - 100, pinned=False)
        self.db.save_item("u3", "Keep me unpinned", now - 10, pinned=False)
        self.db.save_item("p1", "Keep me pinned", now - 300, pinned=True)

        deleted = self.db.delete_unpinned_older_than(now - 50)
        self.assertEqual(deleted, 2)

        remaining = self.db.load_history()
        remaining_ids = {item["id"] for item in remaining}
        self.assertEqual(remaining_ids, {"u3", "p1"})

    def test_pinned_items_never_deleted_on_all_unpinned(self):
        """Verify that 'All Unpinned' cleanup preserves 100% of pinned items regardless of age."""
        now = time.time()
        for i in range(5):
            self.db.save_item(f"p_{i}", f"Pinned {i}", now - (i * 1000), pinned=True)
        for i in range(5):
            self.db.save_item(f"u_{i}", f"Unpinned {i}", now - (i * 1000), pinned=False)

        deleted = self.db.delete_unpinned_older_than(None)
        self.assertEqual(deleted, 5)

        remaining = self.db.load_history()
        self.assertEqual(len(remaining), 5)
        for item in remaining:
            self.assertTrue(item["pinned"])
            self.assertTrue(item["id"].startswith("p_"))

    def test_clipboard_service_bulk_cleanup_memory_sync(self):
        """Verify ClipboardService synchronizes both SQLite storage and in-memory history."""
        # Instantiate ClipboardService using dummy/standalone mode
        service = ClipboardService(parent=None)
        # Override db with our test db
        service._db = self.db
        now = time.time()
        service.history = [
            {"id": "p1", "text": "Pinned", "timestamp": now - 300, "pinned": True},
            {"id": "u1", "text": "Old Unpinned", "timestamp": now - 200, "pinned": False},
            {"id": "u2", "text": "Recent Unpinned", "timestamp": now - 10, "pinned": False},
        ]
        self.db.save_item("p1", "Pinned", now - 300, pinned=True)
        self.db.save_item("u1", "Old Unpinned", now - 200, pinned=False)
        self.db.save_item("u2", "Recent Unpinned", now - 10, pinned=False)

        count = service.count_unpinned_older_than(now - 100)
        self.assertEqual(count, 1)

        deleted = service.delete_unpinned_older_than(now - 100)
        self.assertEqual(deleted, 1)

        history_ids = [item["id"] for item in service.history]
        self.assertEqual(history_ids, ["p1", "u2"])

        db_ids = [item["id"] for item in self.db.load_history()]
        self.assertEqual(set(db_ids), {"p1", "u2"})

    def test_clipboard_service_last_text_updated_after_cleanup(self):
        """Cleanup must reset _last_text so copying the deleted string again is not dropped."""
        service = ClipboardService(parent=None)
        service._db = self.db
        now = time.time()
        service.history = [
            {"id": "u1", "text": "Will Delete", "timestamp": now - 200, "pinned": False},
        ]
        self.db.save_item("u1", "Will Delete", now - 200, pinned=False)
        service._last_text = "Will Delete"
        service._worker._last_text = "Will Delete"

        service.delete_unpinned_older_than(None)
        self.assertEqual(service._last_text, "")
        self.assertEqual(service._worker._last_text, "")

        # Now re-copy the deleted text
        service._process_text("Will Delete")
        self.assertEqual(len(service.history), 1)
        self.assertEqual(service.history[0]["text"], "Will Delete")

    def test_database_service_error_handling_and_cache_preservation(self):
        """Database failure returns -1 and prevents in-memory cache desynchronization."""
        from unittest.mock import patch

        service = ClipboardService(parent=None)
        service._db = self.db
        service.history = [
            {"id": "u1", "text": "Keep If DB Fails", "timestamp": 1000.0, "pinned": False},
        ]

        with patch.object(self.db, "_connect", side_effect=OSError("Disk failure")):
            res = self.db.delete_unpinned_older_than(None)
            self.assertEqual(res, -1)

            service_res = service.delete_unpinned_older_than(None)
            self.assertEqual(service_res, -1)
            # Memory cache must not have been purged
            self.assertEqual(len(service.history), 1)


if __name__ == "__main__":
    unittest.main()
