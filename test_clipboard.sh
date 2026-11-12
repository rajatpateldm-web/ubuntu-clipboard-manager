#!/usr/bin/env bash
# ==============================================================================
# test_clipboard.sh
# End-to-end verification and integration test suite for ClipVault
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="$SCRIPT_DIR/venv/bin/python3"
if [ ! -f "$PYTHON" ]; then
    echo "Error: Python virtual environment not found at $PYTHON" >&2
    exit 1
fi

export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"

echo "=================================================="
echo "ClipVault Clipboard Manager Test Suite"
echo "Running in: $SCRIPT_DIR"
echo "Python interpreter: $PYTHON"
echo "Qt QPA Platform: $QT_QPA_PLATFORM"
echo "=================================================="

# 1. Run unit test suite
echo ""
echo "--- Running Unit & Integration Tests ---"
"$PYTHON" -m unittest discover -s tests -v

# 2. Run E2E GUI & Persistence Verification
echo ""
echo "--- Running E2E Component & GUI Verification ---"
"$PYTHON" - << 'EOF'
import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ui.main_window import MainWindow
from ui.clipboard_model import ItemIdRole, FullTextRole, PinnedRole
from services.database_service import DatabaseService

app = QApplication.instance() or QApplication(sys.argv)

print("1. Initializing MainWindow...")
window = MainWindow()
window.show()

print("2. Verifying initial state...")
assert window._model.rowCount() >= 0, "Model should be accessible"

print("3. Simulating new clipboard capture...")
test_id = "test_e2e_clip_001"
test_text = "ClipVault Virtualized Test String"
window._on_new_clip(test_id, test_text, time.time())

# Verify in model
item = window._model.get_item_by_id(test_id)
assert item is not None, "Model should contain the new clip"
assert item["text"] == test_text

print("4. Testing search filter...")
window._search_bar.setText("Virtualized")
assert window._proxy_model.rowCount() == 1, "Filter should match 'Virtualized'"

window._search_bar.setText("NonExistentString12345")
assert window._proxy_model.rowCount() == 0, "Filter should match 0 rows"

window._search_bar.setText("")
assert window._proxy_model.rowCount() > 0, "Clearing filter should restore rows"

print("5. Testing item pinning...")
window._on_pin_toggled(test_id, True)
assert window._model.get_item_by_id(test_id)["pinned"] is True

print("6. Testing item deletion...")
window._on_delete_item(test_id)
assert window._model.get_item_by_id(test_id) is None, "Deleted item must not exist in model"

print("7. Verifying SQLite WAL mode...")
db = DatabaseService()
import sqlite3
with sqlite3.connect(db.db_path) as conn:
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    assert mode.lower() == "wal", f"Expected WAL mode, got {mode}"

window.close()
print("All E2E checks passed successfully!")
EOF

echo ""
echo "=================================================="
echo "All tests passed successfully!"
echo "=================================================="
exit 0
