from __future__ import annotations

import re
import unittest

import themes
from radial_menu import DEFAULT_RADIAL_ITEMS


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Tokens the wheel and the clipboard strip read while painting. Anything a
# style overrides must keep this key set intact, or a widget would KeyError.
PALETTE_KEYS = frozenset(themes.PALETTES["light"])

GEOMETRY_KEYS = frozenset(themes.STYLE_GEOMETRY["cream"])


class StyleAndModeTests(unittest.TestCase):
    def test_three_styles_and_two_modes_are_offered(self) -> None:
        self.assertEqual(len(themes.WHEEL_STYLES), 3)
        self.assertEqual(len(themes.WHEEL_MODES), 2)
        self.assertEqual(
            themes.STYLE_KEYS, ("cream", "minimal", "apple")
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

    def test_default_style_is_cream(self) -> None:
        # 奶油风 is what a fresh install — and an old settings file with a
        # retired style name — lands on.
        self.assertEqual(themes.DEFAULT_WHEEL_STYLE, "cream")
        self.assertEqual(themes.WHEEL_STYLES[0][0], "cream")
        self.assertEqual(themes.DEFAULT_WHEEL_MODE, "light")

    def test_every_style_label_and_mode_label_is_unique_chinese(self) -> None:
        labels = [label for _, label in themes.WHEEL_STYLES]
        self.assertEqual(len(set(labels)), len(labels))
        for label in labels + [label for _, label in themes.WHEEL_MODES]:
            self.assertTrue(label.strip())

    def test_unknown_values_fall_back_to_defaults(self) -> None:
        for junk in ("", "neon", None, 7, "FROST", "frost", "pastel"):
            with self.subTest(value=junk):
                self.assertEqual(
                    themes.normalize_style(junk), themes.DEFAULT_WHEEL_STYLE
                )
                self.assertEqual(
                    themes.normalize_mode(junk), themes.DEFAULT_WHEEL_MODE
                )

    def test_retired_style_names_no_longer_resolve(self) -> None:
        # V2.7.0 shipped 冰霜 / 烟晶 / 彩璃; they must not survive as keys.
        for retired in ("frost", "graphite", "pastel"):
            self.assertFalse(themes.is_style(retired))

    def test_style_button_cycles_through_every_style_once(self) -> None:
        seen = []
        style = themes.DEFAULT_WHEEL_STYLE
        for _ in range(len(themes.STYLE_KEYS)):
            style = themes.next_style(style)
            seen.append(style)
        self.assertEqual(seen, ["minimal", "apple", "cream"])

    def test_mode_button_toggles_between_light_and_dark(self) -> None:
        self.assertEqual(themes.next_mode("light"), "dark")
        self.assertEqual(themes.next_mode("dark"), "light")
        self.assertEqual(themes.next_mode("junk"), "dark")

    def test_labels_are_reported_for_the_current_choice(self) -> None:
        self.assertEqual(themes.style_label("cream"), "奶油")
        self.assertEqual(themes.style_label("minimal"), "冷淡")
        self.assertEqual(themes.style_label("apple"), "苹果")
        self.assertEqual(themes.mode_label("light"), "明亮")
        self.assertEqual(themes.mode_label("dark"), "暗夜")

    def test_every_style_has_its_own_button_icon(self) -> None:
        icons = [themes.style_icon(style) for style in themes.STYLE_KEYS]
        self.assertEqual(len(set(icons)), len(icons))
        for icon in icons:
            self.assertTrue(icon.strip())
        self.assertEqual(themes.style_icon("nope"), themes.style_icon("cream"))


class PaletteTests(unittest.TestCase):
    def test_every_combination_exposes_the_same_keys(self) -> None:
        for style in themes.STYLE_KEYS:
            for mode in themes.MODE_KEYS:
                with self.subTest(style=style, mode=mode):
                    self.assertEqual(
                        frozenset(themes.palette(mode, style)), PALETTE_KEYS
                    )

    def test_the_wheel_reads_the_tokens_it_paints_with(self) -> None:
        for key in (
            "base",
            "top_bar_border",
            "status_text",
            "status_muted",
            "tile_body",
            "tile_shadow",
            "tile_rim_target",
            "tile_glyph_target",
            "active_glyph",
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
            self.assertIn(key, PALETTE_KEYS)

    def test_colour_values_are_valid_hex(self) -> None:
        def check(label: str, value: object) -> None:
            if isinstance(value, str) and value.startswith("#"):
                with self.subTest(label, value=value):
                    self.assertRegex(value, HEX_COLOR)

        for mode, palette in themes.PALETTES.items():
            for key, value in palette.items():
                check(f"PALETTES/{mode}/{key}", value)
        for style, per_mode in themes.STYLE_PALETTES.items():
            self.assertEqual(set(per_mode), set(themes.MODE_KEYS))
            for mode, palette in per_mode.items():
                for key, value in palette.items():
                    check(f"STYLE_PALETTES/{style}/{mode}/{key}", value)
        for style, per_mode in themes.TILE_ACCENTS.items():
            for mode, accents in per_mode.items():
                for index, value in enumerate(accents):
                    check(f"TILE_ACCENTS/{style}/{mode}[{index}]", value)
        for style, per_mode in themes.MODE_COLORS.items():
            for mode, colors in per_mode.items():
                for key, value in colors.items():
                    check(f"MODE_COLORS/{style}/{mode}/{key}", value)

    def test_style_overrides_only_known_tokens(self) -> None:
        # A typo in an override key would silently add a dead colour instead of
        # changing the look, so every override has to exist in the base sheet.
        for style, per_mode in themes.STYLE_PALETTES.items():
            for mode, overrides in per_mode.items():
                for key in overrides:
                    with self.subTest(style=style, mode=mode, key=key):
                        self.assertIn(key, PALETTE_KEYS)

    def test_numeric_blend_settings_stay_in_range(self) -> None:
        for style in themes.STYLE_KEYS:
            for mode in themes.MODE_KEYS:
                pal = themes.palette(mode, style)
                for key in (
                    "tile_rim_t",
                    "tile_glyph_t",
                    "active_body_t",
                    "active_rim_t",
                    "label_rim_t",
                ):
                    value = pal[key]
                    with self.subTest(style=style, mode=mode, key=key):
                        self.assertIsInstance(value, float)
                        self.assertGreaterEqual(value, 0.0)
                        self.assertLessEqual(value, 1.0)

    def test_tile_accent_count_matches_the_wheel(self) -> None:
        for style in themes.STYLE_KEYS:
            for mode in themes.MODE_KEYS:
                with self.subTest(style=style, mode=mode):
                    self.assertEqual(
                        len(themes.tile_accents(mode, style)),
                        len(DEFAULT_RADIAL_ITEMS),
                    )

    def test_mode_colour_sets_agree_across_styles(self) -> None:
        base = set(themes.accent_colors("light", "cream"))
        for style in themes.STYLE_KEYS:
            for mode in themes.MODE_KEYS:
                with self.subTest(style=style, mode=mode):
                    self.assertEqual(
                        set(themes.accent_colors(mode, style)), base
                    )

    def test_each_style_has_its_own_hue_character(self) -> None:
        # 奶油 warm, 冷淡 desaturated, 苹果 vivid — the sheets must stay apart,
        # otherwise switching 风格 would only change the wallpaper.
        cream = themes.luminance(
            themes.tile_accents("light", "cream")[0]
        )
        apple = themes.luminance(
            themes.tile_accents("light", "apple")[0]
        )
        self.assertNotEqual(
            themes.tile_accents("light", "cream"),
            themes.tile_accents("light", "apple"),
        )
        self.assertNotEqual(
            themes.tile_accents("light", "minimal"),
            themes.tile_accents("light", "apple"),
        )
        self.assertGreater(cream, 0.0)
        self.assertLess(apple, 1.0)

    def test_dark_palette_is_actually_dark(self) -> None:
        for style in themes.STYLE_KEYS:
            light = themes.palette("light", style)
            dark = themes.palette("dark", style)
            with self.subTest(style=style):
                self.assertLess(
                    themes.luminance(dark["tile_body"]),
                    themes.luminance(light["tile_body"]),
                )
                self.assertLess(
                    themes.luminance(dark["base"]),
                    themes.luminance(light["base"]),
                )
                # Text must invert with the surface, otherwise labels vanish.
                self.assertGreater(
                    themes.luminance(dark["label_text"]),
                    themes.luminance(light["label_text"]),
                )

    def test_palette_copy_is_not_shared(self) -> None:
        first = themes.palette("light", "cream")
        first["tile_body"] = "#000000"
        self.assertNotEqual(themes.palette("light")["tile_body"], "#000000")
        self.assertNotEqual(
            themes.PALETTES["light"]["tile_body"], "#000000"
        )

    def test_tile_colors_differ_between_modes(self) -> None:
        accent = themes.tile_accents("light", "cream")[2]
        light = themes.tile_colors("light", accent, "cream")
        dark = themes.tile_colors("dark", accent, "cream")
        self.assertNotEqual(light["body"], dark["body"])
        self.assertNotEqual(light["glyph"], dark["glyph"])
        for colors in (light, dark):
            self.assertEqual(
                set(colors), {"body", "rim", "glyph", "shadow", "hilite"}
            )

    def test_tile_body_follows_the_style_sheet(self) -> None:
        self.assertEqual(
            themes.tile_colors("light", "#FF0000", "cream")["body"], "#FFFDFA"
        )
        self.assertEqual(
            themes.tile_colors("light", "#FF0000", "minimal")["body"], "#FFFFFF"
        )

    def test_active_tile_is_legible_in_every_style(self) -> None:
        # Whatever the style, the highlighted tile's glyph has to contrast with
        # its own body: 奶油/苹果 go white-on-tint, 冷淡 goes ink-on-white.
        for style in themes.STYLE_KEYS:
            for mode in themes.MODE_KEYS:
                accent = themes.tile_accents(mode, style)[2]
                colors = themes.active_tile_colors(mode, accent, style)
                with self.subTest(style=style, mode=mode):
                    gap = abs(
                        themes.luminance(colors["glyph"])
                        - themes.luminance(colors["body"])
                    )
                    self.assertGreater(gap, 0.25)

    def test_active_tile_body_is_tinted_toward_the_accent(self) -> None:
        accent = "#FF3B30"
        colors = themes.active_tile_colors("light", accent, "apple")
        self.assertEqual(colors["glyph"], "#0071E3")
        self.assertNotEqual(
            colors["body"], themes.palette("light", "apple")["tile_body"]
        )
        # 冷淡风 is the exception: it tints almost nothing and signals 「当前」
        # with an ink outline instead of a colour block.
        quiet = themes.active_tile_colors("light", accent, "minimal")
        self.assertEqual(quiet["glyph"], "#1F2429")
        self.assertGreater(
            themes.luminance(quiet["body"]),
            themes.luminance(quiet["rim"]),
        )

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


class GeometryTests(unittest.TestCase):
    def test_every_style_ships_the_same_geometry_keys(self) -> None:
        for style in themes.STYLE_KEYS:
            with self.subTest(style=style):
                self.assertEqual(
                    frozenset(themes.geometry(style)), GEOMETRY_KEYS
                )

    def test_corner_radii_are_valid_proportions(self) -> None:
        for style in themes.STYLE_KEYS:
            geo = themes.geometry(style)
            for key in (
                "tile_radius",
                "hub_radius",
                "sub_radius",
                "hover_radius",
                "label_radius",
                "shadow_depth",
                "glyph_scale",
            ):
                with self.subTest(style=style, key=key):
                    self.assertGreaterEqual(geo[key], 0.0)
                    self.assertLessEqual(geo[key], 1.0)
            for key in ("rim_width", "active_rim_width"):
                with self.subTest(style=style, key=key):
                    self.assertGreater(geo[key], 0.0)
            self.assertLessEqual(
                geo["rim_width"], geo["active_rim_width"]
            )

    def test_styles_are_distinguishable_by_shape_alone(self) -> None:
        cream = themes.geometry("cream")
        minimal = themes.geometry("minimal")
        apple = themes.geometry("apple")
        # 冷淡风: square-ish corners, no lift, no label pill, no hover halo.
        self.assertLess(minimal["tile_radius"], cream["tile_radius"])
        self.assertLess(minimal["tile_radius"], apple["tile_radius"])
        self.assertEqual(minimal["shadow_depth"], 0.0)
        self.assertFalse(minimal["label_pill"])
        self.assertFalse(minimal["specular"])
        self.assertFalse(minimal["hover_halo"])
        # The other two are rounded, lifted cards with pills.
        for geo in (cream, apple):
            self.assertTrue(geo["label_pill"])
            self.assertTrue(geo["specular"])
            self.assertTrue(geo["hover_halo"])
            self.assertGreater(geo["shadow_depth"], 0.0)
        # …and they are still not the same card.
        self.assertNotEqual(cream["tile_radius"], apple["tile_radius"])

    def test_geometry_copy_is_not_shared(self) -> None:
        geo = themes.geometry("cream")
        geo["tile_radius"] = 0.0
        self.assertNotEqual(themes.geometry("cream")["tile_radius"], 0.0)

    def test_unknown_style_falls_back_to_the_default_geometry(self) -> None:
        self.assertEqual(
            themes.geometry("graphite"), themes.geometry("cream")
        )


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

    def test_edge_table_covers_exactly_the_shipped_styles(self) -> None:
        expected = {
            f"{style}/{mode}"
            for style in themes.STYLE_KEYS
            for mode in themes.MODE_KEYS
        }
        self.assertEqual(set(themes.WALLPAPER_EDGES), expected)

    def test_unknown_combination_still_resolves_to_a_default_asset(self) -> None:
        self.assertEqual(
            themes.wallpaper_name("neon", "midnight"), "cream_light.png"
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

    def test_top_bar_text_stays_legible_on_the_wallpaper_edge(self) -> None:
        # The top bar paints with the wallpaper's own top edge, so the palette
        # has to hand it a status colour that still stands out against it —
        # otherwise switching 风格 could silently wash the status line away.
        for style in themes.STYLE_KEYS:
            for mode in themes.MODE_KEYS:
                edge = themes.wallpaper_edges(style, mode)["top"]
                text = themes.palette(mode, style)["status_text"]
                with self.subTest(style=style, mode=mode):
                    self.assertGreater(
                        abs(themes.luminance(edge) - themes.luminance(text)),
                        0.35,
                    )

    def test_top_bar_text_flips_with_the_mode(self) -> None:
        for style in themes.STYLE_KEYS:
            light = themes.readable_text_on(
                themes.wallpaper_edges(style, "light")["top"]
            )
            dark = themes.readable_text_on(
                themes.wallpaper_edges(style, "dark")["top"]
            )
            with self.subTest(style=style):
                self.assertEqual(light, "#1C1C1E")
                self.assertEqual(dark, "#F2F3F7")


class IconAssetTests(unittest.TestCase):
    """The pre-rendered 3D icon sheet that ships beside the wallpapers."""

    def test_only_cream_and_apple_get_3d_icons(self) -> None:
        # 冷淡风 keeps its flat text glyphs, so it must not pull in bitmaps.
        self.assertEqual(themes.ICON_STYLES, ("cream", "apple"))
        self.assertTrue(themes.uses_3d_icons("cream"))
        self.assertTrue(themes.uses_3d_icons("apple"))
        self.assertFalse(themes.uses_3d_icons("minimal"))
        self.assertTrue(
            set(themes.ICON_STYLES).issubset(set(themes.STYLE_KEYS))
        )

    def test_retired_style_names_fall_back_to_cream_art(self) -> None:
        # An old settings file may still name a retired style; normalising to
        # 奶油风 must give it art that exists, not a blank tile.
        self.assertTrue(themes.uses_3d_icons("neon"))
        self.assertTrue(themes.icon_available("neon", "midnight", "cursor", 34))

    def test_every_wheel_glyph_has_an_icon(self) -> None:
        glyphs = {item.icon_text for item in DEFAULT_RADIAL_ITEMS}
        glyphs.add("⚙")  # the hub button shares the sheet
        for glyph in sorted(glyphs):
            with self.subTest(glyph=glyph):
                key = themes.icon_key(glyph)
                self.assertIsNotNone(key)
                self.assertIn(key, themes.ICON_KEYS)

    def test_icon_table_covers_every_shipped_combination(self) -> None:
        for style in themes.ICON_STYLES:
            for mode in themes.MODE_KEYS:
                for key in themes.ICON_KEYS:
                    for size in themes.ICON_SIZES:
                        with self.subTest(style=style, mode=mode, key=key,
                                          size=size):
                            self.assertTrue(
                                themes.icon_available(style, mode, key, size),
                                themes.icon_path(style, mode, key, size),
                            )
                            self.assertEqual(
                                themes.icon_path(style, mode, key, size).name,
                                f"{key}_{size}.png",
                            )

    def test_minimal_style_resolves_to_no_icon(self) -> None:
        self.assertFalse(
            themes.icon_available("minimal", "light", "cursor", 34)
        )

    def test_unknown_glyph_has_no_icon(self) -> None:
        self.assertIsNone(themes.icon_key("★"))

    def test_icon_size_snaps_to_the_nearest_bucket(self) -> None:
        # Tk can only rescale a PhotoImage by whole factors, so the drawing
        # code asks for the closest shipped size instead of an exact one.
        cases = {1: 26, 20: 26, 34: 34, 37: 40, 42: 40, 44: 46, 100: 46}
        for target, expected in cases.items():
            with self.subTest(target=target):
                self.assertEqual(themes.icon_size_for(target), expected)
        # Whatever a resized window asks for, a shipped file answers.
        for target in range(1, 121):
            self.assertIn(themes.icon_size_for(target), themes.ICON_SIZES)

    def test_icon_names_normalise_unknown_style_and_mode(self) -> None:
        self.assertEqual(
            themes.icon_name(themes.icon_key("⚙"), 26), "hub_26.png"
        )
        self.assertEqual(
            themes.icon_path("neon", "midnight", "cursor", 34).parent.name,
            "light",
        )

    def test_icons_stay_small_enough_for_the_single_file_exe(self) -> None:
        total = sum(
            themes.icon_path(style, mode, key, size).stat().st_size
            for style in themes.ICON_STYLES
            for mode in themes.MODE_KEYS
            for key in themes.ICON_KEYS
            for size in themes.ICON_SIZES
        )
        self.assertLess(total, 400_000, f"图标合计 {total:,} 字节")


if __name__ == "__main__":
    unittest.main()
