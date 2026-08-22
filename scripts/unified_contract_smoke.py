"""Bounded live checks for the public AIRouter response contract.

One text call is made per enabled provider, plus one Gemini grounded-search call.
Output contains only response shape and routing metadata, never response text or
credential values.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_router.response_contract import ResponseContractError, validate_response_envelope  # noqa: E402
from ai_router.router import AIRouter  # noqa: E402


TEXT_PROMPT = "Return a JSON object with exactly one field named ok set to true."
SEARCH_PROMPT = "What is the current UTC date? Use Google Search grounding and cite sources."
TRANSLATION_PROMPT = "Translate to Arabic and return only the translation: The capital of France is Paris."


def _provider_ids(router: AIRouter) -> list[str]:
    configured = [provider_id for provider_id, spec in router.config.providers.items() if spec.enabled]
    selected = [item.strip() for item in os.getenv("UNIFIED_CONTRACT_PROVIDERS", ",".join(configured)).split(",") if item.strip()]
    return [provider_id for provider_id in selected if provider_id in router.config.providers]


def _shape(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_type": result.get("output_type"),
        "intent": result.get("intent"),
        "route": result.get("route"),
        "provider": result.get("provider"),
        "model": result.get("model"),
        "url_citations": len(result.get("url_citations", [])) if isinstance(result.get("url_citations"), list) else None,
        "payload_fields": sorted(result.keys()),
    }


def _run_one(provider: str, model: str, scenario: str) -> dict[str, Any]:
    started = time.monotonic()
    router = AIRouter(config_dir=ROOT / "config", state_db=Path(f"/tmp/unified-contract-{scenario}-{provider}-{model.replace('/', '_').replace(':', '_')}.db"))
    try:
        if not router.config.keys_for(provider):
            return {"scenario": scenario, "status": "deferred_no_key", "requested_provider": provider, "requested_model": model, "duration_seconds": round(time.monotonic() - started, 2)}
        route_name = "text" if scenario == "text" else "translation"
        specs = [spec for spec in router.config.output_routes.get(route_name, []) if spec.provider_id == provider and spec.model == model]
        if not specs:
            return {"scenario": scenario, "status": "deferred_not_in_route", "requested_provider": provider, "requested_model": model, "duration_seconds": round(time.monotonic() - started, 2)}
        router.config.output_routes[route_name] = specs
        result = router.complete_auto(
            user_prompt=TEXT_PROMPT if scenario == "text" else TRANSLATION_PROMPT,
            output_type="text" if scenario == "text" else "translation",
            providers=[provider],
            operation=f"unified_contract_{scenario}_{provider}_{model}",
        )
        validated = validate_response_envelope(result)
        return {"scenario": scenario, "status": "passed", "requested_provider": provider, "requested_model": model, "response": _shape(validated), "duration_seconds": round(time.monotonic() - started, 2)}
    except (Exception,) as exc:  # noqa: BLE001
        return {"scenario": scenario, "status": "failed", "requested_provider": provider, "requested_model": model, "error_type": type(exc).__name__, "error": str(exc)[:240], "duration_seconds": round(time.monotonic() - started, 2)}
    finally:
        router.close()


def _target_models(router: AIRouter, route_name: str) -> list[tuple[str, str]]:
    records = [(spec.provider_id, spec.model) for spec in router.config.output_routes.get(route_name, []) if spec.enabled]
    if os.getenv("UNIFIED_CONTRACT_ALL_MODELS", "true").lower() in {"1", "true", "yes"}:
        return list(dict.fromkeys(records))
    selected: dict[str, tuple[str, str]] = {}
    for provider, model in records:
        selected.setdefault(provider, (provider, model))
    return list(selected.values())


def _run_search() -> dict[str, Any]:
    started = time.monotonic()
    router = AIRouter(config_dir=ROOT / "config", state_db=Path("/tmp/unified-contract-search.db"))
    try:
        if not router.config.keys_for("google_gemini"):
            return {"scenario": "search", "status": "deferred_no_key", "duration_seconds": round(time.monotonic() - started, 2)}
        result = router.complete_auto(user_prompt=SEARCH_PROMPT, output_type="text", grounding="search", providers=["google_gemini"], operation="unified_contract_search")
        validated = validate_response_envelope(result)
        if not validated.get("url_citations"):
            raise ResponseContractError("search response has no URL citations")
        return {"scenario": "search", "status": "passed", "response": _shape(validated), "duration_seconds": round(time.monotonic() - started, 2)}
    except (Exception,) as exc:  # noqa: BLE001
        return {"scenario": "search", "status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:240], "duration_seconds": round(time.monotonic() - started, 2)}
    finally:
        router.close()


def main() -> int:
    router = AIRouter(config_dir=ROOT / "config", state_db=Path("/tmp/unified-contract-discovery.db"))
    providers = _provider_ids(router)
    text_targets = [(provider, model) for provider, model in _target_models(router, "text") if provider in providers]
    translation_targets = (
        [(provider, model) for provider, model in _target_models(router, "translation") if provider in providers]
        if os.getenv("UNIFIED_CONTRACT_INCLUDE_TRANSLATION", "true").lower() in {"1", "true", "yes"}
        else []
    )
    router.close()

    scenarios = [(provider, model, "text") for provider, model in text_targets]
    scenarios.extend((provider, model, "translation") for provider, model in translation_targets if provider in {"groq", "nvidia"})

    workers = max(1, min(int(os.getenv("UNIFIED_CONTRACT_WORKERS", "3")), 5))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(lambda item: _run_one(*item), scenarios))
    results.append(_run_search())
    passed = sum(item["status"] == "passed" for item in results)
    deferred = sum(item["status"].startswith("deferred") for item in results)
    failed = sum(item["status"] == "failed" for item in results)
    payload = {"status": "completed", "passed": passed, "deferred": deferred, "failed": failed, "total": len(results), "results": results, "response_text_stored": False, "secret_values_stored": False}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
