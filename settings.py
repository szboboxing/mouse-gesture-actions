from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "MouseGestureActions"
CONFIG_PATH = CONFIG_DIR / "settings.json"


@dataclass(slots=True)
class AppSettings:
    copy_shortcut: str = "Ctrl+C"
    paste_shortcut: str = "Ctrl+V"
    screenshot_shortcut: str = "Win+Shift+S"
    sensitivity: str = "标准"
    double_swipe_interval_ms: int = 850
    launch_listening: bool = True
    minimize_on_start: bool = False

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AppSettings":
        allowed = {item.name for item in fields(cls)}
        values = {key: value for key, value in data.items() if key in allowed}
        settings = cls(**values)
        settings.double_swipe_interval_ms = max(
            350, min(1500, int(settings.double_swipe_interval_ms))
        )
        if settings.sensitivity not in {"灵敏", "标准", "稳健"}:
            settings.sensitivity = "标准"
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
