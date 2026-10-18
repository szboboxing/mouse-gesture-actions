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
KEYBOARD_MAPPING_ACTION_SHORTCUT = "shortcut"
KEYBOARD_MAPPING_ACTION_ENHANCED_PASTE = "enhanced_paste"
KEYBOARD_MAPPING_ACTIONS = (
    KEYBOARD_MAPPING_ACTION_SHORTCUT,
    KEYBOARD_MAPPING_ACTION_ENHANCED_PASTE,
)


@dataclass(frozen=True, slots=True)
class KeyboardMappingSettings:
    mouse_button: str
    modifiers: tuple[str, ...]
    key: str
    enabled: bool = False
    action: str = KEYBOARD_MAPPING_ACTION_SHORTCUT


@dataclass(frozen=True, slots=True)
class RadialMenuItemSettings:
    """Persisted configuration for a single radial menu item."""
    label: str = ""
    icon_text: str = ""
    action_type: str = "open"  # open/set_paste_enhanced/set_paste_normal/
    # calculator/browser/mouse_pointer_size/ai_tool/brightness/contrast
    modifiers: tuple[str, ...] = ()
    key: str = ""
    target: str = ""


def default_radial_menu_items() -> tuple[RadialMenuItemSettings, ...]:
    return (
        RadialMenuItemSettings("鼠标大小", "⤢", "mouse_pointer_size"),
        RadialMenuItemSettings("普通粘贴", "⧉", "set_paste_normal"),
        RadialMenuItemSettings("增强粘贴", "⊕", "set_paste_enhanced"),
        RadialMenuItemSettings("对比度", "◐", "contrast"),
        RadialMenuItemSettings("AI 工具", "✦", "ai_tool"),
        RadialMenuItemSettings("亮度", "☀", "brightness"),
        RadialMenuItemSettings("浏览器", "◎", "browser"),
        RadialMenuItemSettings("计算器", "▦", "calculator"),
    )


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

        action = str(raw.get("action", default.action)).lower()
        if action not in KEYBOARD_MAPPING_ACTIONS:
            action = default.action

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
                action,
            )
        )
    return tuple(normalized)


def _normalize_radial_menu_items(
    raw_items: object,
) -> tuple[RadialMenuItemSettings, ...]:
    defaults = default_radial_menu_items()
    if not isinstance(raw_items, (list, tuple)) or len(raw_items) == 0:
        return defaults

    normalized: list[RadialMenuItemSettings] = []
    for raw in raw_items:
        if isinstance(raw, RadialMenuItemSettings):
            normalized.append(raw)
            continue
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label", "")).strip()
        if not label:
            continue
        icon_text = str(raw.get("icon_text", "●"))
        action_type = str(raw.get("action_type", "open")).lower()
        if action_type not in (
            "shortcut",
            "open",
            "enhanced_paste",
            "set_paste_enhanced",
            "set_paste_normal",
            "calculator",
            "browser",
            "mouse_pointer_size",
            "ai_tool",
            "brightness",
            "contrast",
        ):
            action_type = "open"
        raw_mods = raw.get("modifiers", ())
        if not isinstance(raw_mods, (list, tuple)):
            raw_mods = ()
        modifiers = tuple(str(m).lower() for m in raw_mods)
        key = str(raw.get("key", "")).upper()
        target = str(raw.get("target", "")).strip()
        normalized.append(
            RadialMenuItemSettings(
                label=label,
                icon_text=icon_text,
                action_type=action_type,
                modifiers=modifiers,
                key=key,
                target=target,
            )
        )

    # One-time upgrade from earlier default sets. The current defaults are
    # the eight function tiles (鼠标大小/普通粘贴/增强粘贴/对比度/AI 工具/
    # 亮度/浏览器/计算器); any persisted layout that still carries a legacy
    # shortcut item, the intermediate "enhanced_paste" action, or one of the
    # old labels (打印/剪切/新建文字/新建表格/AI PPT/撤销) is replaced
    # wholesale with the current defaults. There is no radial-item editing
    # UI yet, so replacing the whole layout is safe.
    LEGACY_RADIAL_LABELS = {
        "打印",
        "剪切",
        "新建文字",
        "新建表格",
        "AI PPT",
        "撤销",
        "复制",
    }

    def _is_legacy(item: RadialMenuItemSettings) -> bool:
        if item.action_type == "shortcut":
            return True
        if item.action_type == "enhanced_paste":
            return True
        if item.label in LEGACY_RADIAL_LABELS:
            return True
        return False

    if any(_is_legacy(item) for item in normalized):
        return defaults

    return tuple(normalized) if normalized else defaults


@dataclass(slots=True)
class AppSettings:
    launch_listening: bool = True
    minimize_on_start: bool = False
    show_radial_menu_on_start: bool = True
    clipboard_history_enabled: bool = True
    screenshot_side_buttons: tuple[str, ...] = DEFAULT_SCREENSHOT_SIDE_BUTTONS
    custom_button_name: str = "自定义"
    custom_button_target: str = ""
    ai_tool_target: str = ""
    keyboard_mappings: tuple[KeyboardMappingSettings, ...] = field(
        default_factory=default_keyboard_mappings
    )
    radial_menu_items: tuple[RadialMenuItemSettings, ...] = field(
        default_factory=default_radial_menu_items
    )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AppSettings":
        allowed = {item.name for item in fields(cls)}
        raw_keyboard_mappings = data.get("keyboard_mappings")
        raw_radial_menu_items = data.get("radial_menu_items")
        values = {
            key: value
            for key, value in data.items()
            if key in allowed
            and key not in ("keyboard_mappings", "radial_menu_items")
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
        # 兼容旧版本：custom_button_2_name/target 迁移到通用 custom_button_*
        legacy_name = data.get("custom_button_2_name")
        legacy_target = data.get("custom_button_2_target")
        if (
            settings.custom_button_name == "自定义"
            and not settings.custom_button_target
            and isinstance(legacy_name, str)
            and legacy_name.strip()
        ):
            settings.custom_button_name = legacy_name
            if isinstance(legacy_target, str):
                settings.custom_button_target = legacy_target
        settings.custom_button_name = (
            str(settings.custom_button_name).strip() or "自定义"
        )[:12]
        settings.custom_button_target = str(
            settings.custom_button_target
        ).strip()
        settings.ai_tool_target = str(settings.ai_tool_target).strip()
        settings.keyboard_mappings = _normalize_keyboard_mappings(
            raw_keyboard_mappings
        )
        settings.radial_menu_items = _normalize_radial_menu_items(
            raw_radial_menu_items
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
