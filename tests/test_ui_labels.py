from __future__ import annotations

import unittest

from app import (
    KEYBOARD_MAPPING_MOUSE_LABELS,
    KEYBOARD_MAPPING_MOUSE_VALUES,
    MOUSE_TEST_DIAGRAM_LABELS,
    MOUSE_TEST_LABELS,
    SIDE_BUTTON_NAMES,
)
from mouse_hook import MouseControl


class SideButtonLabelTests(unittest.TestCase):
    def test_mouse_test_labels_are_swapped_without_changing_controls(
        self,
    ) -> None:
        self.assertEqual(
            MOUSE_TEST_LABELS[MouseControl.XBUTTON1],
            "下一页 / XButton2",
        )
        self.assertEqual(
            MOUSE_TEST_LABELS[MouseControl.XBUTTON2],
            "上一页 / XButton1",
        )
        self.assertEqual(
            MOUSE_TEST_DIAGRAM_LABELS[MouseControl.XBUTTON1],
            "X2\n下一页",
        )
        self.assertEqual(
            MOUSE_TEST_DIAGRAM_LABELS[MouseControl.XBUTTON2],
            "X1\n上一页",
        )
        self.assertEqual(
            SIDE_BUTTON_NAMES[MouseControl.XBUTTON1],
            "下一页侧键",
        )
        self.assertEqual(
            SIDE_BUTTON_NAMES[MouseControl.XBUTTON2],
            "上一页侧键",
        )

    def test_keyboard_mapping_labels_keep_the_original_event_values(
        self,
    ) -> None:
        self.assertEqual(
            KEYBOARD_MAPPING_MOUSE_LABELS["xbutton1"],
            "X2 / 下一页侧键",
        )
        self.assertEqual(
            KEYBOARD_MAPPING_MOUSE_LABELS["xbutton2"],
            "X1 / 上一页侧键",
        )
        self.assertEqual(
            KEYBOARD_MAPPING_MOUSE_VALUES["X2 / 下一页侧键"],
            "xbutton1",
        )
        self.assertEqual(
            KEYBOARD_MAPPING_MOUSE_VALUES["X1 / 上一页侧键"],
            "xbutton2",
        )


if __name__ == "__main__":
    unittest.main()
