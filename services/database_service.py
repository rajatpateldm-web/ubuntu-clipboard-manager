"""
services/database_service.py
----------------------------
Lightweight SQLite database service for ClipVault history persistence.
"""

import sqlite3
import os
import logging

log = logging.getLogger("ClipVault.database")

class DatabaseService:
    """
    Handles SQLite database persistence for clipboard items.
    """

    def __init__(self, db_filename="clipvault.db"):
        # In snap or flatpak environments, use standard sandboxed writable directories
        snap_user_data = os.environ.get("SNAP_USER_DATA")
        flatpak_id = os.environ.get("FLATPAK_ID")
        if snap_user_data:
            self.db_path = os.path.join(snap_user_data, db_filename)
        elif flatpak_id:
            data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
            self.db_path = os.path.join(data_home, "clipvault", db_filename)
        else:
            # Resolve the database path relative to the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(project_root, db_filename)
        parent_dir = os.path.dirname(os.path.abspath(self.db_path))
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create the table automatically if it is missing and enable WAL mode."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS clipboard_history (
                        id TEXT PRIMARY KEY,
                        text TEXT,
                        timestamp REAL,
                        pinned INTEGER DEFAULT 0
                    )
                """)
                # Safely migrate existing databases if they don't have 'pinned' column
                cursor.execute("PRAGMA table_info(clipboard_history)")
                columns = [info[1] for info in cursor.fetchall()]
                if "pinned" not in columns:
                    cursor.execute("ALTER TABLE clipboard_history ADD COLUMN pinned INTEGER DEFAULT 0")
                conn.commit()
            if os.path.exists(self.db_path):
                os.chmod(self.db_path, 0o600)
            log.info(f"Database initialized successfully at: {self.db_path}")
        except Exception as e:
            log.error(f"Failed to initialize SQLite database: {e}")

    def save_item(self, item_id: str, text: str, timestamp: float, pinned: bool = False):
        """
        Save a clipboard item immediately to the database.
        Uses INSERT OR REPLACE to handle potential unique ID updates.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO clipboard_history (id, text, timestamp, pinned) VALUES (?, ?, ?, ?)",
                    (item_id, text, timestamp, 1 if pinned else 0)
                )
                conn.commit()
        except Exception as e:
            log.error(f"Error saving item {item_id} to database: {e}")

    def set_pinned(self, item_id: str, pinned: bool):
        """Update the pinned state of a clipboard item in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE clipboard_history SET pinned = ? WHERE id = ?",
                    (1 if pinned else 0, item_id)
                )
                conn.commit()
        except Exception as e:
            log.error(f"Error updating pinned state for item {item_id}: {e}")

    def delete_item(self, item_id: str):
        """Remove a clipboard item from the database using its unique ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM clipboard_history WHERE id = ?",
                    (item_id,)
                )
                conn.commit()
        except Exception as e:
            log.error(f"Error deleting item {item_id} from database: {e}")

    def load_history(self, limit: int = 100) -> list[dict]:
        """
        Load clipboard history from database. Pinned items always come first,
        ordered newest-first, followed by unpinned items, ordered newest-first.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Load pinned items (no limit)
                cursor.execute(
                    "SELECT id, text, timestamp, pinned FROM clipboard_history WHERE pinned = 1 ORDER BY timestamp DESC"
                )
                pinned_rows = cursor.fetchall()
                
                # Load unpinned items (with limit)
                cursor.execute(
                    "SELECT id, text, timestamp, pinned FROM clipboard_history WHERE pinned = 0 ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                unpinned_rows = cursor.fetchall()
                
                rows = pinned_rows + unpinned_rows
                return [
                    {
                        "id": row[0],
                        "text": row[1],
                        "timestamp": row[2],
                        "pinned": bool(row[3])
                    }
                    for row in rows
                ]
        except Exception as e:
            log.error(f"Error loading clipboard history from database: {e}")
            return []

    def prune_old_items(self, keep_limit: int = 100):
        """
        Delete old unpinned entries from the database keeping only the most recent ones.
        Pinned items are excluded from pruning.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
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
                    (keep_limit,)
                )
                conn.commit()
        except Exception as e:
            log.error(f"Error pruning old items from database: {e}")
