from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any


CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "MouseGestureActions"
CONFIG_PATH = CONFIG_DIR / "settings.json"
DEFAULT_SCREENSHOT_SIDE_BUTTONS = ("xbutton1", "xbutton2")
KEYBOARD_MAPPING_MOUSE_BUTTONS = ("xbutton1", "xbutton2")
KEYBOARD_MAPPING_MODIFIERS = ("ctrl", "alt", "shift", "win")
KEYBOARD_MAPPING_KEYS = (
    tuple(chr(code) for code in range(ord("A"), ord("Z") + 1))
    + tuple(f"F{number}" for number in range(1, 13))
)


@dataclass(frozen=True, slots=True)
class KeyboardMappingSettings:
    mouse_button: str
    modifiers: tuple[str, ...]
    key: str
    enabled: bool = False


def default_keyboard_mappings() -> tuple[KeyboardMappingSettings, ...]:
    return (
        KeyboardMappingSettings("xbutton1", ("ctrl",), "C"),
        KeyboardMappingSettings("xbutton2", ("ctrl",), "V"),
    )


def _normalize_keyboard_mappings(
    raw_mappings: object,
) -> tuple[KeyboardMappingSettings, ...]:
    defaults = default_keyboard_mappings()
    if not isinstance(raw_mappings, (list, tuple)):
        return defaults

    normalized: list[KeyboardMappingSettings] = []
    enabled_mouse_buttons: set[str] = set()
    for index, default in enumerate(defaults):
        raw = raw_mappings[index] if index < len(raw_mappings) else {}
        if isinstance(raw, KeyboardMappingSettings):
            raw = asdict(raw)
        if not isinstance(raw, dict):
            raw = {}

        mouse_button = str(
            raw.get("mouse_button", default.mouse_button)
        ).lower()
        if mouse_button not in KEYBOARD_MAPPING_MOUSE_BUTTONS:
            mouse_button = default.mouse_button

        raw_modifiers = raw.get("modifiers", default.modifiers)
        if not isinstance(raw_modifiers, (list, tuple)):
            raw_modifiers = default.modifiers
        selected_modifiers = {
            str(modifier).lower() for modifier in raw_modifiers
        }
        modifiers = tuple(
            modifier
            for modifier in KEYBOARD_MAPPING_MODIFIERS
            if modifier in selected_modifiers
        )

        key = str(raw.get("key", default.key)).upper()
        if key not in KEYBOARD_MAPPING_KEYS:
            key = default.key

        enabled = raw.get("enabled") is True
        if enabled and mouse_button in enabled_mouse_buttons:
            enabled = False
        if enabled:
            enabled_mouse_buttons.add(mouse_button)
        normalized.append(
            KeyboardMappingSettings(
                mouse_button,
                modifiers,
                key,
                enabled,
            )
        )
    return tuple(normalized)


@dataclass(slots=True)
class AppSettings:
    launch_listening: bool = True
    minimize_on_start: bool = False
    screenshot_side_buttons: tuple[str, ...] = DEFAULT_SCREENSHOT_SIDE_BUTTONS
    custom_button_1_name: str = "自定义 1"
    custom_button_1_target: str = ""
    custom_button_2_name: str = "自定义 2"
    custom_button_2_target: str = ""
    keyboard_mappings: tuple[KeyboardMappingSettings, ...] = field(
        default_factory=default_keyboard_mappings
    )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AppSettings":
        allowed = {item.name for item in fields(cls)}
        raw_keyboard_mappings = data.get("keyboard_mappings")
        values = {
            key: value
            for key, value in data.items()
            if key in allowed and key != "keyboard_mappings"
        }
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
        settings.keyboard_mappings = _normalize_keyboard_mappings(
            raw_keyboard_mappings
        )
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
