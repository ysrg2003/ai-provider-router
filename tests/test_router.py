from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_router import AIRouter
from ai_router.providers.base import ProviderError, ProviderResponse


class RouterTests(unittest.TestCase):
    def test_config_is_separate_and_summary_redacts_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = json.dumps([{"id": "first", "key": "SECRET_VALUE", "project": "p1"}])
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            summary = router.summary()
            self.assertEqual(summary["config"]["chains"]["default"][0]["model"], "gemini-2.5-flash")
            self.assertNotIn("SECRET_VALUE", json.dumps(summary))
            router.close()

    def test_single_hf_token_is_loaded_as_fallback_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ.pop("AI_ROUTER_HF_KEYS_JSON", None)
            os.environ["HF_TOKEN"] = "hf_single_test_token"
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            keys = router.config.keys_for("huggingface")
            self.assertEqual(len(keys), 1)
            self.assertEqual(keys[0].secret, "hf_single_test_token")
            router.close()
            os.environ.pop("HF_TOKEN", None)

    def test_key_pool_accepts_wrapper_and_api_key_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = json.dumps({"keys": [
                {"id": "wrapped-1", "api_key": "one", "project": "p1"},
                {"id": "wrapped-2", "token": "two", "project": "p2"},
            ]})
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            keys = router.config.keys_for("google_gemini")
            self.assertEqual([key.key_id for key in keys], ["wrapped-1", "wrapped-2"])
            self.assertEqual([key.secret for key in keys], ["one", "two"])
            router.close()

    def test_rotation_moves_to_next_key_and_records_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = json.dumps([
                {"id": "first", "key": "one", "project": "p1"},
                {"id": "second", "key": "two", "project": "p2"},
            ])
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            calls: list[str] = []

            def fake(*, model, secret, system_prompt, user_prompt, timeout_seconds):
                calls.append(f"{model}:{secret}")
                if secret == "one":
                    raise ProviderError("quota", error_class="quota", status_code=429)
                return ProviderResponse({"ok": True}, {"totalTokenCount": 3})

            with patch.object(router.adapters["google_gemini"], "complete_json", side_effect=fake):
                result = router.complete_json(system_prompt="system", user_prompt="user", operation="test")
            self.assertEqual(result, {"ok": True})
            self.assertEqual(calls[:2], ["gemini-2.5-flash:one", "gemini-2.5-flash:two"])
            self.assertEqual(router.store.stats()["calls"], 2)
            router.close()


    def test_video_rotation_uses_same_key_pool_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = json.dumps([
                {"id": "video-first", "key": "one", "project": "p1"},
                {"id": "video-second", "key": "two", "project": "p2"},
            ])
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            calls: list[str] = []

            def fake_video(*, model, secret, video_uri, system_prompt, user_prompt, timeout_seconds):
                calls.append(f"{model}:{secret}:{video_uri}")
                if secret == "one":
                    raise ProviderError("quota", error_class="quota", status_code=429)
                return ProviderResponse({"summary": "ok"}, {"totalTokenCount": 7})

            with patch.object(router.adapters["google_gemini"], "complete_video_json", side_effect=fake_video):
                result = router.complete_video_json(
                    video_uri="https://www.youtube.com/watch?v=example",
                    system_prompt="system",
                    user_prompt="user",
                    operation="video-test",
                )
            self.assertEqual(result, {"summary": "ok"})
            self.assertEqual(calls[:2], [
                "gemini-2.5-flash:one:https://www.youtube.com/watch?v=example",
                "gemini-2.5-flash:two:https://www.youtube.com/watch?v=example",
            ])
            self.assertEqual(router.store.stats()["calls"], 2)
            router.close()
            os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)


if __name__ == "__main__":
    unittest.main()
