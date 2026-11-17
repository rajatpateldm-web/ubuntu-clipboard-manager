# Bulk History Cleanup Tool Design Specification

## Intent and Overview
ClipVault stores clipboard history locally in SQLite. Over time, unpinned clipboard clips accumulate and can clutter search results or take up storage. This feature introduces a bulk cleanup tool that allows users to delete unpinned clipboard entries older than a selected threshold (24 Hours, 7 Days, 30 Days, or All Unpinned) using an in-window safety confirmation modal. Pinned items are permanently protected and never removed by bulk cleanup.

## Goals
* Provide an intuitive header action button to trigger the cleanup tool.
* Present an in-window modal overlay (`_run_modal_overlay`) that works reliably on both Wayland and X11 without window manager popup misplacement.
* Offer four standard threshold presets:
  1. Older than 24 Hours
  2. Older than 7 Days
  3. Older than 30 Days
  4. All Unpinned
* Display a dynamic item count preview showing exactly how many items will be deleted before the user confirms.
* Strictly safeguard pinned items: items with `pinned = 1` are never deleted regardless of timestamp.
* Keep the UI reactive: update in-memory `ClipboardModel` and `ClipboardService.history` immediately upon deletion without restarting or full reloads.
* Comprehensive test coverage for SQLite persistence, service synchronization, model pruning, and dialog interaction.

## Non-Goals and Anti-Goals
* No background auto-deletion on timer: bulk cleanup is strictly user-initiated. Count-based trimming (`MAX_HISTORY = 100`) remains the only automatic maintenance mechanism.
* No deletion of pinned items: pinned clips cannot be deleted via bulk cleanup under any threshold.
* No separate window manager dialogs: all dialogs are hosted as in-window modal overlays over `MainWindow`.

## Constraints
* Wayland compatibility: Modal dialogs must run inside `_ModalBackdrop` rather than standalone X11 modal transients to prevent compositor positioning glitches.
* SQLite WAL integrity: Bulk deletions must run in standard transactions and maintain database file permissions (`0o600`).
* Flatpak and Snap confinement: File operations must only access sandboxed storage paths determined by `DatabaseService`.

## Approaches Considered
1. **In-Window Modal Dialog with Live Count Preview (Selected):**
   * A dedicated `CleanupDialog` opened via `MainWindow._run_modal_overlay`.
   * Queries item count for the selected preset and informs the user before deletion.
   * Prompts with a destructive confirmation button.
   * Why selected: Provides full transparency and prevents accidental deletion, matching existing `FontOptionsDialog` and `ColorOptionsDialog` UX patterns.
2. **Simple Warning Prompt (QMessageBox):**
   * Standard system message box asking "Are you sure?".
   * Why rejected: Does not allow threshold selection, breaks unified styling, and can misplace windows under Wayland.
3. **Settings Page or Menu Item:**
   * Burying the option inside a configuration tab.
   * Why rejected: ClipVault has a streamlined single-window UI without menus; a direct header button matches the theme and font buttons.

## Detailed Architecture Decisions

### Database Layer (DatabaseService)
* `count_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`:
  * If `cutoff_timestamp is None`: queries `SELECT COUNT(*) FROM clipboard_history WHERE pinned = 0`.
  * If `cutoff_timestamp is not None`: queries `SELECT COUNT(*) FROM clipboard_history WHERE pinned = 0 AND timestamp < ?`.
* `delete_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`:
  * If `cutoff_timestamp is None`: executes `DELETE FROM clipboard_history WHERE pinned = 0`.
  * If `cutoff_timestamp is not None`: executes `DELETE FROM clipboard_history WHERE pinned = 0 AND timestamp < ?`.
  * Returns `cursor.rowcount`.
  * Preserves WAL mode and permissions.

### Service Layer (ClipboardService)
* `count_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`:
  * Delegates to `self._db.count_unpinned_older_than(cutoff_timestamp)`.
* `delete_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`:
  * Calls `self._db.delete_unpinned_older_than(cutoff_timestamp)`.
  * Filters `self.history` in memory to retain all pinned items and unpinned items newer than `cutoff_timestamp`.
  * Returns deleted row count.

### Model Layer (ClipboardModel)
* `remove_unpinned_older_than(cutoff_timestamp: float | None = None) -> int`:
  * Filters `self._items` within `beginResetModel()` / `endResetModel()`.
  * Removes all unpinned items where `cutoff_timestamp is None` or `timestamp < cutoff_timestamp`.
  * Returns the count of removed items.

### Dialog Component (CleanupDialog)
* `ui/cleanup_dialog.py` subclassing `QDialog`.
* Heading: "Clear History"
* Description: "Delete unpinned clipboard entries older than the selected threshold."
* Four preset radio options with clear descriptions:
  * "24 Hours" (cutoff = `now - 86,400`)
  * "7 Days" (cutoff = `now - 7 * 86,400`)
  * "30 Days" (cutoff = `now - 30 * 86,400`)
  * "All Unpinned" (cutoff = `None`)
* Live impact indicator: "X unpinned items will be deleted." (updates on radio change).
* Notice: "Pinned items will not be affected."
* Buttons: "Cancel" (`reject()`) and "Clear Items" (`accept()`, disabled if count is 0).

### Main Window Integration (MainWindow)
* Add `self._cleanup_btn` ("🧹") to `_build_header()`.
* Tooltip: "Clear Clipboard History".
* Connected to `_on_open_cleanup_dialog()`.
* On dialog acceptance:
  * Reads selected cutoff from dialog.
  * Calls `self._service.delete_unpinned_older_than(cutoff)`.
  * Calls `self._model.remove_unpinned_older_than(cutoff)`.
  * Calls `self._update_empty_state()`.

## Testing Strategy
* `tests/test_database_bulk_cleanup.py`: Database count and deletion operations across thresholds, verifying pinned isolation.
* `tests/test_cleanup_dialog.py`: Dialog selection, dynamic item counts, accept/reject flows.
* `tests/test_main_window_cleanup.py`: End-to-end integration from header button through deletion and empty state update.
