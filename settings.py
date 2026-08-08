from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "MouseGestureActions"
CONFIG_PATH = CONFIG_DIR / "settings.json"
DEFAULT_SCREENSHOT_SIDE_BUTTONS = ("xbutton1", "xbutton2")


@dataclass(slots=True)
class AppSettings:
    launch_listening: bool = True
    minimize_on_start: bool = False
    screenshot_side_buttons: tuple[str, ...] = DEFAULT_SCREENSHOT_SIDE_BUTTONS
    custom_button_1_name: str = "自定义 1"
    custom_button_1_target: str = ""
    custom_button_2_name: str = "自定义 2"
    custom_button_2_target: str = ""

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AppSettings":
        allowed = {item.name for item in fields(cls)}
        values = {key: value for key, value in data.items() if key in allowed}
        settings = cls(**values)
        raw_side_buttons = settings.screenshot_side_buttons
        if not isinstance(raw_side_buttons, (list, tuple)):
            raw_side_buttons = DEFAULT_SCREENSHOT_SIDE_BUTTONS
        settings.screenshot_side_buttons = tuple(
            name
            for name in DEFAULT_SCREENSHOT_SIDE_BUTTONS
            if name in raw_side_buttons
        )
        if not settings.screenshot_side_buttons:
            settings.screenshot_side_buttons = DEFAULT_SCREENSHOT_SIDE_BUTTONS
        settings.custom_button_1_name = (
            str(settings.custom_button_1_name).strip() or "自定义 1"
        )[:12]
        settings.custom_button_1_target = str(
            settings.custom_button_1_target
        ).strip()
        settings.custom_button_2_name = (
            str(settings.custom_button_2_name).strip() or "自定义 2"
        )[:12]
        settings.custom_button_2_target = str(
            settings.custom_button_2_target
        ).strip()
        return settings

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        temp_path = CONFIG_PATH.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(CONFIG_PATH)


def load_settings() -> AppSettings:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return AppSettings.from_mapping(data)
    except (OSError, ValueError, TypeError):
        pass
    return AppSettings()
