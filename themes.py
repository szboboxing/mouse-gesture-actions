"""Wheel themes: three wallpaper styles, each with a light / dark palette.

The radial wheel window is dressed in one of three wallpapers — 奶油 (cream
soft), 冷淡 (quiet cold) and 苹果 (liquid glass) — each shipped in a 明亮 and a
暗夜 variant, so the two top-bar buttons are independent: 「风格」 picks the
picture *and* the material, 「明暗」 picks the light or dark variant of it.

A style is more than its wallpaper. Every aesthetic needs its own surface
colours, its own accent hues and its own geometry (奶油 is round and lifted,
冷淡 is square, hairline-edged and flat, 苹果 is translucent glass), so this
module is the single sheet the widgets read from:

* :data:`PALETTES` — the structural base every style starts from (the 苹果
  values), keyed by 明暗.
* :data:`STYLE_PALETTES` — the tokens a style overrides to differ from it.
* :data:`TILE_ACCENTS` / :data:`MODE_COLORS` — accent hues per style × 明暗.
* :data:`STYLE_GEOMETRY` — corner radii, rim widths, shadow depth, label pills.

Everything here is offline and pure data: the wallpapers are plain PNG files
shipped inside ``assets/wallpapers/`` and loaded with ``tk.PhotoImage``, so no
imaging library is needed at runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path


# --------------------------------------------------------------------------
# Styles and modes
# --------------------------------------------------------------------------

# (key, 中文名称) — the 「风格」 button cycles through this order.
WHEEL_STYLES: tuple[tuple[str, str], ...] = (
    ("cream", "奶油"),
    ("minimal", "冷淡"),
    ("apple", "苹果"),
)

# (key, 中文名称) — the 「明暗」 button toggles between these two.
WHEEL_MODES: tuple[tuple[str, str], ...] = (
    ("light", "明亮"),
    ("dark", "暗夜"),
)

DEFAULT_WHEEL_STYLE = "cream"
DEFAULT_WHEEL_MODE = "light"

STYLE_KEYS: tuple[str, ...] = tuple(key for key, _ in WHEEL_STYLES)
MODE_KEYS: tuple[str, ...] = tuple(key for key, _ in WHEEL_MODES)

# Small mark on the 「风格」 button: each style shows its own shape, so the
# button reads as a preview of what the wheel will look like.
STYLE_ICONS: dict[str, str] = {
    "cream": "◍",
    "minimal": "□",
    "apple": "◈",
}

WALLPAPER_DIR = "assets/wallpapers"
# Canvas-sized crops: the wheel canvas is at most 656x526 inside the compact
# window, so 640x400 always covers most of it and is only ever cropped.
WALLPAPER_SIZE = (640, 400)

# Average colour of the first / last 14 rows of every wallpaper, measured by
# ``build/make_style_wallpapers.py --edges``. The top bar and the clipboard
# panel use them as their solid background so the whole window reads as one
# continuous sheet instead of three panels.
WALLPAPER_EDGES: dict[str, dict[str, str]] = {
    "cream/light": {"top": "#FAF0E5", "bottom": "#F1E6D6"},
    "cream/dark": {"top": "#3C2D1F", "bottom": "#3A2C1E"},
    "minimal/light": {"top": "#FAFAFB", "bottom": "#EEF0F1"},
    "minimal/dark": {"top": "#191D20", "bottom": "#121517"},
    "apple/light": {"top": "#D5E1F2", "bottom": "#EAD9F2"},
    "apple/dark": {"top": "#5578AD", "bottom": "#9C69B4"},
}

# --- 立体图标 --------------------------------------------------------------- #
# 奶油风 and 苹果风 ship pre-rendered 3D icons; 冷淡风 deliberately keeps the
# flat text glyphs, because hairline-and-flat *is* that style. The PNGs are
# rendered offline by ``build/make_style_icons.py`` (Pillow is not bundled) and
# loaded with ``tk.PhotoImage``, exactly like the wallpapers.
ICON_DIR = "assets/icons"
ICON_STYLES: tuple[str, ...] = ("cream", "apple")

# Buckets the renderer produces. Tk cannot rescale a PhotoImage smoothly, so a
# tile picks the nearest bucket for its own size instead of stretching one.
# Every key ships at every bucket: the split 亮度/对比度 tiles and the hub ask
# for much smaller art than the orbit tiles, and a missing bucket would
# silently drop them back to a flat glyph.
ICON_SIZES: tuple[int, ...] = (26, 34, 40, 46)

# Wheel glyph -> icon key. The glyph stays the single identity a tile carries
# around, so adding a tile only means extending this table.
ICON_BY_GLYPH: dict[str, str] = {
    "⤢": "cursor",
    "⧉": "copy",
    "⊕": "enhanced",
    "◐": "contrast",
    "✦": "ai",
    "☀": "brightness",
    "◎": "browser",
    "▦": "calculator",
    "⚙": "hub",
}
ICON_KEYS: tuple[str, ...] = tuple(ICON_BY_GLYPH.values())


# --------------------------------------------------------------------------
# Colour palettes
# --------------------------------------------------------------------------

# Structural base colours, keyed by 明暗. These are the 苹果 values, i.e. the
# most neutral reading of the tokens; a style overrides only what makes it
# look like itself. Accent hues stay per-style in TILE_ACCENTS below.
#
# Every key must exist for both modes and survive every style override, so a
# widget can read ``pal["anything"]`` without guessing which style is on.
PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "mode": "light",
        "base": "#EEF1F8",
        "top_bar_border": "#D7DCE8",
        "status_text": "#1C1C1E",
        "status_muted": "#6B7080",
        "tile_body": "#FBFCFF",
        "tile_shadow": "#AEB7CC",
        "tile_rim_target": "#FFFFFF",
        "tile_rim_t": 0.30,
        "tile_glyph_target": "#2A2A30",
        "tile_glyph_t": 0.12,
        "active_body_t": 0.86,
        "active_rim_target": "#FFFFFF",
        "active_rim_t": 0.25,
        "active_glyph": "#0071E3",
        "label_body": "#FFFFFF",
        "label_rim_target": "#FFFFFF",
        "label_rim_t": 0.55,
        "label_text": "#1C1C1E",
        "hub_body": "#FFFFFF",
        "hub_glyph": "#8E8E93",
        "hub_text": "#6B7080",
        "divider": "#C7CCDA",
        "minus_body": "#E9EBF2",
        "minus_rim": "#B7BDCB",
        "minus_text": "#3A3F4B",
        "pill_body": "#FFFFFF",
        "pill_rim": "#D7DCE8",
        "pill_text": "#1C1C1E",
        "pill_hover": "#EDF3FF",
        "orbit": "#B9C1D4",
        "row_body": "#FFFFFF",
        "row_text": "#28282C",
        "row_muted": "#7A7F8C",
        "row_hover": "#F2F5FC",
        "ring": "#FFFFFF",
    },
    "dark": {
        "mode": "dark",
        "base": "#1A1D26",
        "top_bar_border": "#3A4152",
        "status_text": "#F2F3F7",
        "status_muted": "#A2A8B8",
        "tile_body": "#2A2F3D",
        "tile_shadow": "#101219",
        "tile_rim_target": "#FFFFFF",
        "tile_rim_t": 0.10,
        "tile_glyph_target": "#FFFFFF",
        "tile_glyph_t": 0.55,
        "active_body_t": 0.42,
        "active_rim_target": "#FFFFFF",
        "active_rim_t": 0.35,
        "active_glyph": "#FFFFFF",
        "label_body": "#242936",
        "label_rim_target": "#8E95A8",
        "label_rim_t": 0.55,
        "label_text": "#EDEEF3",
        "hub_body": "#2A2F3D",
        "hub_glyph": "#C7CCDA",
        "hub_text": "#A2A8B8",
        "divider": "#4A5266",
        "minus_body": "#3A4152",
        "minus_rim": "#5A6478",
        "minus_text": "#E4E7EF",
        "pill_body": "#2A2F3D",
        "pill_rim": "#4A5266",
        "pill_text": "#F2F3F7",
        "pill_hover": "#394153",
        "row_body": "#262B37",
        "row_text": "#E8EAF0",
        "row_muted": "#9AA1B0",
        "row_hover": "#313848",
        "orbit": "#4A5266",
        "ring": "#F2F3F7",
    },
}

# Per-style overrides on top of PALETTES. 苹果 is the base sheet, so it only
# restates the couple of tokens its own design sheet pins down.
STYLE_PALETTES: dict[str, dict[str, dict[str, str]]] = {
    # 奶油风：暖白卡纸、焦糖描边，图标压成奶茶棕，不跟随磁贴强调色。
    "cream": {
        "light": {
            "base": "#FBF5EE",
            "top_bar_border": "#EFE0D0",
            "status_text": "#4A3B32",
            "status_muted": "#8A7668",
            "tile_body": "#FFFDFA",
            "tile_shadow": "#E7D6C2",
            "tile_rim_target": "#FFFFFF",
            "tile_rim_t": 0.30,
            "tile_glyph_target": "#7A5C48",
            "tile_glyph_t": 0.58,
            "active_body_t": 0.62,
            "active_rim_target": "#FFFFFF",
            "active_rim_t": 0.30,
            "active_glyph": "#A85638",
            "label_body": "#FFFCF7",
            "label_rim_target": "#EFE0D0",
            "label_rim_t": 0.88,
            "label_text": "#6B5344",
            "hub_body": "#FFFDFA",
            "hub_glyph": "#C98A5E",
            "hub_text": "#8A7668",
            "divider": "#EFDCC8",
            "minus_body": "#FFFCF7",
            "minus_rim": "#EFE0D0",
            "minus_text": "#8C6A52",
            "pill_body": "#FFFCF7",
            "pill_rim": "#EFE0D0",
            "pill_text": "#6B5344",
            "pill_hover": "#F7EADC",
            "orbit": "#E7D6C4",
            "row_body": "#FFFCF7",
            "row_text": "#4A3B32",
            "row_muted": "#8A7668",
            "row_hover": "#F7EADC",
            "ring": "#C98A5E",
        },
        "dark": {
            "base": "#241E1A",
            "top_bar_border": "#4A3B2C",
            "status_text": "#F3E7DA",
            "status_muted": "#B79F8A",
            "tile_body": "#33291F",
            "tile_shadow": "#14100C",
            "tile_rim_target": "#6B5540",
            "tile_rim_t": 0.22,
            "tile_glyph_target": "#E8D3BC",
            "tile_glyph_t": 0.58,
            "active_body_t": 0.44,
            "active_rim_target": "#8A6C4C",
            "active_rim_t": 0.45,
            "active_glyph": "#FFF6EA",
            "label_body": "#2E251D",
            "label_rim_target": "#5A4836",
            "label_rim_t": 0.75,
            "label_text": "#F3E7DA",
            "hub_body": "#33291F",
            "hub_glyph": "#E0A475",
            "hub_text": "#B79F8A",
            "divider": "#4A3B2C",
            "minus_body": "#3E3226",
            "minus_rim": "#5A4836",
            "minus_text": "#F3E7DA",
            "pill_body": "#33291F",
            "pill_rim": "#4A3B2C",
            "pill_text": "#F3E7DA",
            "pill_hover": "#46382A",
            "orbit": "#5A4836",
            "row_body": "#2E251D",
            "row_text": "#F3E7DA",
            "row_muted": "#B79F8A",
            "row_hover": "#3E3226",
            "ring": "#E0A475",
        },
    },
    # 极简冷淡风：白卡 + 发丝描边，图标与文字基本是中性墨色，
    # 「当前粘贴模式」靠墨色描边而不是靠色块表达。
    "minimal": {
        "light": {
            "base": "#F5F6F7",
            "top_bar_border": "#E3E6E9",
            "status_text": "#1F2429",
            "status_muted": "#7B848D",
            "tile_body": "#FFFFFF",
            "tile_shadow": "#E8EBEE",
            "tile_rim_target": "#E3E6E9",
            "tile_rim_t": 0.88,
            "tile_glyph_target": "#2C3238",
            "tile_glyph_t": 0.82,
            "active_body_t": 0.94,
            "active_rim_target": "#1F2429",
            "active_rim_t": 0.86,
            "active_glyph": "#1F2429",
            "label_body": "#FFFFFF",
            "label_rim_target": "#E3E6E9",
            "label_rim_t": 0.92,
            "label_text": "#6E767D",
            "hub_body": "#FFFFFF",
            "hub_glyph": "#3E5C76",
            "hub_text": "#A2AAB2",
            "divider": "#E3E6E9",
            "minus_body": "#F5F6F7",
            "minus_rim": "#E3E6E9",
            "minus_text": "#1F2429",
            "pill_body": "#FFFFFF",
            "pill_rim": "#E3E6E9",
            "pill_text": "#5A636B",
            "pill_hover": "#F5F6F7",
            "orbit": "#DDE1E4",
            "row_body": "#FFFFFF",
            "row_text": "#1F2429",
            "row_muted": "#7B848D",
            "row_hover": "#F5F6F7",
            "ring": "#3E5C76",
        },
        "dark": {
            "base": "#141719",
            "top_bar_border": "#2A2F33",
            "status_text": "#E6E9EB",
            "status_muted": "#8A939C",
            "tile_body": "#1B1F22",
            "tile_shadow": "#0A0C0D",
            "tile_rim_target": "#2A2F33",
            "tile_rim_t": 0.85,
            "tile_glyph_target": "#E6E9EB",
            "tile_glyph_t": 0.80,
            "active_body_t": 0.90,
            "active_rim_target": "#E6E9EB",
            "active_rim_t": 0.82,
            "active_glyph": "#F5F6F7",
            "label_body": "#141719",
            "label_rim_target": "#2A2F33",
            "label_rim_t": 0.92,
            "label_text": "#B6BEC5",
            "hub_body": "#1B1F22",
            "hub_glyph": "#7FA6C9",
            "hub_text": "#6E767D",
            "divider": "#2A2F33",
            "minus_body": "#22272B",
            "minus_rim": "#34393E",
            "minus_text": "#E6E9EB",
            "pill_body": "#1B1F22",
            "pill_rim": "#2A2F33",
            "pill_text": "#E6E9EB",
            "pill_hover": "#22272B",
            "orbit": "#34393E",
            "row_body": "#1B1F22",
            "row_text": "#E6E9EB",
            "row_muted": "#8A939C",
            "row_hover": "#22272B",
            "ring": "#7FA6C9",
        },
    },
    # 苹果风格：PALETTES 本身就是它，只把系统色收敛到设计稿的取值。
    "apple": {
        "light": {
            "status_text": "#1D1D1F",
            "tile_glyph_target": "#1D1D1F",
            "tile_glyph_t": 0.18,
            "label_text": "#1D1D1F",
            "hub_glyph": "#0071E3",
            "minus_text": "#1D1D1F",
            "pill_text": "#1D1D1F",
            "row_text": "#1D1D1F",
        },
        "dark": {
            "status_text": "#F5F5F7",
            "tile_glyph_target": "#F5F5F7",
            "label_text": "#F5F5F7",
            "hub_glyph": "#4FA9FF",
            "pill_text": "#F5F5F7",
            "row_text": "#F5F5F7",
        },
    },
}

# Tile accent hues, per style × 明暗, in DEFAULT_RADIAL_ITEMS order:
# 鼠标大小 普通粘贴 增强粘贴 对比度 AI 工具 亮度 浏览器 计算器
# 奶油只用焦糖一族 + 语义绿/警示橙；冷淡几乎单色（钢蓝），只给「增强粘贴」
# 留一点砖红做功能区分；苹果保留 iOS 多彩。
TILE_ACCENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "cream": {
        "light": (
            "#C98A5E",  # 鼠标大小 (焦糖)
            "#C9A96A",  # 普通粘贴 (奶茶金)
            "#D98C6A",  # 增强粘贴 (警示橙)
            "#A8917F",  # 对比度
            "#B9836F",  # AI 工具
            "#7FA37A",  # 亮度 (语义绿)
            "#9C7A5E",  # 浏览器
            "#A8917F",  # 计算器 (中性)
        ),
        "dark": (
            "#E0A475",
            "#E3C089",
            "#E89A76",
            "#B79F8A",
            "#D3A183",
            "#8FB08A",
            "#C79A78",
            "#B79F8A",
        ),
    },
    "minimal": {
        "light": (
            "#3E5C76",  # 鼠标大小 (钢蓝)
            "#5B7F95",  # 普通粘贴
            "#8C5A52",  # 增强粘贴 (砖红)
            "#7B848D",  # 对比度 (中性灰)
            "#3E5C76",  # AI 工具
            "#5B7F6B",  # 亮度 (灰绿)
            "#6E767D",  # 浏览器
            "#9AA3AC",  # 计算器 (弱化灰)
        ),
        "dark": (
            "#7FA6C9",
            "#96BBD9",
            "#C98478",
            "#8A939C",
            "#7FA6C9",
            "#86A892",
            "#6E767D",
            "#5A636B",
        ),
    },
    "apple": {
        "light": (
            "#0071E3",  # 鼠标大小 (系统蓝)
            "#FF9500",  # 普通粘贴 (橙)
            "#FF3B30",  # 增强粘贴 (红)
            "#30B0C7",  # 对比度
            "#AF52DE",  # AI 工具
            "#34C759",  # 亮度 (绿)
            "#5E5CE6",  # 浏览器 (靛蓝)
            "#0071E3",  # 计算器
        ),
        "dark": (
            "#4FA9FF",
            "#FF9F0A",
            "#FF453A",
            "#64D2FF",
            "#BF5AF2",
            "#30D158",
            "#7D7CFF",
            "#4FA9FF",
        ),
    },
}

# Identity colours used outside the wheel (paste badge, status dots, rows).
MODE_COLORS: dict[str, dict[str, dict[str, str]]] = {
    "cream": {
        "light": {
            "hover": "#C98A5E",
            "paste_normal": "#C9A96A",
            "paste_enhanced": "#D98C6A",
            "success": "#7FA37A",
            "warning": "#C98A5E",
            "danger": "#C4614B",
            "teal": "#8FA98A",
            "purple": "#B9836F",
            "indigo": "#9C7A5E",
        },
        "dark": {
            "hover": "#E0A475",
            "paste_normal": "#E3C089",
            "paste_enhanced": "#E89A76",
            "success": "#8FB08A",
            "warning": "#E0A475",
            "danger": "#D9755E",
            "teal": "#A3BFA0",
            "purple": "#D3A183",
            "indigo": "#C79A78",
        },
    },
    "minimal": {
        "light": {
            "hover": "#3E5C76",
            "paste_normal": "#5B7F95",
            "paste_enhanced": "#8C5A52",
            "success": "#5B7F6B",
            "warning": "#8A7250",
            "danger": "#8C5A52",
            "teal": "#4E7A7F",
            "purple": "#6B6A8A",
            "indigo": "#3E5C76",
        },
        "dark": {
            "hover": "#7FA6C9",
            "paste_normal": "#96BBD9",
            "paste_enhanced": "#C98478",
            "success": "#86A892",
            "warning": "#B99A78",
            "danger": "#C98478",
            "teal": "#7FA8AC",
            "purple": "#9A97B8",
            "indigo": "#7FA6C9",
        },
    },
    "apple": {
        "light": {
            "hover": "#0071E3",
            "paste_normal": "#FF9500",
            "paste_enhanced": "#FF3B30",
            "success": "#34C759",
            "warning": "#FF9500",
            "danger": "#FF3B30",
            "teal": "#30B0C7",
            "purple": "#AF52DE",
            "indigo": "#5E5CE6",
        },
        "dark": {
            "hover": "#4FA9FF",
            "paste_normal": "#FF9F0A",
            "paste_enhanced": "#FF453A",
            "success": "#30D158",
            "warning": "#FF9F0A",
            "danger": "#FF453A",
            "teal": "#64D2FF",
            "purple": "#BF5AF2",
            "indigo": "#7D7CFF",
        },
    },
}


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

# Shape is part of the aesthetic, not an afterthought: 奶油 is a soft, lifted
# card, 冷淡 is a flat hairline square, 苹果 is a round piece of glass.
# Ratios are relative to a tile's half-side (``half`` in the drawing code)
# unless noted; ``shadow_depth`` 0.0 means the shadow is not painted at all,
# ``label_pill`` False means labels are bare text, and ``hover_halo`` decides
# whether hovering adds the outer light ring on top of the accent outline.
STYLE_GEOMETRY: dict[str, dict[str, float | bool]] = {
    "cream": {
        "tile_radius": 0.62,
        "hub_radius": 0.90,
        "sub_radius": 0.34,
        "hover_radius": 0.52,
        "label_radius": 0.50,
        "rim_width": 1.2,
        "active_rim_width": 2.0,
        "shadow_depth": 1.0,
        "glyph_scale": 1.0,
        "specular": True,
        "label_pill": True,
        "hover_halo": True,
    },
    "minimal": {
        "tile_radius": 0.14,
        "hub_radius": 0.30,
        "sub_radius": 0.12,
        "hover_radius": 0.16,
        "label_radius": 0.0,
        "rim_width": 1.0,
        "active_rim_width": 1.6,
        "shadow_depth": 0.0,
        "glyph_scale": 0.92,
        "specular": False,
        "label_pill": False,
        "hover_halo": False,
    },
    "apple": {
        "tile_radius": 0.52,
        "hub_radius": 0.90,
        "sub_radius": 0.34,
        "hover_radius": 0.52,
        "label_radius": 0.50,
        "rim_width": 1.4,
        "active_rim_width": 2.2,
        "shadow_depth": 0.85,
        "glyph_scale": 1.0,
        "specular": True,
        "label_pill": True,
        "hover_halo": True,
    },
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def mix(color_a: str, color_b: str, ratio: float) -> str:
    """Linear interpolation between two ``#rrggbb`` colours (ratio 0 → a)."""
    a, b = _rgb(color_a), _rgb(color_b)
    t = max(0.0, min(1.0, ratio))
    return "#{:02X}{:02X}{:02X}".format(
        *(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    )


def _rgb(color: str) -> tuple[int, int, int]:
    value = str(color).strip()
    if value.startswith("#"):
        value = value[1:]
    if len(value) == 3:  # #abc → #aabbcc
        value = "".join(ch * 2 for ch in value)
    try:
        return (
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16),
        )
    except (ValueError, IndexError) as exc:  # defensive: bad literals only
        raise ValueError(f"不是合法的颜色值: {color!r}") from exc


