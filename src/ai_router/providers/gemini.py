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
            raise ProviderError("Gemini returned invalid JSON", error_class="invalid_or_unknown", retryable=False) from exc

    def complete_video_json(
        self,
        *,
        model: str,
        secret: str,
        video_uri: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: int,
    ) -> ProviderResponse:
        """Analyze one public video URI through Gemini Interactions API."""
        endpoint = f"{self.base_url}/interactions"
        combined_prompt = f"{system_prompt.strip()}\n\n{user_prompt.strip()}".strip()
        payload = {
            "model": model,
            "input": [
                {"type": "video", "uri": video_uri},
                {"type": "text", "text": combined_prompt},
            ],
        }
        try:
            response = requests.post(
                endpoint,
                headers={"x-goog-api-key": secret, "Content-Type": "application/json"},
                json=payload,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderError(str(exc), error_class="transient") from exc
        body = self._body(response)
        if response.status_code >= 400:
            raise self._http_error(response.status_code, body)
        try:
            text = self._interaction_text(body)
            parsed = json.loads(self._strip_fences(text))
            if not isinstance(parsed, dict):
                raise ValueError("response is not an object")
            usage = body.get("usage", body.get("usageMetadata", {}))
            return ProviderResponse(parsed, usage if isinstance(usage, dict) else {})
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Gemini video returned invalid JSON", error_class="invalid_or_unknown", retryable=False) from exc

    @staticmethod
    def _body(response: requests.Response) -> dict[str, Any]:
        try:
            value = response.json()
            return value if isinstance(value, dict) else {"data": value}
        except ValueError:
            return {"raw": response.text[:2000]}

    @staticmethod
    def _interaction_text(body: dict[str, Any]) -> str:
        output_text = body.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        chunks: list[str] = []
        for step in body.get("steps", []) or []:
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            for block in step.get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                    chunks.append(block["text"])
        if not chunks:
            raise ValueError("no model output text")
        return "\n".join(chunks)

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
        error = body.get("error", {}) if isinstance(body, dict) else {}
        status = error.get("status") if isinstance(error, dict) else None
        message = str(status or "request rejected")
        if status_code in {401, 403}:
            return ProviderError(message, error_class="auth", status_code=status_code, retryable=False)
        if status_code == 429:
            return ProviderError(message, error_class="quota", status_code=status_code)
        if status_code in {408, 409, 425, 500, 502, 503, 504}:
            return ProviderError(message, error_class="transient", status_code=status_code)
        return ProviderError(message, error_class="invalid_or_unknown", status_code=status_code, retryable=False)
