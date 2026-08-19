from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_router.config import ModelSpec, RouterConfig  # noqa: E402
from ai_router.providers.base import ProviderError  # noqa: E402
from ai_router.providers.openai_compatible import OpenAICompatibleAdapter  # noqa: E402
from ai_router.router import AIRouter  # noqa: E402

JSON_PROMPT = (
    "Return one JSON object only with the key answer. "
    "Answer this real question in one short sentence: What is the capital of Japan?"
)
TEXT_PROMPT = "Answer this real question in one short sentence: What is the capital of Japan?"
TRANSLATION_PROMPT = "Translate to Arabic and return only the translation: The capital of France is Paris."


def collect_specs(config: RouterConfig) -> list[dict[str, Any]]:
    records: dict[tuple[str, str, str], dict[str, Any]] = {}
    for group_name, group in (("model_chains", config.chains), ("output_routes", config.output_routes)):
        for route_name, specs in group.items():
            for spec in specs:
                method = spec.method if spec.method not in {"", "None"} else "json"
                key = (spec.provider_id, spec.model, method)
                record = records.setdefault(
                    key,
                    {
                        "provider": spec.provider_id,
                        "model": spec.model,
                        "method": method,
                        "input_types": list(spec.input_types),
                        "output_types": list(spec.output_types),
                        "routes": [],
                        "enabled": spec.enabled and config.providers[spec.provider_id].enabled,
                        "supports_response_format": spec.supports_response_format,
                    },
                )
                route_id = f"{group_name}.{route_name}"
                if route_id not in record["routes"]:
                    record["routes"].append(route_id)
    return sorted(records.values(), key=lambda item: (item["provider"], item["method"], item["model"]))


def route_only(record: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **{key: record[key] for key in ("provider", "model", "method", "output_types", "routes")},
        "category": "route_contract_only",
        "status": "route_only",
        "reason": reason,
    }


def run_live_record(record: dict[str, Any], config: RouterConfig, adapters: dict[str, Any], secret: str) -> dict[str, Any]:
    started = time.monotonic()
    provider = record["provider"]
    model = record["model"]
    method = record["method"]
    adapter = adapters[provider]
    timeout = config.providers[provider].timeout_seconds
    base = {key: record[key] for key in ("provider", "model", "method", "output_types", "routes")}
    try:
        if method == "translation":
            response = adapter.complete_text(
                model=model,
                secret=secret,
                system_prompt="Translate only. Do not add explanations.",
                user_prompt=TRANSLATION_PROMPT,
                timeout_seconds=timeout,
            )
            text = str(response.payload.get("translation", "")).strip()
            base.update({"category": "translation", "status": "passed" if text else "invalid", "response_chars": len(text)})
        elif method == "embedding":
            response = adapter.embed_content(
                model=model,
                secret=secret,
                text="router capability audit",
                timeout_seconds=timeout,
                output_dimensionality=None,
                content_parts=None,
            )
            values = ((response.payload.get("embeddings") or [{}])[0]).get("values", [])
            base.update({"category": "embedding", "status": "passed" if values else "invalid", "dimensions": len(values)})
        elif method == "interaction_text":
            response = adapter.complete_interaction_text(
                model=model,
                secret=secret,
                system_prompt="Answer briefly and do not reveal secrets.",
                user_prompt=TEXT_PROMPT,
                timeout_seconds=timeout,
                tools=[],
            )
            text = str(response.payload.get("text", "")).strip()
            base.update({"category": "text_interaction", "status": "passed" if text else "invalid", "response_chars": len(text)})
        else:
            response = adapter.complete_json(
                model=model,
                secret=secret,
                system_prompt="Return exactly one JSON object.",
                user_prompt=JSON_PROMPT,
                timeout_seconds=timeout,
                supports_response_format=record["supports_response_format"],
            )
            answer = response.payload.get("answer")
            base.update({"category": "text_json", "status": "passed" if answer not in (None, "") else "invalid", "json_keys": sorted(response.payload)})
        base["duration_seconds"] = round(time.monotonic() - started, 2)
        return base
    except ProviderError as exc:
        base.update({"category": method, "status": "failed", "error_class": exc.error_class, "status_code": exc.status_code})
    except Exception as exc:  # noqa: BLE001
        base.update({"category": method, "status": "failed", "error_type": type(exc).__name__})
    base["duration_seconds"] = round(time.monotonic() - started, 2)
    return base


def main() -> int:
    config = RouterConfig.load(ROOT / "config")
    router = AIRouter(config_dir=ROOT / "config", state_db=Path(os.getenv("CAPABILITY_AUDIT_STATE_DB", "/tmp/capability-audit.db")))
    try:
        records = collect_specs(config)
        results: list[dict[str, Any]] = []
        live_methods = {"json", "interaction_text", "translation", "embedding"}
        for record in records:
            if not record["enabled"]:
                results.append(route_only(record, "disabled_in_config"))
                continue
            if record["method"] not in live_methods:
                results.append(route_only(record, "method_requires_specialized_input_or_transport; no live side-effect call made"))
                continue
            keys = config.keys_for(record["provider"])
            if not keys:
                results.append({**{key: record[key] for key in ("provider", "model", "method", "output_types", "routes")}, "category": record["method"], "status": "no_key"})
                continue
            results.append({"__record": record, "__secret": keys[0].secret})
        pending = [item for item in results if "__record" in item]
        static = [item for item in results if "__record" not in item]
        max_workers = max(1, min(int(os.getenv("CAPABILITY_AUDIT_WORKERS", "3")), 3))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(run_live_record, item["__record"], config, router.adapters, item["__secret"]) for item in pending]
            live_results = [future.result() for future in futures]
        final_results = sorted(static + live_results, key=lambda item: (item["provider"], item["method"], item["model"]))
        counts = defaultdict(int)
        for item in final_results:
            counts[item["status"]] += 1
        payload = {
            "status": "completed",
            "test_type": "all_unique_configured_provider_model_methods",
            "unique_records": len(final_results),
            "live_attempts": len(live_results),
            "counts": dict(sorted(counts.items())),
            "policy": {
                "live": "json/text/translation/embedding only",
                "route_only": "image/audio/video/live/specialized transports are contract-inventoried without quota-consuming calls",
                "search": "search capability is tested through existing grounded route, not as a model capability without a search tool",
            },
            "results": final_results,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        router.close()


if __name__ == "__main__":
    raise SystemExit(main())
