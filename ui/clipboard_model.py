"""
ui/clipboard_model.py
---------------------
High-performance Qt ListModel and QSortFilterProxyModel for virtualized clipboard items.
Avoids widget allocation overhead by representing items as pure data.
"""

from datetime import datetime
from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex, QSortFilterProxyModel

# Custom roles for item data
ItemIdRole = Qt.ItemDataRole.UserRole + 1
FullTextRole = Qt.ItemDataRole.UserRole + 2
TimestampRole = Qt.ItemDataRole.UserRole + 3
PinnedRole = Qt.ItemDataRole.UserRole + 4
LineCountRole = Qt.ItemDataRole.UserRole + 5
PreviewRole = Qt.ItemDataRole.UserRole + 6
TimeStrRole = Qt.ItemDataRole.UserRole + 7

_MAX_PREVIEW_CHARS = 55


def make_preview(text: str, max_chars: int = _MAX_PREVIEW_CHARS) -> tuple[str, int]:
    """
    Build single-line preview string and count original lines.
    Calculated once per item.
    """
    if not text:
        return "", 1
    lines = text.splitlines()
    line_count = len(lines) if lines else 1
    joined = " · ".join(line.strip() for line in lines if line.strip())
    if len(joined) > max_chars:
        joined = joined[:max_chars].rstrip() + "…"
    return joined or text[:max_chars], line_count


class ClipboardModel(QAbstractListModel):
    """
    Core data model storing clipboard history items for QListView.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict] = []

    def rowCount(self, parent=None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item = self._items[index.row()]

        if role in (Qt.ItemDataRole.DisplayRole, PreviewRole):
            return item["preview"]
        if role == ItemIdRole:
            return item["id"]
        if role == FullTextRole:
            return item["text"]
        if role == TimestampRole:
            return item["timestamp"]
        if role == PinnedRole:
            return item["pinned"]
        if role == LineCountRole:
            return item["line_count"]
        if role == TimeStrRole:
            return item["time_str"]

        return None

    def add_item(self, item_id: str, text: str, timestamp: float, pinned: bool = False):
        """Add a single clipboard item and maintain correct sorting."""
        preview, line_count = make_preview(text)
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

        new_entry = {
            "id": item_id,
            "text": text,
            "timestamp": timestamp,
            "pinned": pinned,
            "preview": preview,
            "line_count": line_count,
            "time_str": time_str,
        }

        self.beginResetModel()
        self._items.insert(0, new_entry)
        self._sort_items()
        self.endResetModel()

    def remove_item(self, item_id: str) -> bool:
        """Remove an item by unique ID."""
        for row, item in enumerate(self._items):
            if item["id"] == item_id:
                self.beginRemoveRows(QModelIndex(), row, row)
                del self._items[row]
                self.endRemoveRows()
                return True
        return False

    def set_item_pinned(self, item_id: str, pinned: bool):
        """Update pinned state and re-sort."""
        for item in self._items:
            if item["id"] == item_id:
                item["pinned"] = pinned
                break

        self.beginResetModel()
        self._sort_items()
        self.endResetModel()

    def load_items(self, items: list[dict]):
        """Load history items in batch."""
        self.beginResetModel()
        self._items = []
        for item in items:
            preview, line_count = make_preview(item["text"])
            ts = item.get("timestamp", 0.0)
            self._items.append({
                "id": item["id"],
                "text": item["text"],
                "timestamp": ts,
                "pinned": item.get("pinned", False),
                "preview": preview,
                "line_count": line_count,
                "time_str": datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "",
            })
        self._sort_items()
        self.endResetModel()

    def get_item_by_id(self, item_id: str) -> dict | None:
        """Look up item by ID."""
        for item in self._items:
            if item["id"] == item_id:
                return item
        return None

    def _sort_items(self):
        """Sort items: pinned items first (newest to oldest), then unpinned (newest to oldest)."""
        self._items.sort(
            key=lambda x: (x.get("pinned", False), x.get("timestamp", 0.0)),
            reverse=True,
        )


class ClipboardProxyModel(QSortFilterProxyModel):
    """
    Search filter proxy model for ClipboardModel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = ""

    def set_filter_query(self, query: str):
        """Set search query and refresh filter."""
        self._query = query.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._query:
            return True

        model = self.sourceModel()
        if not model:
            return True

        idx = model.index(source_row, 0, source_parent)
        full_text = model.data(idx, FullTextRole)
        if not full_text:
            return False

        return self._query in full_text.lower()
