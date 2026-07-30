#!/usr/bin/env python3
"""Run smoke checks against the native binary produced on this runner."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINARY = (ROOT / "dist" / "TelegramMediaDownloader").with_suffix(
    ".exe" if os.name == "nt" else ""
)


def main() -> int:
    if not BINARY.is_file():
        raise SystemExit(f"Release binary not found: {BINARY}")
    for arguments in (("--version",), ("--lang", "en", "--help"), ("--lang", "zh", "--help")):
        subprocess.run([str(BINARY), *arguments], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
