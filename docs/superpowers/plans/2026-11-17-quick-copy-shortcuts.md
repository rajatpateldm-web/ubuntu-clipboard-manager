# Quick Copy Keyboard Shortcuts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide rapid in-window Quick Copy shortcuts (`Ctrl+1` through `Ctrl+9` and `Enter`) that copy target clips to the system clipboard and immediately hide the window, while preserving the background monitoring service and keeping manual copy clicks non-dismissive.

**Architecture:** Extend `MainWindow` keyboard event filtering to catch `Ctrl+1..9` and `Enter`, looking up items dynamically from `ClipboardProxyModel` to respect active search filters and pinned order. Enhance `ClipboardItemDelegate` to paint subtle `^1` through `^9` shortcut badges on the first 9 visible item cards. Keep background monitoring and single-instance IPC fully isolated and active when the window is hidden.

**Tech Stack:** Python 3.12, PyQt6, SQLite (WAL mode), pytest.

**Spec:** [docs/superpowers/specs/2026-11-17-quick-copy-shortcuts-design.md](file:///home/rajatkumarpatel/Documents/Projects/ubuntu-clipboard-manager/docs/superpowers/specs/2026-11-17-quick-copy-shortcuts-design.md)

## Global Constraints

* No synthetic keystroke injection: Do not simulate `Ctrl+V` into target windows.
* No in-process global key grabbers: Do not introduce `pynput`, `XGrabKey`, or raw device listeners.
* Wayland and X11 compatibility: Rely strictly on standard Qt event handling and existing `QLocalServer` IPC.
* Preserve background monitoring: Hiding the window must never stop `ClipboardService` or alter SQLite persistence.
* Git commit attribution: Every commit must end with git trailer `Authored-By-Org: NetTantra Technologies`.
* Typography: No em dashes or en dashes or double hyphens in any user-facing or human-read text.

## Review Focus

1. Out-of-bounds row index: Triggering `Ctrl+9` when fewer than 9 items exist must safely no-op without exceptions or window hiding.
2. Search query remapping: Typing in the search bar and immediately pressing `Ctrl+1` must copy the first filtered item, not the first unfiltered item, and must not type literal text into the search bar.
3. Pin state precedence: When items are pinned, `Ctrl+1` must copy the top pinned item in the current proxy view.
4. Window lifecycle separation: Calling Quick Copy or `Escape` must hide the window without stopping `ClipboardService._worker` thread.
5. Manual button independence: Clicking the card "Copy" button must copy the text to clipboard while keeping the window open and visible.

### Task 1: In-Window Quick Copy and Activation in MainWindow

**Files:**
* Modify: `ui/main_window.py`
* Test: `tests/test_quick_copy.py`

**Interfaces:**
* Consumes: `ClipboardProxyModel.data(index, FullTextRole)`, `ClipboardService.set_ignore_next(text)`
* Produces: `MainWindow._on_quick_copy_row(row_idx: int) -> bool`

* [ ] **Step 1: Write the failing tests for MainWindow Quick Copy**

Create `tests/test_quick_copy.py` with tests verifying `_on_quick_copy_row`, `Ctrl+1..9` event filtering, `Enter` activation copy-and-hide, and manual copy retaining visibility:

```python
import pytest
from PyQt6.QtCore import QEvent, QPoint, QRect, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from services.clipboard_service import ClipboardService
from services.database_service import DatabaseService
from ui.clipboard_model import FullTextRole, ItemIdRole
from ui.main_window import MainWindow


@pytest.fixture
def app(qapp):
    return qapp


@pytest.fixture
def clean_db(tmp_path):
    db_file = tmp_path / "test_quick_copy.db"
    db = DatabaseService(db_path=str(db_file))
    yield db
    db.close()


@pytest.fixture
def main_window(app, clean_db):
    service = ClipboardService(clean_db)
    window = MainWindow(service=service)
    window._model.load_items([
        {"id": "1", "text": "First Item", "timestamp": 1000.0, "pinned": True},
        {"id": "2", "text": "Second Item", "timestamp": 2000.0, "pinned": False},
        {"id": "3", "text": "Third Item", "timestamp": 3000.0, "pinned": False},
    ])
    window.show()
    yield window
    window.close()
    service.stop()


def test_quick_copy_row_valid(main_window):
    success = main_window._on_quick_copy_row(0)
    assert success is True
    assert QApplication.clipboard().text() == "First Item"
    assert not main_window.isVisible()


def test_quick_copy_row_out_of_bounds(main_window):
    main_window.show()
    success = main_window._on_quick_copy_row(8)
    assert success is False
    assert main_window.isVisible()


def test_enter_key_activation_hides_window(main_window):
    main_window.show()
    first_index = main_window._proxy_model.index(1, 0)
    main_window._on_item_activated(first_index)
    assert QApplication.clipboard().text() == "Second Item"
    assert not main_window.isVisible()


def test_manual_copy_leaves_window_visible(main_window):
    main_window.show()
    main_window._on_copy_item("2", "Second Item")
    assert QApplication.clipboard().text() == "Second Item"
    assert main_window.isVisible()


def test_ctrl_number_event_filtering(main_window):
    main_window.show()
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_2,
        Qt.KeyboardModifier.ControlModifier,
        "2",
    )
    handled = main_window.eventFilter(main_window._search_bar, event)
    assert handled is True
    assert QApplication.clipboard().text() == "Second Item"
    assert not main_window.isVisible()
```

* [ ] **Step 2: Run test to verify failure**

Run: `uv run --with pytest pytest tests/test_quick_copy.py -v`
Expected: FAIL with `AttributeError: 'MainWindow' object has no attribute '_on_quick_copy_row'`

* [ ] **Step 3: Implement Quick Copy handling in `ui/main_window.py`**

1. Add `_on_quick_copy_row(self, row_idx: int) -> bool`:
   * Validate `0 <= row_idx < self._proxy_model.rowCount()`.
   * If invalid, return `False`.
   * If valid, retrieve `text = self._proxy_model.data(self._proxy_model.index(row_idx, 0), FullTextRole)`.
   * Call `self._on_copy_item("", text)`.
   * Call `self.hide()`.
   * Return `True`.
2. Update `_on_item_activated(self, proxy_index)`:
   * Retrieve text from `proxy_index`.
   * If text is present, call `self._on_copy_item("", text)` and then `self.hide()`.
3. Update `eventFilter(self, watched, event)`:
   * Intercept `QEvent.Type.KeyPress` on both `self._search_bar` and `self._list_view`.
   * Check if `event.modifiers() == Qt.KeyboardModifier.ControlModifier` and `Qt.Key.Key_1 <= event.key() <= Qt.Key.Key_9`.
   * Calculate `target_row = event.key() - Qt.Key.Key_1`.
   * Call `self._on_quick_copy_row(target_row)` and return `True`.

* [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest pytest tests/test_quick_copy.py -v`
Expected: PASS

* [ ] **Step 5: Commit**

```bash
git add ui/main_window.py tests/test_quick_copy.py
git commit -m "feat: implement Quick Copy shortcuts in MainWindow

Authored-By-Org: NetTantra Technologies"
```

### Task 2: Visual Shortcut Badges in ClipboardItemDelegate

**Files:**
* Modify: `ui/clipboard_delegate.py`
* Test: `tests/test_quick_copy.py`

**Interfaces:**
* Consumes: `index.row()`, `self._palette`, `self._build_font()`
* Produces: Visual `^1`..`^9` pill badges painted in card metadata row for top 9 visible rows

* [ ] **Step 1: Write tests for delegate badge rendering geometry**

Append tests to `tests/test_quick_copy.py` verifying badge inclusion:

```python
def test_delegate_shortcut_badge_computation(main_window):
    delegate = main_window._delegate
    first_index = main_window._proxy_model.index(0, 0)
    ninth_index = main_window._proxy_model.index(8, 0)
    assert delegate._get_shortcut_badge_text(first_index.row()) == "^1"
    assert delegate._get_shortcut_badge_text(ninth_index.row()) is None or delegate._get_shortcut_badge_text(8) == "^9"
    assert delegate._get_shortcut_badge_text(9) is None
```

* [ ] **Step 2: Run test to verify failure**

Run: `uv run --with pytest pytest tests/test_quick_copy.py::test_delegate_shortcut_badge_computation -v`
Expected: FAIL with `AttributeError: 'ClipboardItemDelegate' object has no attribute '_get_shortcut_badge_text'`

* [ ] **Step 3: Implement shortcut badge rendering in `ui/clipboard_delegate.py`**

1. Add helper method `_get_shortcut_badge_text(self, row: int) -> str | None`:
   * If `0 <= row < 9`, return `f"^{row + 1}"`.
   * Else, return `None`.
2. In `ClipboardItemDelegate.paint()`, within the Metadata Row section:
   * Query `shortcut_text = self._get_shortcut_badge_text(index.row())`.
   * If `shortcut_text` is not `None`:
     * Use `badge_font = self._build_font(size_offset=-3, force_bold=True, respect_style=True)`.
     * Measure text dimensions: `badge_width = max(24, badge_metrics.horizontalAdvance(shortcut_text) + 8)`.
     * Paint pill badge at `rect.x() + 12 + time_width`, advance offset for subsequent line count badge.
     * Fill background with `p["badge_bg"]`, border with `p["badge_border"]`, text with `p["badge_text"]`.

* [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest pytest tests/test_quick_copy.py -v`
Expected: PASS

* [ ] **Step 5: Commit**

```bash
git add ui/clipboard_delegate.py tests/test_quick_copy.py
git commit -m "feat: render shortcut badges for top items in delegate

Authored-By-Org: NetTantra Technologies"
```

### Task 3: Comprehensive Integration Testing and Documentation

**Files:**
* Modify: `tests/test_quick_copy.py`
* Modify: `README.md`
* Modify: `toggle.sh`

**Interfaces:**
* Consumes: Full Quick Copy stack, search proxy filtering, pinned ordering, and background service lifecycle
* Produces: Validated multi-environment tests and user documentation

* [ ] **Step 1: Write integration tests for search filtering and background persistence**

Add integration test cases in `tests/test_quick_copy.py`:

```python
def test_search_filtering_remaps_quick_copy(main_window):
    main_window.show()
    main_window._search_bar.setText("Third")
    assert main_window._proxy_model.rowCount() == 1
    success = main_window._on_quick_copy_row(0)
    assert success is True
    assert QApplication.clipboard().text() == "Third Item"
    assert not main_window.isVisible()


def test_pinned_item_priority_in_quick_copy(main_window):
    # Pinned items are ordered first
    first_index = main_window._proxy_model.index(0, 0)
    assert first_index.data(ItemIdRole) == "1"
    main_window._on_quick_copy_row(0)
    assert QApplication.clipboard().text() == "First Item"


def test_background_service_persists_when_window_hidden(main_window):
    main_window.show()
    main_window.hide()
    # Adding a clip while hidden updates the model in background
    main_window._on_new_clip("4", "Background Item", 4000.0)
    assert main_window._model.rowCount() == 4
    # Re-showing window contains the item
    main_window.show()
    assert main_window._proxy_model.rowCount() == 4
```

* [ ] **Step 2: Run test suite to verify all tests pass**

Run: `uv run --with pytest pytest tests/test_quick_copy.py -v`
Expected: PASS

* [ ] **Step 3: Update documentation and shortcuts reference**

1. In `README.md`:
   * Update keyboard shortcuts table to document `Ctrl+1` through `Ctrl+9` (Quick Copy and hide) and `Ctrl + Shift + V` system toggle.
2. In `toggle.sh`:
   * Add documentation comment explaining `Ctrl + Shift + V` registration in Ubuntu Settings -> Keyboard -> Custom Shortcuts.

* [ ] **Step 4: Run full regression test suite and linter**

Run:
```bash
uv run --with pytest pytest
uv run --with ruff ruff check .
```
Expected: 100% test pass and zero lint errors.

* [ ] **Step 5: Commit**

```bash
git add README.md toggle.sh tests/test_quick_copy.py
git commit -m "docs: document Quick Copy shortcuts and system toggle hotkey

Authored-By-Org: NetTantra Technologies"
```
