from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_router import AIRouter, AllProvidersFailed
from ai_router.config import ModelSpec
from ai_router.providers.base import ProviderError, ProviderResponse


class RouterTests(unittest.TestCase):
    def test_all_provider_failures_keep_initial_errors_visible(self) -> None:
        errors = [f"openrouter/{index}: auth/401" for index in range(12)] + [f"google_gemini/{index}: transient/500" for index in range(12)]
        visible_errors = errors if len(errors) <= 24 else [*errors[:6], f"... {len(errors) - 18} intermediate attempts omitted ...", *errors[-12:]]
        rendered = " | ".join(visible_errors)
        self.assertIn("openrouter/0", rendered)
        self.assertIn("google_gemini/11", rendered)

    def test_config_is_separate_and_summary_redacts_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = json.dumps([{"id": "first", "key": "SECRET_VALUE", "project": "p1"}])
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            summary = router.summary()
            self.assertEqual(summary["config"]["chains"]["default"][0]["model"], "gemini-3.7-flash")
            self.assertNotIn("SECRET_VALUE", json.dumps(summary))
            router.close()

    def test_gemini_models_are_ordered_descending(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            models = [item.model for item in router.config.model_chain("default") if item.provider_id == "google_gemini"]
            self.assertEqual(models, [
                "gemini-3.7-flash",
                "gemini-3.6-flash",
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.1-flash-lite",
                "gemini-3-flash",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
            ])
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

    def test_grounded_search_without_citations_is_not_provider_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_OPENROUTER_KEYS_JSON"] = json.dumps([{"id": "openrouter-test", "key": "openrouter-secret", "project": "p1"}])
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = json.dumps([{"id": "gemini-test", "key": "gemini-secret", "project": "p2"}])
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            empty = ProviderResponse({"output_type": "text", "text": "I searched but found no qualifying citations.", "url_citations": []}, {})
            calls = []
            def fake(*, model, secret, system_prompt, user_prompt, timeout_seconds, tools=None):
                calls.append((model, secret))
                return empty
            with patch.object(router.adapters["google_gemini"], "complete_interaction_text", side_effect=fake):
                with self.assertRaisesRegex(AllProvidersFailed, "no URL citations"):
                    router.complete_auto(user_prompt="Search for cited sources.", output_type="text", grounding="search", operation="grounded-test")
            self.assertGreaterEqual(len(calls), 1)
            self.assertFalse(router.store.is_cooling("google_gemini", "gemini-2.5-flash", "openrouter-test", "p1"))
            router.close()
            os.environ.pop("AI_ROUTER_OPENROUTER_KEYS_JSON", None)

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
            self.assertEqual(calls[:2], ["gemini-3.7-flash:one", "gemini-3.7-flash:two"])
            self.assertEqual(router.store.stats()["calls"], 2)
            router.close()


    def test_each_key_resumes_its_own_model_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = json.dumps([
                {"id": "first", "key": "one", "project": "p1"},
                {"id": "second", "key": "two", "project": "p2"},
            ])
            try:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                router.config.chains["cursor_test"] = [
                    ModelSpec("google_gemini", "gemini-3.7-flash", True),
                    ModelSpec("google_gemini", "gemini-3.6-flash", True),
                ]
                calls: list[str] = []

                def fake(*, model, secret, system_prompt, user_prompt, timeout_seconds):
                    calls.append(f"{model}:{secret}")
                    if model == "gemini-3.7-flash":
                        raise ProviderError("quota", error_class="quota", status_code=429, retryable=False)
                    if secret == "one":
                        raise ProviderError("quota", error_class="quota", status_code=429, retryable=False)
                    return ProviderResponse({"ok": secret}, {})

                with patch.object(router.adapters["google_gemini"], "complete_json", side_effect=fake):
                    result = router.complete_json(chain="cursor_test", system_prompt="system", user_prompt="first", operation="cursor-1")
                    self.assertEqual(result, {"ok": "two"})
                    result = router.complete_json(chain="cursor_test", system_prompt="system", user_prompt="second", operation="cursor-2")
                self.assertEqual(result, {"ok": "two"})
                self.assertEqual(calls, [
                    "gemini-3.7-flash:one",
                    "gemini-3.7-flash:two",
                    "gemini-3.6-flash:one",
                    "gemini-3.6-flash:two",
                    "gemini-3.6-flash:two",
                ])
                self.assertEqual(router.store.get_model_cursor(
                    provider="google_gemini", chain="cursor_test", key_id="first", project="p1",
                    model_names=["gemini-3.7-flash", "gemini-3.6-flash"],
                ), 0)
                router.close()
            finally:
                os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)

    def test_model_cursor_survives_router_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = json.dumps([
                {"id": "restart-first", "key": "one", "project": "p1"},
                {"id": "restart-second", "key": "two", "project": "p2"},
            ])
            try:
                state_db = Path(temp) / "router.db"
                first_router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=state_db)
                first_router.config.chains["restart_test"] = [
                    ModelSpec("google_gemini", "gemini-3.7-flash", True),
                    ModelSpec("google_gemini", "gemini-3.6-flash", True),
                ]
                first_calls: list[str] = []

                def first_fake(*, model, secret, system_prompt, user_prompt, timeout_seconds):
                    first_calls.append(f"{model}:{secret}")
                    if model == "gemini-3.7-flash":
                        raise ProviderError("quota", error_class="quota", retryable=False)
                    return ProviderResponse({"ok": secret}, {})

                with patch.object(first_router.adapters["google_gemini"], "complete_json", side_effect=first_fake):
                    self.assertEqual(first_router.complete_json(chain="restart_test", system_prompt="s", user_prompt="u"), {"ok": "one"})
                first_router.close()

                second_router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=state_db)
                second_router.config.chains["restart_test"] = [
                    ModelSpec("google_gemini", "gemini-3.7-flash", True),
                    ModelSpec("google_gemini", "gemini-3.6-flash", True),
                ]
                second_calls: list[str] = []

                def second_fake(*, model, secret, system_prompt, user_prompt, timeout_seconds):
                    second_calls.append(f"{model}:{secret}")
                    return ProviderResponse({"ok": secret}, {})

                with patch.object(second_router.adapters["google_gemini"], "complete_json", side_effect=second_fake):
                    self.assertEqual(second_router.complete_json(chain="restart_test", system_prompt="s", user_prompt="u"), {"ok": "one"})
                self.assertEqual(second_calls, ["gemini-3.6-flash:one"])
                second_router.close()
            finally:
                os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)

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
                "gemini-3.7-flash:one:https://www.youtube.com/watch?v=example",
                "gemini-3.7-flash:two:https://www.youtube.com/watch?v=example",
            ])
            self.assertEqual(router.store.stats()["calls"], 2)
            router.close()
            os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)


    def test_project_rotation_round_robin_and_project_scoped_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            os.environ["AI_ROUTER_GEMINI_KEYS_JSON"] = json.dumps([
                {"id": "same-key-id", "key": "project-one-secret", "project": "project-one"},
                {"id": "same-key-id", "key": "project-two-secret", "project": "project-two"},
            ])
            try:
                router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
                router.config.key_pool_rotations["gemini_default"] = "round_robin"
                calls: list[str] = []

                def fake(*, model, secret, system_prompt, user_prompt, timeout_seconds):
                    calls.append(secret)
                    return ProviderResponse({"ok": secret}, {})

                with patch.object(router.adapters["google_gemini"], "complete_json", side_effect=fake):
                    router.complete_json(system_prompt="system", user_prompt="first", operation="test")
                    router.complete_json(system_prompt="system", user_prompt="second", operation="test")
                self.assertEqual(calls, ["project-one-secret", "project-two-secret"])
                self.assertIsNotNone(router.store.get_state("google_gemini", "gemini-3.7-flash", "same-key-id", "project-one")
)
                self.assertIsNotNone(router.store.get_state("google_gemini", "gemini-3.7-flash", "same-key-id", "project-two")
)
                self.assertEqual(router.store.stats()["projects"], 2)
                router.close()
            finally:
                os.environ.pop("AI_ROUTER_GEMINI_KEYS_JSON", None)


