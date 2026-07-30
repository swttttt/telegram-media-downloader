#!/usr/bin/env python3
"""Build a native, portable release package for the current operating system."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "TelegramMediaDownloader"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def application_version() -> str:
    sys.path.insert(0, str(ROOT))
    import telegram_media_downloader

    return telegram_media_downloader.__version__


def platform_tag() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    os_name = {"windows": "windows", "linux": "linux", "darwin": "macos"}.get(system)
    architecture = {
        "amd64": "x64",
        "x86_64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine)
    if not os_name or not architecture:
        raise SystemExit(f"Unsupported build platform: {platform.system()} {platform.machine()}")
    return os_name, architecture


def run_pyinstaller() -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--noupx",
        "--name",
        APP_NAME,
        "--hidden-import",
        "cryptg",
        "--exclude-module",
        "PIL",
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD),
        "--specpath",
        str(BUILD),
    ]
    if os.name == "nt":
        command.extend(
            [
                "--icon",
                str(ROOT / "assets" / "app.ico"),
                "--version-file",
                str(ROOT / "packaging" / "windows-version-info.txt"),
            ]
        )
    command.append(str(ROOT / "telegram_media_downloader.py"))
    subprocess.run(command, cwd=ROOT, check=True)
    binary = DIST / (f"{APP_NAME}.exe" if os.name == "nt" else APP_NAME)
    if not binary.is_file():
        raise SystemExit(f"PyInstaller did not create {binary}")
    if os.name != "nt":
        binary.chmod(binary.stat().st_mode | 0o111)
    return binary


def copy_package_files(stage: Path, binary: Path) -> None:
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    packaged_binary = stage / binary.name
    shutil.copy2(binary, packaged_binary)
    if os.name != "nt":
        packaged_binary.chmod(packaged_binary.stat().st_mode | 0o111)
    launcher = ROOT / ("start.bat" if os.name == "nt" else "start.sh")
    packaged_launcher = stage / launcher.name
    shutil.copy2(launcher, packaged_launcher)
    if os.name != "nt":
        packaged_launcher.chmod(packaged_launcher.stat().st_mode | 0o111)
    for name in ("README.md", "README_EN.md", "LICENSE"):
        shutil.copy2(ROOT / name, stage / name)


def build_archive(stage: Path, package_base: Path) -> Path:
    if os.name == "nt":
        archive = Path(f"{package_base}.zip")
        archive.unlink(missing_ok=True)
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    output.write(path, path.relative_to(stage))
        return archive

    archive = Path(f"{package_base}.tar.gz")
    archive.unlink(missing_ok=True)
    with tarfile.open(archive, "w:gz", compresslevel=9) as output:
        for path in sorted(stage.rglob("*")):
            output.add(path, arcname=path.relative_to(stage), recursive=False)
    return archive


def write_checksum(archive: Path, package_base: Path) -> Path:
    checksum = Path(f"{package_base}.sha256")
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum.write_text(f"{digest.hexdigest()}  {archive.name}\n", encoding="ascii")
    return checksum


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-assets",
        action="store_true",
        help="Do not regenerate checked-in marketing assets before building.",
    )
    args = parser.parse_args()

    if not args.skip_assets:
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_marketing_assets.py")], cwd=ROOT, check=True)

    version = application_version()
    os_name, architecture = platform_tag()
    binary = run_pyinstaller()
    package_name = f"{APP_NAME}-v{version}-{os_name}-{architecture}"
    stage = BUILD / package_name
    copy_package_files(stage, binary)
    package_base = DIST / package_name
    archive = build_archive(stage, package_base)
    checksum = write_checksum(archive, package_base)

    print("Release build complete:")
    print(f"  {binary}")
    print(f"  {archive}")
    print(f"  {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
