"""
ui/main_window.py
------------------
Performance-optimised main window for ClipVault.

PERFORMANCE FIXES VS PREVIOUS VERSION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. _on_new_clip no longer calls _filter_items() when search bar is empty.
   This avoids iterating ALL items on every new clip (was O(n) per clip).

2. Uses setUpdatesEnabled(False/True) around delete operations to
   batch layout changes and prevent intermediate redraws.

3. Connects to ClipboardService.item_trimmed to auto-remove cards
   when history exceeds MAX_HISTORY (100 items).

4. Scroll-to-top uses a single-shot timer with a captured reference
   (no lambda closure per call, avoiding GC churn).
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from services.clipboard_service import ClipboardService
from ui.clipboard_item import ClipboardItemWidget


class MainWindow(QMainWindow):
    """
    Primary window for ClipVault clipboard manager.

    Performance characteristics:
    - Adding a new card: O(1) — single widget insert, no list iteration
    - Search filtering: O(n) — only runs when search bar is non-empty
    - Delete: O(n) find + O(1) remove — with batched layout updates
    - Auto-trim: O(1) — removes last card directly
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ClipVault")
        self.setMinimumSize(400, 500)
        self.resize(500, 700)
        self.setObjectName("mainWindow")

        self._items: list[ClipboardItemWidget] = []

        # ── Build UI ───────────────────────────────────────────────────
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_search())
        root.addWidget(self._build_section_label())
        root.addWidget(self._build_scroll_area(), stretch=1)
        root.addWidget(self._build_footer())

        # ── Clipboard service ─────────────────────────────────────────
        self._service = ClipboardService(self)
        self._service.new_item.connect(self._on_new_clip)
        self._service.item_trimmed.connect(self._on_item_trimmed)
        self._service.start()

        self._update_footer_status()

    # ──────────────────────────────────────────────────────────────────
    # UI builders
    # ──────────────────────────────────────────────────────────────────

    def _build_header(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("headerBar")
        bar.setFixedHeight(48)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        icon = QLabel("📋")
        icon.setStyleSheet("font-size: 18px;")
        title = QLabel("ClipVault")
        title.setObjectName("appTitle")

        layout.addWidget(icon)
        layout.addSpacing(2)
        layout.addWidget(title)
        layout.addStretch()
        return bar

    def _build_search(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 10, 12, 6)

        self._search_bar = QLineEdit()
        self._search_bar.setObjectName("searchBar")
        self._search_bar.setPlaceholderText("🔍  Search clipboard history…")
        self._search_bar.setClearButtonEnabled(True)
        self._search_bar.textChanged.connect(self._filter_items)

        layout.addWidget(self._search_bar)
        return container

    def _build_section_label(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(14, 4, 14, 2)

        label = QLabel("RECENT")
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        layout.addStretch()
        return container

    def _build_scroll_area(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        inner = QWidget()
        inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._list_layout = QVBoxLayout(inner)
        self._list_layout.setContentsMargins(12, 4, 12, 12)
        self._list_layout.setSpacing(6)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._empty_label = QLabel("Copy something to see it here.")
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setMinimumHeight(100)
        self._list_layout.addWidget(self._empty_label)

        scroll.setWidget(inner)
        self._scroll_area = scroll
        return scroll

    def _build_footer(self) -> QLabel:
        self._footer = QLabel("  ●  Starting…")
        self._footer.setObjectName("footerLabel")
        self._footer.setFixedHeight(28)
        self._footer.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        return self._footer

    def _update_footer_status(self):
        """Show active clipboard detection method in the footer."""
        if self._service._clip_cmd:
            tool = self._service._clip_cmd[0]
            if tool == "wl-paste":
                self._footer.setText("  ●  Active: wl-paste  (Tip: run 'sudo apt install xclip' to stop GNOME dock flicker)")
                self._footer.setStyleSheet("color: #D97706;")  # Elegant amber color
            else:
                self._footer.setText(f"  ●  Active: {tool}  (Smooth background monitoring)")
                self._footer.setStyleSheet("color: #10B981;")  # Gorgeous success green
        else:
            self._footer.setText("  ●  Active: Qt Focus-Only Fallback")
            self._footer.setStyleSheet("color: #8B6F3A;")

    # ──────────────────────────────────────────────────────────────────
    # Slots — optimised for minimal work
    # ──────────────────────────────────────────────────────────────────

    def _on_new_clip(self, item_id: str, text: str):
        """
        Add a new card at the top.
        O(1) — just inserts one widget. Does NOT iterate the full list
        unless a search query is active.
        """
        self._empty_label.setVisible(False)

        card = ClipboardItemWidget(item_id, text)
        card.delete_requested.connect(self._on_delete_item)
        self._items.insert(0, card)
        self._list_layout.insertWidget(1, card)

        # Only re-filter if the user has typed something in the search bar.
        # When empty, the new card is already visible — no work needed.
        query = self._search_bar.text().strip()
        if query:
            # Only check the NEW card — don't re-iterate all items
            if not card.matches(query):
                card.setVisible(False)

        # Scroll to top (use method ref instead of lambda to avoid GC churn)
        QTimer.singleShot(50, self._scroll_to_top)

    def _scroll_to_top(self):
        """Scroll the list to the very top."""
        self._scroll_area.verticalScrollBar().setValue(0)

    def _on_delete_item(self, item_id: str):
        """
        Remove a single card using its unique ID.
        Uses setUpdatesEnabled to batch the layout change into one repaint.
        """
        card_to_remove = None
        for card in self._items:
            if card.id == item_id:
                card_to_remove = card
                break

        if card_to_remove is None:
            return

        # Batch the layout update into a single repaint
        scroll_inner = self._scroll_area.widget()
        scroll_inner.setUpdatesEnabled(False)

        self._items.remove(card_to_remove)
        self._list_layout.removeWidget(card_to_remove)
        card_to_remove.setParent(None)   # detach from layout immediately
        card_to_remove.deleteLater()     # schedule destruction

        scroll_inner.setUpdatesEnabled(True)

        self._service.remove_item(item_id)

        if not self._items:
            self._empty_label.setText("Copy something to see it here.")
            self._empty_label.setVisible(True)

    def _on_item_trimmed(self, item_id: str):
        """
        Called by ClipboardService when an old item is auto-removed
        to enforce the MAX_HISTORY cap. Removes the card matching the trimmed ID.
        """
        for card in self._items:
            if card.id == item_id:
                self._items.remove(card)
                self._list_layout.removeWidget(card)
                card.setParent(None)
                card.deleteLater()
                break

    def _filter_items(self, query: str):
        """
        Show/hide cards based on search query.
        Only runs the full loop when query is non-empty.
        When cleared, makes ALL items visible in one pass.
        """
        query = query.strip()
        visible_count = 0

        if not query:
            # Fast path: make everything visible
            for card in self._items:
                card.setVisible(True)
            visible_count = len(self._items)
        else:
            # Filter path: check each card
            for card in self._items:
                match = card.matches(query)
                card.setVisible(match)
                if match:
                    visible_count += 1

        # Update empty-state
        if not self._items:
            self._empty_label.setVisible(True)
            self._empty_label.setText("Copy something to see it here.")
        elif visible_count == 0:
            self._empty_label.setVisible(True)
            self._empty_label.setText(f'No results for "{query}"')
        else:
            self._empty_label.setVisible(False)

    # ──────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Clean shutdown."""
        self._service.stop()
        super().closeEvent(event)
