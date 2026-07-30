from __future__ import annotations

import sys
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
        executable = r"C:\Portable\TelegramMediaDownloader.exe"
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", executable),
        ):
            self.assertEqual(
                downloader.application_dir(),
                Path(executable).parent,
            )


if __name__ == "__main__":
    unittest.main()
