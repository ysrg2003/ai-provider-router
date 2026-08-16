import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_router import AIRouter
from ai_router.providers.openai_compatible import OpenAICompatibleAdapter

ROOT = Path(__file__).parents[1]


class FakeResponse:
    status_code = 200
    text = ''

    def __init__(self):
        self._payload = {
            'choices': [{'message': {'content': '{"ok": true}'}}],
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1},
        }

    def json(self):
        return self._payload


class OpenRouterAdapterTests(unittest.TestCase):
    def test_supported_response_format_is_sent(self):
        adapter = OpenAICompatibleAdapter('openrouter', 'https://openrouter.ai/api/v1')
        with patch('ai_router.providers.openai_compatible.requests.post', return_value=FakeResponse()) as post:
            result = adapter.complete_json(
                model='nvidia/nemotron-3-super-120b-a12b:free',
                secret='placeholder-openrouter-key',
                system_prompt='Return JSON only.',
                user_prompt='Return ok true.',
                timeout_seconds=30,
                supports_response_format=True,
            )
        self.assertEqual(result.payload, {'ok': True})
        self.assertEqual(post.call_args.args[0], 'https://openrouter.ai/api/v1/chat/completions')
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer placeholder-openrouter-key')
        self.assertEqual(post.call_args.kwargs['json']['response_format'], {'type': 'json_object'})

    def test_openrouter_single_token_fallback_is_loaded(self):
        previous = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = "placeholder-openrouter-key"
        try:
            with tempfile.TemporaryDirectory() as temp:
                router = AIRouter(config_dir=ROOT / "config", state_db=Path(temp) / "router.db")
                keys = router.config.keys_for("openrouter")
                self.assertEqual(len(keys), 1)
                self.assertEqual(keys[0].secret, "placeholder-openrouter-key")
                self.assertIn("openrouter", router.summary()["config"]["providers"])
                router.close()
        finally:
            if previous is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = previous

    def test_unsupported_response_format_is_omitted(self):
        adapter = OpenAICompatibleAdapter('openrouter', 'https://openrouter.ai/api/v1')
        with patch('ai_router.providers.openai_compatible.requests.post', return_value=FakeResponse()) as post:
            result = adapter.complete_json(
                model='nvidia/nemotron-3-ultra-550b-a55b:free',
                secret='placeholder-openrouter-key',
                system_prompt='Return JSON only.',
                user_prompt='Return ok true.',
                timeout_seconds=30,
                supports_response_format=False,
            )
        self.assertEqual(result.payload, {'ok': True})
        self.assertNotIn('response_format', post.call_args.kwargs['json'])


if __name__ == '__main__':
    unittest.main()
