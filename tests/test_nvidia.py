import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_router import AIRouter
from ai_router.providers.openai_compatible import OpenAICompatibleAdapter

ROOT = Path(__file__).parents[1]


class FakeNvidiaResponse:
    status_code = 200
    text = ''

    def json(self):
        return {
            'choices': [{'message': {'content': '{"provider": "nvidia", "ok": true}'}}],
            'usage': {'prompt_tokens': 2, 'completion_tokens': 3},
        }


class NvidiaRouterTests(unittest.TestCase):
    def test_nvidia_openai_compatible_request_shape(self):
        adapter = OpenAICompatibleAdapter('nvidia', 'https://integrate.api.nvidia.com/v1')
        with patch('ai_router.providers.openai_compatible.requests.post', return_value=FakeNvidiaResponse()) as post:
            result = adapter.complete_json(
                model='minimaxai/minimax-m3',
                secret='placeholder-nvidia-key',
                system_prompt='Return JSON only.',
                user_prompt='Return ok true.',
                timeout_seconds=30,
                supports_response_format=False,
            )
        self.assertEqual(result.payload, {'provider': 'nvidia', 'ok': True})
        self.assertEqual(post.call_args.args[0], 'https://integrate.api.nvidia.com/v1/chat/completions')
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer placeholder-nvidia-key')
        self.assertNotIn('response_format', post.call_args.kwargs['json'])

    def test_nvidia_single_token_fallback_is_loaded(self):
        previous = os.environ.get('NVIDIA_API_KEY')
        previous_json = os.environ.get('NVIDIA_API_KEYS_JSON')
        os.environ['NVIDIA_API_KEY'] = 'placeholder-nvidia-key'
        os.environ.pop('NVIDIA_API_KEYS_JSON', None)
        try:
            with tempfile.TemporaryDirectory() as temp:
                router = AIRouter(config_dir=ROOT / 'config', state_db=Path(temp) / 'router.db')
                keys = router.config.keys_for('nvidia')
                self.assertEqual(len(keys), 1)
                self.assertEqual(keys[0].secret, 'placeholder-nvidia-key')
                router.close()
        finally:
            if previous is None:
                os.environ.pop('NVIDIA_API_KEY', None)
            else:
                os.environ['NVIDIA_API_KEY'] = previous
            if previous_json is None:
                os.environ.pop('NVIDIA_API_KEYS_JSON', None)
            else:
                os.environ['NVIDIA_API_KEYS_JSON'] = previous_json

    def test_nvidia_routes_follow_openrouter_and_exclude_image(self):
        models = json.loads((ROOT / 'config' / 'models.json').read_text(encoding='utf-8'))
        self.assertEqual(len(models['model_chains']['nvidia_free']), 12)
        for route_name in ('default', 'creative', 'cheap'):
            entries = models['model_chains'][route_name]
            openrouter_indexes = [i for i, item in enumerate(entries) if item['provider'] == 'openrouter']
            nvidia_indexes = [i for i, item in enumerate(entries) if item['provider'] == 'nvidia']
            groq_indexes = [i for i, item in enumerate(entries) if item['provider'] == 'groq']
            huggingface_indexes = [i for i, item in enumerate(entries) if item['provider'] == 'huggingface']
            self.assertTrue(openrouter_indexes)
            self.assertTrue(nvidia_indexes)
            self.assertTrue(groq_indexes)
            self.assertTrue(huggingface_indexes)
            self.assertGreater(min(nvidia_indexes), max(openrouter_indexes))
            self.assertLess(max(groq_indexes), min(huggingface_indexes))
        entries = models['output_routes']['text']
        openrouter_indexes = [i for i, item in enumerate(entries) if item['provider'] == 'openrouter']
        nvidia_indexes = [i for i, item in enumerate(entries) if item['provider'] == 'nvidia']
        self.assertTrue(nvidia_indexes)
        if openrouter_indexes:
            self.assertGreater(min(nvidia_indexes), max(openrouter_indexes))
        groq_indexes = [i for i, item in enumerate(entries) if item['provider'] == 'groq']
        huggingface_indexes = [i for i, item in enumerate(entries) if item['provider'] == 'huggingface']
        self.assertTrue(groq_indexes)
        self.assertTrue(huggingface_indexes)
        self.assertLess(max(groq_indexes), min(huggingface_indexes))

        grounded_entries = models['output_routes']['text_grounded_search']
        self.assertEqual(
            [item['provider'] for item in grounded_entries],
            ['google_gemini'] * 8,
        )
        self.assertEqual(grounded_entries[0]['model'], 'gemini-2.5-flash')
        self.assertTrue(all(item['method'] == 'grounded_text' for item in grounded_entries))
        self.assertTrue(all(item['tools'] == ['search'] for item in grounded_entries))
        self.assertFalse(any(item['provider'] == 'nvidia' for item in grounded_entries))
        self.assertFalse(any(item['provider'] == 'nvidia' for item in models['output_routes']['image']))
        all_nvidia_models = [item['model'] for item in models['model_chains']['nvidia_free']]
        self.assertNotIn('nvidia/riva-translate-4b-instruct-v2', all_nvidia_models)
        self.assertNotIn('meta/llama-3.2-11b-vision-instruct', all_nvidia_models)
        self.assertNotIn('meta/llama-3.1-8b-instruct', all_nvidia_models)

    def test_router_initializes_without_nvidia_key(self):
        previous = os.environ.pop('NVIDIA_API_KEY', None)
        previous_json = os.environ.pop('NVIDIA_API_KEYS_JSON', None)
        try:
            with tempfile.TemporaryDirectory() as temp:
                router = AIRouter(config_dir=ROOT / 'config', state_db=Path(temp) / 'router.db')
                self.assertEqual(router.config.keys_for('nvidia'), [])
                self.assertIn('nvidia', router.summary()['config']['providers'])
                router.close()
        finally:
            if previous is not None:
                os.environ['NVIDIA_API_KEY'] = previous
            if previous_json is not None:
                os.environ['NVIDIA_API_KEYS_JSON'] = previous_json


if __name__ == '__main__':
    unittest.main()
