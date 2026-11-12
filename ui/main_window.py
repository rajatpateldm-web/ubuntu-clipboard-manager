"""
ui/main_window.py
Virtualized, high-performance main window for ClipVault.
Uses QListView with custom ClipboardItemDelegate and ClipboardModel
to achieve constant O(1) memory usage regardless of clipboard history size.
"""

import time

from PyQt6.QtCore import Qt, QEvent, QEventLoop, QSettings
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.clipboard_service import ClipboardService
from ui.clipboard_model import ClipboardModel, ClipboardProxyModel, FullTextRole, ItemIdRole
from ui.clipboard_delegate import ClipboardItemDelegate
from ui.color_dialog import ColorOptionsDialog
from ui.font_dialog import FontOptionsDialog
from ui.styles import (
    DEFAULT_COLOR_SCHEME,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_STYLE,
    build_stylesheet,
    clamp_font_size,
    normalize_color_scheme,
    normalize_font_style,
    sanitize_font_family,
)


class _ModalBackdrop(QFrame):
    """Dimmed in-window overlay container that centers modal dialogs over MainWindow."""

    def __init__(self, parent: QWidget, dialog):
        super().__init__(parent)
        self._dialog = dialog
        self.setObjectName("modalBackdrop")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        # Close modal when clicking the dimmed scrim outside the dialog card
        if self.childAt(event.position().toPoint()) is None and self._dialog is not None:
            self._dialog.accept()
            return
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """
    Primary window for ClipVault clipboard manager.

    Performance characteristics:
    - Adding a new card: O(1) model insert
    - Memory usage: O(1) widget allocations via virtualized QListView
    - Search filtering: O(n) proxy model filter without destroying/rebuilding widgets
    - Item rendering: O(visible) paint passes via custom item delegate
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ClipVault")
        self.setMinimumSize(400, 500)
        self.resize(500, 700)
        self.setObjectName("mainWindow")
        self._active_backdrop: _ModalBackdrop | None = None
        self._active_modal_dialog = None

        # ── Theme & Font Preferences ──────────────────────────────────
        self._settings = QSettings("ClipVault", "App")
        self._theme = self._settings.value("theme", "dark")
        self._color_scheme = normalize_color_scheme(
            self._settings.value("color_scheme", DEFAULT_COLOR_SCHEME)
        )
        self._font_family = sanitize_font_family(
            self._settings.value("font_family", DEFAULT_FONT_FAMILY)
        )
        self._font_size = clamp_font_size(
            self._settings.value("font_size", DEFAULT_FONT_SIZE)
        )
        self._font_style = normalize_font_style(
            self._settings.value("font_style", DEFAULT_FONT_STYLE)
        )

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
        root.addWidget(self._build_list_container(), stretch=1)
        root.addWidget(self._build_footer())

        # Apply initial theme and font settings
        self.set_theme(self._theme, persist=False)

        # ── Clipboard service ─────────────────────────────────────────
        self._service = ClipboardService(self)
        self._service.new_item.connect(self._on_new_clip)
        self._service.item_trimmed.connect(self._on_item_trimmed)

        # Load initial history from database/service
        self._load_initial_history()

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

        self._font_btn = QPushButton("Aa")
        self._font_btn.setObjectName("fontSettingsBtn")
        self._font_btn.setToolTip("Font Style & Size Options")
        self._font_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._font_btn.clicked.connect(self._on_open_font_options)

        self._color_btn = QPushButton("🎨")
        self._color_btn.setObjectName("colorSchemeBtn")
        self._color_btn.setToolTip("Clipboard Color Options")
        self._color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color_btn.clicked.connect(self._on_open_color_options)

        self._theme_btn = QPushButton("☀️" if self._theme == "dark" else "🌙")
        self._theme_btn.setObjectName("themeToggleBtn")
        self._theme_btn.setToolTip("Switch to Light Mode" if self._theme == "dark" else "Switch to Dark Mode")
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.clicked.connect(self._on_toggle_theme)

        layout.addWidget(icon)
        layout.addSpacing(2)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self._font_btn)
        layout.addSpacing(6)
        layout.addWidget(self._color_btn)
        layout.addSpacing(6)
        layout.addWidget(self._theme_btn)
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
        self._search_bar.installEventFilter(self)

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

    def _build_list_container(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 4, 12, 12)
        layout.setSpacing(0)

        # Virtualized QListView
        self._list_view = QListView()
        self._list_view.setObjectName("clipListView")
        self._list_view.setUniformItemSizes(True)  # Key optimization for O(1) layout
        self._list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list_view.setMouseTracking(True)
        self._list_view.setFrameShape(QFrame.Shape.NoFrame)
        self._list_view.installEventFilter(self)

        # Setup model and proxy
        self._model = ClipboardModel(self)
        self._proxy_model = ClipboardProxyModel(self)
        self._proxy_model.setSourceModel(self._model)
        self._list_view.setModel(self._proxy_model)

        # Setup custom item delegate
        self._delegate = ClipboardItemDelegate(self)
        self._delegate.set_theme(self._theme)
        self._list_view.setItemDelegate(self._delegate)

        # Delegate action signals
        self._delegate.pin_requested.connect(self._on_pin_toggled)
        self._delegate.copy_requested.connect(self._on_copy_item)
        self._delegate.delete_requested.connect(self._on_delete_item)

        # Keyboard / double-click activation
        self._list_view.activated.connect(self._on_item_activated)

        # Empty state label
        self._empty_label = QLabel("Copy something to see it here.")
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setMinimumHeight(100)
        self._empty_label.setVisible(False)

        layout.addWidget(self._empty_label)
        layout.addWidget(self._list_view)
        return container

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
                self._footer.setStyleSheet("color: #D97706;")
            else:
                self._footer.setText(f"  ●  Active: {tool}  (Smooth background monitoring)")
                self._footer.setStyleSheet("color: #10B981;")
        elif getattr(self._service, "_use_x11_helper", False):
            self._footer.setText("  ●  Active: XWayland/X11 Helper  (Background monitoring)")
            self._footer.setStyleSheet("color: #10B981;")
        else:
            self._footer.setText("  ●  Active: Qt Focus-Only Fallback")
            self._footer.setStyleSheet("color: #8B6F3A;")

    # ──────────────────────────────────────────────────────────────────
    # Theme & Font Controls
    # ──────────────────────────────────────────────────────────────────

    def _apply_appearance(self):
        """Apply active theme, color scheme, and font preferences to stylesheet, delegate, and view."""
        app = QApplication.instance()
        if app:
            app.setStyleSheet(
                build_stylesheet(
                    self._theme,
                    font_family=self._font_family,
                    font_size=self._font_size,
                    font_style=self._font_style,
                    color_scheme=self._color_scheme,
                )
            )

        if hasattr(self, "_delegate"):
            self._delegate.set_theme(self._theme, self._color_scheme)
            self._delegate.set_font(self._font_family, self._font_size, self._font_style)

        if hasattr(self, "_list_view"):
            self._list_view.doItemsLayout()
            if self._list_view.viewport():
                self._list_view.viewport().update()

    def _on_toggle_theme(self):
        """Toggle between light and dark themes."""
        new_theme = "light" if self._theme == "dark" else "dark"
        self.set_theme(new_theme, persist=True)

    def set_theme(self, theme_name: str, persist: bool = True):
        """Apply theme globally and update delegate and controls."""
        self._theme = theme_name if theme_name in ("light", "dark") else "dark"
        if persist:
            self._settings.setValue("theme", self._theme)

        if hasattr(self, "_theme_btn"):
            if self._theme == "light":
                self._theme_btn.setText("🌙")
                self._theme_btn.setToolTip("Switch to Dark Mode")
            else:
                self._theme_btn.setText("☀️")
                self._theme_btn.setToolTip("Switch to Light Mode")

        self._apply_appearance()

    def _run_modal_overlay(self, dialog) -> int:
        """Present a dialog centered inside MainWindow so Wayland compositors cannot misplace it."""
        if self._active_modal_dialog is not None:
            self._active_modal_dialog.reject()

        backdrop = _ModalBackdrop(self, dialog)
        dialog.setParent(backdrop)
        dialog.setWindowFlags(Qt.WindowType.Widget)
        dialog.setProperty("modalOverlay", "true")
        dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dialog.style().unpolish(dialog)
        dialog.style().polish(dialog)
        dialog.ensurePolished()
        dialog.adjustSize()

        backdrop.layout().addWidget(dialog, 0, Qt.AlignmentFlag.AlignCenter)
        backdrop.setGeometry(self.rect())

        loop = QEventLoop(self)
        dialog.finished.connect(loop.quit)

        self._active_backdrop = backdrop
        self._active_modal_dialog = dialog
        try:
            backdrop.show()
            backdrop.raise_()
            dialog.show()
            dialog.setFocus()
            loop.exec()
            return dialog.result()
        finally:
            self._active_backdrop = None
            self._active_modal_dialog = None
            backdrop.hide()
            backdrop.deleteLater()

    def _on_open_color_options(self):
        """Open the Clipboard Color Options dialog."""
        dialog = ColorOptionsDialog(
            theme_name=self._theme,
            color_scheme=self._color_scheme,
            parent=self,
        )
        dialog.color_scheme_changed.connect(lambda scheme: self.set_color_scheme(scheme, persist=True))
        self._run_modal_overlay(dialog)

    def set_color_scheme(self, color_scheme: str, persist: bool = True):
        """Apply clipboard color scheme globally and persist preference."""
        self._color_scheme = normalize_color_scheme(color_scheme)
        if persist:
            self._settings.setValue("color_scheme", self._color_scheme)
        self._apply_appearance()

    def _on_open_font_options(self):
        """Open the Font Style & Size dialog."""
        dialog = FontOptionsDialog(
            font_family=self._font_family,
            font_size=self._font_size,
            font_style=self._font_style,
            parent=self,
        )
        dialog.font_changed.connect(self._on_font_dialog_changed)
        self._run_modal_overlay(dialog)

    def _on_font_dialog_changed(self, font_family: str, font_size: int, font_style: str):
        """Handle live font updates from FontOptionsDialog."""
        self.set_font_options(
            font_family=font_family,
            font_size=font_size,
            font_style=font_style,
            persist=True,
        )

    def set_font_options(
        self,
        font_family: str | None = None,
        font_size: int | None = None,
        font_style: str | None = None,
        persist: bool = True,
    ):
        """Apply font family, size, and style globally and persist preferences."""
        if font_family is not None:
            self._font_family = sanitize_font_family(font_family)
        if font_size is not None:
            self._font_size = clamp_font_size(font_size)
        if font_style is not None:
            self._font_style = normalize_font_style(font_style)

        if persist:
            self._settings.setValue("font_family", self._font_family)
            self._settings.setValue("font_size", self._font_size)
            self._settings.setValue("font_style", self._font_style)

        self._apply_appearance()

    # ──────────────────────────────────────────────────────────────────
    # Event Filters & Keyboard Shortcuts
    # ──────────────────────────────────────────────────────────────────

    def eventFilter(self, watched, event):
        """Handle keyboard navigation between search bar and list view."""
        if hasattr(self, "_search_bar") and watched == self._search_bar and event.type() == QEvent.Type.KeyPress:
            if hasattr(self, "_proxy_model") and hasattr(self, "_list_view"):
                if event.key() == Qt.Key.Key_Down and self._proxy_model.rowCount() > 0:
                    first_index = self._proxy_model.index(0, 0)
                    self._list_view.setCurrentIndex(first_index)
                    self._list_view.setFocus()
                    return True
        elif hasattr(self, "_list_view") and watched == self._list_view and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Delete and hasattr(self, "_proxy_model"):
                current = self._list_view.currentIndex()
                if current.isValid():
                    item_id = self._proxy_model.data(current, ItemIdRole)
                    if item_id:
                        self._on_delete_item(item_id)
                        return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        """Dismiss modal overlay first, otherwise hide window on Escape key."""
        if event.key() == Qt.Key.Key_Escape:
            if self._active_modal_dialog is not None:
                self._active_modal_dialog.reject()
                return
            self.hide()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Keep active modal backdrop sized to MainWindow."""
        super().resizeEvent(event)
        if getattr(self, "_active_backdrop", None) is not None:
            self._active_backdrop.setGeometry(self.rect())

    # ──────────────────────────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────────────────────────

    def _on_new_clip(self, item_id: str, text: str, timestamp: float = None):
        """Add new clipboard entry into model."""
        ts = timestamp or time.time()
        self._model.add_item(item_id, text, ts, pinned=False)
        self._update_empty_state()
        self._scroll_to_top()

    def _load_initial_history(self):
        """Load history items from service into virtualized model."""
        if self._service.history:
            self._model.load_items(self._service.history)
        self._update_empty_state()

    def _on_pin_toggled(self, item_id: str, pinned: bool):
        """Handle pin state toggle."""
        self._service.set_item_pinned(item_id, pinned)
        self._model.set_item_pinned(item_id, pinned)
        self._update_empty_state()

    def _on_delete_item(self, item_id: str):
        """Delete an item by unique ID."""
        self._service.remove_item(item_id)
        self._model.remove_item(item_id)
        self._update_empty_state()

    def _on_copy_item(self, item_id: str, text: str):
        """Copy item text back to system clipboard."""
        self._service.set_ignore_next(text)
        QApplication.clipboard().setText(text)

    def _on_item_activated(self, proxy_index):
        """Handle Enter / Return key on selected item to copy to clipboard."""
        if not proxy_index.isValid():
            return
        text = self._proxy_model.data(proxy_index, FullTextRole)
        if text:
            self._on_copy_item("", text)

    def _on_item_trimmed(self, item_id: str):
        """Handle auto-trimmed item from service."""
        self._model.remove_item(item_id)
        self._update_empty_state()

    def _filter_items(self, query: str):
        """Update proxy filter with search query."""
        self._proxy_model.set_filter_query(query)
        self._update_empty_state()

    def _update_empty_state(self):
        """Update empty state label based on model row counts."""
        total_items = self._model.rowCount()
        visible_items = self._proxy_model.rowCount()
        query = self._search_bar.text().strip()

        if total_items == 0:
            self._empty_label.setText("Copy something to see it here.")
            self._empty_label.setVisible(True)
            self._list_view.setVisible(False)
        elif visible_items == 0:
            self._empty_label.setText(f'No results for "{query}"')
            self._empty_label.setVisible(True)
            self._list_view.setVisible(False)
        else:
            self._empty_label.setVisible(False)
            self._list_view.setVisible(True)

    def _scroll_to_top(self):
        """Scroll list view to top."""
        self._list_view.scrollToTop()

    # ──────────────────────────────────────────────────────────────────
    # Lifecycle & Window Controls
    # ──────────────────────────────────────────────────────────────────

    def toggle_window(self):
        """Toggle window visibility and keyboard focus in a wayland-friendly way."""
        if not self.isVisible() or self.isMinimized() or not self.isActiveWindow():
            self.showNormal()
            self.show()
            self.raise_()
            self.activateWindow()
            self._search_bar.setFocus()
            self._scroll_to_top()
        else:
            self.hide()

    def closeEvent(self, event):
        """Clean shutdown."""
        if getattr(self, "_active_modal_dialog", None) is not None:
            self._active_modal_dialog.reject()
        self._service.stop()
        super().closeEvent(event)
