from __future__ import annotations

import re
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace

import themes
from radial_menu import (
    DEFAULT_RADIAL_ITEMS,
    LIFT_MIN,
    SPLIT_ACTIONS,
    RadialMenuPanel,
    spring_step,
)


class _FakeEvent(SimpleNamespace):
    pass


def _build_panel() -> RadialMenuPanel:
    """Geometry-only panel fixture: hit testing needs no Tk canvas."""
    panel = RadialMenuPanel.__new__(RadialMenuPanel)
    panel.items = DEFAULT_RADIAL_ITEMS
    panel.on_item_selected = None
    panel.on_settings = None
    panel._center_x = 320.0
    panel._center_y = 240.0
    panel._radius = 150.0
    panel._inner_radius = panel._radius * 0.12
    panel._hovered_key = (-1, 0)
    return panel


def _index_of(action_type: str) -> int:
    for index, item in enumerate(DEFAULT_RADIAL_ITEMS):
        if item.action_type == action_type:
            return index
    raise AssertionError(f"{action_type} 不在默认轮盘项中")


class SplitTileGeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.panel = _build_panel()
        self.half = self.panel._radius * 0.20

    def test_brightness_and_contrast_are_split(self) -> None:
        self.assertEqual(SPLIT_ACTIONS, frozenset({"brightness", "contrast"}))

    def test_split_buttons_have_opposite_signs_and_do_not_overlap(self) -> None:
        index = _index_of("brightness")
        ix, iy = self.panel._item_center(index)
        plus, minus = self.panel._split_button_boxes(ix, iy, self.half)
        self.assertEqual((plus[0], minus[0]), (1, -1))
        # ＋ on the left half, － on the right half
        self.assertLess(plus[1], minus[1])
        # both stay inside the tile body
        for _, _bx, _by, bw, bh in (plus, minus):
            self.assertLessEqual(bw, self.half * 1.0)
            self.assertLessEqual(bh, self.half * 1.0)

    def test_plus_half_hits_and_minus_half_hits(self) -> None:
        for action_type in ("brightness", "contrast"):
            with self.subTest(action_type):
                index = _index_of(action_type)
                ix, iy = self.panel._item_center(index)
                for sign, bx, by, _bw, _bh in self.panel._split_button_boxes(
                    ix, iy, self.half
                ):
                    self.assertEqual(
                        self.panel._hit_test(bx, by),
                        (index, sign),
                    )

    def test_tile_body_left_is_increase_right_is_decrease(self) -> None:
        index = _index_of("brightness")
        ix, iy = self.panel._item_center(index)
        # the shared glyph area above the two buttons still follows 左＋右－
        self.assertEqual(
            self.panel._hit_test(ix - self.half * 0.1, iy - self.half * 0.4),
            (index, 1),
        )
        self.assertEqual(
            self.panel._hit_test(ix + self.half * 0.1, iy - self.half * 0.4),
            (index, -1),
        )

    def test_plain_tile_has_no_direction(self) -> None:
        index = _index_of("calculator")
        ix, iy = self.panel._item_center(index)
        self.assertEqual(self.panel._hit_test(ix, iy), (index, 0))

    def test_hub_and_label_zone_are_not_items(self) -> None:
        self.assertEqual(self.panel._hit_test(320.0, 240.0), (-1, 0))
        # top tile's label pill sits further out than the tile body
        self.assertEqual(
            self.panel._hit_test(320.0, 240.0 - self.panel._radius * 1.08),
            (-1, 0),
        )


class SplitTileDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.panel = _build_panel()
        self.calls: list[tuple[str, bool]] = []
        self.panel.on_item_selected = lambda item, decrease: self.calls.append(
            (item.action_type, bool(decrease))
        )
        self.half = self.panel._radius * 0.20

    def _dispatch(self, x: float, y: float, *, right: bool = False) -> None:
        self.panel._dispatch(_FakeEvent(x=x, y=y), right=right)

    def test_minus_half_decreases_with_left_click(self) -> None:
        index = _index_of("brightness")
        ix, iy = self.panel._item_center(index)
        _sign, bx, by, _bw, _bh = self.panel._split_button_boxes(
            ix, iy, self.half
        )[1]
        self._dispatch(bx, by)
        self.assertEqual(self.calls, [("brightness", True)])

    def test_plus_half_increases_with_left_click(self) -> None:
        index = _index_of("contrast")
        ix, iy = self.panel._item_center(index)
        sign, bx, by, _bw, _bh = self.panel._split_button_boxes(
            ix, iy, self.half
        )[0]
        self._dispatch(bx, by)
        self.assertEqual((sign, self.calls), (1, [("contrast", False)]))

    def test_right_click_still_decreases(self) -> None:
        index = _index_of("brightness")
        ix, iy = self.panel._item_center(index)
        self._dispatch(ix, iy - self.half * 0.4, right=True)
        self.assertEqual(self.calls, [("brightness", True)])

    def test_hub_left_click_opens_settings(self) -> None:
        opened: list[bool] = []
        self.panel.on_settings = lambda: opened.append(True)
        self._dispatch(320.0, 240.0)
        self.assertEqual(opened, [True])
        self.assertEqual(self.calls, [])


