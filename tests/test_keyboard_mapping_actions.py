from __future__ import annotations

import queue
import unittest
from unittest.mock import Mock

from actions import ActionResult
from app import MouseGestureApp, _keyboard_shortcut_text
from mouse_hook import KeyboardMappingAction
from settings import (
    KEYBOARD_MAPPING_ACTION_ENHANCED_PASTE,
    KEYBOARD_MAPPING_ACTION_SHORTCUT,
    AppSettings,
    KeyboardMappingSettings,
)


class KeyboardMappingActionTests(unittest.TestCase):
    def _make_app(
        self,
        mapping: KeyboardMappingSettings,
    ) -> MouseGestureApp:
        app = MouseGestureApp.__new__(MouseGestureApp)
        app.settings = AppSettings(keyboard_mappings=(mapping,))
        app.actions = Mock()
        app.ui_events = queue.Queue()
        return app

    def test_enhanced_paste_mapping_reuses_existing_action(self) -> None:
        mapping = KeyboardMappingSettings(
            "xbutton1",
            ("ctrl",),
            "V",
            True,
            KEYBOARD_MAPPING_ACTION_ENHANCED_PASTE,
        )
        app = self._make_app(mapping)
        result = ActionResult(True, "增强粘贴完成", "已新建文件夹")
        app.actions.create_folder_and_paste_clipboard.return_value = result

        app._on_keyboard_mapping_action(KeyboardMappingAction(0))

        app.actions.create_folder_and_paste_clipboard.assert_called_once_with()
        app.actions.send_custom_shortcut.assert_not_called()
        self.assertEqual(
            app.ui_events.get_nowait(),
            ("keyboard_mapping", (0, mapping, result, "success")),
        )

    def test_shortcut_mapping_keeps_original_behavior(self) -> None:
        mapping = KeyboardMappingSettings(
            "xbutton2",
            ("ctrl", "win"),
            "F12",
            True,
            KEYBOARD_MAPPING_ACTION_SHORTCUT,
        )
        app = self._make_app(mapping)
        result = ActionResult(True, "已执行自定义快捷键", "Ctrl+Win+F12")
        app.actions.send_custom_shortcut.return_value = result

        app._on_keyboard_mapping_action(KeyboardMappingAction(0))

        app.actions.send_custom_shortcut.assert_called_once_with(
            ("ctrl", "win"),
            "F12",
        )
        app.actions.create_folder_and_paste_clipboard.assert_not_called()
        self.assertEqual(
            app.ui_events.get_nowait(),
            ("keyboard_mapping", (0, mapping, result, "success")),
        )

    def test_mapping_preview_uses_selected_action(self) -> None:
        enhanced_paste = KeyboardMappingSettings(
            "xbutton1",
            (),
            "A",
            False,
            KEYBOARD_MAPPING_ACTION_ENHANCED_PASTE,
        )
        shortcut = KeyboardMappingSettings(
            "xbutton2",
            ("shift",),
            "F5",
        )

        self.assertEqual(
            _keyboard_shortcut_text(enhanced_paste),
            "增强粘贴",
        )
        self.assertEqual(_keyboard_shortcut_text(shortcut), "Shift+F5")


if __name__ == "__main__":
    unittest.main()
