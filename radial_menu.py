"""Radial (pie) menu panel for Mouse Gesture Actions.

Minimal Apple/iOS look: the wheel sits on a glass wallpaper (three styles:
冰霜 / 烟晶 / 彩璃) and every element is painted from a light or dark palette,
switched with the 「明暗」 button in the top bar. Tiles are opaque frosted
cards with a thin accent rim so they stay readable on top of the picture.
The current normal/enhanced paste mode is shown as a coloured badge in the
top status bar and highlighted on the matching wheel tile.
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from typing import Callable

import themes

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
# from ``themes.palette(mode)`` so it can switch to 暗夜 at runtime.
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

# Accent hue per tile in light mode (thin outline colour + glyph tint).
# index order = DEFAULT_RADIAL_ITEMS: 鼠标大小 普通粘贴 增强粘贴 对比度
# AI 工具 亮度 浏览器 计算器. 增强=红, 普通=橙; 亮度/浏览器接手旧绿/靛蓝。
# The wheel itself asks ``themes.tile_accents(mode)`` so 暗夜 can brighten them.
ITEM_ACCENTS: tuple[str, ...] = themes.tile_accents("light")

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
            font=("Microsoft YaHei UI", 9),
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
        self._center_x: float = 0
        self._center_y: float = 0
        self._radius: float = 0
        self._inner_radius: float = 0
        self._cw: int = 0
        self._ch: int = 0
        self._hovered_key: tuple[int, int] = (-1, 0)
        self._status_var: tk.StringVar = tk.StringVar(value="正在初始化")
        self._status_dot_color: str = themes.accent_colors(self.mode)["warning"]
        self._paste_enhanced: bool | None = None
        # Wallpaper PhotoImages are cached per style/mode so switching back is
        # instant and the reference keeps Tk from discarding the picture.
        self._bg_images: dict[str, tk.PhotoImage] = {}
        self._apply_theme_state()

        super().__init__(parent, bg=self._pal["base"])
        self._build_ui()

    # ------------------------------------------------------------------
    # Theme (glass style + light/dark palette)
    # ------------------------------------------------------------------

    def _apply_theme_state(self) -> None:
        self._pal = themes.palette(self.mode)
        self._edges = themes.wallpaper_edges(self.style, self.mode)
        self._accents = themes.accent_colors(self.mode)
        self._accents["gray"] = themes.tile_accents(self.mode)[-1]
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
        if self._canvas is not None:
            self._canvas.delete("all")
        for child in self.winfo_children():
            child.destroy()
        self._hovered_key = (-1, 0)
        self._build_ui()

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

        status_frame = tk.Frame(top_bar, bg=self._edges["top"])
        status_frame.pack(side="left", padx=(20, 0), pady=14)

        self._status_canvas = tk.Canvas(
            status_frame,
            width=16,
            height=16,
            bg=self._edges["top"],
            highlightthickness=0,
        )
        self._status_canvas.pack(side="left", padx=(0, 10))
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
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(side="left")

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
            font=("Microsoft YaHei UI", 11, "bold"),
            padx=18,
            pady=6,
        )
        settings_btn.pack(side="right", padx=(0, 20), pady=12)

        # Paste-mode badge (left of the settings button).
        self._mode_badge = tk.Label(
            top_bar,
            text="",
            bg=self._edges["top"],
            fg=pal["status_muted"],
            font=("Microsoft YaHei UI", 11, "bold"),
            padx=14,
            pady=5,
        )
        self._mode_badge.pack(side="right", padx=(0, 12), pady=13)
        self._update_mode_badge()

        # 「明暗」 toggle, then 「风格」 — packed right-to-left so 风格 ends up
        # furthest from the settings button.
        self._mode_btn = self._pill(
            top_bar,
            f"{'☾' if self.mode == 'dark' else '☀'}  {themes.mode_label(self.mode)}",
            self.toggle_mode,
            tip="切换明亮模式 / 暗夜模式",
        )
        self._mode_btn.pack(side="right", padx=(0, 8), pady=12)

        self._style_btn = self._pill(
            top_bar,
            f"◈ 风格 · {themes.style_label(self.style)}",
            self.cycle_style,
            tip="切换轮盘玻璃壁纸：冰霜 → 烟晶 → 彩璃",
        )
        self._style_btn.pack(side="right", padx=(0, 8), pady=12)

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
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
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
    ) -> None:
        """Frosted card: solid body + thin accent rim + soft drop shadow.

        The body is opaque because Tk canvases cannot alpha-blend, and the
        tile has to stay readable on top of the glass wallpaper. Active tiles
        (current paste mode) get an accent-tinted body + a stronger rim.
        """
        radius = half * 0.44
        if active:
            colors = themes.active_tile_colors(self.mode, active_fill or accent)
            width = 2.4
        else:
            colors = themes.tile_colors(self.mode, accent)
            width = 1.8
        # faint floating shadow
        _rounded_rect(
            canvas,
            ix - half + 2,
            iy - half + 5,
            ix + half - 2,
            iy + half + 6,
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
        canvas.create_line(
            ix - half + radius,
            iy - half + 1.5,
            ix - half * 0.1,
            iy - half + 1.5,
            fill=colors["hilite"],
            width=1,
            tags=tags,
        )
        canvas.create_text(
            ix,
            iy,
            text=glyph,
            fill=glyph_fill or colors["glyph"],
            font=("Segoe UI Symbol", int(half * 0.95), "bold"),
            tags=tags,
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
    ) -> None:
        """Brightness / contrast tile: one body, two clickable parts.

        The function glyph stays on the upper part of the tile, while the lower
        part is divided into a 「＋」button (left) and a 「－」button (right). Both
        parts work with the left mouse button, so decreasing no longer depends
        on a right-click reaching the canvas.
        """
        radius = half * 0.44
        pal = self._pal
        colors = themes.tile_colors(self.mode, accent)
        _rounded_rect(
            canvas,
            ix - half + 2,
            iy - half + 5,
            ix + half - 2,
            iy + half + 6,
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
            width=1.8,
            tags=tags,
        )
        canvas.create_line(
            ix - half + radius,
            iy - half + 1.5,
            ix - half * 0.1,
            iy - half + 1.5,
            fill=colors["hilite"],
            width=1,
            tags=tags,
        )
        canvas.create_text(
            ix,
            iy - half * 0.42,
            text=glyph,
            fill=colors["glyph"],
            font=("Segoe UI Symbol", max(11, int(half * 0.62)), "bold"),
            tags=tags,
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
        for sign, bx, by, bw, bh in self._split_button_boxes(ix, iy, half):
            increase = sign > 0
            _rounded_rect(
                canvas,
                bx - bw / 2,
                by - bh / 2,
                bx + bw / 2,
                by + bh / 2,
                min(bw, bh) * 0.34,
                fill=accent if increase else pal["minus_body"],
                outline=accent if increase else pal["minus_rim"],
                width=1.4,
                tags=tags,
            )
            canvas.create_text(
                bx,
                by,
                text="＋" if increase else "－",
                fill="#FFFFFF" if increase else pal["minus_text"],
                font=("Microsoft YaHei UI", max(10, int(half * 0.56)), "bold"),
                tags=tags,
            )

    def _draw_menu(self) -> None:
        canvas = self._canvas
        if canvas is None:
            return

        canvas.delete("all")

        cx, cy = self._center_x, self._center_y
        r = self._radius
        pal = self._pal
        accents = themes.tile_accents(self.mode)

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

        n = len(self.items)
        icon_radius = r * 0.20
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

        for index, item in enumerate(self.items):
            angle = (2 * math.pi * index / n) - math.pi / 2
            ix, iy = self._item_center(index)

            accent = accents[index % len(accents)]

            if item.action_type in SPLIT_ACTIONS:
                # 亮度 / 对比度：一个磁贴分成 ＋、－ 两个可点区域
                self._draw_split_tile(
                    canvas,
                    ix,
                    iy,
                    icon_radius,
                    accent,
                    item.icon_text,
                    tags=f"item_{index}",
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

            # Label: frosted pill matching the tile accent.
            # 1.14r keeps the pill clear of the tile rim in the compact window.
            label_r = r * 1.14
            lx = cx + label_r * math.cos(angle)
            ly = cy + label_r * math.sin(angle)

            label_text = item.label
            text_w = len(label_text) * 13 + 26
            text_h = 26
            corner = text_h / 2
            label_cols = themes.label_colors(self.mode, accent)

            _rounded_rect(
                canvas,
                lx - text_w / 2,
                ly - text_h / 2,
                lx + text_w / 2,
                ly + text_h / 2,
                corner,
                fill=label_cols["body"],
                outline=label_cols["rim"],
                width=1,
                tags=f"item_{index}",
            )
            canvas.create_text(
                lx,
                ly,
                text=label_text,
                fill=label_cols["text"],
                font=("Microsoft YaHei UI", 10, "bold"),
                tags=f"item_{index}",
            )

        # Central frosted hub (settings)
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
        )
        # 中心 ⚙ 下方的小字：轮盘只放快捷动作，其余都在设置页
        canvas.create_text(
            cx,
            cy + close_r * 1.85,
            text="更多设置",
            fill=pal["hub_text"],
            font=("Microsoft YaHei UI", 8),
            tags="center",
        )

    def _on_motion(self, event: tk.Event) -> None:
        index, sign = self._hit_test(event.x, event.y)
        if (index, sign) != self._hovered_key:
            self._clear_hover()
            self._hovered_key = (index, sign)
            if index >= 0:
                self._draw_hover(index, sign)

    def _draw_hover(self, index: int, sign: int = 0) -> None:
        if self._canvas is None:
            return
        r = self._radius
        ix, iy = self._item_center(index)
        half = r * 0.20
        accents = themes.tile_accents(self.mode)
        accent = accents[index % len(accents)]

        _rounded_rect(
            self._canvas,
            ix - half - 5.5,
            iy - half - 5.5,
            ix + half + 5.5,
            iy + half + 5.5,
            half * 0.52,
            fill="",
            outline=self._pal["ring"],
            width=2,
            tags="hover_ring",
        )
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
                    min(bw, bh) * 0.4,
                    fill="",
                    outline=_mix(accent, self._pal["status_text"], 0.25),
                    width=2,
                    tags="hover_ring",
                )

    def _clear_hover(self) -> None:
        if self._canvas is not None:
            self._canvas.delete("hover_ring")
        self._hovered_key = (-1, 0)

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
