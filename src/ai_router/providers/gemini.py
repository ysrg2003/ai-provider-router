from __future__ import annotations

import json
from typing import Any

import requests

from .base import ProviderError, ProviderResponse


class GeminiAdapter:
    provider_id = "google_gemini"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def complete_json(self, *, model: str, secret: str, system_prompt: str, user_prompt: str, timeout_seconds: int) -> ProviderResponse:
        endpoint = f"{self.base_url}/models/{model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        try:
            response = requests.post(endpoint, params={"key": secret}, json=payload, timeout=timeout_seconds)
        except requests.RequestException as exc:
            raise ProviderError(str(exc), error_class="transient") from exc
        body = self._body(response)
        if response.status_code >= 400:
            raise self._http_error(response.status_code, body)
        try:
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(self._strip_fences(text))
            if not isinstance(parsed, dict):
                raise ValueError("response is not an object")
            return ProviderResponse(parsed, body.get("usageMetadata", {}))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(f"Gemini returned invalid JSON: {body}", error_class="invalid_or_unknown", retryable=False) from exc

    @staticmethod
    def _body(response: requests.Response) -> dict[str, Any]:
        try:
            value = response.json()
            return value if isinstance(value, dict) else {"data": value}
        except ValueError:
            return {"raw": response.text[:2000]}

    @staticmethod
    def _strip_fences(text: str) -> str:
        clean = str(text or "").strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1]
        if clean.endswith("```"):
            clean = clean[:-3]
        return clean.strip()

    @staticmethod
    def _http_error(status_code: int, body: dict[str, Any]) -> ProviderError:
        message = json.dumps(body, ensure_ascii=False)[:1000]
        if status_code in {401, 403}:
            return ProviderError(message, error_class="auth", status_code=status_code, retryable=False)
        if status_code == 429:
            return ProviderError(message, error_class="quota", status_code=status_code)
        if status_code in {408, 409, 425, 500, 502, 503, 504}:
            return ProviderError(message, error_class="transient", status_code=status_code)
        return ProviderError(message, error_class="invalid_or_unknown", status_code=status_code, retryable=False)
