@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Telegram Media Downloader

echo.
echo   Telegram Media Downloader
echo   ─────────────────────────
echo   [1] 简体中文
echo   [2] English
echo.
set /p "TMD_LANGUAGE=请选择语言 / Choose language [1]: "
if "%TMD_LANGUAGE%"=="2" (
    set "TMD_LANG=en"
) else (
    set "TMD_LANG=zh"
)
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [错误 / Error] 未找到 Python / Python was not found.
    echo 请安装 Python 3.10 或更高版本 / Install Python 3.10 or later:
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import telethon, cryptg" >nul 2>&1
if errorlevel 1 (
    echo 正在安装运行依赖 / Installing dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误 / Error] 依赖安装失败 / Dependency installation failed.
        pause
        exit /b 1
    )
)

python telegram_media_downloader.py --lang %TMD_LANG%
echo.
pause
