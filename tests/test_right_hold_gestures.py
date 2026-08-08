from __future__ import annotations

import unittest

from mouse_hook import (
    HeldMouseAction,
    RightHoldGestureState,
    _high_word,
    _signed_high_word,
)


class RightHoldGestureStateTests(unittest.TestCase):
    def test_actions_require_right_button_hold(self) -> None:
        state = RightHoldGestureState()

        self.assertFalse(state.scroll_up(1.0).schedule_copy)
        self.assertIsNone(state.scroll_down(1.1).action)
        self.assertIsNone(state.press_xbutton1().action)

    def test_single_scroll_up_copies_after_time_window(self) -> None:
        state = RightHoldGestureState(combo_interval_ms=250)
        state.press_right()

        pending = state.scroll_up(10.0)
        early = state.copy_timeout(10.20)
        completed = state.copy_timeout(10.25)

        self.assertTrue(pending.schedule_copy)
        self.assertIsNone(early.action)
        self.assertEqual(completed.action, HeldMouseAction.COPY)

    def test_release_flushes_pending_single_scroll_up_as_copy(self) -> None:
        state = RightHoldGestureState()
        state.press_right()
        state.scroll_up(5.0)

        released = state.release_right()

        self.assertEqual(released.action, HeldMouseAction.COPY)
        self.assertFalse(released.replay_right_click)
        self.assertFalse(state.active)

    def test_single_scroll_down_runs_enhanced_paste(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        decision = state.scroll_down(2.0)

        self.assertEqual(
            decision.action,
            HeldMouseAction.ENHANCED_PASTE,
        )

    def test_scroll_up_then_down_inside_window_runs_screenshot(self) -> None:
        state = RightHoldGestureState(combo_interval_ms=250)
        state.press_right()
        state.scroll_up(20.0)

        decision = state.scroll_down(20.24)

        self.assertEqual(decision.action, HeldMouseAction.SCREENSHOT)
        self.assertFalse(state.pending_copy)

    def test_scroll_up_then_down_outside_window_commits_copy(self) -> None:
        state = RightHoldGestureState(combo_interval_ms=250)
        state.press_right()
        state.scroll_up(20.0)

        decision = state.scroll_down(20.251)

        self.assertEqual(decision.action, HeldMouseAction.COPY)
        self.assertFalse(state.pending_copy)

    def test_scroll_down_then_up_does_not_run_screenshot(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        first = state.scroll_down(30.0)
        second = state.scroll_up(30.1)

        self.assertEqual(first.action, HeldMouseAction.ENHANCED_PASTE)
        self.assertIsNone(second.action)
        self.assertFalse(second.schedule_copy)

    def test_xbutton1_runs_screenshot_and_cancels_pending_copy(self) -> None:
        state = RightHoldGestureState()
        state.press_right()
        state.scroll_up(40.0)

        decision = state.press_xbutton1()

        self.assertEqual(decision.action, HeldMouseAction.SCREENSHOT)
        self.assertFalse(state.pending_copy)

    def test_only_one_action_is_committed_per_hold(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        first = state.scroll_down(50.0)
        second = state.press_xbutton1()

        self.assertEqual(first.action, HeldMouseAction.ENHANCED_PASTE)
        self.assertIsNone(second.action)

    def test_right_click_without_action_is_replayed(self) -> None:
        state = RightHoldGestureState()
        state.press_right()

        decision = state.release_right()

        self.assertTrue(decision.replay_right_click)
        self.assertIsNone(decision.action)

    def test_combo_interval_is_limited_to_200_300_ms(self) -> None:
        with self.assertRaises(ValueError):
            RightHoldGestureState(199)
        with self.assertRaises(ValueError):
            RightHoldGestureState(301)
        RightHoldGestureState(200)
        RightHoldGestureState(300)


class MouseDataParsingTests(unittest.TestCase):
    def test_mouse_wheel_delta_is_signed(self) -> None:
        self.assertEqual(_signed_high_word(120 << 16), 120)
        self.assertEqual(_signed_high_word((0x10000 - 120) << 16), -120)

    def test_xbutton_is_read_from_high_word(self) -> None:
        self.assertEqual(_high_word(1 << 16), 1)
        self.assertEqual(_high_word(2 << 16), 2)


if __name__ == "__main__":
    unittest.main()
