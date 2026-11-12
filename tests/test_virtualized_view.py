"""
tests/test_virtualized_view.py
------------------------------
Unit and integration tests for virtualized QListView, ClipboardModel,
and ClipboardItemDelegate.
"""

import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt, QModelIndex, QPoint, QEvent
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication

from ui.clipboard_model import (
    ClipboardModel,
    ClipboardProxyModel,
    ItemIdRole,
    FullTextRole,
    TimestampRole,
    PinnedRole,
    LineCountRole,
    PreviewRole,
)
from ui.clipboard_delegate import ClipboardItemDelegate


class TestClipboardModel(unittest.TestCase):
    """Test data storage, roles, and mutations in ClipboardModel."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.model = ClipboardModel()

    def test_empty_model(self):
        """Model starts empty."""
        self.assertEqual(self.model.rowCount(), 0)

    def test_add_item(self):
        """Adding item exposes correct data roles."""
        self.model.add_item("id1", "Hello World", 100.0, pinned=False)
        self.assertEqual(self.model.rowCount(), 1)

        idx = self.model.index(0, 0)
        self.assertEqual(self.model.data(idx, ItemIdRole), "id1")
        self.assertEqual(self.model.data(idx, FullTextRole), "Hello World")
        self.assertEqual(self.model.data(idx, PinnedRole), False)
        self.assertEqual(self.model.data(idx, LineCountRole), 1)

    def test_add_multiline_item_counts_lines(self):
        """Multiline text correctly counts original lines."""
        self.model.add_item("id2", "Line 1\nLine 2\nLine 3", 101.0, pinned=False)
        idx = self.model.index(0, 0)
        self.assertEqual(self.model.data(idx, LineCountRole), 3)

    def test_remove_item(self):
        """Removing item by ID updates row count."""
        self.model.add_item("id1", "Item 1", 100.0, pinned=False)
        self.model.add_item("id2", "Item 2", 101.0, pinned=False)
        self.assertEqual(self.model.rowCount(), 2)

        removed = self.model.remove_item("id1")
        self.assertTrue(removed)
        self.assertEqual(self.model.rowCount(), 1)
        self.assertEqual(self.model.data(self.model.index(0, 0), ItemIdRole), "id2")

    def test_set_pinned(self):
        """Toggling pin state re-sorts model with pinned items first."""
        self.model.add_item("id1", "Item 1", 100.0, pinned=False)
        self.model.add_item("id2", "Item 2", 200.0, pinned=False)

        # Pin id1 (which has older timestamp)
        self.model.set_item_pinned("id1", True)

        # id1 should now be at index 0 because it is pinned
        idx0 = self.model.index(0, 0)
        idx1 = self.model.index(1, 0)
        self.assertEqual(self.model.data(idx0, ItemIdRole), "id1")
        self.assertTrue(self.model.data(idx0, PinnedRole))
        self.assertEqual(self.model.data(idx1, ItemIdRole), "id2")
        self.assertFalse(self.model.data(idx1, PinnedRole))


class TestClipboardProxyModel(unittest.TestCase):
    """Test search filtering and ordering in ClipboardProxyModel."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.source_model = ClipboardModel()
        self.proxy = ClipboardProxyModel()
        self.proxy.setSourceModel(self.source_model)

        self.source_model.add_item("id1", "Apple Banana", 100.0, pinned=False)
        self.source_model.add_item("id2", "Banana Cherry", 200.0, pinned=False)
        self.source_model.add_item("id3", "Dragonfruit", 300.0, pinned=True)

    def test_filter_matches_query(self):
        """Searching filters items case-insensitively."""
        self.proxy.set_filter_query("banana")
        self.assertEqual(self.proxy.rowCount(), 2)

        self.proxy.set_filter_query("dragon")
        self.assertEqual(self.proxy.rowCount(), 1)
        self.assertEqual(self.proxy.data(self.proxy.index(0, 0), ItemIdRole), "id3")

    def test_empty_filter_shows_all(self):
        """Empty query displays all items."""
        self.proxy.set_filter_query("")
        self.assertEqual(self.proxy.rowCount(), 3)


class TestClipboardItemDelegate(unittest.TestCase):
    """Test geometry and interactions in ClipboardItemDelegate."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.delegate = ClipboardItemDelegate()

    def test_size_hint(self):
        """Delegate maintains fixed 64px card height."""
        from PyQt6.QtWidgets import QStyleOptionViewItem
        option = QStyleOptionViewItem()
        option.rect.setWidth(400)
        size = self.delegate.sizeHint(option, QModelIndex())
        self.assertEqual(size.height(), 64)


class TestMainWindowVirtualized(unittest.TestCase):
    """Integration tests for MainWindow using virtualized list view."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    @patch("services.clipboard_service.DatabaseService")
    def test_main_window_lifecycle(self, mock_db_cls):
        """Verify adding, filtering, pinning, and deleting items in MainWindow."""
        from ui.main_window import MainWindow

        mock_db = MagicMock()
        mock_db.load_history.return_value = []
        mock_db_cls.return_value = mock_db

        window = MainWindow()
        window.show()

        # Initially empty
        self.assertEqual(window._model.rowCount(), 0)
        self.assertFalse(window._empty_label.isHidden())
        self.assertTrue(window._list_view.isHidden())

        # Add 2 clips
        window._on_new_clip("c1", "First clipboard text", 100.0)
        window._on_new_clip("c2", "Second clipboard note", 200.0)

        self.assertEqual(window._model.rowCount(), 2)
        self.assertTrue(window._empty_label.isHidden())
        self.assertFalse(window._list_view.isHidden())

        # Test filter
        window._search_bar.setText("first")
        self.assertEqual(window._proxy_model.rowCount(), 1)

        # Clear filter
        window._search_bar.setText("")
        self.assertEqual(window._proxy_model.rowCount(), 2)

        # Test pin
        window._on_pin_toggled("c1", True)
        first_id = window._model.data(window._model.index(0, 0), ItemIdRole)
        self.assertEqual(first_id, "c1")

        # Test delete
        window._on_delete_item("c1")
        self.assertEqual(window._model.rowCount(), 1)

        window.close()


if __name__ == "__main__":
    unittest.main()
