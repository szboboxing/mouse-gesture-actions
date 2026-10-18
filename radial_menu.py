"""Radial (pie) menu overlay for Mouse Gesture Actions."""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class RadialItem:
    """A single item in the radial menu."""
    label: str
    icon_text: str  # short symbol drawn inside the circle
    action_type: str  # "shortcut" or "open"
    modifiers: tuple[str, ...] = ()  # for shortcut: ("ctrl",) etc.
    key: str = ""  # for shortcut: single char or F-key
    target: str = ""  # for open: file/URL/protocol
    description: str = ""


# Default 8 radial menu items (matching the reference screenshot)
DEFAULT_RADIAL_ITEMS: tuple[RadialItem, ...] = (
    RadialItem(
        label="撤销",
        icon_text="↩",
        action_type="shortcut",
        modifiers=("ctrl",),
        key="Z",
    ),
    RadialItem(
        label="复制",
        icon_text="⧉",
        action_type="shortcut",
        modifiers=("ctrl",),
        key="C",
    ),
    RadialItem(
        label="粘贴",
        icon_text="📋",
        action_type="shortcut",
        modifiers=("ctrl",),
        key="V",
    ),
    RadialItem(
        label="新建表格",
        icon_text="⊞",
        action_type="open",
        target="excel",
        description="启动 Excel 新建表格",
    ),
    RadialItem(
        label="AI PPT",
        icon_text="◆",
        action_type="open",
        target="",
        description="待配置 AI PPT 工具",
    ),
    RadialItem(
        label="新建文字",
        icon_text="📄",
        action_type="open",
        target="winword",
        description="启动 Word 新建文档",
    ),
    RadialItem(
        label="剪切",
        icon_text="✂",
        action_type="shortcut",
        modifiers=("ctrl",),
        key="X",
    ),
    RadialItem(
        label="打印",
        icon_text="⎙",
        action_type="shortcut",
        modifiers=("ctrl",),
        key="P",
    ),
)


COLORS = {
    "overlay": "#000000",
    "bg": "#F5F5F5",
    "icon_bg": "#1A1A1A",
    "icon_fg": "#FFFFFF",
    "label_bg": "#FFFFFF",
    "label_fg": "#333333",
    "label_border": "#E0E0E0",
    "close_bg": "#CCCCCC",
    "close_fg": "#666666",
    "hover": "#4F6EF7",
}


