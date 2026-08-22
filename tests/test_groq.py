from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_router import AIRouter
from ai_router.providers.openai_compatible import OpenAICompatibleAdapter


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "choices": [{"message": {"content": "GROQ_SMOKE_OK"}}],
            "usage": {"total_tokens": 3},
        }


class GroqTests(unittest.TestCase):
    def test_groq_text_request_uses_official_openai_compatible_endpoint(self):
        adapter = OpenAICompatibleAdapter("groq", "https://api.groq.com/openai/v1")
        with patch("ai_router.providers.openai_compatible.requests.post", return_value=FakeResponse()) as post:
            result = adapter.complete_text(
                model="openai/gpt-oss-120b",
                secret="test-secret",
                system_prompt="",
                user_prompt="Return exactly GROQ_SMOKE_OK",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["text"], "GROQ_SMOKE_OK")
        self.assertEqual(post.call_args.args[0], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["json"]["max_completion_tokens"], 1024)
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-secret")

    def test_groq_models_are_ranked_by_operational_capability(self):
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            models = [item.model for item in router.config.model_chain("default") if item.provider_id == "groq"]
            self.assertEqual(models, [
                "openai/gpt-oss-120b",
                "groq/compound",
                "qwen/qwen3.6-27b",
                "groq/compound-mini",
                "openai/gpt-oss-20b",
                "allam-2-7b",
            ])
            router.close()

    def test_groq_single_token_fallback_is_loaded(self):
        previous = os.environ.get("GROQ_API_KEY")
        previous_json = os.environ.get("GROQ_API_KEYS_JSON")
        os.environ["GROQ_API_KEY"] = "groq-test-secret"
        os.environ.pop("GROQ_API_KEYS_JSON", None)
        try:
            with tempfile.TemporaryDirectory() as temp:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                keys = router.config.keys_for("groq")
                self.assertEqual(len(keys), 1)
                self.assertEqual(keys[0].secret, "groq-test-secret")
                router.close()
        finally:
            if previous is None:
                os.environ.pop("GROQ_API_KEY", None)
            else:
                os.environ["GROQ_API_KEY"] = previous
            if previous_json is None:
                os.environ.pop("GROQ_API_KEYS_JSON", None)
            else:
                os.environ["GROQ_API_KEYS_JSON"] = previous_json


if __name__ == "__main__":
    unittest.main()
