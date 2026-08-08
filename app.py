from __future__ import annotations

import ctypes
import os
import queue
import random
import sys
import threading
import tkinter as tk
from collections import Counter
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Callable

from actions import ActionResult, SystemActions
from mouse_hook import (
    GlobalRightButtonActionHook,
    HeldMouseAction,
    KeyboardMappingAction,
    MouseControl,
    MouseTestEvent,
)
from settings import (
    KEYBOARD_MAPPING_KEYS,
    AppSettings,
    KeyboardMappingSettings,
    load_settings,
)
from version import APP_NAME, VERSION_TAG


def _force_exit_current_process(exit_code: int) -> None:
    kernel32 = ctypes.windll.kernel32
    kernel32.GetCurrentProcess.argtypes = ()
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.TerminateProcess.argtypes = (
        wintypes.HANDLE,
        wintypes.UINT,
    )
    kernel32.TerminateProcess.restype = wintypes.BOOL
    process = kernel32.GetCurrentProcess()
    kernel32.TerminateProcess(process, exit_code)
    os._exit(exit_code)


COLORS = {
    "nav": "#111827",
    "nav_soft": "#1F2937",
    "nav_text": "#F9FAFB",
    "nav_muted": "#9CA3AF",
    "page": "#F4F6FA",
    "card": "#FFFFFF",
    "text": "#172033",
    "muted": "#657087",
    "line": "#E4E8F0",
    "blue": "#4F6EF7",
    "blue_soft": "#EEF1FF",
    "green": "#1FA774",
    "green_soft": "#E8F8F1",
    "orange": "#E58A28",
    "orange_soft": "#FFF4E5",
    "red": "#DF4B5F",
    "red_soft": "#FDECEF",
}

CUSTOM_TOOL_ICONS = ("◇", "◆")
SHUTDOWN_WATCHDOG_SECONDS = 6.0


def _quick_tool_label(icon: str, label: str) -> str:
    return f"{icon}\n{label}"


ENCOURAGEMENTS = (
    "今天也在认真生活，你已经做得很好了。",
    "别急，稳稳地走，每一步都算数。",
    "辛苦了，记得给努力了一天的自己留点温柔。",
    "工作只是生活的一部分，你的价值远不止于此。",
    "允许自己偶尔慢一点，休息也是前进。",
    "你处理过的难题，正在一点点变成你的底气。",
    "今天的你依然值得一句：做得不错。",
    "再忙也要喝口水，你比待办事项更重要。",
    "不必事事满分，完成和成长同样值得肯定。",
    "愿你下班准时，路上有风，回家有灯。",
    "那些看似普通的坚持，正在悄悄积累成果。",
    "先照顾好自己，明天的事情明天再认真。",
)

USAGE_LABELS = (
    ("copy", "复制"),
    ("paste", "增强粘贴"),
    ("screenshot", "截图"),
    ("calculator", "计算器"),
    ("browser", "浏览器"),
    ("media", "媒体播放器"),
    ("brightness", "亮度调节"),
    ("contrast", "对比度调节"),
    ("keyboard_mapping", "键盘映射"),
    ("custom", "自定义功能"),
)

MOUSE_TEST_LABELS = {
    MouseControl.LEFT: "左键",
    MouseControl.RIGHT: "右键",
    MouseControl.MIDDLE: "中键 / 滚轮按下",
    MouseControl.WHEEL_UP: "滚轮向上",
    MouseControl.WHEEL_DOWN: "滚轮向下",
    MouseControl.XBUTTON1: "下一页 / XButton2",
    MouseControl.XBUTTON2: "上一页 / XButton1",
}
SIDE_BUTTON_CONTROLS = (
    MouseControl.XBUTTON1,
    MouseControl.XBUTTON2,
)
SIDE_BUTTON_NAMES = {
    MouseControl.XBUTTON1: "下一页侧键",
    MouseControl.XBUTTON2: "上一页侧键",
}
MOUSE_TEST_DIAGRAM_LABELS = {
    MouseControl.XBUTTON1: "X2\n下一页",
    MouseControl.XBUTTON2: "X1\n上一页",
}
KEYBOARD_MAPPING_MOUSE_LABELS = {
    "xbutton1": "X2 / 下一页侧键",
    "xbutton2": "X1 / 上一页侧键",
}
KEYBOARD_MAPPING_MOUSE_SHORT_LABELS = {
    "xbutton1": "X2",
    "xbutton2": "X1",
}
KEYBOARD_MAPPING_MOUSE_VALUES = {
    label: value for value, label in KEYBOARD_MAPPING_MOUSE_LABELS.items()
}
KEYBOARD_MAPPING_MODIFIER_LABELS = {
    "ctrl": "Ctrl",
    "alt": "Alt",
    "shift": "Shift",
    "win": "Win",
}


def _side_button_config_text(side_buttons: tuple[str, ...]) -> str:
    names = [
        SIDE_BUTTON_NAMES[control]
        for control in SIDE_BUTTON_CONTROLS
        if control.value in side_buttons
    ]
    return f"已保存截图侧键：{'、'.join(names)}"


def _keyboard_shortcut_text(mapping: KeyboardMappingSettings) -> str:
    parts = [
        KEYBOARD_MAPPING_MODIFIER_LABELS[modifier]
        for modifier in mapping.modifiers
    ]
    parts.append(mapping.key)
    return "+".join(parts)


