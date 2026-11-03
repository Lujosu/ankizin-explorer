#!/usr/bin/env python3
"""Erzeugt dist/ankizin_explorer.ankiaddon (Zip des Pakets, ohne __pycache__/meta.json)."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ankizin_explorer"
DIST = ROOT / "dist"
OUT = DIST / "ankizin_explorer.ankiaddon"

EXCLUDE_DIRS = {"__pycache__", "user_files", ".pytest_cache"}
EXCLUDE_FILES = {"meta.json", ".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def files():
    for path in sorted(PACKAGE.rglob("*")):
        rel = path.relative_to(PACKAGE)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.is_dir() or path.name in EXCLUDE_FILES or path.suffix in EXCLUDE_SUFFIXES:
            continue
        yield path, rel


def main() -> int:
    json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    json.loads((PACKAGE / "config.json").read_text(encoding="utf-8"))
    DIST.mkdir(exist_ok=True)
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, rel in files():
            zf.write(path, rel.as_posix())
            count += 1
    print(f"{OUT.relative_to(ROOT)}: {count} Dateien, {OUT.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
