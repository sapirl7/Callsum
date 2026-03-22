import unittest
from pathlib import Path


class DeploymentContractTests(unittest.TestCase):
    def test_root_dockerfile_no_longer_references_removed_pipeline(self):
        dockerfile = Path("Dockerfile").read_text()
        self.assertNotIn("pipeline.py", dockerfile)

    def test_compose_no_longer_uses_ollama_stack(self):
        compose = Path("docker-compose.yaml").read_text()
        self.assertNotIn("ollama", compose.lower())

    def test_lambda_packaging_targets_built_artifact(self):
        lambda_tf = Path("infrastructure/terraform/lambda.tf").read_text()
        self.assertIn("telegram_bot/build/lambda", lambda_tf)


if __name__ == "__main__":
    unittest.main()
