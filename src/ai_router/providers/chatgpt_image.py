from __future__ import annotations

import base64
import time
from typing import Any

import requests

from .base import ProviderError, ProviderResponse


class ChatGPTImageAdapter:
    """Adapter for the authenticated chatgpt-api visual asset job service."""

    provider_id = "chatgpt_image"

    def __init__(self, base_url: str, *, poll_interval_seconds: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.poll_interval_seconds = poll_interval_seconds

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
        del model, tools
        if image_data:
            raise ProviderError(
                "chatgpt-api image generation accepts text prompts only; use Gemini for image-input edits",
                error_class="invalid_or_unknown",
                retryable=False,
            )
        if not prompt.strip():
            raise ProviderError("image prompt is empty", error_class="invalid_or_unknown", retryable=False)
        # chatgpt-api's documented examples send the raw API key in Authorization.
        # The Space accepts this form as well as the optional Bearer prefix.
        headers = {"Authorization": secret, "Content-Type": "application/json"}
        endpoint = f"{self.base_url}/v1/visual-assets/jobs"
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json={"prompt": prompt},
                timeout=min(timeout_seconds, 60),
            )
        except requests.RequestException as exc:
            raise ProviderError(str(exc), error_class="transient") from exc
        body = self._body(response)
        if response.status_code >= 400:
            raise self._http_error(response.status_code, body)
        job_id = body.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            raise ProviderError("chatgpt-api did not return a visual job id", error_class="invalid_or_unknown", retryable=False)

        deadline = time.monotonic() + max(1, timeout_seconds)
        status_endpoint = f"{self.base_url}/v1/visual-assets/jobs/{job_id}"
        download_endpoint = f"{status_endpoint}/download"
        while time.monotonic() < deadline:
            try:
                status_response = requests.get(status_endpoint, headers={"Authorization": secret}, timeout=min(timeout_seconds, 30))
            except requests.RequestException as exc:
                raise ProviderError(str(exc), error_class="transient") from exc
            status_body = self._body(status_response)
            if status_response.status_code >= 400:
                raise self._http_error(status_response.status_code, status_body)
            status = str(status_body.get("status") or "").lower()
            if status == "error":
                raise ProviderError("chatgpt-api visual job failed", error_class="upstream_error", retryable=False)
            if status == "done":
                return self._download_image(download_endpoint, secret=secret, timeout_seconds=timeout_seconds)
            time.sleep(min(self.poll_interval_seconds, max(0.0, deadline - time.monotonic())))
        raise ProviderError("chatgpt-api visual job timed out", error_class="transient")

    def _download_image(self, endpoint: str, *, secret: str, timeout_seconds: int) -> ProviderResponse:
        try:
            response = requests.get(
                endpoint,
                headers={"Authorization": secret},
                timeout=min(timeout_seconds, 60),
            )
        except requests.RequestException as exc:
            raise ProviderError(str(exc), error_class="transient") from exc
        if response.status_code >= 400:
            raise self._http_error(response.status_code, self._body(response))
        content_type = response.headers.get("content-type", "image/png").split(";", 1)[0].strip().lower()
        if not content_type.startswith("image/"):
            raise ProviderError("chatgpt-api returned a non-image asset", error_class="invalid_or_unknown", retryable=False)
        if not response.content:
            raise ProviderError("chatgpt-api returned an empty image", error_class="invalid_or_unknown", retryable=False)
        return ProviderResponse(
            {
                "output_type": "image",
                "mime_type": content_type,
                "data_base64": base64.b64encode(response.content).decode("ascii"),
                "provider_job": "chatgpt-api",
            },
            {},
        )

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
