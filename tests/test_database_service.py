"""
tests/test_database_service.py
------------------------------
Unit tests for DatabaseService including WAL mode persistence.
"""

import os
import sqlite3
import unittest
from unittest.mock import patch

from services.database_service import DatabaseService


class TestDatabaseService(unittest.TestCase):
    """Test SQLite operations and WAL mode in DatabaseService."""

    def setUp(self):
        self.test_db = "test_clipvault.db"
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.test_db_path = os.path.join(project_root, self.test_db)
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def tearDown(self):
        for ext in ["", "-wal", "-shm"]:
            path = self.test_db_path + ext
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def test_snap_user_data_path_resolution(self):
        """DatabaseService uses SNAP_USER_DATA when running inside a snap package."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"SNAP_USER_DATA": tmpdir}):
                service = DatabaseService(db_filename="snap_test.db")
                expected = os.path.join(tmpdir, "snap_test.db")
                self.assertEqual(service.db_path, expected)
                self.assertTrue(os.path.exists(expected))

    def test_wal_mode_enabled(self):
        """DatabaseService must configure SQLite journal_mode to WAL."""
        service = DatabaseService(db_filename=self.test_db)
        with sqlite3.connect(service.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
        self.assertEqual(mode.lower(), "wal")

    def test_save_and_load_items(self):
        """Items must be saved and loaded in correct order (pinned first)."""
        service = DatabaseService(db_filename=self.test_db)
        service.save_item("id1", "First Unpinned", 1000.0, pinned=False)
        service.save_item("id2", "Second Pinned", 1001.0, pinned=True)
        service.save_item("id3", "Third Unpinned", 1002.0, pinned=False)

        history = service.load_history()
        self.assertEqual(len(history), 3)
        # Pinned item should be first
        self.assertEqual(history[0]["id"], "id2")
        self.assertTrue(history[0]["pinned"])
        # Next should be newest unpinned
        self.assertEqual(history[1]["id"], "id3")
        self.assertEqual(history[2]["id"], "id1")

    def test_set_pinned(self):
        """Updating pin state persists in database."""
        service = DatabaseService(db_filename=self.test_db)
        service.save_item("id1", "Note", 1000.0, pinned=False)
        service.set_pinned("id1", True)

        history = service.load_history()
        self.assertTrue(history[0]["pinned"])

    def test_prune_old_items(self):
        """Pruning deletes old unpinned items and preserves pinned items."""
        service = DatabaseService(db_filename=self.test_db)
        service.save_item("pin1", "Pinned Old", 100.0, pinned=True)
        for i in range(10):
            service.save_item(f"item{i}", f"Text {i}", 200.0 + i, pinned=False)

        service.prune_old_items(keep_limit=5)
        history = service.load_history()
        # 1 pinned + 5 unpinned = 6
        self.assertEqual(len(history), 6)
        ids = [item["id"] for item in history]
        self.assertIn("pin1", ids)


if __name__ == "__main__":
    unittest.main()
