from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from clipboard_history import ClipEntry, ClipboardHistoryStore


class ClipboardHistoryStoreTest(unittest.TestCase):
    def _store(self, tmp: Path, max_entries: int = 50) -> ClipboardHistoryStore:
        store = ClipboardHistoryStore(max_entries=max_entries, path=tmp)
        # Start from empty regardless of any on-disk file.
        store.entries = []
        return store

    def test_add_prepends_and_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "hist.json"
            store = self._store(path)
            self.assertTrue(store.add("alpha"))
            self.assertTrue(store.add("beta"))
            self.assertEqual([e.text for e in store.entries], ["beta", "alpha"])
            # Re-adding an older duplicate moves it to the front, no growth.
            self.assertTrue(store.add("alpha"))
            self.assertEqual([e.text for e in store.entries], ["alpha", "beta"])
            # Same newest text is only a timestamp bump, not a list change.
            self.assertFalse(store.add("alpha"))
            self.assertEqual(len(store.entries), 2)

    def test_blank_text_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            store = self._store(Path(d) / "hist.json")
            self.assertFalse(store.add(""))
            self.assertFalse(store.add("   "))
            self.assertEqual(store.entries, [])

    def test_max_entries_cap(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            store = self._store(Path(d) / "hist.json", max_entries=10)
            for i in range(20):
                store.add(f"item-{i}")
            self.assertLessEqual(len(store.entries), store.max_entries)
            self.assertEqual(store.entries[0].text, "item-19")

    def test_recent_limits_count(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            store = self._store(Path(d) / "hist.json")
            for i in range(8):
                store.add(f"t{i}")
            self.assertEqual(len(store.recent(5)), 5)
            self.assertEqual(len(store.recent(10)), 8)

    def test_persistence_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "hist.json"
            store = self._store(path)
            store.add("keep me")
            store.add("and me")
            reloaded = ClipboardHistoryStore(max_entries=50, path=path)
            self.assertEqual([e.text for e in reloaded.entries], ["and me", "keep me"])

    def test_clear_empties_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "hist.json"
            store = self._store(path)
            store.add("x")
            store.clear()
            self.assertEqual(store.entries, [])
            reloaded = ClipboardHistoryStore(max_entries=50, path=path)
            self.assertEqual(reloaded.entries, [])

    def test_malformed_file_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "hist.json"
            path.write_text("{not json", encoding="utf-8")
            store = ClipboardHistoryStore(max_entries=50, path=path)
            self.assertEqual(store.entries, [])

    def test_entry_from_dict_filters_blank(self) -> None:
        self.assertIsNone(ClipEntry.from_dict({"text": "  "}))
        self.assertIsNone(ClipEntry.from_dict("nope"))
        self.assertIsNotNone(ClipEntry.from_dict({"text": "ok", "ts": 1}))


if __name__ == "__main__":
    unittest.main()
