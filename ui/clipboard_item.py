"""
ui/clipboard_item.py
---------------------
Performance-optimised clipboard card widget.

PERFORMANCE FIXES VS PREVIOUS VERSION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. REMOVED resizeEvent → _elide_preview() cascade.
   Old code: resizeEvent called _elide_preview() which called setText()
   which triggered a layout pass which triggered ANOTHER resizeEvent.
   This infinite-loop was the #1 cause of UI sluggishness.

   New code: Preview text is computed ONCE in __init__ and never changed.
   We use a fixed character limit + "…" truncation instead of pixel-level
   QFontMetrics elision. This is simpler and eliminates the resize cascade.

2. Copy-back now calls service.set_ignore_next() BEFORE writing to
   QClipboard, preventing the feedback loop where our own clipboard
   write triggers a new card.

3. Widget cleanup: deleteLater() is called by MainWindow, and we
   don't hold any circular references.

Layout:
  ┌──────────────────────────────────────────────┐
  │  [preview text…]                [Copy] [✕]   │
  │  10:32:15  3 lines                           │
  └──────────────────────────────────────────────┘
"""

from datetime import datetime
import time

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Max characters in the preview text.
# This is a CHARACTER limit, not a pixel limit.
# At 13px font in a ~500px window with ~90px for buttons, ~55 chars fit.
_MAX_PREVIEW_CHARS = 55