class HoverSpringTests(unittest.TestCase):
    """The pure integrator behind the hover lift — no Tk window needed."""

    @staticmethod
    def _run(
        start: float, target: float, frames: int = 400, dt: float = 0.016
    ) -> list[float]:
        values: list[float] = []
        current, velocity = start, 0.0
        for _ in range(frames):
            current, velocity, _settling = spring_step(
                current, velocity, target, dt
            )
            values.append(current)
        return values

    def test_resting_tile_reports_no_work(self) -> None:
        self.assertEqual(spring_step(0.0, 0.0, 0.0, 0.016), (0.0, 0.0, False))
        self.assertEqual(spring_step(1.0, 0.0, 1.0, 0.016), (1.0, 0.0, False))

    def test_hover_rises_settles_and_bounces_once(self) -> None:
        values = self._run(0.0, 1.0)
        # Overshoots, then comes back to rest — the visible "bounce".
        self.assertGreater(max(values), 1.0)
        self.assertLess(max(values), 1.35)
        self.assertEqual(values[-1], 1.0)

    def test_release_returns_to_rest(self) -> None:
        values = self._run(1.0, 0.0)
        self.assertEqual(values[-1], 0.0)
        # The rebound may dip below rest, but never by more than the floor.
        self.assertGreaterEqual(min(values), LIFT_MIN)

    def test_settles_well_inside_half_a_second(self) -> None:
        current, velocity = 0.0, 0.0
        for frame in range(40):
            current, velocity, settling = spring_step(
                current, velocity, 1.0, 0.016
            )
            if not settling:
                break
        else:
            self.fail("the lift never settled within 40 frames")
        self.assertEqual((current, velocity), (1.0, 0.0))
        self.assertLess(frame * 0.016, 0.5)

    def test_a_long_frame_cannot_make_it_explode(self) -> None:
        # The caller clamps dt to 0.05 s, but the integrator must stay
        # bounded at that worst-case step too.
        values = self._run(0.0, 1.0, frames=60, dt=0.05)
        self.assertTrue(all(LIFT_MIN <= v <= 1.5 for v in values))
        self.assertEqual(values[-1], 1.0)


def _padx_pair(widget: tk.Widget) -> tuple[int, int]:
    """Normalise ``pack_info()['padx']`` into ``(left, right)``."""
    raw = widget.pack_info().get("padx", 0)
    if isinstance(raw, str):
        parts = raw.split()
        return (int(parts[0]), int(parts[-1])) if parts else (0, 0)
    return (int(raw[0]), int(raw[1]))


def _app_status_texts() -> list[str]:
    """Every status string the app can push into the wheel top bar.

    Read from ``app.py`` itself so the width guard below can never drift away
    from the real copy.
    """
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(
        encoding="utf-8"
    )
    found = re.findall(r'(?:_sync_radial_status|set_status)\("([^"]+)"', source)
    return sorted(set(found), key=len, reverse=True)


