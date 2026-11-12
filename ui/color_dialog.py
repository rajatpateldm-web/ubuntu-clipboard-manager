"""
ui/color_dialog.py
Dialog for selecting ClipVault clipboard color schemes (Classic, Cyan, IDE palettes).
"""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ui.styles import (
    COLOR_SCHEMES,
    COLOR_SCHEME_DESCRIPTIONS,
    DEFAULT_COLOR_SCHEME,
    get_scheme_swatches,
    normalize_color_scheme,
)


def _build_swatch_icon(colors: list[str]) -> QIcon:
    """Render a 4-color swatch pill QIcon for a color scheme button."""
    width, height = 46, 16
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    slot_w = 10
    gap = 2
    border_pen = QPen(QColor(128, 128, 128, 110), 1)
    painter.setPen(border_pen)

    for idx, hex_color in enumerate(colors[:4]):
        x = idx * (slot_w + gap)
        painter.setBrush(QColor(hex_color))
        painter.drawRoundedRect(x, 1, slot_w, height - 2, 3, 3)

    painter.end()
    return QIcon(pixmap)


class ColorOptionsDialog(QDialog):
    """Modal dialog providing live-updating clipboard color scheme selection."""

    color_scheme_changed = pyqtSignal(str)

    def __init__(
        self,
        theme_name: str = "dark",
        color_scheme: str = DEFAULT_COLOR_SCHEME,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("colorOptionsDialog")
        self.setWindowTitle("Color Options")
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setFixedWidth(400)
        self.setModal(True)

        self._theme_name = theme_name if theme_name in ("dark", "light") else "dark"
        self._color_scheme = normalize_color_scheme(color_scheme)
        self._scheme_buttons: dict[str, QPushButton] = {}

        self._build_ui()
        self._refresh_selection()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        heading = QLabel("Clipboard Color Options")
        heading.setObjectName("dialogHeading")
        root.addWidget(heading)

        mode_label = "Dark Mode Palettes" if self._theme_name == "dark" else "Light Mode Palettes"
        subheading = QLabel(f"{mode_label} (toggle theme anytime for light/dark variants)")
        subheading.setObjectName("dialogSubheading")
        subheading.setWordWrap(True)
        root.addWidget(subheading)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        for index, scheme_name in enumerate(COLOR_SCHEMES):
            swatches = get_scheme_swatches(self._theme_name, scheme_name)
            btn = QPushButton(f"  {scheme_name}")
            btn.setObjectName("colorOptionCard")
            btn.setIcon(_build_swatch_icon(swatches))
            btn.setIconSize(QSize(46, 16))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(40)
            desc = COLOR_SCHEME_DESCRIPTIONS.get(scheme_name, scheme_name)
            btn.setToolTip(f"{scheme_name}: {desc}")
            btn.clicked.connect(lambda _checked=False, name=scheme_name: self._on_select_scheme(name))

            self._scheme_buttons[scheme_name] = btn
            grid.addWidget(btn, index // 2, index % 2)

        root.addLayout(grid)

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

    def _on_select_scheme(self, scheme_name: str):
        self._color_scheme = normalize_color_scheme(scheme_name)
        self._refresh_selection()
        self.color_scheme_changed.emit(self._color_scheme)

    def _on_reset(self):
        self._on_select_scheme(DEFAULT_COLOR_SCHEME)

    def _refresh_selection(self):
        for name, btn in self._scheme_buttons.items():
            is_selected = name == self._color_scheme
            btn.setProperty("selected", "true" if is_selected else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

