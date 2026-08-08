from __future__ import annotations

import unittest

from gesture_recognizer import Point
from mouse_hook import (
    WM_LBUTTONDOWN,
    WM_MOUSEMOVE,
    WM_RBUTTONDOWN,
    MouseMetricsTracker,
)


class MouseMetricsTrackerTests(unittest.TestCase):
    def test_counts_buttons_and_movement_distance(self) -> None:
        tracker = MouseMetricsTracker()
        tracker.record(WM_MOUSEMOVE, Point(10, 20, 0.0))
        tracker.record(WM_MOUSEMOVE, Point(13, 24, 0.1))
        tracker.record(WM_LBUTTONDOWN, Point(13, 24, 0.2))
        tracker.record(WM_LBUTTONDOWN, Point(13, 24, 0.3))
        tracker.record(WM_RBUTTONDOWN, Point(13, 24, 0.4))

        metrics = tracker.snapshot()

        self.assertEqual(metrics.left_clicks, 2)
        self.assertEqual(metrics.right_clicks, 1)
        self.assertEqual(metrics.distance_pixels, 5.0)

    def test_reset_clears_all_session_metrics(self) -> None:
        tracker = MouseMetricsTracker()
        tracker.record(WM_MOUSEMOVE, Point(0, 0, 0.0))
        tracker.record(WM_MOUSEMOVE, Point(10, 0, 0.1))
        tracker.record(WM_LBUTTONDOWN, Point(10, 0, 0.2))

        tracker.reset()

        self.assertEqual(tracker.snapshot().left_clicks, 0)
        self.assertEqual(tracker.snapshot().right_clicks, 0)
        self.assertEqual(tracker.snapshot().distance_pixels, 0.0)


if __name__ == "__main__":
    unittest.main()
