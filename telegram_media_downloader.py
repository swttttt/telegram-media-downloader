#!/usr/bin/env python3
r"""
下载 Telegram 帖子中的整组最高质量图片和视频。

用法：
    python telegram_media_downloader.py
    python telegram_media_downloader.py "https://t.me/ExampleChannel/37?single"
    python telegram_media_downloader.py URL --overwrite
    python telegram_media_downloader.py URL --jobs 4 --retries 6

默认下载目录：
    本脚本所在目录\download

首次使用需要自己的 Telegram API_ID / API_HASH。脚本优先读取：
    TELEGRAM_API_ID
    TELEGRAM_API_HASH

若环境变量不存在，首次运行会询问并安全保存到系统凭据存储。
登录成功后，Telegram 登录会话保存在脚本目录的
telegram_media.session 中，后续不需要重复输入手机号和验证码。

English interface:
    python telegram_media_downloader.py --lang en
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import getpass
import mimetypes
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
if os.name == "nt":
    from ctypes import wintypes


__version__ = "1.2.0"


def application_dir() -> Path:
    """Return the stable folder beside the script or frozen executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


SCRIPT_DIR = application_dir()
VENDOR_DIR = SCRIPT_DIR / "_vendor"
DEFAULT_DOWNLOAD_DIR = SCRIPT_DIR / "download"
SESSION_PATH = SCRIPT_DIR / "telegram_media"

if VENDOR_DIR.is_dir():
    sys.path.insert(0, str(VENDOR_DIR))


def requested_language(argv: list[str] | None = None) -> str:
    """Read --lang early so even argparse help and import errors are localized."""
    values = list(sys.argv[1:] if argv is None else argv)
    language = (os.getenv("TMD_LANG") or "zh").strip().lower()
    for index, value in enumerate(values):
        if value.startswith("--lang="):
            language = value.partition("=")[2].strip().lower()
            break
        if value == "--lang" and index + 1 < len(values):
            language = values[index + 1].strip().lower()
            break
    return language if language in {"zh", "en"} else "zh"


LANGUAGE = requested_language()


def tr(chinese: str, english: str) -> str:
    """Return the text for the active interface language."""
    return english if LANGUAGE == "en" else chinese


try:
    from telethon import TelegramClient, functions
    from telethon.errors import (
        FileReferenceExpiredError,
        FloodWaitError,
        RPCError,
        RpcCallFailError,
        ServerError,
        TimedOutError,
    )
except ModuleNotFoundError:
    print(tr("缺少 Telethon。请执行：", "Telethon is missing. Run:"))
    print(f'python -m pip install --target "{VENDOR_DIR}" "telethon>=1.40,<2"')
    raise SystemExit(2)


SUPPORTED_HOSTS = {
    "t.me",
    "www.t.me",
    "telegram.me",
    "www.telegram.me",
    "telegram.dog",
    "www.telegram.dog",
}
SAFE_NAME_RE = re.compile(r"[^0-9A-Za-z._-]+")
CREDENTIAL_SERVICE = "TelegramMediaDownloader.API"
CREDENTIAL_ACCOUNT = "api"
WINDOWS_CREDENTIAL_TARGET = CREDENTIAL_SERVICE
ERROR_NOT_FOUND = 1168
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2


if os.name == "nt":
    class WindowsCredential(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]
else:
    WindowsCredential = None
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


# ---------------------------------------------------------------------------
# 终端界面
# ---------------------------------------------------------------------------


class Palette:
    """终端配色。在不支持 ANSI 的环境中自动退化为纯文本。"""

    def __init__(self, enabled: bool) -> None:
        def c(*codes: int) -> str:
            if not enabled:
                return ""
            return "\x1b[" + ";".join(str(code) for code in codes) + "m"

        self.reset = c(0)
        self.bold = c(1)
        self.dim = c(2)
        self.gray = c(90)
        self.red = c(91)
        self.green = c(92)
        self.yellow = c(93)
        self.cyan = c(36)
        self.bright_cyan = c(96)


P = Palette(False)


def _enable_windows_ansi() -> bool:
    """在 Windows 控制台中开启 ANSI 转义序列支持。"""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        for handle_id in (-11, -12):  # STD_OUTPUT_HANDLE / STD_ERROR_HANDLE
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_uint32()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                continue
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        return True
    except (AttributeError, OSError):
        return False


