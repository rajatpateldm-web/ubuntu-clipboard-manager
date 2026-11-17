# Bulk History Cleanup Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a bulk cleanup tool allowing users to delete unpinned clipboard history items older than a selected threshold (24 Hours, 7 Days, 30 Days, or All Unpinned) using an in-window safety confirmation modal, with pinned items permanently protected.

**Architecture:** Add age-based deletion and preview counting queries to `DatabaseService` and `ClipboardService`. Implement in-memory pruning on `ClipboardModel`. Build `CleanupDialog` with preset selectors and live count feedback, presented via `MainWindow._run_modal_overlay`. Integrate a header action button and trigger live UI state updates.

**Tech Stack:** Python 3.12, PyQt6, SQLite (WAL mode), unittest / pytest.

**Spec:** [docs/superpowers/specs/2026-11-17-bulk-cleanup-design.md](file:///home/rajatkumarpatel/Documents/Projects/ubuntu-clipboard-manager/docs/superpowers/specs/2026-11-17-bulk-cleanup-design.md)

## Global Constraints

* Pinned protection: Clips with `pinned = 1` must never be deleted under any threshold.
* Modal overlay: All dialogs must be rendered using `MainWindow._run_modal_overlay` for Wayland and X11 reliability.
* Single-instance & background stability: Bulk cleanup must not stop or destabilize the clipboard monitoring thread or IPC server.
* SQLite security: Database permissions must remain restricted to `0o600` after modifications.
* Commit attribution: Every git commit must end with git trailer `Authored-By-Org: NetTantra Technologies`.
* Typography: Do not use em dashes, en dashes, or double hyphens as dashes in any prose or UI strings.

## Review Focus

1. Deletion boundary accuracy: Verify that items with timestamp exactly at or newer than the cutoff timestamp are preserved, and only items strictly older are removed.
2. Pinned immunity: Even when "All Unpinned" is chosen, pinned items with older timestamps must remain untouched in the database and UI model.
3. Zero-count safety: When no items match the selected threshold, the deletion button must be disabled to prevent accidental no-op submissions.
4. Live synchronization: After deletion, the clipboard list view and empty-state notice must immediately reflect the remaining items without window re-creation.
5. In-window modal escape handling: Pressing Escape or clicking Cancel must safely dismiss the dialog without executing deletion.

### Task 1: Database and Service Layer Bulk Cleanup Support

**Files:**
* Modify: `services/database_service.py`
* Modify: `services/clipboard_service.py`
* Test: `tests/test_database_bulk_cleanup.py`

**Interfaces:**
* `DatabaseService.count_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`
* `DatabaseService.delete_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`
* `ClipboardService.count_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`
* `ClipboardService.delete_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`

* [x] **Step 1: Write failing tests for DatabaseService and ClipboardService cleanup**

Create `tests/test_database_bulk_cleanup.py` with test cases:
1. `test_count_unpinned_older_than`: verify count with specific cutoffs and with `None`.
2. `test_delete_unpinned_older_than_with_cutoff`: verify deletion of unpinned items older than cutoff while keeping newer unpinned items.
3. `test_pinned_items_never_deleted`: populate pinned items with old timestamps, run cleanup with `None` (All Unpinned), verify 100% of pinned items remain intact.
4. `test_clipboard_service_memory_sync`: verify `ClipboardService.history` list is filtered consistently with database rows.

* [x] **Step 2: Run test suite to verify test failure**

Run:
```bash
./venv/bin/python3 -m unittest tests/test_database_bulk_cleanup.py
```
Expected: Failures due to missing methods on `DatabaseService` and `ClipboardService`.

* [x] **Step 3: Implement database queries and service synchronization**

In `services/database_service.py`:
Implement `count_unpinned_older_than(cutoff_timestamp: float | None = None) -> int` and `delete_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`.
Ensure `_restrict_db_permissions()` is called after deletion.

In `services/clipboard_service.py`:
Implement `count_unpinned_older_than` and `delete_unpinned_older_than`. Update `self.history` in-memory list to drop deleted unpinned entries.

* [x] **Step 4: Run test suite to verify test pass**

Run:
```bash
./venv/bin/python3 -m unittest tests/test_database_bulk_cleanup.py
```
Expected: All tests pass.

* [x] **Step 5: Commit changes**

Stage modified service files and tests, commit with:
```
feat(database): add age-based cleanup and counting for unpinned clips

Authored-By-Org: NetTantra Technologies
```

### Task 2: Clipboard Model Cleanup Support

**Files:**
* Modify: `ui/clipboard_model.py`
* Test: `tests/test_clipboard_model_cleanup.py`

**Interfaces:**
* `ClipboardModel.count_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`
* `ClipboardModel.remove_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`

* [x] **Step 1: Write failing tests for ClipboardModel cleanup**

Create `tests/test_clipboard_model_cleanup.py` with test cases:
1. `test_model_count_unpinned`: verify accurate count based on timestamp and pinned flag.
2. `test_model_remove_unpinned_with_cutoff`: verify items older than cutoff are removed from `_items` and `rowCount()` decreases.
3. `test_model_remove_all_unpinned`: verify all unpinned items are removed, leaving only pinned items.
4. `test_model_pinned_preservation`: verify pinned items are preserved regardless of timestamp.

* [x] **Step 2: Run test suite to verify test failure**

Run:
```bash
./venv/bin/python3 -m unittest tests/test_clipboard_model_cleanup.py
```
Expected: Failures due to missing `count_unpinned_older_than` / `remove_unpinned_older_than`.

* [x] **Step 3: Implement ClipboardModel cleanup methods**

In `ui/clipboard_model.py`:
Implement `count_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`.
Implement `remove_unpinned_older_than(cutoff_timestamp: float | None = None) -> int` wrapping list filtering inside `beginResetModel()` and `endResetModel()`.

* [x] **Step 4: Run test suite to verify test pass**

Run:
```bash
./venv/bin/python3 -m unittest tests/test_clipboard_model_cleanup.py
```
Expected: All tests pass.

* [x] **Step 5: Commit changes**

Stage `ui/clipboard_model.py` and `tests/test_clipboard_model_cleanup.py`, commit with:
```
feat(model): add unpinned item pruning to ClipboardModel

Authored-By-Org: NetTantra Technologies
```

### Task 3: Cleanup Modal Dialog Component

**Files:**
* Create: `ui/cleanup_dialog.py`
* Modify: `ui/styles.py`
* Test: `tests/test_cleanup_dialog.py`

**Interfaces:**
* `CleanupDialog(count_callback, parent=None)`
* `CleanupDialog.selected_cutoff() -> float | None`
* `CleanupDialog.PRESETS`: mapping of preset keys to labels and duration seconds.

* [x] **Step 1: Write failing tests for CleanupDialog**

Create `tests/test_cleanup_dialog.py` with tests:
1. `test_dialog_initialization`: verify default preset selection ("24 Hours") and dialog properties.
2. `test_dialog_preset_change_updates_count`: verify switching radio options triggers count callback and updates impact text.
3. `test_dialog_delete_button_disabled_when_zero`: verify delete button is disabled when matching count is 0.
4. `test_dialog_accept_reject`: verify clicking Cancel rejects and clicking Delete accepts with proper `selected_cutoff()`.

* [x] **Step 2: Run test suite to verify test failure**

Run:
```bash
./venv/bin/python3 -m unittest tests/test_cleanup_dialog.py
```
Expected: ModuleNotFoundError for `ui.cleanup_dialog`.

* [x] **Step 3: Implement CleanupDialog and styles**

In `ui/cleanup_dialog.py`:
Implement `CleanupDialog` subclassing `QDialog`:
- Preset radio buttons: "24 Hours" (1 day), "7 Days" (7 days), "30 Days" (30 days), "All Unpinned" (None).
- Information / warning labels clearly stating pinned items remain safe.
- Live item count indicator updated via `count_callback`.
- Action buttons: "Cancel" (rejects) and "Clear Items" (destructive accent, accepts, disabled if count is 0).

In `ui/styles.py`:
Add QSS styles for `cleanupDialog`, `cleanupRadioOption`, `cleanupWarningBanner`, and `cleanupDeleteBtn`.

* [x] **Step 4: Run test suite to verify test pass**

Run:
```bash
./venv/bin/python3 -m unittest tests/test_cleanup_dialog.py
```
Expected: All tests pass.

* [x] **Step 5: Commit changes**

Stage `ui/cleanup_dialog.py`, `ui/styles.py`, and `tests/test_cleanup_dialog.py`, commit with:
```
feat(ui): add CleanupDialog component with preset selection and safety feedback

Authored-By-Org: NetTantra Technologies
```

### Task 4: MainWindow Integration and Header Cleanup Button

**Files:**
* Modify: `ui/main_window.py`
* Modify: `ui/styles.py`
* Test: `tests/test_main_window_cleanup.py`

**Interfaces:**
* `MainWindow._build_header()` includes `self._cleanup_btn`
* `MainWindow._on_open_cleanup()` opens `CleanupDialog` in `_run_modal_overlay`
* `MainWindow._count_unpinned_items(cutoff: float | None) -> int`
* `MainWindow._execute_cleanup(cutoff: float | None) -> int`

* [x] **Step 1: Write failing tests for MainWindow cleanup integration**

Create `tests/test_main_window_cleanup.py` with tests:
1. `test_header_has_cleanup_button`: verify `_cleanup_btn` exists in header with tooltip and icon.
2. `test_cleanup_execution_updates_model_and_service`: verify calling `_execute_cleanup` deletes unpinned items from both service and model, leaving pinned items.
3. `test_cleanup_updates_empty_state`: verify that clearing all items displays the empty state label.

* [x] **Step 2: Run test suite to verify test failure**

Run:
```bash
./venv/bin/python3 -m unittest tests/test_main_window_cleanup.py
```
Expected: Failures due to missing `_cleanup_btn` and cleanup methods on `MainWindow`.

* [x] **Step 3: Integrate cleanup into MainWindow**

In `ui/main_window.py`:
- Add `self._cleanup_btn` to `_build_header()` with icon `"🧹"` and tooltip `"Clear Old History"`.
- Implement `_on_open_cleanup()`, `_count_unpinned_items(cutoff)`, and `_execute_cleanup(cutoff)`.
- Connect button to `_on_open_cleanup()`.
- On dialog accept, execute cleanup and update empty state.

In `ui/styles.py`:
Ensure `#cleanupHistoryBtn` is styled identically to `#fontSettingsBtn` and `#colorSchemeBtn`.

* [x] **Step 4: Run test suite to verify test pass**

Run:
```bash
./venv/bin/python3 -m unittest tests/test_main_window_cleanup.py
```
Expected: All tests pass.

* [x] **Step 5: Commit changes**

Stage `ui/main_window.py`, `ui/styles.py`, and `tests/test_main_window_cleanup.py`, commit with:
```
feat(ui): integrate bulk history cleanup into MainWindow header and overlay

Authored-By-Org: NetTantra Technologies
```

### Task 5: Full Test Suite Verification and Styling Polish

**Files:**
* Modify: `tests/test_quick_copy.py` (if any shared fixtures require updates)
* Test: Full test suite `./test_clipboard.sh`
* Lint: `uv run --with ruff ruff check .`

* [x] **Step 1: Run full test suite**

Run:
```bash
./test_clipboard.sh
```
Expected: 100% of tests pass across all test modules.

* [x] **Step 2: Run Ruff linter**

Run:
```bash
uv run --with ruff ruff check .
```
Expected: Zero lint errors or warnings.

* [x] **Step 3: Verify git status and branch integrity**

Verify clean working directory on `feature/bulk-history-cleanup`.
Ensure no unreviewed merges to `main`.
