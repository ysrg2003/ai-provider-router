from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"


def fetch_models(base_url: str, api_key: str, timeout: int) -> list[dict]:
    response = requests.get(
        f"{base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=timeout,
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Groq returned non-JSON HTTP {response.status_code}") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"Groq models request failed with HTTP {response.status_code}: {json.dumps(body, ensure_ascii=False)[:500]}")
    models = body.get("data") if isinstance(body, dict) else None
    if not isinstance(models, list):
        raise RuntimeError("Groq models response has no data list")
    return [item for item in models if isinstance(item, dict) and item.get("id")]


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover active Groq hosted models without printing the API key")
    parser.add_argument("--base-url", default=os.getenv("GROQ_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--write", type=Path, help="Write a redacted catalog JSON to this path")
    args = parser.parse_args()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        print("GROQ_API_KEY is required", file=sys.stderr)
        return 2
    try:
        models = fetch_models(args.base_url, api_key, max(5, args.timeout))
    except (OSError, requests.RequestException, RuntimeError) as exc:
        print(f"groq_discovery_error={str(exc)[:500]}", file=sys.stderr)
        return 1
    catalog = {
        "provider": "groq",
        "base_url": args.base_url.rstrip("/"),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": [
            {
                "id": str(item["id"]),
                "owned_by": item.get("owned_by"),
                "created": item.get("created"),
                "context_window": item.get("context_window"),
                "max_completion_tokens": item.get("max_completion_tokens"),
            }
            for item in sorted(models, key=lambda value: str(value["id"]))
        ],
    }
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"provider": "groq", "base_url": catalog["base_url"], "count": len(catalog["models"]), "models": [item["id"] for item in catalog["models"]]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
