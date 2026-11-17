# Quick Copy Keyboard Shortcuts Design Specification

## Intent and Overview
ClipVault enables fast, keyboard-driven clipboard retrieval for Linux desktops (Wayland and X11). This feature introduces in-window Quick Copy shortcuts (`Ctrl+1` through `Ctrl+9` and `Enter`) that immediately copy the target clip to the system clipboard and dismiss the ClipVault window, returning focus to the previously active application. Manual copy clicks remain available and keep the window open for multi-clip reviews.

## Goals
* Fast in-window clip selection via `Ctrl+1` through `Ctrl+9` mapping to the first nine items in the active (and filtered) list view.
* Instant copy-and-hide workflow on `Ctrl+1..9` and `Enter` key activation.
* Discrete visual shortcut badge (`^1` through `^9`) displayed on the first 9 visible item cards in `ClipboardItemDelegate`.
* Keep the window open when clicking the manual copy button on any card.
* Full compatibility with Ubuntu Wayland and X11 sessions, strict Snap confinement, and Flatpak sandboxes.
* Verified test suite covering keypress filtering, index boundary conditions, search filtering, pinned states, and window lifecycle.

## Non-Goals and Anti-Goals
* No synthetic keystroke injection: ClipVault will not simulate `Ctrl+V` into target windows.
* No in-process global key grabbing: ClipVault will not use `pynput`, `XGrabKey`, or raw `/dev/input` devices.
* No changes to SQLite WAL schema, database migrations, or clipboard monitoring internals.

## Constraints
* Must work seamlessly under GNOME Wayland compositor restrictions where unfocused keyboard snooping is blocked.
* Global toggle shortcut (`Ctrl + Shift + V`) relies on ClipVault's single-instance `QLocalServer` IPC (`toggle.sh` or app launcher command) registered in desktop system keyboard settings.
* Memory usage and rendering performance must remain O(1) across the virtualized `QListView`.

## Approaches Considered
1. **Integrated Qt Shortcuts with Visual Key Badges (Selected):**
   * Use Qt shortcut event handling in `MainWindow` for `Ctrl+1..9` and `Enter`.
   * Look up row index in `ClipboardProxyModel` to respect active search filters and pinned order.
   * Render compact `^1`..`^9` badges in `ClipboardItemDelegate` for visible rows 0 through 8.
   * Dismiss the window on quick copy while leaving it open on manual button clicks.
   * Why selected: Zero extra dependencies, robust across all compositors, and clear visual affordance for users.
2. **Integrated Qt Shortcuts Without Visual Badges:**
   * Same shortcut logic but no badge rendered on cards.
   * Why rejected: Users cannot easily tell which item corresponds to which number key, especially when filtering search results.
3. **Background Global Shortcut Listener Daemon:**
   * Run background thread with `pynput` or X11 event grabber.
   * Why rejected: Completely breaks under Wayland compositors and fails strict Snap confinement.

## Detailed Design Decisions

### In-Window Shortcut Handling in MainWindow
* Bind `Ctrl+1` through `Ctrl+9` (Qt key codes `Key_1` through `Key_9` with `ControlModifier`) in `MainWindow.eventFilter` or `QShortcut`.
* On shortcut trigger:
  * Read visible row index `target_row = key_number - 1`.
  * Validate `0 <= target_row < proxy_model.rowCount()`.
  * If valid, retrieve `FullTextRole` from `proxy_model.index(target_row, 0)`.
  * Call `_on_copy_item("", text)`.
  * Call `self.hide()`.
* On list view `Enter` / activation:
  * Call `_on_copy_item("", text)`.
  * Call `self.hide()`.
* On card manual copy button click:
  * Delegate emits `copy_requested(item_id, text)`.
  * `_on_copy_item(item_id, text)` copies text to clipboard without calling `self.hide()`.
* On `Escape`:
  * If an in-window modal overlay is active (e.g. Font or Color dialog), reject the dialog.
  * Otherwise, call `self.hide()`.

### Visual Shortcut Badges in ClipboardItemDelegate
* For visible rows 0 through 8 in `paint()`:
  * Calculate badge text `f"^{row + 1}"` (or `f"Ctrl+{row + 1}"` based on available width).
  * Render a subtle pill badge in the card header next to the timestamp or line count badge.
  * Theme-aware colors: Match badge background and text to the active theme palette (`card_badge_bg` and `card_badge_text`).

### Search and Filter Compatibility
* Shortcuts and badges operate directly on `ClipboardProxyModel`. When the user types in `_search_bar`, the visible results update dynamically, and `Ctrl+1` through `Ctrl+9` immediately map to the top filtered results.
* If fewer than 9 items are visible, only available rows have active badges and shortcuts. Out-of-bounds keys are safely ignored.

### Testing and Verification
* Automated test suite in `tests/test_quick_copy.py`:
  * Verify `Ctrl+1` through `Ctrl+9` copy text of visible rows and invoke hide.
  * Verify out-of-range keys (e.g., `Ctrl+5` when only 3 items exist) do nothing and do not crash.
  * Verify `Enter` copies selected item and invokes hide.
  * Verify manual copy button copies text and does not invoke hide.
  * Verify search filtering re-maps `Ctrl+1..9` to filtered items.
  * Verify pinned items appear first and receive appropriate shortcuts.
  * Verify empty results handle shortcuts gracefully.
