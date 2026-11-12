"""
services/database_service.py
----------------------------
Lightweight SQLite database service for ClipVault history persistence.
"""

from contextlib import contextmanager
import logging
import os
import sqlite3

log = logging.getLogger("ClipVault.database")


class DatabaseService:
    """Handles SQLite database persistence for clipboard items."""

    def __init__(self, db_filename: str = "clipvault.db"):
        # In snap or flatpak environments, use standard sandboxed writable directories
        snap_user_data = os.environ.get("SNAP_USER_DATA")
        flatpak_id = os.environ.get("FLATPAK_ID")
        if snap_user_data:
            self.db_path = os.path.join(snap_user_data, db_filename)
        elif flatpak_id:
            data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
            self.db_path = os.path.join(data_home, "clipvault", db_filename)
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(project_root, db_filename)

        parent_dir = os.path.dirname(os.path.abspath(self.db_path))
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, mode=0o700, exist_ok=True)

        self._init_db()

    @contextmanager
    def _connect(self):
        """Open, yield, and reliably close a SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _restrict_db_permissions(self):
        """Restrict database and WAL sidecar files to owner-only read/write."""
        for suffix in ("", "-wal", "-shm"):
            target = f"{self.db_path}{suffix}"
            if os.path.exists(target):
                os.chmod(target, 0o600)

    def _init_db(self):
        """Create the table automatically if missing and enable WAL mode."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clipboard_history (
                        id TEXT PRIMARY KEY,
                        text TEXT,
                        timestamp REAL,
                        pinned INTEGER DEFAULT 0
                    )
                    """
                )
                # Safely migrate existing databases if they lack the 'pinned' column
                cursor.execute("PRAGMA table_info(clipboard_history)")
                columns = [info[1] for info in cursor.fetchall()]
                if "pinned" not in columns:
                    cursor.execute("ALTER TABLE clipboard_history ADD COLUMN pinned INTEGER DEFAULT 0")
                conn.commit()
            self._restrict_db_permissions()
            log.info("Database initialized successfully at: %s", self.db_path)
        except (sqlite3.Error, OSError) as exc:
            log.error("Failed to initialize SQLite database: %s", exc)

    def save_item(self, item_id: str, text: str, timestamp: float, pinned: bool = False):
        """Save or update a clipboard item immediately in the database."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO clipboard_history (id, text, timestamp, pinned) VALUES (?, ?, ?, ?)",
                    (item_id, text, timestamp, 1 if pinned else 0),
                )
                conn.commit()
            self._restrict_db_permissions()
        except (sqlite3.Error, OSError) as exc:
            log.error("Error saving item %s to database: %s", item_id, exc)

    def set_pinned(self, item_id: str, pinned: bool):
        """Update the pinned state of a clipboard item in the database."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE clipboard_history SET pinned = ? WHERE id = ?",
                    (1 if pinned else 0, item_id),
                )
                conn.commit()
        except (sqlite3.Error, OSError) as exc:
            log.error("Error updating pinned state for item %s: %s", item_id, exc)

    def delete_item(self, item_id: str):
        """Remove a clipboard item from the database using its unique ID."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM clipboard_history WHERE id = ?",
                    (item_id,),
                )
                conn.commit()
        except (sqlite3.Error, OSError) as exc:
            log.error("Error deleting item %s from database: %s", item_id, exc)

    def load_history(self, limit: int = 100) -> list[dict]:
        """
        Load clipboard history from database. Pinned items always come first,
        ordered newest-first, followed by unpinned items, ordered newest-first.
        """
        safe_limit = max(0, int(limit))
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, text, timestamp, pinned FROM clipboard_history "
                    "WHERE pinned = 1 ORDER BY timestamp DESC"
                )
                pinned_rows = cursor.fetchall()

                cursor.execute(
                    "SELECT id, text, timestamp, pinned FROM clipboard_history "
                    "WHERE pinned = 0 ORDER BY timestamp DESC LIMIT ?",
                    (safe_limit,),
                )
                unpinned_rows = cursor.fetchall()

            rows = pinned_rows + unpinned_rows
            return [
                {
                    "id": row[0],
                    "text": row[1],
                    "timestamp": row[2],
                    "pinned": bool(row[3]),
                }
                for row in rows
            ]
        except (sqlite3.Error, OSError) as exc:
            log.error("Error loading clipboard history from database: %s", exc)
            return []

    def prune_old_items(self, keep_limit: int = 100):
        """
        Delete old unpinned entries from the database keeping only the most recent ones.
        Pinned items are excluded from pruning.
        """
        safe_limit = max(0, int(keep_limit))
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM clipboard_history
                    WHERE pinned = 0 AND id NOT IN (
                        SELECT id FROM clipboard_history
                        WHERE pinned = 0
                        ORDER BY timestamp DESC
                        LIMIT ?
                    )
                    """,
                    (safe_limit,),
                )
                conn.commit()
        except (sqlite3.Error, OSError) as exc:
            log.error("Error pruning old items from database: %s", exc)
