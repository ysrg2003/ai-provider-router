from __future__ import annotations

import base64
import time
from typing import Any

import requests

from .base import ProviderError, ProviderResponse


class ChatGPTConversationImageAdapter:
    """Use the uploaded service's ChatGPT conversation for text and images."""

    provider_id = "chatgpt_conversation"

    def __init__(self, base_url: str, *, poll_interval_seconds: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.poll_interval_seconds = poll_interval_seconds

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
        body = self._post_job(
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
        body = self._post_job(
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
        image = self._first_image_from_body(body, content)
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

    def _post_job(
        self,
        *,
        secret: str,
        messages: list[dict[str, str]],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        endpoint = f"{self.base_url}/v1/jobs"
        headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
        request_timeout = min(max(timeout_seconds, 30), 60)
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json={"model": "gpt-4o-mini", "messages": messages, "stream": False},
                timeout=request_timeout,
            )
        except requests.RequestException as exc:
            raise ProviderError(str(exc), error_class="transient") from exc
        body = self._body(response)
        if response.status_code >= 400:
            raise self._http_error(response.status_code, body)
        job_id = body.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            raise ProviderError(
                "chatgpt-api did not return a conversation job id",
                error_class="invalid_or_unknown",
                retryable=False,
            )

        deadline = time.monotonic() + max(timeout_seconds, 1)
        status_endpoint = f"{endpoint}/{job_id}"
        while time.monotonic() < deadline:
            try:
                status_response = requests.get(
                    status_endpoint,
                    headers={"Authorization": f"Bearer {secret}"},
                    timeout=min(request_timeout, 30),
                )
            except requests.RequestException as exc:
                raise ProviderError(str(exc), error_class="transient") from exc
            status_body = self._body(status_response)
            if status_response.status_code >= 400:
                raise self._http_error(status_response.status_code, status_body)
            state = str(status_body.get("status") or "").lower()
            if state == "done":
                result = status_body.get("response")
                if isinstance(result, dict):
                    return result
                raise ProviderError(
                    "chatgpt-api conversation job returned no response",
                    error_class="invalid_or_unknown",
                    retryable=False,
                )
            if state == "error":
                raise ProviderError(
                    str(status_body.get("error") or "chatgpt-api conversation job failed"),
                    error_class="upstream_error",
                    retryable=False,
                )
            time.sleep(min(self.poll_interval_seconds, max(0.0, deadline - time.monotonic())))
        raise ProviderError("chatgpt-api conversation job timed out", error_class="transient")

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

    @classmethod
    def _first_image_from_body(cls, body: dict[str, Any], content: Any) -> tuple[str, str] | None:
        candidates: list[Any] = [content]
        for key in ("output", "data", "images", "image", "result"):
            if key in body:
                candidates.append(body[key])
        for candidate in candidates:
            image = cls._first_image(candidate)
            if image is not None:
                return image
        return None

    @classmethod
    def _first_image(cls, value: Any) -> tuple[str, str] | None:
        """Extract image bytes from common ChatGPT/OpenAI and browser-wrapper shapes."""
        if isinstance(value, str):
            return cls._parse_image_string(value, "image/png")
        if isinstance(value, list):
            for item in value:
                image = cls._first_image(item)
                if image is not None:
                    return image
            return None
        if not isinstance(value, dict):
            return None

        mime = str(value.get("mime_type") or value.get("content_type") or value.get("media_type") or "image/png").lower()
        if not mime.startswith("image/"):
            mime = "image/png"
        for key in ("image_url", "url", "src", "data_url", "image", "image_asset", "attachment"):
            nested = value.get(key)
            if nested is not None:
                image = cls._first_image(nested) if isinstance(nested, (dict, list)) else cls._parse_image_string(str(nested), mime)
                if image is not None:
                    return image
        for key in ("b64_json", "data_base64", "image_base64", "base64", "result"):
            encoded = value.get(key)
            if isinstance(encoded, str) and encoded:
                if encoded.startswith("data:image/"):
                    image = cls._parse_image_string(encoded, mime)
                    if image is not None:
                        return image
                else:
                    return mime, encoded
        for key in ("content", "parts", "output"):
            nested = value.get(key)
            if nested is not None:
                image = cls._first_image(nested)
                if image is not None:
                    return image
        return None

    @staticmethod
    def _parse_image_string(value: str, default_mime: str) -> tuple[str, str] | None:
        if not value:
            return None
        if value.startswith("data:image/"):
            header, separator, encoded = value.partition(",")
            if separator and ";base64" in header and encoded:
                mime_type = header[5:].split(";", 1)[0].strip().lower()
                if mime_type.startswith("image/"):
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
        if isinstance(error, dict):
            message = str(error.get("message") or error.get("type") or "request rejected")
        else:
            message = "request rejected"
        if status_code in {401, 403}:
            return ProviderError(message, error_class="auth", status_code=status_code, retryable=False)
        if status_code == 429:
            return ProviderError(message, error_class="quota", status_code=status_code)
        if status_code in {408, 409, 425, 500, 502, 503, 504}:
            return ProviderError(message, error_class="transient", status_code=status_code)
        return ProviderError(message, error_class="invalid_or_unknown", status_code=status_code, retryable=False)
