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

    def test_image_route_uses_only_attached_imagen_rows(self):
        self.assertEqual(
            [item["model"] for item in self.models["output_routes"]["image"]],
            [
                "imagen-4.0-ultra-generate-001",
                "imagen-4.0-generate-001",
                "imagen-4.0-fast-generate-001",
            ],
        )
        forbidden = {"gemini-3-pro-image", "gemini-3.1-flash-image", "gemini-3.1-flash-lite-image", "gemini-2.5-flash-image"}
        configured = {item["model"] for item in self.models["output_routes"]["image"]}
        self.assertTrue(forbidden.isdisjoint(configured))

    def test_tts_route_uses_only_attached_tts_rows(self):
        self.assertEqual(
            [item["model"] for item in self.models["output_routes"]["audio"]],
            ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"],
        )
        self.assertNotIn("gemini-2.5-pro-preview-tts", [item["model"] for item in self.models["output_routes"]["audio"]])

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
