"""
ui/font_dialog.py
Dialog for configuring ClipVault font family, font style, and font size.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)

from ui.styles import (
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_FONT_STYLE,
    FONT_FAMILY_PRESETS,
    FONT_STYLE_OPTIONS,
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    clamp_font_size,
    normalize_font_style,
    resolve_font_qss,
    resolve_qt_font_family,
    sanitize_font_family,
)


class FontOptionsDialog(QDialog):
    """Modal dialog providing live-updating font family, style, and size controls."""

    font_changed = pyqtSignal(str, int, str)  # (font_family, font_size, font_style)

    def __init__(
        self,
        font_family: str = DEFAULT_FONT_FAMILY,
        font_size: int = DEFAULT_FONT_SIZE,
        font_style: str = DEFAULT_FONT_STYLE,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("fontOptionsDialog")
        self.setWindowTitle("Font Options")
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setFixedWidth(400)
        self.setModal(True)

        self._font_family = sanitize_font_family(font_family)
        self._font_size = clamp_font_size(font_size)
        self._font_style = normalize_font_style(font_style)

        self._build_ui()
        self._sync_controls(self._font_family, self._font_size, self._font_style)
        self._update_preview()
        self.ensurePolished()
        self.adjustSize()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        heading = QLabel("Font Style & Size")
        heading.setObjectName("dialogHeading")
        root.addWidget(heading)

        # Font family selector
        family_label = QLabel("Font Family")
        family_label.setObjectName("dialogFieldLabel")
        self._family_combo = QComboBox()
        self._family_combo.setObjectName("fontFamilyCombo")
        self._populate_families()
        self._family_combo.currentTextChanged.connect(self._on_controls_changed)
        root.addWidget(family_label)
        root.addWidget(self._family_combo)

        # Style and Size row
        row = QHBoxLayout()
        row.setSpacing(10)

        style_col = QVBoxLayout()
        style_col.setSpacing(4)
        style_label = QLabel("Font Style")
        style_label.setObjectName("dialogFieldLabel")
        self._style_combo = QComboBox()
        self._style_combo.setObjectName("fontStyleCombo")
        self._style_combo.addItems(list(FONT_STYLE_OPTIONS.keys()))
        self._style_combo.currentTextChanged.connect(self._on_controls_changed)
        style_col.addWidget(style_label)
        style_col.addWidget(self._style_combo)

        size_col = QVBoxLayout()
        size_col.setSpacing(4)
        size_label = QLabel("Font Size")
        size_label.setObjectName("dialogFieldLabel")
        self._size_spin = QSpinBox()
        self._size_spin.setObjectName("fontSizeSpin")
        self._size_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self._size_spin.setSuffix(" px")
        self._size_spin.valueChanged.connect(self._on_controls_changed)
        size_col.addWidget(size_label)
        size_col.addWidget(self._size_spin)

        row.addLayout(style_col, stretch=3)
        row.addLayout(size_col, stretch=2)
        root.addLayout(row)

        # Live preview card
        self._preview_card = QFrame()
        self._preview_card.setObjectName("fontPreviewCard")
        self._preview_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        preview_layout = QVBoxLayout(self._preview_card)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        preview_layout.setSpacing(6)

        self._preview_text = QLabel("Sample clip: The quick brown fox 0123")
        self._preview_text.setWordWrap(True)
        self._preview_text.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._preview_meta = QLabel("Just now  |  3 lines")
        self._preview_meta.setObjectName("fontPreviewMeta")

        preview_layout.addWidget(self._preview_text)
        preview_layout.addWidget(self._preview_meta)
        root.addWidget(self._preview_card)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setObjectName("dialogSecondaryBtn")
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.clicked.connect(self._on_reset)

        self._done_btn = QPushButton("Done")
        self._done_btn.setObjectName("dialogPrimaryBtn")
        self._done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._done_btn.setDefault(True)
        self._done_btn.clicked.connect(self.accept)

        btn_row.addWidget(self._reset_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._done_btn)
        root.addLayout(btn_row)

    def _populate_families(self):
        preset_names = list(FONT_FAMILY_PRESETS.keys())
        self._family_combo.addItems(preset_names)

        preset_lower = {name.lower() for name in preset_names}
        system_families = sorted(
            {fam for fam in QFontDatabase.families() if fam and fam.lower() not in preset_lower},
            key=str.lower,
        )
        if system_families:
            self._family_combo.insertSeparator(len(preset_names))
            self._family_combo.addItems(system_families)

    def _sync_controls(self, font_family: str, font_size: int, font_style: str):
        self._family_combo.blockSignals(True)
        self._style_combo.blockSignals(True)
        self._size_spin.blockSignals(True)
        try:
            idx = self._family_combo.findText(font_family, Qt.MatchFlag.MatchFixedString)
            if idx < 0:
                self._family_combo.addItem(font_family)
                idx = self._family_combo.findText(font_family, Qt.MatchFlag.MatchFixedString)
            self._family_combo.setCurrentIndex(max(0, idx))

            style_idx = self._style_combo.findText(font_style, Qt.MatchFlag.MatchFixedString)
            self._style_combo.setCurrentIndex(max(0, style_idx))
            self._size_spin.setValue(font_size)
        finally:
            self._family_combo.blockSignals(False)
            self._style_combo.blockSignals(False)
            self._size_spin.blockSignals(False)

    def _on_controls_changed(self):
        self._font_family = sanitize_font_family(self._family_combo.currentText())
        self._font_style = normalize_font_style(self._style_combo.currentText())
        self._font_size = clamp_font_size(self._size_spin.value())
        self._update_preview()
        self.font_changed.emit(self._font_family, self._font_size, self._font_style)

    def _on_reset(self):
        self._font_family = DEFAULT_FONT_FAMILY
        self._font_size = DEFAULT_FONT_SIZE
        self._font_style = DEFAULT_FONT_STYLE
        self._sync_controls(self._font_family, self._font_size, self._font_style)
        self._update_preview()
        self.font_changed.emit(self._font_family, self._font_size, self._font_style)

    def _update_preview(self):
        qt_family = resolve_qt_font_family(self._font_family)
        font_qss = resolve_font_qss(self._font_family)
        font_weight, font_slant, is_bold, is_italic = FONT_STYLE_OPTIONS[self._font_style]
        meta_size = max(9, self._font_size - 2)

        preview_font = QFont(qt_family)
        preview_font.setPixelSize(self._font_size)
        preview_font.setBold(is_bold)
        preview_font.setItalic(is_italic)
        self._preview_text.setFont(preview_font)
        self._preview_text.setStyleSheet(
            f"font-family: {font_qss}; font-size: {self._font_size}px; "
            f"font-weight: {font_weight}; font-style: {font_slant};"
        )

        meta_font = QFont(qt_family)
        meta_font.setPixelSize(meta_size)
        meta_font.setBold(is_bold)
        meta_font.setItalic(is_italic)
        self._preview_meta.setFont(meta_font)
        self._preview_meta.setStyleSheet(
            f"font-family: {font_qss}; font-size: {meta_size}px; "
            f"font-weight: {font_weight}; font-style: {font_slant};"
        )

        # Keep preview card and dialog tall enough using polished QSS font metrics
        self._preview_text.ensurePolished()
        self._preview_meta.ensurePolished()
        preview_width = self._preview_text.width() if self._preview_text.width() > 100 else 290
        text_fm = self._preview_text.fontMetrics()
        text_bounds = text_fm.boundingRect(
            0,
            0,
            preview_width,
            1000,
            Qt.TextFlag.TextWordWrap,
            self._preview_text.text(),
        )
        text_height = max(text_bounds.height(), self._preview_text.heightForWidth(preview_width)) + 6
        meta_height = self._preview_meta.fontMetrics().height() + 4

        self._preview_text.setMinimumHeight(text_height)
        self._preview_meta.setMinimumHeight(meta_height)
        self._preview_card.setMinimumHeight(text_height + meta_height + 28)
        self._preview_card.updateGeometry()
        if self.layout():
            self.layout().activate()
        self.adjustSize()

