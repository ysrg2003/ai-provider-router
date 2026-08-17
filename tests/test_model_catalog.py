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
        self.assertEqual(image_route[0]["provider"], "chatgpt_space")
        self.assertEqual(image_route[0]["model"], "gpt-4o-mini")
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
