from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from actions import (
    ENHANCED_PASTE_DELAY_SECONDS,
    KEYEVENTF_KEYUP,
    VK_ALT,
    VK_C,
    VK_CONTROL,
    VK_F1,
    VK_LWIN,
    VK_N,
    VK_S,
    VK_SHIFT,
    VK_V,
    ActionResult,
    SystemActions,
)


class FakeUser32:
    def __init__(self) -> None:
        self.keybd_event = Mock()


class FixedShortcutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actions = SystemActions.__new__(SystemActions)
        self.actions._user32 = FakeUser32()

    def test_copy_sends_ctrl_c_in_press_release_order(self) -> None:
        result = self.actions.copy_selection()

        self.assertTrue(result.success)
        self.assertEqual(result.detail, "Ctrl+C")
        self.assertEqual(
            self.actions._user32.keybd_event.call_args_list,
            [
                call(VK_CONTROL, 0, 0, 0),
                call(VK_C, 0, 0, 0),
                call(VK_C, 0, KEYEVENTF_KEYUP, 0),
                call(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0),
            ],
        )

    def test_screenshot_sends_win_shift_s_in_press_release_order(self) -> None:
        result = self.actions.capture_screenshot()

        self.assertTrue(result.success)
        self.assertEqual(result.detail, "Win+Shift+S")
        self.assertEqual(
            self.actions._user32.keybd_event.call_args_list,
            [
                call(VK_LWIN, 0, 0, 0),
                call(VK_SHIFT, 0, 0, 0),
                call(VK_S, 0, 0, 0),
                call(VK_S, 0, KEYEVENTF_KEYUP, 0),
                call(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0),
                call(VK_LWIN, 0, KEYEVENTF_KEYUP, 0),
            ],
        )

    def test_custom_shortcut_orders_modifiers_and_releases_in_reverse(
        self,
    ) -> None:
        result = self.actions.send_custom_shortcut(
            ("win", "shift", "ctrl", "alt"),
            "a",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.detail, "Ctrl+Alt+Shift+Win+A")
        self.assertEqual(
            self.actions._user32.keybd_event.call_args_list,
            [
                call(VK_CONTROL, 0, 0, 0),
                call(VK_ALT, 0, 0, 0),
                call(VK_SHIFT, 0, 0, 0),
                call(VK_LWIN, 0, 0, 0),
                call(ord("A"), 0, 0, 0),
                call(ord("A"), 0, KEYEVENTF_KEYUP, 0),
                call(VK_LWIN, 0, KEYEVENTF_KEYUP, 0),
                call(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0),
                call(VK_ALT, 0, KEYEVENTF_KEYUP, 0),
                call(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0),
            ],
        )

    def test_custom_shortcut_allows_a_letter_without_modifiers(
        self,
    ) -> None:
        result = self.actions.send_custom_shortcut((), "b")

        self.assertTrue(result.success)
        self.assertEqual(result.detail, "B")
        self.assertEqual(
            self.actions._user32.keybd_event.call_args_list,
            [
                call(ord("B"), 0, 0, 0),
                call(ord("B"), 0, KEYEVENTF_KEYUP, 0),
            ],
        )

    def test_custom_shortcut_sends_function_key(self) -> None:
        result = self.actions.send_custom_shortcut(("win",), "f12")

        self.assertTrue(result.success)
        self.assertEqual(result.detail, "Win+F12")
        self.assertEqual(
            self.actions._user32.keybd_event.call_args_list,
            [
                call(VK_LWIN, 0, 0, 0),
                call(VK_F1 + 11, 0, 0, 0),
                call(VK_F1 + 11, 0, KEYEVENTF_KEYUP, 0),
                call(VK_LWIN, 0, KEYEVENTF_KEYUP, 0),
            ],
        )

    def test_custom_shortcut_rejects_invalid_modifier(self) -> None:
        result = self.actions.send_custom_shortcut(("meta",), "A")

        self.assertFalse(result.success)
        self.assertIn("修饰键", result.detail)
        self.actions._user32.keybd_event.assert_not_called()

    def test_custom_shortcut_rejects_unsupported_key(self) -> None:
        result = self.actions.send_custom_shortcut(("ctrl",), "F13")

        self.assertFalse(result.success)
        self.assertIn("F1-F12", result.detail)
        self.actions._user32.keybd_event.assert_not_called()


class EnhancedPasteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actions = SystemActions.__new__(SystemActions)
        self.actions._send_keys = Mock(
            side_effect=[
                ActionResult(True, "已执行新建文件夹", "Ctrl+Shift+N"),
                ActionResult(True, "已执行粘贴剪贴板内容", "Ctrl+V"),
            ]
        )

    @patch("actions.pythoncom.CoUninitialize")
    @patch("actions.pythoncom.CoInitialize")
    @patch("actions.time.sleep")
    @patch(
        "actions.get_active_explorer_directory",
        return_value=Path("D:/work"),
    )
    def test_creates_folder_then_pastes_into_rename_field(
        self,
        _get_directory: Mock,
        sleep: Mock,
        co_initialize: Mock,
        co_uninitialize: Mock,
    ) -> None:
        result = self.actions.create_folder_and_paste_clipboard()

        self.assertTrue(result.success)
        self.assertEqual(
            self.actions._send_keys.call_args_list,
            [
                call(
                    (VK_CONTROL, VK_SHIFT, VK_N),
                    "新建文件夹",
                    "Ctrl+Shift+N",
                ),
                call(
                    (VK_CONTROL, VK_V),
                    "粘贴剪贴板内容",
                    "Ctrl+V",
                ),
            ],
        )
        sleep.assert_called_once_with(ENHANCED_PASTE_DELAY_SECONDS)
        co_initialize.assert_called_once_with()
        co_uninitialize.assert_called_once_with()

    @patch("actions.pythoncom.CoUninitialize")
    @patch("actions.pythoncom.CoInitialize")
    @patch("actions.get_active_explorer_directory", return_value=None)
    def test_rejects_non_explorer_foreground_window(
        self,
        _get_directory: Mock,
        co_initialize: Mock,
        co_uninitialize: Mock,
    ) -> None:
        result = self.actions.create_folder_and_paste_clipboard()

        self.assertFalse(result.success)
        self.assertIn("资源管理器", result.detail)
        self.actions._send_keys.assert_not_called()
        co_initialize.assert_called_once_with()
        co_uninitialize.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
