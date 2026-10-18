"""Local clipboard history for the radial menu.

Records recently copied plain text so the user can review and re-arm any
entry from below the wheel. Everything is local: the clipboard is read on a
Tk ``after`` poll and persisted to a JSON file under %APPDATA%\\MouseGestureActions.
No network access is used anywhere.

Tkinter has no real widget alpha, so the panel uses the same frosted base
and thin hairline look as the wheel tiles.
"""

from __future__ import annotations

import ctypes
import json
import time
from ctypes import wintypes as wt
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import tkinter as tk

from radial_menu import COLORS
from settings import CONFIG_DIR

CLIPBOARD_HISTORY_PATH = CONFIG_DIR / "clipboard_history.json"

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


def _os_name() -> str:
    import os

    return os.name


_IS_WIN = _os_name() == "nt"

_user32 = None
_kernel32 = None


def _load_api() -> bool:
    global _user32, _kernel32
    if _user32 is not None:
        return True
    if not _IS_WIN:
        return False
    try:
        _user32 = ctypes.WinDLL("user32", use_last_error=True)
        _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except OSError:
        _user32 = None
        _kernel32 = None
        return False
    _user32.OpenClipboard.argtypes = (wt.HWND,)
    _user32.OpenClipboard.restype = wt.BOOL
    _user32.CloseClipboard.restype = wt.BOOL
    _user32.EmptyClipboard.restype = wt.BOOL
    _user32.IsClipboardFormatAvailable.argtypes = (wt.UINT,)
    _user32.IsClipboardFormatAvailable.restype = wt.BOOL
    _user32.GetClipboardData.argtypes = (wt.UINT,)
    _user32.GetClipboardData.restype = wt.HANDLE
    _user32.SetClipboardData.argtypes = (wt.UINT, wt.HANDLE)
    _user32.SetClipboardData.restype = wt.HANDLE
    _user32.GetClipboardSequenceNumber.argtypes = ()
    _user32.GetClipboardSequenceNumber.restype = wt.DWORD
    _kernel32.GlobalAlloc.argtypes = (wt.UINT, ctypes.c_size_t)
    _kernel32.GlobalAlloc.restype = wt.HANDLE
    _kernel32.GlobalLock.argtypes = (wt.HANDLE,)
    _kernel32.GlobalLock.restype = wt.LPVOID
    _kernel32.GlobalUnlock.argtypes = (wt.HANDLE,)
    _kernel32.GlobalUnlock.restype = wt.BOOL
    return True


def clipboard_sequence() -> int:
    """Cheap change detector; increments on every clipboard write."""
    if not _load_api():
        return 0
    try:
        return int(_user32.GetClipboardSequenceNumber())
    except Exception:
        return 0


def read_clipboard_text() -> str | None:
    if not _load_api():
        return None
    if not _user32.OpenClipboard(None):
        return None
    try:
        if not _user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None
        handle = _user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = _kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            text = ctypes.cast(ptr, ctypes.c_wchar_p).value
        finally:
            _kernel32.GlobalUnlock(handle)
        return text
    finally:
        _user32.CloseClipboard()


def write_clipboard_text(text: str) -> bool:
    if not _load_api():
        return False
    data = (text + "\0").encode("utf-16-le")
    if not _user32.OpenClipboard(None):
        return False
    try:
        _user32.EmptyClipboard()
        handle = _kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            return False
        ptr = _kernel32.GlobalLock(handle)
        if not ptr:
            return False
        try:
            ctypes.memmove(ptr, data, len(data))
        finally:
            _kernel32.GlobalUnlock(handle)
        return bool(_user32.SetClipboardData(CF_UNICODETEXT, handle))
    finally:
        _user32.CloseClipboard()


def _shorten(text: str, limit: int) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1] + "…"


@dataclass(slots=True)
class ClipEntry:
    text: str
    ts: float

    def as_dict(self) -> dict[str, object]:
        return {"text": self.text, "ts": self.ts}

    @staticmethod
    def from_dict(raw: dict) -> "ClipEntry | None":
        if not isinstance(raw, dict):
            return None
        text = raw.get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        try:
            ts = float(raw.get("ts", time.time()))
        except (TypeError, ValueError):
            ts = time.time()
        return ClipEntry(text=text, ts=ts)


