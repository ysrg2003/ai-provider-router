from __future__ import annotations

import base64
import json
import unittest
from unittest.mock import patch

import requests

from ai_router.providers.base import ProviderError
from ai_router.providers.chatgpt_conversation_image import (
    ChatGPTConversationImageAdapter,
)


class ChatGPTConversationImageAdapterTests(unittest.TestCase):
    def test_extracts_image_from_queued_conversation_job(self):
        raw = b"queued-chat-image"
        encoded = base64.b64encode(raw).decode("ascii")
        create = requests.Response()
        create.status_code = 200
        create._content = b'{"job_id":"image-job-1","status":"queued"}'
        status = requests.Response()
        status.status_code = 200
        status._content = json.dumps({
            "status": "done",
            "response": {
                "choices": [{
                    "message": {
                        "content": [
                            {"type": "text", "text": "Done."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                        ]
                    }
                }],
                "usage": {"total_tokens": 4},
            },
        }).encode()

        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=create) as post, patch(
            "ai_router.providers.chatgpt_conversation_image.requests.get", return_value=status
        ) as get:
            result = ChatGPTConversationImageAdapter("https://uploaded.example", poll_interval_seconds=0).generate_image(
                model="chatgpt-conversation",
                secret="local-secret",
                prompt="generate an image of a blue circle",
                timeout_seconds=30,
            )

        self.assertEqual(result.payload["output_type"], "image")
        self.assertEqual(result.payload["mime_type"], "image/png")
        self.assertEqual(base64.b64decode(result.payload["data_base64"]), raw)
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer local-secret")
        self.assertEqual(post.call_args.args[0], "https://uploaded.example/v1/jobs")
        self.assertEqual(get.call_args.args[0], "https://uploaded.example/v1/jobs/image-job-1")

    @staticmethod
    def _job_responses(content="Live answer with sources."):
        create = requests.Response()
        create.status_code = 200
        create._content = b'{"job_id":"job-1","status":"queued"}'
        status = requests.Response()
        status.status_code = 200
        status._content = json.dumps({
            "status": "done",
            "response": {
                "choices": [{"message": {"content": content}}],
                "usage": {"total_tokens": 8},
            },
        }).encode()
        return create, status

    def test_extracts_text_from_queued_job(self):
        create, status = self._job_responses()
        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=create) as post, patch(
            "ai_router.providers.chatgpt_conversation_image.requests.get", return_value=status
        ) as get:
            result = ChatGPTConversationImageAdapter("https://uploaded.example", poll_interval_seconds=0).complete_interaction_text(
                model="chatgpt-conversation",
                secret="local-secret",
                system_prompt="Be concise.",
                user_prompt="What is the current status?",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["output_type"], "text")
        self.assertEqual(result.payload["text"], "Live answer with sources.")
        self.assertEqual(post.call_args.args[0], "https://uploaded.example/v1/jobs")
        self.assertEqual(post.call_args.kwargs["json"]["messages"], [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "What is the current status?"},
        ])
        self.assertEqual(get.call_args.args[0], "https://uploaded.example/v1/jobs/job-1")

    def test_search_route_adds_live_web_instruction_to_queued_job(self):
        create, status = self._job_responses("Sourced answer")
        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=create) as post, patch(
            "ai_router.providers.chatgpt_conversation_image.requests.get", return_value=status
        ):
            ChatGPTConversationImageAdapter("https://uploaded.example", poll_interval_seconds=0).complete_interaction_text(
                model="chatgpt-conversation",
                secret="local-secret",
                system_prompt="",
                user_prompt="ابحث في الويب بحث حي عن آخر الأخبار",
                timeout_seconds=30,
                tools=[{"type": "google_search"}],
            )
        messages = post.call_args.kwargs["json"]["messages"]
        self.assertEqual(messages[-1]["role"], "user")
        self.assertIn("بحثًا حيًا في الويب", messages[0]["content"])
        self.assertIn("المصادر والروابط", messages[0]["content"])

    def test_extracts_output_image_b64_json_shape(self):
        encoded = base64.b64encode(b"output-image").decode("ascii")
        body = {"output": [{"type": "image_generation_call", "result": encoded, "mime_type": "image/webp"}]}
        result = ChatGPTConversationImageAdapter._first_image_from_body(body, None)
        self.assertEqual(result, ("image/webp", encoded))

    def test_extracts_nested_data_url_without_image_url_type(self):
        encoded = base64.b64encode(b"nested-image").decode("ascii")
        body = {"result": {"attachment": {"src": f"data:image/jpeg;base64,{encoded}"}}}
        result = ChatGPTConversationImageAdapter._first_image_from_body(body, None)
        self.assertEqual(result, ("image/jpeg", encoded))

    def test_missing_image_is_terminal_invalid_response(self):
        response = requests.Response()
        response.status_code = 200
        create = requests.Response()
        create.status_code = 200
        create._content = b'{"job_id":"image-job-2","status":"queued"}'
        status = requests.Response()
        status.status_code = 200
        status._content = b'{"status":"done","response":{"choices":[{"message":{"content":"text only"}}]}}'
        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=create), patch(
            "ai_router.providers.chatgpt_conversation_image.requests.get", return_value=status
        ), self.assertRaisesRegex(ProviderError, "no image"):
            ChatGPTConversationImageAdapter("https://uploaded.example").generate_image(
                model="chatgpt-conversation",
                secret="local-secret",
                prompt="create an image",
                timeout_seconds=30,
            )

    def test_image_quota_text_is_classified_as_quota(self):
        create = requests.Response()
        create.status_code = 200
        create._content = b'{"job_id":"image-job-quota","status":"queued"}'
        status = requests.Response()
        status.status_code = 200
        status._content = b'{"status":"done","response":{"choices":[{"message":{"content":"You have hit the Free plan limit for image generations."}}]}}'
        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=create), patch(
            "ai_router.providers.chatgpt_conversation_image.requests.get", return_value=status
        ), self.assertRaisesRegex(ProviderError, "Free plan limit") as raised:
            ChatGPTConversationImageAdapter("https://uploaded.example", poll_interval_seconds=0).generate_image(
                model="chatgpt-conversation",
                secret="local-secret",
                prompt="generate an image",
                timeout_seconds=30,
            )
        self.assertEqual(raised.exception.error_class, "quota")

    def test_auth_error_is_non_retryable(self):
        response = requests.Response()
        response.status_code = 401
        response._content = b'{"error":{"message":"invalid API key"}}'
        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=response), self.assertRaises(ProviderError) as raised:
            ChatGPTConversationImageAdapter("https://uploaded.example").generate_image(
                model="chatgpt-conversation",
                secret="local-secret",
                prompt="create an image",
                timeout_seconds=30,
            )
        self.assertEqual(raised.exception.error_class, "auth")
        self.assertFalse(raised.exception.retryable)


if __name__ == "__main__":
    unittest.main()
