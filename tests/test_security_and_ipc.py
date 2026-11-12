"""
tests/test_security_and_ipc.py
Security, resource-management, and bounds-checking tests for ClipVault.
"""

import os
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch

from main import _MAX_IPC_BYTES, parse_ipc_command
from services.clipboard_service import MAX_TEXT_LENGTH, normalize_text, sort_history_items
from services.database_service import DatabaseService


class TestSecurityAndResourceSafety(unittest.TestCase):
    """Verify file permissions, payload bounds, and shared sorting helpers."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="clipvault_sec_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_and_wal_permissions_restricted_to_owner(self):
        with patch.dict(os.environ, {"SNAP_USER_DATA": self.temp_dir}):
            db = DatabaseService("sec_test.db")
            db.save_item("item1", "hello", 1000.0, pinned=False)

            for suffix in ("", "-wal", "-shm"):
                path = f"{db.db_path}{suffix}"
                if os.path.exists(path):
                    mode = stat.S_IMODE(os.stat(path).st_mode)
                    self.assertEqual(mode, 0o600, f"Expected 0o600 on {path}, got {oct(mode)}")

    def test_database_negative_limit_handled_safely(self):
        with patch.dict(os.environ, {"SNAP_USER_DATA": self.temp_dir}):
            db = DatabaseService("sec_limit.db")
            db.save_item("item1", "hello", 1000.0, pinned=False)
            self.assertEqual(db.load_history(limit=-5), [])
            db.prune_old_items(keep_limit=-1)
            self.assertEqual(db.load_history(limit=10), [])

    def test_normalize_text_caps_oversized_payload_and_strips_nulls(self):
        payload = "x\0" * (MAX_TEXT_LENGTH + 500)
        normalized = normalize_text(payload)
        self.assertNotIn("\0", normalized)
        self.assertLessEqual(len(normalized), MAX_TEXT_LENGTH)

    def test_sort_history_items_places_pinned_newest_first(self):
        items = [
            {"id": "1", "pinned": False, "timestamp": 100.0},
            {"id": "2", "pinned": True, "timestamp": 50.0},
            {"id": "3", "pinned": False, "timestamp": 200.0},
            {"id": "4", "pinned": True, "timestamp": 150.0},
        ]
        sort_history_items(items)
        self.assertEqual([item["id"] for item in items], ["4", "2", "3", "1"])

    def test_parse_ipc_command_bounds_and_exact_matching(self):
        self.assertEqual(parse_ipc_command(b"toggle\n"), "toggle")
        self.assertNotEqual(parse_ipc_command(b"not_toggle\n"), "toggle")
        oversized = (b" " * _MAX_IPC_BYTES) + b"toggle"
        self.assertEqual(parse_ipc_command(oversized), "")


if __name__ == "__main__":
    unittest.main()
