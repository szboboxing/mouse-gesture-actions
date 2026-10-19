"""Wheel themes: glass wallpaper styles plus light / dark colour palettes.

The radial wheel window can be dressed in three Apple-style glass wallpapers
(冰霜 / 烟晶 / 彩璃), each available in a 明亮 and a 暗夜 variant, so the two
top-bar buttons are independent: 「风格」 picks the picture, 「明暗」 picks the
colour palette used by the tiles, labels, pills and the clipboard panel.

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
    ("frost", "冰霜"),
    ("graphite", "烟晶"),
    ("pastel", "彩璃"),
)

# (key, 中文名称) — the 「明暗」 button toggles between these two.
WHEEL_MODES: tuple[tuple[str, str], ...] = (
    ("light", "明亮"),
    ("dark", "暗夜"),
)

DEFAULT_WHEEL_STYLE = "frost"
DEFAULT_WHEEL_MODE = "light"

STYLE_KEYS: tuple[str, ...] = tuple(key for key, _ in WHEEL_STYLES)
MODE_KEYS: tuple[str, ...] = tuple(key for key, _ in WHEEL_MODES)

WALLPAPER_DIR = "assets/wallpapers"
# Canvas-sized crops: the wheel canvas is at most 640x375 inside the compact
# 640x660 window, so 640x400 always covers it and is only ever cropped.
WALLPAPER_SIZE = (640, 400)

# Average colour of the first / last 14 rows of every wallpaper. The top bar
# and the clipboard panel use them as their solid background so the whole
# window reads as one continuous sheet of glass instead of three panels.
WALLPAPER_EDGES: dict[str, dict[str, str]] = {
    "frost/light": {"top": "#EBF2FE", "bottom": "#E1E0F7"},
    "frost/dark": {"top": "#384864", "bottom": "#192740"},
    "graphite/light": {"top": "#E2E3EB", "bottom": "#D0D0D7"},
    "graphite/dark": {"top": "#262E3F", "bottom": "#222B3F"},
    "pastel/light": {"top": "#C5D7C7", "bottom": "#DEC4C6"},
    "pastel/dark": {"top": "#3B2F3C", "bottom": "#5A3D38"},
}


# --------------------------------------------------------------------------
# Colour palettes
# --------------------------------------------------------------------------

# Structural colours only. Accent hues (blue / orange / red / teal / …) stay
# per-mode in TILE_ACCENTS below because iOS uses brighter variants at night.
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
        "active_body_t": 0.72,
        "active_glyph": "#FFFFFF",
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

# Tile accent hues, in DEFAULT_RADIAL_ITEMS order:
# 鼠标大小 普通粘贴 增强粘贴 对比度 AI 工具 亮度 浏览器 计算器
TILE_ACCENTS: dict[str, tuple[str, ...]] = {
    "light": (
        "#0A84FF",  # 鼠标大小
        "#FF9500",  # 普通粘贴 (橙)
        "#FF3B30",  # 增强粘贴 (红)
        "#30B0C7",  # 对比度
        "#AF52DE",  # AI 工具
        "#34C759",  # 亮度 (绿)
        "#5E5CE6",  # 浏览器 (靛蓝)
        "#0A84FF",  # 计算器
    ),
    "dark": (
        "#4FA9FF",  # 鼠标大小
        "#FF9F0A",  # 普通粘贴
        "#FF453A",  # 增强粘贴
        "#64D2FF",  # 对比度
        "#BF5AF2",  # AI 工具
        "#30D158",  # 亮度
        "#7D7CFF",  # 浏览器
        "#4FA9FF",  # 计算器
    ),
}

# Mode-identity colours used outside the wheel (paste badge, status dots).
MODE_COLORS: dict[str, dict[str, str]] = {
    "light": {
        "hover": "#0A84FF",
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


def mode_label(mode: object) -> str:
    mode = normalize_mode(mode)
    return dict(WHEEL_MODES)[mode]


def next_style(style: object) -> str:
    """The 「风格」 button cycles: 冰霜 → 烟晶 → 彩璃 → 冰霜."""
    order = STYLE_KEYS
    current = normalize_style(style)
    return order[(order.index(current) + 1) % len(order)]


def next_mode(mode: object) -> str:
    """The 「明暗」 button toggles 明亮 ⇄ 暗夜."""
    return "dark" if normalize_mode(mode) == "light" else "light"


def palette(mode: object) -> dict[str, str]:
    """A copy of the structural palette for ``mode`` (never shared/mutated)."""
    return dict(PALETTES[normalize_mode(mode)])


def tile_accents(mode: object) -> tuple[str, ...]:
    return TILE_ACCENTS[normalize_mode(mode)]


def accent_colors(mode: object) -> dict[str, str]:
    return dict(MODE_COLORS[normalize_mode(mode)])


def tile_colors(mode: object, accent: str) -> dict[str, str]:
    """Body / rim / glyph / shadow for one tile of the given accent."""
    pal = PALETTES[normalize_mode(mode)]
    body = pal["tile_body"]
    return {
        "body": body,
        "rim": mix(accent, pal["tile_rim_target"], pal["tile_rim_t"]),
        "glyph": mix(accent, pal["tile_glyph_target"], pal["tile_glyph_t"]),
        "shadow": pal["tile_shadow"],
        "hilite": mix(
            mix(accent, pal["tile_rim_target"], pal["tile_rim_t"]),
            pal["tile_rim_target"],
            0.6,
        ),
    }


def active_tile_colors(mode: object, accent: str) -> dict[str, str]:
    """The highlighted (current paste mode) tile: tinted body, white glyph."""
    pal = PALETTES[normalize_mode(mode)]
    return {
        "body": mix(accent, pal["tile_body"], pal["active_body_t"]),
        "rim": mix(accent, pal["tile_rim_target"], pal["tile_rim_t"]),
        "glyph": pal["active_glyph"],
        "shadow": pal["tile_shadow"],
        "hilite": mix(accent, "#FFFFFF", 0.6),
    }


def label_colors(mode: object, accent: str) -> dict[str, str]:
    pal = PALETTES[normalize_mode(mode)]
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
