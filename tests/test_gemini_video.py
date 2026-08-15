import unittest
from unittest.mock import patch

from ai_router.providers.base import ProviderError
from ai_router.providers.gemini import GeminiAdapter


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "steps": [
                {
                    "type": "model_output",
                    "content": [
                        {
                            "type": "text",
                            "text": '{"summary":"video understood","claims":[]}',
                        }
                    ],
                }
            ],
            "usage": {"total_tokens": 12},
        }


class FakeErrorResponse:
    status_code = 403

    def json(self):
        return {"error": {"status": "PERMISSION_DENIED", "message": "secret must not leak"}}


class GeminiVideoAdapterTests(unittest.TestCase):
    def test_interactions_payload_and_json_output(self):
        adapter = GeminiAdapter("https://generativelanguage.googleapis.com/v1beta")
        with patch("ai_router.providers.gemini.requests.post", return_value=FakeResponse()) as post:
            result = adapter.complete_video_json(
                model="gemini-3.6-flash",
                secret="placeholder-secret",
                video_uri="https://www.youtube.com/watch?v=example",
                system_prompt="system",
                user_prompt="return JSON",
                timeout_seconds=90,
            )
        self.assertEqual(result.payload, {"summary": "video understood", "claims": []})
        self.assertEqual(result.usage["total_tokens"], 12)
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://generativelanguage.googleapis.com/v1beta/interactions")
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "placeholder-secret")
        self.assertEqual(kwargs["json"]["input"][0], {"type": "video", "uri": "https://www.youtube.com/watch?v=example"})

    def test_error_does_not_expose_raw_provider_message(self):
        adapter = GeminiAdapter("https://generativelanguage.googleapis.com/v1beta")
        with patch("ai_router.providers.gemini.requests.post", return_value=FakeErrorResponse()), self.assertRaises(ProviderError) as context:
            adapter.complete_video_json(
                model="gemini-3.6-flash",
                secret="placeholder-secret",
                video_uri="https://www.youtube.com/watch?v=example",
                system_prompt="system",
                user_prompt="return JSON",
                timeout_seconds=90,
            )
        self.assertNotIn("secret must not leak", str(context.exception))
        self.assertEqual(context.exception.error_class, "auth")


if __name__ == "__main__":
    unittest.main()