class ClipboardHistoryStore:
    """Bounded, deduplicated, newest-first clipboard history persisted to disk."""

    def __init__(
        self,
        max_entries: int = 50,
        path: Path = CLIPBOARD_HISTORY_PATH,
    ) -> None:
        self.max_entries = max(10, int(max_entries))
        self.path = Path(path)
        self.entries: list[ClipEntry] = []
        self.load()

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, list):
            return
        loaded: list[ClipEntry] = []
        for raw in data:
            entry = ClipEntry.from_dict(raw)
            if entry is not None:
                loaded.append(entry)
        self.entries = loaded[: self.max_entries]

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = [e.as_dict() for e in self.entries]
            temp = self.path.with_suffix(".tmp")
            temp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            temp.replace(self.path)
        except OSError:
            pass

    def add(self, text: str) -> bool:
        """Push new text to the front. Returns True if the visible list changed."""
        if not text or not text.strip():
            return False
        text = text.rstrip("\0")
        if self.entries and self.entries[0].text == text:
            self.entries[0].ts = time.time()
            return False
        # Drop any older duplicate of the same content.
        self.entries = [e for e in self.entries if e.text != text]
        self.entries.insert(0, ClipEntry(text=text, ts=time.time()))
        del self.entries[self.max_entries:]
        self.save()
        return True

    def recent(self, count: int) -> list[ClipEntry]:
        return self.entries[: max(1, count)]

    def clear(self) -> None:
        self.entries = []
        self.save()


