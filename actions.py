from __future__ import annotations

import ctypes
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pythoncom
import win32com.client
import win32gui
from win32com.shell import shell, shellcon


KEYEVENTF_KEYUP = 0x0002
GA_ROOT = 2

VK_ALIASES = {
    "CTRL": 0x11,
    "CONTROL": 0x11,
    "SHIFT": 0x10,
    "ALT": 0x12,
    "WIN": 0x5B,
    "WINDOWS": 0x5B,
    "SPACE": 0x20,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "TAB": 0x09,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "BACKSPACE": 0x08,
    "DELETE": 0x2E,
    "INSERT": 0x2D,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
}

for _function_number in range(1, 25):
    VK_ALIASES[f"F{_function_number}"] = 0x6F + _function_number


@dataclass(frozen=True, slots=True)
class ActionResult:
    success: bool
    message: str
    detail: str = ""


class SystemActions:
    def __init__(self) -> None:
        self._user32 = ctypes.windll.user32
        self._user32.keybd_event.argtypes = (
            ctypes.c_ubyte,
            ctypes.c_ubyte,
            ctypes.c_ulong,
            ctypes.c_size_t,
        )

    def send_shortcut(self, shortcut: str, action_name: str) -> ActionResult:
        try:
            keys = parse_shortcut(shortcut)
        except ValueError as exc:
            return ActionResult(False, f"{action_name}未执行", str(exc))

        try:
            for virtual_key in keys:
                self._user32.keybd_event(virtual_key, 0, 0, 0)
            for virtual_key in reversed(keys):
                self._user32.keybd_event(
                    virtual_key, 0, KEYEVENTF_KEYUP, 0
                )
            return ActionResult(True, f"已执行{action_name}", shortcut)
        except OSError as exc:
            return ActionResult(False, f"{action_name}执行失败", str(exc))

    def create_folder_in_active_directory(self) -> ActionResult:
        pythoncom.CoInitialize()
        try:
            directory = get_active_explorer_directory()
            if directory is None:
                return ActionResult(
                    False,
                    "未新建文件夹",
                    "请先激活文件资源管理器或桌面，再连续完成两次快划",
                )

            target = _next_folder_path(directory)
            target.mkdir()
            return ActionResult(True, "已新建文件夹", str(target))
        except (OSError, pythoncom.com_error) as exc:
            return ActionResult(False, "新建文件夹失败", str(exc))
        finally:
            pythoncom.CoUninitialize()


def parse_shortcut(shortcut: str) -> tuple[int, ...]:
    tokens = [
        token.strip().upper()
        for token in re.split(r"\s*\+\s*", shortcut.strip())
        if token.strip()
    ]
    if not tokens:
        raise ValueError("快捷键不能为空")
    if len(tokens) > 5:
        raise ValueError("快捷键最多包含 5 个按键")

    virtual_keys: list[int] = []
    for token in tokens:
        if token in VK_ALIASES:
            virtual_key = VK_ALIASES[token]
        elif len(token) == 1 and ("A" <= token <= "Z" or "0" <= token <= "9"):
            virtual_key = ord(token)
        else:
            raise ValueError(f"不支持的按键：{token}")
        if virtual_key in virtual_keys:
            raise ValueError(f"快捷键包含重复按键：{token}")
        virtual_keys.append(virtual_key)

    if len(virtual_keys) == 1 and virtual_keys[0] in {
        VK_ALIASES["CTRL"],
        VK_ALIASES["SHIFT"],
        VK_ALIASES["ALT"],
        VK_ALIASES["WIN"],
    }:
        raise ValueError("快捷键不能只有修饰键")
    return tuple(virtual_keys)


def get_active_explorer_directory() -> Path | None:
    foreground = win32gui.GetForegroundWindow()
    root_window = win32gui.GetAncestor(foreground, GA_ROOT)
    class_name = win32gui.GetClassName(root_window)

    if class_name in {"Progman", "WorkerW"}:
        desktop = shell.SHGetFolderPath(
            0, shellcon.CSIDL_DESKTOPDIRECTORY, None, 0
        )
        return Path(desktop)

    if class_name not in {"CabinetWClass", "ExploreWClass"}:
        return None

    shell_application = win32com.client.Dispatch("Shell.Application")
    for window in shell_application.Windows():
        try:
            if int(window.HWND) != root_window:
                continue
            path_text = str(window.Document.Folder.Self.Path)
            path = Path(path_text)
            return path if path.is_dir() else None
        except (AttributeError, TypeError, pythoncom.com_error):
            continue
    return None


def _next_folder_path(directory: Path) -> Path:
    base = directory / "新建文件夹"
    if not base.exists():
        return base

    for number in range(2, 10_000):
        candidate = directory / f"新建文件夹 ({number})"
        if not candidate.exists():
            return candidate
    return directory / f"新建文件夹 ({time.strftime('%Y%m%d-%H%M%S')})"
