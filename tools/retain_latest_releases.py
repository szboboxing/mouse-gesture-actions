from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path


VERSION_PATTERN = re.compile(r"_[vV](\d+)\.(\d+)\.exe$", re.IGNORECASE)


def parse_version(path: Path) -> tuple[int, int] | None:
    match = VERSION_PATTERN.search(path.name)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def retain_latest_releases(directory: Path, keep: int = 2) -> list[Path]:
    if keep < 1:
        raise ValueError("keep must be at least 1")
    directory.mkdir(parents=True, exist_ok=True)

    grouped: dict[tuple[int, int], list[Path]] = defaultdict(list)
    for path in directory.glob("*.exe"):
        version = parse_version(path)
        if version is not None:
            grouped[version].append(path)

    retained_versions = set(sorted(grouped, reverse=True)[:keep])
    deleted: list[Path] = []
    for version, paths in grouped.items():
        newest = max(paths, key=lambda item: item.stat().st_mtime_ns)
        for path in paths:
            if version not in retained_versions or path != newest:
                path.unlink()
                deleted.append(path)

    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Keep only the latest local EXE release versions."
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--keep", type=int, default=2)
    args = parser.parse_args()

    deleted = retain_latest_releases(args.directory, args.keep)
    print(f"Deleted {len(deleted)} old local release file(s)")
    for path in deleted:
        print(f"  {path.name}")


if __name__ == "__main__":
    main()
