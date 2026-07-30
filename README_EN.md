<p align="center">
  <a href="README.md">简体中文</a> · <strong>English</strong>
</p>

<div align="center">
  <img src="assets/logo.svg" width="112" alt="Telegram Media Downloader logo">
  <h1>Telegram Media Downloader</h1>
  <p><strong>One link. Every original-quality Telegram image and video.</strong></p>
  <p>Download complete albums, individual videos, and discussion media with no config file, plus built-in parallel downloads, retries, and integrity checks.</p>

  <p>
    <a href="https://github.com/swttttt/telegram-media-downloader/releases/latest"><img alt="Download cross-platform builds" src="https://img.shields.io/badge/Download-Windows_%7C_Linux_%7C_macOS-22C55E?style=for-the-badge"></a>
    <a href="https://github.com/swttttt/telegram-media-downloader/actions/workflows/ci.yml"><img alt="Quality checks" src="https://img.shields.io/github/actions/workflow/status/swttttt/telegram-media-downloader/ci.yml?branch=main&style=for-the-badge&label=checks"></a>
    <a href="https://github.com/swttttt/telegram-media-downloader/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/swttttt/telegram-media-downloader?style=for-the-badge&logo=github&color=FBBF24"></a>
    <img alt="MIT License" src="https://img.shields.io/badge/License-MIT-3B82F6?style=for-the-badge">
  </p>
</div>

<div align="center">
  <a href="https://github.com/swttttt/telegram-media-downloader/releases/latest"><strong>⬇️ Download for Windows, Linux, or macOS</strong></a>
</div>

<br>

<div align="center">
  <img src="assets/demo.gif" width="100%" alt="Anonymous bilingual download-flow demo">
</div>

> ⭐ If this project saves you time, consider starring it. Your support helps other people discover it.

## What it solves

Saving a Telegram album from the web client often means clicking every item, while media inside discussions can be hard to organize. This tool resolves one post URL into the complete media group and saves the files provided by Telegram’s API—without screenshots, transcoding, or recompression.

| Capability | This project | Browser save | Typical CLI script |
| --- | :---: | :---: | :---: |
| Complete album from one URL | ✅ | ❌ | Varies |
| Discussion `?comment=` media | ✅ | Manual | Rare |
| Original files provided by Telegram | ✅ | Inconsistent | Varies |
| Native Windows / Linux / macOS build | ✅ | — | Usually needs Python |
| Chinese and English UI | ✅ | — | Usually one language |
| Secure OS credential store | ✅ | — | Often plain-text config |
| Parallelism, retries, integrity checks | ✅ | ❌ | Varies |

## Fastest start: portable builds

