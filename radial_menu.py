"""Radial (pie) menu panel for Mouse Gesture Actions.

The wheel sits on one of three wallpapers — 奶油 / 冷淡 / 苹果 — each of which
brings its own colours *and* its own shape language from ``themes``: 奶油 is a
soft, lifted cream card, 冷淡 a flat hairline square, 苹果 a piece of frosted
glass. The 「明暗」 button switches between the light and dark variant of the
current style. Tiles are always opaque cards because Tk canvases cannot
alpha-blend, so they stay readable on top of the picture. The current
normal/enhanced paste mode is shown as a coloured badge in the top status bar
and highlighted on the matching wheel tile.

奶油风 and 苹果风 paint their tiles with pre-rendered 3D icons (``assets/icons``)
while 冷淡风 keeps the flat text glyph — being flat *is* that style. Hovering a
tile springs it outward and upward, then springs it back when the pointer
leaves; the spring is integrated per frame in ``_tick`` rather than tweened
between two static states, which is what gives the release its small bounce.
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from dataclasses import dataclass
from typing import Callable

import themes

# --- hover lift (a damped spring, so releasing bounces once and settles) ---- #
LIFT_SCALE = 0.14  # how much bigger a lifted tile gets
LIFT_RAISE = 4.0  # px it floats toward the viewer
LIFT_MIN = -0.15  # overshoot floor: the tile may dip slightly below rest
SPRING_K = 380.0  # stiffness
SPRING_C = 22.0  # damping
FRAME_MS = 16  # ~60fps, and Tk coalesces the redraws anyway

# Snap tolerance for the spring: below this the tile is declared at rest. An
# asymptotic spring would otherwise keep the frame loop alive forever on a
# sub-pixel wobble.
SPRING_EPS = 0.004
SPRING_V_EPS = 0.05


def spring_step(
    current: float, velocity: float, target: float, dt: float
) -> tuple[float, float, bool]:
    """Advance one damped-spring frame for a single tile.

    Returns ``(value, velocity, settling)``. Pure so the animation can be
    tested without opening a Tk window.
    """
    accel = (target - current) * SPRING_K - velocity * SPRING_C
    velocity += accel * dt
    current = max(LIFT_MIN, current + velocity * dt)
    if abs(current - target) < SPRING_EPS and abs(velocity) < SPRING_V_EPS:
        return target, 0.0, False
    return current, velocity, True


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
        description="点左半「＋」提高对比度，点右半「－」降低对比度",
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
        description="点左半「＋」提高屏幕亮度，点右半「－」降低屏幕亮度",
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


# Light-mode colour map kept for backwards compatibility: app.py and
# clipboard_history.py still read a few keys from it. The wheel itself paints
# from ``themes.palette(mode, style)`` so it can follow either button.
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

# Accent hue per tile in the default 奶油 style (thin outline colour + glyph
# tint). Index order = DEFAULT_RADIAL_ITEMS: 鼠标大小 普通粘贴 增强粘贴 对比度
# AI 工具 亮度 浏览器 计算器. 增强=警示橙, 普通=奶茶金.
# The wheel itself asks ``themes.tile_accents(mode, style)`` so every style and
# 暗夜 can restate them.
ITEM_ACCENTS: tuple[str, ...] = themes.tile_accents(
    "light", themes.DEFAULT_WHEEL_STYLE
)

# Tiles whose icon is split into two independent halves: the left half is the
# 「＋」button and the right half is the 「－」button. Both halves respond to the
# left mouse button. The previous 「右键减」 gesture could not be relied on: the
# global low-level hook consumes WM_RBUTTONDOWN while a right-held gesture is
# active, so a right-click on the wheel did not always reach the canvas.
SPLIT_ACTIONS = frozenset({"brightness", "contrast"})

# Kept as an alias: colour maths now lives in themes so every widget blends
# the light/dark palettes the same way.
_mix = themes.mix


class _Tooltip:
    """Tiny hover hint — no external widgets, works offline in the EXE."""

    _current: "_Tooltip | None" = None

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Button-1>", self._hide, add="+")

    def _schedule(self, _event: tk.Event) -> None:
        _Tooltip.dismiss()
        try:
            self.widget.after(650, self._show)
        except tk.TclError:
            pass

    def _show(self) -> None:
        if self.window is not None or not self.widget.winfo_exists():
            return
        _Tooltip.dismiss()
        x = self.widget.winfo_rootx() + 6
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.window,
            text=self.text,
            bg="#1C1C1E",
            fg="#FFFFFF",
            font=themes.wheel_font(9, "normal"),
            padx=8,
            pady=4,
        ).pack()
        _Tooltip._current = self

    def _hide(self, _event: tk.Event | None = None) -> None:
        _Tooltip.dismiss()

    @classmethod
    def dismiss(cls) -> None:
        tip = cls._current
        if tip is not None and tip.window is not None:
            try:
                tip.window.destroy()
            except tk.TclError:
                pass
            tip.window = None
        cls._current = None


def _attach_tooltip(widget: tk.Widget, text: str) -> None:
    """Best-effort hint: never let a tooltip break the button it decorates."""
    try:
        widget._qoder_tooltip = _Tooltip(widget, text)
    except (AttributeError, tk.TclError):
        pass


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
        style: str | None = None,
        mode: str | None = None,
        on_theme_change: Callable[[str, str], None] | None = None,
    ) -> None:
        self.style = themes.normalize_style(style)
        self.mode = themes.normalize_mode(mode)
        self.on_item_selected = on_item_selected
        self.on_settings = on_settings
        self.on_theme_change = on_theme_change
        self.items = items
        self._canvas: tk.Canvas | None = None
        self._geo: dict[str, float | bool] = themes.geometry(self.style)
        self._center_x: float = 0
        self._center_y: float = 0
        self._radius: float = 0
        self._inner_radius: float = 0
        self._cw: int = 0
        self._ch: int = 0
        self._hovered_key: tuple[int, int] = (-1, 0)
        self._status_var: tk.StringVar = tk.StringVar(value="正在初始化")
        self._status_dot_color: str = themes.accent_colors(
            self.mode, self.style
        )["warning"]
        self._paste_enhanced: bool | None = None
        # Wallpaper PhotoImages are cached per style/mode so switching back is
        # instant and the reference keeps Tk from discarding the picture.
        self._bg_images: dict[str, tk.PhotoImage] = {}
        # 3D icon pictures are cached per (style, mode, key, size) bucket; the
        # reference matters for the same reason as above.
        self._icon_images: dict[str, tk.PhotoImage] = {}
        # Per-tile spring state for the hover lift.
        self._lift: dict[int, float] = {}
        self._lift_velocity: dict[int, float] = {}
        self._anim_job: str | None = None
        self._anim_last: float | None = None
        self._apply_theme_state()

        super().__init__(parent, bg=self._pal["base"])
        self._build_ui()

    # ------------------------------------------------------------------
    # Theme (glass style + light/dark palette)
    # ------------------------------------------------------------------

    def _apply_theme_state(self) -> None:
        """Pull the whole design sheet for the current 风格 × 明暗 combination.

        Colours and shape both come from ``themes``; nothing here hard-codes a
        hex value or a corner radius, so adding a style never touches this file.
        """
        self._pal = themes.palette(self.mode, self.style)
        self._geo = themes.geometry(self.style)
        self._edges = themes.wallpaper_edges(self.style, self.mode)
        self._accents = themes.accent_colors(self.mode, self.style)
        self._accents["gray"] = themes.tile_accents(self.mode, self.style)[-1]
        self._bg_color = themes.mix(
            self._edges["top"], self._edges["bottom"], 0.5
        )

    @property
    def palette(self) -> dict[str, str]:
        """The palette the wheel is currently painted with."""
        return dict(self._pal)

    def theme(self) -> tuple[str, str]:
        return (self.style, self.mode)

    def set_theme(
        self,
        style: str | None = None,
        mode: str | None = None,
        *,
        notify: bool = True,
    ) -> None:
        """Switch the wallpaper style and/or the light/dark palette."""
        if style is not None:
            self.style = themes.normalize_style(style)
        if mode is not None:
            self.mode = themes.normalize_mode(mode)
        self._apply_theme_state()
        self.configure(bg=self._pal["base"])
        self._rebuild_ui()
        if notify and self.on_theme_change is not None:
            self.on_theme_change(self.style, self.mode)

    def cycle_style(self) -> None:
        self.set_theme(style=themes.next_style(self.style))

    def toggle_mode(self) -> None:
        self.set_theme(mode=themes.next_mode(self.mode))

    def _rebuild_ui(self) -> None:
        """Re-create every child widget so the new palette is applied."""
        self._stop_animation()
        if self._canvas is not None:
            self._canvas.delete("all")
        for child in self.winfo_children():
            child.destroy()
        self._hovered_key = (-1, 0)
        self._build_ui()

    def _stop_animation(self) -> None:
        """Drop the hover spring: used on rebuild and on destroy."""
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except (tk.TclError, ValueError):
                pass
            self._anim_job = None
        self._lift.clear()
        self._lift_velocity.clear()
        self._anim_last = None

    def destroy(self) -> None:
        self._stop_animation()
        super().destroy()

    def _background_image(self) -> tk.PhotoImage | None:
        """Load (and cache) the wallpaper for the current style/mode."""
        key = f"{self.style}_{self.mode}"
        cached = self._bg_images.get(key)
        if cached is not None:
            return cached
        path = themes.wallpaper_path(self.style, self.mode)
        if not path.is_file():
            return None
        try:
            image = tk.PhotoImage(file=str(path))
        except tk.TclError:
            return None
        self._bg_images[key] = image
        return image

    def _icon_image(self, key: str, size: int) -> tk.PhotoImage | None:
        """Load (and cache) one 3D icon, or None so the caller uses the glyph.

        Only 奶油风 and 苹果风 have icon art; a missing file degrades to the
        flat text glyph rather than to an empty tile.
        """
        if not themes.uses_3d_icons(self.style):
            return None
        cache_key = f"{self.style}_{self.mode}_{key}_{size}"
        cached = self._icon_images.get(cache_key)
        if cached is not None:
            return cached
        path = themes.icon_path(self.style, self.mode, key, size)
        if not path.is_file():
            return None
        try:
            image = tk.PhotoImage(file=str(path))
        except tk.TclError:
            return None
        self._icon_images[cache_key] = image
        return image

    def _draw_glyph(
        self,
        canvas: tk.Canvas,
        ix: float,
        iy: float,
        half: float,
        glyph: str,
        color: str,
        tags: str,
        *,
        size_factor: float = 1.15,
    ) -> None:
        """Tile artwork: a pre-rendered 3D icon when available, else the glyph.

        Tk cannot rescale a picture smoothly, so the icon snaps to the nearest
        rendered bucket; the card around it still scales continuously.
        """
        key = themes.icon_key(glyph)
        image = None
        if key is not None:
            image = self._icon_image(
                key, themes.icon_size_for(half * size_factor)
            )
        if image is not None:
            canvas.create_image(ix, iy, image=image, anchor="center", tags=tags)
            return
        canvas.create_text(
            ix,
            iy,
            text=glyph,
            fill=color,
            font=themes.wheel_font(
                max(9, int(half * size_factor * 0.83 * self._geo["glyph_scale"])),
                family="Segoe UI Symbol",
            ),
            tags=tags,
        )

    def _build_ui(self) -> None:
        pal = self._pal
        # Top bar painted with the wallpaper's own top edge colour so the bar,
        # the picture and the clipboard panel read as one sheet of glass.
        top_bar = tk.Frame(self, bg=self._edges["top"], height=58)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)
        tk.Frame(self, bg=pal["top_bar_border"], height=1).pack(
            fill="x", side="top"
        )

        # pack 的顺序就是顶栏的空间分配顺序：先 pack 的控件先拿到自己需要的
        # 宽度，最后一个 pack 的控件承担所有挤压。V2.7.2 之前左侧状态区排在第
        # 一位，最长状态文案（已开启 · 正在监听）+「增强模式」徽标下整行实测需
        # 要 661px，超出 640px 窗口，被挤出可视区的正好是最后 pack 的「风格」药
        # 丸——按钮看不见也点不到。
        # 现在两件事一起改：各处间距收紧到最长文案也能在 640px 内放下（实测
        # ~605px），并把右侧按钮组排在前面、左侧状态区最后 pack。这样即使窗口
        # 被拖到最小尺寸，让步的也只是状态文字末尾几个像素，四枚按钮永远完整可点。

        # Glass settings pill
        settings_btn = tk.Button(
            top_bar,
            text="⚙  更多设置",
            command=self._handle_settings,
            bg=pal["pill_body"],
            fg=pal["pill_text"],
            activebackground=pal["pill_hover"],
            activeforeground=pal["pill_text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=themes.wheel_font(11),
            padx=14,
            pady=6,
        )
        settings_btn.pack(side="right", padx=(0, 14), pady=12)

        # Paste-mode badge (left of the settings button).
        self._mode_badge = tk.Label(
            top_bar,
            text="",
            bg=self._edges["top"],
            fg=pal["status_muted"],
            font=themes.wheel_font(11),
            padx=10,
            pady=5,
        )
        self._mode_badge.pack(side="right", padx=(0, 9), pady=13)
        self._update_mode_badge()

        # 「明暗」 toggle, then 「风格」 — packed right-to-left so 风格 ends up
        # furthest from the settings button.
        self._mode_btn = self._pill(
            top_bar,
            f"{'☾' if self.mode == 'dark' else '☀'}  {themes.mode_label(self.mode)}",
            self.toggle_mode,
            tip="切换明亮模式 / 暗夜模式",
        )
        self._mode_btn.pack(side="right", padx=(0, 6), pady=12)

        self._style_btn = self._pill(
            top_bar,
            f"{themes.style_icon(self.style)} 风格 · {themes.style_label(self.style)}",
            self.cycle_style,
            tip="切换轮盘外观：奶油 → 冷淡 → 苹果",
        )
        self._style_btn.pack(side="right", padx=(0, 6), pady=12)

        # Left status area — packed LAST on purpose (see the note above).
        status_frame = tk.Frame(top_bar, bg=self._edges["top"])
        self._status_canvas = tk.Canvas(
            status_frame,
            width=16,
            height=16,
            bg=self._edges["top"],
            highlightthickness=0,
        )
        self._status_canvas.pack(side="left", padx=(0, 7))
        # status dot with a soft halo
        self._status_canvas.create_oval(
            2, 2, 14, 14, fill=themes.mix(self._edges["top"], pal["base"], 0.5), outline=""
        )
        self._status_dot_id = self._status_canvas.create_oval(
            4, 4, 12, 12, fill=self._status_dot_color, outline=""
        )

        tk.Label(
            status_frame,
            textvariable=self._status_var,
            bg=self._edges["top"],
            fg=pal["status_text"],
            font=themes.wheel_font(11),
            anchor="w",
        ).pack(side="left")

        status_frame.pack(side="left", padx=(13, 0), pady=14)

        # Canvas area carrying the glass wallpaper + the wheel
        canvas_frame = tk.Frame(self, bg=self._bg_color)
        canvas_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(
            canvas_frame,
            bg=self._bg_color,
            highlightthickness=0,
        )
        self._canvas.pack(fill="both", expand=True)

        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Button-3>", self._on_right_click)
        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<Leave>", self._on_leave)

        if self._cw > 0 and self._ch > 0:
            # Repaint straight away after a theme switch (no new Configure
            # arrives because the geometry did not change).
            self._draw_menu()

    def _pill(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        tip: str = "",
    ) -> tk.Button:
        pal = self._pal
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=pal["pill_body"],
            fg=pal["pill_text"],
            activebackground=pal["pill_hover"],
            activeforeground=pal["pill_text"],
            disabledforeground=pal["pill_text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=themes.wheel_font(10),
            padx=11,
            pady=5,
            highlightthickness=1,
            highlightbackground=pal["pill_rim"],
            highlightcolor=pal["pill_rim"],
        )
        if tip:
            _attach_tooltip(btn, tip)
        return btn

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
        pal = self._pal
        if self._paste_enhanced is True:
            accent = self._accents["paste_enhanced"]
            self._mode_badge.configure(
                text="●  增强模式",
                bg=themes.mix(accent, pal["tile_body"], 0.80),
                fg=themes.mix(accent, pal["status_text"], 0.15),
            )
        elif self._paste_enhanced is False:
            accent = self._accents["paste_normal"]
            self._mode_badge.configure(
                text="●  普通模式",
                bg=themes.mix(accent, pal["tile_body"], 0.80),
                fg=themes.mix(accent, pal["status_text"], 0.15),
            )
        else:
            self._mode_badge.configure(
                text="", bg=self._edges["top"], fg=pal["status_muted"]
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
        body: str | None = None,
        hub: bool = False,
        lift: float = 0.0,
    ) -> None:
        """Card: solid body + thin accent rim + optional drop shadow.

        The body is opaque because Tk canvases cannot alpha-blend, and the
        tile has to stay readable on top of the glass wallpaper. Active tiles
        (current paste mode) get an accent-tinted body + a stronger rim.

        Corner radius, rim width, shadow depth and the specular tick all come
        from the style's geometry sheet — that is what makes 冷淡风 read as a
        flat hairline square and 奶油风 as a lifted soft card. ``lift`` is the
        hover spring (0 = at rest, 1 = fully raised): it only deepens the
        shadow, because the raised position and size are already baked into
        ``ix``/``iy``/``half`` by ``_tile_box``.
        """
        geo = self._geo
        radius = half * (geo["hub_radius"] if hub else geo["tile_radius"])
        if active:
            colors = themes.active_tile_colors(
                self.mode, active_fill or accent, self.style
            )
            width = geo["active_rim_width"]
        else:
            colors = themes.tile_colors(self.mode, accent, self.style)
            width = geo["rim_width"]
        depth = geo["shadow_depth"] * (1.0 + 1.35 * lift)
        if depth > 0:  # faint floating shadow; 冷淡风 keeps it off
            _rounded_rect(
                canvas,
                ix - half + 2,
                iy - half + (5 + 3.5 * lift) * depth,
                ix + half - 2,
                iy + half + (6 + 5.0 * lift) * depth,
                radius,
                fill=colors["shadow"],
                outline="",
                tags=tags,
            )
        _rounded_rect(
            canvas,
            ix - half,
            iy - half,
            ix + half,
            iy + half,
            radius,
            fill=body or colors["body"],
            outline=colors["rim"],
            width=width,
            tags=tags,
        )
        # thin specular tick on the top-left rim (subtle)
        if geo["specular"]:
            canvas.create_line(
                ix - half + radius,
                iy - half + 1.5,
                ix - half * 0.1,
                iy - half + 1.5,
                fill=colors["hilite"],
                width=1,
                tags=tags,
            )
        self._draw_glyph(
            canvas, ix, iy, half, glyph, glyph_fill or colors["glyph"], tags
        )

    def _item_center(self, index: int) -> tuple[float, float]:
        """Tile centre for a wheel index using the same layout maths as drawing."""
        angle = (2 * math.pi * index / len(self.items)) - math.pi / 2
        item_r = self._radius * 0.72
        return (
            self._center_x + item_r * math.cos(angle),
            self._center_y + item_r * math.sin(angle),
        )

    @staticmethod
    def _split_button_boxes(
        ix: float,
        iy: float,
        half: float,
    ) -> tuple[tuple[int, float, float, float, float], ...]:
        """Return (sign, centre_x, centre_y, width, height) for the ＋/－ halves."""
        return (
            (1, ix - half * 0.5, iy + half * 0.42, half * 0.88, half * 0.72),
            (-1, ix + half * 0.5, iy + half * 0.42, half * 0.88, half * 0.72),
        )

    def _draw_split_tile(
        self,
        canvas: tk.Canvas,
        ix: float,
        iy: float,
        half: float,
        accent: str,
        glyph: str,
        tags: str,
        *,
        lift: float = 0.0,
    ) -> None:
        """Brightness / contrast tile: one body, two clickable parts.

        The function glyph stays on the upper part of the tile, while the lower
        part is divided into a 「＋」button (left) and a 「－」button (right). Both
        parts work with the left mouse button, so decreasing no longer depends
        on a right-click reaching the canvas.
        """
        geo = self._geo
        radius = half * geo["tile_radius"]
        pal = self._pal
        colors = themes.tile_colors(self.mode, accent, self.style)
        depth = geo["shadow_depth"] * (1.0 + 1.35 * lift)
        if depth > 0:
            _rounded_rect(
                canvas,
                ix - half + 2,
                iy - half + (5 + 3.5 * lift) * depth,
                ix + half - 2,
                iy + half + (6 + 5.0 * lift) * depth,
                radius,
                fill=colors["shadow"],
                outline="",
                tags=tags,
            )
        _rounded_rect(
            canvas,
            ix - half,
            iy - half,
            ix + half,
            iy + half,
            radius,
            fill=colors["body"],
            outline=colors["rim"],
            width=geo["rim_width"],
            tags=tags,
        )
        if geo["specular"]:
            canvas.create_line(
                ix - half + radius,
                iy - half + 1.5,
                ix - half * 0.1,
                iy - half + 1.5,
                fill=colors["hilite"],
                width=1,
                tags=tags,
            )
        self._draw_glyph(
            canvas,
            ix,
            iy - half * 0.42,
            half,
            glyph,
            colors["glyph"],
            tags,
            size_factor=0.75,
        )
        canvas.create_line(
            ix,
            iy - half * 0.02,
            ix,
            iy + half * 0.9,
            fill=pal["divider"],
            width=1,
            tags=tags,
        )
        # The 「＋」 chip is a solid accent block, so its own text colour has to
        # follow the accent: 冷淡's mid-tone steel blue would eat a white 「＋」.
        increase_text = themes.readable_text_on(accent)
        for sign, bx, by, bw, bh in self._split_button_boxes(ix, iy, half):
            increase = sign > 0
            _rounded_rect(
                canvas,
                bx - bw / 2,
                by - bh / 2,
                bx + bw / 2,
                by + bh / 2,
                min(bw, bh) * geo["sub_radius"],
                fill=accent if increase else pal["minus_body"],
                outline=accent if increase else pal["minus_rim"],
                width=1.4,
                tags=tags,
            )
            canvas.create_text(
                bx,
                by,
                text="＋" if increase else "－",
                fill=increase_text if increase else pal["minus_text"],
                font=themes.wheel_font(max(10, int(half * 0.56))),
                tags=tags,
            )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _lift_of(self, index: int) -> float:
        """Current hover lift for a tile: 0 at rest, 1 fully raised."""
        return self._lift.get(index, 0.0)

    def _tile_box(
        self, index: int, lift: float | None = None
    ) -> tuple[float, float, float]:
        """(centre_x, centre_y, half) for a tile, honouring its hover lift.

        A lifted tile grows and floats toward the viewer. Hit-testing keeps
        using the resting box on purpose: a tile that got bigger must not
        chase the pointer into a different hover state.
        """
        if lift is None:
            lift = self._lift_of(index)
        ix, iy = self._item_center(index)
        return (
            ix,
            iy - LIFT_RAISE * lift,
            self._radius * 0.20 * (1.0 + LIFT_SCALE * lift),
        )

    def _draw_menu(self) -> None:
        canvas = self._canvas
        if canvas is None:
            return

        canvas.delete("all")

        cx, cy = self._center_x, self._center_y
        r = self._radius
        pal = self._pal

        # Glass wallpaper for the current 风格 × 明暗 combination, centred so a
        # smaller window simply crops it. Falls back to the flat palette base
        # if the asset is missing so the wheel never renders without a backdrop.
        image = self._background_image()
        if image is not None:
            canvas.configure(bg=self._bg_color)
            canvas.create_image(
                self._cw / 2,
                self._ch / 2,
                image=image,
                anchor="center",
                tags="bg",
            )
        else:
            canvas.configure(bg=pal["base"])

        if r <= 0:
            return

        item_r = r * 0.72

        # Very faint orbit ring
        canvas.create_oval(
            cx - item_r,
            cy - item_r,
            cx + item_r,
            cy + item_r,
            outline=pal["orbit"],
            width=1,
        )

        for index in range(len(self.items)):
            self._paint_tile(index)

        # Central hub (settings)
        close_r = self._inner_radius
        self._draw_tile(
            canvas,
            cx,
            cy,
            close_r,
            self._accents["hover"],
            "⚙",
            tags="center",
            body=pal["hub_body"],
            glyph_fill=pal["hub_glyph"],
            hub=True,
        )
        # 中心 ⚙ 下方的小字：轮盘只放快捷动作，其余都在设置页
        canvas.create_text(
            cx,
            cy + close_r * 1.85,
            text="更多设置",
            fill=pal["hub_text"],
            font=themes.wheel_font(8, "normal"),
            tags="center",
        )

        self._redraw_hover_ring()

    def _paint_tile(self, index: int) -> None:
        """(Re)draw one tile plus its label, honouring that tile's hover lift.

        Only this tile's canvas items are deleted and rebuilt, so the spring
        can run at frame rate without ever clearing the wallpaper. Redrawing
        also raises the tile, which is exactly right for the one floating
        toward the viewer.
        """
        canvas = self._canvas
        if canvas is None or self._radius <= 0 or index >= len(self.items):
            return

        item = self.items[index]
        geo = self._geo
        lift = self._lift_of(index)
        ix, iy, half = self._tile_box(index, lift)
        angle = (2 * math.pi * index / len(self.items)) - math.pi / 2
        accents = themes.tile_accents(self.mode, self.style)
        accent = accents[index % len(accents)]
        canvas.delete(f"item_{index}")
        tags = f"item_{index}"

        if item.action_type in SPLIT_ACTIONS:
            # 亮度 / 对比度：一个磁贴分成 ＋、－ 两个可点区域
            self._draw_split_tile(
                canvas, ix, iy, half, accent, item.icon_text, tags, lift=lift
            )
        else:
            active = None
            if item.action_type == "set_paste_enhanced":
                active = self._paste_enhanced is True
            elif item.action_type == "set_paste_normal":
                active = self._paste_enhanced is False

            if active:
                active_fill = (
                    self._accents["paste_enhanced"]
                    if item.action_type == "set_paste_enhanced"
                    else self._accents["paste_normal"]
                )
                self._draw_tile(
                    canvas,
                    ix,
                    iy,
                    half,
                    accent,
                    item.icon_text,
                    tags=tags,
                    active=True,
                    active_fill=active_fill,
                    lift=lift,
                )
            else:
                self._draw_tile(
                    canvas,
                    ix,
                    iy,
                    half,
                    accent,
                    item.icon_text,
                    tags=tags,
                    lift=lift,
                )

        # Label: a frosted pill matching the tile accent, or — in 冷淡风,
        # where nothing is allowed to be a card — bare text on the wallpaper.
        # 1.14r keeps the pill clear of the tile rim in the compact window.
        label_r = self._radius * 1.14
        lx = self._center_x + label_r * math.cos(angle)
        ly = (
            self._center_y
            + label_r * math.sin(angle)
            - LIFT_RAISE * lift * 0.5
        )

        label_text = item.label
        text_w = len(label_text) * 13 + 26
        text_h = 26
        label_cols = themes.label_colors(self.mode, accent, self.style)

        if geo["label_pill"]:
            _rounded_rect(
                canvas,
                lx - text_w / 2,
                ly - text_h / 2,
                lx + text_w / 2,
                ly + text_h / 2,
                text_h * geo["label_radius"],
                fill=label_cols["body"],
                outline=label_cols["rim"],
                width=1,
                tags=tags,
            )
        canvas.create_text(
            lx,
            ly,
            text=label_text,
            fill=label_cols["text"],
            font=themes.wheel_font(10),
            tags=tags,
        )

    # ------------------------------------------------------------------
    # Hover spring: a lifted tile floats out, a released one bounces back
    # ------------------------------------------------------------------

    def _schedule_anim(self) -> None:
        """Start the frame loop if it is not already running."""
        if self._anim_job is None and self._canvas is not None:
            self._anim_last = None
            self._anim_job = self.after(FRAME_MS, self._tick)

    def _tick(self) -> None:
        """Integrate the per-tile springs and repaint only what moved."""
        self._anim_job = None
        try:
            if not self.winfo_exists() or self._canvas is None:
                return
        except tk.TclError:
            return

        now = time.monotonic()
        if self._anim_last is None:
            dt = FRAME_MS / 1000.0
        else:
            # Clamp: returning from a background tab must not fast-forward the
            # whole animation in one step.
            dt = max(0.001, min(0.05, now - self._anim_last))
        self._anim_last = now

        hovered = self._hovered_key[0]
        moved: list[int] = []
        settling = False
        for index in range(len(self.items)):
            target = 1.0 if index == hovered else 0.0
            current = self._lift.get(index, 0.0)
            velocity = self._lift_velocity.get(index, 0.0)
            if current == target and velocity == 0.0:
                continue
            current, velocity, settling_now = spring_step(
                current, velocity, target, dt
            )
            settling = settling or settling_now
            self._lift[index] = current
            self._lift_velocity[index] = velocity
            moved.append(index)

        for index in moved:
            self._paint_tile(index)
        if moved:
            self._redraw_hover_ring()
        if settling:
            self._anim_job = self.after(FRAME_MS, self._tick)
        else:
            self._anim_last = None

    def _on_motion(self, event: tk.Event) -> None:
        index, sign = self._hit_test(event.x, event.y)
        if (index, sign) != self._hovered_key:
            self._hovered_key = (index, sign)
            # The spring brings the old tile back down and the new one up, so
            # nothing is painted here — _tick owns every redraw.
            self._schedule_anim()

    def _redraw_hover_ring(self) -> None:
        """Repaint the outline for whichever tile is under the pointer."""
        if self._canvas is None:
            return
        self._canvas.delete("hover_ring")
        index, sign = self._hovered_key
        if index >= 0:
            self._draw_hover(index, sign)

    def _draw_hover(self, index: int, sign: int = 0) -> None:
        if self._canvas is None:
            return
        ix, iy, half = self._tile_box(index)
        geo = self._geo
        accents = themes.tile_accents(self.mode, self.style)
        accent = accents[index % len(accents)]
        corner = half * geo["hover_radius"]
        lift = self._lift_of(index)
        # The ring rides the tile outward and opens up a little as it lifts.
        gap = 4.0 + 1.6 * lift

        if geo["hover_halo"]:
            # Lifted styles get a light halo outside the accent outline.
            _rounded_rect(
                self._canvas,
                ix - half - gap - 1.5,
                iy - half - gap - 1.5,
                ix + half + gap + 1.5,
                iy + half + gap + 1.5,
                corner,
                fill="",
                outline=self._pal["ring"],
                width=2,
                tags="hover_ring",
            )
        _rounded_rect(
            self._canvas,
            ix - half - gap,
            iy - half - gap,
            ix + half + gap,
            iy + half + gap,
            max(0.0, corner - half * 0.02),
            fill="",
            outline=accent,
            width=2,
            tags="hover_ring",
        )
        if sign and self.items[index].action_type in SPLIT_ACTIONS:
            # Highlight only the ＋ or － part under the pointer.
            for button_sign, bx, by, bw, bh in self._split_button_boxes(
                ix, iy, half
            ):
                if button_sign != sign:
                    continue
                _rounded_rect(
                    self._canvas,
                    bx - bw / 2 - 2.5,
                    by - bh / 2 - 2.5,
                    bx + bw / 2 + 2.5,
                    by + bh / 2 + 2.5,
                    min(bw, bh) * (geo["sub_radius"] + 0.06),
                    fill="",
                    outline=_mix(accent, self._pal["status_text"], 0.25),
                    width=2,
                    tags="hover_ring",
                )

    def _clear_hover(self) -> None:
        """Drop the hover state; the spring animates the tile back down."""
        if self._hovered_key != (-1, 0):
            self._hovered_key = (-1, 0)
            self._schedule_anim()

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

        index, sign = self._hit_test(event.x, event.y)
        if index < 0 or self.on_item_selected is None:
            return
        # sign < 0 → the 「－」 half; a legacy right-click also decreases.
        self.on_item_selected(self.items[index], bool(right or sign < 0))

    def _hit_test(self, x: float, y: float) -> tuple[int, int]:
        """Return (item index, direction) — direction is +1, -1 or 0 (n/a)."""
        cx, cy = self._center_x, self._center_y
        distance = math.hypot(x - cx, y - cy)

        inner_bound = self._inner_radius * 1.9
        outer_bound = self._radius * 1.18
        if self._radius <= 0 or distance < inner_bound or distance > outer_bound:
            return (-1, 0)

        half = self._radius * 0.20
        # Tiles sit on sector boundaries, so the nearest sector centre is the
        # only candidate; fall back to a full scan keeps edge clicks reliable.
        n = len(self.items)
        angle = math.atan2(y - cy, x - cx) + math.pi / 2
        if angle < 0:
            angle += 2 * math.pi
        sector_angle = 2 * math.pi / n
        candidates = [int(angle / sector_angle + 0.5) % n]
        candidates += [i for i in range(n) if i not in candidates]

        for index in candidates:
            ix, iy = self._item_center(index)
            split = self.items[index].action_type in SPLIT_ACTIONS
            if split:
                for sign, bx, by, bw, bh in self._split_button_boxes(
                    ix, iy, half
                ):
                    if abs(x - bx) <= bw / 2 and abs(y - by) <= bh / 2:
                        return (index, sign)
            if math.hypot(x - ix, y - iy) <= half * 1.4:
                # Only register a hit near the tile body, not the label zone.
                if split:
                    return (index, 1 if x < ix else -1)
                return (index, 0)
        return (-1, 0)
