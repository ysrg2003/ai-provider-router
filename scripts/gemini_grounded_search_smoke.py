"""Live GenerateContent + Google Search check for each configured Gemini search model."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_router.router import AIRouter  # noqa: E402

PROMPT = "What is the current UTC date? Use Google Search grounding and cite the sources."


def shape(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_type": result.get("output_type"),
        "intent": result.get("intent"),
        "route": result.get("route"),
        "provider": result.get("provider"),
        "model": result.get("model"),
        "url_citations": len(result.get("url_citations", [])) if isinstance(result.get("url_citations"), list) else None,
        "payload_fields": sorted(result),
    }


def main() -> int:
    discovery_router = AIRouter(config_dir=ROOT / "config", state_db=Path("/tmp/gemini-grounded-discovery.db"))
    models = [spec.model for spec in discovery_router.config.output_routes.get("text_grounded_search", []) if spec.enabled and spec.provider_id == "google_gemini"]
    discovery_router.close()

    results = []
    for model in models:
        router = AIRouter(config_dir=ROOT / "config", state_db=Path(f"/tmp/gemini-grounded-{model.replace('/', '_')}.db"))
        started = time.monotonic()
        try:
            candidates = [spec for spec in router.config.output_routes["text_grounded_search"] if spec.provider_id == "google_gemini" and spec.model == model]
            router.config.output_routes["text_grounded_search"] = candidates
            result = router.complete_auto(
                user_prompt=PROMPT,
                output_type="text",
                grounding="search",
                providers=["google_gemini"],
                operation=f"gemini_grounded_search_{model}",
            )
            results.append({"model": model, "status": "passed", "response": shape(result), "duration_seconds": round(time.monotonic() - started, 2)})
        except Exception as exc:  # noqa: BLE001
            results.append({"model": model, "status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:240], "duration_seconds": round(time.monotonic() - started, 2)})
        finally:
            router.close()

    passed = sum(item["status"] == "passed" for item in results)
    failed = len(results) - passed
    payload = {"status": "completed", "route": "text_grounded_search", "method": "grounded_text", "tool": "google_search", "model_order": models, "passed": passed, "failed": failed, "total": len(results), "results": results, "response_text_stored": False, "secret_values_stored": False}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
