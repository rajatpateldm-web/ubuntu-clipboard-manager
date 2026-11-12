#!/bin/sh
# Launcher script for ClipVault inside Flatpak
export PYTHONPATH="/app/share/clipvault:${PYTHONPATH}"
exec python3 /app/share/clipvault/main.py "$@"
