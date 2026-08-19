from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_router import AIRouter  # noqa: E402
from ai_router.providers.base import ProviderError  # noqa: E402

SPACE_IDS = ["chatgpt_space_replica_01", "chatgpt_space_replica_02", "chatgpt_space"]
TEXT_PROMPT = "Answer in one short sentence: What is the capital of Japan?"
SEARCH_PROMPT = "What is the current UTC date? Use live web search and cite at least one source."
IMAGE_PROMPT = "Create a simple blue circle on a white background."


def summarize_success(kind: str, result: dict[str, Any]) -> dict[str, Any]:
    if kind == "image":
        data = str(result.get("data_base64", ""))
        return {
            "status": "passed" if data else "invalid",
            "output_type": result.get("output_type"),
            "mime_type": result.get("mime_type"),
            "image_base64_chars": len(data),
            "text_chars": len(str(result.get("text", ""))),
        }
    return {
        "status": "passed" if str(result.get("text", "")).strip() else "invalid",
        "output_type": result.get("output_type"),
        "text_chars": len(str(result.get("text", ""))),
        "annotations": len(result.get("annotations", [])),
        "images_in_response": len(result.get("images", [])),
    }


def run_one(adapter: Any, provider_id: str, secret: str, timeout: int, kind: str) -> dict[str, Any]:
    started = time.monotonic()
    base = {"provider": provider_id, "scenario": kind}
    try:
        if kind == "text":
            response = adapter.complete_interaction_text(
                model="gpt-4o-mini",
                secret=secret,
                system_prompt="Answer briefly. Do not reveal secrets.",
                user_prompt=TEXT_PROMPT,
                timeout_seconds=timeout,
                tools=[],
            )
        elif kind == "search":
            response = adapter.complete_interaction_text(
                model="gpt-4o-mini",
                secret=secret,
                system_prompt="Answer briefly and cite the live source if available.",
                user_prompt=SEARCH_PROMPT,
                timeout_seconds=timeout,
                tools=[{"type": "google_search"}],
            )
        else:
            response = adapter.generate_image(
                model="gpt-4o-mini",
                secret=secret,
                prompt=IMAGE_PROMPT,
                timeout_seconds=timeout,
            )
        base.update(summarize_success(kind, response.payload))
    except ProviderError as exc:
        base.update({"status": "failed", "error_class": exc.error_class, "status_code": exc.status_code})
    except Exception as exc:  # noqa: BLE001
        base.update({"status": "failed", "error_type": type(exc).__name__})
    base["duration_seconds"] = round(time.monotonic() - started, 2)
    return base


def main() -> int:
    router = AIRouter(config_dir=ROOT / "config", state_db=Path(os.getenv("CHATGPT_SPACES_STATE_DB", "/tmp/chatgpt-spaces-functional.db")))
    try:
        keys = router.config.keys_for("chatgpt_space_replica_01")
        image_enabled = os.getenv("CHATGPT_SPACES_TEST_IMAGES", "true").lower() in {"1", "true", "yes"}
        results: list[dict[str, Any]] = []
        if not keys:
            for provider_id in SPACE_IDS:
                for scenario in ("text", "search", "image") if image_enabled else ("text", "search"):
                    results.append({"provider": provider_id, "scenario": scenario, "status": "no_key"})
        else:
            secret = keys[0].secret
            for provider_id in SPACE_IDS:
                adapter = router.adapters[provider_id]
                provider_timeout = router.config.providers[provider_id].timeout_seconds
                for scenario in ("text", "search", "image") if image_enabled else ("text", "search"):
                    # Sequential execution avoids concurrent browser/session load and accidental quota bursts.
                    results.append(run_one(adapter, provider_id, secret, provider_timeout, scenario))
        counts: dict[str, int] = {}
        for item in results:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        payload = {
            "status": "completed",
            "spaces": SPACE_IDS,
            "image_tested": image_enabled,
            "execution_policy": "sequential_per_space_and_scenario",
            "counts": counts,
            "results": results,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        router.close()


if __name__ == "__main__":
    raise SystemExit(main())