class GestureCard(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        gesture: str,
        title: str,
        subtitle: str,
        action_text: str,
        accent: str,
    ) -> None:
        super().__init__(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=16,
            pady=10,
        )
        self.columnconfigure(1, weight=1)

        icon = tk.Canvas(
            self,
            width=54,
            height=54,
            bg=COLORS["blue_soft"],
            highlightthickness=0,
        )
        icon.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 13))
        self._draw_icon(icon, gesture, accent)

        tk.Label(
            self,
            text=title,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
            anchor="w",
            justify="left",
            wraplength=180,
        ).grid(row=0, column=1, sticky="ew")
        tk.Label(
            self,
            text=subtitle,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            justify="left",
            wraplength=190,
        ).grid(row=1, column=1, sticky="new", pady=(3, 0))

        tk.Label(
            self,
            text="执行动作",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(9, 4))

        tk.Label(
            self,
            text=action_text,
            bg=COLORS["page"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=10,
            pady=5,
            anchor="w",
            justify="left",
            wraplength=270,
        ).grid(row=3, column=0, columnspan=2, sticky="ew")

    @staticmethod
    def _draw_icon(canvas: tk.Canvas, gesture: str, accent: str) -> None:
        canvas.create_rectangle(0, 0, 54, 54, fill=COLORS["blue_soft"], outline="")
        if gesture in {"wheel_up", "wheel_down"}:
            canvas.create_oval(
                13, 7, 41, 48, outline=accent, width=3
            )
            canvas.create_line(27, 8, 27, 25, fill=accent, width=2)
            if gesture == "wheel_up":
                canvas.create_line(
                    27, 12, 20, 20, fill=accent, width=3, arrow="first"
                )
            else:
                canvas.create_line(
                    27, 12, 34, 20, fill=accent, width=3, arrow="last"
                )
        elif gesture == "xbutton1":
            canvas.create_oval(
                16, 7, 42, 48, outline=accent, width=3
            )
            canvas.create_rectangle(
                9, 20, 18, 31, fill=accent, outline=""
            )
            canvas.create_text(
                29,
                28,
                text="X2",
                fill=accent,
                font=("Segoe UI", 9, "bold"),
            )
        else:
            canvas.create_line(
                17, 40, 17, 13, fill=accent, width=4, arrow="last"
            )
            canvas.create_line(
                37, 14, 37, 41, fill=accent, width=4, arrow="last"
            )


class MouseGestureApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.settings = load_settings()
        self.actions = SystemActions()
        self.ui_events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.hook = GlobalRightButtonActionHook(
            self._on_hook_action,
            self._on_mouse_test_event,
        )
        self.hook.set_screenshot_side_buttons(
            self.settings.screenshot_side_buttons
        )
        self.hook.set_keyboard_mappings(
            (
                (mapping.mouse_button, index)
                for index, mapping in enumerate(
                    self.settings.keyboard_mappings
                )
                if mapping.enabled
            )
        )
        self.usage_counts: Counter[str] = Counter()
        self.mouse_test_counts: Counter[MouseControl] = Counter()
        self.detected_side_buttons: set[MouseControl] = set()
        self.listening = False
        self.active_page = "dashboard"
        self.toast: tk.Toplevel | None = None
        self.toast_after_id: str | None = None
        self.pages: dict[str, tk.Frame] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.mouse_test_items: dict[
            MouseControl,
            list[tuple[int, str, str]],
        ] = {}
        self.mouse_test_status_labels: dict[MouseControl, tk.Label] = {}
        self.mouse_test_after_ids: dict[MouseControl, str] = {}
        self.mouse_test_canvas: tk.Canvas | None = None
        self._closing = False
        self._shutdown_watchdog: threading.Timer | None = None

        self.launch_var = tk.BooleanVar(value=self.settings.launch_listening)
        self.minimize_var = tk.BooleanVar(
            value=self.settings.minimize_on_start
        )
        self.status_var = tk.StringVar(value="正在初始化")
        self.left_clicks_var = tk.StringVar(value="0")
        self.right_clicks_var = tk.StringVar(value="0")
        self.distance_var = tk.StringVar(value="0 px")
        self.usage_vars = {
            key: tk.StringVar(value="0") for key, _label in USAGE_LABELS
        }
        self.mouse_test_status_var = tk.StringVar(value="等待操作")
        self.mouse_test_count_vars = {
            control: tk.StringVar(value="0") for control in MouseControl
        }
        self.side_button_config_var = tk.StringVar(
            value=_side_button_config_text(
                self.settings.screenshot_side_buttons
            )
        )
        self.side_button_confirm_var = tk.StringVar(
            value="侧键无反应时，请重新确认并保存检测结果。"
        )
        self.custom_name_vars = (
            tk.StringVar(value=self.settings.custom_button_1_name),
            tk.StringVar(value=self.settings.custom_button_2_name),
        )
        self.custom_quick_label_vars = tuple(
            tk.StringVar(
                value=_quick_tool_label(
                    CUSTOM_TOOL_ICONS[index],
                    name_var.get(),
                )
            )
            for index, name_var in enumerate(self.custom_name_vars)
        )
        self.keyboard_mapping_mouse_vars = tuple(
            tk.StringVar(
                value=KEYBOARD_MAPPING_MOUSE_LABELS[
                    mapping.mouse_button
                ]
            )
            for mapping in self.settings.keyboard_mappings
        )
        self.keyboard_mapping_key_vars = tuple(
            tk.StringVar(value=mapping.key)
            for mapping in self.settings.keyboard_mappings
        )
        self.keyboard_mapping_modifier_vars = tuple(
            {
                modifier: tk.BooleanVar(
                    value=modifier in mapping.modifiers
                )
                for modifier in KEYBOARD_MAPPING_MODIFIER_LABELS
            }
            for mapping in self.settings.keyboard_mappings
        )
        self.keyboard_mapping_enabled_vars = tuple(
            tk.BooleanVar(value=mapping.enabled)
            for mapping in self.settings.keyboard_mappings
        )
        self.keyboard_mapping_preview_vars = tuple(
            tk.StringVar() for _mapping in self.settings.keyboard_mappings
        )
        self.keyboard_mapping_buttons: list[tk.Button] = []
        self.encouragement_var = tk.StringVar()

        self._configure_window()
        self._configure_styles()
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(60, self._poll_ui_events)
        self.root.after(300, self._refresh_metrics)
        self.root.after(150, self._start_hook)

    def _configure_window(self) -> None:
        self.root.title(f"{APP_NAME} {VERSION_TAG}")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(1440, max(1180, screen_width - 80))
        height = min(900, max(700, screen_height - 90))
        width = min(width, screen_width)
        height = min(height, screen_height)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(1120, screen_width), min(680, screen_height))
        self.root.configure(bg=COLORS["page"])
        self.root.option_add("*Font", ("Microsoft YaHei UI", 9))
        icon_path = resource_path("assets/mouse_gesture.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass
        self.root.update_idletasks()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "App.TCombobox",
            fieldbackground=COLORS["card"],
            background=COLORS["card"],
            foreground=COLORS["text"],
            bordercolor=COLORS["line"],
            lightcolor=COLORS["line"],
            darkcolor=COLORS["line"],
            padding=6,
        )
        style.map(
            "App.TCombobox",
            fieldbackground=[("readonly", COLORS["card"])],
            selectbackground=[("readonly", COLORS["card"])],
            selectforeground=[("readonly", COLORS["text"])],
        )
        style.configure(
            "App.TCheckbutton",
            background=COLORS["card"],
            foreground=COLORS["text"],
            font=("Microsoft YaHei UI", 9),
        )
        style.map(
            "App.TCheckbutton",
            background=[("active", COLORS["card"])],
            indicatorcolor=[
                ("selected", COLORS["blue"]),
                ("!selected", COLORS["card"]),
            ],
        )
        style.configure(
            "Mapping.TCheckbutton",
            background=COLORS["page"],
            foreground=COLORS["text"],
            font=("Microsoft YaHei UI", 8),
        )
        style.map(
            "Mapping.TCheckbutton",
            background=[("active", COLORS["page"])],
            indicatorcolor=[
                ("selected", COLORS["blue"]),
                ("!selected", COLORS["page"]),
            ],
        )

    def _build_layout(self) -> None:
        sidebar = tk.Frame(self.root, bg=COLORS["nav"], width=264)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=COLORS["nav"])
        brand.pack(fill="x", padx=22, pady=(28, 24))
        logo = tk.Canvas(
            brand,
            width=46,
            height=46,
            bg=COLORS["blue"],
            highlightthickness=0,
        )
        logo.pack(side="left")
        logo.create_arc(
            9, 9, 37, 37, start=25, extent=290, style="arc",
            outline="#FFFFFF", width=4
        )
        logo.create_polygon(8, 18, 17, 17, 13, 26, fill="#FFFFFF")
        name_box = tk.Frame(brand, bg=COLORS["nav"])
        name_box.pack(side="left", padx=(12, 0))
        tk.Label(
            name_box,
            text=APP_NAME,
            bg=COLORS["nav"],
            fg=COLORS["nav_text"],
            font=("Microsoft YaHei UI", 12, "bold"),
            justify="left",
            wraplength=145,
        ).pack(anchor="w")
        tk.Label(
            name_box,
            text=f"GESTURE  {VERSION_TAG}",
            bg=COLORS["nav"],
            fg=COLORS["nav_muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", pady=(2, 0))

        status_box = tk.Frame(
            sidebar,
            bg=COLORS["nav_soft"],
            padx=15,
            pady=15,
        )
        status_box.pack(fill="x", padx=17, pady=(8, 12))
        self.status_dot = tk.Canvas(
            status_box,
            width=12,
            height=12,
            bg=COLORS["nav_soft"],
            highlightthickness=0,
        )
        self.status_dot.grid(row=0, column=0, padx=(0, 8))
        self.status_dot_id = self.status_dot.create_oval(
            2, 2, 10, 10, fill=COLORS["orange"], outline=""
        )
        tk.Label(
            status_box,
            textvariable=self.status_var,
            bg=COLORS["nav_soft"],
            fg=COLORS["nav_text"],
            font=("Microsoft YaHei UI", 10, "bold"),
        ).grid(row=0, column=1, sticky="w")
        tk.Label(
            status_box,
            text="未触发组合时保留原生右键菜单",
            bg=COLORS["nav_soft"],
            fg=COLORS["nav_muted"],
            font=("Microsoft YaHei UI", 8),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(7, 0))

        self.toggle_button = tk.Button(
            sidebar,
            text="暂停组合监听",
            command=self.toggle_listening,
            bg=COLORS["blue"],
            fg="#FFFFFF",
            activebackground="#405ED9",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=14,
            pady=10,
        )
        self.toggle_button.pack(fill="x", padx=17, pady=(0, 22))

        tk.Label(
            sidebar,
            text="功能模块",
            bg=COLORS["nav"],
            fg=COLORS["nav_muted"],
            font=("Microsoft YaHei UI", 8, "bold"),
        ).pack(anchor="w", padx=22, pady=(0, 8))
        nav_box = tk.Frame(sidebar, bg=COLORS["nav"])
        nav_box.pack(fill="x", padx=17)
        self.nav_buttons["dashboard"] = self._nav_button(
            nav_box,
            "功能首页",
            lambda: self._show_page("dashboard"),
        )
        self.nav_buttons["mouse_test"] = self._nav_button(
            nav_box,
            "鼠标按键测试",
            lambda: self._show_page("mouse_test"),
        )

        help_box = tk.Frame(sidebar, bg=COLORS["nav"])
        help_box.pack(side="bottom", fill="x", padx=22, pady=25)
        tk.Label(
            help_box,
            text="使用方式",
            bg=COLORS["nav"],
            fg=COLORS["nav_text"],
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 9))
        for text in (
            "1  按住鼠标右键",
            "2  滚动滚轮或按任一侧键",
            "3  松开右键退出自定义状态",
        ):
            tk.Label(
                help_box,
                text=text,
                bg=COLORS["nav"],
                fg=COLORS["nav_muted"],
                font=("Microsoft YaHei UI", 9),
            ).pack(anchor="w", pady=3)

        page_container = tk.Frame(self.root, bg=COLORS["page"])
        page_container.pack(side="left", fill="both", expand=True)
        page_container.rowconfigure(0, weight=1)
        page_container.columnconfigure(0, weight=1)

        dashboard_page = tk.Frame(page_container, bg=COLORS["page"])
        mouse_test_page = tk.Frame(page_container, bg=COLORS["page"])
        self.pages = {
            "dashboard": dashboard_page,
            "mouse_test": mouse_test_page,
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self._build_page(dashboard_page)
        self._build_mouse_test_page(mouse_test_page)
        self._show_page("dashboard")

    @staticmethod
    def _nav_button(
        parent: tk.Frame,
        text: str,
        command: Callable[[], None],
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=COLORS["nav"],
            fg=COLORS["nav_text"],
            activebackground=COLORS["nav_soft"],
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            anchor="w",
            padx=14,
            pady=10,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        button.pack(fill="x", pady=2)
        return button

    def _show_page(self, page_name: str) -> None:
        page = self.pages.get(page_name)
        if page is None:
            return

        self.active_page = page_name
        page.tkraise()
        test_mode = page_name == "mouse_test"
        self.hook.set_test_mode(test_mode)
        if not test_mode:
            self._clear_mouse_test_pressed()

        for name, button in self.nav_buttons.items():
            selected = name == page_name
            button.configure(
                bg=COLORS["blue"] if selected else COLORS["nav"],
                activebackground=(
                    "#405ED9" if selected else COLORS["nav_soft"]
                ),
            )
        self._refresh_listening_state()

    def _build_page(self, page: tk.Frame) -> None:
        header = tk.Frame(page, bg=COLORS["page"])
        header.pack(fill="x", padx=22, pady=(12, 8))
        title_box = tk.Frame(header, bg=COLORS["page"])
        title_box.pack(side="left")
        tk.Label(
            title_box,
            text="右键组合控制面板",
            bg=COLORS["page"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="右键保持时执行动作，普通侧键可映射自定义快捷键",
            bg=COLORS["page"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(4, 0))
        tk.Label(
            header,
            text="方案 A · 右键保持",
            bg=COLORS["green_soft"],
            fg=COLORS["green"],
            padx=13,
            pady=7,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="right", anchor="n")

        content = tk.Frame(page, bg=COLORS["page"])
        content.pack(fill="both", expand=True, padx=22)
        content.columnconfigure(0, weight=5, minsize=420)
        content.columnconfigure(1, weight=2, minsize=150)
        content.columnconfigure(2, weight=3, minsize=220)
        content.rowconfigure(0, weight=1)

        cards = tk.Frame(content, bg=COLORS["page"])
        cards.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)
        cards.rowconfigure(0, weight=1)
        cards.rowconfigure(1, weight=1)

        card_specs = (
            (
                "wheel_up",
                "复制",
                "右键按住 + 滚轮向上",
                "复制选中的文本或文件（Ctrl+C）",
                COLORS["blue"],
            ),
            (
                "wheel_down",
                "增强粘贴",
                "右键按住 + 滚轮向下",
                "新建文件夹，进入重命名并粘贴剪贴板内容",
                COLORS["green"],
            ),
            (
                "xbutton1",
                "侧键截图",
                "右键按住 + 已确认侧键",
                "测试页可重新确认；未启动映射时保留前进/后退",
                COLORS["orange"],
            ),
        )
        for index, spec in enumerate(card_specs):
            card = GestureCard(cards, *spec)
            row, column = (0, index) if index < 2 else (1, 0)
            card.grid(
                row=row,
                column=column,
                sticky="nsew",
                columnspan=2 if index == 2 else 1,
                padx=(
                    (0, 0)
                    if index == 2
                    else (0, 7) if column == 0 else (7, 0)
                ),
                pady=(0 if row == 0 else 7, 7 if row == 0 else 0),
            )

        activity = tk.Frame(
            content,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=16,
            pady=15,
        )
        activity.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        activity.rowconfigure(2, weight=1)
        activity.columnconfigure(0, weight=1)
        tk.Label(
            activity,
            text="触发记录",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            activity,
            text="最近的组合动作和执行结果",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
        ).grid(row=1, column=0, sticky="w", pady=(3, 10))
        self.log_text = tk.Text(
            activity,
            bg="#F8F9FC",
            fg=COLORS["text"],
            relief="flat",
            bd=0,
            wrap="word",
            state="disabled",
            width=1,
            height=1,
            padx=11,
            pady=9,
            font=("Microsoft YaHei UI", 8),
            spacing2=2,
            spacing3=7,
        )
        self.log_text.grid(row=2, column=0, sticky="nsew")
        self.log_text.tag_configure("success", foreground=COLORS["green"])
        self.log_text.tag_configure("warning", foreground=COLORS["orange"])
        self.log_text.tag_configure("error", foreground=COLORS["red"])
        self.log_text.tag_configure("muted", foreground=COLORS["muted"])

        statistics = tk.Frame(
            content,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=16,
            pady=15,
        )
        statistics.grid(row=0, column=2, sticky="nsew")
        statistics.columnconfigure(0, weight=1)
        tk.Label(
            statistics,
            text="鼠标统计器",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            statistics,
            text="本次运行的按键、移动距离和功能使用次数",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
            justify="left",
            wraplength=270,
        ).grid(row=1, column=0, sticky="w", pady=(3, 10))

        metric_grid = tk.Frame(statistics, bg=COLORS["card"])
        metric_grid.grid(row=2, column=0, sticky="ew")
        for column in range(3):
            metric_grid.columnconfigure(column, weight=1, uniform="metric")
        for column, (label, variable) in enumerate(
            (
                ("左键", self.left_clicks_var),
                ("右键", self.right_clicks_var),
                ("移动", self.distance_var),
            )
        ):
            box = tk.Frame(
                metric_grid,
                bg=COLORS["page"],
                padx=7,
                pady=7,
            )
            box.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 3, 0 if column == 2 else 3),
            )
            tk.Label(
                box,
                text=label,
                bg=COLORS["page"],
                fg=COLORS["muted"],
                font=("Microsoft YaHei UI", 8),
            ).pack(anchor="w")
            tk.Label(
                box,
                textvariable=variable,
                bg=COLORS["page"],
                fg=COLORS["text"],
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            statistics,
            text="功能使用次数",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 9, "bold"),
        ).grid(row=3, column=0, sticky="w", pady=(12, 5))
        usage_grid = tk.Frame(statistics, bg=COLORS["card"])
        usage_grid.grid(row=4, column=0, sticky="nsew")
        usage_grid.columnconfigure(0, weight=1)
        usage_grid.columnconfigure(1, weight=1)
        for index, (key, label) in enumerate(USAGE_LABELS):
            row, column = divmod(index, 2)
            item = tk.Frame(usage_grid, bg=COLORS["card"])
            item.grid(
                row=row,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 7, 7 if column == 0 else 0),
                pady=2,
            )
            tk.Label(
                item,
                text=label,
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=("Microsoft YaHei UI", 8),
            ).pack(side="left")
            tk.Label(
                item,
                textvariable=self.usage_vars[key],
                bg=COLORS["card"],
                fg=COLORS["blue"],
                font=("Segoe UI", 8, "bold"),
            ).pack(side="right")

        self._build_keyboard_mappings(page)
        self._build_quick_tools(page)

        settings_panel = tk.Frame(
            page,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=18,
            pady=10,
        )
        settings_panel.pack(fill="x", padx=22, pady=(8, 6))
        tk.Label(
            settings_panel,
            text="启动设置",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 18))

        ttk.Checkbutton(
            settings_panel,
            text="启动后自动监听",
            variable=self.launch_var,
            style="App.TCheckbutton",
        ).grid(row=0, column=1, padx=(18, 8))
        ttk.Checkbutton(
            settings_panel,
            text="启动时最小化",
            variable=self.minimize_var,
            style="App.TCheckbutton",
        ).grid(row=0, column=2, padx=(0, 10))

        save_button = tk.Button(
            settings_panel,
            text="保存设置",
            command=self.save_settings,
            bg=COLORS["blue"],
            fg="#FFFFFF",
            activebackground="#405ED9",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=16,
            pady=7,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        save_button.grid(row=0, column=3, sticky="e")
        settings_panel.columnconfigure(3, weight=1)
        self._build_encouragement(page)

    def _build_mouse_test_page(self, page: tk.Frame) -> None:
        header = tk.Frame(page, bg=COLORS["page"])
        header.pack(fill="x", padx=28, pady=(24, 16))
        title_box = tk.Frame(header, bg=COLORS["page"])
        title_box.pack(side="left")
        tk.Label(
            title_box,
            text="鼠标按键测试",
            bg=COLORS["page"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="操作鼠标并观察图示高亮，快速检查每个物理按键",
            bg=COLORS["page"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", pady=(5, 0))
        tk.Label(
            header,
            text="实时检测 · 可确认保存侧键",
            bg=COLORS["green_soft"],
            fg=COLORS["green"],
            padx=14,
            pady=8,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="right", anchor="n")

        content = tk.Frame(page, bg=COLORS["page"])
        content.pack(fill="both", expand=True, padx=28, pady=(0, 18))
        content.columnconfigure(0, weight=3, minsize=540)
        content.columnconfigure(1, weight=2, minsize=330)
        content.rowconfigure(0, weight=1)

        visual_panel = tk.Frame(
            content,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=18,
            pady=16,
        )
        visual_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        tk.Label(
            visual_panel,
            text="鼠标按键图示",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
        ).pack(anchor="w")
        tk.Label(
            visual_panel,
            text="按下时对应区域变为绿色；滚轮方向会短暂闪烁",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(4, 8))

        self.mouse_test_canvas = tk.Canvas(
            visual_panel,
            width=620,
            height=520,
            bg="#F8F9FC",
            highlightthickness=0,
        )
        self.mouse_test_canvas.pack(fill="both", expand=True)
        self._draw_mouse_test_mouse(self.mouse_test_canvas)

        details = tk.Frame(
            content,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=18,
            pady=16,
        )
        details.grid(row=0, column=1, sticky="nsew")
        details.columnconfigure(0, weight=1)
        tk.Label(
            details,
            text="检测结果",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        status_card = tk.Frame(
            details,
            bg=COLORS["blue_soft"],
            padx=13,
            pady=12,
        )
        status_card.grid(row=1, column=0, sticky="ew", pady=(10, 14))
        tk.Label(
            status_card,
            text="最后检测",
            bg=COLORS["blue_soft"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
        ).pack(anchor="w")
        tk.Label(
            status_card,
            textvariable=self.mouse_test_status_var,
            bg=COLORS["blue_soft"],
            fg=COLORS["blue"],
            font=("Microsoft YaHei UI", 12, "bold"),
            wraplength=270,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        list_box = tk.Frame(details, bg=COLORS["card"])
        list_box.grid(row=2, column=0, sticky="nsew")
        details.rowconfigure(2, weight=1)
        for control in MouseControl:
            item = tk.Frame(
                list_box,
                bg=COLORS["page"],
                padx=10,
                pady=8,
            )
            item.pack(fill="x", pady=3)
            indicator = tk.Label(
                item,
                text="●",
                bg=COLORS["page"],
                fg=COLORS["line"],
                font=("Segoe UI", 9, "bold"),
            )
            indicator.pack(side="left")
            self.mouse_test_status_labels[control] = indicator
            tk.Label(
                item,
                text=MOUSE_TEST_LABELS[control],
                bg=COLORS["page"],
                fg=COLORS["text"],
                font=("Microsoft YaHei UI", 9),
            ).pack(side="left", padx=(8, 0))
            tk.Label(
                item,
                textvariable=self.mouse_test_count_vars[control],
                bg=COLORS["page"],
                fg=COLORS["blue"],
                font=("Segoe UI", 10, "bold"),
            ).pack(side="right")

        side_config = tk.Frame(
            details,
            bg=COLORS["orange_soft"],
            padx=12,
            pady=10,
        )
        side_config.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        tk.Label(
            side_config,
            text="侧键截图确认",
            bg=COLORS["orange_soft"],
            fg=COLORS["orange"],
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            side_config,
            textvariable=self.side_button_config_var,
            bg=COLORS["orange_soft"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 8, "bold"),
            justify="left",
            wraplength=270,
        ).pack(anchor="w", pady=(4, 0))
        tk.Label(
            side_config,
            textvariable=self.side_button_confirm_var,
            bg=COLORS["orange_soft"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
            justify="left",
            wraplength=270,
        ).pack(anchor="w", pady=(3, 7))
        side_buttons = tk.Frame(side_config, bg=COLORS["orange_soft"])
        side_buttons.pack(fill="x")
        tk.Button(
            side_buttons,
            text="重新确认侧键",
            command=self._begin_side_button_reconfirmation,
            bg=COLORS["card"],
            fg=COLORS["orange"],
            activebackground=COLORS["page"],
            activeforeground=COLORS["orange"],
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=8,
            pady=6,
            font=("Microsoft YaHei UI", 8, "bold"),
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(
            side_buttons,
            text="保存检测结果",
            command=self._save_detected_side_buttons,
            bg=COLORS["green"],
            fg="#FFFFFF",
            activebackground="#17875F",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=8,
            pady=6,
            font=("Microsoft YaHei UI", 8, "bold"),
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        tk.Button(
            details,
            text="清空测试记录",
            command=self._reset_mouse_test,
            bg=COLORS["blue"],
            fg="#FFFFFF",
            activebackground="#405ED9",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=9,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).grid(row=4, column=0, sticky="ew", pady=(10, 0))

    def _draw_mouse_test_mouse(self, canvas: tk.Canvas) -> None:
        self.mouse_test_items.clear()
        canvas.create_oval(
            155,
            24,
            465,
            505,
            fill="#E9EDF5",
            outline="#B9C2D1",
            width=3,
        )
        canvas.create_line(
            310,
            42,
            310,
            220,
            fill="#B9C2D1",
            width=2,
        )

        left = canvas.create_polygon(
            181,
            91,
            214,
            57,
            302,
            39,
            302,
            216,
            173,
            205,
            fill="#FFFFFF",
            outline="#CCD3DF",
            width=2,
        )
        left_text = canvas.create_text(
            239,
            137,
            text="左键",
            fill=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
        )
        self._register_mouse_test_visual(
            MouseControl.LEFT,
            left,
            "#FFFFFF",
            COLORS["green"],
        )
        self._register_mouse_test_visual(
            MouseControl.LEFT,
            left_text,
            COLORS["text"],
            "#FFFFFF",
        )

        right = canvas.create_polygon(
            318,
            39,
            406,
            57,
            439,
            91,
            447,
            205,
            318,
            216,
            fill="#FFFFFF",
            outline="#CCD3DF",
            width=2,
        )
        right_text = canvas.create_text(
            381,
            137,
            text="右键",
            fill=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
        )
        self._register_mouse_test_visual(
            MouseControl.RIGHT,
            right,
            "#FFFFFF",
            COLORS["green"],
        )
        self._register_mouse_test_visual(
            MouseControl.RIGHT,
            right_text,
            COLORS["text"],
            "#FFFFFF",
        )

        wheel = canvas.create_rectangle(
            282,
            72,
            338,
            194,
            fill="#CBD3E1",
            outline="#9CA8BA",
            width=2,
        )
        self._register_mouse_test_visual(
            MouseControl.MIDDLE,
            wheel,
            "#CBD3E1",
            COLORS["green"],
        )
        wheel_label = canvas.create_text(
            310,
            133,
            text="按下",
            angle=90,
            fill=COLORS["muted"],
            font=("Microsoft YaHei UI", 8, "bold"),
        )
        self._register_mouse_test_visual(
            MouseControl.MIDDLE,
            wheel_label,
            COLORS["muted"],
            "#FFFFFF",
        )

        for control, y, text in (
            (MouseControl.WHEEL_UP, 88, "▲"),
            (MouseControl.WHEEL_DOWN, 178, "▼"),
        ):
            arrow = canvas.create_text(
                310,
                y,
                text=text,
                fill=COLORS["muted"],
                font=("Segoe UI", 13, "bold"),
            )
            self._register_mouse_test_visual(
                control,
                arrow,
                COLORS["muted"],
                COLORS["orange"],
            )

        for control, top in (
            (MouseControl.XBUTTON2, 246),
            (MouseControl.XBUTTON1, 320),
        ):
            button = canvas.create_rectangle(
                127,
                top,
                183,
                top + 55,
                fill=COLORS["blue_soft"],
                outline=COLORS["blue"],
                width=2,
            )
            text = canvas.create_text(
                155,
                top + 27,
                text=MOUSE_TEST_DIAGRAM_LABELS[control],
                fill=COLORS["blue"],
                font=("Microsoft YaHei UI", 8, "bold"),
            )
            self._register_mouse_test_visual(
                control,
                button,
                COLORS["blue_soft"],
                COLORS["green"],
            )
            self._register_mouse_test_visual(
                control,
                text,
                COLORS["blue"],
                "#FFFFFF",
            )

        canvas.create_text(
            310,
            455,
            text="移动鼠标不会影响测试计数",
            fill=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
        )

    def _register_mouse_test_visual(
        self,
        control: MouseControl,
        item_id: int,
        idle_color: str,
        active_color: str,
    ) -> None:
        self.mouse_test_items.setdefault(control, []).append(
            (item_id, idle_color, active_color)
        )

    def _build_keyboard_mappings(self, page: tk.Frame) -> None:
        panel = tk.Frame(
            page,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=12,
            pady=6,
        )
        panel.pack(fill="x", padx=22, pady=(6, 0))

        heading = tk.Frame(panel, bg=COLORS["card"])
        heading.pack(fill="x")
        tk.Label(
            heading,
            text="自定义键盘映射键",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side="left")
        tk.Label(
            heading,
            text="普通侧键执行映射；右键保持截图和测试页优先",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
        ).pack(side="right")

        mappings = tk.Frame(panel, bg=COLORS["card"])
        mappings.pack(fill="x", pady=(4, 0))
        for column in range(2):
            mappings.columnconfigure(column, weight=1, uniform="mapping")

        for index in range(2):
            card = tk.Frame(
                mappings,
                bg=COLORS["page"],
                highlightbackground=COLORS["line"],
                highlightthickness=1,
                padx=10,
                pady=4,
            )
            card.grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, 5) if index == 0 else (5, 0),
            )

            summary = tk.Frame(card, bg=COLORS["page"])
            summary.pack(fill="x", pady=(0, 3))
            tk.Label(
                summary,
                text=f"映射 {index + 1}",
                bg=COLORS["page"],
                fg=COLORS["text"],
                font=("Microsoft YaHei UI", 9, "bold"),
            ).pack(side="left")
            tk.Label(
                summary,
                textvariable=self.keyboard_mapping_preview_vars[index],
                bg=COLORS["page"],
                fg=COLORS["muted"],
                font=("Microsoft YaHei UI", 8),
            ).pack(side="right")

            controls = tk.Frame(card, bg=COLORS["page"])
            controls.pack(fill="x")
            mouse_box = ttk.Combobox(
                controls,
                textvariable=self.keyboard_mapping_mouse_vars[index],
                values=tuple(KEYBOARD_MAPPING_MOUSE_VALUES),
                state="readonly",
                width=16,
                style="App.TCombobox",
            )
            mouse_box.pack(side="left", padx=(0, 7))
            mouse_box.bind(
                "<<ComboboxSelected>>",
                lambda _event, target=index: (
                    self._on_keyboard_mapping_changed(target)
                ),
            )

            for modifier, label in KEYBOARD_MAPPING_MODIFIER_LABELS.items():
                ttk.Checkbutton(
                    controls,
                    text=label,
                    variable=self.keyboard_mapping_modifier_vars[index][
                        modifier
                    ],
                    command=lambda target=index: (
                        self._on_keyboard_mapping_changed(target)
                    ),
                    style="Mapping.TCheckbutton",
                ).pack(side="left", padx=(0, 3))

            key_box = ttk.Combobox(
                controls,
                textvariable=self.keyboard_mapping_key_vars[index],
                values=KEYBOARD_MAPPING_KEYS,
                state="readonly",
                width=3,
                style="App.TCombobox",
            )
            key_box.pack(side="left", padx=(4, 7))
            key_box.bind(
                "<<ComboboxSelected>>",
                lambda _event, target=index: (
                    self._on_keyboard_mapping_changed(target)
                ),
            )

            button = tk.Button(
                controls,
                text="启动",
                command=lambda target=index: (
                    self._toggle_keyboard_mapping(target)
                ),
                bg=COLORS["blue"],
                fg="#FFFFFF",
                activebackground="#405ED9",
                activeforeground="#FFFFFF",
                relief="flat",
                bd=0,
                cursor="hand2",
                padx=13,
                pady=3,
                font=("Microsoft YaHei UI", 8, "bold"),
            )
            button.pack(side="right")
            self.keyboard_mapping_buttons.append(button)
            self._refresh_keyboard_mapping_ui(index)

    def _build_quick_tools(self, page: tk.Frame) -> None:
        panel = tk.Frame(
            page,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=12,
            pady=9,
        )
        panel.pack(fill="x", padx=22, pady=(6, 0))
        tk.Label(
            panel,
            text="快捷工具",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            panel,
            text="自定义按钮可右键编辑名称及打开目标",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
        ).place(relx=1.0, x=-1, y=2, anchor="ne")

        buttons = tk.Frame(panel, bg=COLORS["card"])
        buttons.pack(fill="x", pady=(7, 0))
        for column in range(8):
            buttons.columnconfigure(column, weight=1, uniform="quick")

        self._quick_button(
            buttons,
            0,
            "计算器",
            lambda: self._run_quick_action(
                "calculator", self.actions.open_calculator
            ),
            COLORS["blue"],
            icon="▦",
            hover_color=COLORS["blue_soft"],
        )
        self._quick_button(
            buttons,
            1,
            "浏览器",
            lambda: self._run_quick_action(
                "browser", self.actions.open_browser
            ),
            COLORS["green"],
            icon="◎",
            hover_color=COLORS["green_soft"],
        )
        self._quick_button(
            buttons,
            2,
            "媒体播放器",
            lambda: self._run_quick_action(
                "media", self.actions.open_media_player
            ),
            COLORS["orange"],
            icon="▶",
            hover_color=COLORS["orange_soft"],
        )
        self._adjustment_group(
            buttons,
            3,
            "屏幕亮度",
            lambda: self._run_display_adjustment("brightness", -1),
            lambda: self._run_display_adjustment("brightness", 1),
            "☀",
            COLORS["orange"],
            COLORS["orange_soft"],
        )
        self._adjustment_group(
            buttons,
            4,
            "屏幕对比度",
            lambda: self._run_display_adjustment("contrast", -1),
            lambda: self._run_display_adjustment("contrast", 1),
            "◐",
            COLORS["blue"],
            COLORS["blue_soft"],
        )
        self._quick_button(
            buttons,
            5,
            "统计清零",
            self._reset_statistics,
            COLORS["red"],
            icon="↻",
            hover_color=COLORS["red_soft"],
        )
        for offset in range(2):
            button = self._quick_button(
                buttons,
                6 + offset,
                "",
                lambda index=offset: self._run_custom_action(index),
                COLORS["blue"],
                textvariable=self.custom_quick_label_vars[offset],
                hover_color=COLORS["blue_soft"],
            )
            button.bind(
                "<Button-3>",
                lambda _event, index=offset: self._edit_custom_button(index),
            )

    @staticmethod
    def _quick_button(
        parent: tk.Frame,
        column: int,
        text: str,
        command: Callable[[], None],
        accent: str,
        textvariable: tk.StringVar | None = None,
        *,
        icon: str = "",
        hover_color: str = COLORS["blue_soft"],
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=_quick_tool_label(icon, text) if icon else text,
            textvariable=textvariable,
            command=command,
            bg=COLORS["page"],
            fg=COLORS["text"],
            activebackground=COLORS["blue_soft"],
            activeforeground=accent,
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "bold"),
            wraplength=95,
            justify="center",
            padx=5,
            pady=7,
        )
        MouseGestureApp._bind_button_hover(
            button,
            base_background=COLORS["page"],
            base_foreground=COLORS["text"],
            hover_background=hover_color,
            hover_foreground=accent,
        )
        button.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 3, 0 if column == 7 else 3),
        )
        return button

    @staticmethod
    def _bind_button_hover(
        button: tk.Button,
        *,
        base_background: str,
        base_foreground: str,
        hover_background: str,
        hover_foreground: str,
    ) -> None:
        def apply_hover(_event: tk.Event[tk.Misc]) -> None:
            if button.cget("state") != "disabled":
                button.configure(
                    bg=hover_background,
                    fg=hover_foreground,
                    highlightbackground=hover_foreground,
                )

        def clear_hover(_event: tk.Event[tk.Misc]) -> None:
            button.configure(
                bg=base_background,
                fg=base_foreground,
                highlightbackground=COLORS["line"],
            )

        button.bind("<Enter>", apply_hover, add="+")
        button.bind("<Leave>", clear_hover, add="+")

    @staticmethod
    def _adjustment_group(
        parent: tk.Frame,
        column: int,
        title: str,
        decrease: Callable[[], None],
        increase: Callable[[], None],
        icon: str,
        accent: str,
        hover_color: str,
    ) -> None:
        group = tk.Frame(
            parent,
            bg=COLORS["page"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=5,
            pady=4,
        )
        group.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(3, 3),
        )
        tk.Label(
            group,
            text=f"{icon}  {title}",
            bg=COLORS["page"],
            fg=accent,
            font=("Microsoft YaHei UI", 8, "bold"),
        ).pack()
        controls = tk.Frame(group, bg=COLORS["page"])
        controls.pack(pady=(3, 0))
        for text, command in (("－", decrease), ("＋", increase)):
            button = tk.Button(
                controls,
                text=text,
                command=command,
                bg=COLORS["card"],
                fg=accent,
                activebackground=hover_color,
                activeforeground=accent,
                highlightbackground=COLORS["line"],
                highlightthickness=1,
                relief="flat",
                bd=0,
                cursor="hand2",
                font=("Segoe UI", 8, "bold"),
                width=3,
                pady=1,
            )
            MouseGestureApp._bind_button_hover(
                button,
                base_background=COLORS["card"],
                base_foreground=accent,
                hover_background=hover_color,
                hover_foreground=accent,
            )
            button.pack(side="left", padx=2)

    def _build_encouragement(self, page: tk.Frame) -> None:
        self._new_encouragement()
        bar = tk.Frame(
            page,
            bg=COLORS["green_soft"],
            padx=13,
            pady=7,
        )
        bar.pack(fill="x", padx=22, pady=(0, 14))
        tk.Label(
            bar,
            text="今日鼓励",
            bg=COLORS["green_soft"],
            fg=COLORS["green"],
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="left")
        tk.Label(
            bar,
            textvariable=self.encouragement_var,
            bg=COLORS["green_soft"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 9),
            justify="left",
            wraplength=760,
        ).pack(side="left", padx=(14, 8))
        tk.Button(
            bar,
            text="换一句",
            command=self._new_encouragement,
            bg=COLORS["green_soft"],
            fg=COLORS["green"],
            activebackground=COLORS["card"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 8, "bold"),
        ).pack(side="right")

    def _start_hook(self) -> None:
        if not self.hook.start():
            self.status_var.set("监听启动失败")
            self._set_status_dot(COLORS["red"])
            self.toggle_button.configure(text="重试启动监听")
            messagebox.showerror(
                "启动失败",
                self.hook.start_error or "无法安装全局鼠标监听。",
            )
            return

        mapping_enabled = any(
            mapping.enabled for mapping in self.settings.keyboard_mappings
        )
        self.listening = bool(
            self.settings.launch_listening or mapping_enabled
        )
        self.hook.set_enabled(self.listening)
        self._refresh_listening_state()
        self._append_log(
            "程序已就绪；右键保持时识别滚轮和截图侧键，"
            "已启动的普通侧键映射优先于浏览器前进/后退",
            "muted",
        )
        if self.settings.minimize_on_start:
            self.root.after(250, self.root.iconify)

    def toggle_listening(self) -> None:
        if self.hook.start_error:
            self._start_hook()
            return
        self.listening = not self.listening
        self.hook.set_enabled(self.listening)
        self._refresh_listening_state()
        state = "组合监听已启动" if self.listening else "组合监听已暂停"
        self._append_log(state, "success" if self.listening else "warning")

    def _refresh_listening_state(self) -> None:
        if self.active_page == "mouse_test":
            self.status_var.set("按键测试中")
            self._set_status_dot(COLORS["blue"])
            self.toggle_button.configure(
                text="测试期间暂停组合",
                bg=COLORS["nav_soft"],
                activebackground=COLORS["nav_soft"],
                state="disabled",
                disabledforeground="#FFFFFF",
            )
            return

        self.toggle_button.configure(state="normal")
        if self.listening:
            self.status_var.set("正在监听")
            self._set_status_dot(COLORS["green"])
            self.toggle_button.configure(
                text="暂停组合监听",
                bg=COLORS["blue"],
                activebackground="#405ED9",
            )
        else:
            self.status_var.set("监听已暂停")
            self._set_status_dot(COLORS["orange"])
            self.toggle_button.configure(
                text="开始组合监听",
                bg=COLORS["orange"],
                activebackground="#C9761E",
            )

    def _set_status_dot(self, color: str) -> None:
        self.status_dot.itemconfigure(self.status_dot_id, fill=color)

    def _refresh_metrics(self) -> None:
        metrics = self.hook.snapshot_metrics()
        self.left_clicks_var.set(f"{metrics.left_clicks:,}")
        self.right_clicks_var.set(f"{metrics.right_clicks:,}")
        self.distance_var.set(self._format_distance(metrics.distance_pixels))
        for key, variable in self.usage_vars.items():
            variable.set(f"{self.usage_counts[key]:,}")
        self.root.after(300, self._refresh_metrics)

    @staticmethod
    def _format_distance(distance_pixels: float) -> str:
        if distance_pixels >= 10_000:
            return f"{distance_pixels / 10_000:.1f}万 px"
        return f"{round(distance_pixels):,} px"

    def _record_usage(self, key: str) -> None:
        self.usage_counts[key] += 1
        self.usage_vars[key].set(f"{self.usage_counts[key]:,}")

    def _reset_statistics(self) -> None:
        self.hook.reset_metrics()
        self.usage_counts.clear()
        self.left_clicks_var.set("0")
        self.right_clicks_var.set("0")
        self.distance_var.set("0 px")
        for variable in self.usage_vars.values():
            variable.set("0")
        self._append_log("本次运行统计已清零", "muted")
        self._show_toast("统计已清零", COLORS["blue"])

    def _run_quick_action(
        self,
        usage_key: str,
        action: Callable[[], ActionResult],
    ) -> None:
        try:
            result = action()
        except Exception as exc:
            result = ActionResult(False, "快捷功能执行失败", str(exc))
        self._display_quick_result(usage_key, result)

    def _run_display_adjustment(self, control: str, direction: int) -> None:
        action = (
            self.actions.adjust_brightness
            if control == "brightness"
            else self.actions.adjust_contrast
        )
        self._run_quick_action(control, lambda: action(direction))

    def _run_custom_action(self, index: int) -> None:
        name = self.custom_name_vars[index].get().strip()
        target = (
            self.settings.custom_button_1_target
            if index == 0
            else self.settings.custom_button_2_target
        )
        if not target:
            self._edit_custom_button(index)
            return
        self._run_quick_action(
            "custom",
            lambda: self.actions.open_custom_target(target, name),
        )

    def _edit_custom_button(self, index: int) -> None:
        current_name = self.custom_name_vars[index].get()
        current_target = (
            self.settings.custom_button_1_target
            if index == 0
            else self.settings.custom_button_2_target
        )
        name = simpledialog.askstring(
            "编辑自定义按钮",
            "按钮名称（最多 12 个字符）：",
            initialvalue=current_name,
            parent=self.root,
        )
        if name is None:
            return
        name = name.strip()[:12] or f"自定义 {index + 1}"
        target = simpledialog.askstring(
            "编辑自定义按钮",
            "要打开的程序、文件、文件夹或网址：",
            initialvalue=current_target,
            parent=self.root,
        )
        if target is None:
            return
        target = target.strip()

        if index == 0:
            self.settings.custom_button_1_name = name
            self.settings.custom_button_1_target = target
        else:
            self.settings.custom_button_2_name = name
            self.settings.custom_button_2_target = target
        try:
            self.settings.save()
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc))
            return
        self.custom_name_vars[index].set(name)
        self.custom_quick_label_vars[index].set(
            _quick_tool_label(CUSTOM_TOOL_ICONS[index], name)
        )
        self._append_log(f"已更新自定义按钮：{name}", "success")
        self._show_toast("自定义按钮已保存", COLORS["green"])

    def _display_quick_result(
        self,
        usage_key: str,
        result: ActionResult,
    ) -> None:
        event_type = "success" if result.success else "error"
        text = result.message
        if result.detail:
            text += f"\n{result.detail}"
        if result.success:
            self._record_usage(usage_key)
        self._append_log(text, event_type)
        self._show_toast(
            result.message,
            COLORS["green"] if result.success else COLORS["red"],
        )

    def _new_encouragement(self) -> None:
        current = self.encouragement_var.get()
        choices = [
            sentence for sentence in ENCOURAGEMENTS if sentence != current
        ]
        self.encouragement_var.set(random.choice(choices or ENCOURAGEMENTS))

    def _collect_keyboard_mappings(
        self,
    ) -> tuple[KeyboardMappingSettings, ...]:
        mappings: list[KeyboardMappingSettings] = []
        for index, current in enumerate(self.settings.keyboard_mappings):
            mouse_button = KEYBOARD_MAPPING_MOUSE_VALUES.get(
                self.keyboard_mapping_mouse_vars[index].get(),
                current.mouse_button,
            )
            modifiers = tuple(
                modifier
                for modifier in KEYBOARD_MAPPING_MODIFIER_LABELS
                if self.keyboard_mapping_modifier_vars[index][
                    modifier
                ].get()
            )
            key = self.keyboard_mapping_key_vars[index].get().upper()
            if key not in KEYBOARD_MAPPING_KEYS:
                key = current.key
            mappings.append(
                KeyboardMappingSettings(
                    mouse_button=mouse_button,
                    modifiers=modifiers,
                    key=key,
                    enabled=self.keyboard_mapping_enabled_vars[
                        index
                    ].get(),
                )
            )
        return tuple(mappings)

    def _sync_keyboard_mapping_vars(
        self,
        mappings: tuple[KeyboardMappingSettings, ...],
    ) -> None:
        for index, mapping in enumerate(mappings):
            self.keyboard_mapping_mouse_vars[index].set(
                KEYBOARD_MAPPING_MOUSE_LABELS[mapping.mouse_button]
            )
            self.keyboard_mapping_key_vars[index].set(mapping.key)
            for modifier, variable in (
                self.keyboard_mapping_modifier_vars[index].items()
            ):
                variable.set(modifier in mapping.modifiers)
            self.keyboard_mapping_enabled_vars[index].set(
                mapping.enabled
            )
            self._refresh_keyboard_mapping_ui(index)

    def _apply_keyboard_mappings_to_hook(self) -> None:
        self.hook.set_keyboard_mappings(
            (
                (mapping.mouse_button, index)
                for index, mapping in enumerate(
                    self.settings.keyboard_mappings
                )
                if mapping.enabled
            )
        )

    def _persist_keyboard_mappings(
        self,
        mappings: tuple[KeyboardMappingSettings, ...],
    ) -> bool:
        previous = self.settings.keyboard_mappings
        self.settings.keyboard_mappings = mappings
        try:
            self.settings.save()
        except OSError as exc:
            self.settings.keyboard_mappings = previous
            self._sync_keyboard_mapping_vars(previous)
            messagebox.showerror(
                "保存失败",
                str(exc),
                parent=self.root,
            )
            return False

        self._apply_keyboard_mappings_to_hook()
        for index in range(len(mappings)):
            self._refresh_keyboard_mapping_ui(index)
        return True

    def _disable_conflicting_keyboard_mapping(
        self,
        active_index: int,
    ) -> int | None:
        if not self.keyboard_mapping_enabled_vars[active_index].get():
            return None
        active_mouse = KEYBOARD_MAPPING_MOUSE_VALUES.get(
            self.keyboard_mapping_mouse_vars[active_index].get()
        )
        for index, enabled_var in enumerate(
            self.keyboard_mapping_enabled_vars
        ):
            if index == active_index or not enabled_var.get():
                continue
            mouse_button = KEYBOARD_MAPPING_MOUSE_VALUES.get(
                self.keyboard_mapping_mouse_vars[index].get()
            )
            if mouse_button == active_mouse:
                enabled_var.set(False)
                return index
        return None

    def _refresh_keyboard_mapping_ui(self, index: int) -> None:
        mapping = self._collect_keyboard_mappings()[index]
        mouse_name = KEYBOARD_MAPPING_MOUSE_SHORT_LABELS[
            mapping.mouse_button
        ]
        state_text = "已启动" if mapping.enabled else "未启动"
        self.keyboard_mapping_preview_vars[index].set(
            f"{mouse_name} → {_keyboard_shortcut_text(mapping)} · "
            f"{state_text}"
        )
        if index >= len(self.keyboard_mapping_buttons):
            return
        self.keyboard_mapping_buttons[index].configure(
            text="停用" if mapping.enabled else "启动",
            bg=COLORS["green"] if mapping.enabled else COLORS["blue"],
            activebackground=(
                "#18865E" if mapping.enabled else "#405ED9"
            ),
        )

    def _on_keyboard_mapping_changed(self, index: int) -> None:
        conflict = self._disable_conflicting_keyboard_mapping(index)
        mappings = self._collect_keyboard_mappings()
        if not self._persist_keyboard_mappings(mappings):
            return
        if conflict is not None:
            self._append_log(
                f"映射 {conflict + 1} 已停用："
                "同一侧键只能启动一组映射",
                "warning",
            )

    def _toggle_keyboard_mapping(self, index: int) -> None:
        enabled_var = self.keyboard_mapping_enabled_vars[index]
        enabling = not enabled_var.get()
        if enabling and not self.hook.start():
            messagebox.showerror(
                "启动失败",
                self.hook.start_error or "无法安装全局鼠标监听。",
                parent=self.root,
            )
            return

        enabled_var.set(enabling)
        conflict = self._disable_conflicting_keyboard_mapping(index)
        mappings = self._collect_keyboard_mappings()
        if not self._persist_keyboard_mappings(mappings):
            return

        mapping = mappings[index]
        if enabling:
            self.listening = True
            self.hook.set_enabled(True)
            self._refresh_listening_state()
        if conflict is not None:
            self._append_log(
                f"映射 {conflict + 1} 已停用："
                "同一侧键只能启动一组映射",
                "warning",
            )

        shortcut = _keyboard_shortcut_text(mapping)
        mouse_name = KEYBOARD_MAPPING_MOUSE_LABELS[
            mapping.mouse_button
        ]
        state_text = "已启动" if enabling else "已停用"
        self._append_log(
            f"映射 {index + 1} {state_text}："
            f"{mouse_name} → {shortcut}",
            "success" if enabling else "warning",
        )
        self._show_toast(
            f"键盘映射{state_text}",
            COLORS["green"] if enabling else COLORS["orange"],
        )

    def save_settings(self) -> None:
        self.settings = AppSettings(
            launch_listening=self.launch_var.get(),
            minimize_on_start=self.minimize_var.get(),
            screenshot_side_buttons=self.settings.screenshot_side_buttons,
            custom_button_1_name=self.settings.custom_button_1_name,
            custom_button_1_target=self.settings.custom_button_1_target,
            custom_button_2_name=self.settings.custom_button_2_name,
            custom_button_2_target=self.settings.custom_button_2_target,
            keyboard_mappings=self._collect_keyboard_mappings(),
        )
        try:
            self.settings.save()
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc))
            return

        self._apply_keyboard_mappings_to_hook()
        self._append_log("设置已保存并立即生效", "success")
        self._show_toast("设置已保存", COLORS["green"])

    def _on_hook_action(
        self,
        action: HeldMouseAction | KeyboardMappingAction,
    ) -> None:
        if isinstance(action, KeyboardMappingAction):
            self._on_keyboard_mapping_action(action)
            return
        self._on_held_action(action)

    def _on_held_action(self, action: HeldMouseAction) -> None:
        action_result = self._execute_held_action(action)
        event_type = "success" if action_result.success else "error"
        self.ui_events.put(
            ("held_action", (action, action_result, event_type))
        )

    def _on_keyboard_mapping_action(
        self,
        action: KeyboardMappingAction,
    ) -> None:
        try:
            mapping = self.settings.keyboard_mappings[
                action.mapping_index
            ]
        except IndexError:
            return
        if not mapping.enabled:
            return
        action_result = self.actions.send_custom_shortcut(
            mapping.modifiers,
            mapping.key,
        )
        event_type = "success" if action_result.success else "error"
        self.ui_events.put(
            (
                "keyboard_mapping",
                (action.mapping_index, mapping, action_result, event_type),
            )
        )

    def _on_mouse_test_event(self, event: MouseTestEvent) -> None:
        self.ui_events.put(("mouse_test", event))

    def _display_mouse_test_event(self, event: MouseTestEvent) -> None:
        if self.active_page != "mouse_test":
            return

        control = event.control
        if event.pressed:
            self.mouse_test_counts[control] += 1
            self.mouse_test_count_vars[control].set(
                f"{self.mouse_test_counts[control]:,}"
            )
            self.mouse_test_status_var.set(
                f"检测到：{MOUSE_TEST_LABELS[control]}"
            )
            if control in SIDE_BUTTON_CONTROLS:
                self.detected_side_buttons.add(control)
                self._refresh_side_button_confirmation()
        self._set_mouse_test_visual(control, event.pressed)

        if control in (MouseControl.WHEEL_UP, MouseControl.WHEEL_DOWN):
            previous = self.mouse_test_after_ids.pop(control, None)
            if previous is not None:
                self.root.after_cancel(previous)
            self.mouse_test_after_ids[control] = self.root.after(
                220,
                lambda target=control: self._release_mouse_test_control(
                    target
                ),
            )

    def _release_mouse_test_control(self, control: MouseControl) -> None:
        self.mouse_test_after_ids.pop(control, None)
        self._set_mouse_test_visual(control, False)

    def _set_mouse_test_visual(
        self,
        control: MouseControl,
        pressed: bool,
    ) -> None:
        if self.mouse_test_canvas is not None:
            for item_id, idle_color, active_color in self.mouse_test_items.get(
                control,
                (),
            ):
                self.mouse_test_canvas.itemconfigure(
                    item_id,
                    fill=active_color if pressed else idle_color,
                )
        indicator = self.mouse_test_status_labels.get(control)
        if indicator is not None:
            indicator.configure(
                fg=COLORS["green"] if pressed else COLORS["line"]
            )

    def _clear_mouse_test_pressed(self) -> None:
        for after_id in self.mouse_test_after_ids.values():
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        self.mouse_test_after_ids.clear()
        for control in MouseControl:
            self._set_mouse_test_visual(control, False)

    def _reset_mouse_test(self) -> None:
        self.mouse_test_counts.clear()
        self.detected_side_buttons.clear()
        self.mouse_test_status_var.set("等待操作")
        self.side_button_confirm_var.set(
            "测试记录已清空；已保存的截图侧键配置保持不变。"
        )
        for variable in self.mouse_test_count_vars.values():
            variable.set("0")
        self._clear_mouse_test_pressed()

    def _begin_side_button_reconfirmation(self) -> None:
        self.detected_side_buttons.clear()
        for control in SIDE_BUTTON_CONTROLS:
            self.mouse_test_counts[control] = 0
            self.mouse_test_count_vars[control].set("0")
            self._set_mouse_test_visual(control, False)
        self.mouse_test_status_var.set("请依次按下鼠标的两枚侧键")
        self.side_button_confirm_var.set(
            "等待侧键信号；按下可用的上一页、下一页侧键。"
        )

    def _refresh_side_button_confirmation(self) -> None:
        names = [
            SIDE_BUTTON_NAMES[control]
            for control in SIDE_BUTTON_CONTROLS
            if control in self.detected_side_buttons
        ]
        if len(names) == len(SIDE_BUTTON_CONTROLS):
            text = "两枚侧键均已检测，请点击“保存检测结果”。"
        elif names:
            text = (
                f"已检测：{'、'.join(names)}；可继续测试另一枚，"
                "或直接保存当前侧键。"
            )
        else:
            text = "尚未检测到侧键。"
        self.side_button_confirm_var.set(text)

    def _save_detected_side_buttons(self) -> None:
        if not self.detected_side_buttons:
            messagebox.showwarning(
                "未检测到侧键",
                "请先按下鼠标侧键。\n\n"
                "若图示没有反应，请在鼠标驱动中将侧键恢复为"
                "“浏览器上一页/下一页（XButton1/XButton2）”，"
                "然后重新确认。",
                parent=self.root,
            )
            return

        side_buttons = tuple(
            control.value
            for control in SIDE_BUTTON_CONTROLS
            if control in self.detected_side_buttons
        )
        self.settings.screenshot_side_buttons = side_buttons
        try:
            self.settings.save()
        except OSError as exc:
            messagebox.showerror(
                "保存失败",
                str(exc),
                parent=self.root,
            )
            return

        self.hook.set_screenshot_side_buttons(side_buttons)
        self.side_button_config_var.set(
            _side_button_config_text(side_buttons)
        )
        self.side_button_confirm_var.set(
            "配置已保存；返回功能首页后，按住右键加已确认侧键即可截图。"
        )
        names = "、".join(
            SIDE_BUTTON_NAMES[control]
            for control in SIDE_BUTTON_CONTROLS
            if control in self.detected_side_buttons
        )
        self._append_log(f"侧键截图配置已保存：{names}", "success")
        self._show_toast("侧键截图配置已保存", COLORS["green"])

    def _execute_held_action(
        self,
        action: HeldMouseAction,
    ) -> ActionResult:
        if action is HeldMouseAction.COPY:
            return self.actions.copy_selection()
        if action is HeldMouseAction.ENHANCED_PASTE:
            return self.actions.create_folder_and_paste_clipboard()
        return self.actions.capture_screenshot()

    def _poll_ui_events(self) -> None:
        try:
            while True:
                event_name, payload = self.ui_events.get_nowait()
                if event_name == "held_action":
                    action, action_result, event_type = payload
                    self._display_held_action(
                        action,
                        action_result,
                        event_type,
                    )
                elif event_name == "mouse_test":
                    self._display_mouse_test_event(payload)
                elif event_name == "keyboard_mapping":
                    (
                        mapping_index,
                        mapping,
                        action_result,
                        event_type,
                    ) = payload
                    self._display_keyboard_mapping_action(
                        mapping_index,
                        mapping,
                        action_result,
                        event_type,
                    )
        except queue.Empty:
            pass
        self.root.after(60, self._poll_ui_events)

    def _display_keyboard_mapping_action(
        self,
        mapping_index: int,
        mapping: KeyboardMappingSettings,
        action_result: ActionResult,
        event_type: str,
    ) -> None:
        mouse_name = KEYBOARD_MAPPING_MOUSE_LABELS[
            mapping.mouse_button
        ]
        text = (
            f"映射 {mapping_index + 1}：{mouse_name} → "
            f"{_keyboard_shortcut_text(mapping)}"
            f"  ·  {action_result.message}"
        )
        if action_result.detail:
            text += f"\n{action_result.detail}"
        if action_result.success:
            self._record_usage("keyboard_mapping")

        self._append_log(text, event_type)
        self._show_toast(
            action_result.message,
            COLORS["green"]
            if action_result.success
            else COLORS["red"],
        )

    def _display_held_action(
        self,
        action: HeldMouseAction,
        action_result: ActionResult,
        event_type: str,
    ) -> None:
        trigger_text = {
            HeldMouseAction.COPY: "右键 + 滚轮上滚",
            HeldMouseAction.ENHANCED_PASTE: "右键 + 滚轮下滚",
            HeldMouseAction.SCREENSHOT: "右键 + 鼠标侧键",
        }[action]
        text = f"{trigger_text}  ·  {action_result.message}"
        if action_result.detail:
            text += f"\n{action_result.detail}"
        if action_result.success:
            self._record_usage(action.value)

        self._append_log(text, event_type)
        accent = {
            "success": COLORS["green"],
            "warning": COLORS["orange"],
            "error": COLORS["red"],
        }.get(event_type, COLORS["muted"])
        self._show_toast(action_result.message, accent)

    def _append_log(self, message: str, tag: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("1.0", f"{timestamp}  {message}\n", tag)
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > 80:
            self.log_text.delete("70.0", "end")
        self.log_text.configure(state="disabled")

    def _show_toast(self, text: str, accent: str) -> None:
        if self.toast_after_id:
            self.root.after_cancel(self.toast_after_id)
            self.toast_after_id = None
        if self.toast is not None and self.toast.winfo_exists():
            self.toast.destroy()

        toast = tk.Toplevel(self.root)
        self.toast = toast
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        body = tk.Frame(
            toast,
            bg=COLORS["nav"],
            highlightbackground=accent,
            highlightthickness=2,
            padx=16,
            pady=11,
        )
        body.pack(fill="both", expand=True)
        tk.Label(
            body,
            text=text,
            bg=COLORS["nav"],
            fg="#FFFFFF",
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack()
        toast.update_idletasks()
        width = toast.winfo_reqwidth()
        height = toast.winfo_reqheight()
        x = self.root.winfo_screenwidth() - width - 28
        y = self.root.winfo_screenheight() - height - 70
        toast.geometry(f"+{x}+{y}")
        self.toast_after_id = self.root.after(1600, self._hide_toast)

    def _hide_toast(self) -> None:
        if self.toast is not None and self.toast.winfo_exists():
            self.toast.destroy()
        self.toast = None
        self.toast_after_id = None

    def close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._shutdown_watchdog = threading.Timer(
            SHUTDOWN_WATCHDOG_SECONDS,
            _force_exit_current_process,
            args=(0,),
        )
        self._shutdown_watchdog.daemon = True
        self._shutdown_watchdog.start()
        try:
            self.hook.stop()
        except Exception:
            pass
        finally:
            self.root.quit()
            self.root.destroy()


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


def acquire_single_instance() -> int | None:
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = (
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    )
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.GetLastError.argtypes = ()
    kernel32.GetLastError.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    mutex = kernel32.CreateMutexW(
        None, False, "Local\\MouseGestureActions_v1_0"
    )
    if not mutex:
        return None
    if kernel32.GetLastError() == 183:
        kernel32.CloseHandle(mutex)
        ctypes.windll.user32.MessageBoxW(
            None,
            f"{APP_NAME}已经在运行。",
            APP_NAME,
            0x00000040,
        )
        return None
    return int(mutex)


def main() -> None:
    enable_dpi_awareness()
    mutex = acquire_single_instance()
    if mutex is None:
        return
    normal_shutdown = False
    try:
        root = tk.Tk()
        MouseGestureApp(root)
        root.mainloop()
        normal_shutdown = True
    finally:
        ctypes.windll.kernel32.CloseHandle(mutex)
    if normal_shutdown:
        _force_exit_current_process(0)


if __name__ == "__main__":
    main()
