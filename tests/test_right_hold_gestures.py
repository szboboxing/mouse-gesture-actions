from __future__ import annotations

import ctypes
import queue
import threading
import unittest
from unittest.mock import Mock

from mouse_hook import (
    HC_ACTION,
    MSLLHOOKSTRUCT,
    WM_LBUTTONDOWN,
    WM_XBUTTONDOWN,
    WM_XBUTTONUP,
    XBUTTON1,
    XBUTTON2,
    GlobalRightButtonActionHook,
    HeldMouseAction,
    MouseMetricsTracker,
    RightHoldGestureState,
    _high_word,
    _signed_high_word,
)


class RightHoldGestureStateTests(unittest.TestCase):
    def test_actions_require_right_button_hold(self) -> None:
        state = RightHoldGestureState()

        self.assertIsNone(state.scroll_up().action)
        self.assertIsNone(state.scroll_down().action)
        self.assertIsNone(state.press_side_button().action)

    def test_scroll_up_copies_immediately(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        decision = state.scroll_up()

        self.assertEqual(decision.action, HeldMouseAction.COPY)

    def test_single_scroll_down_runs_enhanced_paste(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        decision = state.scroll_down()

        self.assertEqual(
            decision.action,
            HeldMouseAction.ENHANCED_PASTE,
        )

    def test_scroll_up_then_down_does_not_run_screenshot(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        first = state.scroll_up()
        second = state.scroll_down()

        self.assertEqual(first.action, HeldMouseAction.COPY)
        self.assertIsNone(second.action)

    def test_scroll_down_then_up_does_not_run_screenshot(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        first = state.scroll_down()
        second = state.scroll_up()

        self.assertEqual(first.action, HeldMouseAction.ENHANCED_PASTE)
        self.assertIsNone(second.action)

    def test_side_button_runs_screenshot(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        decision = state.press_side_button()

        self.assertEqual(decision.action, HeldMouseAction.SCREENSHOT)

    def test_only_one_action_is_committed_per_hold(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        first = state.scroll_down()
        second = state.press_side_button()

        self.assertEqual(first.action, HeldMouseAction.ENHANCED_PASTE)
        self.assertIsNone(second.action)

    def test_right_click_without_action_is_replayed(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        decision = state.release_right()

        self.assertTrue(decision.replay_right_click)
        self.assertIsNone(decision.action)

class FakeUser32:
    def __init__(self, right_button_down: bool = False) -> None:
        self.right_button_down = right_button_down

    def GetAsyncKeyState(self, _key: int) -> int:
        return 0x8000 if self.right_button_down else 0


class SideButtonHookTests(unittest.TestCase):
    def _hook(
        self,
        right_button_down: bool = False,
    ) -> GlobalRightButtonActionHook:
        hook = GlobalRightButtonActionHook.__new__(
            GlobalRightButtonActionHook
        )
        hook._enabled = True
        hook._lock = threading.Lock()
        hook._state = RightHoldGestureState()
        hook._metrics = MouseMetricsTracker()
        hook._suppressed_xbuttons = set()
        hook._action_queue = queue.Queue()
        hook._user32 = FakeUser32(right_button_down)
        hook._call_next = Mock(return_value=73)
        hook._replay_right_click = Mock()
        return hook

    @staticmethod
    def _mouse_event(
        hook: GlobalRightButtonActionHook,
        message: int,
        xbutton: int = 0,
    ) -> int:
        data = MSLLHOOKSTRUCT()
        data.mouseData = xbutton << 16
        return hook._mouse_proc(
            HC_ACTION,
            message,
            ctypes.addressof(data),
        )

    def test_side_buttons_pass_through_without_right_hold(self) -> None:
        for xbutton in (XBUTTON1, XBUTTON2):
            with self.subTest(xbutton=xbutton):
                hook = self._hook()

                down = self._mouse_event(hook, WM_XBUTTONDOWN, xbutton)
                up = self._mouse_event(hook, WM_XBUTTONUP, xbutton)

                self.assertEqual((down, up), (73, 73))
                self.assertEqual(hook._call_next.call_count, 2)
                self.assertTrue(hook._action_queue.empty())

    def test_left_button_always_passes_through(self) -> None:
        hook = self._hook(right_button_down=True)
        hook._state.press_right()

        result = self._mouse_event(hook, WM_LBUTTONDOWN)

        self.assertEqual(result, 73)
        hook._call_next.assert_called_once()
        self.assertTrue(hook._action_queue.empty())

    def test_either_side_button_screenshots_during_right_hold(self) -> None:
        for xbutton in (XBUTTON1, XBUTTON2):
            with self.subTest(xbutton=xbutton):
                hook = self._hook(right_button_down=True)
                hook._state.press_right()

                down = self._mouse_event(hook, WM_XBUTTONDOWN, xbutton)
                action = hook._action_queue.get_nowait()
                up = self._mouse_event(hook, WM_XBUTTONUP, xbutton)

                self.assertEqual((down, up), (1, 1))
                self.assertEqual(action, HeldMouseAction.SCREENSHOT)
                self.assertFalse(hook._suppressed_xbuttons)
                hook._call_next.assert_not_called()

    def test_stale_right_hold_does_not_swallow_side_button(self) -> None:
        hook = self._hook(right_button_down=False)
        hook._state.press_right()

        down = self._mouse_event(hook, WM_XBUTTONDOWN, XBUTTON1)
        up = self._mouse_event(hook, WM_XBUTTONUP, XBUTTON1)

        self.assertEqual((down, up), (73, 73))
        self.assertFalse(hook._state.active)
        self.assertTrue(hook._action_queue.empty())


class MouseDataParsingTests(unittest.TestCase):
    def test_mouse_wheel_delta_is_signed(self) -> None:
        self.assertEqual(_signed_high_word(120 << 16), 120)
        self.assertEqual(_signed_high_word((0x10000 - 120) << 16), -120)

    def test_xbutton_is_read_from_high_word(self) -> None:
        self.assertEqual(_high_word(1 << 16), 1)
        self.assertEqual(_high_word(2 << 16), 2)


if __name__ == "__main__":
    unittest.main()
