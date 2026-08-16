from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_router import AIRouter
from ai_router.router import AllProvidersFailed, UnsupportedOutputType

SCENARIOS = {
    "text": {"user_prompt": "Return JSON with exactly one field ok set to true.", "output_type": "text"},
    "normal_search": {"user_prompt": "Find the latest public English YouTube videos relevant to: vibe coding AI-assisted development software engineering. Return up to three exact YouTube URLs, titles, and a brief reason for each. Do not use any external tools; if you cannot verify a URL, say so explicitly.", "output_type": "text"},
    "openrouter": {"user_prompt": "Return JSON with exactly one field ok set to true.", "output_type": "text", "chain": "openrouter_free"},
    "search": {"user_prompt": "What is the current UTC date? Use Google Search grounding and cite sources.", "output_type": "text", "grounding": "search"},
    "maps": {"user_prompt": "Name one well-known landmark near these coordinates and explain briefly.", "output_type": "text", "grounding": "maps", "latitude": 24.7136, "longitude": 46.6753},
    "image": {"user_prompt": "Create a simple blue circle on a white background.", "output_type": "image"},
    "audio": {"user_prompt": "Say exactly: Gemini router smoke test.", "output_type": "audio"},
    "embedding": {"user_prompt": "router smoke test embedding", "output_type": "embedding"},
}


def summarize(name: str, result: dict[str, Any]) -> dict[str, Any]:
    output_type = result.get("output_type", result.get("intent", name))
    summary: dict[str, Any] = {"scenario": name, "status": "passed", "output_type": output_type, "route": result.get("route")}
    if output_type == "image":
        data = result.get("data_base64", "")
        summary.update({"mime_type": result.get("mime_type"), "bytes_base64": len(data)})
    elif output_type == "audio":
        data = result.get("data_base64", "")
        summary.update({"mime_type": result.get("mime_type"), "bytes_base64": len(data), "sample_rate_hz": result.get("sample_rate_hz")})
    elif output_type == "embedding":
        embeddings = result.get("embeddings") or []
        first = embeddings[0] if embeddings else {}
        values = first.get("values") if isinstance(first, dict) else first
        summary.update({"embedding_count": len(embeddings), "dimensions": len(values or [])})
    elif output_type == "text":
        text = result.get("text", result.get("response", ""))
        summary.update(
            {
                "text_chars": len(str(text)) if text else 0,
                "json_fields": sorted(key for key in result if key not in {"route", "intent", "text", "response", "annotations"}) if not text else [],
                "annotations": len(result.get("annotations", [])),
            }
        )
    return summary


def run_route_plans(router: AIRouter) -> list[dict[str, Any]]:
    results = []
    for output_type, prompt in (("live", "Start a real-time voice conversation"), ("video_generation", "Generate an eight-second cinematic video"), ("video_analysis", "Analyze a public video")):
        try:
            plan = router.route_plan(user_prompt=prompt, output_type=output_type)
            results.append({"scenario": output_type, "status": "route_plan_only", "route": plan["route"], "first_model": plan["models"][0]["model"] if plan["models"] else None})
        except Exception as exc:  # noqa: BLE001
            results.append({"scenario": output_type, "status": "failed", "error_type": type(exc).__name__})
    return results


def main() -> int:
    selected = os.getenv("SMOKE_SCENARIO", "all")
    state_db = Path(os.getenv("SMOKE_STATE_DB", "/tmp/ai-router-live-smoke.db"))
    router = AIRouter(config_dir=ROOT / "config", state_db=state_db)
    results: list[dict[str, Any]] = []
    try:
        if selected in {"all", "routing"}:
            results.extend(run_route_plans(router))
        scenario_names = list(SCENARIOS) if selected == "all" else ([selected] if selected in SCENARIOS else [])
        for name in scenario_names:
            spec = SCENARIOS[name]
            try:
                result = router.complete_auto(**spec, operation=f"live_smoke_{name}")
                results.append(summarize(name, result))
            except (AllProvidersFailed, UnsupportedOutputType, ValueError) as exc:
                results.append({"scenario": name, "status": "failed", "error_type": type(exc).__name__, "message": str(exc)[:240]})
        passed = sum(item["status"] in {"passed", "route_plan_only"} for item in results)
        config_summary = router.summary().get("config", {})
        payload = {
            "status": "completed",
            "scenario_filter": selected,
            "loaded_key_counts": config_summary.get("secrets_loaded", {}),
            "passed_or_planned": passed,
            "total": len(results),
            "results": results,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if all(item["status"] in {"passed", "route_plan_only"} for item in results) else 1
    finally:
        router.close()


if __name__ == "__main__":
    raise SystemExit(main())
