<p align="center">
  <strong>简体中文</strong> · <a href="README_EN.md">English</a>
</p>

<div align="center">
  <img src="assets/logo.svg" width="112" alt="Telegram Media Downloader logo">
  <h1>Telegram Media Downloader</h1>
  <p><strong>一条链接，完整保存 Telegram 原画质图片与视频。</strong></p>
  <p>支持整组相册、单视频和评论区媒体；无需配置文件，并发下载、智能重试与完整性校验全部内置。</p>

  <p>
    <a href="https://github.com/swttttt/telegram-media-downloader/releases/latest"><img alt="下载 Windows 版" src="https://img.shields.io/badge/下载-Windows_免安装版-22C55E?style=for-the-badge&logo=windows&logoColor=white"></a>
    <a href="https://github.com/swttttt/telegram-media-downloader/actions/workflows/ci.yml"><img alt="Quality checks" src="https://img.shields.io/github/actions/workflow/status/swttttt/telegram-media-downloader/ci.yml?branch=main&style=for-the-badge&label=checks"></a>
    <a href="https://github.com/swttttt/telegram-media-downloader/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/swttttt/telegram-media-downloader?style=for-the-badge&logo=github&color=FBBF24"></a>
    <img alt="MIT License" src="https://img.shields.io/badge/License-MIT-3B82F6?style=for-the-badge">
  </p>
</div>

<div align="center">
  <a href="https://github.com/swttttt/telegram-media-downloader/releases/latest"><strong>⬇️ 下载最新版 Windows 免安装包</strong></a>
</div>

<br>

<div align="center">
  <img src="assets/demo.gif" width="100%" alt="匿名化的双语下载流程演示">
</div>

> ⭐ 如果它替你省下了时间，欢迎点一个 Star。你的支持会帮助更多人发现这个项目。

## 它解决什么问题

Telegram 网页端保存相册时，常常需要逐项点击，评论区媒体也难以整理。本工具把一个帖子链接解析成完整媒体组，直接保存 Telegram API 提供的原始文件，不截图、不转码、不二次压缩。

| 能力 | 本项目 | 浏览器逐个保存 | 通用命令行脚本 |
| --- | :---: | :---: | :---: |
| 一个链接下载完整相册 | ✅ | ❌ | 视脚本而定 |
| 评论区 `?comment=` 媒体 | ✅ | 手动查找 | 很少支持 |
| Telegram 提供的原始质量 | ✅ | 不稳定 | 视脚本而定 |
| Windows 免安装 EXE | ✅ | — | 通常需要 Python |
| 中文 / English | ✅ | — | 通常单语言 |
| Windows 凭据管理器 | ✅ | — | 通常明文配置 |
| 并发、重试、完整性校验 | ✅ | ❌ | 视脚本而定 |

## 最快开始：Windows 免安装版

