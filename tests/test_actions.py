from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from actions import SystemActions, _next_folder_path, parse_shortcut


class ShortcutParserTests(unittest.TestCase):
    def test_default_shortcuts(self) -> None:
        self.assertEqual(parse_shortcut("Ctrl+C"), (0x11, ord("C")))
        self.assertEqual(parse_shortcut("Ctrl+V"), (0x11, ord("V")))
        self.assertEqual(
            parse_shortcut("Win+Shift+S"),
            (0x5B, 0x10, ord("S")),
        )

    def test_shortcut_is_case_insensitive(self) -> None:
        self.assertEqual(parse_shortcut("ctrl + shift + a"), (0x11, 0x10, 0x41))

    def test_unknown_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_shortcut("Ctrl+不存在")

    def test_duplicate_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_shortcut("Ctrl+Ctrl+C")


class FolderNamingTests(unittest.TestCase):
    def test_first_folder_uses_default_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = _next_folder_path(Path(directory))
            self.assertEqual(target.name, "新建文件夹")

    def test_existing_folder_uses_numbered_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "新建文件夹").mkdir()
            (root / "新建文件夹 (2)").mkdir()
            target = _next_folder_path(root)
            self.assertEqual(target.name, "新建文件夹 (3)")

    def test_create_folder_action_uses_active_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                "actions.get_active_explorer_directory",
                return_value=root,
            ):
                result = SystemActions().create_folder_in_active_directory()
            self.assertTrue(result.success)
            self.assertTrue((root / "新建文件夹").is_dir())


if __name__ == "__main__":
    unittest.main()