def luminance(color: str) -> float:
    """Relative brightness of a colour (0 = black, 1 = white)."""
    r, g, b = (channel / 255 for channel in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def readable_text_on(background: str) -> str:
    """Pick dark or light text so labels stay legible on any wallpaper edge."""
    return "#1C1C1E" if luminance(background) > 0.5 else "#F2F3F7"


def is_style(value: object) -> bool:
    return str(value) in STYLE_KEYS


def is_mode(value: object) -> bool:
    return str(value) in MODE_KEYS


def normalize_style(value: object) -> str:
    return str(value) if is_style(value) else DEFAULT_WHEEL_STYLE


def normalize_mode(value: object) -> str:
    return str(value) if is_mode(value) else DEFAULT_WHEEL_MODE


def style_label(style: object) -> str:
    style = normalize_style(style)
    return dict(WHEEL_STYLES)[style]


def style_icon(style: object) -> str:
    """The shape mark shown in front of the style name on the button."""
    return STYLE_ICONS[normalize_style(style)]


def mode_label(mode: object) -> str:
    mode = normalize_mode(mode)
    return dict(WHEEL_MODES)[mode]


def next_style(style: object) -> str:
    """The 「风格」 button cycles: 奶油 → 冷淡 → 苹果 → 奶油."""
    order = STYLE_KEYS
    current = normalize_style(style)
    return order[(order.index(current) + 1) % len(order)]


def next_mode(mode: object) -> str:
    """The 「明暗」 button toggles 明亮 ⇄ 暗夜."""
    return "dark" if normalize_mode(mode) == "light" else "light"


def palette(mode: object, style: object = DEFAULT_WHEEL_STYLE) -> dict[str, str]:
    """A copy of the merged palette for ``style`` × ``mode``.

    Never shared and never the caller's to mutate: the base sheet is copied
    first, then the style's overrides are layered on top.
    """
    merged = dict(PALETTES[normalize_mode(mode)])
    merged.update(STYLE_PALETTES[normalize_style(style)][normalize_mode(mode)])
    merged["mode"] = normalize_mode(mode)
    return merged


# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------

WHEEL_FONT_FAMILY = "Microsoft YaHei UI"
# Tk 的正数字号单位是「磅」，会跟着系统 DPI 一起放大（tk scaling = dpi / 72）；
# 只有负数字号才是像素、不受缩放影响。轮盘是固定 640×660 像素的画布，壁纸和立体
# 图标也都是固定尺寸的位图，所以文字必须一起按像素钉死：在 150% 缩放的机器上，
# 磅值字号会大 1.5 倍而贴图不变，顶栏一行实测需要 835px，「风格」药丸直接被挤出
# 640px 的窗口——这正是用户反馈的「按钮被挡住」。
# 换算基准取 96 DPI（1pt = 4/3 px），因此成品与改前在 100% 缩放下逐像素一致。
WHEEL_FONT_PIXELS_PER_POINT = 4 / 3


def wheel_font(
    points: float,
    weight: str = "bold",
    family: str = WHEEL_FONT_FAMILY,
) -> tuple[str, int, str]:
    """把「按 96 DPI 设计出来的磅值」换成固定像素字号的 Tk 字体元组。"""
    pixels = max(1, int(round(points * WHEEL_FONT_PIXELS_PER_POINT)))
    return (family, -pixels, weight)


def geometry(style: object = DEFAULT_WHEEL_STYLE) -> dict[str, float | bool]:
    """A copy of the shape sheet for ``style`` (radii, widths, shadow, pills)."""
    return dict(STYLE_GEOMETRY[normalize_style(style)])


def tile_accents(mode: object, style: object = DEFAULT_WHEEL_STYLE) -> tuple[str, ...]:
    return TILE_ACCENTS[normalize_style(style)][normalize_mode(mode)]


def accent_colors(
    mode: object, style: object = DEFAULT_WHEEL_STYLE
) -> dict[str, str]:
    return dict(MODE_COLORS[normalize_style(style)][normalize_mode(mode)])


def tile_colors(
    mode: object, accent: str, style: object = DEFAULT_WHEEL_STYLE
) -> dict[str, str]:
    """Body / rim / glyph / shadow / hilite for one tile of the given accent."""
    pal = palette(mode, style)
    return {
        "body": pal["tile_body"],
        "rim": mix(accent, pal["tile_rim_target"], pal["tile_rim_t"]),
        "glyph": mix(accent, pal["tile_glyph_target"], pal["tile_glyph_t"]),
        "shadow": pal["tile_shadow"],
        "hilite": mix(
            mix(accent, pal["tile_rim_target"], pal["tile_rim_t"]),
            pal["tile_rim_target"],
            0.6,
        ),
    }


def active_tile_colors(
    mode: object, accent: str, style: object = DEFAULT_WHEEL_STYLE
) -> dict[str, str]:
    """The highlighted (current paste mode) tile.

    How a style signals 「当前」 is itself a style decision: 奶油 and 苹果 tint
    the body toward the accent and flip the glyph to white, 冷淡 keeps the
    surface white and draws an ink outline instead.
    """
    pal = palette(mode, style)
    return {
        "body": mix(accent, pal["tile_body"], pal["active_body_t"]),
        "rim": mix(accent, pal["active_rim_target"], pal["active_rim_t"]),
        "glyph": pal["active_glyph"],
        "shadow": pal["tile_shadow"],
        "hilite": mix(accent, pal["active_rim_target"], 0.6),
    }


def label_colors(
    mode: object, accent: str, style: object = DEFAULT_WHEEL_STYLE
) -> dict[str, str]:
    pal = palette(mode, style)
    return {
        "body": pal["label_body"],
        "rim": mix(accent, pal["label_rim_target"], pal["label_rim_t"]),
        "text": pal["label_text"],
    }


def wallpaper_name(style: object, mode: object) -> str:
    return f"{normalize_style(style)}_{normalize_mode(mode)}.png"


def wallpaper_edges(style: object, mode: object) -> dict[str, str]:
    key = f"{normalize_style(style)}/{normalize_mode(mode)}"
    return dict(WALLPAPER_EDGES[key])


def resource_path(relative_path: str) -> Path:
    """Resolve a bundled file, both from sources and inside the one-file EXE."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


def wallpaper_path(style: object, mode: object) -> Path:
    return resource_path(f"{WALLPAPER_DIR}/{wallpaper_name(style, mode)}")


def wallpaper_available(style: object, mode: object) -> bool:
    """False → the caller falls back to the flat ``palette(mode)['base']``."""
    return wallpaper_path(style, mode).is_file()


def uses_3d_icons(style: object) -> bool:
    """True for the styles that ship pre-rendered icons; 冷淡风 stays flat."""
    return normalize_style(style) in ICON_STYLES


def icon_key(glyph: str) -> str | None:
    """Icon key for a wheel glyph, or None when the glyph has no 3D art."""
    return ICON_BY_GLYPH.get(glyph)


def icon_size_for(target: float) -> int:
    """Snap a wanted pixel size to the nearest rendered bucket.

    Tk can only rescale a PhotoImage by whole numbers, so hovering cannot
    stretch an icon — the tile steps to the next bucket instead, which reads
    as part of the lift rather than as a resize.
    """
    return min(ICON_SIZES, key=lambda size: (abs(size - target), -size))


def icon_name(key: str, size: int) -> str:
    return f"{key}_{size}.png"


def icon_path(style: object, mode: object, key: str, size: int) -> Path:
    return resource_path(
        f"{ICON_DIR}/{normalize_style(style)}/{normalize_mode(mode)}"
        f"/{icon_name(key, size)}"
    )


def icon_available(style: object, mode: object, key: str, size: int) -> bool:
    """False → the caller draws the flat text glyph instead.

    Missing art must degrade to the old look, never to an empty tile.
    """
    return icon_path(style, mode, key, size).is_file()

# --------------------------------------------------------------------------
# 控制面板（点「更多设置」之后的那套界面）
# --------------------------------------------------------------------------
# 轮盘有三套风格，但控制面板只用一套：奶油风。它是用户 90% 时间面对的东西，
# 换成冷蓝灰会跟轮盘的暖色底对不上，所以这里固定读取 cream/light 的令牌，
# 轮盘切风格 / 明暗都不会改动控制面板（与帮助说明里的描述一致）。
#
# 凡是与轮盘共享的颜色都直接取 cream 表里的值，避免两处各写一遍而漂移；
# 面板独有的（侧边栏、输入框、示意图、状态色的深/浅档）在下面补齐。
_CREAM_LIGHT = STYLE_PALETTES["cream"]["light"]

PANEL_COLORS: dict[str, str] = {
    # 侧边栏：浓缩咖啡深棕，配奶油白文字
    "nav": "#3A2C23",
    "nav_soft": "#4B3A2E",
    "nav_text": _CREAM_LIGHT["base"],
    "nav_muted": "#C8B2A0",
    "nav_link": "#E8B58C",
    "nav_link_hover": "#F6D6B4",
    # 页面与卡片：页面比卡片深一档（亮度差 0.07），暖白卡才浮得起来
    "page": "#F5E9DA",
    "card": _CREAM_LIGHT["tile_body"],
    "card_soft": _CREAM_LIGHT["row_body"],
    "text": _CREAM_LIGHT["status_text"],
    # 次要文字与卡片描边：按 WCAG 对比度下限调过（muted 在页面底 4.8、
    # 卡片底 5.65；line 加深到能真正勾出卡片边界，奶油风仍是低反差）。
    "muted": "#776254",
    "line": "#D9BFA2",
    # 主强调色：焦糖棕（与奶油风磁贴的图标同色）
    "accent": _CREAM_LIGHT["active_glyph"],
    "accent_soft": _CREAM_LIGHT["pill_hover"],
    "accent_active": "#8A4429",
    "accent_hover": "#B96944",
    "on_accent": "#FFFCF7",
    # 状态色：控制面板里它们要承载白字，所以比轮盘的浅档更沉
    "success": "#487851",
    "success_soft": "#EAF2E7",
    "success_active": "#3E6B46",
    "warning": "#A5651D",
    "warning_soft": "#FAEEDC",
    "warning_active": "#985F1C",
    "danger": "#B4453A",
    "danger_soft": "#FAE7E2",
    "danger_active": "#95342C",
    # 输入框与选中态
    "field": "#FFFFFF",
    "field_line": "#E2CFB8",
    "selection": "#F1DEC8",
    "selection_text": "#7A4A2E",
    "disabled": "#E6D8C9",
    "disabled_text": "#776254",
    # 鼠标按键测试示意图
    "diagram": "#EEDCC4",
    "diagram_soft": "#DFC9AF",
    "diagram_line": "#C9A98C",
    "diagram_strong": "#A37F5F",
}


def panel_palette() -> dict[str, str]:
    """控制面板的配色表（永远是奶油风浅色）。

    返回副本：调用方会往里塞自己的键（如帮助窗口的 hover），不该改到模块表。
    """
    return dict(PANEL_COLORS)
