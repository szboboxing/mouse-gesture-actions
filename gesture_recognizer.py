from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float
    timestamp: float


class GestureKind(str, Enum):
    CIRCLE_LEFT = "circle_left"
    CIRCLE_RIGHT = "circle_right"
    CHECK = "check"
    SWIPE_UP_RIGHT = "swipe_up_right"
    SWIPE_DOWN_LEFT = "swipe_down_left"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class GestureResult:
    kind: GestureKind
    confidence: float
    description: str


SENSITIVITY_PROFILES = {
    "灵敏": {
        "minimum_path": 55.0,
        "circle_size": 50.0,
        "circle_turn": math.pi * 1.35,
        "circle_closure": 0.58,
        "swipe_distance": 90.0,
        "swipe_duration": 0.62,
        "swipe_straightness": 0.72,
    },
    "标准": {
        "minimum_path": 70.0,
        "circle_size": 65.0,
        "circle_turn": math.pi * 1.55,
        "circle_closure": 0.48,
        "swipe_distance": 115.0,
        "swipe_duration": 0.52,
        "swipe_straightness": 0.80,
    },
    "稳健": {
        "minimum_path": 90.0,
        "circle_size": 80.0,
        "circle_turn": math.pi * 1.72,
        "circle_closure": 0.40,
        "swipe_distance": 140.0,
        "swipe_duration": 0.44,
        "swipe_straightness": 0.86,
    },
}