def setup_terminal() -> None:
    """UTF-8 输出 + ANSI 配色探测，替代旧的 configure_console。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except OSError:
                pass

    enabled = (
        sys.stdout.isatty()
        and os.getenv("NO_COLOR") is None
        and _enable_windows_ansi()
    )
    global P
    P = Palette(enabled)


def display_width(text: str) -> int:
    """计算可见宽度，中文等宽字符按 2 格计。"""
    return sum(
        2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        for char in text
    )


def visible_width(text: str) -> int:
    """剥掉 ANSI 转义后的可见宽度。"""
    return display_width(ANSI_RE.sub("", text))


def print_banner() -> None:
    accent = P.bright_cyan
    brand = (
        f"{P.bold}{P.bright_cyan}TG{P.reset}  "
        f"{P.bold}TELEGRAM MEDIA{P.reset}"
    )
    title = f"{P.bold}{tr('原画质媒体下载器', 'Original-quality media downloader')}{P.reset}"
    features = (
        f"{P.dim}"
        f"{tr('整组识别  ·  并发下载  ·  智能重试', 'Album detection  ·  Parallel downloads  ·  Smart retries')}"
        f"{P.reset}"
    )
    width = max(54, *(visible_width(row) + 4 for row in (brand, title, features)))
    print()
    print(f"{accent}╭{'─' * width}╮{P.reset}")
    for row in (brand, title):
        pad = " " * max(0, width - visible_width(row) - 4)
        print(f"{accent}│{P.reset}    {row}{pad}{accent}│{P.reset}")
    print(f"{accent}├{'─' * width}┤{P.reset}")
    feature_pad = " " * max(0, width - visible_width(features) - 4)
    print(
        f"{accent}│{P.reset}    {features}{feature_pad}"
        f"{accent}│{P.reset}"
    )
    print(f"{accent}╰{'─' * width}╯{P.reset}")


def print_panel(title: str, rows: list[str], accent: str) -> None:
    """打印一个自动对齐中文宽度的信息面板。"""
    content = max([visible_width(row) for row in rows] + [visible_width(title) + 2])
    header_dash = content - visible_width(title) - 1
    print(
        f"{accent}┌─{P.reset} {P.bold}{title}{P.reset} "
        f"{accent}{'─' * header_dash}┐{P.reset}"
    )
    for row in rows:
        pad = " " * (content - visible_width(row))
        print(f"{accent}│{P.reset} {row}{pad} {accent}│{P.reset}")
    print(f"{accent}└{'─' * (content + 2)}┘{P.reset}")


def ask(question: str) -> str:
    return input(f"{P.bright_cyan}❯{P.reset} {question} ").strip()


def icon_download(text: str) -> str:
    return f"{P.cyan}↓{P.reset} {text}"


def icon_done(text: str) -> str:
    return f"{P.green}✓{P.reset} {text}"


def icon_skip(text: str) -> str:
    return f"{P.gray}•{P.reset} {P.dim}{text}{P.reset}"


def icon_retry(text: str) -> str:
    return f"{P.yellow}↻{P.reset} {text}"


def icon_error(text: str) -> str:
    return f"{P.red}✗{P.reset} {text}"


def icon_wait(text: str) -> str:
    return f"{P.gray}…{P.reset} {text}"


def format_elapsed(seconds: float) -> str:
    total = int(seconds)
    if total >= 60:
        return f"{total // 60:02d}:{total % 60:02d}"
    return f"{total}s"


# ---------------------------------------------------------------------------
# 下载逻辑
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TelegramPost:
    original_url: str
    channel_label: str
    entity: str | int
    message_id: int
    comment_id: int | None = None


class IncompleteDownloadError(RuntimeError):
    pass


class BatchProgress:
    BAR_WIDTH = 24

    def __init__(self, total_items: int) -> None:
        self.current: dict[str, int] = {}
        self.total: dict[str, int] = {}
        self.total_items = max(1, total_items)
        self.items_done = 0
        self.last_update = 0.0
        self.last_width = 0
        self.started = time.monotonic()

    def callback(self, key: str):
        def update(current: int, total: int) -> None:
            self.current[key] = max(0, int(current))
            if total > 0:
                self.total[key] = int(total)

            now = time.monotonic()
            done = sum(self.current.values())
            expected = sum(self.total.values())
            if done < expected and now - self.last_update < 0.15:
                return

            self._render(done, expected)
            self.last_update = now

        return update

    def _render(self, done: int, expected: int) -> None:
        if expected > 0:
            ratio = min(1.0, done / expected)
            filled = int(self.BAR_WIDTH * ratio)
            bar = "█" * filled + "░" * (self.BAR_WIDTH - filled)
            percent = f"{int(ratio * 100):3d}%"
            size_text = f"{format_bytes(done)}/{format_bytes(expected)}"
        else:
            bar = "░" * self.BAR_WIDTH
            percent = "    "
            size_text = format_bytes(done)

        text = (
            f"{P.cyan}{tr('总进度', 'Overall')}{P.reset} "
            f"{P.bright_cyan}{bar}{P.reset} "
            f"{P.bold}{percent}{P.reset} {P.gray}│{P.reset} {size_text} "
            f"{P.gray}│{P.reset} {self.items_done}/{self.total_items} "
            f"{tr('项', 'items')} "
            f"{P.gray}│{P.reset} {P.dim}{format_elapsed(time.monotonic() - self.started)}{P.reset}"
        )
        pad = max(0, self.last_width - visible_width(text))
        print(f"\r{text}{' ' * pad}", end="", flush=True)
        self.last_width = visible_width(text)

    def set_expected(self, key: str, size: int | None) -> None:
        if size is not None and size > 0:
            self.total[key] = size

    def reset_item(self, key: str) -> None:
        self.current[key] = 0

    def complete_item(self, key: str, size: int) -> None:
        self.current[key] = size
        self.total[key] = size
        self.items_done += 1

    def log(self, text: str) -> None:
        if self.last_width:
            print(f"\r{' ' * self.last_width}\r", end="")
            self.last_width = 0
        print(text, flush=True)

    def finish(self) -> None:
        if self.last_width:
            print()
            self.last_width = 0


def parse_post_url(raw_url: str) -> TelegramPost:
    raw_url = raw_url.strip()
    if not raw_url:
        raise ValueError(tr("链接不能为空", "The URL cannot be empty"))

    candidate = raw_url
    if "://" not in candidate:
        candidate = "https://" + candidate

    parsed = urlparse(candidate)
    if parsed.hostname is None or parsed.hostname.lower() not in SUPPORTED_HOSTS:
        raise ValueError(
            tr(
                "只支持 t.me、telegram.me 或 telegram.dog 的帖子链接",
                "Only t.me, telegram.me, and telegram.dog post URLs are supported",
            )
        )

    query = parse_qs(parsed.query)
    comment_values = query.get("comment", [])
    comment_id: int | None = None
    if comment_values:
        raw_comment = comment_values[-1]
        if not raw_comment.isdigit() or int(raw_comment) <= 0:
            raise ValueError(
                tr(
                    f"无效的评论编号：{raw_comment}",
                    f"Invalid comment ID: {raw_comment}",
                )
            )
        comment_id = int(raw_comment)

    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if parts and parts[0].lower() == "s":
        parts.pop(0)

    if len(parts) < 2:
        raise ValueError(
            tr(
                "链接中没有找到频道名和帖子编号",
                "The URL does not contain a channel and post ID",
            )
        )

    if parts[0].lower() == "c":
        if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
            raise ValueError(
                tr(
                    "无效的 Telegram 私有频道帖子链接",
                    "Invalid private Telegram channel post URL",
                )
            )
        internal_id = parts[1]
        message_id = int(parts[2])
        return TelegramPost(
            original_url=raw_url,
            channel_label=f"channel_{internal_id}",
            entity=int(f"-100{internal_id}"),
            message_id=message_id,
            comment_id=comment_id,
        )

    channel = parts[0].lstrip("@")
    if not re.fullmatch(r"[0-9A-Za-z_]+", channel):
        raise ValueError(
            tr(f"无效的频道名：{channel}", f"Invalid channel name: {channel}")
        )
    if not parts[1].isdigit():
        raise ValueError(
            tr(f"无效的帖子编号：{parts[1]}", f"Invalid post ID: {parts[1]}")
        )

    return TelegramPost(
        original_url=raw_url,
        channel_label=channel,
        entity=channel,
        message_id=int(parts[1]),
        comment_id=comment_id,
    )


def windows_credential_api():
    """返回 Windows Credential Manager API；非 Windows 返回 None。"""
    if os.name != "nt":
        return None

    advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    credential_pointer = ctypes.POINTER(WindowsCredential)
    advapi32.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(credential_pointer),
    ]
    advapi32.CredReadW.restype = wintypes.BOOL
    advapi32.CredWriteW.argtypes = [
        ctypes.POINTER(WindowsCredential),
        wintypes.DWORD,
    ]
    advapi32.CredWriteW.restype = wintypes.BOOL
    advapi32.CredDeleteW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    advapi32.CredDeleteW.restype = wintypes.BOOL
    advapi32.CredFree.argtypes = [ctypes.c_void_p]
    advapi32.CredFree.restype = None
    return advapi32


def _load_windows_credentials() -> tuple[str, str] | None:
    """从 Windows Credential Manager 读取 API_ID/API_HASH。"""
    advapi32 = windows_credential_api()
    if advapi32 is None:
        return None

    credential_pointer = ctypes.POINTER(WindowsCredential)()
    if not advapi32.CredReadW(
        WINDOWS_CREDENTIAL_TARGET,
        CRED_TYPE_GENERIC,
        0,
        ctypes.byref(credential_pointer),
    ):
        error = ctypes.get_last_error()
        if error == ERROR_NOT_FOUND:
            return None
        raise ctypes.WinError(error)

    try:
        credential = credential_pointer.contents
        api_id = credential.UserName or ""
        blob = ctypes.string_at(
            credential.CredentialBlob,
            credential.CredentialBlobSize,
        )
        api_hash = blob.decode("utf-16-le")
        return api_id, api_hash
    finally:
        advapi32.CredFree(credential_pointer)


def _save_windows_credentials(api_id: int, api_hash: str) -> None:
    """把 API 凭据写入当前 Windows 用户的 Credential Manager。"""
    advapi32 = windows_credential_api()
    if advapi32 is None:
        return

    blob = api_hash.encode("utf-16-le")
    blob_buffer = ctypes.create_string_buffer(blob)
    credential = WindowsCredential()
    credential.Flags = 0
    credential.Type = CRED_TYPE_GENERIC
    credential.TargetName = WINDOWS_CREDENTIAL_TARGET
    credential.Comment = "Telegram media downloader API credentials"
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(
        blob_buffer,
        ctypes.POINTER(ctypes.c_ubyte),
    )
    credential.Persist = CRED_PERSIST_LOCAL_MACHINE
    credential.AttributeCount = 0
    credential.Attributes = None
    credential.TargetAlias = None
    credential.UserName = str(api_id)

    if not advapi32.CredWriteW(ctypes.byref(credential), 0):
        raise ctypes.WinError(ctypes.get_last_error())


def _delete_windows_credentials() -> bool:
    """删除本下载器保存在 Windows Credential Manager 中的 API 凭据。"""
    advapi32 = windows_credential_api()
    if advapi32 is None:
        return False
    if advapi32.CredDeleteW(
        WINDOWS_CREDENTIAL_TARGET,
        CRED_TYPE_GENERIC,
        0,
    ):
        return True

    error = ctypes.get_last_error()
    if error == ERROR_NOT_FOUND:
        return False
    raise ctypes.WinError(error)


def _credential_payload(api_id: int | str, api_hash: str) -> str:
    return f"{api_id}:{api_hash}"


def _parse_credential_payload(payload: str) -> tuple[str, str] | None:
    api_id, separator, api_hash = payload.strip().partition(":")
    if not separator or not api_id or not api_hash:
        return None
    return api_id, api_hash


def _run_credential_command(
    command: list[str],
    *,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise OSError(f"{command[0]}: {exc}") from exc


def _command_error(result: subprocess.CompletedProcess[str]) -> OSError:
    detail = (result.stderr or result.stdout or "").strip()
    return OSError(detail or f"credential command exited with code {result.returncode}")


def _macos_keychain_command() -> str | None:
    if sys.platform != "darwin":
        return None
    return shutil.which("security") or (
        "/usr/bin/security" if Path("/usr/bin/security").exists() else None
    )


def _linux_secret_tool() -> str | None:
    if not sys.platform.startswith("linux"):
        return None
    return shutil.which("secret-tool")


def credential_store_name() -> str | None:
    """返回当前平台可用的安全凭据存储名称。"""
    if os.name == "nt":
        return tr("Windows 凭据管理器", "Windows Credential Manager")
    if _macos_keychain_command():
        return tr("macOS 钥匙串", "macOS Keychain")
    if _linux_secret_tool():
        return tr("Linux Secret Service 密钥环", "Linux Secret Service keyring")
    return None


def load_saved_api_credentials() -> tuple[str, str] | None:
    """从当前操作系统的安全凭据存储读取 API_ID/API_HASH。"""
    if os.name == "nt":
        return _load_windows_credentials()

    security = _macos_keychain_command()
    if security:
        result = _run_credential_command(
            [
                security,
                "find-generic-password",
                "-s",
                CREDENTIAL_SERVICE,
                "-a",
                CREDENTIAL_ACCOUNT,
                "-w",
            ]
        )
        if result.returncode == 0:
            return _parse_credential_payload(result.stdout)
        if result.returncode == 44 or "could not be found" in result.stderr.lower():
            return None
        raise _command_error(result)

    secret_tool = _linux_secret_tool()
    if secret_tool:
        result = _run_credential_command(
            [
                secret_tool,
                "lookup",
                "application",
                CREDENTIAL_SERVICE,
                "account",
                CREDENTIAL_ACCOUNT,
            ]
        )
        if result.returncode != 0:
            raise _command_error(result)
        if not result.stdout.strip():
            return None
        return _parse_credential_payload(result.stdout)

    return None


def save_api_credentials(api_id: int, api_hash: str) -> bool:
    """安全保存 API 凭据；没有支持的系统存储时返回 False。"""
    if os.name == "nt":
        _save_windows_credentials(api_id, api_hash)
        return True

    payload = _credential_payload(api_id, api_hash)
    security = _macos_keychain_command()
    if security:
        result = _run_credential_command(
            [
                security,
                "add-generic-password",
                "-U",
                "-s",
                CREDENTIAL_SERVICE,
                "-a",
                CREDENTIAL_ACCOUNT,
                "-w",
                payload,
            ]
        )
        if result.returncode != 0:
            raise _command_error(result)
        return True

    secret_tool = _linux_secret_tool()
    if secret_tool:
        result = _run_credential_command(
            [
                secret_tool,
                "store",
                f"--label={CREDENTIAL_SERVICE}",
                "application",
                CREDENTIAL_SERVICE,
                "account",
                CREDENTIAL_ACCOUNT,
            ],
            input_text=payload,
        )
        if result.returncode != 0:
            raise _command_error(result)
        return True

    return False


def delete_saved_api_credentials() -> bool:
    """从当前操作系统的安全凭据存储删除 API 凭据。"""
    if os.name == "nt":
        return _delete_windows_credentials()

    security = _macos_keychain_command()
    if security:
        result = _run_credential_command(
            [
                security,
                "delete-generic-password",
                "-s",
                CREDENTIAL_SERVICE,
                "-a",
                CREDENTIAL_ACCOUNT,
            ]
        )
        if result.returncode == 0:
            return True
        if result.returncode == 44 or "could not be found" in result.stderr.lower():
            return False
        raise _command_error(result)

    secret_tool = _linux_secret_tool()
    if secret_tool:
        saved = load_saved_api_credentials()
        if saved is None:
            return False
        result = _run_credential_command(
            [
                secret_tool,
                "clear",
                "application",
                CREDENTIAL_SERVICE,
                "account",
                CREDENTIAL_ACCOUNT,
            ]
        )
        if result.returncode != 0:
            raise _command_error(result)
        return True

    return False


def read_api_credentials() -> tuple[int, str]:
    raw_id = os.getenv("TELEGRAM_API_ID") or os.getenv("TG_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH") or os.getenv("TG_API_HASH")
    prompted = False

    if not raw_id and not api_hash:
        try:
            saved = load_saved_api_credentials()
        except OSError as exc:
            saved = None
            print(
                icon_retry(
                    tr(
                        f"读取系统凭据失败，将重新询问：{exc}",
                        f"Could not read system credentials; asking again: {exc}",
                    )
                )
            )
        if saved is not None:
            raw_id, api_hash = saved
            store_name = credential_store_name() or tr("系统凭据存储", "system credential store")
            print(
                icon_done(
                    tr(
                        f"已从{store_name}读取 API 凭据",
                        f"API credentials loaded from {store_name}",
                    )
                )
            )

    if not raw_id or not api_hash:
        print()
        store_name = credential_store_name()
        if store_name:
            storage_message = tr(
                f"凭据将安全保存到{store_name}，不会写入脚本。",
                f"Credentials are stored securely in {store_name}, never in the script.",
            )
        else:
            storage_message = tr(
                "未检测到安全凭据存储，本次不会把凭据写入磁盘。Linux 可安装 secret-tool，或使用 TELEGRAM_API_ID / TELEGRAM_API_HASH 环境变量。",
                "No secure credential store was detected, so credentials will not be written to disk. On Linux, install secret-tool or use TELEGRAM_API_ID / TELEGRAM_API_HASH.",
            )
        print_panel(
            tr("首次设置", "First-time setup"),
            [
                tr(
                    "请使用你自己的 Telegram API_ID 和 API_HASH。",
                    "Use your own Telegram API_ID and API_HASH.",
                ),
                tr("获取地址：", "Get them at: ")
                + f"{P.bright_cyan}https://my.telegram.org{P.reset}"
                " → API development tools",
                f"{P.dim}{storage_message}{P.reset}",
            ],
            P.yellow,
        )
        print()

    if not raw_id:
        raw_id = input(f"{P.bright_cyan}❯{P.reset} API_ID: ").strip()
        prompted = True
    if not api_hash:
        api_hash = getpass.getpass(
            f"{P.bright_cyan}❯{P.reset} "
            f"{tr('API_HASH（输入时不显示）:', 'API_HASH (hidden):')} "
        ).strip()
        prompted = True

    try:
        api_id = int(raw_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(tr("API_ID 必须是整数", "API_ID must be an integer")) from exc

    if api_id <= 0:
        raise ValueError(tr("API_ID 必须大于 0", "API_ID must be greater than 0"))
    if not re.fullmatch(r"[0-9a-fA-F]{32}", api_hash):
        raise ValueError(
            tr(
                "API_HASH 应为 32 位十六进制字符串",
                "API_HASH must be a 32-character hexadecimal string",
            )
        )

    if prompted:
        try:
            saved = save_api_credentials(api_id, api_hash)
            if saved:
                print(
                    icon_done(
                        tr(
                            "API 凭据已安全保存，后续启动无需重复输入",
                            "API credentials saved securely; you will not be asked again",
                        )
                    )
                )
            else:
                print(
                    icon_skip(
                        tr(
                            "未找到可用的安全凭据存储，API 凭据仅用于本次运行",
                            "No secure credential store is available; API credentials are used for this run only",
                        )
                    )
                )
        except OSError as exc:
            print(
                icon_retry(
                    tr(
                        f"保存到系统凭据存储失败：{exc}",
                        f"Could not save to the system credential store: {exc}",
                    )
                )
            )

    return api_id, api_hash


def sanitize_name(value: str, fallback: str) -> str:
    value = SAFE_NAME_RE.sub("_", value).strip("._-")
    return value[:80] or fallback


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def classify_media(message: Any) -> str | None:
    if getattr(message, "photo", None) is not None:
        return "image"

    document = getattr(message, "document", None)
    if document is None or getattr(message, "sticker", None) is not None:
        return None

    mime_type = (getattr(document, "mime_type", "") or "").lower()
    if mime_type.startswith("video/"):
        return "video"
    if mime_type.startswith("image/"):
        return "image"
    return None


def media_extension(message: Any, kind: str) -> str:
    if getattr(message, "photo", None) is not None:
        return ".jpg"

    file_info = getattr(message, "file", None)
    extension = (getattr(file_info, "ext", "") or "").lower()
    if re.fullmatch(r"\.[0-9a-z]{1,8}", extension):
        return extension

    document = getattr(message, "document", None)
    mime_type = (getattr(document, "mime_type", "") or "").lower()
    guessed = mimetypes.guess_extension(mime_type, strict=False)
    if guessed and re.fullmatch(r"\.[0-9a-z]{1,8}", guessed):
        return guessed
    return ".mp4" if kind == "video" else ".jpg"


def expected_media_size(message: Any) -> int | None:
    file_info = getattr(message, "file", None)
    size = getattr(file_info, "size", None)
    if isinstance(size, int) and size > 0:
        return size
    return None


async def resolve_album_messages(
    client: TelegramClient,
    entity: Any,
    message_id: int,
) -> list[Any]:
    target = await client.get_messages(entity, ids=message_id)
    if target is None:
        raise RuntimeError(
            tr(
                f"找不到帖子 {message_id}，或当前账号无权访问",
                f"Post {message_id} was not found or this account cannot access it",
            )
        )

    grouped_id = getattr(target, "grouped_id", None)
    if grouped_id is None:
        return [target]

    # Telegram 相册最多 10 项；向前后多取一些编号以兼容帖子链接
    # 指向相册中间项的情况。
    first_id = max(1, message_id - 32)
    nearby_ids = list(range(first_id, message_id + 33))
    nearby = await client.get_messages(entity, ids=nearby_ids)
    album = [
        message
        for message in nearby
        if message is not None and getattr(message, "grouped_id", None) == grouped_id
    ]
    album.sort(key=lambda message: message.id)
    return album or [target]


async def resolve_entity(client: TelegramClient, post: TelegramPost) -> Any:
    try:
        return await client.get_entity(post.entity)
    except (ValueError, RPCError):
        if isinstance(post.entity, int):
            # 私有频道链接需要账号已加入；加载会话列表可补齐实体缓存。
            await client.get_dialogs(limit=None)
            return await client.get_entity(post.entity)
        raise


async def resolve_comment_entity(
    client: TelegramClient,
    channel_entity: Any,
    channel_message_id: int,
) -> Any:
    """解析频道帖子的关联讨论组，用于读取 ?comment= 指向的消息。"""
    discussion = await client(
        functions.messages.GetDiscussionMessageRequest(
            peer=channel_entity,
            msg_id=channel_message_id,
        )
    )
    if not getattr(discussion, "messages", None):
        raise RuntimeError(
            tr(
                "该频道帖子没有可访问的评论区",
                "This channel post has no accessible discussion",
            )
        )

    # Telegram 官方约定：返回结果按 ID 倒序排列，最后一条是讨论组中
    # 自动转发的频道帖子；它的 peer_id 就是关联讨论组。
    discussion_root = discussion.messages[-1]
    discussion_peer = getattr(discussion_root, "peer_id", None)
    if discussion_peer is None:
        raise RuntimeError(
            tr(
                "无法识别该帖子的关联讨论组",
                "Could not identify the discussion linked to this post",
            )
        )

    try:
        return await client.get_input_entity(discussion_peer)
    except ValueError:
        peer_numeric_id = (
            getattr(discussion_peer, "channel_id", None)
            or getattr(discussion_peer, "chat_id", None)
        )
        for chat in getattr(discussion, "chats", []):
            if getattr(chat, "id", None) == peer_numeric_id:
                return await client.get_input_entity(chat)
        raise RuntimeError(
            tr(
                "当前账号无法访问该帖子的关联讨论组",
                "This account cannot access the discussion linked to the post",
            )
        )


async def download_one_media(
    client: TelegramClient,
    entity: Any,
    message: Any,
    kind: str,
    index: int,
    total_items: int,
    channel_name: str,
    post_id: int | str,
    output_dir: Path,
    overwrite: bool,
    semaphore: asyncio.Semaphore,
    retries: int,
    progress: BatchProgress,
) -> str:
    extension = media_extension(message, kind)
    filename = f"{channel_name}_{post_id}_{index:02d}{extension}"
    destination = output_dir / filename
    temporary = output_dir / f".{filename}.part"
    expected_size = expected_media_size(message)
    progress.set_expected(filename, expected_size)

    if destination.exists() and not overwrite:
        actual_size = destination.stat().st_size
        progress.complete_item(filename, actual_size)
        progress.log(
            icon_skip(
                tr(
                    f"[{index}/{total_items}] 已存在，跳过："
                    f"{filename}（{format_bytes(actual_size)}）",
                    f"[{index}/{total_items}] Already exists, skipped: "
                    f"{filename} ({format_bytes(actual_size)})",
                )
            )
        )
        return "skipped"

    async with semaphore:
        for attempt in range(retries + 1):
            if temporary.exists():
                temporary.unlink()
            progress.reset_item(filename)
            progress.log(
                icon_download(
                    tr(
                        f"[{index}/{total_items}] "
                        f"下载{('视频' if kind == 'video' else '图片')}："
                        f"{P.bold}{filename}{P.reset}",
                        f"[{index}/{total_items}] Downloading "
                        f"{'video' if kind == 'video' else 'image'}: "
                        f"{P.bold}{filename}{P.reset}",
                    )
                )
            )

            try:
                result = await client.download_media(
                    message,
                    file=str(temporary),
                    progress_callback=progress.callback(filename),
                )
                if result is None or not temporary.is_file():
                    raise IncompleteDownloadError(
                        tr(
                            "Telegram 未返回下载文件",
                            "Telegram did not return a downloaded file",
                        )
                    )

                actual_size = temporary.stat().st_size
                if actual_size <= 0:
                    raise IncompleteDownloadError(
                        tr("下载结果为空文件", "The downloaded file is empty")
                    )
                if expected_size is not None and actual_size != expected_size:
                    raise IncompleteDownloadError(
                        tr(
                            f"文件大小不完整：应为 {expected_size}，实际为 {actual_size}",
                            f"Incomplete file size: expected {expected_size}, got {actual_size}",
                        )
                    )

                os.replace(temporary, destination)
                progress.complete_item(filename, actual_size)
                progress.log(
                    icon_done(
                        tr(
                            f"[{index}/{total_items}] 完成："
                            f"{filename}（{format_bytes(actual_size)}）",
                            f"[{index}/{total_items}] Complete: "
                            f"{filename} ({format_bytes(actual_size)})",
                        )
                    )
                )
                return "downloaded"
            except FloodWaitError as exc:
                if attempt >= retries:
                    raise
                delay = int(getattr(exc, "seconds", 1)) + 1
                if delay > 300:
                    raise RuntimeError(
                        tr(
                            f"Telegram 要求等待 {delay} 秒，请稍后重新运行",
                            f"Telegram requires a {delay}-second wait; run the downloader again later",
                        )
                    ) from exc
                reason = tr(
                    f"Telegram 限流 {delay} 秒",
                    f"Telegram rate limit: {delay} seconds",
                )
            except (
                FileReferenceExpiredError,
                IncompleteDownloadError,
                RpcCallFailError,
                ServerError,
                TimedOutError,
                asyncio.TimeoutError,
                ConnectionError,
            ) as exc:
                if attempt >= retries:
                    raise
                delay = min(30.0, 2.0 ** attempt) + random.uniform(0.0, 0.8)
                reason = str(exc) or exc.__class__.__name__

            if temporary.exists():
                temporary.unlink()

            # 每次重试前重新获取消息，刷新可能过期的 file_reference。
            try:
                refreshed = await client.get_messages(entity, ids=message.id)
                if refreshed is not None:
                    message = refreshed
                    refreshed_size = expected_media_size(message)
                    if refreshed_size is not None:
                        expected_size = refreshed_size
                        progress.set_expected(filename, refreshed_size)
            except RPCError:
                pass

            progress.log(
                icon_retry(
                    tr(
                        f"[{index}/{total_items}] 第 {attempt + 1}/{retries} 次重试，"
                        f"{delay:.1f} 秒后继续：{P.dim}{reason}{P.reset}",
                        f"[{index}/{total_items}] Retry {attempt + 1}/{retries}; "
                        f"continuing in {delay:.1f}s: {P.dim}{reason}{P.reset}",
                    )
                )
            )
            await asyncio.sleep(delay)

    raise RuntimeError(
        tr(f"下载未完成：{filename}", f"Download did not complete: {filename}")
    )


async def download_post(
    client: TelegramClient,
    post: TelegramPost,
    output_dir: Path,
    overwrite: bool,
    jobs: int,
    retries: int,
) -> tuple[int, int]:
    channel_entity = await resolve_entity(client, post)
    media_entity = channel_entity
    media_message_id = post.message_id
    filename_post_id: int | str = post.message_id
    if post.comment_id is not None:
        media_entity = await resolve_comment_entity(
            client,
            channel_entity,
            post.message_id,
        )
        media_message_id = post.comment_id
        filename_post_id = f"{post.message_id}_comment_{post.comment_id}"

    messages = await resolve_album_messages(
        client,
        media_entity,
        media_message_id,
    )
    media_messages: list[tuple[Any, str]] = []
    for message in messages:
        kind = classify_media(message)
        if kind is not None:
            media_messages.append((message, kind))

    if not media_messages:
        raise RuntimeError(
            tr(
                "该帖子中没有可下载的图片或视频",
                "This post contains no downloadable images or videos",
            )
        )

    username = getattr(channel_entity, "username", None) or post.channel_label
    channel_name = sanitize_name(str(username), post.channel_label)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_count = sum(kind == "image" for _, kind in media_messages)
    video_count = sum(kind == "video" for _, kind in media_messages)
    print()
    print_panel(
        tr("找到完整媒体组", "Complete media group found"),
        [
            f"{tr('来源', 'Source')}　{P.bold}@{channel_name}{P.reset} · "
            f"{tr('帖子', 'Post')} {P.bold}#{post.message_id}{P.reset}"
            + (
                f" · {tr('评论', 'Comment')} {P.bold}#{post.comment_id}{P.reset}"
                if post.comment_id is not None
                else ""
            ),
            tr(
                f"数量　{P.bold}{len(media_messages)} 项{P.reset}"
                f"（图片 {image_count}，视频 {video_count}）",
                f"Items　{P.bold}{len(media_messages)}{P.reset} "
                f"(images {image_count}, videos {video_count})",
            ),
            f"{tr('目录', 'Folder')}　{P.bright_cyan}{output_dir}{P.reset}",
        ],
        P.bright_cyan,
    )

    total_items = len(media_messages)
    semaphore = asyncio.Semaphore(jobs)
    progress = BatchProgress(total_items)
    tasks = [
        asyncio.create_task(
            download_one_media(
                client=client,
                entity=media_entity,
                message=message,
                kind=kind,
                index=index,
                total_items=total_items,
                channel_name=channel_name,
                post_id=filename_post_id,
                output_dir=output_dir,
                overwrite=overwrite,
                semaphore=semaphore,
                retries=retries,
                progress=progress,
            )
        )
        for index, (message, kind) in enumerate(media_messages, start=1)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    progress.finish()

    failures = [result for result in results if isinstance(result, BaseException)]
    downloaded = sum(result == "downloaded" for result in results)
    skipped = sum(result == "skipped" for result in results)
    if failures:
        details = "; ".join(
            f"{failure.__class__.__name__}: {failure}" for failure in failures
        )
        raise RuntimeError(
            tr(
                f"{len(failures)} 个媒体下载失败；成功 {downloaded}，"
                f"跳过 {skipped}。{details}",
                f"{len(failures)} media downloads failed; {downloaded} succeeded, "
                f"{skipped} skipped. {details}",
            )
        )

    print()
    print(
        icon_done(
            tr(
                f"{P.bold}帖子完成{P.reset}：新下载 {P.green}{downloaded}{P.reset} 项 · "
                f"跳过 {skipped} 项 · 共 {total_items} 项",
                f"{P.bold}Post complete{P.reset}: "
                f"{P.green}{downloaded}{P.reset} downloaded · "
                f"{skipped} skipped · {total_items} total",
            )
        )
    )
    return downloaded, skipped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=tr(
            "下载 Telegram 帖子整组最高质量图片和视频",
            "Download the complete highest-quality image and video group from a Telegram post",
        )
    )
    parser.add_argument(
        "url",
        nargs="?",
        help=tr(
            "例如 https://t.me/ExampleChannel/37?single",
            "Example: https://t.me/ExampleChannel/37?single",
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_DOWNLOAD_DIR,
        help=tr(
            f"下载目录（默认：{DEFAULT_DOWNLOAD_DIR}）",
            f"Download folder (default: {DEFAULT_DOWNLOAD_DIR})",
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=tr(
            "覆盖已经存在的同名文件",
            "Overwrite files that already exist",
        ),
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=3,
        help=tr(
            "相册并发下载数，1-8（默认：3）",
            "Parallel album downloads, 1-8 (default: 3)",
        ),
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=5,
        help=tr(
            "网络失败后的重试次数，0-10（默认：5）",
            "Retries after a network failure, 0-10 (default: 5)",
        ),
    )
    parser.add_argument(
        "--forget-credentials",
        action="store_true",
        help=tr(
            "从系统安全凭据存储删除 API_ID/API_HASH 后退出",
            "Delete API_ID/API_HASH from the system credential store and exit",
        ),
    )
    parser.add_argument(
        "--lang",
        choices=("zh", "en"),
        default=LANGUAGE,
        help=tr(
            "界面语言：zh 或 en（默认：zh）",
            "Interface language: zh or en (default: en for this command)",
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


async def run_downloader(args: argparse.Namespace) -> int:
    if args.forget_credentials:
        print_banner()
        try:
            removed = delete_saved_api_credentials()
        except OSError as exc:
            print(
                icon_error(
                    tr(
                        f"删除系统凭据失败：{exc}",
                        f"Could not delete system credentials: {exc}",
                    )
                ),
                file=sys.stderr,
            )
            return 1
        if removed:
            print(
                icon_done(
                    tr(
                        "已删除保存的 API_ID/API_HASH",
                        "Saved API_ID/API_HASH credentials deleted",
                    )
                )
            )
        else:
            print(
                icon_skip(
                    tr(
                        "没有找到已保存的 API 凭据",
                        "No saved API credentials were found",
                    )
                )
            )
        return 0

    if not 1 <= args.jobs <= 8:
        print(
            icon_error(
                tr(
                    "输入错误：--jobs 必须在 1 到 8 之间",
                    "Input error: --jobs must be between 1 and 8",
                )
            ),
            file=sys.stderr,
        )
        return 2
    if not 0 <= args.retries <= 10:
        print(
            icon_error(
                tr(
                    "输入错误：--retries 必须在 0 到 10 之间",
                    "Input error: --retries must be between 0 and 10",
                )
            ),
            file=sys.stderr,
        )
        return 2

    print_banner()

    first_url = args.url
    if first_url is None:
        print()
        first_url = ask(
            tr(
                "粘贴 Telegram 帖子链接（直接回车退出）:",
                "Paste a Telegram post URL (press Enter to exit):",
            )
        )
        if not first_url:
            return 0

    try:
        first_post = parse_post_url(first_url)
        api_id, api_hash = read_api_credentials()
    except ValueError as exc:
        print(
            icon_error(tr(f"输入错误：{exc}", f"Input error: {exc}")),
            file=sys.stderr,
        )
        return 2

    client = TelegramClient(
        str(SESSION_PATH),
        api_id,
        api_hash,
        device_model="Telegram Media Downloader",
        app_version=__version__,
        lang_code="en" if LANGUAGE == "en" else "zh-hans",
        system_lang_code="en" if LANGUAGE == "en" else "zh-hans",
        request_retries=5,
        connection_retries=5,
        retry_delay=1,
        auto_reconnect=True,
        flood_sleep_threshold=60,
        receive_updates=False,
    )

    try:
        print()
        print(icon_wait(tr("正在连接 Telegram …", "Connecting to Telegram …")))
        await client.start()
        print(
            icon_done(
                tr(
                    f"Telegram {P.bold}登录成功{P.reset}",
                    f"Telegram {P.bold}login successful{P.reset}",
                )
            )
        )

        current_post: TelegramPost | None = first_post
        while current_post is not None:
            try:
                await download_post(
                    client,
                    current_post,
                    args.output.resolve(),
                    args.overwrite,
                    args.jobs,
                    args.retries,
                )
            except (RPCError, RuntimeError, ValueError, OSError) as exc:
                print(
                    icon_error(
                        tr(f"下载失败：{exc}", f"Download failed: {exc}")
                    ),
                    file=sys.stderr,
                )
                if args.url is not None:
                    return 1

            if args.url is not None:
                break

            print()
            next_url = ask(
                tr(
                    "继续粘贴下一条帖子链接（直接回车退出）:",
                    "Paste another post URL (press Enter to exit):",
                )
            )
            if not next_url:
                current_post = None
                continue
            try:
                current_post = parse_post_url(next_url)
            except ValueError as exc:
                print(
                    icon_error(
                        tr(f"输入错误：{exc}", f"Input error: {exc}")
                    ),
                    file=sys.stderr,
                )
                current_post = None

        return 0
    except sqlite3.OperationalError as exc:
        if "database is locked" in str(exc).lower():
            print(
                icon_error(
                    tr(
                        "已有一个下载器窗口正在运行。请关闭旧窗口或等待其完成后再试。",
                        "Another downloader window is already running. Close it or wait for it to finish, then try again.",
                    )
                ),
                file=sys.stderr,
            )
            return 1
        raise
    finally:
        try:
            await client.disconnect()
        except sqlite3.OperationalError as exc:
            if "database is locked" not in str(exc).lower():
                raise


def main() -> int:
    global LANGUAGE
    LANGUAGE = requested_language()
    setup_terminal()
    parser = build_parser()
    args = parser.parse_args()
    LANGUAGE = args.lang
    try:
        return asyncio.run(run_downloader(args))
    except KeyboardInterrupt:
        print(f"\n{P.yellow}{tr('已取消。', 'Cancelled.')}{P.reset}")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
