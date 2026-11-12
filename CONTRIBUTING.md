# Contributing to ClipVault

Welcome to ClipVault. This guide helps engineers set up a local environment, understand the codebase layout, and follow the project's clean-code, DRY, and security standards.

## Local Development Setup

### Prerequisites

- Python 3.12+
- PyQt6 and dependencies from `requirements.txt`
- Optional system clipboard utilities (`xclip`, `xsel`, or `wl-clipboard`)

Create or activate the virtual environment:

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Running Locally

If the Snap package is installed and already running in the background, it holds the `/tmp/ClipVaultLocalServer` socket. Either stop the Snap process first or launch your dev build with an isolated `TMPDIR`:

```bash
# Option 1: Stop Snap instance first
pkill -f "/snap/clipvault-teckscaler"
./venv/bin/python main.py

# Option 2: Run isolated alongside Snap
mkdir -p /tmp/clipvault-dev
TMPDIR=/tmp/clipvault-dev ./venv/bin/python main.py
```

## Project Layout

- `main.py`: Application bootstrap, logging setup, stylesheet loading, and single-instance `QLocalServer` IPC.
- `services/clipboard_service.py`: Three-tier clipboard controller (`ClipboardService`) and off-thread `ClipboardWorker`.
- `services/x11_clipboard_helper.py`: Persistent windowless `QT_QPA_PLATFORM=xcb` background watcher used when CLI clipboard tools are absent.
- `services/sensitive_detector.py`: Pre-read MIME hint checks for password managers.
- `services/database_service.py`: SQLite WAL persistence, schema migrations, and `0o600` file permissions.
- `ui/main_window.py`: Primary window layout, keyboard shortcuts, and preferences orchestration.
- `ui/clipboard_model.py`: `QAbstractListModel` and `QSortFilterProxyModel` for virtualized list rendering and search.
- `ui/clipboard_delegate.py`: Custom `QPainter` card delegate and shared button hit-testing.
- `ui/styles.py`: Single source of truth for QSS generation, color schemes, and font sanitization/scaling helpers.
- `ui/font_dialog.py`: Modal dialog for font family, style, and pixel size configuration.
- `ui/color_dialog.py`: Modal dialog for selecting clipboard color schemes.
- `tests/`: Unit and integration test suites runnable offline under `QT_QPA_PLATFORM=offscreen`.

## Engineering Standards

Refer to [SKILLS.md](SKILLS.md) and [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and security checklist:

- **Single source of truth (DRY):** Centralize constants, sanitization helpers, sorting helpers, and stylesheet/palette definitions rather than duplicating them across UI and service layers.
- **Targeted error handling:** Catch specific exception classes (such as `sqlite3.Error`, `subprocess.SubprocessError`, `OSError`) and log context. Never add silent `except: pass` blocks.
- **Resource safety:** Always use context managers (`with`) for files, sockets, and SQLite connections (`DatabaseService._connect()`).
- **Security invariants:**
  - Always inspect MIME types/targets via `sensitive_detector` before reading clipboard text.
  - Never pass `shell=True` to `subprocess.run` or `subprocess.Popen`.
  - Always use parameterized `?` placeholders in SQLite queries.
  - Sanitize external strings (clipboard payloads, IPC commands, `QSettings` values, and CSS inputs).
- **Thread safety:** Keep all subprocess I/O off the GUI thread and communicate back to `MainWindow` exclusively via Qt signals.

## Running Tests

Run the full unit, integration, and E2E verification suite before submitting changes:

```bash
./test_clipboard.sh
```

## Changelog and Commit Conventions

- Record user-facing features, fixes, and security improvements under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md).
- End every git commit message body with a blank line followed by:

  ```text
  Authored-By-Org: NetTantra Technologies
  ```

