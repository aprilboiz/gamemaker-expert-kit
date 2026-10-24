"""
check_pii.py - Fails if tracked files contain machine-specific paths or personal identifiers.
Run before every commit/release: python tools/check_pii.py
"""

import os
import re
import subprocess
import sys

PATTERNS = [
    (re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+(?!<)[^\\/\s\"'`]+", re.IGNORECASE), "absolute user-profile path"),
    (re.compile(r"file:///", re.IGNORECASE), "file:/// link (use a relative link)"),
    (re.compile(r"GameMakerStudio2[^\\/\s]*[\\/]+(?!<|Cache|download|unknownUser)[A-Za-z0-9.]+_\d+"), "GameMaker licence user-folder id"),
]

SKIP_FILES = {"tools/check_pii.py"}


def tracked_files(repo_root: str) -> list:
    out = subprocess.run(["git", "ls-files"], cwd=repo_root, capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if f and f not in SKIP_FILES]


def scan(repo_root: str) -> list:
    hits = []
    for rel in tracked_files(repo_root):
        path = os.path.join(repo_root, rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (UnicodeDecodeError, OSError):
            continue  # binary file
        for idx, line in enumerate(lines, 1):
            for pattern, label in PATTERNS:
                if pattern.search(line):
                    hits.append(f"{rel}:{idx}: {label}: {line.strip()[:120]}")
    return hits


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    found = scan(root)
    for h in found:
        print(h)
    print(f"check_pii: {len(found)} issue(s)")
    sys.exit(1 if found else 0)
