from __future__ import annotations

import math
import unittest

from gesture_controller import ActionKind, GestureController
from gesture_recognizer import GestureKind, GestureRecognizer, Point


def make_circle(direction: int) -> list[Point]:
    points = []
    for index in range(49):
        angle = direction * math.tau * index / 48
        points.append(
            Point(
                300 + math.cos(angle) * 90,
                260 + math.sin(angle) * 78,
                index * 0.018,
            )
        )
    return points


def make_line(
    start: tuple[float, float],
    end: tuple[float, float],
    duration: float = 0.30,
    timestamp_offset: float = 0.0,
) -> list[Point]:
    points = []
    for index in range(16):
        progress = index / 15
        points.append(
            Point(
                start[0] + (end[0] - start[0]) * progress,
                start[1] + (end[1] - start[1]) * progress,
                timestamp_offset + duration * progress,
            )
        )
    return points


class GestureRecognizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.recognizer = GestureRecognizer("标准")

    def test_counterclockwise_circle_is_left_circle(self) -> None:
        result = self.recognizer.recognize(make_circle(-1))
        self.assertEqual(result.kind, GestureKind.CIRCLE_LEFT)
        self.assertGreater(result.confidence, 0.75)

    def test_clockwise_circle_is_right_circle(self) -> None:
        result = self.recognizer.recognize(make_circle(1))
        self.assertEqual(result.kind, GestureKind.CIRCLE_RIGHT)
        self.assertGreater(result.confidence, 0.75)

    def test_check_mark(self) -> None:
        points = [
            Point(100, 100, 0.00),
            Point(112, 116, 0.04),
            Point(126, 134, 0.08),
            Point(140, 151, 0.12),
            Point(156, 130, 0.16),
            Point(178, 104, 0.20),
            Point(205, 70, 0.24),
        ]
        result = self.recognizer.recognize(points)
        self.assertEqual(result.kind, GestureKind.CHECK)

    def test_fast_up_right_swipe(self) -> None:
        result = self.recognizer.recognize(
            make_line((100, 300), (270, 130))
        )
        self.assertEqual(result.kind, GestureKind.SWIPE_UP_RIGHT)

    def test_fast_down_left_swipe(self) -> None:
        result = self.recognizer.recognize(
            make_line((300, 100), (120, 280))
        )
        self.assertEqual(result.kind, GestureKind.SWIPE_DOWN_LEFT)

    def test_slow_swipe_is_unknown(self) -> None:
        result = self.recognizer.recognize(
            make_line((100, 300), (270, 130), duration=1.2)
        )
        self.assertEqual(result.kind, GestureKind.UNKNOWN)


class GestureControllerTests(unittest.TestCase):
    def test_second_matching_swipe_creates_folder(self) -> None:
        controller = GestureController(double_swipe_interval_ms=850)
        first = controller.process(
            make_line((100, 300), (270, 130), timestamp_offset=10.0)
        )
        second = controller.process(
            make_line((120, 320), (290, 150), timestamp_offset=10.6)
        )
        self.assertIsNone(first.action)
        self.assertTrue(first.awaiting_second_swipe)
        self.assertEqual(second.action, ActionKind.CREATE_FOLDER)

    def test_opposite_swipe_does_not_complete_pair(self) -> None:
        controller = GestureController(double_swipe_interval_ms=850)
        controller.process(
            make_line((100, 300), (270, 130), timestamp_offset=10.0)
        )
        second = controller.process(
            make_line((300, 100), (120, 280), timestamp_offset=10.5)
        )
        self.assertIsNone(second.action)
        self.assertTrue(second.awaiting_second_swipe)

    def test_expired_swipe_does_not_complete_pair(self) -> None:
        controller = GestureController(double_swipe_interval_ms=600)
        controller.process(
            make_line((100, 300), (270, 130), timestamp_offset=10.0)
        )
        second = controller.process(
            make_line((120, 320), (290, 150), timestamp_offset=10.9)
        )
        self.assertIsNone(second.action)


if __name__ == "__main__":
    unittest.main()
