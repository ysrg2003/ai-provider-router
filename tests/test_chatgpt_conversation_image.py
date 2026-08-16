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
    def test_extracts_image_from_ordinary_chat_completion(self):
        raw = b"ordinary-chat-image"
        encoded = base64.b64encode(raw).decode("ascii")
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({
            "choices": [{
                "message": {
                    "content": [
                        {"type": "text", "text": "Done."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                    ]
                }
            }],
            "usage": {"total_tokens": 4},
        }).encode()
        response.headers["content-type"] = "application/json"

        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=response) as post:
            result = ChatGPTConversationImageAdapter("https://uploaded.example").generate_image(
                model="chatgpt-conversation",
                secret="local-secret",
                prompt="create a blue circle",
                timeout_seconds=30,
            )

        self.assertEqual(result.payload["output_type"], "image")
        self.assertEqual(result.payload["mime_type"], "image/png")
        self.assertEqual(base64.b64decode(result.payload["data_base64"]), raw)
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer local-secret")
        self.assertEqual(post.call_args.kwargs["url"] if "url" in post.call_args.kwargs else post.call_args.args[0], "https://uploaded.example/v1/chat/completions")

    def test_extracts_text_from_ordinary_chat_completion(self):
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({
            "choices": [{"message": {"content": "Live answer with sources."}}],
            "usage": {"total_tokens": 8},
        }).encode()
        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=response) as post:
            result = ChatGPTConversationImageAdapter("https://uploaded.example").complete_interaction_text(
                model="chatgpt-conversation",
                secret="local-secret",
                system_prompt="Be concise.",
                user_prompt="What is the current status?",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["output_type"], "text")
        self.assertEqual(result.payload["text"], "Live answer with sources.")
        self.assertEqual(post.call_args.kwargs["json"]["messages"], [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "What is the current status?"},
        ])

    def test_search_route_adds_live_web_instruction(self):
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"choices":[{"message":{"content":"Sourced answer"}}]}'
        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=response) as post:
            ChatGPTConversationImageAdapter("https://uploaded.example").complete_interaction_text(
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

    def test_missing_image_is_terminal_invalid_response(self):
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"choices":[{"message":{"content":"text only"}}]}'
        with patch("ai_router.providers.chatgpt_conversation_image.requests.post", return_value=response), self.assertRaisesRegex(ProviderError, "no image"):
            ChatGPTConversationImageAdapter("https://uploaded.example").generate_image(
                model="chatgpt-conversation",
                secret="local-secret",
                prompt="create an image",
                timeout_seconds=30,
            )

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
