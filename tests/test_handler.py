# -*- coding: utf-8 -*-
"""
Tests for runpod_service/handler.py — pure processing functions.
All ML models and network calls are mocked.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

# Stub out all heavy ML imports before importing handler
import sys

for mod in [
    "torch",
    "faster_whisper",
    "pyannote",
    "pyannote.audio",
    "transformers",
    "vllm",
    "runpod",
    "httpx",
]:
    sys.modules.setdefault(mod, MagicMock())

# Patch module-level model initialization
_torch_mock = sys.modules["torch"]
_torch_mock.cuda.is_available.return_value = False
_torch_mock.device.return_value = "cpu"

# Prevent actual model loading at import time
with patch.dict(os.environ, {"HF_TOKEN": "test_token"}):
    with patch("faster_whisper.WhisperModel"):
        with patch("pyannote.audio.Pipeline.from_pretrained"):
            with patch("vllm.LLM"):
                with patch(
                    "transformers.AutoTokenizer.from_pretrained"
                ) as mock_tokenizer:
                    mock_tokenizer.return_value = MagicMock()
                    sys.path.insert(
                        0,
                        os.path.join(os.path.dirname(__file__), "..", "runpod_service"),
                    )
                    import importlib

                    handler_mod = importlib.import_module("handler")


class TestAlignSpeakersWithWords(unittest.TestCase):
    """Tests for align_speakers_with_words() — word-to-speaker mapping."""

    def _make_diarization(self, tracks):
        """Create a mock diarization object with itertracks()."""
        mock = MagicMock()
        mock.itertracks.return_value = tracks
        return mock

    def _make_turn(self, start, end):
        turn = MagicMock()
        turn.start = start
        turn.end = end
        return turn

    def test_single_speaker_single_word(self):
        turn = self._make_turn(0.0, 2.0)
        diarization = self._make_diarization([(turn, None, "SPEAKER_00")])
        words = [{"text": "Hello", "start": 0.5, "end": 1.0}]

        result = handler_mod.align_speakers_with_words(diarization, words)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["speaker"], "SPEAKER_00")
        self.assertEqual(result[0]["text"], "Hello")

    def test_unknown_speaker_when_no_match(self):
        diarization = self._make_diarization([])
        words = [{"text": "Lost", "start": 5.0, "end": 6.0}]

        result = handler_mod.align_speakers_with_words(diarization, words)

        self.assertEqual(result[0]["speaker"], "UNKNOWN")

    def test_multiple_speakers(self):
        turn1 = self._make_turn(0.0, 3.0)
        turn2 = self._make_turn(3.0, 6.0)
        diarization = self._make_diarization(
            [
                (turn1, None, "SPEAKER_00"),
                (turn2, None, "SPEAKER_01"),
            ]
        )
        words = [
            {"text": "Hi", "start": 1.0, "end": 1.5},
            {"text": "there", "start": 4.0, "end": 4.5},
        ]

        result = handler_mod.align_speakers_with_words(diarization, words)

        self.assertEqual(result[0]["speaker"], "SPEAKER_00")
        self.assertEqual(result[1]["speaker"], "SPEAKER_01")

    def test_empty_words(self):
        turn = self._make_turn(0.0, 5.0)
        diarization = self._make_diarization([(turn, None, "SPEAKER_00")])

        result = handler_mod.align_speakers_with_words(diarization, [])
        self.assertEqual(result, [])

    def test_word_midpoint_determines_speaker(self):
        # Word from 2.5 to 3.5 → midpoint = 3.0
        # Speaker 1 covers 0-3, Speaker 2 covers 3-6
        # Midpoint 3.0 falls in Speaker 1's range (<=)
        turn1 = self._make_turn(0.0, 3.0)
        turn2 = self._make_turn(3.0, 6.0)
        diarization = self._make_diarization(
            [
                (turn1, None, "SPEAKER_00"),
                (turn2, None, "SPEAKER_01"),
            ]
        )
        words = [{"text": "boundary", "start": 2.5, "end": 3.5}]

        result = handler_mod.align_speakers_with_words(diarization, words)
        # Midpoint 3.0 is within turn1 (0.0 <= 3.0 <= 3.0)
        self.assertEqual(result[0]["speaker"], "SPEAKER_00")


class TestFormatDialogueForLlm(unittest.TestCase):
    """Tests for format_dialogue_for_llm() — dialogue text formatting."""

    def test_empty_dialogue(self):
        result = handler_mod.format_dialogue_for_llm([])
        self.assertEqual(result, "")

    def test_single_utterance(self):
        dialogue = [
            {"speaker": "SPEAKER_00", "text": "Hello", "start": 0.0, "end": 1.0},
        ]
        result = handler_mod.format_dialogue_for_llm(dialogue)
        self.assertIn("[SPEAKER_00, 00:00]", result)
        self.assertIn("Hello", result)

    def test_groups_consecutive_speaker_words(self):
        dialogue = [
            {"speaker": "SPEAKER_00", "text": "Hello", "start": 0.0, "end": 0.5},
            {"speaker": "SPEAKER_00", "text": "world", "start": 0.5, "end": 1.0},
            {"speaker": "SPEAKER_01", "text": "Hi", "start": 1.0, "end": 1.5},
        ]
        result = handler_mod.format_dialogue_for_llm(dialogue)
        lines = result.split("\n\n")
        self.assertEqual(len(lines), 2)
        self.assertIn("Hello world", lines[0])
        self.assertIn("Hi", lines[1])

    def test_timestamp_format(self):
        dialogue = [
            {"speaker": "SPEAKER_00", "text": "Late", "start": 125.0, "end": 126.0},
        ]
        result = handler_mod.format_dialogue_for_llm(dialogue)
        # 125 seconds = 2 minutes 5 seconds → 02:05
        self.assertIn("[SPEAKER_00, 02:05]", result)

    def test_multiple_speaker_switches(self):
        dialogue = [
            {"speaker": "A", "text": "one", "start": 0.0, "end": 1.0},
            {"speaker": "B", "text": "two", "start": 1.0, "end": 2.0},
            {"speaker": "A", "text": "three", "start": 2.0, "end": 3.0},
        ]
        result = handler_mod.format_dialogue_for_llm(dialogue)
        lines = result.split("\n\n")
        self.assertEqual(len(lines), 3)


class TestBuildCallbackHeaders(unittest.TestCase):
    """Tests for build_callback_headers() — RunPod auth header."""

    def test_with_token(self):
        headers = handler_mod.build_callback_headers("secret123")
        self.assertEqual(headers[handler_mod.RUNPOD_CALLBACK_HEADER], "secret123")

    def test_without_token(self):
        headers = handler_mod.build_callback_headers(None)
        self.assertEqual(headers, {})

    def test_with_empty_token(self):
        headers = handler_mod.build_callback_headers("")
        self.assertEqual(headers, {})


class TestHandlerTestInput(unittest.TestCase):
    """Tests for handler() — test/health check mode."""

    def test_test_input_returns_status(self):
        job = {"input": {"test": True}}
        result = handler_mod.handler(job)
        self.assertEqual(result["status"], "ok")
        self.assertIn("device", result)
        self.assertIn("cuda_available", result)


class TestHandlerMissingInput(unittest.TestCase):
    """Tests for handler() — error handling for missing fields."""

    def test_missing_download_url_returns_error(self):
        job = {
            "input": {
                "job_id": "test-123",
                "chat_id": "456",
                "callback_url": None,
                "callback_token": None,
                "audio_download_url": None,
                "result_upload_url": "https://s3.example.com/upload",
                "result_key": "results/test.json",
            }
        }

        # The handler should raise/return error about missing download_url
        with patch.object(handler_mod, "send_progress_update"):
            result = handler_mod.handler(job)
            self.assertEqual(result["status"], "error")
            self.assertIn("audio_download_url", result["error"])


class TestSystemPromptIntegrity(unittest.TestCase):
    """Tests that the Russian system prompt is well-formed and contains required sections."""

    def test_prompt_contains_json_schema(self):
        self.assertIn('"discussed"', handler_mod.SYSTEM_PROMPT)
        self.assertIn('"tasks"', handler_mod.SYSTEM_PROMPT)

    def test_prompt_contains_categories(self):
        self.assertIn("commerce", handler_mod.SYSTEM_PROMPT)
        self.assertIn("operations", handler_mod.SYSTEM_PROMPT)
        self.assertIn("technical", handler_mod.SYSTEM_PROMPT)

    def test_prompt_contains_task_fields(self):
        self.assertIn('"task"', handler_mod.SYSTEM_PROMPT)
        self.assertIn('"responsible"', handler_mod.SYSTEM_PROMPT)
        self.assertIn('"deadline"', handler_mod.SYSTEM_PROMPT)
        self.assertIn('"priority"', handler_mod.SYSTEM_PROMPT)

    def test_prompt_requires_json_output(self):
        self.assertIn("JSON", handler_mod.SYSTEM_PROMPT)


class TestLlmModelConfig(unittest.TestCase):
    """Tests for model configuration constants."""

    def test_llm_model_name(self):
        self.assertEqual(
            handler_mod.LLM_MODEL_NAME, "meta-llama/Meta-Llama-3.1-8B-Instruct"
        )

    def test_callback_header_constant(self):
        self.assertEqual(handler_mod.RUNPOD_CALLBACK_HEADER, "x-runpod-callback-token")


if __name__ == "__main__":
    unittest.main()
