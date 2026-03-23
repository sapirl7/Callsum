# -*- coding: utf-8 -*-
"""
Tests for telegram_bot/bot.py — pure functions and isolated logic.
All cloud dependencies (AWS, Telegram, RunPod) are mocked.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Module under test is loaded with heavy imports (boto3, telegram).
# We patch them at import time so tests run without real AWS credentials.
# ---------------------------------------------------------------------------
import sys

# Stub out heavy SDK modules before importing bot
_boto3_mock = MagicMock()
sys.modules.setdefault("boto3", _boto3_mock)
sys.modules.setdefault("httpx", MagicMock())
sys.modules.setdefault("telegram", MagicMock())
sys.modules.setdefault("telegram.ext", MagicMock())

# Now import the module under test
_project_root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_project_root, "telegram_bot"))
sys.path.insert(0, _project_root)
import importlib  # noqa: E402

bot = importlib.import_module("bot")


class TestSplitMessage(unittest.TestCase):
    """Tests for split_message() — Telegram 4096-char limit splitting."""

    def test_short_message_returns_single_part(self):
        result = bot.split_message("Hello", 100)
        self.assertEqual(result, ["Hello"])

    def test_exact_limit_returns_single_part(self):
        text = "a" * 100
        result = bot.split_message(text, 100)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], text)

    def test_long_message_splits_on_newlines(self):
        lines = [f"Line {i}" for i in range(20)]
        text = "\n".join(lines)
        result = bot.split_message(text, 50)
        self.assertTrue(len(result) > 1)
        # Reassembled text should contain all original lines
        reassembled = "\n".join(result)
        for line in lines:
            self.assertIn(line, reassembled)

    def test_empty_message(self):
        result = bot.split_message("", 100)
        self.assertEqual(result, [""])

    def test_single_very_long_line_not_split_mid_line(self):
        # A single line longer than the limit — split_message can't break it
        long_line = "a" * 200
        result = bot.split_message(long_line, 100)
        # The function puts it as one chunk since there are no newlines
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], long_line)

    def test_preserves_line_content(self):
        text = "Line 1\nLine 2\nLine 3"
        result = bot.split_message(text, 1000)
        self.assertEqual(result, [text])


class TestEstimateProcessingTime(unittest.TestCase):
    """Tests for estimate_processing_time() — time estimation formula."""

    def test_one_hour_audio(self):
        # 1 hour = 3600 seconds → 3600/60 * 0.33 = 19.8 → int = 19
        result = bot.estimate_processing_time(3600)
        self.assertEqual(result, 19)

    def test_one_minute_audio(self):
        # 60s → 60/60 * 0.33 = 0.33 → max(1, 0) = 1
        result = bot.estimate_processing_time(60)
        self.assertEqual(result, 1)

    def test_zero_duration(self):
        # Should return at least 1 minute
        result = bot.estimate_processing_time(0)
        self.assertEqual(result, 1)

    def test_two_hour_audio(self):
        # 7200s → 7200/60 * 0.33 = 39.6 → 39
        result = bot.estimate_processing_time(7200)
        self.assertEqual(result, 39)

    def test_short_audio_minimum(self):
        # 10 seconds → 10/60 * 0.33 ≈ 0.055 → max(1, 0) = 1
        result = bot.estimate_processing_time(10)
        self.assertEqual(result, 1)


class TestGetEnvInt(unittest.TestCase):
    """Tests for get_env_int() — safe integer parsing from env."""

    def test_returns_default_when_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            result = bot.get_env_int("NONEXISTENT_VAR", 42)
            self.assertEqual(result, 42)

    def test_returns_parsed_value(self):
        with patch.dict(os.environ, {"TEST_VAR": "123"}):
            result = bot.get_env_int("TEST_VAR", 42)
            self.assertEqual(result, 123)

    def test_returns_default_on_invalid_value(self):
        with patch.dict(os.environ, {"TEST_VAR": "not_a_number"}):
            result = bot.get_env_int("TEST_VAR", 42)
            self.assertEqual(result, 42)

    def test_handles_empty_string(self):
        with patch.dict(os.environ, {"TEST_VAR": ""}):
            result = bot.get_env_int("TEST_VAR", 42)
            self.assertEqual(result, 42)

    def test_handles_negative_values(self):
        with patch.dict(os.environ, {"TEST_VAR": "-5"}):
            result = bot.get_env_int("TEST_VAR", 42)
            self.assertEqual(result, -5)

    def test_handles_zero(self):
        with patch.dict(os.environ, {"TEST_VAR": "0"}):
            result = bot.get_env_int("TEST_VAR", 42)
            self.assertEqual(result, 0)


class TestGetAwsRegion(unittest.TestCase):
    """Tests for get_aws_region() — AWS region resolution."""

    def test_returns_default_region(self):
        with patch.dict(os.environ, {}, clear=True):
            result = bot.get_aws_region()
            self.assertEqual(result, "us-east-1")

    def test_returns_custom_region(self):
        with patch.dict(os.environ, {"AWS_REGION": "eu-west-1"}):
            result = bot.get_aws_region()
            self.assertEqual(result, "eu-west-1")


class TestGetAudioExtension(unittest.TestCase):
    """Tests for get_audio_extension() — file extension detection."""

    def test_from_file_name(self):
        voice = MagicMock()
        voice.file_name = "recording.mp3"
        voice.mime_type = None
        telegram_file = MagicMock()
        telegram_file.file_path = ""
        result = bot.get_audio_extension(voice, telegram_file)
        self.assertEqual(result, ".mp3")

    def test_from_telegram_file_path(self):
        voice = MagicMock()
        voice.file_name = None
        voice.mime_type = None
        telegram_file = MagicMock()
        telegram_file.file_path = "file_0/audio.wav"
        result = bot.get_audio_extension(voice, telegram_file)
        self.assertEqual(result, ".wav")

    def test_from_mime_type(self):
        voice = MagicMock()
        voice.file_name = None
        voice.mime_type = "audio/mp4"
        telegram_file = MagicMock()
        telegram_file.file_path = ""
        result = bot.get_audio_extension(voice, telegram_file)
        self.assertEqual(result, ".mp4")

    def test_fallback_to_ogg(self):
        voice = MagicMock()
        voice.file_name = None
        voice.mime_type = "application/octet-stream"
        telegram_file = MagicMock()
        telegram_file.file_path = ""
        result = bot.get_audio_extension(voice, telegram_file)
        self.assertEqual(result, ".ogg")

    def test_no_info_defaults_to_ogg(self):
        voice = MagicMock()
        voice.file_name = None
        voice.mime_type = None
        telegram_file = MagicMock()
        telegram_file.file_path = None
        result = bot.get_audio_extension(voice, telegram_file)
        self.assertEqual(result, ".ogg")

    def test_file_name_takes_priority_over_mime(self):
        voice = MagicMock()
        voice.file_name = "meeting.m4a"
        voice.mime_type = "audio/ogg"
        telegram_file = MagicMock()
        telegram_file.file_path = ""
        result = bot.get_audio_extension(voice, telegram_file)
        self.assertEqual(result, ".m4a")

    def test_webm_mime_type(self):
        voice = MagicMock()
        voice.file_name = None
        voice.mime_type = "audio/webm"
        telegram_file = MagicMock()
        telegram_file.file_path = ""
        result = bot.get_audio_extension(voice, telegram_file)
        self.assertEqual(result, ".webm")


class TestGetHeader(unittest.TestCase):
    """Tests for get_header() — case-insensitive header lookup."""

    def test_exact_case_match(self):
        headers = {"Content-Type": "application/json"}
        self.assertEqual(bot.get_header(headers, "Content-Type"), "application/json")

    def test_case_insensitive(self):
        headers = {"X-Custom-Header": "value123"}
        self.assertEqual(bot.get_header(headers, "x-custom-header"), "value123")

    def test_missing_header(self):
        headers = {"Content-Type": "text/html"}
        self.assertEqual(bot.get_header(headers, "Authorization"), "")

    def test_none_headers(self):
        self.assertEqual(bot.get_header(None, "Any"), "")

    def test_empty_headers(self):
        self.assertEqual(bot.get_header({}, "Any"), "")


class TestParseEventBody(unittest.TestCase):
    """Tests for parse_event_body() — Lambda event parsing."""

    def test_json_string_body(self):
        event = {"body": '{"update_id": 123}'}
        result = bot.parse_event_body(event)
        self.assertEqual(result, {"update_id": 123})

    def test_no_body_returns_event(self):
        event = {"update_id": 123}
        result = bot.parse_event_body(event)
        self.assertEqual(result, {"update_id": 123})

    def test_none_body_returns_event(self):
        event = {"body": None}
        result = bot.parse_event_body(event)
        self.assertEqual(result, {"body": None})

    def test_empty_body(self):
        event = {"body": ""}
        result = bot.parse_event_body(event)
        self.assertEqual(result, {})

    def test_base64_encoded_raises(self):
        event = {"body": "dGVzdA==", "isBase64Encoded": True}
        with self.assertRaises(ValueError):
            bot.parse_event_body(event)

    def test_invalid_json_raises(self):
        event = {"body": "not json at all"}
        with self.assertRaises(json.JSONDecodeError):
            bot.parse_event_body(event)


class TestSupportedAudioFormats(unittest.TestCase):
    """Tests for SUPPORTED_AUDIO_FORMATS constant."""

    def test_ogg_supported(self):
        self.assertIn("audio/ogg", bot.SUPPORTED_AUDIO_FORMATS)

    def test_mp3_supported(self):
        self.assertIn("audio/mpeg", bot.SUPPORTED_AUDIO_FORMATS)
        self.assertIn("audio/mp3", bot.SUPPORTED_AUDIO_FORMATS)

    def test_wav_supported(self):
        self.assertIn("audio/wav", bot.SUPPORTED_AUDIO_FORMATS)
        self.assertIn("audio/x-wav", bot.SUPPORTED_AUDIO_FORMATS)

    def test_webm_supported(self):
        self.assertIn("audio/webm", bot.SUPPORTED_AUDIO_FORMATS)

    def test_video_not_supported(self):
        self.assertNotIn("video/mp4", bot.SUPPORTED_AUDIO_FORMATS)

    def test_text_not_supported(self):
        self.assertNotIn("text/plain", bot.SUPPORTED_AUDIO_FORMATS)


class TestValidateProcessingRuntime(unittest.TestCase):
    """Tests for validate_processing_runtime() — config completeness check."""

    def test_raises_when_endpoint_missing(self):
        mock_runtime = MagicMock()
        mock_runtime.runpod_endpoint = None
        mock_runtime.runpod_api_key = "key123"
        mock_runtime.callback_url = None
        mock_runtime.runpod_callback_token = ""

        with patch.object(bot, "get_runtime_services", return_value=mock_runtime):
            with self.assertRaises(RuntimeError) as ctx:
                bot.validate_processing_runtime()
            self.assertIn("RUNPOD_ENDPOINT_URL", str(ctx.exception))

    def test_raises_when_api_key_missing(self):
        mock_runtime = MagicMock()
        mock_runtime.runpod_endpoint = "https://api.runpod.ai/v2/xxx"
        mock_runtime.runpod_api_key = None
        mock_runtime.callback_url = None
        mock_runtime.runpod_callback_token = ""

        with patch.object(bot, "get_runtime_services", return_value=mock_runtime):
            with self.assertRaises(RuntimeError) as ctx:
                bot.validate_processing_runtime()
            self.assertIn("RUNPOD_API_KEY", str(ctx.exception))

    def test_passes_when_fully_configured(self):
        mock_runtime = MagicMock()
        mock_runtime.runpod_endpoint = "https://api.runpod.ai/v2/xxx"
        mock_runtime.runpod_api_key = "key123"
        mock_runtime.callback_url = "https://callback.example.com"
        mock_runtime.runpod_callback_token = "token123"

        with patch.object(bot, "get_runtime_services", return_value=mock_runtime):
            result = bot.validate_processing_runtime()
            self.assertEqual(result, mock_runtime)

    def test_raises_when_callback_url_without_token(self):
        mock_runtime = MagicMock()
        mock_runtime.runpod_endpoint = "https://api.runpod.ai/v2/xxx"
        mock_runtime.runpod_api_key = "key123"
        mock_runtime.callback_url = "https://callback.example.com"
        mock_runtime.runpod_callback_token = ""

        with patch.object(bot, "get_runtime_services", return_value=mock_runtime):
            with self.assertRaises(RuntimeError) as ctx:
                bot.validate_processing_runtime()
            self.assertIn("RUNPOD_CALLBACK_TOKEN", str(ctx.exception))


class TestRequireBotToken(unittest.TestCase):
    """Tests for require_bot_token() — token resolution."""

    def test_raises_when_no_token(self):
        with patch.object(bot, "get_telegram_token", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                bot.require_bot_token()
            self.assertIn("Telegram bot token", str(ctx.exception))

    def test_returns_token_when_set(self):
        with patch.object(bot, "get_telegram_token", return_value="123456:ABC"):
            result = bot.require_bot_token()
            self.assertEqual(result, "123456:ABC")


if __name__ == "__main__":
    unittest.main()
