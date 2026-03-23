# -*- coding: utf-8 -*-
"""
Tests for config.py — configuration constants validation.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


class TestConfigConstants(unittest.TestCase):
    """Validates that config values are within sane ranges."""

    def test_max_audio_duration_range(self):
        # Should be between 1 minute and 8 hours
        self.assertGreaterEqual(config.MAX_AUDIO_DURATION_SECONDS, 60)
        self.assertLessEqual(config.MAX_AUDIO_DURATION_SECONDS, 28800)

    def test_min_audio_duration_positive(self):
        self.assertGreaterEqual(config.MIN_AUDIO_DURATION_SECONDS, 1)

    def test_min_less_than_max_duration(self):
        self.assertLess(
            config.MIN_AUDIO_DURATION_SECONDS,
            config.MAX_AUDIO_DURATION_SECONDS,
        )

    def test_file_size_limit_reasonable(self):
        # Between 1 MB and 1 GB
        self.assertGreaterEqual(config.MAX_FILE_SIZE_MB, 1)
        self.assertLessEqual(config.MAX_FILE_SIZE_MB, 1024)

    def test_rate_limits_positive(self):
        self.assertGreater(config.FREE_TIER_REQUESTS_PER_HOUR, 0)
        self.assertGreater(config.FREE_TIER_REQUESTS_PER_DAY, 0)

    def test_hourly_less_than_daily(self):
        self.assertLessEqual(
            config.FREE_TIER_REQUESTS_PER_HOUR,
            config.FREE_TIER_REQUESTS_PER_DAY,
        )

    def test_whisper_model_is_large_v3(self):
        self.assertEqual(config.WHISPER_MODEL, "large-v3")

    def test_pyannote_model_version(self):
        self.assertIn("speaker-diarization", config.PYANNOTE_MODEL)

    def test_retry_config_sane(self):
        self.assertGreater(config.MAX_RETRIES, 0)
        self.assertGreater(config.RETRY_BACKOFF_MULTIPLIER, 0)
        self.assertLessEqual(
            config.RETRY_MIN_WAIT_SECONDS, config.RETRY_MAX_WAIT_SECONDS
        )

    def test_timeouts_positive(self):
        self.assertGreater(config.RUNPOD_TIMEOUT_SECONDS, 0)
        self.assertGreater(config.LAMBDA_TIMEOUT_SECONDS, 0)

    def test_s3_retention_positive(self):
        self.assertGreater(config.S3_AUDIO_RETENTION_DAYS, 0)
        self.assertGreater(config.S3_RESULTS_RETENTION_DAYS, 0)

    def test_telegram_message_length(self):
        # Telegram limit is 4096, our limit should be at or below
        self.assertGreater(config.TELEGRAM_MAX_MESSAGE_LENGTH, 0)
        self.assertLessEqual(config.TELEGRAM_MAX_MESSAGE_LENGTH, 4096)

    def test_dynamodb_ttl_positive(self):
        self.assertGreater(config.DYNAMODB_TTL_DAYS, 0)


class TestConfigConsistency(unittest.TestCase):
    """Cross-module consistency checks."""

    def test_results_retained_longer_than_audio(self):
        self.assertGreaterEqual(
            config.S3_RESULTS_RETENTION_DAYS,
            config.S3_AUDIO_RETENTION_DAYS,
        )

    def test_runpod_timeout_greater_than_lambda(self):
        self.assertGreater(
            config.RUNPOD_TIMEOUT_SECONDS,
            config.LAMBDA_TIMEOUT_SECONDS,
        )


if __name__ == "__main__":
    unittest.main()
