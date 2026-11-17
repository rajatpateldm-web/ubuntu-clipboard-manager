"""
ui/cleanup_dialog.py
--------------------
Dialog for bulk deletion of unpinned clipboard history entries with safety confirmation.
"""

from collections.abc import Callable
import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

PRESET_OPTIONS = [
    ("24_hours", "Older than 24 Hours", 86400),
    ("7_days", "Older than 7 Days", 7 * 86400),
    ("30_days", "Older than 30 Days", 30 * 86400),
    ("all_unpinned", "All Unpinned", None),
]


class CleanupDialog(QDialog):
    """
    Modal dialog providing threshold selection and safety confirmation for bulk cleanup.
    Pinned items are permanently protected and never deleted.
    """

    scrim_dismiss_action = "ignore"

    def __init__(
        self,
        count_callback: Callable[[float | None], int] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("cleanupDialog")
        self.setWindowTitle("Clear History")
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setFixedWidth(400)
        self.setModal(True)
        self.scrim_dismiss_action = "ignore"

        self._count_callback = count_callback
        self._preset_buttons: dict[str, QRadioButton] = {}
        self._current_count = 0

        self._build_ui()
        self._sync_count()
        self.ensurePolished()
        self.adjustSize()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        heading = QLabel("Clear Clipboard History")
        heading.setObjectName("dialogHeading")
        root.addWidget(heading)

        subheading = QLabel("Permanently delete unpinned clips older than the selected threshold.")
        subheading.setObjectName("dialogSubheading")
        subheading.setWordWrap(True)
        root.addWidget(subheading)

        # Warning card highlighting pinned preservation
        warning_card = QFrame()
        warning_card.setObjectName("cleanupWarningCard")
        w_layout = QHBoxLayout(warning_card)
        w_layout.setContentsMargins(10, 8, 10, 8)
        w_layout.setSpacing(8)

        warn_icon = QLabel("📌")
        warn_icon.setStyleSheet("font-size: 14px;")
        warn_text = QLabel("Pinned items are protected and will never be deleted.")
        warn_text.setObjectName("cleanupWarningText")
        warn_text.setWordWrap(True)

        w_layout.addWidget(warn_icon)
        w_layout.addWidget(warn_text, stretch=1)
        root.addWidget(warning_card)

        # Preset options
        options_label = QLabel("Select Threshold")
        options_label.setObjectName("dialogFieldLabel")
        root.addWidget(options_label)

        self._button_group = QButtonGroup(self)
        for idx, (key, label, _duration) in enumerate(PRESET_OPTIONS):
            radio = QRadioButton(label)
            radio.setObjectName("cleanupRadioOption")
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            self._button_group.addButton(radio, idx)
            self._preset_buttons[key] = radio
            root.addWidget(radio)

        # Default to first preset ("24_hours")
        self._preset_buttons["24_hours"].setChecked(True)
        self._button_group.idToggled.connect(self._on_preset_toggled)

        # Impact count preview label
        self._count_label = QLabel("")
        self._count_label.setObjectName("cleanupImpactLabel")
        self._count_label.setWordWrap(True)
        root.addWidget(self._count_label)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("dialogSecondaryBtn")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setDefault(True)
        self._cancel_btn.clicked.connect(self.reject)

        self._delete_btn = QPushButton("Clear Items")
        self._delete_btn.setObjectName("cleanupDeleteBtn")
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.setDefault(False)
        self._delete_btn.setAutoDefault(False)
        self._delete_btn.clicked.connect(self.accept)

        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._delete_btn)
        root.addLayout(btn_row)

    def _on_preset_toggled(self, _id: int, checked: bool):
        if checked:
            self._sync_count()

    def select_preset(self, preset_key: str):
        """Programmatically select a preset by key."""
        if preset_key in self._preset_buttons:
            self._preset_buttons[preset_key].setChecked(True)
            self._sync_count()

    def selected_preset_key(self) -> str:
        """Return the active preset key."""
        for key, btn in self._preset_buttons.items():
            if btn.isChecked():
                return key
        return "24_hours"

    def selected_cutoff(self) -> float | None:
        """Compute cutoff timestamp based on selected preset."""
        preset_key = self.selected_preset_key()
        for key, _label, duration in PRESET_OPTIONS:
            if key == preset_key:
                if duration is None:
                    return None
                return time.time() - duration
        return time.time() - 86400

    def matching_count(self) -> int:
        """Return the calculated count of items that match the current threshold."""
        return self._current_count

    def _sync_count(self):
        """Update live count preview and enable/disable delete button."""
        cutoff = self.selected_cutoff()
        if self._count_callback:
            self._current_count = self._count_callback(cutoff)
        else:
            self._current_count = 0

        if self._current_count == 0:
            self._count_label.setText("No unpinned items match this threshold.")
            self._delete_btn.setEnabled(False)
        elif self._current_count == 1:
            self._count_label.setText("1 unpinned item will be deleted.")
            self._delete_btn.setEnabled(True)
        else:
            self._count_label.setText(f"{self._current_count} unpinned items will be deleted.")
            self._delete_btn.setEnabled(True)
