from __future__ import annotations

import ctypes
import math
import queue
import threading
import time
from dataclasses import dataclass
from ctypes import wintypes
from enum import Enum
from typing import Callable, Iterable


WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
WM_QUIT = 0x0012
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002
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


class HeldMouseAction(str, Enum):
    COPY = "copy"
    ENHANCED_PASTE = "paste"
    SCREENSHOT = "screenshot"


class MouseControl(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    WHEEL_UP = "wheel_up"
    WHEEL_DOWN = "wheel_down"
    XBUTTON1 = "xbutton1"
    XBUTTON2 = "xbutton2"


@dataclass(frozen=True, slots=True)
class MouseTestEvent:
    control: MouseControl
    pressed: bool


@dataclass(frozen=True, slots=True)
class KeyboardMappingAction:
    mapping_index: int


@dataclass(frozen=True, slots=True)
class StateDecision:
    action: HeldMouseAction | None = None
    replay_right_click: bool = False


class RightHoldGestureState:
    """Pure state machine for actions performed while right is held."""

    def __init__(self) -> None:
        self._active = False
        self._action_committed = False

    @property
    def active(self) -> bool:
        return self._active

    def press_right(self) -> None:
        self._active = True
        self._action_committed = False

    def scroll_up(self) -> StateDecision:
        if not self._active or self._action_committed:
            return StateDecision()
        self._action_committed = True
        return StateDecision(action=HeldMouseAction.COPY)

    def scroll_down(self) -> StateDecision:
        if not self._active or self._action_committed:
            return StateDecision()
        self._action_committed = True
        return StateDecision(action=HeldMouseAction.ENHANCED_PASTE)

    def press_side_button(self) -> StateDecision:
        if not self._active or self._action_committed:
            return StateDecision()
        self._action_committed = True
        return StateDecision(action=HeldMouseAction.SCREENSHOT)

    def release_right(self) -> StateDecision:
        if not self._active:
            return StateDecision()

        if not self._action_committed:
            decision = StateDecision(replay_right_click=True)
        else:
            decision = StateDecision()
        self.cancel()
        return decision

    def cancel(self) -> None:
        self._active = False
        self._action_committed = False


@dataclass(frozen=True, slots=True)
class MousePoint:
    x: float
    y: float
    timestamp: float


@dataclass(frozen=True, slots=True)
class MouseMetrics:
    left_clicks: int = 0
    right_clicks: int = 0
    distance_pixels: float = 0.0


class MouseMetricsTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._left_clicks = 0
        self._right_clicks = 0
        self._distance_pixels = 0.0
        self._last_point: MousePoint | None = None

    def record(self, message: int, point: MousePoint) -> None:
        with self._lock:
            if message == WM_LBUTTONDOWN:
                self._left_clicks += 1
            elif message == WM_RBUTTONDOWN:
                self._right_clicks += 1
            elif message == WM_MOUSEMOVE:
                if self._last_point is not None:
                    self._distance_pixels += _point_distance(
                        self._last_point, point
                    )
                self._last_point = point

    def snapshot(self) -> MouseMetrics:
        with self._lock:
            return MouseMetrics(
                self._left_clicks,
                self._right_clicks,
                self._distance_pixels,
            )

    def reset(self) -> None:
        with self._lock:
            self._left_clicks = 0
            self._right_clicks = 0
            self._distance_pixels = 0.0
            self._last_point = None


class GlobalRightButtonActionHook:
    """Capture right-held wheel and side-button actions."""

    def __init__(
        self,
        on_action: Callable[
            [HeldMouseAction | KeyboardMappingAction],
            None,
        ],
        on_test_event: Callable[[MouseTestEvent], None] | None = None,
    ) -> None:
        self._on_action = on_action
        self._on_test_event = on_test_event
        self._enabled = True
        self._test_mode = False
        self._lock = threading.Lock()
        self._state = RightHoldGestureState()
        self._metrics = MouseMetricsTracker()
        self._screenshot_xbuttons = {XBUTTON1, XBUTTON2}
        self._keyboard_mappings: dict[int, int] = {}
        self._suppressed_xbuttons: set[int] = set()
        self._right_button_down = False
        self._hook = None
        self._hook_thread: threading.Thread | None = None
        self._dispatch_thread: threading.Thread | None = None
        self._hook_thread_id = 0
        self._action_queue: queue.Queue[
            HeldMouseAction | KeyboardMappingAction | None
        ] = queue.Queue()
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
                self._state.cancel()
                self._suppressed_xbuttons.clear()
                self._right_button_down = False

    def set_test_mode(self, enabled: bool) -> None:
        with self._lock:
            self._test_mode = enabled
            self._state.cancel()
            self._suppressed_xbuttons.clear()
            self._right_button_down = False

    def set_screenshot_side_buttons(
        self,
        controls: Iterable[str | MouseControl],
    ) -> None:
        mapping = {
            MouseControl.XBUTTON1.value: XBUTTON1,
            MouseControl.XBUTTON2.value: XBUTTON2,
        }
        configured: set[int] = set()
        for control in controls:
            value = getattr(control, "value", control)
            xbutton = mapping.get(value)
            if xbutton is not None:
                configured.add(xbutton)
        with self._lock:
            self._screenshot_xbuttons = configured
            self._state.cancel()
            self._suppressed_xbuttons.clear()
            self._right_button_down = False

    def set_keyboard_mappings(
        self,
        mappings: Iterable[tuple[str | MouseControl, int]],
    ) -> None:
        xbuttons = {
            MouseControl.XBUTTON1.value: XBUTTON1,
            MouseControl.XBUTTON2.value: XBUTTON2,
        }
        configured: dict[int, int] = {}
        for control, mapping_index in mappings:
            value = getattr(control, "value", control)
            xbutton = xbuttons.get(value)
            if xbutton is not None:
                configured[xbutton] = int(mapping_index)
        with self._lock:
            self._keyboard_mappings = configured
            self._suppressed_xbuttons.clear()

    def snapshot_metrics(self) -> MouseMetrics:
        return self._metrics.snapshot()

    def reset_metrics(self) -> None:
        self._metrics.reset()

    def start(self) -> bool:
        if self._hook_thread and self._hook_thread.is_alive():
            return self._hook is not None

        self._started.clear()
        self._start_error = None
        if not self._dispatch_thread or not self._dispatch_thread.is_alive():
            self._dispatch_thread = threading.Thread(
                target=self._dispatch_loop,
                name="mouse-action-dispatch",
                daemon=True,
            )
            self._dispatch_thread.start()
        self._hook_thread = threading.Thread(
            target=self._hook_loop,
            name="mouse-hook",
            daemon=True,
        )
        self._hook_thread.start()
        self._started.wait(timeout=3.0)
        return self._hook is not None

    def stop(self) -> None:
        self.set_enabled(False)
        hook_to_remove = self._hook
        if hook_to_remove:
            if self._user32.UnhookWindowsHookEx(hook_to_remove):
                self._hook = None
        if self._hook_thread_id:
            self._user32.PostThreadMessageW(
                self._hook_thread_id, WM_QUIT, 0, 0
            )
        self._action_queue.put(None)
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
            injected_xbutton = (
                data.flags & LLMHF_INJECTED
                and message in (WM_XBUTTONDOWN, WM_XBUTTONUP)
            )
            if data.flags & LLMHF_INJECTED and not injected_xbutton:
                return self._call_next(code, message, data_pointer)

            now = time.perf_counter()
            point = MousePoint(float(data.pt.x), float(data.pt.y), now)
            self._metrics.record(message, point)

            test_event = _decode_mouse_test_event(message, data.mouseData)
            with self._lock:
                test_mode = self._test_mode
            if test_mode:
                if test_event is not None and self._on_test_event is not None:
                    self._on_test_event(test_event)
                return self._call_next(code, message, data_pointer)

            action: HeldMouseAction | KeyboardMappingAction | None = None
            replay_right_click = False
            consume = False
            with self._lock:
                if not self._enabled:
                    return self._call_next(code, message, data_pointer)

                if message == WM_RBUTTONDOWN:
                    self._right_button_down = True
                    self._state.press_right()
                    consume = True
                elif message == WM_MOUSEWHEEL and self._state.active:
                    delta = _signed_high_word(data.mouseData)
                    if delta > 0:
                        action = self._state.scroll_up().action
                    elif delta < 0:
                        action = self._state.scroll_down().action
                    consume = delta != 0
                elif message == WM_XBUTTONDOWN:
                    xbutton = _high_word(data.mouseData)
                    if xbutton in (XBUTTON1, XBUTTON2):
                        right_button_down = self._right_button_down
                        if (
                            xbutton in self._screenshot_xbuttons
                            and self._state.active
                            and right_button_down
                        ):
                            action = self._state.press_side_button().action
                            self._suppressed_xbuttons.add(xbutton)
                            consume = True
                        elif xbutton in self._suppressed_xbuttons:
                            consume = True
                        else:
                            if self._state.active and not right_button_down:
                                self._state.cancel()
                            mapping_index = self._keyboard_mappings.get(
                                xbutton
                            )
                            if (
                                mapping_index is not None
                                and not right_button_down
                            ):
                                action = KeyboardMappingAction(mapping_index)
                                self._suppressed_xbuttons.add(xbutton)
                                consume = True
                elif message == WM_XBUTTONUP:
                    xbutton = _high_word(data.mouseData)
                    if xbutton in self._suppressed_xbuttons:
                        self._suppressed_xbuttons.remove(xbutton)
                        consume = True
                elif message == WM_RBUTTONUP:
                    self._right_button_down = False
                    if self._state.active:
                        decision = self._state.release_right()
                        action = decision.action
                        replay_right_click = decision.replay_right_click
                        consume = True

            if action is not None:
                self._action_queue.put(action)
            if replay_right_click:
                self._replay_right_click()
            if consume:
                return 1
        except Exception:
            with self._lock:
                self._state.cancel()
                self._suppressed_xbuttons.clear()
                self._right_button_down = False

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
            action = self._action_queue.get()
            if action is None:
                return
            try:
                self._on_action(action)
            except Exception:
                continue


def _high_word(value: int) -> int:
    return (int(value) >> 16) & 0xFFFF


def _signed_high_word(value: int) -> int:
    word = _high_word(value)
    return word - 0x10000 if word & 0x8000 else word


def _decode_mouse_test_event(
    message: int,
    mouse_data: int,
) -> MouseTestEvent | None:
    simple_events = {
        WM_LBUTTONDOWN: (MouseControl.LEFT, True),
        WM_LBUTTONUP: (MouseControl.LEFT, False),
        WM_RBUTTONDOWN: (MouseControl.RIGHT, True),
        WM_RBUTTONUP: (MouseControl.RIGHT, False),
        WM_MBUTTONDOWN: (MouseControl.MIDDLE, True),
        WM_MBUTTONUP: (MouseControl.MIDDLE, False),
    }
    if message in simple_events:
        control, pressed = simple_events[message]
        return MouseTestEvent(control, pressed)

    if message == WM_MOUSEWHEEL:
        delta = _signed_high_word(mouse_data)
        if delta > 0:
            return MouseTestEvent(MouseControl.WHEEL_UP, True)
        if delta < 0:
            return MouseTestEvent(MouseControl.WHEEL_DOWN, True)
        return None

    if message in (WM_XBUTTONDOWN, WM_XBUTTONUP):
        xbutton = _high_word(mouse_data)
        control = {
            XBUTTON1: MouseControl.XBUTTON1,
            XBUTTON2: MouseControl.XBUTTON2,
        }.get(xbutton)
        if control is not None:
            return MouseTestEvent(control, message == WM_XBUTTONDOWN)
    return None


def _point_distance(left: MousePoint, right: MousePoint) -> float:
    return math.hypot(right.x - left.x, right.y - left.y)
