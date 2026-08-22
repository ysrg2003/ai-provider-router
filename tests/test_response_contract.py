import unittest

from ai_router.response_contract import ResponseContractError, validate_response_envelope


class ResponseContractTests(unittest.TestCase):
    def base(self, output_type="text"):
        return {
            "output_type": output_type,
            "intent": output_type,
            "route": output_type,
            "provider": "test-provider",
            "model": "test-model",
            "url_citations": [],
        }

    def test_text_structured_response_is_valid(self):
        result = validate_response_envelope({**self.base(), "answer": "ok"})
        self.assertEqual(result["provider"], "test-provider")

    def test_translation_requires_text(self):
        result = validate_response_envelope({**self.base("translation"), "translation": "مرحبا"})
        self.assertEqual(result["translation"], "مرحبا")

    def test_image_requires_valid_base64_and_mime_type(self):
        result = validate_response_envelope({**self.base("image"), "data_base64": "aW1hZ2U=", "mime_type": "image/png"})
        self.assertEqual(result["mime_type"], "image/png")

    def test_audio_requires_integer_sample_rate_when_present(self):
        with self.assertRaises(ResponseContractError):
            validate_response_envelope({**self.base("audio"), "data_base64": "c29uZw==", "mime_type": "audio/pcm", "sample_rate_hz": "24000"})

    def test_embedding_requires_nonempty_values(self):
        result = validate_response_envelope({**self.base("embedding"), "embeddings": [{"values": [0.1, 0.2]}]})
        self.assertEqual(result["embeddings"][0]["values"], [0.1, 0.2])

    def test_missing_common_field_is_rejected(self):
        payload = self.base()
        del payload["model"]
        with self.assertRaisesRegex(ResponseContractError, "model"):
            validate_response_envelope(payload)

    def test_invalid_citation_is_rejected(self):
        with self.assertRaises(ResponseContractError):
            validate_response_envelope({**self.base(), "answer": "ok", "url_citations": ["not-a-url"]})


if __name__ == "__main__":
    unittest.main()
