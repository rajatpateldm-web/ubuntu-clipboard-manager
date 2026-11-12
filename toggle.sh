#!/bin/bash
# toggle.sh
# ---------
# Helper script to trigger ClipVault's single-instance toggle via local IPC socket.
#
# Register this script's absolute path in Ubuntu -> Settings -> Keyboard -> Custom Shortcuts.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$PROJECT_DIR/venv/bin/python3" "$PROJECT_DIR/main.py"
