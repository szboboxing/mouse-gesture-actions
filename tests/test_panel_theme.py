"""奶油风控制面板：令牌完整性、对比度、无硬编码颜色、保存设置不丢字段。

这些测试守的是 V2.7.2 的两件事：
* 控制面板（点「更多设置」之后的所有页面）和帮助窗口读同一张奶油令牌表，
  不允许再出现散落的 #RRGGBB；
* 文字与底色之间保持可用的对比度，浅色奶油底不能为了「柔和」把次要文字
  和状态按钮推到看不清的程度。
"""
from __future__ import annotations

import io
import re
import unittest
from unittest.mock import Mock, patch

import help_browser
import themes
from app import MouseGestureApp
from settings import AppSettings

HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}")

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def _relative_luminance(color: str) -> float:
    channels = []
    for index in (1, 3, 5):
        value = int(color[index:index + 2], 16) / 255
        channels.append(
            value / 12.92
            if value <= 0.04045
            else ((value + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(first: str, second: str) -> float:
    high = max(_relative_luminance(first), _relative_luminance(second))
    low = min(_relative_luminance(first), _relative_luminance(second))
    return (high + 0.05) / (low + 0.05)


class PanelPaletteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.palette = themes.panel_palette()

    def test_every_token_is_a_six_digit_hex_colour(self) -> None:
        for name, value in self.palette.items():
            self.assertRegex(value, r"^#[0-9A-F]{6}$")
            self.assertIsInstance(name, str)

    def test_palette_exposes_the_full_token_set(self) -> None:
        required = {
            "nav", "nav_soft", "nav_text", "nav_muted", "nav_link",
            "nav_link_hover", "page", "card", "card_soft", "text", "muted",
            "line", "accent", "accent_soft", "accent_active", "accent_hover",
            "on_accent", "success", "success_soft", "success_active",
            "warning", "warning_soft", "warning_active", "danger",
            "danger_soft", "danger_active", "field", "field_line",
            "selection", "selection_text", "disabled", "disabled_text",
            "diagram", "diagram_soft", "diagram_line", "diagram_strong",
        }
        self.assertEqual(required, set(self.palette))

    def test_caller_cannot_mutate_the_shared_table(self) -> None:
        returned = themes.panel_palette()
        returned["page"] = "#000000"
        self.assertNotEqual(returned["page"], themes.panel_palette()["page"])

    def test_shared_colours_match_the_cream_wheel(self) -> None:
        cream = themes.STYLE_PALETTES["cream"]["light"]
        self.assertEqual(self.palette["card"], cream["tile_body"])
        self.assertEqual(self.palette["text"], cream["status_text"])
        self.assertEqual(self.palette["accent"], cream["active_glyph"])

    def test_status_text_stays_legible_on_accent_buttons(self) -> None:
        for token in ("accent", "accent_active", "success", "warning", "danger"):
            self.assertGreaterEqual(
                _contrast(self.palette[token], self.palette["on_accent"]),
                4.5,
                token,
            )

    def test_body_and_secondary_text_stay_legible(self) -> None:
        for surface in ("page", "card", "card_soft", "field", "accent_soft"):
            self.assertGreaterEqual(
                _contrast(self.palette["text"], self.palette[surface]),
                7.0,
                surface,
            )
            self.assertGreaterEqual(
                _contrast(self.palette["muted"], self.palette[surface]),
                4.5,
                surface,
            )

    def test_sidebar_text_stays_legible_on_espresso(self) -> None:
        self.assertGreaterEqual(
            _contrast(self.palette["nav_text"], self.palette["nav"]), 7.0
        )
        self.assertGreaterEqual(
            _contrast(self.palette["nav_muted"], self.palette["nav"]), 4.5
        )
        self.assertGreaterEqual(
            _contrast(self.palette["nav_link"], self.palette["nav"]), 4.5
        )

    def test_card_edges_are_visible_on_both_backgrounds(self) -> None:
        for surface in ("page", "card", "card_soft"):
            self.assertGreater(
                _contrast(self.palette["line"], self.palette[surface]), 1.35,
                surface,
            )


class NoHardcodedColourTests(unittest.TestCase):
    """控制面板和帮助窗口的颜色只能来自 themes.panel_palette()。"""

    def test_widget_modules_contain_no_hex_literals(self) -> None:
        for filename in ("app.py", "help_browser.py"):
            with io.open(
                PROJECT_ROOT / filename, encoding="utf-8"
            ) as handle:
                source = handle.read()
            self.assertEqual(HEX_RE.findall(source), [], filename)

    def test_help_browser_reuses_the_panel_palette(self) -> None:
        palette = themes.panel_palette()
        self.assertEqual(help_browser.PAGE_BG, palette["page"])
        self.assertEqual(help_browser.CARD_BG, palette["card"])
        self.assertEqual(help_browser.TEXT, palette["text"])
        self.assertEqual(help_browser.MUTED, palette["muted"])
        self.assertEqual(help_browser.LINE, palette["line"])
        self.assertEqual(help_browser.BLUE, palette["accent"])
        self.assertEqual(help_browser.BLUE_ACTIVE, palette["accent_active"])
        self.assertEqual(help_browser.BLUE_SOFT, palette["accent_soft"])
        self.assertEqual(help_browser.DISABLED_BG, palette["disabled"])
        self.assertEqual(help_browser.DISABLED_FG, palette["disabled_text"])
        self.assertEqual(help_browser.ON_ACCENT, palette["on_accent"])

    def test_app_colours_are_the_panel_palette(self) -> None:
        import app

        self.assertEqual(app.COLORS, themes.panel_palette())
        self.assertIsNot(app.COLORS, themes.PANEL_COLORS)


class _Var:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value


class SaveSettingsTests(unittest.TestCase):
    """「保存设置」只改它负责的三个开关，别把其他字段重置回默认值。"""

    def _make_app(self, settings: AppSettings) -> MouseGestureApp:
        app = MouseGestureApp.__new__(MouseGestureApp)
        app.settings = settings
        app.launch_var = _Var(False)
        app.minimize_var = _Var(True)
        app.radial_menu_var = _Var(False)
        app._collect_keyboard_mappings = Mock(return_value=())
        app._apply_keyboard_mappings_to_hook = Mock()
        app._append_log = Mock()
        app._show_toast = Mock()
        return app

    def test_save_keeps_wheel_clipboard_and_ai_settings(self) -> None:
        original = AppSettings(
            launch_listening=True,
            minimize_on_start=False,
            show_radial_menu_on_start=True,
            clipboard_history_enabled=False,
            wheel_style="apple",
            wheel_mode="dark",
            ai_tool_target="D:/tools/ai.exe",
            custom_button_name="截图",
            custom_button_target="ms-screenclip:",
        )
        app = self._make_app(original)

        with patch.object(AppSettings, "save") as save:
            app.save_settings()

        saved = app.settings
        self.assertEqual(saved.wheel_style, "apple")
        self.assertEqual(saved.wheel_mode, "dark")
        self.assertFalse(saved.clipboard_history_enabled)
        self.assertEqual(saved.ai_tool_target, "D:/tools/ai.exe")
        self.assertEqual(saved.custom_button_name, "截图")
        self.assertEqual(saved.custom_button_target, "ms-screenclip:")
        self.assertEqual(saved.screenshot_side_buttons, original.screenshot_side_buttons)
        self.assertEqual(saved.radial_menu_items, original.radial_menu_items)
        # 只有面板上真正的三个开关会被写回
        self.assertFalse(saved.launch_listening)
        self.assertTrue(saved.minimize_on_start)
        self.assertFalse(saved.show_radial_menu_on_start)
        self.assertEqual(saved.keyboard_mappings, ())
        save.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
