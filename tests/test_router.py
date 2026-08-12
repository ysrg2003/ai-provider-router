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


if __name__ == "__main__":
    unittest.main()
