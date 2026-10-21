"""Fail when a project source file is not valid UTF-8.

Thai comments that are saved as cp874/TIS-620 turn into garbage the moment an
editor, git diff, or CI job reads the file as UTF-8. This checker keeps every
text file in the project UTF-8 so that cannot happen again.

Usage:
    python tools/check_encoding.py              # scan the project root
    python tools/check_encoding.py path [...]   # scan specific files/dirs
"""

from __future__ import annotations

import os
import sys

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Files that are legitimately not UTF-8. Keep this empty unless there is a
# documented reason; every entry here is a file with possibly garbled Thai.
ALLOWED_NON_UTF8: frozenset[str] = frozenset()

TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".spec",
    ".bat",
    ".ps1",
    ".yml",
    ".yaml",
    ".ini",
    ".cfg",
    ".csv",
    ".drawio",
}

SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "logs",
    "reports",
    "tables",
    "assets",
    "build",
    "dist",
    "mock_smco",
}

MAX_SIZE = 5 * 1024 * 1024


def iter_text_files(root: str):
    """Yield text files under root, skipping generated and binary folders."""
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if os.path.splitext(name)[1].lower() not in TEXT_EXTENSIONS:
                continue
            path = os.path.join(current, name)
            if os.path.getsize(path) > MAX_SIZE:
                continue
            yield path


def check_file(path: str) -> str | None:
    """Return None when the file is UTF-8, otherwise a reason string."""
    if os.path.abspath(path) in ALLOWED_NON_UTF8:
        return None
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        raw.decode("utf-8")
        return None
    except UnicodeDecodeError as exc:
        reason = f"not UTF-8 (byte {exc.start}: {exc.reason})"
    try:
        raw.decode("cp874")
        reason += "; it decodes as legacy cp874, re-save it as UTF-8"
    except UnicodeDecodeError:
        pass
    return reason


def main(argv: list[str]) -> int:
    targets = argv[1:] or [PROJECT_DIR]
    checked = 0
    failures: list[tuple[str, str]] = []
    for target in targets:
        target = os.path.abspath(target)
        paths = iter_text_files(target) if os.path.isdir(target) else [target]
        for path in paths:
            checked += 1
            reason = check_file(path)
            if reason is not None:
                failures.append((path, reason))

    for path, reason in failures:
        display = os.path.relpath(path, PROJECT_DIR)
        if display.startswith(".."):
            display = path
        print(f"FAIL {display}: {reason}")

    if failures:
        print(f"{len(failures)} of {checked} files are not UTF-8")
        return 1

    print(f"OK {checked} files are UTF-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
