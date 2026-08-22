import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_router import AIRouter
from ai_router.intent import detect_intent
from ai_router.providers.base import ProviderError, ProviderResponse
from ai_router.providers.gemini import GROUNDED_SEARCH_PROMPT_PREFIX, GeminiAdapter
from ai_router.providers.openai_compatible import OpenAICompatibleAdapter


class FakeResponse:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


class IntentTests(unittest.TestCase):
    def test_explicit_output_type_wins(self):
        intent = detect_intent("اكتب وصفًا لصورة", output_type="audio")
        self.assertEqual(intent.output_type, "audio")
        self.assertEqual(intent.confidence, "explicit")

    def test_automatic_image_and_grounding_detection(self):
        intent = detect_intent("أنشئ صورة عن الطقس الحالي مع مصادر حديثة")
        self.assertEqual(intent.output_type, "image")
        self.assertEqual(intent.grounding, "search")

    def test_maps_detection_precedes_generic_search(self):
        intent = detect_intent("ابحث في خرائط Google عن مطاعم قريبة مني")
        self.assertEqual(intent.grounding, "maps")

    def test_translation_detection(self):
        intent = detect_intent("ترجم هذا النص إلى العربية")
        self.assertEqual(intent.output_type, "translation")
        self.assertEqual(intent.confidence, "heuristic")


class OpenAICompatibleTranslationTests(unittest.TestCase):
    def test_complete_text_uses_raw_completion_contract(self):
        adapter = OpenAICompatibleAdapter("nvidia", "https://integrate.api.nvidia.com/v1")
        response = FakeResponse({"choices": [{"message": {"content": "هذه هي الترجمة"}}], "usage": {"total_tokens": 3}})
        with patch("ai_router.providers.openai_compatible.requests.post", return_value=response) as post:
            result = adapter.complete_text(
                model="nvidia/riva-translate-4b-instruct-v2",
                secret="secret",
                system_prompt="Translate only.",
                user_prompt="Translate this.",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["translation"], "هذه هي الترجمة")
        self.assertNotIn("response_format", post.call_args.kwargs["json"])


