"""帮助中心浏览窗口。

三级页面：首页（模块列表）→ 模块页（条目列表）→ 说明页（正文）。
底部导航：首页 / 返回上级 / 上一页 / 下一页。
帮助内容均取自程序实际功能，与 README 保持一致。
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from version import APP_NAME, VERSION_TAG

# 与 app.py 保持一致的配色
PAGE_BG = "#F4F6FA"
CARD_BG = "#FFFFFF"
TEXT = "#172033"
MUTED = "#657087"
LINE = "#E4E8F0"
BLUE = "#4F6EF7"
BLUE_ACTIVE = "#405ED9"
BLUE_SOFT = "#EEF1FF"


# 各功能模块帮助主题，内容均取自程序实际功能
HELP_TOPICS: dict[str, dict] = {
    "gesture": {
        "label": "🖱 右键组合手势",
        "items": [
            {"label": "功能简介", "sections": [
                ("方案 A · 右键保持",
                 "按住鼠标右键不放，再滚动滚轮或按侧键即可执行动作，"
                 "松开右键退出自定义状态。"),
                ("三个手势动作",
                 "① 右键按住 + 滚轮向上：立即复制（Ctrl+C）；"
                 "② 右键按住 + 滚轮向下：立即增强粘贴（新建文件夹并粘贴剪贴板内容）；"
                 "③ 右键按住 + 已确认保存的侧键：调用系统截图（Win+Shift+S）。"),
                ("只执行一个动作",
                 "每次按住右键最多执行一个动作。未触发任何动作时，松开右键会回放"
                 "原生右键单击；已执行动作时不会额外弹出右键菜单。"),
            ]},
            {"label": "判定规则与优先级", "sections": [
                ("滚轮判定",
                 "上滚立即复制、下滚立即增强粘贴，都不再等待时间窗口；"
                 "“上滚→下滚”不再识别为截图，同一次右键保持只执行先发生的动作。"),
                ("侧键判定",
                 "右键按住时，已确认保存的 XButton1 或 XButton2 可立即截图；"
                 "未按右键时，已启动映射的侧键发送自定义快捷键并替代浏览器原生动作，"
                 "未启动映射的侧键完整透传（保留前进/后退），左键始终透传。"),
                ("输入优先级（从高到低）",
                 "鼠标按键测试页透传 ＞ 右键保持 + 已确认侧键截图 ＞ "
                 "普通侧键键盘映射 ＞ 浏览器原生前进/后退。"),
            ]},
            {"label": "增强粘贴", "sections": [
                ("执行位置",
                 "增强粘贴只在当前激活的 Windows 文件资源管理器窗口或 Windows 桌面执行，"
                 "前台程序不是这两者时动作会被拒绝，不会在错误位置创建文件夹。"),
                ("执行过程",
                 "先发送 Ctrl+Shift+N 新建文件夹，等待重命名输入框出现，再发送 Ctrl+V，"
                 "完成“新建文件夹并以剪贴板内容命名”。"),
                ("名称限制",
                 "剪贴板内容须能作为文件夹名称使用，Windows 禁止的文件名字符仍受系统规则限制。"),
            ]},
        ],
    },
    "keyboard": {
        "label": "⌨ 自定义键盘映射",
        "items": [
            {"label": "两组映射配置", "sections": [
                ("可配置项",
                 "功能首页“快捷工具”上方提供两组独立映射，每组可选："
                 "鼠标侧键（X2/下一页侧键 或 X1/上一页侧键）、"
                 "修饰键（Ctrl、Alt、Shift、Win，可任意组合也可全不选）、"
                 "主键（A-Z 或 F1-F12）。"),
                ("增强粘贴选项",
                 "每组都可点选“增强粘贴”，效果为在当前目录新建文件夹、进入重命名状态"
                 "并粘贴剪贴板内容；点选不会清空已选修饰键和主键，取消点选即恢复原快捷键。"
                 "映射 2 的增强粘贴为整行大按钮：开启绿色高亮、关闭灰色显示。"),
                ("默认配置",
                 "映射 1：X2 → Ctrl+C（初始关闭）；映射 2：X1 → Ctrl+V（初始关闭）。"),
            ]},
            {"label": "启停与冲突处理", "sections": [
                ("同一侧键只允许一组",
                 "同一侧键最多启动一组映射；若两组选择相同侧键，后启动或后修改的一组生效，"
                 "另一组自动停用。每组右侧的“启动/停用”按钮可立即切换。"),
                ("与监听的关系",
                 "启动任意键盘映射时会自动开启全局监听；手动暂停组合监听后，"
                 "右键动作和键盘映射都会暂停。"),
                ("立即保存",
                 "配置内容和启用状态会立即保存，无需重启程序。"),
            ]},
        ],
    },
    "mouse_test": {
        "label": "🧪 鼠标按键测试",
        "items": [
            {"label": "检测内容与计数", "sections": [
                ("七类输入检测",
                 "左键、右键按下高亮抬起恢复；中键（滚轮按下）按下高亮；"
                 "滚轮向上/向下按方向短暂闪烁；X2/下一页、X1/上一页两枚侧键检测。"),
                ("结果与计数",
                 "页面显示最后检测结果，并分别累计七类输入的触发次数。"),
                ("只读透传模式",
                 "测试期间进入只读模式，所有鼠标消息继续透传给 Windows，"
                 "不会执行复制、增强粘贴或截图；离开测试页后恢复进入前的监听状态。"),
            ]},
            {"label": "侧键重新确认", "sections": [
                ("操作步骤",
                 "侧键无反应或截图失败时：① 单击“重新确认侧键”；"
                 "② 按下可用的上一页、下一页侧键，确认图示和计数有响应；"
                 "③ 单击“保存检测结果”；④ 返回功能首页用“右键按住 + 已确认侧键”截图。"),
                ("保存规则",
                 "可只保存一枚检测正常的侧键，也可保存两枚；保存后立即生效并写入设置文件，"
                 "无需重启。"),
                ("硬件前提",
                 "若按侧键图示完全无响应，需先在鼠标驱动中将侧键恢复为"
                 "“浏览器上一页/下一页（XButton1/XButton2）”，软件无法替代硬件或驱动"
                 "产生缺失的侧键信号。"),
            ]},
        ],
    },
    "tools": {
        "label": "🧰 界面工具",
        "items": [
            {"label": "快捷启动与显示调节", "sections": [
                ("快捷启动",
                 "一键启动计算器、系统默认浏览器和 Windows 媒体播放器。"),
                ("显示调节",
                 "亮度和对比度分别提供“降低 / 提高”按钮。内置屏幕亮度优先使用 "
                 "Windows WMI；外接显示器亮度和对比度使用 DDC/CI。"
                 "硬件不支持时会显示失败原因。"),
            ]},
            {"label": "自定义按钮与统计", "sections": [
                ("两个自定义按钮",
                 "两个按钮均可右键编辑名称和打开目标（程序、文件或网址）。"),
                ("鼠标统计器",
                 "统计本次运行的左键/右键次数、鼠标移动像素距离，以及复制、增强粘贴、"
                 "截图等各功能的成功使用次数；“统计清零”可清除本次运行数据。"),
                ("随机鼓励语",
                 "启动时随机显示一句鼓励语，也可单击“换一句”刷新。"),
            ]},
            {"label": "监听开关与设置保存", "sections": [
                ("监听开关",
                 "左侧“暂停组合监听 / 开启组合监听”大按钮可随时暂停或恢复全部手势动作。"),
                ("启动设置",
                 "可勾选“启动后自动监听”和“启动时最小化”，修改后单击“保存设置”。"),
                ("设置文件位置",
                 "设置保存在 %APPDATA%\\MouseGestureActions\\settings.json；"
                 "V1.0-V1.9 的旧配置可继续读取，已移除的旧字段会被自动忽略。"),
            ]},
        ],
    },
    "window": {
        "label": "🪟 窗口与权限",
        "items": [
            {"label": "关闭主窗口保护", "sections": [
                ("三个选择",
                 "点击右上角关闭按钮不会立即退出，而是弹出选择："
                 "“确认关闭”执行完整退出清理；“最小化”隐藏窗口但全局监听继续运行；"
                 "“取消”返回主窗口。"),
                ("默认焦点",
                 "确认窗默认聚焦“取消”按钮，鼠标指针自动移动到该按钮中央；"
                 "按 Enter、Esc 或直接关闭确认窗也按取消处理。"),
            ]},
            {"label": "权限与使用限制", "sections": [
                ("管理员权限",
                 "普通权限程序不能向管理员权限窗口发送按键；目标程序以管理员身份运行时，"
                 "本工具也需要以相同权限运行。"),
                ("侧键与显示器",
                 "侧键需要鼠标硬件和驱动向 Windows 上报 XButton1/XButton2；"
                 "若驱动把侧键映射成键盘快捷键，需先恢复为浏览器前进/后退侧键；"
                 "对比度调节依赖显示器 DDC/CI 支持。"),
            ]},
            {"label": "已移除的旧功能", "sections": [
                ("轨迹手势已移除",
                 "当前版本不再使用轨迹绘制，已移除逆时针/顺时针圆圈识别、对勾截图识别、"
                 "同方向双快划新建目录、删除和回车确认动作，以及旧版轨迹灵敏度设置。"),
                ("旧截图组合已移除",
                 "已移除滚轮“上滚→下滚”组合截图和 200-300ms 截图组合窗口及相关设置；"
                 "增强粘贴仍包含“新建文件夹”步骤。"),
            ]},
        ],
    },
}


class HelpBrowser(tk.Toplevel):
    """帮助中心浏览窗口（首页 → 模块页 → 说明页）。"""

    def __init__(
        self,
        parent: tk.Misc,
        module_key: str | None = None,
        item_index: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.parent_window = parent

        # 全部说明页展平后的顺序，供“上一页/下一页”线性翻页
        self.leaf_order = [
            (mkey, i)
            for mkey, module in HELP_TOPICS.items()
            for i in range(len(module["items"]))
        ]

        if module_key is not None and item_index is not None:
            self.path: list[object] = [module_key, item_index]
        elif module_key is not None:
            self.path = [module_key]
        else:
            self.path = []

        self.title(f"帮助 · {APP_NAME} {VERSION_TAG}")
        self.configure(bg=PAGE_BG)
        self.geometry("640x540")
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        outer = tk.Frame(self, bg=PAGE_BG)
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        self.crumb_var = tk.StringVar()
        tk.Label(
            outer, textvariable=self.crumb_var,
            font=("Microsoft YaHei UI", 9),
            fg=MUTED, bg=PAGE_BG,
        ).pack(anchor="w")
        self.title_var = tk.StringVar()
        tk.Label(
            outer, textvariable=self.title_var,
            font=("Microsoft YaHei UI", 15, "bold"),
            fg=BLUE, bg=PAGE_BG,
        ).pack(anchor="w", pady=(2, 10))

        self.box = tk.Frame(
            outer, bg=CARD_BG,
            highlightbackground=LINE, highlightthickness=1,
        )
        self.box.pack(fill="both", expand=True)

        nav = tk.Frame(outer, bg=PAGE_BG)
        nav.pack(fill="x", pady=(12, 0))
        self.btn_home = self._nav_button(nav, "🏠 首页", self.go_home)
        self.btn_up = self._nav_button(nav, "⬆ 返回上级", self.go_up)
        self.btn_prev = self._nav_button(nav, "◀ 上一页", self.go_prev)
        self.btn_next = self._nav_button(nav, "下一页 ▶", self.go_next)
        self.btn_home.pack(side="left")
        self.btn_up.pack(side="left", padx=(8, 0))
        self.btn_prev.pack(side="left", padx=(8, 0))
        self.btn_next.pack(side="left", padx=(8, 0))
        self._nav_button(nav, "关闭", self._on_close, accent=True).pack(
            side="right"
        )

        self._render()

    # ---------- 导航动作 ----------

    def navigate(
        self, module_key: str | None = None, item_index: int | None = None
    ) -> None:
        """从侧边栏入口跳转到指定页，并把窗口提到最前。"""
        if module_key is not None and item_index is not None:
            self.path = [module_key, item_index]
        elif module_key is not None:
            self.path = [module_key]
        else:
            self.path = []
        self._render()
        self.deiconify()
        self.lift()
        self.focus_force()

    def go_home(self) -> None:
        self.path = []
        self._render()

    def go_up(self) -> None:
        if len(self.path) >= 2:
            self.path = self.path[:1]
        elif len(self.path) == 1:
            self.path = []
        self._render()

    def _neighbor_index(self, delta: int) -> int | None:
        """返回上一页/下一页目标在 leaf_order 中的下标，不可达返回 None。"""
        if len(self.path) == 2:
            cur = self.leaf_order.index((self.path[0], self.path[1]))
            target = cur + delta
        elif len(self.path) == 1:
            start = next(
                i for i, (mkey, _idx) in enumerate(self.leaf_order)
                if mkey == self.path[0]
            )
            target = start - 1 if delta < 0 else start
        else:
            target = 0 if delta > 0 else -1
        if 0 <= target < len(self.leaf_order):
            return target
        return None

    def go_prev(self) -> None:
        idx = self._neighbor_index(-1)
        if idx is not None:
            mkey, item_index = self.leaf_order[idx]
            self.path = [mkey, item_index]
            self._render()

    def go_next(self) -> None:
        idx = self._neighbor_index(1)
        if idx is not None:
            mkey, item_index = self.leaf_order[idx]
            self.path = [mkey, item_index]
            self._render()

    def _on_close(self) -> None:
        if getattr(self.parent_window, "_help_browser", None) is self:
            self.parent_window._help_browser = None
        self.destroy()

    # ---------- 页面渲染 ----------

    def _render(self) -> None:
        for child in self.box.winfo_children():
            child.destroy()
        inner = tk.Frame(self.box, bg=CARD_BG)
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        if not self.path:
            self._render_home(inner)
        elif len(self.path) == 1:
            self._render_module(inner, str(self.path[0]))
        else:
            self._render_leaf(inner, str(self.path[0]), int(self.path[1]))

        self._set_enabled(self.btn_home, bool(self.path))
        self._set_enabled(self.btn_up, bool(self.path))
        self._set_enabled(self.btn_prev, self._neighbor_index(-1) is not None)
        self._set_enabled(self.btn_next, self._neighbor_index(1) is not None)

    @staticmethod
    def _set_enabled(button: tk.Button, enabled: bool) -> None:
        button.configure(
            state="normal" if enabled else "disabled",
            bg=BLUE if enabled else "#C7CEE8",
            activebackground=BLUE_ACTIVE if enabled else "#C7CEE8",
            disabledforeground="#F2F4FB",
        )

    def _nav_button(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        accent: bool = False,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=BLUE,
            fg="#FFFFFF",
            activebackground=BLUE_ACTIVE,
            activeforeground="#FFFFFF",
            disabledforeground="#F2F4FB",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=7,
            font=("Microsoft YaHei UI", 9, "bold"),
        )

    def _index_button(
        self, parent: tk.Misc, text: str, command: Callable[[], None]
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=BLUE_SOFT,
            fg=TEXT,
            activebackground=BLUE,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            anchor="w",
            padx=14,
            pady=9,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        button.pack(fill="x", pady=3)
        return button

    def _render_home(self, inner: tk.Frame) -> None:
        self.crumb_var.set("首页")
        self.title_var.set("帮助中心")
        tk.Label(
            inner, text=f"{APP_NAME} {VERSION_TAG} · 请选择要查看的功能模块：",
            font=("Microsoft YaHei UI", 10, "bold"),
            fg=TEXT, bg=CARD_BG,
        ).pack(anchor="w", pady=(0, 6))
        for mkey, module in HELP_TOPICS.items():
            self._index_button(
                inner, module["label"],
                lambda k=mkey: self._open_module(k),
            )

    def _open_module(self, module_key: str) -> None:
        self.path = [module_key]
        self._render()

    def _render_module(self, inner: tk.Frame, module_key: str) -> None:
        module = HELP_TOPICS[module_key]
        label = module["label"]
        self.crumb_var.set(f"首页 / {label}")
        self.title_var.set(label)
        tk.Label(
            inner, text="请选择要查看的说明：",
            font=("Microsoft YaHei UI", 10, "bold"),
            fg=TEXT, bg=CARD_BG,
        ).pack(anchor="w", pady=(0, 6))
        for item_index, item in enumerate(module["items"]):
            self._index_button(
                inner, item["label"],
                lambda k=module_key, i=item_index: self.navigate(k, i),
            )

    def _render_leaf(
        self, inner: tk.Frame, module_key: str, item_index: int
    ) -> None:
        module = HELP_TOPICS[module_key]
        item = module["items"][item_index]
        label = module["label"]
        item_label = item["label"]
        self.crumb_var.set(f"首页 / {label} / {item_label}")
        self.title_var.set(item_label)

        for index, (heading, body) in enumerate(item["sections"]):
            tk.Label(
                inner, text=heading,
                font=("Microsoft YaHei UI", 10, "bold"),
                fg=TEXT, bg=CARD_BG,
            ).pack(anchor="w", pady=(0 if index == 0 else 10, 2))
            tk.Label(
                inner, text=body,
                font=("Microsoft YaHei UI", 9),
                fg=MUTED, bg=CARD_BG,
                wraplength=556, justify="left", anchor="w",
            ).pack(anchor="w")


def open_help_browser(
    window: tk.Misc,
    module_key: str | None = None,
    item_index: int | None = None,
) -> HelpBrowser:
    """打开（或复用）该窗口唯一的帮助中心，并跳到指定页。"""
    existing = getattr(window, "_help_browser", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.navigate(module_key, item_index)
                return existing
        except tk.TclError:
            pass
    browser = HelpBrowser(window, module_key, item_index)
    window._help_browser = browser
    return browser
