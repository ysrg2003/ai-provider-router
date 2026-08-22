import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class ModelCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = json.loads((ROOT / "config" / "models.json").read_text(encoding="utf-8"))
        cls.catalog = (ROOT / "docs" / "model-catalog.md").read_text(encoding="utf-8")

    def test_reference_catalog_and_table_are_present(self):
        reference = self.models["reference_catalog"]
        self.assertEqual(reference["source_file"], "docs/model-catalog.md")
        self.assertEqual(reference["model_rows"], 24)
        self.assertEqual(reference["tool_rows"], 13)
        self.assertIn("`Imagen 4 Fast Generate`", self.catalog)
        self.assertIn("`Gemini 3.1 Flash TTS`", self.catalog)

    def test_image_route_uses_current_native_models_and_legacy_imagen_is_disabled(self):
        image_route = self.models["output_routes"]["image"]
        self.assertEqual(
            [item["provider"] for item in image_route[:2]],
            ["google_gemini", "google_gemini"],
        )
        self.assertEqual(image_route[0]["model"], "gemini-3-pro-image")
        self.assertEqual(
            [item["model"] for item in image_route if item["provider"] == "google_gemini"],
            [
                "gemini-3-pro-image",
                "gemini-3.1-flash-image",
                "gemini-3.1-flash-lite-image",
                "gemini-2.5-flash-image",
            ],
        )
        self.assertEqual(
            [item["model"] for item in self.models["output_routes"]["image_legacy"]],
            [
                "imagen-4.0-ultra-generate-001",
                "imagen-4.0-generate-001",
                "imagen-4.0-fast-generate-001",
            ],
        )
        self.assertTrue(all(not item["enabled"] for item in self.models["output_routes"]["image_legacy"]))

    def test_tts_route_uses_only_attached_tts_rows(self):
        self.assertEqual(
            [item["model"] for item in self.models["output_routes"]["audio"]],
            ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"],
        )
        self.assertNotIn("gemini-2.5-pro-preview-tts", [item["model"] for item in self.models["output_routes"]["audio"]])

    def test_nvidia_free_catalog_snapshot_and_order_are_present(self):
        reference = self.models["reference_catalog"]["nvidia_free"]
        self.assertEqual(reference["catalog_free_endpoint_count"], 57)
        self.assertEqual(reference["source"]["api_base"], "https://integrate.api.nvidia.com/v1")
        catalog = json.loads((ROOT / "config" / "nvidia_free_catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(reference["catalog_file"], "config/nvidia_free_catalog.json")
        self.assertEqual(len(catalog["models"]), 57)
        self.assertEqual(len({item["name"] for item in catalog["models"]}), 57)
        self.assertEqual(len(reference["active_text_models"]), 12)
        deprecated = {item["api_model"] for item in catalog["models"] if item["deprecated"]}
        self.assertTrue(deprecated.isdisjoint(reference["active_text_models"]))
        self.assertEqual(
            [item["model"] for item in self.models["model_chains"]["nvidia_free"]],
            reference["active_text_models"],
        )
        self.assertIn("z-ai/glm-5.2", reference["active_text_models"])
        self.assertNotIn("minimaxai/minimax-m3", reference["active_text_models"])
        self.assertNotIn("nvidia/riva-translate-4b-instruct-v2", reference["active_text_models"])
        self.assertNotIn("meta/llama-3.2-11b-vision-instruct", reference["active_text_models"])
        self.assertEqual(reference["specialized_functional_models"], ["nvidia/riva-translate-4b-instruct-v2"])
        self.assertEqual(reference["json_incompatible_models"], ["meta/llama-3.2-11b-vision-instruct", "meta/llama-3.1-8b-instruct"])
        self.assertNotIn("nvidia", {item["provider"] for item in self.models["output_routes"]["image"]})

    def test_openrouter_free_catalog_and_order_are_present(self):
        reference = self.models["reference_catalog"]["openrouter_free"]
        self.assertEqual(reference["count"], 19)
        self.assertEqual(len(reference["active_text_models"]), 16)
        self.assertEqual(reference["active_text_models"][0], "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(reference["active_text_models"][-1], "openrouter/free")
        self.assertEqual(
            reference["audio_catalog_disabled"],
            ["google/lyria-3-clip-preview", "google/lyria-3-pro-preview"],
        )
        self.assertEqual(reference["moderation_catalog_disabled"], ["nvidia/nemotron-3.5-content-safety:free"])
        self.assertIn("openrouter", {item["provider"] for item in self.models["model_chains"]["openrouter_free"]})
        self.assertEqual(
            [item["model"] for item in self.models["model_chains"]["openrouter_free"]],
            reference["active_text_models"],
        )

    def test_grounded_search_route_starts_with_25_flash_and_contains_all_text_gemini_models(self):
        self.assertEqual(
            [item["model"] for item in self.models["output_routes"]["text_grounded_search"]],
            [
                "gemini-2.5-flash",
                "gemini-3.7-flash",
                "gemini-3.6-flash",
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.1-flash-lite",
                "gemini-3-flash",
                "gemini-2.5-flash-lite",
            ],
        )
        self.assertTrue(all(item["method"] == "grounded_text" for item in self.models["output_routes"]["text_grounded_search"]))
        self.assertTrue(all(item["tools"] == ["search"] for item in self.models["output_routes"]["text_grounded_search"]))

    def test_text_out_route_matches_eight_attached_gemini_rows(self):
        self.assertEqual(
            [item["model"] for item in self.models["output_routes"]["text"] if item["provider"] == "google_gemini"],
            [
                "gemini-3.7-flash",
                "gemini-3.6-flash",
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.1-flash-lite",
                "gemini-3-flash",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
            ],
        )


if __name__ == "__main__":
    unittest.main()