class WheelTopBarWidthTests(unittest.TestCase):
    """「风格」 must never be pushed out of the window again.

    pack order is allocation order: the item packed last is the one that gets
    squeezed. Historically that was the style pill (the left status block was
    packed first and always kept its full width), so the longest status text
    plus the 「增强模式」 badge — 661px of demand in a 640px window — silently
    covered the button. The bar is now measured with real Tk font metrics.
    """

    # app.py locks the wheel at minsize 620 / maxsize 640, so 620 is the
    # narrowest legal window the bar has to survive.
    MIN_LEGAL_WIDTH = 620

    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.root = tk.Tk()
        except tk.TclError:  # headless runner: metrics need a display
            raise unittest.SkipTest("no Tk display available") from None
        cls.root.withdraw()
        cls.root.update_idletasks()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.root.destroy()

    def _measure(self, style: str, mode: str, badge: bool, status: str) -> int:
        panel = RadialMenuPanel(self.root, style=style, mode=mode)
        try:
            panel._paste_enhanced = badge
            panel._update_mode_badge()
            panel._status_var.set(status)
            panel.update_idletasks()
            top_bar = panel.winfo_children()[0]
            total = 1  # the 1px hairline under the bar
            for child in top_bar.winfo_children():
                left, right = _padx_pair(child)
                total += child.winfo_reqwidth() + left + right
            return total
        finally:
            panel.destroy()

    def _button_group_width(self, style: str, mode: str, badge: bool) -> int:
        """Demand of the right-hand group only (badge + three buttons).

        These are packed before the status block, so this is the width that
        must always be paid for — everything left of it is allowed to shrink.
        """
        panel = RadialMenuPanel(self.root, style=style, mode=mode)
        try:
            panel._paste_enhanced = badge
            panel._update_mode_badge()
            panel._status_var.set("")
            panel.update_idletasks()
            top_bar = panel.winfo_children()[0]
            total = 0
            for child in top_bar.winfo_children():
                if str(child.pack_info()["side"]) != "right":
                    continue
                left, right = _padx_pair(child)
                total += child.winfo_reqwidth() + left + right
            return total
        finally:
            panel.destroy()

    def test_longest_status_fits_the_narrowest_legal_window(self) -> None:
        statuses = _app_status_texts()
        self.assertTrue(statuses)
        for style, _ in themes.WHEEL_STYLES:
            for mode, _ in themes.WHEEL_MODES:
                for badge in (True, False):
                    for status in statuses:
                        with self.subTest(style=style, mode=mode, badge=badge, status=status):
                            self.assertLessEqual(
                                self._measure(style, mode, badge, status),
                                self.MIN_LEGAL_WIDTH,
                            )

    def test_top_bar_needs_the_same_width_at_any_dpi(self) -> None:
        """150% 缩放（tk scaling 2.0）下顶栏必须和 96 DPI 一样宽。

        轮盘窗口、壁纸与立体图标都是固定像素，只有磅值字号会跟着 DPI 放大；
        这正是「风格」按钮被挤出去的真实原因，所以字号一律走
        ``themes.wheel_font()`` 的负数（像素）写法。
        """
        baseline = self._measure("cream", "light", True, "已开启 · 正在监听")
        original = str(self.root.tk.call("tk", "scaling"))
        try:
            self.root.tk.call("tk", "scaling", 2.0)  # 144 DPI
            scaled = self._measure("cream", "light", True, "已开启 · 正在监听")
        finally:
            self.root.tk.call("tk", "scaling", original)
        self.assertEqual(scaled, baseline)

    def test_wheel_font_helper_uses_pixel_sizes(self) -> None:
        family, size, weight = themes.wheel_font(11)
        self.assertEqual(family, themes.WHEEL_FONT_FAMILY)
        self.assertLess(size, 0, "轮盘字号必须是负数（像素），否则会被 DPI 放大")
        self.assertEqual(size, -int(round(11 * themes.WHEEL_FONT_PIXELS_PER_POINT)))
        self.assertEqual(weight, "bold")
        self.assertEqual(themes.wheel_font(9, "normal")[2], "normal")
        self.assertEqual(
            themes.wheel_font(9, family="Segoe UI Symbol")[0], "Segoe UI Symbol"
        )

    def test_wheel_modules_do_not_use_point_sized_fonts(self) -> None:
        """radial_menu / clipboard_history 里不允许再出现正数字号。"""
        root_dir = Path(__file__).resolve().parents[1]
        pattern = re.compile(r'"(?:Microsoft YaHei UI|Segoe UI Symbol)",\s*\d')
        for name in ("radial_menu.py", "clipboard_history.py"):
            source = (root_dir / name).read_text(encoding="utf-8")
            self.assertIsNone(
                pattern.search(source),
                f"{name} 里还有磅值字号，DPI 缩放会把它撑大",
            )

    def test_build_ui_creates_the_wheel_canvas(self) -> None:
        """顶栏改动的回归保护：画布与磁贴必须还在（漏掉一段就是白盘）。"""
        panel = RadialMenuPanel(self.root, style="cream", mode="light")
        try:
            self.assertIsInstance(panel._canvas, tk.Canvas)
            self.assertEqual(
                [type(child).__name__ for child in panel.winfo_children()],
                ["Frame", "Frame", "Frame"],
            )
        finally:
            panel.destroy()

    def test_status_block_is_the_one_that_yields(self) -> None:
        panel = RadialMenuPanel(self.root, style="cream", mode="light")
        try:
            top_bar = panel.winfo_children()[0]
            order = [str(child.pack_info()["side"]) for child in top_bar.winfo_children()]
            self.assertEqual(order[-1], "left", "状态区必须最后 pack")
            self.assertEqual(order.count("left"), 1, "只有状态区可以从左侧让步")
            self.assertIsInstance(
                top_bar.winfo_children()[-1], tk.Frame
            )
        finally:
            panel.destroy()

    def test_button_group_never_depends_on_the_status_text(self) -> None:
        """The four right-hand controls cost the same whatever the status says.

        Worst legal window is 620px; the status block then gets what is left.
        Keeping the group under 520px means even a much narrower window leaves
        every button whole — only the status text would lose its tail.
        """
        for style, _ in themes.WHEEL_STYLES:
            for mode, _ in themes.WHEEL_MODES:
                for badge in (True, False):
                    with self.subTest(style=style, mode=mode, badge=badge):
                        self.assertLessEqual(
                            self._button_group_width(style, mode, badge), 520
                        )

    def test_status_block_keeps_room_for_the_dot(self) -> None:
        longest = _app_status_texts()[0]
        reserve = self.MIN_LEGAL_WIDTH - self._button_group_width(
            "apple", "dark", True
        )
        # 16px 状态点 + 7px 间距，剩下的都留给文字；至少还能放下 6 个汉字。
        self.assertGreaterEqual(reserve, 23 + 6 * 14)
        self.assertTrue(len(longest) >= 9)


if __name__ == "__main__":
    unittest.main()
