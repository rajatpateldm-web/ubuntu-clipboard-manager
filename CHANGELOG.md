# Changelog

All notable changes to ClipVault are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Bulk history cleanup tool (`ui/cleanup_dialog.py`) allowing users to delete unpinned clipboard entries older than 24 hours, 7 days, 30 days, or all unpinned entries, with a safety confirmation modal and permanent protection for pinned items.
- In-window Quick Copy shortcuts (`Ctrl+1` through `Ctrl+9` and `Enter`) to instantly copy visible clips and dismiss the window, with visible shortcut badges (`^1` through `^9`) on item cards.
- Database service age-based counting and deletion methods (`count_unpinned_older_than` and `delete_unpinned_older_than`).
- Configurable modal backdrop dismissal (`dismiss_on_scrim_click`) in `MainWindow._run_modal_overlay` to ignore backdrop clicks for destructive dialogs while preserving live preview dismissal for settings dialogs.
- Automated unit and integration tests across database bulk cleanup, model pruning, cleanup dialog interaction, and quick copy shortcuts (`tests/test_database_bulk_cleanup.py`, `tests/test_clipboard_model_cleanup.py`, `tests/test_cleanup_dialog.py`, `tests/test_main_window_cleanup.py`, `tests/test_quick_copy.py`).

### Changed

- Updated bottom footer in `MainWindow` to display application version centered without monitor status text.
- Expanded automated test suite from 68 to 108 unit and integration tests.

## [1.1.0] - 2026-11-12

### Added

- Font customization dialog (`ui/font_dialog.py`) with font family presets (`System Default`, `Ubuntu`, `Sans Serif`, `Monospace`, `Serif`), installed system fonts via `QFontDatabase`, font styles (`Regular`, `Bold`, `Italic`, `Bold Italic`), font sizes (`10 px` to `22 px`), live preview, reset, and `QSettings` persistence.
- Clipboard color scheme dialog (`ui/color_dialog.py`) and 10 themeable palettes (`Classic`, `Cyan`, `One Dark`, `Dracula`, `Nord`, `Tokyo Night`, `Monokai`, `Gruvbox`, `Solarized`, `Catppuccin`), each supporting both Dark and Light mode variants.
- Built-in persistent X11/XWayland background clipboard helper (`services/x11_clipboard_helper.py`) so clipboard copies from other applications are captured even when ClipVault is unfocused and external tools (`xclip`, `xsel`, `wl-paste`) are not installed.
- Automated unit and integration tests in `tests/test_font_options.py`, `tests/test_color_options.py`, `tests/test_x11_helper.py`, and `tests/test_security_and_ipc.py`.
- Developer onboarding guide (`CONTRIBUTING.md`) and centralized project tooling configuration (`pyproject.toml`).

### Changed

- Scaled `ClipboardItemDelegate` card height and metadata layout dynamically when font size increases above `13 px`, and consolidated card/button hit-testing geometry into a single `_button_rects()` helper.
- Adjusted `FontOptionsDialog` and `ColorOptionsDialog` into centered in-window modal overlays inside `MainWindow` with compact padding so they remain vertically centered and unclipped under GNOME Wayland compositors.
- Bundled `adwaita-icon-theme` and `hicolor-icon-theme` in `snap/snapcraft.yaml` and configured `$SNAP/usr/share/icons` and `Adwaita` icon theme fallback in `main.py` so Wayland window control icons render inside strict confinement.
- Consolidated SQLite connection lifecycle in `DatabaseService._connect()`, restricted `.db`, `-wal`, and `-shm` file permissions to `0o600`, and enforced non-negative query limits.
- Replaced duplicated Qt focus-capture paths in `ClipboardService` with `_capture_active_qt_clipboard()`, centralized `sort_history_items()` and `MAX_TEXT_LENGTH`, and replaced silent `except Exception: pass` blocks with targeted exception handling and debug logging.
- Hardened IPC command handling in `main.py` with bounded `64`-byte reads, exact `"toggle"` command matching, and socket cleanup.
- Extended copy-back ignore window in `ClipboardService.set_ignore_next()` to `1200 ms` and synced `_worker._last_text` to prevent copy-back re-entry.

## [1.0.0] - 2026-11-12

### Added

- Virtualized `QListView` presentation layer (`ClipboardModel`, `ClipboardProxyModel`, `ClipboardItemDelegate`) for constant `O(1)` memory rendering.
- Three-tier clipboard detection engine supporting `xclip`, `xsel`, `wl-paste` watch/poll modes, and Qt focus fallback.
- Pre-read sensitive clipboard filtering (`services/sensitive_detector.py`) respecting password manager MIME hints (`x-kde-passwordManagerHint`, `application/x-password-manager-hint`, `application/x-copyq-secret`, `application/x-nspasteboard-concealed-type`, `text/x-moz-secret`, and related flags) plus negative override values.
- SQLite WAL persistence (`services/database_service.py`) with automatic `pinned` column migration and 100-item unpinned pruning.
- Dark and Light mode toggle with `QSettings` persistence and keyboard navigation (`Down`, `Enter`, `Delete`, `Escape`).
- Single-instance `QLocalServer` IPC (`ClipVaultLocalServer`) and Snap/Flatpak/Flathub packaging configurations.

