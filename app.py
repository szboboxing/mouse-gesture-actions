from __future__ import annotations

import ctypes
import queue
import sys
import tkinter as tk
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, Sequence

from actions import ActionResult, SystemActions, parse_shortcut
from gesture_controller import ActionKind, GestureController, GestureOutcome
from gesture_recognizer import Point
from mouse_hook import GlobalRightButtonGestureHook
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


class GestureCard(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        gesture: str,
        title: str,
        subtitle: str,
        action_text: str,
        accent: str,
        shortcut_variable: tk.StringVar | None = None,
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
        ).grid(row=0, column=1, sticky="ew")
        tk.Label(
            self,
            text=subtitle,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=1, column=1, sticky="new", pady=(3, 0))

        tk.Label(
            self,
            text="执行动作",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 8),
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(14, 5))

        if shortcut_variable is None:
            tk.Label(
                self,
                text=action_text,
                bg=COLORS["page"],
                fg=COLORS["text"],
                font=("Microsoft YaHei UI", 9, "bold"),
                padx=10,
                pady=7,
                anchor="w",
            ).grid(row=3, column=0, columnspan=2, sticky="ew")
        else:
            entry = tk.Entry(
                self,
                textvariable=shortcut_variable,
                bg=COLORS["page"],
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
                font=("Segoe UI", 10, "bold"),
                highlightbackground=COLORS["line"],
                highlightcolor=accent,
                highlightthickness=1,
            )
            entry.grid(
                row=3,
                column=0,
                columnspan=2,
                sticky="ew",
                ipady=7,
            )

    @staticmethod
    def _draw_icon(canvas: tk.Canvas, gesture: str, accent: str) -> None:
        canvas.create_rectangle(0, 0, 54, 54, fill=COLORS["blue_soft"], outline="")
        if gesture in {"circle_left", "circle_right"}:
            start = 35 if gesture == "circle_left" else 145
            extent = 285 if gesture == "circle_left" else -285
            canvas.create_arc(
                10,
                10,
                44,
                44,
                start=start,
                extent=extent,
                style="arc",
                outline=accent,
                width=4,
            )
            if gesture == "circle_left":
                canvas.create_polygon(
                    9, 20, 18, 18, 14, 27, fill=accent, outline=""
                )
            else:
                canvas.create_polygon(
                    45, 20, 36, 18, 40, 27, fill=accent, outline=""
                )
        elif gesture == "check":
            canvas.create_line(
                10,
                28,
                22,
                40,
                45,
                14,
                fill=accent,
                width=5,
                capstyle="round",
                joinstyle="round",
            )
        else:
            canvas.create_line(
                11, 39, 40, 10, fill=accent, width=4, arrow="last"
            )
            canvas.create_line(
                43, 16, 14, 45, fill=accent, width=4, arrow="last"
            )


class MouseGestureApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.settings = load_settings()
        self.actions = SystemActions()
        self.controller = GestureController(
            self.settings.sensitivity,
            self.settings.double_swipe_interval_ms,
        )
        self.action_shortcuts = {
            ActionKind.COPY: self.settings.copy_shortcut,
            ActionKind.PASTE: self.settings.paste_shortcut,
            ActionKind.SCREENSHOT: self.settings.screenshot_shortcut,
        }
        self.ui_events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.hook = GlobalRightButtonGestureHook(self._on_stroke)
        self.listening = False
        self.toast: tk.Toplevel | None = None
        self.toast_after_id: str | None = None

        self.copy_var = tk.StringVar(value=self.settings.copy_shortcut)
        self.paste_var = tk.StringVar(value=self.settings.paste_shortcut)
        self.screenshot_var = tk.StringVar(
            value=self.settings.screenshot_shortcut
        )
        self.sensitivity_var = tk.StringVar(value=self.settings.sensitivity)
        self.interval_var = tk.IntVar(
            value=self.settings.double_swipe_interval_ms
        )
        self.launch_var = tk.BooleanVar(value=self.settings.launch_listening)
        self.minimize_var = tk.BooleanVar(
            value=self.settings.minimize_on_start
        )
        self.status_var = tk.StringVar(value="正在初始化")

        self._configure_window()
        self._configure_styles()
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(60, self._poll_ui_events)
        self.root.after(150, self._start_hook)

    def _configure_window(self) -> None:
        self.root.title(f"{APP_NAME} {VERSION_TAG}")
        self.root.geometry("1120x750")
        self.root.minsize(1020, 690)
        self.root.configure(bg=COLORS["page"])
        self.root.option_add("*Font", ("Microsoft YaHei UI", 9))
        icon_path = resource_path("assets/mouse_gesture.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass
        self.root.update_idletasks()
        width = 1120
        height = 750
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
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
        sidebar = tk.Frame(self.root, bg=COLORS["nav"], width=244)
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
            font=("Microsoft YaHei UI", 13, "bold"),
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
            text="普通右键单击保持正常",
            bg=COLORS["nav_soft"],
            fg=COLORS["nav_muted"],
            font=("Microsoft YaHei UI", 8),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(7, 0))

        self.toggle_button = tk.Button(
            sidebar,
            text="暂停手势监听",
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
            "2  连续画出完整轨迹",
            "3  松开右键立即执行",
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
        header.pack(fill="x", padx=28, pady=(25, 17))
        title_box = tk.Frame(header, bg=COLORS["page"])
        title_box.pack(side="left")
        tk.Label(
            title_box,
            text="手势控制面板",
            bg=COLORS["page"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="将鼠标轨迹转换为键盘组合键和系统动作",
            bg=COLORS["page"],
            fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", pady=(4, 0))
        tk.Label(
            header,
            text="按住右键绘制",
            bg=COLORS["green_soft"],
            fg=COLORS["green"],
            padx=13,
            pady=7,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="right", anchor="n")

        content = tk.Frame(page, bg=COLORS["page"])
        content.pack(fill="both", expand=True, padx=28)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        cards = tk.Frame(content, bg=COLORS["page"])
        cards.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)
        cards.rowconfigure(0, weight=1)
        cards.rowconfigure(1, weight=1)

        card_specs = (
            (
                "circle_left",
                "左向圆圈",
                "逆时针画圆",
                "复制",
                COLORS["blue"],
                self.copy_var,
            ),
            (
                "circle_right",
                "右向圆圈",
                "顺时针画圆",
                "粘贴",
                COLORS["green"],
                self.paste_var,
            ),
            (
                "check",
                "对勾",
                "先向右下，再向右上",
                "截图",
                COLORS["orange"],
                self.screenshot_var,
            ),
            (
                "double_swipe",
                "同向快划两次",
                "右上或左下，连续两次",
                "当前目录新建文件夹",
                COLORS["red"],
                None,
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
        activity.grid(row=0, column=1, sticky="nsew")
        activity.rowconfigure(2, weight=1)
        activity.columnconfigure(0, weight=1)
        tk.Label(
            activity,
            text="识别记录",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            activity,
            text="最近的手势和执行结果",
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

        settings_panel = tk.Frame(
            page,
            bg=COLORS["card"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=18,
            pady=14,
        )
        settings_panel.pack(fill="x", padx=28, pady=(16, 25))
        tk.Label(
            settings_panel,
            text="识别设置",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 18))

        tk.Label(
            settings_panel,
            text="灵敏度",
            bg=COLORS["card"],
            fg=COLORS["muted"],
        ).grid(row=0, column=1, sticky="e", padx=(0, 6))
        sensitivity = ttk.Combobox(
            settings_panel,
            textvariable=self.sensitivity_var,
            values=("灵敏", "标准", "稳健"),
            state="readonly",
            width=7,
            style="App.TCombobox",
        )
        sensitivity.grid(row=0, column=2, sticky="w")

        tk.Label(
            settings_panel,
            text="双划间隔(ms)",
            bg=COLORS["card"],
            fg=COLORS["muted"],
        ).grid(row=0, column=3, sticky="e", padx=(18, 6))
        interval = ttk.Spinbox(
            settings_panel,
            from_=350,
            to=1500,
            increment=50,
            textvariable=self.interval_var,
            width=7,
            style="App.TSpinbox",
        )
        interval.grid(row=0, column=4, sticky="w")

        ttk.Checkbutton(
            settings_panel,
            text="启动后自动监听",
            variable=self.launch_var,
            style="App.TCheckbutton",
        ).grid(row=0, column=5, padx=(18, 8))
        ttk.Checkbutton(
            settings_panel,
            text="启动时最小化",
            variable=self.minimize_var,
            style="App.TCheckbutton",
        ).grid(row=0, column=6, padx=(0, 10))

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
        save_button.grid(row=0, column=7, sticky="e")
        settings_panel.columnconfigure(7, weight=1)

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
        self._append_log("程序已就绪，右键单击保持正常", "muted")
        if self.settings.minimize_on_start:
            self.root.after(250, self.root.iconify)

    def toggle_listening(self) -> None:
        if self.hook.start_error:
            self._start_hook()
            return
        self.listening = not self.listening
        self.hook.set_enabled(self.listening)
        self.controller.reset_pending_swipe()
        self._refresh_listening_state()
        state = "手势监听已启动" if self.listening else "手势监听已暂停"
        self._append_log(state, "success" if self.listening else "warning")

    def _refresh_listening_state(self) -> None:
        if self.listening:
            self.status_var.set("正在监听")
            self._set_status_dot(COLORS["green"])
            self.toggle_button.configure(
                text="暂停手势监听",
                bg=COLORS["blue"],
                activebackground="#405ED9",
            )
        else:
            self.status_var.set("监听已暂停")
            self._set_status_dot(COLORS["orange"])
            self.toggle_button.configure(
                text="开始手势监听",
                bg=COLORS["orange"],
                activebackground="#C9761E",
            )

    def _set_status_dot(self, color: str) -> None:
        self.status_dot.itemconfigure(self.status_dot_id, fill=color)

    def save_settings(self) -> None:
        try:
            parse_shortcut(self.copy_var.get())
            parse_shortcut(self.paste_var.get())
            parse_shortcut(self.screenshot_var.get())
            interval = int(self.interval_var.get())
            if not 350 <= interval <= 1500:
                raise ValueError("双划间隔必须在 350-1500 毫秒之间")
        except (ValueError, tk.TclError) as exc:
            messagebox.showwarning("设置未保存", str(exc))
            return

        self.settings = AppSettings(
            copy_shortcut=self.copy_var.get().strip(),
            paste_shortcut=self.paste_var.get().strip(),
            screenshot_shortcut=self.screenshot_var.get().strip(),
            sensitivity=self.sensitivity_var.get(),
            double_swipe_interval_ms=interval,
            launch_listening=self.launch_var.get(),
            minimize_on_start=self.minimize_var.get(),
        )
        try:
            self.settings.save()
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc))
            return

        self.controller.update_settings(
            self.settings.sensitivity,
            self.settings.double_swipe_interval_ms,
        )
        self.action_shortcuts = {
            ActionKind.COPY: self.settings.copy_shortcut,
            ActionKind.PASTE: self.settings.paste_shortcut,
            ActionKind.SCREENSHOT: self.settings.screenshot_shortcut,
        }
        self._append_log("设置已保存并立即生效", "success")
        self._show_toast("设置已保存", COLORS["green"])

    def _on_stroke(self, points: Sequence[Point]) -> None:
        outcome = self.controller.process(points)
        if outcome.action is None:
            event_type = "warning" if outcome.awaiting_second_swipe else "muted"
            self.ui_events.put(("gesture", (outcome, None, event_type)))
            return

        action_result = self._execute_action(outcome.action)
        event_type = "success" if action_result.success else "error"
        self.ui_events.put(
            ("gesture", (outcome, action_result, event_type))
        )

    def _execute_action(self, action: ActionKind) -> ActionResult:
        if action is ActionKind.COPY:
            return self.actions.send_shortcut(
                self.action_shortcuts[ActionKind.COPY], "复制"
            )
        if action is ActionKind.PASTE:
            return self.actions.send_shortcut(
                self.action_shortcuts[ActionKind.PASTE], "粘贴"
            )
        if action is ActionKind.SCREENSHOT:
            return self.actions.send_shortcut(
                self.action_shortcuts[ActionKind.SCREENSHOT], "截图"
            )
        return self.actions.create_folder_in_active_directory()

    def _poll_ui_events(self) -> None:
        try:
            while True:
                event_name, payload = self.ui_events.get_nowait()
                if event_name == "gesture":
                    outcome, action_result, event_type = payload
                    self._display_outcome(outcome, action_result, event_type)
        except queue.Empty:
            pass
        self.root.after(60, self._poll_ui_events)

    def _display_outcome(
        self,
        outcome: GestureOutcome,
        action_result: ActionResult | None,
        event_type: str,
    ) -> None:
        confidence = (
            f"{outcome.result.confidence * 100:.0f}%"
            if outcome.result.confidence > 0
            else "--"
        )
        if action_result is None:
            text = f"{outcome.message}  ·  置信度 {confidence}"
            toast_text = outcome.message
        else:
            text = (
                f"{outcome.message}  ·  {action_result.message}"
                f"  ·  置信度 {confidence}"
            )
            if action_result.detail:
                text += f"\n{action_result.detail}"
            toast_text = action_result.message

        self._append_log(text, event_type)
        accent = {
            "success": COLORS["green"],
            "warning": COLORS["orange"],
            "error": COLORS["red"],
        }.get(event_type, COLORS["muted"])
        self._show_toast(toast_text, accent)

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
