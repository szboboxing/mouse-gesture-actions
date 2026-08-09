from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from actions import ActionResult
from app import (
    GITHUB_PROJECT_NAME,
    GITHUB_PROJECT_URL,
    KEYBOARD_MAPPING_MODIFIER_LABELS,
    KEYBOARD_MAPPING_MOUSE_LABELS,
    KEYBOARD_MAPPING_MOUSE_VALUES,
    MOUSE_TEST_DIAGRAM_LABELS,
    MOUSE_TEST_LABELS,
    MouseGestureApp,
    SIDE_BUTTON_NAMES,
)
from mouse_hook import MouseControl


class SideButtonLabelTests(unittest.TestCase):
    def test_keyboard_mapping_modifier_labels_include_win(self) -> None:
        self.assertEqual(
            KEYBOARD_MAPPING_MODIFIER_LABELS,
            {
                "ctrl": "Ctrl",
                "alt": "Alt",
                "shift": "Shift",
                "win": "Win",
            },
        )

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


class GitHubLinkTests(unittest.TestCase):
    def test_project_name_and_url_match_the_public_repository(self) -> None:
        self.assertEqual(GITHUB_PROJECT_NAME, "鼠标手势动作小工具")
        self.assertEqual(
            GITHUB_PROJECT_URL,
            "https://github.com/szboboxing/mouse-gesture-actions",
        )

    def test_clicking_link_opens_the_exact_project_url(self) -> None:
        application = MouseGestureApp.__new__(MouseGestureApp)
        application.actions = Mock()
        application.root = Mock()
        application.actions.open_custom_target.return_value = ActionResult(
            True,
            "已启动GitHub 项目",
            GITHUB_PROJECT_URL,
        )

        result = application._open_github_project()

        self.assertTrue(result.success)
        application.actions.open_custom_target.assert_called_once_with(
            GITHUB_PROJECT_URL,
            "GitHub 项目",
        )

    @patch("app.messagebox.showerror")
    def test_link_failure_is_reported(self, showerror: Mock) -> None:
        application = MouseGestureApp.__new__(MouseGestureApp)
        application.actions = Mock()
        application.root = Mock()
        application.actions.open_custom_target.return_value = ActionResult(
            False,
            "GitHub 项目启动失败",
            "未找到默认浏览器",
        )

        result = application._open_github_project()

        self.assertFalse(result.success)
        showerror.assert_called_once_with(
            "GitHub 链接打开失败",
            "GitHub 项目启动失败\n\n未找到默认浏览器",
            parent=application.root,
        )


if __name__ == "__main__":
    unittest.main()
