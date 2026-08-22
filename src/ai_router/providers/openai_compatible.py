from __future__ import annotations

import json
from typing import Any

import requests

from .base import ProviderError, ProviderResponse


class OpenAICompatibleAdapter:
    def __init__(self, provider_id: str, base_url: str) -> None:
        self.provider_id = provider_id
        self.base_url = base_url.rstrip("/")

    def complete_json(self, *, model: str, secret: str, system_prompt: str, user_prompt: str, timeout_seconds: int, supports_response_format: bool = True) -> ProviderResponse:
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        if supports_response_format:
            payload["response_format"] = {"type": "json_object"}
        if self.provider_id == "groq":
            payload["max_completion_tokens"] = 1024
        try:
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderError(str(exc), error_class="transient") from exc
        body = self._body(response)
        if response.status_code >= 400:
            raise self._http_error(response.status_code, body)
        try:
            text = body["choices"][0]["message"]["content"]
            parsed = json.loads(self._strip_fences(text))
            if not isinstance(parsed, dict):
                raise TypeError("response is not an object")
            return ProviderResponse(parsed, body.get("usage", {}))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(f"OpenAI-compatible provider returned invalid JSON: {body}", error_class="invalid_or_unknown", retryable=False) from exc

    def complete_text(self, *, model: str, secret: str, system_prompt: str, user_prompt: str, timeout_seconds: int) -> ProviderResponse:
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        if self.provider_id == "groq":
            payload["max_completion_tokens"] = 1024
        try:
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderError(str(exc), error_class="transient") from exc
        body = self._body(response)
        if response.status_code >= 400:
            raise self._http_error(response.status_code, body)
        try:
            content = body["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
            text = str(content).strip()
            if not text:
                raise ValueError("empty text content")
            return ProviderResponse({"output_type": "translation", "text": text, "translation": text}, body.get("usage", {}))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(f"OpenAI-compatible provider returned empty text: {body}", error_class="invalid_or_unknown", retryable=False) from exc

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
        clean = clean.removesuffix("```")
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
