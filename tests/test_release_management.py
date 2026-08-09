from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.generate_version_info import version_tuple
from tools.retain_latest_releases import retain_latest_releases
from version import VERSION_TAG


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class VersionMetadataTests(unittest.TestCase):
    def test_version_is_windows_compatible(self) -> None:
        self.assertEqual(version_tuple(), (2, 2, 0, 0))

    def test_current_release_has_version_notes(self) -> None:
        notes_path = (
            PROJECT_ROOT / "docs" / "releases" / f"{VERSION_TAG}.md"
        )
        self.assertTrue(notes_path.is_file())
        self.assertIn(
            f"# 鼠标手势动作小工具 {VERSION_TAG} 版本说明",
            notes_path.read_text(encoding="utf-8"),
        )


class ReleaseRetentionTests(unittest.TestCase):
    def test_latest_two_versions_are_retained(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for version in ("V2.0", "V2.1", "V2.2"):
                (root / f"鼠标手势动作小工具_{version}.exe").write_bytes(b"test")
            unrelated = root / "other.exe"
            unrelated.write_bytes(b"keep")

            deleted = retain_latest_releases(root)

            self.assertEqual(
                {path.name for path in deleted},
                {
                    "鼠标手势动作小工具_V2.0.exe",
                },
            )
            self.assertFalse((root / "鼠标手势动作小工具_V2.0.exe").exists())
            self.assertTrue((root / "鼠标手势动作小工具_V2.1.exe").exists())
            self.assertTrue((root / "鼠标手势动作小工具_V2.2.exe").exists())
            self.assertTrue(unrelated.exists())


if __name__ == "__main__":
    unittest.main()
