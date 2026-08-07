from __future__ import annotations

import ctypes
import math
import queue
import threading
import time
from ctypes import wintypes
from typing import Callable, Sequence

from gesture_recognizer import Point


WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_QUIT = 0x0012
LLMHF_INJECTED = 0x00000001
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
HC_ACTION = 0

LRESULT = ctypes.c_ssize_t
ULONG_PTR = wintypes.WPARAM


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = (
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


LowLevelMouseProc = ctypes.WINFUNCTYPE(
    LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)


class GlobalRightButtonGestureHook:
    """Capture right-button strokes while preserving normal right clicks."""

    def __init__(
        self,
        on_stroke: Callable[[Sequence[Point]], None],
        click_tolerance: float = 18.0,
    ) -> None:
        self._on_stroke = on_stroke
        self._click_tolerance = click_tolerance
        self._enabled = True
        self._active = False
        self._points: list[Point] = []
        self._lock = threading.Lock()
        self._hook = None
        self._hook_thread: threading.Thread | None = None
        self._dispatch_thread: threading.Thread | None = None
        self._hook_thread_id = 0
        self._stroke_queue: queue.Queue[tuple[Point, ...] | None] = queue.Queue()
        self._callback = LowLevelMouseProc(self._mouse_proc)
        self._started = threading.Event()
        self._start_error: str | None = None

        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._configure_winapi()

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    @property
    def start_error(self) -> str | None:
        return self._start_error

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = enabled
            if not enabled:
                self._active = False
                self._points.clear()

    def start(self) -> bool:
        if self._hook_thread and self._hook_thread.is_alive():
            return self._hook is not None

        self._started.clear()
        self._start_error = None
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop,
            name="gesture-dispatch",
            daemon=True,
        )
        self._hook_thread = threading.Thread(
            target=self._hook_loop,
            name="mouse-hook",
            daemon=True,
        )
        self._dispatch_thread.start()
        self._hook_thread.start()
        self._started.wait(timeout=3.0)
        return self._hook is not None

    def stop(self) -> None:
        self.set_enabled(False)
        if self._hook_thread_id:
            self._user32.PostThreadMessageW(
                self._hook_thread_id, WM_QUIT, 0, 0
            )
        self._stroke_queue.put(None)
        if self._hook_thread and self._hook_thread.is_alive():
            self._hook_thread.join(timeout=2.0)
        if self._dispatch_thread and self._dispatch_thread.is_alive():
            self._dispatch_thread.join(timeout=2.0)

    def _configure_winapi(self) -> None:
        self._kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
        self._kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        self._kernel32.GetCurrentThreadId.argtypes = ()
        self._kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self._kernel32.GetLastError.argtypes = ()
        self._kernel32.GetLastError.restype = wintypes.DWORD
        self._user32.SetWindowsHookExW.argtypes = (
            ctypes.c_int,
            LowLevelMouseProc,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        )
        self._user32.SetWindowsHookExW.restype = wintypes.HHOOK
        self._user32.CallNextHookEx.argtypes = (
            wintypes.HHOOK,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self._user32.CallNextHookEx.restype = LRESULT
        self._user32.UnhookWindowsHookEx.argtypes = (wintypes.HHOOK,)
        self._user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        self._user32.GetMessageW.argtypes = (
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        )
        self._user32.GetMessageW.restype = wintypes.BOOL
        self._user32.TranslateMessage.argtypes = (ctypes.POINTER(wintypes.MSG),)
        self._user32.DispatchMessageW.argtypes = (ctypes.POINTER(wintypes.MSG),)
        self._user32.PostThreadMessageW.argtypes = (
            wintypes.DWORD,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self._user32.mouse_event.argtypes = (
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ULONG_PTR,
        )

    def _hook_loop(self) -> None:
        self._hook_thread_id = self._kernel32.GetCurrentThreadId()
        module_handle = self._kernel32.GetModuleHandleW(None)
        self._hook = self._user32.SetWindowsHookExW(
            WH_MOUSE_LL, self._callback, module_handle, 0
        )
        if not self._hook:
            error_code = self._kernel32.GetLastError()
            self._start_error = f"无法安装鼠标钩子，Windows 错误码：{error_code}"
            self._started.set()
            return

        self._started.set()
        message = wintypes.MSG()
        try:
            while True:
                result = self._user32.GetMessageW(
                    ctypes.byref(message), None, 0, 0
                )
                if result <= 0:
                    break
                self._user32.TranslateMessage(ctypes.byref(message))
                self._user32.DispatchMessageW(ctypes.byref(message))
        finally:
            if self._hook:
                self._user32.UnhookWindowsHookEx(self._hook)
                self._hook = None
            self._hook_thread_id = 0

    def _mouse_proc(
        self, code: int, message: int, data_pointer: int
    ) -> int:
        try:
            if code != HC_ACTION:
                return self._call_next(code, message, data_pointer)

            data = ctypes.cast(
                data_pointer, ctypes.POINTER(MSLLHOOKSTRUCT)
            ).contents
            if data.flags & LLMHF_INJECTED:
                return self._call_next(code, message, data_pointer)

            with self._lock:
                enabled = self._enabled
            if not enabled:
                return self._call_next(code, message, data_pointer)

            now = time.perf_counter()
            point = Point(float(data.pt.x), float(data.pt.y), now)

            if message == WM_RBUTTONDOWN:
                self._active = True
                self._points = [point]
                return 1

            if message == WM_MOUSEMOVE and self._active:
                if (
                    not self._points
                    or _point_distance(self._points[-1], point) >= 2.5
                ):
                    if len(self._points) < 4096:
                        self._points.append(point)
                return self._call_next(code, message, data_pointer)

            if message == WM_RBUTTONUP and self._active:
                self._active = False
                self._points.append(point)
                points = tuple(self._points)
                self._points.clear()
                if _maximum_displacement(points) <= self._click_tolerance:
                    self._replay_right_click()
                else:
                    self._stroke_queue.put(points)
                return 1
        except Exception:
            self._active = False
            self._points.clear()

        return self._call_next(code, message, data_pointer)

    def _call_next(self, code: int, message: int, data_pointer: int) -> int:
        return int(
            self._user32.CallNextHookEx(
                self._hook, code, message, data_pointer
            )
        )

    def _replay_right_click(self) -> None:
        self._user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        self._user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def _dispatch_loop(self) -> None:
        while True:
            points = self._stroke_queue.get()
            if points is None:
                return
            try:
                self._on_stroke(points)
            except Exception:
                continue


def _point_distance(left: Point, right: Point) -> float:
    return math.hypot(right.x - left.x, right.y - left.y)


def _maximum_displacement(points: Sequence[Point]) -> float:
    if not points:
        return 0.0
    start = points[0]
    return max(_point_distance(start, point) for point in points)