class ClipboardHistoryPanel(tk.Frame):
    """Below-wheel strip: enable toggle, recent list, 5/10 'more' switch."""

    POLL_MS = 500
    BASE_COUNT = 5
    MORE_COUNT = 10

    def __init__(
        self,
        parent: tk.Misc,
        store: ClipboardHistoryStore,
        on_status: Callable[[str], None] | None = None,
        on_toggle: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.store = store
        self.on_status = on_status
        self.on_toggle = on_toggle
        self.enabled = True
        self.show_count = self.BASE_COUNT
        self._last_seq: int | None = None
        self._after_id: str | None = None
        self._row_buttons: list[tk.Button] = []

        self._build()

    def _build(self) -> None:
        tk.Frame(self, bg=COLORS["top_bar_border"], height=1).pack(
            fill="x", side="top"
        )

        header = tk.Frame(self, bg=COLORS["bg"])
        header.pack(fill="x", side="top", padx=20, pady=(10, 4))

        tk.Label(
            header,
            text="剪贴板历史",
            bg=COLORS["bg"],
            fg=COLORS["status_text"],
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(side="left")

        self._more_btn = self._pill(
            header, "More ▾", self.toggle_more
        )
        self._more_btn.pack(side="right")

        self._clear_btn = self._pill(header, "清空", self._clear)
        self._clear_btn.pack(side="right", padx=(0, 8))

        self._enable_btn = self._pill(
            header, "", self.toggle_enabled
        )
        self._enable_btn.pack(side="right", padx=(0, 8))

        self._hint = tk.Label(
            header,
            text="",
            bg=COLORS["bg"],
            fg=COLORS["status_muted"],
            font=("Microsoft YaHei UI", 9),
        )
        self._hint.pack(side="right", padx=(0, 12))

        self._list = tk.Frame(self, bg=COLORS["bg"])
        self._list.pack(fill="x", side="top", padx=16, pady=(0, 12))

        self._refresh_enabled_button()
        self.refresh()

    def _pill(self, parent: tk.Misc, text: str, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=COLORS["card"],
            fg=COLORS["hover"],
            activebackground=COLORS["icon_accent"] if False else "#D7E8FF",
            activeforeground=COLORS["hover"],
            relief="flat",
            bd=0,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=COLORS["top_bar_border"],
            highlightcolor=COLORS["top_bar_border"],
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=12,
            pady=4,
        )

    # ---- public ---------------------------------------------------------
    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self._refresh_enabled_button()
        if self.enabled and self._after_id is None:
            self.start()

    def start(self) -> None:
        if self._after_id is not None:
            return
        self._last_seq = clipboard_sequence()
        self._schedule()

    def stop(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def save(self) -> None:
        self.store.save()

    def toggle_enabled(self) -> None:
        self.set_enabled(not self.enabled)
        if self.on_toggle is not None:
            self.on_toggle(self.enabled)
        if self.on_status is not None:
            self.on_status(
                "剪贴板历史：开始记录" if self.enabled else "剪贴板历史：已暂停"
            )

    def toggle_more(self) -> None:
        self.show_count = (
            self.MORE_COUNT
            if self.show_count == self.BASE_COUNT
            else self.BASE_COUNT
        )
        self._more_btn.configure(
            text="收起 ▴" if self.show_count == self.MORE_COUNT else "More ▾"
        )
        self.refresh()

    def refresh(self) -> None:
        for btn in self._row_buttons:
            btn.destroy()
        self._row_buttons.clear()

        entries = self.store.recent(self.show_count)
        if not entries:
            placeholder = tk.Label(
                self._list,
                text="（暂无记录，复制任意文本后这里会显示）"
                if self.enabled
                else "（记录已暂停）",
                bg=COLORS["bg"],
                fg=COLORS["status_muted"],
                font=("Microsoft YaHei UI", 10),
                anchor="w",
            )
            placeholder.pack(fill="x", pady=6)
            self._row_buttons.append(placeholder)  # type: ignore[list-item]
            return

        for index, entry in enumerate(entries):
            self._add_row(index, entry)

    # ---- internals ------------------------------------------------------
    def _add_row(self, index: int, entry: ClipEntry) -> None:
        preview = _shorten(entry.text, 64)
        stamp = time.strftime("%H:%M", time.localtime(entry.ts))
        label = f"  {index + 1}.  {preview}    ·  {stamp}"
        btn = tk.Button(
            self._list,
            text=label,
            command=lambda e=entry: self._use_entry(e),
            anchor="w",
            justify="left",
            bg=COLORS["card"],
            fg=COLORS["status_text"],
            activebackground="#D7E8FF",
            activeforeground=COLORS["status_text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=COLORS["top_bar_border"],
            highlightcolor=COLORS["top_bar_border"],
            font=("Microsoft YaHei UI", 10),
            padx=10,
            pady=5,
        )
        btn.pack(fill="x", pady=2)
        btn.bind(
            "<Enter>",
            lambda _e, b=btn: b.configure(highlightcolor=COLORS["hover"]),
        )
        btn.bind(
            "<Leave>",
            lambda _e, b=btn: b.configure(
                highlightcolor=COLORS["top_bar_border"]
            ),
        )
        self._row_buttons.append(btn)

    def _use_entry(self, entry: ClipEntry) -> None:
        if write_clipboard_text(entry.text):
            # Bring the re-armed entry to the front of history.
            self.store.add(entry.text)
            self._last_seq = clipboard_sequence()
            self.refresh()
            self._set_hint("已复制到剪贴板")
            if self.on_status is not None:
                self.on_status("已重新复制剪贴板历史条目")

    def _clear(self) -> None:
        self.store.clear()
        self._last_seq = clipboard_sequence()
        self.refresh()
        self._set_hint("已清空记录")

    def _refresh_enabled_button(self) -> None:
        if self.enabled:
            self._enable_btn.configure(
                text="记录：已开启",
                fg="#FFFFFF",
                bg=COLORS["icon_success"],
                activebackground=COLORS["icon_success"],
                activeforeground="#FFFFFF",
            )
        else:
            self._enable_btn.configure(
                text="记录：已暂停",
                fg=COLORS["status_muted"],
                bg=COLORS["card"],
                activebackground="#D7E8FF",
                activeforeground=COLORS["status_muted"],
            )
        self.refresh()

    def _set_hint(self, text: str) -> None:
        self._hint.configure(text=text)
        self.after(2200, lambda: self._hint.configure(text="") if self.winfo_exists() else None)

    def _schedule(self) -> None:
        self._after_id = self.after(self.POLL_MS, self._poll)

    def _poll(self) -> None:
        self._after_id = None
        try:
            if self.enabled:
                seq = clipboard_sequence()
                if self._last_seq is None:
                    self._last_seq = seq
                elif seq != self._last_seq:
                    self._last_seq = seq
                    text = read_clipboard_text()
                    if text and text.strip():
                        if self.store.add(text):
                            self.refresh()
        finally:
            if self.enabled and self.winfo_exists():
                self._schedule()
