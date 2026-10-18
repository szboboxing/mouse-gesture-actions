"""Radial (pie) menu panel for Mouse Gesture Actions.

Minimal Apple/iOS look: a clean frosted base with transparent, thin-outlined
tiles and label pills floating on top (soft shadow + hairline rim + glyph).
The current normal/enhanced paste mode is shown as a coloured badge in the
top status bar and highlighted on the matching wheel tile.
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class RadialItem:
    label: str
    icon_text: str
    action_type: str  # set_paste_*/calculator/browser/mouse_pointer_size/ai_tool/brightness/contrast/open
    modifiers: tuple[str, ...] = ()
    key: str = ""
    target: str = ""
    description: str = ""


DEFAULT_RADIAL_ITEMS: tuple[RadialItem, ...] = (
    RadialItem(
        label="鼠标大小",
        icon_text="⤢",
        action_type="mouse_pointer_size",
        description="打开鼠标指针大小设置",
    ),
    RadialItem(
        label="普通粘贴",
        icon_text="⧉",
        action_type="set_paste_normal",
        description="将增强粘贴切换为已关闭（普通粘贴）",
    ),
    RadialItem(
        label="增强粘贴",
        icon_text="⊕",
        action_type="set_paste_enhanced",
        description="将增强粘贴切换为已开启",
    ),
    RadialItem(
        label="对比度",
        icon_text="◐",
        action_type="contrast",
        description="左键提高对比度，右键降低对比度",
    ),
    RadialItem(
        label="AI 工具",
        icon_text="✦",
        action_type="ai_tool",
        description="打开设置页配置的 AI 工具",
    ),
    RadialItem(
        label="亮度",
        icon_text="☀",
        action_type="brightness",
        description="左键提高屏幕亮度，右键降低屏幕亮度",
    ),
    RadialItem(
        label="浏览器",
        icon_text="◎",
        action_type="browser",
        description="打开系统默认浏览器",
    ),
    RadialItem(
        label="计算器",
        icon_text="▦",
        action_type="calculator",
        description="打开计算器",
    ),
)


COLORS = {
    "bg": "#EEF1F8",
    "card": "#FFFFFF",
    "canvas_bg": "#EEF1F8",
    "top_bar": "#FFFFFF",
    "top_bar_border": "#D7DCE8",
    "status_text": "#1C1C1E",
    "status_muted": "#8E8E93",
    "hover": "#0A84FF",
    "icon_fg": "#1C1C1E",
    "icon_accent": "#0A84FF",
    "icon_success": "#34C759",
    "icon_warning": "#FF9500",
    "icon_pink": "#FF2D55",
    "icon_purple": "#AF52DE",
    "icon_indigo": "#5E5CE6",
    "icon_teal": "#30B0C7",
    "label_fg": "#1C1C1E",
    "center_fg": "#8E8E93",
    "status_green": "#34C759",
    "status_orange": "#FF9500",
    "status_red": "#FF3B30",
    # Paste-mode identity colours: 增强粘贴 = 红色, 普通粘贴 = 橙色
    "paste_enhanced": "#FF3B30",
    "paste_normal": "#FF9500",
}

# Frosted backdrop palette
_BASE = "#EEF1F8"
_SHADOW = "#B9C1D4"
_HILITE = "#FFFFFF"

# Accent hue per tile (thin outline colour + glyph tint)
# index order = DEFAULT_RADIAL_ITEMS: 鼠标大小 普通粘贴 增强粘贴 对比度
# AI 工具 亮度 浏览器 计算器. 增强=红, 普通=橙; 亮度/浏览器接手旧绿/靛蓝。
ITEM_ACCENTS: tuple[str, ...] = (
    COLORS["hover"],        # 鼠标大小
    COLORS["paste_normal"], # 普通粘贴 (橙)
    COLORS["paste_enhanced"],  # 增强粘贴 (红)
    COLORS["icon_teal"],    # 对比度
    COLORS["icon_purple"],  # AI 工具
    COLORS["icon_success"], # 亮度 (绿)
    COLORS["icon_indigo"],  # 浏览器 (靛蓝)
    COLORS["hover"],        # 计算器
)


def _mix(color_a: str, color_b: str, t: float) -> str:
    """Linear interpolation between two #rrggbb colours (t=0 → a)."""
    ar, ag, ab = int(color_a[1:3], 16), int(color_a[3:5], 16), int(color_a[5:7], 16)
    br, bg, bb = int(color_b[1:3], 16), int(color_b[3:5], 16), int(color_b[5:7], 16)
    r = round(ar + (br - ar) * t)
    g = round(ag + (bg - ag) * t)
    b = round(ab + (bb - ab) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


def _tint(accent: str, toward_white: float) -> str:
    """Glass body colour: blend accent toward the frosted base."""
    return _mix(accent, _BASE, toward_white)


def _rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    **kwargs,
) -> int:
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RadialMenuPanel(tk.Frame):
    """Embeddable radial menu panel — the primary UI of the application."""

    def __init__(
        self,
        parent: tk.Misc,
        on_item_selected: Callable[..., None] | None = None,
        on_settings: Callable[[], None] | None = None,
        items: tuple[RadialItem, ...] = DEFAULT_RADIAL_ITEMS,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.on_item_selected = on_item_selected
        self.on_settings = on_settings
        self.items = items
        self._canvas: tk.Canvas | None = None
        self._center_x: float = 0
        self._center_y: float = 0
        self._radius: float = 0
        self._inner_radius: float = 0
        self._cw: int = 0
        self._ch: int = 0
        self._hovered_index: int = -1
        self._status_var: tk.StringVar = tk.StringVar(value="正在初始化")
        self._status_dot_color: str = COLORS["status_orange"]
        self._paste_enhanced: bool | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        # Frosted top bar
        top_bar = tk.Frame(self, bg=COLORS["top_bar"], height=58)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)
        tk.Frame(self, bg=COLORS["top_bar_border"], height=1).pack(
            fill="x", side="top"
        )

        status_frame = tk.Frame(top_bar, bg=COLORS["top_bar"])
        status_frame.pack(side="left", padx=(24, 0), pady=14)

        self._status_canvas = tk.Canvas(
            status_frame,
            width=16,
            height=16,
            bg=COLORS["top_bar"],
            highlightthickness=0,
        )
        self._status_canvas.pack(side="left", padx=(0, 10))
        # status dot with a soft halo
        self._status_canvas.create_oval(2, 2, 14, 14, fill="#E6E9F2", outline="")
        self._status_dot_id = self._status_canvas.create_oval(
            4, 4, 12, 12, fill=self._status_dot_color, outline=""
        )

        tk.Label(
            status_frame,
            textvariable=self._status_var,
            bg=COLORS["top_bar"],
            fg=COLORS["status_text"],
            font=("Microsoft YaHei UI", 12, "bold"),
        ).pack(side="left")

        # Glass settings pill
        settings_btn = tk.Button(
            top_bar,
            text="⚙  设置",
            command=self._handle_settings,
            bg=_tint(COLORS["hover"], 0.82),
            fg=COLORS["hover"],
            activebackground=_tint(COLORS["hover"], 0.68),
            activeforeground=COLORS["hover"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 11, "bold"),
            padx=18,
            pady=6,
        )
        settings_btn.pack(side="right", padx=(0, 20), pady=12)

        # Paste-mode badge (right of status, left of settings button).
        self._mode_badge = tk.Label(
            top_bar,
            text="",
            bg=COLORS["top_bar"],
            fg=COLORS["status_muted"],
            font=("Microsoft YaHei UI", 11, "bold"),
            padx=14,
            pady=5,
        )
        self._mode_badge.pack(side="right", padx=(0, 12), pady=13)
        self._update_mode_badge()

        # Canvas area for the frosted radial menu
        canvas_frame = tk.Frame(self, bg=COLORS["canvas_bg"])
        canvas_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(
            canvas_frame,
            bg=COLORS["canvas_bg"],
            highlightthickness=0,
        )
        self._canvas.pack(fill="both", expand=True)

        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Button-3>", self._on_right_click)
        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<Leave>", self._on_leave)

    def set_status(self, text: str, color: str) -> None:
        self._status_var.set(text)
        self._status_dot_color = color
        if self._status_canvas is not None:
            self._status_canvas.itemconfigure(
                self._status_dot_id, fill=color
            )

    def set_items(self, items: tuple[RadialItem, ...]) -> None:
        self.items = items
        self._redraw()

    def set_paste_mode(self, enhanced: bool | None) -> None:
        """Highlight the paste tile matching the current switch state."""
        self._paste_enhanced = enhanced
        self._update_mode_badge()
        self._redraw()

    def _update_mode_badge(self) -> None:
        """Reflect the normal/enhanced paste mode in the top-bar badge."""
        if getattr(self, "_mode_badge", None) is None:
            return
        if self._paste_enhanced is True:
            self._mode_badge.configure(
                text="●  增强模式",
                bg=_tint(COLORS["paste_enhanced"], 0.86),
                fg=COLORS["paste_enhanced"],
            )
        elif self._paste_enhanced is False:
            self._mode_badge.configure(
                text="●  普通模式",
                bg=_tint(COLORS["paste_normal"], 0.82),
                fg=COLORS["paste_normal"],
            )
        else:
            self._mode_badge.configure(
                text="", bg=COLORS["top_bar"], fg=COLORS["status_muted"]
            )

    def _handle_settings(self) -> None:
        if self.on_settings is not None:
            self.on_settings()

    def _on_resize(self, event: tk.Event) -> None:
        self._cw = event.width
        self._ch = event.height
        self._center_x = event.width / 2
        self._center_y = event.height / 2
        available = min(event.width, event.height)
        self._radius = available * 0.36
        self._inner_radius = self._radius * 0.12
        self._draw_menu()

    def _redraw(self) -> None:
        if self._canvas is not None and self._radius > 0:
            self._draw_menu()

    def _draw_tile(
        self,
        canvas: tk.Canvas,
        ix: float,
        iy: float,
        half: float,
        accent: str,
        glyph: str,
        tags: str,
        *,
        active: bool = False,
        active_fill: str | None = None,
        glyph_fill: str | None = None,
    ) -> None:
        """Transparent floating tile: near-invisible body + thin accent
        outline + soft shadow so the glyph floats on the plain backdrop.
        Active tiles (current paste mode) get a tinted body + stronger rim.
        """
        radius = half * 0.44
        # faint floating shadow
        _rounded_rect(
            canvas,
            ix - half + 2,
            iy - half + 5,
            ix + half - 2,
            iy + half + 6,
            radius,
            fill=_mix(_BASE, _SHADOW, 0.5),
            outline="",
            tags=tags,
        )
        if active:
            fill_color = active_fill or accent
            body = _tint(fill_color, 0.72)
            outline = fill_color
            width = 2.4
            text_fill = glyph_fill or "#FFFFFF"
        else:
            body = _mix(_BASE, accent, 0.06)
            outline = _mix(_BASE, accent, 0.7)
            width = 1.6
            text_fill = glyph_fill or _mix(accent, "#2A2A30", 0.1)
        _rounded_rect(
            canvas,
            ix - half,
            iy - half,
            ix + half,
            iy + half,
            radius,
            fill=body,
            outline=outline,
            width=width,
            tags=tags,
        )
        # thin specular tick on the top-left rim (subtle)
        canvas.create_line(
            ix - half + radius,
            iy - half + 1.5,
            ix - half * 0.1,
            iy - half + 1.5,
            fill=_mix(outline, _HILITE, 0.6),
            width=1,
            tags=tags,
        )
        canvas.create_text(
            ix,
            iy,
            text=glyph,
            fill=text_fill,
            font=("Segoe UI Symbol", int(half * 0.95), "bold"),
            tags=tags,
        )

    def _draw_menu(self) -> None:
        canvas = self._canvas
        if canvas is None:
            return

        canvas.delete("all")

        cx, cy = self._center_x, self._center_y
        r = self._radius
        if r <= 0:
            return

        # Clean frosted base (no colour blobs) so tiles read as transparent.
        canvas.configure(bg=_BASE)

        n = len(self.items)
        icon_radius = r * 0.20
        item_r = r * 0.72

        # Very faint orbit ring
        canvas.create_oval(
            cx - item_r,
            cy - item_r,
            cx + item_r,
            cy + item_r,
            outline=_mix(_BASE, "#B9C1D4", 0.35),
            width=1,
        )

        for index, item in enumerate(self.items):
            angle = (2 * math.pi * index / n) - math.pi / 2
            ix = cx + item_r * math.cos(angle)
            iy = cy + item_r * math.sin(angle)

            accent = ITEM_ACCENTS[index % len(ITEM_ACCENTS)]

            active = None
            if item.action_type == "set_paste_enhanced":
                active = self._paste_enhanced is True
            elif item.action_type == "set_paste_normal":
                active = self._paste_enhanced is False

            if active:
                active_fill = (
                    COLORS["paste_enhanced"]
                    if item.action_type == "set_paste_enhanced"
                    else COLORS["paste_normal"]
                )
                self._draw_tile(
                    canvas,
                    ix,
                    iy,
                    icon_radius,
                    accent,
                    item.icon_text,
                    tags=f"item_{index}",
                    active=True,
                    active_fill=active_fill,
                )
            else:
                self._draw_tile(
                    canvas,
                    ix,
                    iy,
                    icon_radius,
                    accent,
                    item.icon_text,
                    tags=f"item_{index}",
                )

            # Label: transparent pill (body matches base, hairline only)
            label_r = r * 1.08
            lx = cx + label_r * math.cos(angle)
            ly = cy + label_r * math.sin(angle)

            label_text = item.label
            has_hint = item.action_type in ("brightness", "contrast")
            text_w = len(label_text) * 13 + 26
            if has_hint:
                text_w += 46
            text_h = 28
            corner = text_h / 2

            _rounded_rect(
                canvas,
                lx - text_w / 2,
                ly - text_h / 2,
                lx + text_w / 2,
                ly + text_h / 2,
                corner,
                fill=_mix(_BASE, accent, 0.05),
                outline=_mix(_BASE, accent, 0.5),
                width=1,
                tags=f"item_{index}",
            )
            if has_hint:
                # Label on the left, ＋/－ hint on the right of the pill.
                canvas.create_text(
                    lx - 23,
                    ly,
                    text=label_text,
                    fill=COLORS["label_fg"],
                    font=("Microsoft YaHei UI", 10, "bold"),
                    tags=f"item_{index}",
                    anchor="e",
                )
                canvas.create_text(
                    lx + 23,
                    ly,
                    text="＋/－",
                    fill=_mix(accent, "#2A2A30", 0.1),
                    font=("Microsoft YaHei UI", 9, "bold"),
                    tags=f"item_{index}",
                    anchor="w",
                )
            else:
                canvas.create_text(
                    lx,
                    ly,
                    text=label_text,
                    fill=COLORS["label_fg"],
                    font=("Microsoft YaHei UI", 10, "bold"),
                    tags=f"item_{index}",
                )

        # Central transparent hub (settings)
        close_r = self._inner_radius
        self._draw_tile(
            canvas,
            cx,
            cy,
            close_r,
            COLORS["hover"],
            "⚙",
            tags="center",
            glyph_fill=COLORS["center_fg"],
        )

    def _on_motion(self, event: tk.Event) -> None:
        index = self._hit_test(event.x, event.y)
        if index != self._hovered_index:
            self._clear_hover()
            self._hovered_index = index
            if index >= 0:
                self._draw_hover(index)

    def _draw_hover(self, index: int) -> None:
        if self._canvas is None:
            return
        n = len(self.items)
        angle = (2 * math.pi * index / n) - math.pi / 2
        r = self._radius
        cx, cy = self._center_x, self._center_y
        item_r = r * 0.72
        ix = cx + item_r * math.cos(angle)
        iy = cy + item_r * math.sin(angle)
        half = r * 0.20
        accent = ITEM_ACCENTS[index % len(ITEM_ACCENTS)]

        _rounded_rect(
            self._canvas,
            ix - half - 4,
            iy - half - 4,
            ix + half + 4,
            iy + half + 4,
            half * 0.5,
            fill="",
            outline=accent,
            width=2,
            tags="hover_ring",
        )

    def _clear_hover(self) -> None:
        if self._canvas is not None:
            self._canvas.delete("hover_ring")
        self._hovered_index = -1

    def _on_leave(self, _event: tk.Event) -> None:
        self._clear_hover()

    def _on_click(self, event: tk.Event) -> None:
        self._dispatch(event, right=False)

    def _on_right_click(self, event: tk.Event) -> None:
        self._dispatch(event, right=True)

    def _dispatch(self, event: tk.Event, *, right: bool) -> None:
        cx, cy = self._center_x, self._center_y
        dist_to_center = math.hypot(event.x - cx, event.y - cy)
        if dist_to_center <= self._inner_radius * 1.9:
            # Only the left click on the hub opens settings.
            if not right:
                self._handle_settings()
            return

        index = self._hit_test(event.x, event.y)
        if index >= 0 and self.on_item_selected is not None:
            self.on_item_selected(self.items[index], right)

    def _hit_test(self, x: float, y: float) -> int:
        cx, cy = self._center_x, self._center_y
        dx = x - cx
        dy = y - cy
        distance = math.hypot(dx, dy)

        inner_bound = self._inner_radius * 1.9
        outer_bound = self._radius * 1.18
        if distance < inner_bound or distance > outer_bound:
            return -1

        n = len(self.items)
        icon_radius = self._radius * 0.20
        item_r = self._radius * 0.72

        angle = math.atan2(dy, dx)
        angle = angle + math.pi / 2
        if angle < 0:
            angle += 2 * math.pi

        sector_angle = 2 * math.pi / n
        # Tiles are centred on sector boundaries (i * sector), so round to
        # the nearest sector rather than floor — otherwise the half of each
        # tile that leans toward the previous sector would map to the wrong
        # index and fail the distance check (making it unclickable).
        index = int(angle / sector_angle + 0.5) % n

        # Only register a hit near the tile body, not the label zone
        item_angle = (2 * math.pi * index / n) - math.pi / 2
        ix = cx + item_r * math.cos(item_angle)
        iy = cy + item_r * math.sin(item_angle)
        tile_dist = math.hypot(x - ix, y - iy)
        if tile_dist > icon_radius * 1.4:
            return -1
        return index
