from __future__ import annotations

import sys
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import telegram_media_downloader as downloader


class ParsePostUrlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_language = downloader.LANGUAGE
        downloader.LANGUAGE = "zh"

    def tearDown(self) -> None:
        downloader.LANGUAGE = self.original_language

    def test_public_post(self) -> None:
        post = downloader.parse_post_url(
            "https://t.me/ExampleChannel/37?single"
        )
        self.assertEqual(post.channel_label, "ExampleChannel")
        self.assertEqual(post.entity, "ExampleChannel")
        self.assertEqual(post.message_id, 37)
        self.assertIsNone(post.comment_id)

    def test_comment_link(self) -> None:
        post = downloader.parse_post_url(
            "https://t.me/channel/737?single&comment=7145"
        )
        self.assertEqual(post.channel_label, "channel")
        self.assertEqual(post.message_id, 737)
        self.assertEqual(post.comment_id, 7145)

    def test_private_channel(self) -> None:
        post = downloader.parse_post_url(
            "https://t.me/c/1234567890/321"
        )
        self.assertEqual(post.channel_label, "channel_1234567890")
        self.assertEqual(post.entity, -1001234567890)
        self.assertEqual(post.message_id, 321)

    def test_rejects_untrusted_host(self) -> None:
        with self.assertRaisesRegex(ValueError, "只支持"):
            downloader.parse_post_url(
                "https://example.com/ExampleChannel/37"
            )

    def test_rejects_invalid_comment_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "无效的评论编号"):
            downloader.parse_post_url(
                "https://t.me/ExampleChannel/37?comment=hello"
            )


class LanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_language = downloader.LANGUAGE

    def tearDown(self) -> None:
        downloader.LANGUAGE = self.original_language

    def test_requested_language_from_cli(self) -> None:
        self.assertEqual(
            downloader.requested_language(["--lang", "en"]),
            "en",
        )
        self.assertEqual(
            downloader.requested_language(["--lang=zh"]),
            "zh",
        )

    def test_english_validation_message(self) -> None:
        downloader.LANGUAGE = "en"
        with self.assertRaisesRegex(ValueError, "Only t.me"):
            downloader.parse_post_url(
                "https://example.com/ExampleChannel/37"
            )

    def test_english_help(self) -> None:
        downloader.LANGUAGE = "en"
        help_text = downloader.build_parser().format_help()
        self.assertIn("Interface language", help_text)
        self.assertIn("Download folder", help_text)

    def test_version_is_exposed(self) -> None:
        self.assertRegex(downloader.__version__, r"^\d+\.\d+\.\d+$")

    def test_frozen_application_dir_is_beside_executable(self) -> None:
        executable = str(
            PROJECT_ROOT
            / "portable"
            / ("TelegramMediaDownloader.exe" if sys.platform == "win32" else "TelegramMediaDownloader")
        )
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", executable),
        ):
            self.assertEqual(
                downloader.application_dir(),
                Path(executable).resolve().parent,
            )


class CredentialStoreTests(unittest.TestCase):
    def test_payload_round_trip(self) -> None:
        payload = downloader._credential_payload(123456, "a" * 32)
        self.assertEqual(
            downloader._parse_credential_payload(payload),
            ("123456", "a" * 32),
        )

    def test_rejects_invalid_payload(self) -> None:
        self.assertIsNone(downloader._parse_credential_payload("missing-separator"))

    def test_linux_secret_service_lookup(self) -> None:
        result = subprocess.CompletedProcess(
            args=["secret-tool"],
            returncode=0,
            stdout=f"123456:{'b' * 32}\n",
            stderr="",
        )
        with (
            patch.object(downloader.os, "name", "posix"),
            patch.object(downloader, "_macos_keychain_command", return_value=None),
            patch.object(downloader, "_linux_secret_tool", return_value="/usr/bin/secret-tool"),
            patch.object(downloader, "_run_credential_command", return_value=result) as command,
        ):
            self.assertEqual(
                downloader.load_saved_api_credentials(),
                ("123456", "b" * 32),
            )
        self.assertEqual(command.call_args.args[0][1], "lookup")

    def test_macos_keychain_save(self) -> None:
        result = subprocess.CompletedProcess(
            args=["security"],
            returncode=0,
            stdout="",
            stderr="",
        )
        with (
            patch.object(downloader.os, "name", "posix"),
            patch.object(downloader, "_macos_keychain_command", return_value="/usr/bin/security"),
            patch.object(downloader, "_run_credential_command", return_value=result) as command,
        ):
            self.assertTrue(downloader.save_api_credentials(654321, "c" * 32))
        arguments = command.call_args.args[0]
        self.assertIn("add-generic-password", arguments)
        self.assertIn(f"654321:{'c' * 32}", arguments)

    def test_no_plaintext_fallback_without_secure_store(self) -> None:
        with (
            patch.object(downloader.os, "name", "posix"),
            patch.object(downloader, "_macos_keychain_command", return_value=None),
            patch.object(downloader, "_linux_secret_tool", return_value=None),
        ):
            self.assertFalse(downloader.save_api_credentials(1, "d" * 32))


if __name__ == "__main__":
    unittest.main()
