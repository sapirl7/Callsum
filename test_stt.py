import unittest
from pathlib import Path


class SpeechPipelineContractTests(unittest.TestCase):
    def test_handler_uses_current_pyannote_token_argument(self):
        handler_source = Path("runpod_service/handler.py").read_text()

        self.assertIn("token=HF_TOKEN", handler_source)
        self.assertNotIn("use_auth_token", handler_source)

    def test_handler_cleans_up_temp_files(self):
        handler_source = Path("runpod_service/handler.py").read_text()

        self.assertIn("finally:", handler_source)
        self.assertIn("os.remove(audio_path)", handler_source)


if __name__ == "__main__":
    unittest.main()