class RadialMenu:
    """Fullscreen radial menu overlay."""

    def __init__(
        self,
        parent: tk.Tk,
        on_item_selected: Callable[[RadialItem], None] | None = None,
        on_close: Callable[[], None] | None = None,
        items: tuple[RadialItem, ...] = DEFAULT_RADIAL_ITEMS,
    ) -> None:
        self.parent = parent
        self.on_item_selected = on_item_selected
        self.on_close = on_close
        self.items = items
        self._window: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._center_x: float = 0
        self._center_y: float = 0
        self._radius: float = 0
        self._inner_radius: float = 0
        self._hovered_index: int = -1
        self._is_active = False

    def show(self) -> None:
        """Display the radial menu overlay."""
        if self._is_active:
            return

        self._window = tk.Toplevel(self.parent)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.attributes("-fullscreen", True)
        self._window.configure(bg=COLORS["overlay"])
        self._window.attributes("-alpha", 0.75)

        # Bind escape and close
        self._window.bind("<Escape>", lambda _e: self._handle_close())

        self._canvas = tk.Canvas(
            self._window,
            bg=COLORS["overlay"],
            highlightthickness=0,
            cursor="sizedown",
        )
        self._canvas.pack(fill="both", expand=True)

        # Wait for window to render so we can get dimensions
        self._window.update_idletasks()
        screen_w = self._canvas.winfo_width()
        screen_h = self._canvas.winfo_height()

        self._center_x = screen_w / 2
        self._center_y = screen_h / 2
        # Radius: fit within 40% of the smaller dimension
        self._radius = min(screen_w, screen_h) * 0.28
        self._inner_radius = self._radius * 0.12

        self._draw_menu()

        # Bind click
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<Leave>", self._on_leave)

        self._is_active = True
        self._window.focus_force()

    def hide(self) -> None:
        """Close the radial menu overlay."""
        self._is_active = False
        if self._window is not None and self._window.winfo_exists():
            self._window.destroy()
        self._window = None
        self._canvas = None

    def _draw_menu(self) -> None:
        """Draw the full radial menu on the canvas."""
        canvas = self._canvas
        if canvas is None:
            return

        canvas.delete("all")

        # Draw a subtle circular guide
        r = self._radius
        cx, cy = self._center_x, self._center_y

        # Draw outer ring (faint)
        canvas.create_oval(
            cx - r * 1.1, cy - r * 1.1,
            cx + r * 1.1, cy + r * 1.1,
            outline="#444444",
            width=1,
        )

        # Draw each item
        n = len(self.items)
        for index, item in enumerate(self.items):
            # Angle: start from top (270°), go clockwise
            angle = (2 * math.pi * index / n) - math.pi / 2
            item_r = r * 0.72
            ix = cx + item_r * math.cos(angle)
            iy = cy + item_r * math.sin(angle)

            # Icon circle
            icon_radius = r * 0.18
            canvas.create_oval(
                ix - icon_radius, iy - icon_radius,
                ix + icon_radius, iy + icon_radius,
                fill=COLORS["icon_bg"],
                outline="",
                tags=f"item_{index}",
            )

            # Icon text
            canvas.create_text(
                ix, iy,
                text=item.icon_text,
                fill=COLORS["icon_fg"],
                font=("Segoe UI Emoji", int(icon_radius * 0.9), "bold"),
                tags=f"item_{index}",
            )

            # Label positioned outside the icon
            label_r = r * 1.05
            lx = cx + label_r * math.cos(angle)
            ly = cy + label_r * math.sin(angle)

            # Label background (rounded rectangle simulation)
            label_text = item.label
            # Calculate text width estimate
            text_w = len(label_text) * 14 + 20
            text_h = 26

            canvas.create_rectangle(
                lx - text_w / 2, ly - text_h / 2,
                lx + text_w / 2, ly + text_h / 2,
                fill=COLORS["label_bg"],
                outline=COLORS["label_border"],
                width=1,
                tags=f"item_{index}",
            )
            canvas.create_text(
                lx, ly,
                text=label_text,
                fill=COLORS["label_fg"],
                font=("Microsoft YaHei UI", 10, "bold"),
                tags=f"item_{index}",
            )

        # Draw center close button
        close_r = self._inner_radius
        canvas.create_oval(
            cx - close_r, cy - close_r,
            cx + close_r, cy + close_r,
            fill=COLORS["close_bg"],
            outline="",
            tags="close_btn",
        )
        canvas.create_text(
            cx, cy,
            text="×",
            fill=COLORS["close_fg"],
            font=("Segoe UI", int(close_r * 1.2), "bold"),
            tags="close_btn",
        )

    def _on_motion(self, event: tk.Event) -> None:
        """Handle mouse motion for hover effects."""
        index = self._hit_test(event.x, event.y)
        if index != self._hovered_index:
            self._clear_hover()
            self._hovered_index = index
            if index >= 0:
                self._draw_hover(index)

    def _draw_hover(self, index: int) -> None:
        """Draw a highlight ring around the hovered item."""
        if self._canvas is None:
            return
        n = len(self.items)
        angle = (2 * math.pi * index / n) - math.pi / 2
        r = self._radius
        cx, cy = self._center_x, self._center_y
        item_r = r * 0.72
        ix = cx + item_r * math.cos(angle)
        iy = cy + item_r * math.sin(angle)
        icon_radius = r * 0.18

        # Draw highlight ring
        self._canvas.create_oval(
            ix - icon_radius - 3, iy - icon_radius - 3,
            ix + icon_radius + 3, iy + icon_radius + 3,
            outline=COLORS["hover"],
            width=3,
            tags="hover_ring",
        )

    def _clear_hover(self) -> None:
        if self._canvas is not None:
            self._canvas.delete("hover_ring")
        self._hovered_index = -1

    def _on_leave(self, _event: tk.Event) -> None:
        self._clear_hover()

    def _on_click(self, event: tk.Event) -> None:
        """Handle click: determine which item was selected."""
        # Check close button first
        cx, cy = self._center_x, self._center_y
        dist_to_center = math.hypot(event.x - cx, event.y - cy)
        if dist_to_center <= self._inner_radius * 1.5:
            self._handle_close()
            return

        index = self._hit_test(event.x, event.y)
        if index >= 0:
            self._handle_item_click(index)

    def _hit_test(self, x: float, y: float) -> int:
        """Determine which radial item the point (x,y) falls in."""
        cx, cy = self._center_x, self._center_y
        dx = x - cx
        dy = y - cy
        distance = math.hypot(dx, dy)

        # Must be within the ring area (not too close to center, not too far)
        inner_bound = self._inner_radius * 1.5
        outer_bound = self._radius * 1.15
        if distance < inner_bound or distance > outer_bound:
            return -1

        # Calculate angle (0 = right, going counter-clockwise)
        angle = math.atan2(dy, dx)
        # Shift so 0 = top, going clockwise
        angle = angle + math.pi / 2
        if angle < 0:
            angle += 2 * math.pi

        n = len(self.items)
        sector_angle = 2 * math.pi / n
        index = int(angle / sector_angle) % n
        return index

    def _handle_item_click(self, index: int) -> None:
        """Execute the selected item's action."""
        item = self.items[index]
        self.hide()
        if self.on_item_selected is not None:
            self.on_item_selected(item)

    def _handle_close(self) -> None:
        """Close the menu without selecting an item."""
        self.hide()
        if self.on_close is not None:
            self.on_close()
