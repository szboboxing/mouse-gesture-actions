from __future__ import annotations

import ctypes
import queue
import random
import sys
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
)
from settings import AppSettings, load_settings
from version import APP_NAME, VERSION_TAG


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
    ("custom", "自定义功能"),
)


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
            pady=14,
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
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(14, 5))

        tk.Label(
            self,
            text=action_text,
            bg=COLORS["page"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=10,
            pady=7,
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
                text="X1",
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
            self._on_held_action,
            self.settings.screenshot_combo_interval_ms,
        )
        self.usage_counts: Counter[str] = Counter()
        self.listening = False
        self.toast: tk.Toplevel | None = None
        self.toast_after_id: str | None = None

        self.interval_var = tk.IntVar(
            value=self.settings.screenshot_combo_interval_ms
        )
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
        self.custom_name_vars = (
            tk.StringVar(value=self.settings.custom_button_1_name),
            tk.StringVar(value=self.settings.custom_button_2_name),
        )
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
            "App.TSpinbox",
            fieldbackground=COLORS["card"],
            foreground=COLORS["text"],
            bordercolor=COLORS["line"],
            arrowcolor=COLORS["blue"],
            padding=6,
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
            "2  滚动滚轮或按 XButton1",
            "3  松开右键退出自定义状态",
        ):
            tk.Label(
                help_box,
                text=text,
                bg=COLORS["nav"],
                fg=COLORS["nav_muted"],
                font=("Microsoft YaHei UI", 9),
            ).pack(anchor="w", pady=3)

        page = tk.Frame(self.root, bg=COLORS["page"])
        page.pack(side="left", fill="both", expand=True)
        self._build_page(page)

    def _build_page(self, page: tk.Frame) -> None:
        header = tk.Frame(page, bg=COLORS["page"])
        header.pack(fill="x", padx=22, pady=(18, 12))
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
            text="仅在按住右键期间识别滚轮和侧键组合",
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
                "右键按住 + XButton1",
                "调用系统截图工具（Win+Shift+S）",
                COLORS["orange"],
            ),
            (
                "wheel_combo",
                "滚轮组合截图",
                "右键按住 + 上滚→下滚",
                "在时间窗口内完成组合才调用系统截图",
                COLORS["red"],
            ),
        )
        for index, spec in enumerate(card_specs):
            card = GestureCard(cards, *spec)
            row, column = divmod(index, 2)
            card.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 7, 7 if column == 0 else 0),
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

        self._build_quick_tools(page)

        settings_panel = tk.Frame(
            page,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=18,
            pady=10,
        )
        settings_panel.pack(fill="x", padx=22, pady=(10, 8))
        tk.Label(
            settings_panel,
            text="组合设置",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 18))

        tk.Label(
            settings_panel,
            text="上→下截图窗口(ms)",
            bg=COLORS["card"],
            fg=COLORS["muted"],
        ).grid(row=0, column=1, sticky="e", padx=(0, 6))
        interval = ttk.Spinbox(
            settings_panel,
            from_=200,
            to=300,
            increment=10,
            textvariable=self.interval_var,
            width=7,
            style="App.TSpinbox",
        )
        interval.grid(row=0, column=2, sticky="w")

        tk.Label(
            settings_panel,
            text="滚轮较松时建议调低，默认 250ms",
            bg=COLORS["card"],
            fg=COLORS["orange"],
            font=("Microsoft YaHei UI", 8),
        ).grid(row=0, column=3, sticky="w", padx=(12, 4))

        ttk.Checkbutton(
            settings_panel,
            text="启动后自动监听",
            variable=self.launch_var,
            style="App.TCheckbutton",
        ).grid(row=0, column=4, padx=(18, 8))
        ttk.Checkbutton(
            settings_panel,
            text="启动时最小化",
            variable=self.minimize_var,
            style="App.TCheckbutton",
        ).grid(row=0, column=5, padx=(0, 10))

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
        save_button.grid(row=0, column=6, sticky="e")
        settings_panel.columnconfigure(6, weight=1)
        self._build_encouragement(page)

    def _build_quick_tools(self, page: tk.Frame) -> None:
        panel = tk.Frame(
            page,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=12,
            pady=9,
        )
        panel.pack(fill="x", padx=22, pady=(10, 0))
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
        )
        self._quick_button(
            buttons,
            1,
            "浏览器",
            lambda: self._run_quick_action(
                "browser", self.actions.open_browser
            ),
            COLORS["green"],
        )
        self._quick_button(
            buttons,
            2,
            "媒体播放器",
            lambda: self._run_quick_action(
                "media", self.actions.open_media_player
            ),
            COLORS["orange"],
        )
        self._adjustment_group(
            buttons,
            3,
            "屏幕亮度",
            lambda: self._run_display_adjustment("brightness", -1),
            lambda: self._run_display_adjustment("brightness", 1),
        )
        self._adjustment_group(
            buttons,
            4,
            "屏幕对比度",
            lambda: self._run_display_adjustment("contrast", -1),
            lambda: self._run_display_adjustment("contrast", 1),
        )
        self._quick_button(
            buttons,
            5,
            "统计清零",
            self._reset_statistics,
            COLORS["red"],
        )
        for offset in range(2):
            button = self._quick_button(
                buttons,
                6 + offset,
                "",
                lambda index=offset: self._run_custom_action(index),
                COLORS["blue"],
                textvariable=self.custom_name_vars[offset],
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
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
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
            font=("Microsoft YaHei UI", 8, "bold"),
            wraplength=95,
            padx=5,
            pady=9,
        )
        button.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 3, 0 if column == 7 else 3),
        )
        return button

    @staticmethod
    def _adjustment_group(
        parent: tk.Frame,
        column: int,
        title: str,
        decrease: Callable[[], None],
        increase: Callable[[], None],
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
            text=title,
            bg=COLORS["page"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 8, "bold"),
        ).pack()
        controls = tk.Frame(group, bg=COLORS["page"])
        controls.pack(pady=(3, 0))
        for text, command in (("－", decrease), ("＋", increase)):
            tk.Button(
                controls,
                text=text,
                command=command,
                bg=COLORS["card"],
                fg=COLORS["blue"],
                activebackground=COLORS["blue_soft"],
                relief="flat",
                bd=0,
                cursor="hand2",
                font=("Segoe UI", 8, "bold"),
                width=3,
                pady=1,
            ).pack(side="left", padx=2)

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

        self.listening = bool(self.settings.launch_listening)
        self.hook.set_enabled(self.listening)
        self._refresh_listening_state()
        self._append_log(
            "程序已就绪，仅在按住右键时识别滚轮和 XButton1",
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

    def save_settings(self) -> None:
        try:
            interval = int(self.interval_var.get())
            if not 200 <= interval <= 300:
                raise ValueError("上→下截图窗口必须在 200-300 毫秒之间")
        except (ValueError, tk.TclError) as exc:
            messagebox.showwarning("设置未保存", str(exc))
            return

        self.settings = AppSettings(
            screenshot_combo_interval_ms=interval,
            launch_listening=self.launch_var.get(),
            minimize_on_start=self.minimize_var.get(),
            custom_button_1_name=self.settings.custom_button_1_name,
            custom_button_1_target=self.settings.custom_button_1_target,
            custom_button_2_name=self.settings.custom_button_2_name,
            custom_button_2_target=self.settings.custom_button_2_target,
        )
        try:
            self.settings.save()
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc))
            return

        self.hook.set_combo_interval_ms(interval)
        self._append_log("设置已保存并立即生效", "success")
        self._show_toast("设置已保存", COLORS["green"])

    def _on_held_action(self, action: HeldMouseAction) -> None:
        action_result = self._execute_held_action(action)
        event_type = "success" if action_result.success else "error"
        self.ui_events.put(
            ("held_action", (action, action_result, event_type))
        )

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
        except queue.Empty:
            pass
        self.root.after(60, self._poll_ui_events)

    def _display_held_action(
        self,
        action: HeldMouseAction,
        action_result: ActionResult,
        event_type: str,
    ) -> None:
        trigger_text = {
            HeldMouseAction.COPY: "右键 + 滚轮上滚",
            HeldMouseAction.ENHANCED_PASTE: "右键 + 滚轮下滚",
            HeldMouseAction.SCREENSHOT: "右键截图组合",
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
        self.hook.stop()
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
    try:
        root = tk.Tk()
        MouseGestureApp(root)
        root.mainloop()
    finally:
        ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