class GeminiMultimodalAdapterTests(unittest.TestCase):
    def test_image_payload_and_output(self):
        adapter = GeminiAdapter("https://generativelanguage.googleapis.com/v1beta")
        response = FakeResponse({"candidates": [{"content": {"parts": [{"inlineData": {"data": "aW1hZ2U=", "mimeType": "image/png"}}]}}], "usageMetadata": {"totalTokenCount": 5}})
        with patch("ai_router.providers.gemini.requests.post", return_value=response) as post:
            result = adapter.generate_image(
                model="gemini-3.1-flash-image",
                secret="secret",
                prompt="draw a cat",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["output_type"], "image")
        self.assertEqual(result.payload["data_base64"], "aW1hZ2U=")
        self.assertEqual(post.call_args.args[0], "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent")
        self.assertEqual(post.call_args.kwargs["json"]["contents"], [{"parts": [{"text": "draw a cat"}]}])
        self.assertEqual(post.call_args.kwargs["json"]["generationConfig"]["responseModalities"], ["TEXT", "IMAGE"])

    def test_grounded_text_generate_content_payload_and_sources(self):
        adapter = GeminiAdapter("https://generativelanguage.googleapis.com/v1beta")
        response = FakeResponse({
            "candidates": [{
                "content": {"parts": [{"text": "إجابة حديثة"}]},
                "groundingMetadata": {
                    "groundingChunks": [{"web": {"uri": "https://example.org/source", "title": "Example"}}]
                },
            }],
            "usageMetadata": {"totalTokenCount": 5},
        })
        with patch("ai_router.providers.gemini.requests.post", return_value=response) as post:
            result = adapter.complete_grounded_text(
                model="gemini-2.5-flash",
                secret="secret",
                system_prompt="Use cited sources.",
                user_prompt="What happened today?",
                timeout_seconds=30,
                tools=[{"type": "google_search"}],
            )
        self.assertEqual(result.payload["text"], "إجابة حديثة")
        self.assertEqual(result.payload["url_citations"], ["https://example.org/source"])
        self.assertEqual(result.payload["grounding_sources"], [{"title": "Example", "url": "https://example.org/source"}])
        self.assertEqual(post.call_args.args[0], "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["tools"], [{"google_search": {}}])
        self.assertEqual(payload["generationConfig"], {"temperature": 0.3})
        merged_prompt = payload["contents"][0]["parts"][0]["text"]
        self.assertTrue(merged_prompt.startswith(GROUNDED_SEARCH_PROMPT_PREFIX))
        self.assertIn("سؤال المستخدم:\nWhat happened today?", merged_prompt)

    def test_tts_payload_and_output(self):
        adapter = GeminiAdapter("https://generativelanguage.googleapis.com/v1beta")
        response = FakeResponse({"output_audio": {"data": "c29uZw==", "mime_type": "audio/pcm"}, "usage": {"total_tokens": 4}})
        with patch("ai_router.providers.gemini.requests.post", return_value=response) as post:
            result = adapter.generate_speech(
                model="gemini-3.1-flash-tts-preview",
                secret="secret",
                text="مرحبا",
                timeout_seconds=30,
                voice="Kore",
            )
        self.assertEqual(result.payload["output_type"], "audio")
        self.assertEqual(post.call_args.kwargs["json"]["response_format"], {"type": "audio"})
        self.assertEqual(post.call_args.kwargs["json"]["generation_config"]["speech_config"], [{"voice": "Kore"}])

    def test_tts_steps_audio_payload_is_normalized(self):
        adapter = GeminiAdapter("https://generativelanguage.googleapis.com/v1beta")
        response = FakeResponse({"steps": [{"type": "model_output", "content": [{"type": "audio", "data": "c29uZw==", "mime_type": "audio/pcm"}]}]})
        with patch("ai_router.providers.gemini.requests.post", return_value=response):
            result = adapter.generate_speech(
                model="gemini-3.1-flash-tts-preview",
                secret="secret",
                text="مرحبا",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["output_type"], "audio")
        self.assertEqual(result.payload["data_base64"], "c29uZw==")

    def test_embedding_payload_and_output(self):
        adapter = GeminiAdapter("https://generativelanguage.googleapis.com/v1beta")
        response = FakeResponse({"embeddings": [{"values": [0.1, 0.2]}], "usageMetadata": {"totalTokenCount": 2}})
        with patch("ai_router.providers.gemini.requests.post", return_value=response) as post:
            result = adapter.embed_content(
                model="gemini-embedding-2",
                secret="secret",
                text="meaning",
                timeout_seconds=30,
                output_dimensionality=768,
            )
        self.assertEqual(result.payload["output_type"], "embedding")
        self.assertEqual(result.payload["embeddings"][0]["values"], [0.1, 0.2])
        self.assertEqual(post.call_args.kwargs["json"]["output_dimensionality"], 768)

    def test_single_embedding_payload_is_normalized_to_a_list(self):
        adapter = GeminiAdapter("https://generativelanguage.googleapis.com/v1beta")
        response = FakeResponse({"embedding": {"values": [0.3, 0.4]}})
        with patch("ai_router.providers.gemini.requests.post", return_value=response):
            result = adapter.embed_content(
                model="gemini-embedding-2",
                secret="secret",
                text="meaning",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["embeddings"], [{"values": [0.3, 0.4]}])


class RouterRoutePlanTests(unittest.TestCase):
    def test_route_plan_chooses_image_and_search_routes(self):
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            image_plan = router.route_plan(user_prompt="أنشئ صورة لمدينة مستقبلية")
            audio_plan = router.route_plan(user_prompt="حوّل هذا النص إلى صوت", output_type="audio")
            search_plan = router.route_plan(user_prompt="ما آخر الأخبار مع مصادر حديثة؟")
            translation_plan = router.route_plan(user_prompt="ترجم هذا إلى العربية")
            live_plan = router.route_plan(user_prompt="أريد محادثة صوتية مباشرة")
            video_plan = router.route_plan(user_prompt="توليد فيديو سينمائي")
            self.assertEqual(image_plan["output_type"], "image")
            self.assertEqual(image_plan["route"], "image")
            self.assertEqual(image_plan["models"][0]["provider"], "google_gemini")
            self.assertEqual(image_plan["models"][0]["model"], "gemini-3-pro-image")
            self.assertEqual(image_plan["models"][0]["input_types"], ["text", "image"])
            self.assertEqual(image_plan["models"][0]["output_types"], ["image", "text"])
            self.assertEqual(audio_plan["models"][0]["model"], "gemini-3.1-flash-tts-preview")
            self.assertEqual(audio_plan["models"][0]["input_types"], ["text"])
            self.assertEqual(audio_plan["models"][0]["output_types"], ["audio"])
            self.assertEqual(search_plan["route"], "text_grounded_search")
            self.assertEqual(translation_plan["route"], "translation")
            self.assertEqual(translation_plan["models"][0]["model"], "nvidia/riva-translate-4b-instruct-v2")
            self.assertEqual(translation_plan["models"][0]["method"], "translation")
            self.assertEqual(search_plan["models"][0]["provider"], "google_gemini")
            self.assertEqual(search_plan["models"][0]["model"], "gemini-2.5-flash")
            self.assertEqual([item["model"] for item in search_plan["models"]], [
                "gemini-2.5-flash",
                "gemini-3.7-flash",
                "gemini-3.6-flash",
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.1-flash-lite",
                "gemini-3-flash",
                "gemini-2.5-flash-lite",
            ])
            self.assertTrue(all(item["provider"] == "google_gemini" for item in search_plan["models"]))
            self.assertTrue(all(item["method"] == "grounded_text" for item in search_plan["models"]))
            self.assertTrue(all(item["tools"] == ["search"] for item in search_plan["models"]))
            self.assertNotIn("groq", {item["provider"] for item in search_plan["models"]})
            self.assertEqual(live_plan["output_type"], "live")
            self.assertEqual(video_plan["output_type"], "video_generation")
            router.close()

    def test_complete_auto_adds_common_response_envelope(self):
        import os

        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = '[{"id":"text-key","key":"secret","project":"p1"}]'
            try:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                with patch.object(
                    router.adapters["google_gemini"],
                    "complete_json",
                    return_value=ProviderResponse({"ok": True}, {}),
                ):
                    result = router.complete_auto(user_prompt="اكتب إجابة قصيرة", output_type="text")
                self.assertEqual(result["output_type"], "text")
                self.assertEqual(result["intent"], "text")
                self.assertEqual(result["provider"], "google_gemini")
                self.assertEqual(result["model"], "gemini-3.7-flash")
                self.assertEqual(result["url_citations"], [])
                router.close()
            finally:
                os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)

    def test_complete_auto_executes_image_route(self):
        import os

        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = '[{"id":"image-key","key":"secret","project":"p1"}]'
            try:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                with patch.object(
                    router.adapters["google_gemini"],
                    "generate_image",
                    return_value=ProviderResponse({"output_type": "image", "data_base64": "aW1hZ2U=", "mime_type": "image/png"}, {}),
                ) as generate:
                    result = router.complete_auto(user_prompt="أنشئ صورة لقطة")
                self.assertEqual(result["route"], "image")
                self.assertEqual(result["intent"], "image")
                self.assertEqual(generate.call_args.kwargs["model"], "gemini-3-pro-image")
                router.close()
            finally:
                os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)

    def test_complete_auto_executes_translation_route(self):
        previous = os.environ.get("NVIDIA_API_KEY")
        os.environ["NVIDIA_API_KEY"] = "translation-secret"
        try:
            with tempfile.TemporaryDirectory() as temp:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                with patch.object(
                    router.adapters["nvidia"],
                    "complete_text",
                    return_value=ProviderResponse({"output_type": "translation", "text": "This is translated", "translation": "This is translated"}, {}),
                ) as complete:
                    result = router.complete_auto(user_prompt="ترجم هذا إلى الإنجليزية", output_type="translation")
                self.assertEqual(result["route"], "translation")
                self.assertEqual(result["intent"], "translation")
                self.assertEqual(result["translation"], "This is translated")
                self.assertEqual(complete.call_args.kwargs["model"], "nvidia/riva-translate-4b-instruct-v2")
                router.close()
        finally:
            if previous is None:
                os.environ.pop("NVIDIA_API_KEY", None)
            else:
                os.environ["NVIDIA_API_KEY"] = previous

    def test_complete_auto_passes_grounding_tool(self):
        import os

        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = '[{"id":"search-key","key":"secret","project":"p1"}]'
            try:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                with patch.object(
                    router.adapters["google_gemini"],
                    "complete_grounded_text",
                    return_value=ProviderResponse({"output_type": "text", "text": "grounded https://example.org/news", "url_citations": ["https://example.org/news"]}, {}),
                ) as complete:
                    result = router.complete_auto(user_prompt="ما آخر الأخبار؟", output_type="text", grounding="search")
                self.assertEqual(result["route"], "text_grounded_search")
                self.assertEqual(complete.call_args.kwargs["tools"], [{"type": "google_search"}])
                router.close()
            finally:
                os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)

    def test_grounded_search_falls_back_to_next_gemini_model(self):
        import os

        previous = os.environ.get("AI_ROUTER_GEMINI_KEYS_JSON")
        os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = '[{"id":"search-key","key":"secret","project":"p1"}]'
        try:
            with tempfile.TemporaryDirectory() as temp:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                attempts = []

                def fake_grounded(**kwargs):
                    attempts.append(kwargs["model"])
                    if len(attempts) == 1:
                        raise ProviderError("first search model unavailable", error_class="invalid_or_unknown", status_code=404, retryable=True)
                    return ProviderResponse({"output_type": "text", "text": "grounded fallback", "url_citations": ["https://example.org/fallback"]}, {})

                with patch.object(router.adapters["google_gemini"], "complete_grounded_text", side_effect=fake_grounded):
                    result = router.complete_auto(user_prompt="ابحث عن خبر حديث مع مصادر", output_type="text", grounding="search")
                self.assertEqual(attempts[:2], ["gemini-2.5-flash", "gemini-3.7-flash"])
                self.assertEqual(result["model"], "gemini-3.7-flash")
                self.assertEqual(result["url_citations"], ["https://example.org/fallback"])
                router.close()
        finally:
            if previous is None:
                os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)
            else:
                os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = previous

    def test_summary_exposes_output_routes_without_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            summary = router.summary()
            self.assertIn("image", summary["config"]["output_routes"])
            self.assertIn("embedding", summary["config"]["output_routes"])
            router.close()


if __name__ == "__main__":
    unittest.main()
