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
    WM_LBUTTONUP,
    WM_MBUTTONDOWN,
    WM_MBUTTONUP,
    WM_MOUSEWHEEL,
    WM_RBUTTONDOWN,
    WM_RBUTTONUP,
    WM_XBUTTONDOWN,
    WM_XBUTTONUP,
    XBUTTON1,
    XBUTTON2,
    GlobalRightButtonActionHook,
    HeldMouseAction,
    MouseControl,
    MouseMetricsTracker,
    MouseTestEvent,
    RightHoldGestureState,
    _decode_mouse_test_event,
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
        hook._test_mode = False
        hook._on_test_event = Mock()
        hook._lock = threading.Lock()
        hook._state = RightHoldGestureState()
        hook._metrics = MouseMetricsTracker()
        hook._screenshot_xbuttons = {XBUTTON1, XBUTTON2}
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
        high_word: int = 0,
    ) -> int:
        data = MSLLHOOKSTRUCT()
        data.mouseData = high_word << 16
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

    def test_only_confirmed_side_buttons_trigger_screenshot(self) -> None:
        hook = self._hook(right_button_down=True)
        hook.set_screenshot_side_buttons((MouseControl.XBUTTON1,))
        hook._state.press_right()

        unconfirmed_down = self._mouse_event(
            hook,
            WM_XBUTTONDOWN,
            XBUTTON2,
        )
        unconfirmed_up = self._mouse_event(
            hook,
            WM_XBUTTONUP,
            XBUTTON2,
        )
        confirmed_down = self._mouse_event(
            hook,
            WM_XBUTTONDOWN,
            XBUTTON1,
        )
        confirmed_up = self._mouse_event(
            hook,
            WM_XBUTTONUP,
            XBUTTON1,
        )

        self.assertEqual(
            (
                unconfirmed_down,
                unconfirmed_up,
                confirmed_down,
                confirmed_up,
            ),
            (73, 73, 1, 1),
        )
        self.assertEqual(
            hook._action_queue.get_nowait(),
            HeldMouseAction.SCREENSHOT,
        )
        self.assertTrue(hook._action_queue.empty())

    def test_stale_right_hold_does_not_swallow_side_button(self) -> None:
        hook = self._hook(right_button_down=False)
        hook._state.press_right()

        down = self._mouse_event(hook, WM_XBUTTONDOWN, XBUTTON1)
        up = self._mouse_event(hook, WM_XBUTTONUP, XBUTTON1)

        self.assertEqual((down, up), (73, 73))
        self.assertFalse(hook._state.active)
        self.assertTrue(hook._action_queue.empty())

    def test_test_mode_passes_every_control_through(self) -> None:
        hook = self._hook(right_button_down=True)
        hook.set_enabled(False)
        hook.set_test_mode(True)
        events = (
            (WM_LBUTTONDOWN, 0),
            (WM_LBUTTONUP, 0),
            (WM_RBUTTONDOWN, 0),
            (WM_RBUTTONUP, 0),
            (WM_MBUTTONDOWN, 0),
            (WM_MBUTTONUP, 0),
            (WM_MOUSEWHEEL, 120),
            (WM_MOUSEWHEEL, 0x10000 - 120),
            (WM_XBUTTONDOWN, XBUTTON1),
            (WM_XBUTTONUP, XBUTTON1),
            (WM_XBUTTONDOWN, XBUTTON2),
            (WM_XBUTTONUP, XBUTTON2),
        )

        results = [
            self._mouse_event(hook, message, high_word)
            for message, high_word in events
        ]

        self.assertEqual(results, [73] * len(events))
        self.assertEqual(hook._call_next.call_count, len(events))
        self.assertEqual(hook._on_test_event.call_count, len(events))
        self.assertTrue(hook._action_queue.empty())
        self.assertFalse(hook._state.active)

    def test_leaving_test_mode_restores_right_hold_actions(self) -> None:
        hook = self._hook(right_button_down=True)
        hook.set_test_mode(True)
        test_result = self._mouse_event(
            hook,
            WM_XBUTTONDOWN,
            XBUTTON1,
        )

        hook.set_test_mode(False)
        hook._state.press_right()
        action_result = self._mouse_event(
            hook,
            WM_XBUTTONDOWN,
            XBUTTON1,
        )

        self.assertEqual(test_result, 73)
        self.assertEqual(action_result, 1)
        self.assertEqual(
            hook._action_queue.get_nowait(),
            HeldMouseAction.SCREENSHOT,
        )


class MouseDataParsingTests(unittest.TestCase):
    def test_mouse_wheel_delta_is_signed(self) -> None:
        self.assertEqual(_signed_high_word(120 << 16), 120)
        self.assertEqual(_signed_high_word((0x10000 - 120) << 16), -120)

    def test_xbutton_is_read_from_high_word(self) -> None:
        self.assertEqual(_high_word(1 << 16), 1)
        self.assertEqual(_high_word(2 << 16), 2)

    def test_mouse_test_button_events_are_decoded(self) -> None:
        cases = (
            (WM_LBUTTONDOWN, MouseControl.LEFT, True),
            (WM_LBUTTONUP, MouseControl.LEFT, False),
            (WM_RBUTTONDOWN, MouseControl.RIGHT, True),
            (WM_RBUTTONUP, MouseControl.RIGHT, False),
            (WM_MBUTTONDOWN, MouseControl.MIDDLE, True),
            (WM_MBUTTONUP, MouseControl.MIDDLE, False),
            (WM_XBUTTONDOWN, MouseControl.XBUTTON1, True),
            (WM_XBUTTONUP, MouseControl.XBUTTON1, False),
        )
        for message, control, pressed in cases:
            with self.subTest(message=message, control=control):
                high_word = XBUTTON1 if "xbutton" in control.value else 0
                event = _decode_mouse_test_event(
                    message,
                    high_word << 16,
                )
                self.assertEqual(event, MouseTestEvent(control, pressed))

        for message, pressed in (
            (WM_XBUTTONDOWN, True),
            (WM_XBUTTONUP, False),
        ):
            with self.subTest(message=message, control=MouseControl.XBUTTON2):
                event = _decode_mouse_test_event(
                    message,
                    XBUTTON2 << 16,
                )
                self.assertEqual(
                    event,
                    MouseTestEvent(MouseControl.XBUTTON2, pressed),
                )

    def test_mouse_test_wheel_directions_are_decoded(self) -> None:
        self.assertEqual(
            _decode_mouse_test_event(WM_MOUSEWHEEL, 120 << 16),
            MouseTestEvent(MouseControl.WHEEL_UP, True),
        )
        self.assertEqual(
            _decode_mouse_test_event(
                WM_MOUSEWHEEL,
                (0x10000 - 120) << 16,
            ),
            MouseTestEvent(MouseControl.WHEEL_DOWN, True),
        )


if __name__ == "__main__":
    unittest.main()