class ClipboardItemWidget(QFrame):
    """
    Lightweight dark card for a single clipboard entry.

    Signals
    -------
    delete_requested(str)
        Emitted when the user clicks the Delete button. Carries the item_id.
    pin_toggled(str, bool)
        Emitted when the user toggles the Pin button. Carries the item_id and the new pinned state.
    """

    delete_requested = pyqtSignal(str)
    pin_toggled = pyqtSignal(str, bool)

    def __init__(self, item_id: str, text: str, timestamp: float = None, pinned: bool = False, parent=None):
        super().__init__(parent)

        self._id = item_id
        self._full_text = text
        self._timestamp = timestamp or time.time()
        self._pinned = pinned

        self.setObjectName("clipItem")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(64)

        # Build the UI ONCE — no rebuilds, no resize recalculations
        self._build_ui(text)

    # ------------------------------------------------------------------
    # UI construction (called exactly once)
    # ------------------------------------------------------------------

    def _build_ui(self, text: str):
        """Build the card layout. Called once in __init__."""

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 6, 8, 6)
        outer.setSpacing(8)

        # ── Left: text preview + meta ─────────────────────────────────
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        # Compute the preview string ONCE (never recomputed)
        preview, line_count = self._make_preview(text)

        preview_label = QLabel(preview)
        preview_label.setObjectName("itemText")
        preview_label.setWordWrap(False)
        preview_label.setTextFormat(Qt.TextFormat.PlainText)
        preview_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed
        )
        preview_label.setMinimumWidth(0)  # Allows shrinking below default text width
        preview_label.setFixedHeight(18)  # Strict fixed height prevents layout oscillation

        # Meta row
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        meta_row.setContentsMargins(0, 0, 0, 0)

        dt = datetime.fromtimestamp(self._timestamp)
        ts = QLabel(dt.strftime("%H:%M:%S"))
        ts.setObjectName("itemTime")
        ts.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        ts.setFixedHeight(16)  # Strict height
        meta_row.addWidget(ts)

        if line_count > 1:
            badge = QLabel(f"{line_count} lines")
            badge.setObjectName("lineBadge")
            badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            badge.setFixedHeight(16)  # Strict height
            meta_row.addWidget(badge)

        meta_row.addStretch()

        text_col.addWidget(preview_label)
        text_col.addLayout(meta_row)

        # ── Right: buttons container (strictly fixed size) ────────────
        btn_container = QWidget()
        btn_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_container.setFixedSize(112, 26)

        btn_row = QHBoxLayout(btn_container)
        btn_row.setSpacing(4)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setObjectName("pinBtn")
        self._pin_btn.setFixedSize(28, 26)
        self._pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pin_btn.setToolTip("Pin/Unpin item")
        self._pin_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._pin_btn.clicked.connect(self._on_pin_toggle)

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setObjectName("copyBtn")
        self._copy_btn.setFixedSize(48, 26)
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setToolTip("Copy back to clipboard")
        self._copy_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._copy_btn.clicked.connect(self._on_copy)

        self._del_btn = QPushButton("✕")
        self._del_btn.setObjectName("deleteBtn")
        self._del_btn.setFixedSize(28, 26)
        self._del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._del_btn.setToolTip("Remove from history")
        self._del_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._del_btn.clicked.connect(self._on_delete)

        self._update_pin_visual()

        btn_row.addWidget(self._pin_btn)
        btn_row.addWidget(self._copy_btn)
        btn_row.addWidget(self._del_btn)

        # ── Assemble ──────────────────────────────────────────────────
        outer.addLayout(text_col, stretch=1)
        outer.addWidget(btn_container)

    # ------------------------------------------------------------------
    # Preview builder (pure function, no side effects)
    # ------------------------------------------------------------------

    @staticmethod
    def _make_preview(text: str) -> tuple[str, int]:
        """
        Build a single-line preview and count original lines.
        Called ONCE per card — never recomputed.
        """
        lines = text.splitlines()
        line_count = len(lines)

        # Join non-empty lines with a visible separator
        joined = " · ".join(line.strip() for line in lines if line.strip())

        # Character-level truncation
        if len(joined) > _MAX_PREVIEW_CHARS:
            joined = joined[:_MAX_PREVIEW_CHARS].rstrip() + "…"

        return joined or text[:_MAX_PREVIEW_CHARS], line_count

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_copy(self):
        """Copy text back to clipboard with feedback loop prevention."""
        # Tell the service to ignore the next clipboard change
        # (our own write should NOT create a new card)
        clipboard = QApplication.clipboard()

        # Walk up to MainWindow to get the service reference
        window = self.window()
        if hasattr(window, "_service"):
            window._service.set_ignore_next(self._full_text)

        clipboard.setText(self._full_text)
        self._flash_copy_btn()

    def _on_delete(self):
        """Signal MainWindow to remove this card by ID."""
        self.delete_requested.emit(self._id)

    def _on_pin_toggle(self):
        """Toggle pinned status and notify window/service."""
        self._pinned = not self._pinned
        self._update_pin_visual()
        self.pin_toggled.emit(self._id, self._pinned)

    def _update_pin_visual(self):
        """Sync button and card stylesheet properties with pinned state."""
        self._pin_btn.setProperty("pinned", self._pinned)
        self._pin_btn.style().unpolish(self._pin_btn)
        self._pin_btn.style().polish(self._pin_btn)
        self._pin_btn.update()

        self.setProperty("pinned", self._pinned)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _flash_copy_btn(self):
        """Brief green flash on the Copy button."""
        self._copy_btn.setText("✓")
        self._copy_btn.setStyleSheet(
            "background-color:#2D6A4F; color:#B7E4C7; border:none; "
            "border-radius:5px; font-size:12px;"
        )
        QTimer.singleShot(600, self._reset_copy_btn)

    def _reset_copy_btn(self):
        """Restore Copy button to stylesheet-driven look."""
        self._copy_btn.setText("Copy")
        self._copy_btn.setStyleSheet("")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """The stable unique ID of this card."""
        return self._id

    @property
    def full_text(self) -> str:
        """The full original text stored in this card."""
        return self._full_text

    @property
    def pinned(self) -> bool:
        """Whether this card is pinned."""
        return self._pinned

    @property
    def timestamp(self) -> float:
        """The timestamp of this card."""
        return self._timestamp

    def matches(self, query: str) -> bool:
        """Case-insensitive search match."""
        return query.lower() in self._full_text.lower()
