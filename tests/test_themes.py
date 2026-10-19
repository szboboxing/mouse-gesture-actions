from __future__ import annotations

import re
import unittest

import themes
from radial_menu import DEFAULT_RADIAL_ITEMS


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class StyleAndModeTests(unittest.TestCase):
    def test_three_styles_and_two_modes_are_offered(self) -> None:
        self.assertEqual(len(themes.WHEEL_STYLES), 3)
        self.assertEqual(len(themes.WHEEL_MODES), 2)
        self.assertEqual(
            themes.STYLE_KEYS, ("frost", "graphite", "pastel")
        )
        self.assertEqual(themes.MODE_KEYS, ("light", "dark"))
        self.assertEqual(
            len({key for key, _ in themes.WHEEL_STYLES}),
            len(themes.WHEEL_STYLES),
        )
        self.assertEqual(
            len({key for key, _ in themes.WHEEL_MODES}),
            len(themes.WHEEL_MODES),
        )

    def test_every_style_label_and_mode_label_is_unique_chinese(self) -> None:
        labels = [label for _, label in themes.WHEEL_STYLES]
        self.assertEqual(len(set(labels)), len(labels))
        for label in labels + [label for _, label in themes.WHEEL_MODES]:
            self.assertTrue(label.strip())

    def test_unknown_values_fall_back_to_defaults(self) -> None:
        for junk in ("", "neon", None, 7, "FROST"):
            with self.subTest(value=junk):
                self.assertEqual(
                    themes.normalize_style(junk), themes.DEFAULT_WHEEL_STYLE
                )
                self.assertEqual(
                    themes.normalize_mode(junk), themes.DEFAULT_WHEEL_MODE
                )

    def test_style_button_cycles_through_every_style_once(self) -> None:
        seen = []
        style = themes.DEFAULT_WHEEL_STYLE
        for _ in range(len(themes.STYLE_KEYS)):
            style = themes.next_style(style)
            seen.append(style)
        self.assertEqual(seen, ["graphite", "pastel", "frost"])

    def test_mode_button_toggles_between_light_and_dark(self) -> None:
        self.assertEqual(themes.next_mode("light"), "dark")
        self.assertEqual(themes.next_mode("dark"), "light")
        self.assertEqual(themes.next_mode("junk"), "dark")

    def test_labels_are_reported_for_the_current_choice(self) -> None:
        self.assertEqual(themes.style_label("frost"), "冰霜")
        self.assertEqual(themes.style_label("graphite"), "烟晶")
        self.assertEqual(themes.style_label("pastel"), "彩璃")
        self.assertEqual(themes.mode_label("light"), "明亮")
        self.assertEqual(themes.mode_label("dark"), "暗夜")


