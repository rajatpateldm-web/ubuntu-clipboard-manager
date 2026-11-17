"""
tests/test_cleanup_dialog.py
----------------------------
Unit tests for CleanupDialog component.
"""

import time
import unittest
from PyQt6.QtWidgets import QApplication

from ui.cleanup_dialog import CleanupDialog


class TestCleanupDialog(unittest.TestCase):
    """Test preset selection, cutoff calculation, and count updates in CleanupDialog."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(["-platform", "offscreen"])

    def test_default_preset_selection(self):
        """CleanupDialog defaults to 24 Hours preset."""
        dialog = CleanupDialog(count_callback=lambda cutoff: 5)
        self.assertEqual(dialog.selected_preset_key(), "24_hours")
        cutoff = dialog.selected_cutoff()
        self.assertIsNotNone(cutoff)
        # Cutoff should be approximately 24 hours ago
        expected_cutoff = time.time() - 86400
        self.assertAlmostEqual(cutoff, expected_cutoff, delta=5.0)

    def test_all_unpinned_preset_cutoff(self):
        """All Unpinned preset returns None as cutoff."""
        dialog = CleanupDialog(count_callback=lambda cutoff: 10)
        dialog.select_preset("all_unpinned")
        self.assertEqual(dialog.selected_preset_key(), "all_unpinned")
        self.assertIsNone(dialog.selected_cutoff())

    def test_count_callback_updates_label_and_button_state(self):
        """Changing preset updates impact label and disables delete button if count is 0."""
        counts = {
            "24_hours": 0,
            "7_days": 3,
            "30_days": 8,
            "all_unpinned": 15,
        }

        def mock_counter(cutoff):
            # If cutoff is None, return all_unpinned count
            if cutoff is None:
                return counts["all_unpinned"]
            diff = time.time() - cutoff
            if diff < 100000:  # ~24h
                return counts["24_hours"]
            elif diff < 700000:  # ~7d
                return counts["7_days"]
            else:
                return counts["30_days"]

        dialog = CleanupDialog(count_callback=mock_counter)

        # 24 hours has 0 items: delete button must be disabled
        self.assertEqual(dialog.matching_count(), 0)
        self.assertFalse(dialog._delete_btn.isEnabled())
        self.assertIn("No unpinned items", dialog._count_label.text())

        # Switch to 7 days: 3 items, button enabled
        dialog.select_preset("7_days")
        self.assertEqual(dialog.matching_count(), 3)
        self.assertTrue(dialog._delete_btn.isEnabled())
        self.assertIn("3 unpinned items will be deleted", dialog._count_label.text())

        # Switch to All Unpinned: 15 items, button enabled
        dialog.select_preset("all_unpinned")
        self.assertEqual(dialog.matching_count(), 15)
        self.assertTrue(dialog._delete_btn.isEnabled())
        self.assertIn("15 unpinned items will be deleted", dialog._count_label.text())

    def test_dialog_accept_and_reject(self):
        """Clicking cancel rejects; clicking delete accepts."""
        dialog = CleanupDialog(count_callback=lambda cutoff: 5)
        dialog._cancel_btn.click()
        self.assertEqual(dialog.result(), CleanupDialog.DialogCode.Rejected)

        dialog2 = CleanupDialog(count_callback=lambda cutoff: 5)
        dialog2._delete_btn.click()
        self.assertEqual(dialog2.result(), CleanupDialog.DialogCode.Accepted)


if __name__ == "__main__":
    unittest.main()