class ProviderFilterTests(unittest.TestCase):
    def test_no_provider_filter_keeps_all_configured_provider_families(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            plan = router.route_plan(user_prompt="write a short answer")
            providers = {item["provider"] for item in plan["models"]}
            self.assertTrue({
                "google_gemini",
                "huggingface",
                "openrouter",
                "nvidia",
            }.issubset(providers))
            router.close()

    def test_provider_alias_allowlist_selects_only_requested_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            for alias, provider_id in (("gemini", "google_gemini"), ("hf", "huggingface"), ("openrouter", "openrouter"), ("nvidia", "nvidia"), ("groq", "groq")):
                plan = router.route_plan(user_prompt="write a short answer", providers=alias)
                self.assertTrue(plan["models"])
                self.assertEqual({item["provider"] for item in plan["models"]}, {provider_id})
            router.close()

    def test_provider_denylist_excludes_gemini_but_keeps_other_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            plan = router.route_plan(user_prompt="write a short answer", exclude_providers="gemini")
            providers = {item["provider"] for item in plan["models"]}
            self.assertNotIn("google_gemini", providers)
            self.assertTrue(providers)
            router.close()

    def test_provider_filter_rejects_conflict_and_unknown_selector(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            with self.assertRaisesRegex(ValueError, "both allowed and excluded"):
                router.route_plan(user_prompt="write a short answer", providers="nvidia", exclude_providers="nvidia")
            with self.assertRaisesRegex(ValueError, "Unknown provider selector"):
                router.route_plan(user_prompt="write a short answer", providers="does-not-exist")
            router.close()

    def test_provider_filter_fails_when_no_models_remain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            router = AIRouter(config_dir=Path(__file__).parents[1] / "config", state_db=Path(temp) / "router.db")
            with self.assertRaisesRegex(Exception, "No configured models remain"):
                router.route_plan(user_prompt="generate audio", output_type="audio", providers="nvidia")
            router.close()


if __name__ == "__main__":
    unittest.main()
