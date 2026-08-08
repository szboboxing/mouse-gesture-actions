from __future__ import annotations

import ctypes
import os
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path

import pythoncom
import win32com.client
import win32gui
from win32com.shell import shell, shellcon

from display_controls import DisplayController


KEYEVENTF_KEYUP = 0x0002
GA_ROOT = 2
VK_CONTROL = 0x11
VK_ALT = 0x12
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_C = ord("C")
VK_N = ord("N")
VK_S = ord("S")
VK_V = ord("V")
ENHANCED_PASTE_DELAY_SECONDS = 0.20


@dataclass(frozen=True, slots=True)
class ActionResult:
    success: bool
    message: str
    detail: str = ""


class SystemActions:
    def __init__(self) -> None:
        self._user32 = ctypes.windll.user32
        self._display = DisplayController()
        self._user32.keybd_event.argtypes = (
            ctypes.c_ubyte,
            ctypes.c_ubyte,
            ctypes.c_ulong,
            ctypes.c_size_t,
        )

    def _send_keys(
        self,
        keys: tuple[int, ...],
        action_name: str,
        shortcut_text: str,
    ) -> ActionResult:
        try:
            for virtual_key in keys:
                self._user32.keybd_event(virtual_key, 0, 0, 0)
            for virtual_key in reversed(keys):
                self._user32.keybd_event(
                    virtual_key, 0, KEYEVENTF_KEYUP, 0
                )
            return ActionResult(
                True,
                f"已执行{action_name}",
                shortcut_text,
            )
        except OSError as exc:
            return ActionResult(False, f"{action_name}执行失败", str(exc))

    def copy_selection(self) -> ActionResult:
        return self._send_keys(
            (VK_CONTROL, VK_C),
            "复制",
            "Ctrl+C",
        )

    def capture_screenshot(self) -> ActionResult:
        return self._send_keys(
            (VK_LWIN, VK_SHIFT, VK_S),
            "系统截图",
            "Win+Shift+S",
        )

    def send_custom_shortcut(
        self,
        modifiers: tuple[str, ...],
        key: str,
    ) -> ActionResult:
        modifier_keys = {
            "ctrl": (VK_CONTROL, "Ctrl"),
            "alt": (VK_ALT, "Alt"),
            "shift": (VK_SHIFT, "Shift"),
        }
        selected = {str(modifier).lower() for modifier in modifiers}
        if selected.difference(modifier_keys):
            return ActionResult(
                False,
                "自定义快捷键执行失败",
                "包含不支持的修饰键",
            )

        letter = str(key).upper()
        if len(letter) != 1 or not "A" <= letter <= "Z":
            return ActionResult(
                False,
                "自定义快捷键执行失败",
                "主键必须是 A-Z",
            )

        ordered_modifiers = tuple(
            name for name in modifier_keys if name in selected
        )
        virtual_keys = tuple(
            modifier_keys[name][0] for name in ordered_modifiers
        ) + (ord(letter),)
        shortcut_text = "+".join(
            tuple(modifier_keys[name][1] for name in ordered_modifiers)
            + (letter,)
        )
        return self._send_keys(
            virtual_keys,
            "自定义快捷键",
            shortcut_text,
        )

    def create_folder_and_paste_clipboard(self) -> ActionResult:
        pythoncom.CoInitialize()
        try:
            directory = get_active_explorer_directory()
            if directory is None:
                return ActionResult(
                    False,
                    "增强粘贴未执行",
                    "请先激活文件资源管理器或桌面",
                )

            create_result = self._send_keys(
                (VK_CONTROL, VK_SHIFT, VK_N),
                "新建文件夹",
                "Ctrl+Shift+N",
            )
            if not create_result.success:
                return create_result

            time.sleep(ENHANCED_PASTE_DELAY_SECONDS)
            paste_result = self._send_keys(
                (VK_CONTROL, VK_V),
                "粘贴剪贴板内容",
                "Ctrl+V",
            )
            if not paste_result.success:
                return ActionResult(
                    False,
                    "文件夹已新建，但剪贴板内容粘贴失败",
                    paste_result.detail,
                )
            return ActionResult(
                True,
                "已执行增强粘贴",
                f"已在 {directory} 新建文件夹并粘贴剪贴板内容",
            )
        except (OSError, pythoncom.com_error) as exc:
            return ActionResult(False, "增强粘贴执行失败", str(exc))
        finally:
            pythoncom.CoUninitialize()

    def open_calculator(self) -> ActionResult:
        return self._open_target("calc.exe", "计算器")

    def open_browser(self) -> ActionResult:
        try:
            if not webbrowser.open("https://www.bing.com", new=2):
                return ActionResult(False, "浏览器启动失败", "未找到默认浏览器")
            return ActionResult(True, "已启动浏览器", "使用系统默认浏览器")
        except (OSError, webbrowser.Error) as exc:
            return ActionResult(False, "浏览器启动失败", str(exc))

    def open_media_player(self) -> ActionResult:
        errors: list[str] = []
        for target in ("mswindowsmusic:", "wmplayer.exe"):
            result = self._open_target(target, "媒体播放器")
            if result.success:
                return result
            errors.append(result.detail)
        return ActionResult(
            False,
            "媒体播放器启动失败",
            "；".join(item for item in errors if item),
        )

    def adjust_brightness(self, direction: int) -> ActionResult:
        result = self._display.adjust_brightness(direction)
        if not result.success:
            return ActionResult(False, "亮度调节失败", result.detail)
        direction_text = "提高" if direction > 0 else "降低"
        return ActionResult(
            True,
            f"已{direction_text}亮度至 {result.value}%",
            result.detail,
        )

    def adjust_contrast(self, direction: int) -> ActionResult:
        result = self._display.adjust_contrast(direction)
        if not result.success:
            return ActionResult(False, "对比度调节失败", result.detail)
        direction_text = "提高" if direction > 0 else "降低"
        return ActionResult(
            True,
            f"已{direction_text}对比度至 {result.value}%",
            result.detail,
        )

    def open_custom_target(
        self,
        target: str,
        action_name: str,
    ) -> ActionResult:
        target = os.path.expandvars(target.strip())
        if not target:
            return ActionResult(
                False,
                f"{action_name}尚未配置",
                "请右键单击该按钮编辑名称和打开目标",
            )
        return self._open_target(target, action_name)

    @staticmethod
    def _open_target(target: str, action_name: str) -> ActionResult:
        try:
            os.startfile(target)
            return ActionResult(True, f"已启动{action_name}", target)
        except OSError as exc:
            return ActionResult(False, f"{action_name}启动失败", str(exc))


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
