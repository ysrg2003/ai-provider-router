import unittest

from ai_router.providers.base import url_citations_from_annotations, url_citations_from_text
from ai_router.providers.chatgpt_space import ChatGPTSpaceAdapter
from ai_router.providers.gemini import GeminiAdapter


class SearchContractTests(unittest.TestCase):
    def test_url_citations_from_text_preserves_explicit_urls_only(self):
        text = 'Sources: https://www.nasa.gov/eclipse. Also https://example.org/page, and the same https://www.nasa.gov/eclipse.'
        self.assertEqual(
            url_citations_from_text(text),
            ['https://www.nasa.gov/eclipse', 'https://example.org/page'],
        )

    def test_url_citations_from_annotations_normalizes_bare_domains(self):
        annotations = [{"url": "www.nasa.gov/eclipse"}, {"href": "example.org/page"}]
        self.assertEqual(
            url_citations_from_annotations(annotations),
            ['https://www.nasa.gov/eclipse', 'https://example.org/page'],
        )

    def test_url_citations_from_annotations_reads_structured_url_fields(self):
        annotations = [
            {"type": "url_citation", "url": "https://www.nasa.gov/eclipse"},
            {"citation": {"uri": "https://example.org/page"}},
        ]
        self.assertEqual(
            url_citations_from_annotations(annotations),
            ['https://www.nasa.gov/eclipse', 'https://example.org/page'],
        )

    def test_url_citations_from_annotations_reads_tool_content_blocks(self):
        value = {"tool_output": {"content": [{"annotation": "https://www.nasa.gov/eclipse"}, {"text": "Source: https://example.org/page"}]}}
        self.assertEqual(
            url_citations_from_annotations(value),
            ["https://www.nasa.gov/eclipse", "https://example.org/page"],
        )

    def test_url_citations_from_annotations_accepts_direct_url_strings(self):
        self.assertEqual(
            url_citations_from_annotations(["https://www.nasa.gov/eclipse", "https://example.org/page"]),
            ["https://www.nasa.gov/eclipse", "https://example.org/page"],
        )

    def test_url_citations_from_text_extracts_embedded_json(self):
        text = 'Search result summary: {"sources":[{"url":"www.nasa.gov/eclipse"}]} End.'
        self.assertEqual(url_citations_from_text(text), ['https://www.nasa.gov/eclipse'])

    def test_url_citations_from_text_unescapes_json_slashes(self):
        text = r'{"sources":[{"url":"https:\/\/www.nasa.gov\/eclipse"}]}'
        self.assertEqual(url_citations_from_text(text), ['https://www.nasa.gov/eclipse'])

    def test_chatgpt_content_blocks_are_flattened_before_url_extraction(self):
        adapter = ChatGPTSpaceAdapter('https://example.invalid')
        adapter._post = lambda **kwargs: {
            "choices": [{"message": {"content": [
                {"type": "text", "text": r'{"url":"https:\/\/www.nasa.gov\/eclipse"}'},
                {"type": "text", "text": "Additional context."},
            ]}}]
        }
        response = adapter.complete_interaction_text(
            model='gpt-4o-mini',
            secret='test-secret',
            system_prompt='Search.',
            user_prompt='Return JSON.',
            timeout_seconds=1,
            tools=[{"type": "search"}],
        )
        self.assertEqual(response.payload['url_citations'], ['https://www.nasa.gov/eclipse'])

    def test_chatgpt_complete_json_preserves_search_metadata(self):
        adapter = ChatGPTSpaceAdapter('https://example.invalid')
        adapter._post = lambda **kwargs: {
            "choices": [{"message": {"content": '{"sources":[{"url":"https://www.nasa.gov/eclipse"}],"url_citations":[]}'}}],
        }
        response = adapter.complete_json(
            model='gpt-4o-mini',
            secret='test-secret',
            system_prompt='Search.',
            user_prompt='Return JSON.',
            timeout_seconds=1,
        )
        self.assertEqual(response.payload['url_citations'], ['https://www.nasa.gov/eclipse'])
        self.assertIn('provider_text', response.payload)

    def test_chatgpt_interaction_exposes_structured_body_citations(self):
        adapter = ChatGPTSpaceAdapter('https://example.invalid')
        adapter._post = lambda **kwargs: {
            "choices": [{"message": {"content": '{"sources":[{"url":"https://www.nasa.gov/eclipse"}]}'}}],
            "citations": [{"href": "https://example.org/primary"}],
        }
        response = adapter.complete_interaction_text(
            model='gpt-4o-mini',
            secret='test-secret',
            system_prompt='Search.',
            user_prompt='Return JSON.',
            timeout_seconds=1,
            tools=[{"type": "search"}],
        )
        self.assertEqual(response.payload['url_citations'], ['https://www.nasa.gov/eclipse', 'https://example.org/primary'])

    def test_gemini_interaction_exposes_body_urls_as_url_citations(self):
        adapter = GeminiAdapter('https://example.invalid')
        adapter._post_interactions = lambda **kwargs: {
            "steps": [{"type": "model_output", "content": [{"type": "text", "text": 'A grounded result.'}]}],
            "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://www.youtube.com/watch?v=abcdefghijk"}}]},
        }
        response = adapter.complete_interaction_text(
            model='gemini-2.5-flash',
            secret='test-secret',
            system_prompt='Search.',
            user_prompt='Return JSON.',
            timeout_seconds=1,
            tools=[{"type": "search"}],
        )
        self.assertEqual(response.payload['url_citations'], ['https://www.youtube.com/watch?v=abcdefghijk'])

    def test_chatgpt_interaction_exposes_text_urls_as_url_citations(self):
        adapter = ChatGPTSpaceAdapter('https://example.invalid')
        adapter._post = lambda **kwargs: {
            "choices": [{"message": {"content": '{"sources":[{"url":"https://www.nasa.gov/eclipse"}]}'}}]
        }
        response = adapter.complete_interaction_text(
            model='gpt-4o-mini',
            secret='test-secret',
            system_prompt='Search.',
            user_prompt='Return JSON.',
            timeout_seconds=1,
            tools=[{"type": "search"}],
        )
        self.assertEqual(response.payload['url_citations'], ['https://www.nasa.gov/eclipse'])
        self.assertEqual(response.payload['annotations'], [])


if __name__ == '__main__':
    unittest.main()
