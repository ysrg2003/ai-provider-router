from __future__ import annotations

import base64
from typing import Any

import requests

from .base import ProviderError, ProviderResponse


class ChatGPTConversationImageAdapter:
    """Generate images through the uploaded service's ordinary chat endpoint."""

    provider_id = "chatgpt_conversation"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def generate_image(
        self,
        *,
        model: str,
        secret: str,
        prompt: str,
        timeout_seconds: int,
        image_data: str | None = None,
        image_mime_type: str = "image/png",
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        del model, image_data, image_mime_type, tools
        if not prompt.strip():
            raise ProviderError("image prompt is empty", error_class="invalid_or_unknown", retryable=False)
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
        }
        endpoint = f"{self.base_url}/v1/chat/completions"
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
            content = body["choices"][0]["message"].get("content")
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("chatgpt conversation returned no message", error_class="invalid_or_unknown", retryable=False) from exc
        image = self._first_image(content)
        if image is None:
            raise ProviderError("chatgpt conversation returned no image", error_class="invalid_or_unknown", retryable=False)
        mime_type, encoded = image
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ProviderError("chatgpt conversation returned invalid image data", error_class="invalid_or_unknown", retryable=False) from exc
        if not raw:
            raise ProviderError("chatgpt conversation returned an empty image", error_class="invalid_or_unknown", retryable=False)
        return ProviderResponse(
            {
                "output_type": "image",
                "mime_type": mime_type,
                "data_base64": base64.b64encode(raw).decode("ascii"),
                "provider": self.provider_id,
            },
            body.get("usage", {}),
        )

    @staticmethod
    def _first_image(content: Any) -> tuple[str, str] | None:
        if not isinstance(content, list):
            return None
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "image_url":
                continue
            image_url = part.get("image_url")
            url = image_url.get("url") if isinstance(image_url, dict) else image_url
            if not isinstance(url, str) or not url.startswith("data:image/"):
                continue
            header, separator, encoded = url.partition(",")
            if not separator or ";base64" not in header:
                continue
            mime_type = header[5:].split(";", 1)[0].strip().lower()
            if mime_type.startswith("image/") and encoded:
                return mime_type, encoded
        return None

    @staticmethod
    def _body(response: requests.Response) -> dict[str, Any]:
        try:
            value = response.json()
            return value if isinstance(value, dict) else {"data": value}
        except ValueError:
            return {"raw": response.text[:2000]}

    @staticmethod
    def _http_error(status_code: int, body: dict[str, Any]) -> ProviderError:
        error = body.get("error", {}) if isinstance(body, dict) else {}
        message = str(error.get("message") or error.get("type") or "request rejected") if isinstance(error, dict) else "request rejected"
        if status_code in {401, 403}:
            return ProviderError(message, error_class="auth", status_code=status_code, retryable=False)
        if status_code == 429:
            return ProviderError(message, error_class="quota", status_code=status_code)
        if status_code in {408, 409, 425, 500, 502, 503, 504}:
            return ProviderError(message, error_class="transient", status_code=status_code)
        return ProviderError(message, error_class="invalid_or_unknown", status_code=status_code, retryable=False)
