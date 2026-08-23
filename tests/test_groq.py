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
                "groq/compound-mini",
                "openai/gpt-oss-20b",
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


    def test_groq_json_profile_uses_completion_tokens_and_json_parser(self):
        class JsonResponse(FakeResponse):
            def json(self):
                return {
                    "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                    "usage": {"total_tokens": 3},
                }

        adapter = OpenAICompatibleAdapter("groq", "https://api.groq.com/openai/v1")
        with patch("ai_router.providers.openai_compatible.requests.post", return_value=JsonResponse()) as post:
            result = adapter.complete_json(
                model="openai/gpt-oss-120b",
                secret="test-secret",
                system_prompt="Return JSON",
                user_prompt="Answer",
                timeout_seconds=30,
                invocation_profile={
                    "response_parser": "json_object",
                    "response_format": "json_object",
                    "max_tokens_field": "max_completion_tokens",
                    "max_tokens": 512,
                },
            )
        self.assertEqual(result.payload, {"answer": "ok"})
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["max_completion_tokens"], 512)
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_flexible_profile_wraps_plain_text_without_crashing(self):
        class TextResponse(FakeResponse):
            def json(self):
                return {"choices": [{"message": {"content": "plain answer"}}], "usage": {}}

        adapter = OpenAICompatibleAdapter("huggingface", "https://router.huggingface.co/v1")
        with patch("ai_router.providers.openai_compatible.requests.post", return_value=TextResponse()):
            result = adapter.complete_json(
                model="test-model",
                secret="test-secret",
                system_prompt="",
                user_prompt="Answer",
                timeout_seconds=30,
                invocation_profile={"response_parser": "json_or_text_envelope", "response_format": "none"},
            )
        self.assertEqual(result.payload["provider_text"], "plain answer")


if __name__ == "__main__":
    unittest.main()
