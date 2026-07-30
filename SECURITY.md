# Security Policy

## Supported version

Security fixes are applied to the latest release.

## Reporting a vulnerability

Please use GitHub’s private vulnerability reporting feature on this repository. Do not open a public issue for an unpatched vulnerability.

Include the affected version, impact, reproduction steps, and a minimal anonymized example. Never include Telegram session files, API credentials, phone numbers, private channel links, downloaded media, or other personal data.

## Local secrets

- `telegram_media.session` grants access through the signed-in Telegram session and must never be shared.
- API credentials are stored in Windows Credential Manager, macOS Keychain, or Linux Secret Service. The application never falls back to a plain-text credential file.
- The repository ignores sessions, downloads, temporary files, local environments, and build output by default.