class PaletteTests(unittest.TestCase):
    def test_light_and_dark_palettes_expose_the_same_keys(self) -> None:
        light = set(themes.PALETTES["light"])
        dark = set(themes.PALETTES["dark"])
        self.assertEqual(light, dark)
        # The wheel reads these keys while painting.
        for key in (
            "base",
            "top_bar_border",
            "status_text",
            "status_muted",
            "tile_body",
            "tile_shadow",
            "tile_rim_target",
            "tile_glyph_target",
            "label_body",
            "label_text",
            "hub_body",
            "hub_glyph",
            "hub_text",
            "divider",
            "minus_body",
            "minus_rim",
            "minus_text",
            "pill_body",
            "pill_rim",
            "pill_text",
            "pill_hover",
            "orbit",
            "row_body",
            "row_text",
            "row_hover",
            "ring",
        ):
            self.assertIn(key, light)

    def test_colour_values_are_valid_hex(self) -> None:
        for mode, palette in themes.PALETTES.items():
            for key, value in palette.items():
                if key in ("mode",):
                    continue
                if isinstance(value, str) and value.startswith("#"):
                    with self.subTest(mode=mode, key=key):
                        self.assertRegex(value, HEX_COLOR)
        for mode, accents in themes.TILE_ACCENTS.items():
            for index, value in enumerate(accents):
                with self.subTest(mode=mode, index=index):
                    self.assertRegex(value, HEX_COLOR)

    def test_numeric_blend_settings_stay_in_range(self) -> None:
        for mode, palette in themes.PALETTES.items():
            for key in (
                "tile_rim_t",
                "tile_glyph_t",
                "label_rim_t",
                "active_body_t",
            ):
                value = palette[key]
                with self.subTest(mode=mode, key=key):
                    self.assertIsInstance(value, float)
                    self.assertGreaterEqual(value, 0.0)
                    self.assertLessEqual(value, 1.0)

    def test_tile_accent_count_matches_the_wheel(self) -> None:
        for mode in themes.MODE_KEYS:
            self.assertEqual(
                len(themes.tile_accents(mode)), len(DEFAULT_RADIAL_ITEMS)
            )

    def test_dark_palette_is_actually_dark(self) -> None:
        light = themes.palette("light")
        dark = themes.palette("dark")
        self.assertLess(
            themes.luminance(dark["tile_body"]),
            themes.luminance(light["tile_body"]),
        )
        self.assertLess(
            themes.luminance(dark["base"]), themes.luminance(light["base"])
        )
        # Text must invert with the surface, otherwise labels disappear.
        self.assertGreater(
            themes.luminance(dark["label_text"]),
            themes.luminance(light["label_text"]),
        )

    def test_palette_copy_is_not_shared(self) -> None:
        first = themes.palette("light")
        first["tile_body"] = "#000000"
        self.assertNotEqual(themes.palette("light")["tile_body"], "#000000")

    def test_tile_colors_differ_between_modes(self) -> None:
        accent = themes.tile_accents("light")[0]
        light = themes.tile_colors("light", accent)
        dark = themes.tile_colors("dark", accent)
        self.assertNotEqual(light["body"], dark["body"])
        self.assertNotEqual(light["glyph"], dark["glyph"])
        for colors in (light, dark):
            self.assertEqual(
                set(colors), {"body", "rim", "glyph", "shadow", "hilite"}
            )

    def test_active_tile_body_is_tinted_toward_the_accent(self) -> None:
        accent = "#FF3B30"
        colors = themes.active_tile_colors("light", accent)
        self.assertEqual(colors["glyph"], "#FFFFFF")
        self.assertNotEqual(colors["body"], themes.palette("light")["tile_body"])

    def test_mix_blends_and_clamps(self) -> None:
        self.assertEqual(themes.mix("#000000", "#FFFFFF", 0.0), "#000000")
        self.assertEqual(themes.mix("#000000", "#FFFFFF", 1.0), "#FFFFFF")
        self.assertEqual(themes.mix("#000000", "#FFFFFF", 0.5), "#808080")
        self.assertEqual(themes.mix("#000000", "#FFFFFF", 5.0), "#FFFFFF")
        self.assertEqual(themes.mix("#000000", "#FFFFFF", -5.0), "#000000")
        self.assertEqual(themes.mix("#abc", "#000", 0.0), "#AABBCC")

    def test_mix_rejects_garbage(self) -> None:
        with self.assertRaises(ValueError):
            themes.mix("nope", "#FFFFFF", 0.5)

    def test_readable_text_on_follows_the_surface(self) -> None:
        self.assertEqual(themes.readable_text_on("#FFFFFF"), "#1C1C1E")
        self.assertEqual(themes.readable_text_on("#101010"), "#F2F3F7")


class WallpaperAssetTests(unittest.TestCase):
    def test_every_combination_ships_a_wallpaper_and_edges(self) -> None:
        for style in themes.STYLE_KEYS:
            for mode in themes.MODE_KEYS:
                with self.subTest(style=style, mode=mode):
                    self.assertTrue(
                        themes.wallpaper_available(style, mode),
                        themes.wallpaper_path(style, mode),
                    )
                    self.assertEqual(
                        themes.wallpaper_path(style, mode).name,
                        f"{style}_{mode}.png",
                    )
                    edges = themes.wallpaper_edges(style, mode)
                    self.assertEqual(set(edges), {"top", "bottom"})
                    for value in edges.values():
                        self.assertRegex(value, HEX_COLOR)

    def test_unknown_combination_still_resolves_to_a_default_asset(self) -> None:
        self.assertEqual(
            themes.wallpaper_name("neon", "midnight"), "frost_light.png"
        )

    def test_wallpapers_stay_small_enough_for_the_single_file_exe(self) -> None:
        total = sum(
            themes.wallpaper_path(style, mode).stat().st_size
            for style in themes.STYLE_KEYS
            for mode in themes.MODE_KEYS
        )
        self.assertLess(total, 1_200_000, f"贴图合计 {total:,} 字节")

    def test_edge_colours_match_their_mode(self) -> None:
        for style in themes.STYLE_KEYS:
            light = themes.wallpaper_edges(style, "light")["top"]
            dark = themes.wallpaper_edges(style, "dark")["top"]
            with self.subTest(style=style):
                self.assertGreater(
                    themes.luminance(light), themes.luminance(dark)
                )


if __name__ == "__main__":
    unittest.main()
