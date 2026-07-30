# Changelog

All notable changes to Telegram Media Downloader are documented here.

## [1.2.0] - 2026-07-30

### Added

- Native portable releases for Linux x64, macOS Apple Silicon, and macOS Intel alongside Windows x64.
- Bilingual `start.sh` launcher for Linux and macOS.
- Secure API credential storage through macOS Keychain and Linux Secret Service.
- Native build and smoke-test matrices for Windows, Linux, and macOS.

### Changed

- Release packaging is now driven by one cross-platform Python build script.
- Credential messages, documentation, security guidance, and promotional assets now describe every supported operating system.
- Linux systems without a supported desktop keyring never fall back to a plain-text credential file.

## [1.1.0] - 2026-07-30

### Added

- Portable Windows x64 executable and ZIP release package.
- Chinese and English interfaces with a bilingual launcher.
- Anonymous animated demo, social preview, and application icon.
- Reproducible PyInstaller build and tag-driven GitHub release workflow.
- `--version` command, contribution guide, security policy, and issue forms.

### Changed

- Frozen builds now store downloads and Telegram sessions beside the executable instead of in a temporary extraction directory.
- Both READMEs now provide a direct Windows download path, comparison table, clearer privacy notes, and release guidance.

## [1.0.0] - 2026-07-30

### Added

- Original-quality Telegram album, video, and discussion-media downloads.
- Parallel downloads, automatic retries, flood-wait handling, and strict file-size checks.
- Windows Credential Manager integration for API credentials.

[1.2.0]: https://github.com/swttttt/telegram-media-downloader/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/swttttt/telegram-media-downloader/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/swttttt/telegram-media-downloader/releases/tag/v1.0.0
