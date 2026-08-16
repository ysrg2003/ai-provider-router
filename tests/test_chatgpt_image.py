import base64
import unittest
from unittest.mock import Mock, patch

from ai_router.providers.base import ProviderError
from ai_router.providers.chatgpt_image import ChatGPTImageAdapter


class FakeResponse:
    def __init__(self, status_code, body=None, *, content=b"", headers=None):
        self.status_code = status_code
        self._body = body or {}
        self.content = content
        self.headers = headers or {}
        self.text = ""

    def json(self):
        return self._body


class ChatGPTImageAdapterTests(unittest.TestCase):
    def test_job_poll_and_image_download(self):
        adapter = ChatGPTImageAdapter("https://space.example", poll_interval_seconds=0)
        image_bytes = b"\x89PNG\r\n\x1a\nimage"
        session = Mock()
        session.headers = {}
        session.post.return_value = FakeResponse(200, {"job_id": "job-1", "status": "queued"})
        session.get.side_effect = [
            FakeResponse(200, {"job_id": "job-1", "status": "running"}),
            FakeResponse(200, {"job_id": "job-1", "status": "done"}),
            FakeResponse(200, content=image_bytes, headers={"content-type": "image/png"}),
        ]
        with patch(
            "ai_router.providers.chatgpt_image.requests.Session",
            return_value=session,
        ):
            result = adapter.generate_image(
                model="chatgpt-api",
                secret="space-secret",
                prompt="a blue circle on white",
                timeout_seconds=30,
            )

        self.assertEqual(result.payload["output_type"], "image")
        self.assertEqual(result.payload["mime_type"], "image/png")
        self.assertEqual(base64.b64decode(result.payload["data_base64"]), image_bytes)
        self.assertEqual(session.post.call_args.kwargs["json"], {"prompt": "a blue circle on white"})
        self.assertEqual(session.headers["Authorization"], "space-secret")
        self.assertEqual(session.get.call_count, 3)

    def test_auth_error_is_not_retryable(self):
        adapter = ChatGPTImageAdapter("https://space.example")
        session = Mock()
        session.headers = {}
        session.post.return_value = FakeResponse(401, {"error": {"message": "Invalid API Key"}})
        with patch(
            "ai_router.providers.chatgpt_image.requests.Session",
            return_value=session,
        ), self.assertRaises(ProviderError) as raised:
            adapter.generate_image(
                model="chatgpt-api",
                secret="wrong",
                prompt="a test image",
                timeout_seconds=30,
            )
        self.assertEqual(raised.exception.error_class, "auth")
        self.assertFalse(raised.exception.retryable)

    def test_image_input_falls_back_instead_of_being_sent_as_text_only(self):
        adapter = ChatGPTImageAdapter("https://space.example")
        with self.assertRaises(ProviderError) as raised:
            adapter.generate_image(
                model="chatgpt-api",
                secret="space-secret",
                prompt="edit this image",
                timeout_seconds=30,
                image_data="aW1hZ2U=",
            )
        self.assertEqual(raised.exception.error_class, "invalid_or_unknown")
        self.assertFalse(raised.exception.retryable)


if __name__ == "__main__":
    unittest.main()
