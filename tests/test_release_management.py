from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.generate_version_info import version_tuple
from tools.retain_latest_releases import retain_latest_releases


class VersionMetadataTests(unittest.TestCase):
    def test_version_is_windows_compatible(self) -> None:
        self.assertEqual(version_tuple(), (1, 0, 0, 0))


class ReleaseRetentionTests(unittest.TestCase):
    def test_only_two_latest_versions_are_retained(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for version in ("V1.0", "V1.1", "V1.2"):
                (root / f"鼠标手势动作小工具_{version}.exe").write_bytes(b"test")
            unrelated = root / "other.exe"
            unrelated.write_bytes(b"keep")

            deleted = retain_latest_releases(root, keep=2)

            self.assertEqual(
                {path.name for path in deleted},
                {"鼠标手势动作小工具_V1.0.exe"},
            )
            self.assertFalse((root / "鼠标手势动作小工具_V1.0.exe").exists())
            self.assertTrue((root / "鼠标手势动作小工具_V1.1.exe").exists())
            self.assertTrue((root / "鼠标手势动作小工具_V1.2.exe").exists())
            self.assertTrue(unrelated.exists())


if __name__ == "__main__":
    unittest.main()
