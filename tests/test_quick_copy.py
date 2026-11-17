"""
tests/test_quick_copy.py
Unit and integration tests for Quick Copy keyboard shortcuts and window lifecycle.
"""

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from ui.clipboard_model import FullTextRole, ItemIdRole
from ui.main_window import MainWindow


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication(["-platform", "offscreen"])


@pytest.fixture
def main_window(app, monkeypatch, tmp_path):
    monkeypatch.setenv("SNAP_USER_DATA", str(tmp_path))
    window = MainWindow()
    window._model.load_items([
        {"id": "1", "text": "First Item", "timestamp": 1000.0, "pinned": True},
        {"id": "2", "text": "Second Item", "timestamp": 2000.0, "pinned": False},
        {"id": "3", "text": "Third Item", "timestamp": 3000.0, "pinned": False},
    ])
    window.show()
    yield window
    window.close()


def test_quick_copy_row_valid(main_window):
    """Calling _on_quick_copy_row with valid row copies text and hides window."""
    success = main_window._on_quick_copy_row(0)
    assert success is True
    assert QApplication.clipboard().text() == "First Item"
    assert not main_window.isVisible()


def test_quick_copy_row_out_of_bounds(main_window):
    """Calling _on_quick_copy_row with out of bounds row returns False and keeps window visible."""
    main_window.show()
    success = main_window._on_quick_copy_row(8)
    assert success is False
    assert main_window.isVisible()


def test_enter_key_activation_hides_window(main_window):
    """Activating an item in list view via Enter copies text and hides window."""
    main_window.show()
    second_index = main_window._proxy_model.index(1, 0)
    main_window._on_item_activated(second_index)
    assert QApplication.clipboard().text() == "Third Item"
    assert not main_window.isVisible()


def test_enter_key_in_search_bar_does_not_hide_window(main_window):
    """Pressing Enter in search bar does not trigger quick copy or hide window."""
    main_window.show()
    main_window._search_bar.setText("test query")
    enter_event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.NoModifier,
        "\r",
    )
    handled = main_window.eventFilter(main_window._search_bar, enter_event)
    assert handled is False or handled is None
    assert main_window.isVisible()


def test_manual_copy_leaves_window_visible(main_window):
    """Clicking manual copy button copies text and leaves window open."""
    main_window.show()
    main_window._on_copy_item("2", "Second Item")
    assert QApplication.clipboard().text() == "Second Item"
    assert main_window.isVisible()


def test_ctrl_number_from_search_bar(main_window):
    """Pressing Ctrl+2 in search bar quick-copies second item and hides window."""
    main_window.show()
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_2,
        Qt.KeyboardModifier.ControlModifier,
        "2",
    )
    handled = main_window.eventFilter(main_window._search_bar, event)
    assert handled is True
    assert QApplication.clipboard().text() == "Third Item"
    assert not main_window.isVisible()


def test_ctrl_number_from_list_view(main_window):
    """Pressing Ctrl+1 when list view is focused quick-copies first item and hides window."""
    main_window.show()
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_1,
        Qt.KeyboardModifier.ControlModifier,
        "1",
    )
    handled = main_window.eventFilter(main_window._list_view, event)
    assert handled is True
    assert QApplication.clipboard().text() == "First Item"
    assert not main_window.isVisible()


def test_quick_copy_does_not_create_duplicate_history_entry(main_window):
    """Quick copy calls set_ignore_next to prevent clipboard echo duplicate."""
    initial_count = main_window._model.rowCount()
    main_window._on_quick_copy_row(0)
    # Service ignore window is active for this text
    assert main_window._service._ignore_next is True
    assert main_window._service._ignore_text == "First Item"
    assert main_window._model.rowCount() == initial_count


def test_delegate_shortcut_badge_computation(main_window):
    """Delegate returns ^1 through ^9 for rows 0 through 8, and None for row >= 9."""
    delegate = main_window._delegate
    assert delegate._get_shortcut_badge_text(0) == "^1"
    assert delegate._get_shortcut_badge_text(1) == "^2"
    assert delegate._get_shortcut_badge_text(8) == "^9"
    assert delegate._get_shortcut_badge_text(9) is None
    assert delegate._get_shortcut_badge_text(-1) is None


def test_search_filtering_remaps_quick_copy(main_window):
    """Typing a search query dynamically remaps Ctrl+1 to the first filtered item."""
    main_window.show()
    main_window._search_bar.setText("Third")
    assert main_window._proxy_model.rowCount() == 1
    success = main_window._on_quick_copy_row(0)
    assert success is True
    assert QApplication.clipboard().text() == "Third Item"
    assert not main_window.isVisible()


def test_pinned_item_priority_in_quick_copy(main_window):
    """Pinned items appear first and receive top shortcut indices."""
    first_index = main_window._proxy_model.index(0, 0)
    assert first_index.data(ItemIdRole) == "1"
    success = main_window._on_quick_copy_row(0)
    assert success is True
    assert QApplication.clipboard().text() == "First Item"


def test_background_service_persists_when_window_hidden(main_window):
    """Clipboard monitoring and model ingestion remain fully operational when window is hidden."""
    main_window.show()
    main_window.hide()
    assert not main_window.isVisible()

    # Simulate new incoming clip while window is hidden
    main_window._on_new_clip("4", "Background Item", 4000.0)
    assert main_window._model.rowCount() == 4

    # Re-showing the window reflects the updated model
    main_window.show()
    assert main_window._proxy_model.rowCount() == 4
    assert main_window._proxy_model.index(1, 0).data(FullTextRole) == "Background Item"


def test_toggle_window_repeated_cycles(main_window):
    """Toggling window repeatedly preserves service state and focus."""
    for _ in range(3):
        main_window.toggle_window()
        main_window.toggle_window()
    assert main_window._model.rowCount() >= 3


def test_ctrl_number_from_window_keypress(main_window):
    """Pressing Ctrl+1 directly on the window dispatches quick copy."""
    main_window.show()
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_1,
        Qt.KeyboardModifier.ControlModifier,
        "1",
    )
    main_window.keyPressEvent(event)
    assert QApplication.clipboard().text() == "First Item"
    assert not main_window.isVisible()
