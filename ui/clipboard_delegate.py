"""
ui/clipboard_delegate.py
Custom QStyledItemDelegate for rendering clipboard item cards inside QListView.
Renders cards, badges, and action buttons dynamically using theme palettes.
"""

from PyQt6.QtCore import Qt, QRect, QSize, QEvent, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem

from ui.clipboard_model import (
    ItemIdRole,
    FullTextRole,
    PinnedRole,
    LineCountRole,
    PreviewRole,
    TimeStrRole,
)
from ui.styles import (
    DEFAULT_COLOR_SCHEME,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_STYLE,
    DELEGATE_PALETTES,
    FONT_STYLE_OPTIONS,
    clamp_font_size,
    get_delegate_palette,
    normalize_color_scheme,
    normalize_font_style,
    resolve_qt_font_family,
    sanitize_font_family,
)


class ClipboardItemDelegate(QStyledItemDelegate):
    """
    Renders high-performance theme-aware clipboard cards.
    Handles pin, copy, and delete actions directly from paint events and editorEvents.
    """

    pin_requested = pyqtSignal(str, bool)       # (item_id, new_pinned)
    copy_requested = pyqtSignal(str, str)      # (item_id, full_text)
    delete_requested = pyqtSignal(str)         # (item_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._copied_item_id: str | None = None
        self._hovered_btn: tuple[str, str] | None = None  # (item_id, "pin"|"copy"|"delete")
        self._theme_name = "dark"
        self._color_scheme = DEFAULT_COLOR_SCHEME
        self._palette = DELEGATE_PALETTES["dark"]
        self._font_family = DEFAULT_FONT_FAMILY
        self._font_size = DEFAULT_FONT_SIZE
        self._font_style = DEFAULT_FONT_STYLE

    def set_theme(self, theme_name: str, color_scheme: str | None = None):
        """Update active theme palette and optional color scheme for painting."""
        self._theme_name = theme_name if theme_name in DELEGATE_PALETTES else "dark"
        if color_scheme is not None:
            self._color_scheme = normalize_color_scheme(color_scheme)
        self._palette = get_delegate_palette(self._theme_name, self._color_scheme)

    def set_color_scheme(self, color_scheme: str):
        """Update active color scheme while preserving current light/dark mode."""
        self._color_scheme = normalize_color_scheme(color_scheme)
        self._palette = get_delegate_palette(self._theme_name, self._color_scheme)

    def set_font(
        self,
        font_family: str = DEFAULT_FONT_FAMILY,
        font_size: int = DEFAULT_FONT_SIZE,
        font_style: str = DEFAULT_FONT_STYLE,
    ):
        """Update font family, pixel size, and style used for card painting."""
        self._font_family = sanitize_font_family(font_family)
        self._font_size = clamp_font_size(font_size)
        self._font_style = normalize_font_style(font_style)

    def _build_font(
        self,
        size_offset: int = 0,
        force_bold: bool = False,
        respect_style: bool = True,
    ) -> QFont:
        """Construct a QFont scaled from the configured base font settings."""
        qt_family = resolve_qt_font_family(self._font_family)
        base_pt = max(7, self._font_size - 3)
        pt_size = max(6, base_pt + size_offset)
        font = QFont(qt_family, pt_size)

        if respect_style:
            _, _, is_bold, is_italic = FONT_STYLE_OPTIONS[self._font_style]
            font.setBold(is_bold or force_bold)
            font.setItalic(is_italic)
        elif force_bold:
            font.setBold(True)
        return font

    @staticmethod
    def _button_rects(option_rect: QRect) -> tuple[QRect, QRect, QRect, QRect]:
        """Compute card rect and right-aligned action button rectangles."""
        rect = option_rect.adjusted(6, 3, -6, -3)
        btn_y = rect.y() + (rect.height() - 26) // 2
        pin_rect = QRect(rect.right() - 110, btn_y, 26, 26)
        copy_rect = QRect(rect.right() - 80, btn_y, 48, 26)
        del_rect = QRect(rect.right() - 28, btn_y, 26, 26)
        return rect, pin_rect, copy_rect, del_rect

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        extra_height = max(0, (self._font_size - DEFAULT_FONT_SIZE) * 3)
        return QSize(option.rect.width(), 64 + extra_height)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(6, 3, -6, -3)

        pinned = bool(index.data(PinnedRole))
        item_id = str(index.data(ItemIdRole) or "")
        preview = str(index.data(PreviewRole) or "")
        time_str = str(index.data(TimeStrRole) or "")
        line_count = int(index.data(LineCountRole) or 1)
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)

        p = self._palette

        # ── Background and Border ─────────────────────────────────────
        if pinned:
            bg_color = QColor(p["pinned_bg_hover"] if is_hovered else p["pinned_bg"])
            border_color = QColor(p["pinned_border_hover"] if is_hovered else p["pinned_border"])
        else:
            bg_color = QColor(p["unpinned_bg_hover"] if is_hovered else p["unpinned_bg"])
            border_color = QColor(p["unpinned_border_hover"] if is_hovered else p["unpinned_border"])

        if is_selected:
            bg_color = QColor(p["selected_bg"])

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 8, 8)

        # ── Left Column: Preview Text ─────────────────────────────────
        text_font = self._build_font(size_offset=0, respect_style=True)
        painter.setFont(text_font)
        painter.setPen(QPen(QColor(p["text_primary"])))

        metrics = painter.fontMetrics()
        text_height = max(20, metrics.height() + 4)
        text_rect = QRect(rect.x() + 12, rect.y() + 8, rect.width() - 135, text_height)
        elided_text = metrics.elidedText(preview, Qt.TextElideMode.ElideRight, text_rect.width())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_text)

        # ── Left Column: Metadata Row ─────────────────────────────────
        meta_y = rect.y() + 8 + text_height + 4
        time_font = self._build_font(size_offset=-2, respect_style=True)
        painter.setFont(time_font)
        painter.setPen(QPen(QColor(p["text_secondary"])))

        time_metrics = painter.fontMetrics()
        time_width = max(60, time_metrics.horizontalAdvance(time_str) + 12)
        meta_height = max(16, time_metrics.height() + 2)
        time_rect = QRect(rect.x() + 12, meta_y, time_width, meta_height)
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, time_str)

        if line_count > 1:
            badge_font = self._build_font(size_offset=-3, respect_style=True)
            painter.setFont(badge_font)
            badge_metrics = painter.fontMetrics()
            badge_text = f"{line_count} lines"
            badge_width = max(46, badge_metrics.horizontalAdvance(badge_text) + 12)
            max_badge_width = max(0, rect.right() - 118 - (rect.x() + 12 + time_width))
            if max_badge_width >= 36:
                badge_rect = QRect(
                    rect.x() + 12 + time_width,
                    meta_y,
                    min(badge_width, max_badge_width),
                    meta_height,
                )
                painter.setPen(QPen(QColor(p["badge_border"]), 1))
                painter.setBrush(QBrush(QColor(p["badge_bg"])))
                painter.drawRoundedRect(badge_rect, 4, 4)

                painter.setPen(QPen(QColor(p["badge_text"])))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        # ── Right Column: Buttons ─────────────────────────────────────
        _, pin_rect, copy_rect, del_rect = self._button_rects(option.rect)
        btn_family = resolve_qt_font_family(self._font_family)

        # 1. Pin Button (26x26)
        pin_hover = self._hovered_btn == (item_id, "pin")
        if pin_hover:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(p["pin_hover_bg"])))
            painter.drawRoundedRect(pin_rect, 5, 5)

        painter.setFont(QFont(btn_family, 10))
        pin_color = QColor(p["pin_active"] if pinned else (p["pin_hover"] if pin_hover else p["pin_inactive"]))
        painter.setPen(QPen(pin_color))
        painter.drawText(pin_rect, Qt.AlignmentFlag.AlignCenter, "📌")

        # 2. Copy Button (48x26)
        copy_hover = self._hovered_btn == (item_id, "copy")
        is_just_copied = self._copied_item_id == item_id

        if is_just_copied:
            copy_bg = QColor(p["copy_success_bg"])
            copy_fg = QColor(p["copy_success_fg"])
            copy_label = "✓"
        else:
            copy_bg = QColor(p["copy_bg_hover"] if copy_hover else p["copy_bg"])
            copy_fg = QColor(p["copy_fg_hover"] if copy_hover else p["copy_fg"])
            copy_label = "Copy"

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(copy_bg))
        painter.drawRoundedRect(copy_rect, 5, 5)

        painter.setFont(QFont(btn_family, 8, QFont.Weight.Bold if is_just_copied else QFont.Weight.Normal))
        painter.setPen(QPen(copy_fg))
        painter.drawText(copy_rect, Qt.AlignmentFlag.AlignCenter, copy_label)

        # 3. Delete Button (26x26)
        del_hover = self._hovered_btn == (item_id, "delete")
        if del_hover:
            painter.setPen(QPen(QColor(p["del_border_hover"]), 1))
            painter.setBrush(QBrush(QColor(p["del_bg_hover"])))
            del_fg = QColor(p["del_fg_hover"])
        else:
            painter.setPen(QPen(QColor(p["del_border"]), 1))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            del_fg = QColor(p["del_fg"])

        painter.drawRoundedRect(del_rect, 5, 5)
        painter.setFont(QFont(btn_family, 9, QFont.Weight.Bold))
        painter.setPen(QPen(del_fg))
        painter.drawText(del_rect, Qt.AlignmentFlag.AlignCenter, "✕")

        painter.restore()

    def editorEvent(self, event: QEvent, model, option: QStyleOptionViewItem, index) -> bool:
        """Handle mouse clicks on action buttons and cards."""
        rect, pin_rect, copy_rect, del_rect = self._button_rects(option.rect)

        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item_id = str(index.data(ItemIdRole) or "")
        full_text = str(index.data(FullTextRole) or "")
        pinned = bool(index.data(PinnedRole))

        if event.type() == QEvent.Type.MouseMove:
            prev_hover = self._hovered_btn
            if pin_rect.contains(pos):
                self._hovered_btn = (item_id, "pin")
            elif copy_rect.contains(pos):
                self._hovered_btn = (item_id, "copy")
            elif del_rect.contains(pos):
                self._hovered_btn = (item_id, "delete")
            else:
                self._hovered_btn = None

            if prev_hover != self._hovered_btn:
                if option.widget:
                    option.widget.update()
            return True

        if event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                if pin_rect.contains(pos):
                    self.pin_requested.emit(item_id, not pinned)
                    return True
                if copy_rect.contains(pos):
                    self._flash_copy(item_id, option.widget)
                    self.copy_requested.emit(item_id, full_text)
                    return True
                if del_rect.contains(pos):
                    self.delete_requested.emit(item_id)
                    return True
                if rect.contains(pos):
                    # Clicking card body copies to clipboard
                    self._flash_copy(item_id, option.widget)
                    self.copy_requested.emit(item_id, full_text)
                    return True

        return super().editorEvent(event, model, option, index)

    def _flash_copy(self, item_id: str, widget):
        """Temporarily show checkmark icon for copy feedback."""
        self._copied_item_id = item_id
        if widget:
            widget.update()
        QTimer.singleShot(600, lambda: self._reset_copy(widget))

    def _reset_copy(self, widget):
        self._copied_item_id = None
        if widget:
            try:
                widget.update()
            except RuntimeError:
                pass
