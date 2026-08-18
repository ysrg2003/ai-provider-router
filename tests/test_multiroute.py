import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_router import AIRouter
from ai_router.intent import detect_intent
from ai_router.providers.base import ProviderResponse
from ai_router.providers.chatgpt_space import ChatGPTSpaceAdapter
from ai_router.providers.gemini import GeminiAdapter


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


class ChatGPTSpaceAdapterTests(unittest.TestCase):
    def test_text_search_prefix_and_auth_header(self):
        adapter = ChatGPTSpaceAdapter("https://space.example")
        response = FakeResponse({"choices": [{"message": {"content": "grounded"}}], "usage": {"total_tokens": 3}})
        with patch("ai_router.providers.chatgpt_space.requests.post", return_value=response) as post:
            result = adapter.complete_interaction_text(
                model="gpt-4o-mini",
                secret="secret",
                system_prompt="",
                user_prompt="ما آخر موديل؟",
                timeout_seconds=300,
                tools=[{"type": "search"}],
            )
        self.assertEqual(result.payload["text"], "grounded")
        self.assertEqual(post.call_args.args[0], "https://space.example/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(post.call_args.kwargs["json"]["messages"][0]["content"], "ابحث في الويب بحث حي: ما آخر موديل؟")

    def test_image_retries_when_first_response_has_no_images(self):
        adapter = ChatGPTSpaceAdapter("https://space.example")
        empty = FakeResponse({"choices": [{"message": {"content": "still generating"}}]})
        success = FakeResponse({
            "choices": [{"message": {"content": "done"}}],
            "images": [{"data_url": "data:image/png;base64,aW1hZ2U="}],
        })
        with patch("ai_router.providers.chatgpt_space.requests.post", side_effect=[empty, success]) as post, patch("ai_router.providers.chatgpt_space.time.sleep") as sleep:
            result = adapter.generate_image(
                model="gpt-4o-mini",
                secret="secret",
                prompt="draw a cat",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["data_base64"], "aW1hZ2U=")
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(20)
        self.assertEqual(post.call_args_list[0].kwargs["timeout"], 540)

    def test_image_quota_response_is_terminal(self):
        adapter = ChatGPTSpaceAdapter("https://space.example")
        response = FakeResponse({"choices": [{"message": {"content": "You've hit the Free plan limit for image generations requests."}}]})
        with patch("ai_router.providers.chatgpt_space.requests.post", return_value=response), patch("ai_router.providers.chatgpt_space.time.sleep") as sleep:
            with self.assertRaisesRegex(Exception, "quota") as raised:
                adapter.generate_image(
                    model="gpt-4o-mini",
                    secret="secret",
                    prompt="draw a cat",
                    timeout_seconds=30,
                )
        self.assertEqual(raised.exception.error_class, "quota")
        sleep.assert_not_called()

    def test_image_src_fallback_is_downloaded(self):
        adapter = ChatGPTSpaceAdapter("https://space.example")
        response = FakeResponse({
            "choices": [{"message": {"content": "done"}}],
            "images": [{"src": "https://cdn.example/image.png"}],
        })
        download = FakeResponse({})
        download.content = b"png-bytes"
        download.headers = {"content-type": "image/png"}
        download.raise_for_status = lambda: None
        with patch("ai_router.providers.chatgpt_space.requests.post", return_value=response), patch("ai_router.providers.chatgpt_space.requests.get", return_value=download) as get:
            result = adapter.generate_image(
                model="gpt-4o-mini",
                secret="secret",
                prompt="draw a cat",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["output_type"], "image")
        self.assertEqual(result.payload["mime_type"], "image/png")
        self.assertEqual(result.payload["data_base64"], "cG5nLWJ5dGVz")
        self.assertEqual(get.call_args.args[0], "https://cdn.example/image.png")

    def test_image_data_url_is_normalized(self):
        adapter = ChatGPTSpaceAdapter("https://space.example")
        response = FakeResponse({
            "choices": [{"message": {"content": "done"}}],
            "images": [{"data_url": "data:image/png;base64,aW1hZ2U="}],
        })
        with patch("ai_router.providers.chatgpt_space.requests.post", return_value=response):
            result = adapter.generate_image(
                model="gpt-4o-mini",
                secret="secret",
                prompt="draw a cat",
                timeout_seconds=30,
            )
        self.assertEqual(result.payload["output_type"], "image")
        self.assertEqual(result.payload["data_base64"], "aW1hZ2U=")
        self.assertEqual(result.payload["mime_type"], "image/png")


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
            live_plan = router.route_plan(user_prompt="أريد محادثة صوتية مباشرة")
            video_plan = router.route_plan(user_prompt="توليد فيديو سينمائي")
            self.assertEqual(image_plan["output_type"], "image")
            self.assertEqual(image_plan["route"], "image")
            self.assertEqual(image_plan["models"][0]["provider"], "chatgpt_space")
            self.assertEqual(image_plan["models"][0]["model"], "gpt-4o-mini")
            self.assertEqual(image_plan["models"][0]["input_types"], ["text", "image"])
            self.assertEqual(image_plan["models"][0]["output_types"], ["image", "text"])
            self.assertEqual(audio_plan["models"][0]["model"], "gemini-3.1-flash-tts-preview")
            self.assertEqual(audio_plan["models"][0]["input_types"], ["text"])
            self.assertEqual(audio_plan["models"][0]["output_types"], ["audio"])
            self.assertEqual(search_plan["route"], "text_grounded_search")
            self.assertEqual(search_plan["models"][0]["provider"], "chatgpt_space")
            self.assertEqual(search_plan["models"][0]["tools"], ["search"])
            self.assertEqual(live_plan["output_type"], "live")
            self.assertEqual(video_plan["output_type"], "video_generation")
            router.close()

    def test_complete_auto_executes_image_route(self):
        import os

        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = '[{"id":"image-key","key":"secret","project":"p1"}]'
            try:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                with patch.object(
                    router.adapters["google_gemini"],
                    "generate_image",
                    return_value=ProviderResponse({"output_type": "image", "data_base64": "aW1hZ2U="}, {}),
                ) as generate:
                    result = router.complete_auto(user_prompt="أنشئ صورة لقطة")
                self.assertEqual(result["route"], "image")
                self.assertEqual(result["intent"], "image")
                self.assertEqual(generate.call_args.kwargs["model"], "gemini-3-pro-image")

                router.close()
            finally:
                os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)

    def test_complete_auto_passes_grounding_tool(self):
        import os

        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = '[{"id":"search-key","key":"secret","project":"p1"}]'
            try:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                with patch.object(
                    router.adapters["google_gemini"],
                    "complete_interaction_text",
                    return_value=ProviderResponse({"output_type": "text", "text": "grounded"}, {}),
                ) as complete:
                    result = router.complete_auto(user_prompt="ما آخر الأخبار؟", output_type="text", grounding="search")
                self.assertEqual(result["route"], "text_grounded_search")
                self.assertEqual(complete.call_args.kwargs["tools"], [{"type": "google_search"}])
                router.close()
            finally:
                os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)

    def test_summary_exposes_output_routes_without_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            summary = router.summary()
            self.assertIn("image", summary["config"]["output_routes"])
            self.assertIn("embedding", summary["config"]["output_routes"])
            router.close()


if __name__ == "__main__":
    unittest.main()
