#!/usr/bin/env bash
set -u

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$project_dir" || exit 1

printf '\n  Telegram Media Downloader\n'
printf '  -------------------------\n'
printf '  [1] 简体中文\n'
printf '  [2] English\n\n'
printf '请选择语言 / Choose language [1]: '
IFS= read -r language_choice

if [ "${language_choice:-1}" = "2" ]; then
    app_language="en"
else
    app_language="zh"
fi
printf '\n'

if [ -x "$project_dir/TelegramMediaDownloader" ]; then
    exec "$project_dir/TelegramMediaDownloader" --lang "$app_language"
fi

python_command="${PYTHON:-python3}"
if ! command -v "$python_command" >/dev/null 2>&1; then
    printf '%s\n' '[错误 / Error] 未找到 Python / Python was not found.' >&2
    printf '%s\n' '请安装 Python 3.10 或更高版本 / Install Python 3.10 or later:' >&2
    printf '%s\n' 'https://www.python.org/downloads/' >&2
    exit 1
fi

if ! "$python_command" -c "import telethon, cryptg" >/dev/null 2>&1; then
    printf '%s\n' '正在安装运行依赖 / Installing dependencies...'
    "$python_command" -m pip install -r requirements.txt || {
        printf '%s\n' '[错误 / Error] 依赖安装失败 / Dependency installation failed.' >&2
        exit 1
    }
fi

exec "$python_command" telegram_media_downloader.py --lang "$app_language"
