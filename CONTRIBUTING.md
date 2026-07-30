# Contributing

Thanks for helping improve Telegram Media Downloader.

## Before opening an issue

- Use the latest release.
- Search existing issues first.
- Never attach `telegram_media.session`, API credentials, phone numbers, private URLs, or downloaded media.
- Replace channel names, message IDs, usernames, and local paths with anonymous examples.

## Development setup

```powershell
git clone https://github.com/swttttt/telegram-media-downloader.git
cd telegram-media-downloader
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
```

Run the application with:

```powershell
python telegram_media_downloader.py --lang en
```

Build the Windows package with:

```powershell
.\build_release.ps1
```

## Pull requests

- Keep changes focused and explain the user-visible result.
- Add or update tests for parsing and behavior changes.
- Update both `README.md` and `README_EN.md` when user-facing behavior changes.
- Preserve credential safety, `.part` downloads, integrity checks, and session locking.
- Confirm that screenshots, logs, fixtures, and build output contain no private or machine-specific data.

By contributing, you agree that your work is provided under the project’s MIT License.
