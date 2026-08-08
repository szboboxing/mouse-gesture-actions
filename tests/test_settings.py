from __future__ import annotations

import unittest

from settings import (
    AppSettings,
    KEYBOARD_MAPPING_KEYS,
    KEYBOARD_MAPPING_MODIFIERS,
    KeyboardMappingSettings,
)


class SettingsTests(unittest.TestCase):
    def test_keyboard_mapping_options_include_win_and_function_keys(
        self,
    ) -> None:
        self.assertEqual(
            KEYBOARD_MAPPING_MODIFIERS,
            ("ctrl", "alt", "shift", "win"),
        )
        self.assertEqual(KEYBOARD_MAPPING_KEYS[:2], ("A", "B"))
        self.assertEqual(KEYBOARD_MAPPING_KEYS[-12:], tuple(
            f"F{number}" for number in range(1, 13)
        ))

    def test_old_gesture_and_combo_settings_are_ignored(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "sensitivity": "标准",
                "double_swipe_interval_ms": 850,
                "copy_shortcut": "Ctrl+C",
                "paste_shortcut": "Ctrl+V",
                "screenshot_shortcut": "Win+Shift+S",
                "screenshot_combo_interval_ms": 250,
            }
        )

        self.assertFalse(hasattr(settings, "screenshot_combo_interval_ms"))
        self.assertEqual(
            settings.screenshot_side_buttons,
            ("xbutton1", "xbutton2"),
        )
        self.assertEqual(settings.custom_button_1_name, "自定义 1")
        self.assertEqual(settings.custom_button_2_name, "自定义 2")
        self.assertEqual(settings.custom_button_1_target, "")
        self.assertEqual(settings.custom_button_2_target, "")

    def test_custom_button_names_are_trimmed_and_limited(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "custom_button_1_name": "  工作资料快速打开按钮超长名称  ",
                "custom_button_1_target": "  D:\\work  ",
            }
        )

        self.assertEqual(settings.custom_button_1_name, "工作资料快速打开按钮超长")
        self.assertEqual(settings.custom_button_1_target, "D:\\work")

    def test_confirmed_screenshot_side_buttons_are_normalized(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "screenshot_side_buttons": [
                    "xbutton2",
                    "unknown",
                    "xbutton2",
                ]
            }
        )

        self.assertEqual(settings.screenshot_side_buttons, ("xbutton2",))

    def test_invalid_side_button_config_uses_compatible_default(self) -> None:
        for value in ([], "xbutton1", ["unknown"]):
            with self.subTest(value=value):
                settings = AppSettings.from_mapping(
                    {"screenshot_side_buttons": value}
                )
                self.assertEqual(
                    settings.screenshot_side_buttons,
                    ("xbutton1", "xbutton2"),
                )

    def test_keyboard_mappings_have_compatible_defaults(self) -> None:
        settings = AppSettings.from_mapping({})

        self.assertEqual(
            settings.keyboard_mappings,
            (
                KeyboardMappingSettings(
                    "xbutton1", ("ctrl",), "C", False
                ),
                KeyboardMappingSettings(
                    "xbutton2", ("ctrl",), "V", False
                ),
            ),
        )

    def test_keyboard_mapping_values_are_normalized(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "keyboard_mappings": [
                    {
                        "mouse_button": "XBUTTON2",
                        "modifiers": [
                            "shift",
                            "CTRL",
                            "unsupported",
                            "alt",
                            "win",
                        ],
                        "key": "f12",
                        "enabled": True,
                    },
                    {
                        "mouse_button": "xbutton1",
                        "modifiers": [],
                        "key": "z",
                        "enabled": True,
                    },
                ]
            }
        )

        self.assertEqual(
            settings.keyboard_mappings,
            (
                KeyboardMappingSettings(
                    "xbutton2",
                    ("ctrl", "alt", "shift", "win"),
                    "F12",
                    True,
                ),
                KeyboardMappingSettings(
                    "xbutton1",
                    (),
                    "Z",
                    True,
                ),
            ),
        )

    def test_invalid_keyboard_mapping_values_use_defaults(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "keyboard_mappings": [
                    {
                        "mouse_button": "middle",
                        "modifiers": "ctrl",
                        "key": "F13",
                        "enabled": "yes",
                    }
                ]
            }
        )

        self.assertEqual(
            settings.keyboard_mappings[0],
            KeyboardMappingSettings(
                "xbutton1", ("ctrl",), "C", False
            ),
        )

    def test_only_one_mapping_can_enable_the_same_side_button(self) -> None:
        settings = AppSettings.from_mapping(
            {
                "keyboard_mappings": [
                    {
                        "mouse_button": "xbutton1",
                        "modifiers": ["ctrl"],
                        "key": "c",
                        "enabled": True,
                    },
                    {
                        "mouse_button": "xbutton1",
                        "modifiers": ["ctrl"],
                        "key": "v",
                        "enabled": True,
                    },
                ]
            }
        )

        self.assertTrue(settings.keyboard_mappings[0].enabled)
        self.assertFalse(settings.keyboard_mappings[1].enabled)


if __name__ == "__main__":
    unittest.main()
