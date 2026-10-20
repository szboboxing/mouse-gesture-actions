"""打包与内网安全相关的静态守卫测试。

这些用例不启动界面，只读取源码文本，用来守住两条已经确认过的结论：

1. 单文件包里不该再出现确认无用的 stdlib 依赖链与 Tcl/Tk 可选包；
2. 运行时源码不该引入任何联网或起子进程的能力（内网离线要求）。
"""

from __future__ import annotations

import ast
from pathlib import Path

import unittest


ROOT = Path(__file__).resolve().parent.parent
RUNTIME_MODULES = (
    "main.py",
    "app.py",
    "actions.py",
    "radial_menu.py",
    "settings.py",
    "themes.py",
    "clipboard_history.py",
    "display_controls.py",
    "help_browser.py",
    "mouse_hook.py",
)
SPEC_PATH = ROOT / "mouse_gesture_actions.spec"

# Tcl/Tk 里核对过可以安全剔除的可选包（详见 spec 中的注释）。
EXPECTED_PRUNED = (
    "_tcl_data/tzdata/",
    "_tcl_data/http1.0/",
    "tcl8/8.6/http",
    "tcl8/8.5/tcltest",
    "tcl8/8.4/platform",
)
# 必须保留：少了这些 Tk 会在启动或弹窗时直接报错。
EXPECTED_KEPT = ("msgcat", "opt0.4", "encoding", "msgs")

# 确认无用的 stdlib 依赖链，全部写进 spec 的 excludes。
EXPECTED_EXCLUDES = (
    "statistics",
    "decimal",
    "fractions",
    "_pydecimal",
    "webbrowser",
    "subprocess",
    "signal",
    "selectors",
    "shlex",
    "lzma",
    "bz2",
    "tarfile",
    "gzip",
    "email",
    "importlib.metadata",
    "csv",
)

# 内网离线工具不允许出现的导入（urllib.parse 只做字符串解析，不联网）。
FORBIDDEN_IMPORTS = {
    "socket",
    "_socket",
    "ssl",
    "subprocess",
    "webbrowser",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "nntplib",
    "telnetlib",
    "http",
    "urllib.request",
    "multiprocessing",
    "asyncio",
    "requests",
    "urllib3",
}


class BuildSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec_text = SPEC_PATH.read_text(encoding="utf-8")

    def test_spec_prunes_unused_tcl_packages(self) -> None:
        for prefix in EXPECTED_PRUNED:
            self.assertIn(f'"{prefix}"', self.spec_text, prefix)

    def test_spec_keeps_required_tcl_packages(self) -> None:
        for name in EXPECTED_KEPT:
            self.assertNotIn(
                f'"{name}',
                self.spec_text,
                f"{name} 是 Tcl/Tk 运行时必需的，不能被剔除",
            )

    def test_spec_excludes_dead_stdlib_chain(self) -> None:
        for name in EXPECTED_EXCLUDES:
            self.assertIn(f'"{name}",', self.spec_text, name)

    def test_spec_ships_the_wheel_assets(self) -> None:
        # 壁纸与立体图标都必须整目录随包，否则运行时只能回退成纯色/平面字形。
        self.assertIn('("assets/wallpapers", "assets/wallpapers")', self.spec_text)
        self.assertIn('("assets/icons", "assets/icons")', self.spec_text)

    def test_spec_prints_are_ascii_only(self) -> None:
        # Runner 的 PowerShell 可能按 cp1252 输出，spec 里的中文日志会抛
        # UnicodeEncodeError 并让 PyInstaller 中途退出（V2.7.2 首次 CI 就是这样失败的）。
        for node in ast.walk(ast.parse(self.spec_text)):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        self.assertTrue(
                            arg.value.isascii(),
                            f"spec 第 {node.lineno} 行 print 含非 ASCII 文本",
                        )
                    if isinstance(arg, ast.JoinedStr):
                        for value in arg.values:
                            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                                self.assertTrue(
                                    value.value.isascii(),
                                    f"spec 第 {node.lineno} 行 f-string 含非 ASCII 文本",
                                )


class OfflineSafetyTests(unittest.TestCase):
    def _top_level_imports(self, filename: str) -> set[str]:
        tree = ast.parse(
            (ROOT / filename).read_text(encoding="utf-8"), filename=filename
        )
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module)
        return found

    def test_runtime_modules_never_touch_the_network(self) -> None:
        for filename in RUNTIME_MODULES:
            with self.subTest(module=filename):
                banned = self._top_level_imports(filename) & FORBIDDEN_IMPORTS
                self.assertEqual(banned, set())

    def test_browser_tile_uses_the_shell_not_the_webbrowser_module(self) -> None:
        # os.startfile 是 Windows 上的 ShellExecute，等价于 webbrowser 的最终动作，
        # 但不把 subprocess/signal/selectors 整条依赖链拖进单文件包。
        source = (ROOT / "actions.py").read_text(encoding="utf-8")
        self.assertIn('os.startfile("about:blank")', source)


if __name__ == "__main__":
    unittest.main()
