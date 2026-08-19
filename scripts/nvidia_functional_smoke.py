from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time

import requests
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_router.config import RouterConfig  # noqa: E402
from ai_router.providers.base import ProviderError  # noqa: E402
from ai_router.providers.openai_compatible import OpenAICompatibleAdapter  # noqa: E402

FACTUAL_PROMPT = (
    "أجب عن السؤال التالي ككائن JSON فقط بالمفاتيح answer وconfidence وkey_fact. "
    "السؤال: ما عاصمة اليابان؟ لا تضف Markdown أو نصًا خارج JSON."
)
REASONING_PROMPT = (
    "حل المسألة التالية ثم أجب ككائن JSON فقط بالمفاتيح answer وreasoning_summary وkey_fact. "
    "لدى سارة 3 صناديق، في كل صندوق 4 كرات، ثم أضافت كرتين إلى كل صندوق. كم كرة أصبحت لديها؟ "
    "لا تضف Markdown أو نصًا خارج JSON."
)
TRANSLATION_MODEL = "nvidia/riva-translate-4b-instruct-v2"
TRANSLATION_PROMPT = "Translate to Arabic and return only the translation: The capital of France is Paris."


def run_translation_model(base_url: str, model: str, secret: str) -> dict[str, Any]:
    started = time.monotonic()
    result: dict[str, Any] = {"model": model, "functional_category": "specialized_translation", "status": "passed"}
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": TRANSLATION_PROMPT}],
                "stream": False,
            },
            timeout=120,
        )
        if response.status_code >= 400:
            result.update({"status": "failed", "error_class": "http", "status_code": response.status_code})
        else:
            body = response.json()
            text = str(body.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
            result["translation"] = {"status": "passed" if text else "invalid", "text_chars": len(text), "contains_paris": "باريس" in text}
            if not text:
                result["status"] = "failed"
    except requests.RequestException:
        result.update({"status": "failed", "error_class": "transient"})
    except (ValueError, KeyError, IndexError, TypeError):
        result.update({"status": "failed", "error_class": "invalid_or_unknown"})
    result["duration_seconds"] = round(time.monotonic() - started, 2)
    return result


def run_model(adapter: OpenAICompatibleAdapter, model: str, secret: str, base_url: str) -> dict[str, Any]:
    if model == TRANSLATION_MODEL:
        return run_translation_model(base_url, model, secret)
    started = time.monotonic()
    result: dict[str, Any] = {
        "model": model,
        "status": "passed",
        "factual": {},
        "reasoning": {},
    }
    for label, prompt in (("factual", FACTUAL_PROMPT), ("reasoning", REASONING_PROMPT)):
        try:
            response = adapter.complete_json(
                model=model,
                secret=secret,
                system_prompt="Return exactly one JSON object. Do not include secrets or Markdown.",
                user_prompt=prompt,
                timeout_seconds=120,
                supports_response_format=False,
            )
            payload = response.payload
            answer = payload.get("answer")
            result[label] = {
                "status": "passed" if answer not in (None, "") else "invalid",
                "keys": sorted(str(key) for key in payload.keys()),
                "answer_present": answer not in (None, ""),
                "answer_excerpt": str(answer)[:240] if answer not in (None, "") else "",
            }
            if result[label]["status"] != "passed":
                result["status"] = "failed"
        except ProviderError as exc:
            result[label] = {
                "status": "failed",
                "error_class": exc.error_class,
                "status_code": exc.status_code,
            }
            result["status"] = "failed"
        except Exception as exc:  # noqa: BLE001
            result[label] = {"status": "failed", "error_type": type(exc).__name__}
            result["status"] = "failed"
    result["duration_seconds"] = round(time.monotonic() - started, 2)
    return result


def main() -> int:
    config = RouterConfig.load(ROOT / "config")
    keys = config.keys_for("nvidia")
    if not keys:
        print(json.dumps({"status": "blocked", "reason": "NVIDIA key is not configured"}))
        return 2
    all_models = [spec.model for spec in config.model_chain("nvidia_free")]
    requested = [item.strip() for item in os.getenv("NVIDIA_FUNCTIONAL_MODELS", "").split(",") if item.strip()]
    unknown = sorted(set(requested) - set(all_models))
    if unknown:
        print(json.dumps({"status": "blocked", "reason": "Unknown NVIDIA model selection", "unknown_models": unknown}))
        return 2
    models = [model for model in all_models if not requested or model in requested]
    adapter = OpenAICompatibleAdapter("nvidia", config.providers["nvidia"].base_url)
    max_workers = max(1, min(int(os.getenv("NVIDIA_FUNCTIONAL_WORKERS", "3")), 3))
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run_model, adapter, model, keys[0].secret, config.providers["nvidia"].base_url) for model in models]
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda item: models.index(item["model"]))
    passed = sum(item["status"] == "passed" for item in results)
    general_text_passed = sum(item["status"] == "passed" and item.get("functional_category", "general_text") == "general_text" for item in results)
    specialized_passed = sum(item["status"] == "passed" and item.get("functional_category") == "specialized_translation" for item in results)
    payload = {
        "status": "completed",
        "test_type": "functional_text",
        "models_tested": len(results),
        "model_filter": requested or "all_active_nvidia_free",
        "models_passed": passed,
        "general_text_models_passed_both_prompts": general_text_passed,
        "specialized_models_passed": specialized_passed,
        "prompts": ["factual_knowledge_arabic", "arithmetic_reasoning_arabic"],
        "search_test": {"status": "not_supported_by_nvidia_adapter", "reason": "No search tool is sent to the NVIDIA OpenAI-compatible endpoint."},
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
