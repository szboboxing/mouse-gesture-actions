from __future__ import annotations

import unittest

from settings import AppSettings


class SettingsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
