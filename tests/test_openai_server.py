from __future__ import annotations

import http.client
import json
import threading
import unittest

from ai_router.openai_server import RouterHTTPServer


class FakeRouter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete_chat(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "role": "assistant",
            "content": "ready",
            "tool_calls": [],
            "finish_reason": "stop",
            "provider": "groq",
            "model": "test-model",
            "route": "default",
        }


class OpenAIServerTests(unittest.TestCase):
    def test_auth_selection_and_metadata(self) -> None:
        router = FakeRouter()
        server = RouterHTTPServer(("127.0.0.1", 0), router, "local-secret")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            connection = http.client.HTTPConnection(host, port, timeout=5)
            connection.request("GET", "/v1/models")
            unauthorized = connection.getresponse()
            self.assertEqual(unauthorized.status, 401)
            unauthorized.read()

            body = json.dumps({
                "model": "ai-provider-router",
                "messages": [{"role": "user", "content": "hello"}],
                "tools": [{"type": "function", "function": {"name": "lookup"}}],
                "router_provider": "groq",
                "router_model": "test-model",
            })
            connection.request(
                "POST",
                "/v1/chat/completions",
                body=body,
                headers={"Authorization": "Bearer local-secret", "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["router_provider"], "groq")
            self.assertEqual(payload["router_model"], "test-model")
            self.assertEqual(response.getheader("X-AI-Router-Provider"), "groq")
            self.assertEqual(response.getheader("X-AI-Router-Model"), "test-model")
            self.assertEqual(router.calls[0]["provider"], "groq")
            self.assertEqual(router.calls[0]["model"], "test-model")
            self.assertEqual(router.calls[0]["tools"][0]["type"], "function")
        finally:
            connection.close()
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
