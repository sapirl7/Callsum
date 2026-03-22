import unittest
from pathlib import Path


class RunpodHandlerContractTests(unittest.TestCase):
    def test_runpod_handler_uses_chat_template(self):
        handler_source = Path("runpod_service/handler.py").read_text()

        self.assertIn("apply_chat_template", handler_source)
        self.assertIn('runpod.serverless.start({"handler": handler})', handler_source)

    def test_runpod_handler_supports_test_mode(self):
        handler_source = Path("runpod_service/handler.py").read_text()

        self.assertIn('if job_input.get("test"):', handler_source)


if __name__ == "__main__":
    unittest.main()
