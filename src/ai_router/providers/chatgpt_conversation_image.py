from __future__ import annotations

import base64
from typing import Any

import requests

from .base import ProviderError, ProviderResponse


class ChatGPTConversationImageAdapter:
    """Use the uploaded service's ordinary ChatGPT conversation for text and images."""

    provider_id = "chatgpt_conversation"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def complete_interaction_text(
        self,
        *,
        model: str,
        secret: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: int,
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        del model
        system = system_prompt.strip()
        if tools and any(tool.get("type") == "google_search" for tool in tools):
            system = (
                f"{system}\n\n" if system else ""
            ) + (
                "نفّذ بحثًا حيًا في الويب قبل الإجابة. استخدم البحث الفعلي الآن، "
                "ولا تعتمد على الذاكرة وحدها. اذكر المصادر والروابط التي اعتمدت عليها."
            )
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_prompt})
        body = self._post_chat(
            secret=secret,
            messages=messages,
            timeout_seconds=timeout_seconds,
        )
        text = self._message_text(body)
        if not text:
            raise ProviderError(
                "chatgpt conversation returned no text",
                error_class="invalid_or_unknown",
                retryable=False,
            )
        return ProviderResponse(
            {
                "output_type": "text",
                "text": text,
                "steps": [],
                "annotations": [],
                "provider": self.provider_id,
            },
            body.get("usage", {}),
        )

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
        body = self._post_chat(
            secret=secret,
            messages=[{"role": "user", "content": prompt}],
            timeout_seconds=timeout_seconds,
        )
        try:
            content = body["choices"][0]["message"].get("content")
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "chatgpt conversation returned no message",
                error_class="invalid_or_unknown",
                retryable=False,
            ) from exc
        image = self._first_image(content)
        if image is None:
            raise ProviderError(
                "chatgpt conversation returned no image",
                error_class="invalid_or_unknown",
                retryable=False,
            )
        mime_type, encoded = image
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ProviderError(
                "chatgpt conversation returned invalid image data",
                error_class="invalid_or_unknown",
                retryable=False,
            ) from exc
        if not raw:
            raise ProviderError(
                "chatgpt conversation returned an empty image",
                error_class="invalid_or_unknown",
                retryable=False,
            )
        return ProviderResponse(
            {
                "output_type": "image",
                "mime_type": mime_type,
                "data_base64": base64.b64encode(raw).decode("ascii"),
                "provider": self.provider_id,
            },
            body.get("usage", {}),
        )

    def _post_chat(
        self,
        *,
        secret: str,
        messages: list[dict[str, str]],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        endpoint = f"{self.base_url}/v1/chat/completions"
        try:
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "messages": messages},
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderError(str(exc), error_class="transient") from exc
        body = self._body(response)
        if response.status_code >= 400:
            raise self._http_error(response.status_code, body)
        return body

    @staticmethod
    def _message_text(body: dict[str, Any]) -> str:
        try:
            content = body["choices"][0]["message"].get("content")
        except (KeyError, IndexError, TypeError):
            return ""
        if isinstance(content, str):
            return content.strip()
        if not isinstance(content, list):
            return ""
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()

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