1. 打开 [Releases](https://github.com/swttttt/telegram-media-downloader/releases/latest)，下载 `TelegramMediaDownloader-v*-windows-x64.zip`。
2. 解压后双击 `start.bat`，选择简体中文或 English。
3. 粘贴 Telegram 帖子链接并回车。媒体默认保存到程序旁边的 `download` 文件夹。

也可以直接运行 `TelegramMediaDownloader.exe`，默认使用中文界面。

> 首次运行需要输入自己的 `API_ID` 和 `API_HASH`。请在 [my.telegram.org](https://my.telegram.org) 的 **API development tools** 页面创建。它们不是账号密码；输入一次后会保存在 Windows 凭据管理器中。

## 支持的链接

```text
# 公开频道帖子或相册
https://t.me/ExampleChannel/37

# Telegram 的 single 形式
https://t.me/ExampleChannel/37?single

# 频道帖子评论区中的媒体
https://t.me/ExampleChannel/737?single&comment=7145

# 当前账号已加入的私有频道
https://t.me/c/1234567890/321
```

程序会自动识别同一帖子的完整媒体组，并为图片和视频生成不冲突的文件名。

## 从源码运行

需要 Windows 10/11 与 Python 3.10 或更高版本：

```powershell
git clone https://github.com/swttttt/telegram-media-downloader.git
cd telegram-media-downloader
python -m pip install -r requirements.txt
python telegram_media_downloader.py
```

双击源码目录中的 `start.bat` 也可以完成依赖检查并选择界面语言。

## 命令行用法

```powershell
# 下载指定帖子
python telegram_media_downloader.py "https://t.me/ExampleChannel/37?single"

# 指定保存目录
python telegram_media_downloader.py URL --output "D:\Telegram"

# 英文界面
python telegram_media_downloader.py URL --lang en

# 覆盖同名文件
python telegram_media_downloader.py URL --overwrite

# 自定义并发和重试
python telegram_media_downloader.py URL --jobs 4 --retries 6

# 删除安全保存的 API 凭据
python telegram_media_downloader.py --forget-credentials
```

| 参数 | 作用 | 默认值 |
| --- | --- | --- |
| `url` | Telegram 帖子、相册或评论链接 | 交互粘贴 |
| `-o, --output` | 媒体保存目录 | 程序旁的 `download` |
| `--overwrite` | 覆盖已存在的同名文件 | 关闭 |
| `-j, --jobs` | 并发下载数，范围 1–8 | `3` |
| `--retries` | 网络失败重试次数，范围 0–10 | `5` |
| `--forget-credentials` | 删除 Windows 凭据管理器中的 API 凭据 | — |
| `--lang` | 界面语言：`zh` 或 `en` | `zh` |
| `--version` | 显示版本号 | — |

## 快且稳定的原因

- 使用 `cryptg` 加速 Telegram 媒体解密，默认并行处理多个媒体项。
- 网络超时、临时服务异常和过期 `file_reference` 会自动恢复。
- 遇到 Telegram 限流时按服务端要求等待，而不是高频无效重试。
- 先写入隐藏 `.part` 文件，通过大小校验后再原子替换，避免留下伪装成成品的残缺文件。
- 已存在文件默认跳过，重复执行同一链接不会浪费流量。
- 单个本地会话只允许一个程序实例写入，降低 SQLite 会话损坏风险。

## 隐私与安全

- API 凭据保存在 Windows 凭据管理器，不写入源码或明文配置文件。
- `telegram_media.session`、下载内容、缓存和构建目录均已被 `.gitignore` 排除。
- 项目发布配图和演示数据全部匿名化，不包含频道、群组、账号、帖子链接或本机路径。
- 登录会话相当于本机授权，请勿上传或分享。只下载你有权访问与保存的内容。

## 常见问题

<details>
<summary><strong>为什么必须填写 API_ID / API_HASH？</strong></summary>
<br>
Telegram 用户客户端必须使用官方 API 应用身份连接。它们不是 Bot Token，也不是你的账号密码。Telegram 不允许项目作者把一套公共凭据安全地分发给所有用户。
</details>

<details>
<summary><strong>文件会被压缩吗？</strong></summary>
<br>
不会。程序直接保存 Telegram API 返回的媒体文件，不进行转码或二次压缩。
</details>

<details>
<summary><strong>为什么私有频道链接无法下载？</strong></summary>
<br>
当前登录的 Telegram 账号必须已经加入该频道，并拥有查看目标消息的权限。
</details>

<details>
<summary><strong>为什么提示另一个下载器正在运行？</strong></summary>
<br>
Telegram 登录会话由 SQLite 保存，同一会话不能被两个进程同时写入。关闭旧窗口或等待它完成后再运行。
</details>

## 参与项目

欢迎提交 [Bug](https://github.com/swttttt/telegram-media-downloader/issues/new?template=bug_report.yml)、[功能建议](https://github.com/swttttt/telegram-media-downloader/issues/new?template=feature_request.yml) 或 Pull Request。开始前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)；版本变化见 [CHANGELOG.md](CHANGELOG.md)。

## License

[MIT](LICENSE) © 2026 [swttttt](https://github.com/swttttt)