class GestureRecognizer:
    def __init__(self, sensitivity: str = "标准") -> None:
        self.set_sensitivity(sensitivity)

    def set_sensitivity(self, sensitivity: str) -> None:
        self.sensitivity = (
            sensitivity if sensitivity in SENSITIVITY_PROFILES else "标准"
        )
        self.profile = SENSITIVITY_PROFILES[self.sensitivity]

    def recognize(self, raw_points: Iterable[Point]) -> GestureResult:
        points = _reduce_points(tuple(raw_points), minimum_gap=3.0)
        if len(points) < 3:
            return _unknown("轨迹过短")

        path_length = _path_length(points)
        if path_length < self.profile["minimum_path"]:
            return _unknown("轨迹长度不足")

        circle = self._recognize_circle(points, path_length)
        if circle is not None:
            return circle

        check = self._recognize_check(points)
        if check is not None:
            return check

        swipe = self._recognize_swipe(points, path_length)
        if swipe is not None:
            return swipe

        return _unknown("未匹配到已配置手势")

    def _recognize_circle(
        self, points: Sequence[Point], path_length: float
    ) -> GestureResult | None:
        min_x, max_x, min_y, max_y = _bounds(points)
        width = max_x - min_x
        height = max_y - min_y
        size = max(width, height)
        if (
            min(width, height) < self.profile["circle_size"]
            or min(width, height) / max(size, 1.0) < 0.55
        ):
            return None

        diagonal = math.hypot(width, height)
        closure = _distance(points[0], points[-1])
        if closure > diagonal * self.profile["circle_closure"]:
            return None

        center_x = sum(point.x for point in points) / len(points)
        center_y = sum(point.y for point in points) / len(points)
        angles = [
            math.atan2(point.y - center_y, point.x - center_x)
            for point in points
        ]
        total_turn = 0.0
        for previous, current in zip(angles, angles[1:]):
            delta = current - previous
            if delta > math.pi:
                delta -= math.tau
            elif delta < -math.pi:
                delta += math.tau
            total_turn += delta

        required_turn = self.profile["circle_turn"]
        if abs(total_turn) < required_turn:
            return None

        ideal_length = math.pi * (width + height) / 2.0
        length_ratio = min(path_length, ideal_length) / max(
            path_length, ideal_length, 1.0
        )
        closure_score = max(
            0.0, 1.0 - closure / max(diagonal * self.profile["circle_closure"], 1.0)
        )
        turn_score = min(1.0, abs(total_turn) / math.tau)
        confidence = _clamp(
            0.48 + length_ratio * 0.18 + closure_score * 0.16 + turn_score * 0.18
        )

        # Screen coordinates grow downward, so a positive turn is clockwise.
        if total_turn < 0:
            return GestureResult(
                GestureKind.CIRCLE_LEFT, confidence, "逆时针左向圆圈"
            )
        return GestureResult(
            GestureKind.CIRCLE_RIGHT, confidence, "顺时针右向圆圈"
        )

    def _recognize_check(
        self, points: Sequence[Point]
    ) -> GestureResult | None:
        pivot_index = max(range(1, len(points) - 1), key=lambda index: points[index].y)
        progress = pivot_index / (len(points) - 1)
        if not 0.18 <= progress <= 0.72:
            return None

        start = points[0]
        pivot = points[pivot_index]
        end = points[-1]
        left_dx = pivot.x - start.x
        left_drop = pivot.y - start.y
        right_dx = end.x - pivot.x
        right_rise = pivot.y - end.y
        if min(left_dx, left_drop, right_dx, right_rise) <= 14.0:
            return None

        left_direct = _distance(start, pivot)
        right_direct = _distance(pivot, end)
        left_path = _path_length(points[: pivot_index + 1])
        right_path = _path_length(points[pivot_index:])
        if (
            left_direct / max(left_path, 1.0) < 0.68
            or right_direct / max(right_path, 1.0) < 0.72
        ):
            return None

        if right_rise < left_drop * 0.55 or right_direct < left_direct * 0.72:
            return None

        span = max(end.x, pivot.x) - min(start.x, pivot.x)
        height = max(start.y, pivot.y, end.y) - min(start.y, pivot.y, end.y)
        if span < 45.0 or height < 30.0:
            return None

        confidence = _clamp(
            0.58
            + min(left_direct / max(left_path, 1.0), 1.0) * 0.16
            + min(right_direct / max(right_path, 1.0), 1.0) * 0.18
        )
        return GestureResult(GestureKind.CHECK, confidence, "对勾")

    def _recognize_swipe(
        self, points: Sequence[Point], path_length: float
    ) -> GestureResult | None:
        start = points[0]
        end = points[-1]
        duration = max(0.001, end.timestamp - start.timestamp)
        direct_distance = _distance(start, end)
        straightness = direct_distance / max(path_length, 1.0)
        if (
            duration > self.profile["swipe_duration"]
            or direct_distance < self.profile["swipe_distance"]
            or straightness < self.profile["swipe_straightness"]
        ):
            return None

        dx = end.x - start.x
        dy = end.y - start.y
        ratio = abs(dx) / max(abs(dy), 1.0)
        if not 0.35 <= ratio <= 2.85:
            return None

        confidence = _clamp(
            0.55
            + straightness * 0.25
            + min(1.0, direct_distance / 260.0) * 0.12
            + max(
                0.0,
                1.0 - duration / self.profile["swipe_duration"],
            )
            * 0.08
        )
        if dx > 0 and dy < 0:
            return GestureResult(
                GestureKind.SWIPE_UP_RIGHT, confidence, "向右上快速滑动"
            )
        if dx < 0 and dy > 0:
            return GestureResult(
                GestureKind.SWIPE_DOWN_LEFT, confidence, "向左下快速滑动"
            )
        return None


def _reduce_points(
    points: Sequence[Point], minimum_gap: float
) -> tuple[Point, ...]:
    if not points:
        return ()
    reduced = [points[0]]
    for point in points[1:-1]:
        if _distance(reduced[-1], point) >= minimum_gap:
            reduced.append(point)
    if len(points) > 1 and points[-1] != reduced[-1]:
        reduced.append(points[-1])
    return tuple(reduced)


def _path_length(points: Sequence[Point]) -> float:
    return sum(_distance(left, right) for left, right in zip(points, points[1:]))


def _distance(left: Point, right: Point) -> float:
    return math.hypot(right.x - left.x, right.y - left.y)


def _bounds(points: Sequence[Point]) -> tuple[float, float, float, float]:
    xs = [point.x for point in points]
    ys = [point.y for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _unknown(description: str) -> GestureResult:
    return GestureResult(GestureKind.UNKNOWN, 0.0, description)
