"""
tests/test_clipboard_model_cleanup.py
--------------------------------------
Unit tests for bulk unpinned cleanup in ClipboardModel.
"""

import time
import unittest
from PyQt6.QtWidgets import QApplication

from ui.clipboard_model import ClipboardModel, ClipboardProxyModel


class TestClipboardModelCleanup(unittest.TestCase):
    """Test bulk unpinned removal and count helpers in ClipboardModel."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.model = ClipboardModel()
        self.proxy = ClipboardProxyModel()
        self.proxy.setSourceModel(self.model)

    def test_model_count_unpinned_older_than(self):
        """Verify accurate counting of unpinned items matching timestamp cutoff."""
        now = time.time()
        self.model.load_items([
            {"id": "p1", "text": "Pinned item", "timestamp": now - 300, "pinned": True},
            {"id": "u1", "text": "Old item 1", "timestamp": now - 200, "pinned": False},
            {"id": "u2", "text": "Old item 2", "timestamp": now - 100, "pinned": False},
            {"id": "u3", "text": "Recent item", "timestamp": now - 10, "pinned": False},
        ])

        # Older than 50 seconds: u1 and u2 (u3 is newer, p1 is pinned)
        self.assertEqual(self.model.count_unpinned_older_than(now - 50), 2)
        # All unpinned: u1, u2, u3
        self.assertEqual(self.model.count_unpinned_older_than(None), 3)
        # Older than 500 seconds: 0
        self.assertEqual(self.model.count_unpinned_older_than(now - 500), 0)

    def test_model_remove_unpinned_with_cutoff(self):
        """Verify removal of unpinned items older than cutoff while keeping newer and pinned items."""
        now = time.time()
        self.model.load_items([
            {"id": "p1", "text": "Pinned item", "timestamp": now - 300, "pinned": True},
            {"id": "u1", "text": "Old item 1", "timestamp": now - 200, "pinned": False},
            {"id": "u2", "text": "Old item 2", "timestamp": now - 100, "pinned": False},
            {"id": "u3", "text": "Recent item", "timestamp": now - 10, "pinned": False},
        ])

        removed = self.model.remove_unpinned_older_than(now - 50)
        self.assertEqual(removed, 2)
        self.assertEqual(self.model.rowCount(), 2)

        remaining_ids = [self.model._items[i]["id"] for i in range(self.model.rowCount())]
        self.assertEqual(remaining_ids, ["p1", "u3"])
        self.assertEqual(self.proxy.rowCount(), 2)

    def test_model_remove_all_unpinned(self):
        """Verify removing all unpinned items retains only pinned items."""
        now = time.time()
        self.model.load_items([
            {"id": "p1", "text": "Pinned 1", "timestamp": now - 50, "pinned": True},
            {"id": "p2", "text": "Pinned 2", "timestamp": now - 20, "pinned": True},
            {"id": "u1", "text": "Unpinned 1", "timestamp": now - 10, "pinned": False},
            {"id": "u2", "text": "Unpinned 2", "timestamp": now - 5, "pinned": False},
        ])

        removed = self.model.remove_unpinned_older_than(None)
        self.assertEqual(removed, 2)
        self.assertEqual(self.model.rowCount(), 2)
        for i in range(self.model.rowCount()):
            self.assertTrue(self.model._items[i]["pinned"])

    def test_model_remove_when_no_match(self):
        """Verify zero removals when no unpinned items match cutoff."""
        now = time.time()
        self.model.load_items([
            {"id": "u1", "text": "Recent unpinned", "timestamp": now - 10, "pinned": False},
        ])

        removed = self.model.remove_unpinned_older_than(now - 100)
        self.assertEqual(removed, 0)
        self.assertEqual(self.model.rowCount(), 1)


if __name__ == "__main__":
    unittest.main()
