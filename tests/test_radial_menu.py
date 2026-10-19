from __future__ import annotations

import unittest
from types import SimpleNamespace

from radial_menu import (
    DEFAULT_RADIAL_ITEMS,
    SPLIT_ACTIONS,
    RadialMenuPanel,
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


if __name__ == "__main__":
    unittest.main()
