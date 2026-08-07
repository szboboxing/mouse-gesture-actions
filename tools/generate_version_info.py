from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from version import APP_NAME, APP_VERSION, VERSION_TAG


OUTPUT = ROOT / "version_info.txt"


def version_tuple() -> tuple[int, int, int, int]:
    parts = [int(part) for part in APP_VERSION.split(".")]
    if not 1 <= len(parts) <= 4:
        raise ValueError("APP_VERSION must contain 1-4 numeric parts")
    return tuple((parts + [0, 0, 0, 0])[:4])


def generate_version_info() -> None:
    numeric_version = version_tuple()
    dotted_version = ".".join(str(part) for part in numeric_version)
    executable_name = f"{APP_NAME}_{VERSION_TAG}.exe"
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numeric_version},
    prodvers={numeric_version},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '080404B0',
          [
            StringStruct('CompanyName', 'szboboxing'),
            StringStruct('FileDescription', '{APP_NAME}'),
            StringStruct('FileVersion', '{dotted_version}'),
            StringStruct('InternalName', 'MouseGestureActions'),
            StringStruct('LegalCopyright', 'Copyright (C) 2026 szboboxing'),
            StringStruct('OriginalFilename', '{executable_name}'),
            StringStruct('ProductName', '{APP_NAME}'),
            StringStruct('ProductVersion', '{dotted_version}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Generated {OUTPUT.name} for {VERSION_TAG}")


if __name__ == "__main__":
    generate_version_info()