Open [Releases](https://github.com/swttttt/telegram-media-downloader/releases/latest) and choose the archive for your system:

| System | Asset | Start |
| --- | --- | --- |
| Windows x64 | `*-windows-x64.zip` | Extract and double-click `start.bat` |
| Linux x64 | `*-linux-x64.tar.gz` | Extract and run `./start.sh` |
| macOS Apple Silicon | `*-macos-arm64.tar.gz` | Extract and run `./start.sh` |
| macOS Intel | `*-macos-x64.tar.gz` | Extract and run `./start.sh` |

On Linux or macOS:

```bash
mkdir TelegramMediaDownloader
tar -xzf TelegramMediaDownloader-v*-linux-x64.tar.gz -C TelegramMediaDownloader  # use the matching macOS name when applicable
cd TelegramMediaDownloader
./start.sh
```

Paste a Telegram post URL. Media is saved in the `download` folder beside the program.

> The first run asks for your own `API_ID` and `API_HASH`. Create them under **API development tools** at [my.telegram.org](https://my.telegram.org). They are not your account password. The app stores them in Windows Credential Manager, macOS Keychain, or Linux Secret Service.

### Linux keyring

The Linux build uses `secret-tool` to access the desktop keyring. Install it with `sudo apt install libsecret-tools` on Ubuntu / Debian, `sudo dnf install libsecret` on Fedora, or `sudo pacman -S libsecret` on Arch Linux. Without a usable keyring the downloader still works, but it will not write API credentials to disk. You can also provide `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` as environment variables.

### First launch on macOS

The release is not currently signed with an Apple Developer ID. If macOS blocks the first launch, approve **Open Anyway** under **System Settings → Privacy & Security**, then run `./start.sh` again. Confirm that the archive came from this project’s Releases page and optionally verify its included SHA-256 checksum first.

## Supported URLs

```text
# Public channel post or album
https://t.me/ExampleChannel/37

# Telegram's single form
https://t.me/ExampleChannel/37?single

# Media inside a channel discussion
https://t.me/ExampleChannel/737?single&comment=7145

# A private channel the current account has joined
https://t.me/c/1234567890/321
```

The downloader detects the complete media group and generates collision-resistant names for its images and videos.

## Run from source

Windows, Linux, and macOS are supported with Python 3.10 or newer:

```bash
git clone https://github.com/swttttt/telegram-media-downloader.git
cd telegram-media-downloader
python3 -m pip install -r requirements.txt
python3 telegram_media_downloader.py --lang en
```

On Windows, double-click `start.bat`. On Linux or macOS, run `./start.sh`. The launcher checks dependencies and lets you choose the interface language.

## Command-line usage

```powershell
# Download a post
python telegram_media_downloader.py "https://t.me/ExampleChannel/37?single" --lang en

# Choose a destination
python telegram_media_downloader.py URL --output "D:\Telegram" --lang en

# Replace existing same-name files
python telegram_media_downloader.py URL --overwrite --lang en

# Customize parallelism and retries
python telegram_media_downloader.py URL --jobs 4 --retries 6 --lang en

# Delete stored API credentials
python telegram_media_downloader.py --forget-credentials --lang en
```

| Option | Purpose | Default |
| --- | --- | --- |
| `url` | Telegram post, album, or discussion URL | Interactive prompt |
| `-o, --output` | Media destination | `download` beside the app |
| `--overwrite` | Replace existing same-name files | Off |
| `-j, --jobs` | Parallel downloads, from 1 to 8 | `3` |
| `--retries` | Retries after network failures, from 0 to 10 | `5` |
| `--forget-credentials` | Remove API credentials from the secure OS credential store | — |
| `--lang` | Interface language: `zh` or `en` | `zh` |
| `--version` | Print the application version | — |

## Why it is fast and reliable

- `cryptg` accelerates Telegram media decryption, with several media items processed in parallel by default.
- Network timeouts, temporary Telegram failures, and expired `file_reference` values recover automatically.
- Telegram flood waits are respected instead of being retried aggressively.
- Downloads go to hidden `.part` files and are atomically moved into place only after size validation.
- Existing files are skipped by default, so running the same URL again does not waste bandwidth.
- A local session is protected against simultaneous writes that could corrupt its SQLite database.

## Privacy and security

- API credentials are kept in Windows Credential Manager, macOS Keychain, or Linux Secret Service—not source code or a plain-text config file.
- Telegram sessions, downloads, caches, and local build folders are excluded by `.gitignore`.
- Project screenshots and demo data are anonymous and contain no channel, group, account, post URL, or local path.
- A session file represents local authorization and must never be uploaded or shared. Only download content you have permission to access and save.

## FAQ

<details>
<summary><strong>Why are API_ID and API_HASH required?</strong></summary>
<br>
Telegram user clients must connect using an official API application identity. These values are not a Bot Token or your account password. A project author cannot safely distribute one public credential pair to every user.
</details>

<details>
<summary><strong>Are files compressed?</strong></summary>
<br>
No. The downloader saves media returned by the Telegram API without transcoding or recompression.
</details>

<details>
<summary><strong>Why does a private-channel URL fail?</strong></summary>
<br>
The currently signed-in Telegram account must already be a member of that channel and have permission to view the target message.
</details>

<details>
<summary><strong>Why does it say another downloader is running?</strong></summary>
<br>
The Telegram login session is stored in SQLite and cannot be written by two processes at the same time. Close the old window or wait for it to finish.
</details>

## Contributing

Bug reports, feature requests, and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before getting started; release history is in [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE) © 2026 [swttttt](https://github.com/swttttt)
