from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from gesture_recognizer import (
    GestureKind,
    GestureRecognizer,
    GestureResult,
    Point,
)


class ActionKind(str, Enum):
    COPY = "copy"
    PASTE = "paste"
    SCREENSHOT = "screenshot"
    CREATE_FOLDER = "create_folder"


@dataclass(frozen=True, slots=True)
class GestureOutcome:
    result: GestureResult
    action: ActionKind | None
    message: str
    awaiting_second_swipe: bool = False


class GestureController:
    def __init__(
        self,
        sensitivity: str = "标准",
        double_swipe_interval_ms: int = 850,
    ) -> None:
        self.recognizer = GestureRecognizer(sensitivity)
        self.double_swipe_interval = double_swipe_interval_ms / 1000.0
        self._pending_swipe: GestureKind | None = None
        self._pending_time = 0.0

    def update_settings(
        self, sensitivity: str, double_swipe_interval_ms: int
    ) -> None:
        self.recognizer.set_sensitivity(sensitivity)
        self.double_swipe_interval = max(
            0.35, min(1.5, double_swipe_interval_ms / 1000.0)
        )
        self.reset_pending_swipe()

    def reset_pending_swipe(self) -> None:
        self._pending_swipe = None
        self._pending_time = 0.0

    def process(self, points: Sequence[Point]) -> GestureOutcome:
        result = self.recognizer.recognize(points)
        if result.kind is GestureKind.CIRCLE_LEFT:
            self.reset_pending_swipe()
            return GestureOutcome(result, ActionKind.COPY, "左向圆圈：复制")
        if result.kind is GestureKind.CIRCLE_RIGHT:
            self.reset_pending_swipe()
            return GestureOutcome(result, ActionKind.PASTE, "右向圆圈：粘贴")
        if result.kind is GestureKind.CHECK:
            self.reset_pending_swipe()
            return GestureOutcome(result, ActionKind.SCREENSHOT, "对勾：截图")
        if result.kind in {
            GestureKind.SWIPE_UP_RIGHT,
            GestureKind.SWIPE_DOWN_LEFT,
        }:
            return self._process_swipe(result, points[-1].timestamp)

        if points and points[-1].timestamp - self._pending_time > self.double_swipe_interval:
            self.reset_pending_swipe()
        return GestureOutcome(result, None, result.description)

    def _process_swipe(
        self, result: GestureResult, timestamp: float
    ) -> GestureOutcome:
        within_interval = (
            self._pending_swipe is result.kind
            and timestamp - self._pending_time <= self.double_swipe_interval
        )
        if within_interval:
            self.reset_pending_swipe()
            return GestureOutcome(
                result,
                ActionKind.CREATE_FOLDER,
                f"{result.description}两次：新建文件夹",
            )

        self._pending_swipe = result.kind
        self._pending_time = timestamp
        return GestureOutcome(
            result,
            None,
            f"{result.description}：请再滑动一次",
            awaiting_second_swipe=True,
        )
