from __future__ import annotations

import base64
import json
import time
from typing import Any

import requests

from .base import ProviderError, ProviderResponse, url_citations_from_annotations, url_citations_from_text


class ChatGPTSpaceAdapter:
    """HTTP adapter for the deployed chatgpt-api Hugging Face Space."""

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
        messages: list[dict[str, str]] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        effective_prompt = user_prompt
        if tools and any(
            str(tool.get("type", "")).lower() in {"search", "google_search", "web_search_preview"}
            or str(tool.get("name", "")).lower() == "search"
            for tool in tools
        ):
            if "ابحث في الويب بحث حي:" not in effective_prompt and "live web search:" not in effective_prompt.lower():
                effective_prompt = f"ابحث في الويب بحث حي: {effective_prompt}"
        messages.append({"role": "user", "content": effective_prompt})
        body = self._post(model=model, secret=secret, messages=messages, timeout_seconds=timeout_seconds, tools=tools)
        text = self._text_from_body(body)
        url_citations = url_citations_from_text(text)
        structured_nodes = [body.get("annotations"), body.get("citations"), body.get("choices")]
        for url in url_citations_from_annotations(structured_nodes):
            if url not in url_citations:
                url_citations.append(url)
        return ProviderResponse(
            {
                "output_type": "text",
                "text": text,
                "annotations": body.get("annotations", []),
                "url_citations": url_citations,
                "images": body.get("images", []),
            },
            body.get("usage", {}),
        )

    def complete_json(
        self,
        *,
        model: str,
        secret: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: int,
        supports_response_format: bool = True,
    ) -> ProviderResponse:
        response = self.complete_interaction_text(
            model=model,
            secret=secret,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=timeout_seconds,
        )
        try:
            payload = json.loads(self._strip_fences(str(response.payload["text"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("ChatGPT Space returned invalid JSON", error_class="invalid_or_unknown", retryable=False) from exc
        if not isinstance(payload, dict):
            raise ProviderError("ChatGPT Space returned a non-object JSON value", error_class="invalid_or_unknown", retryable=False)
        return ProviderResponse(payload, response.usage)

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
        user_content: str | list[dict[str, Any]] = prompt
        if image_data:
            user_content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{image_mime_type};base64,{image_data}"}},
            ]
        body: dict[str, Any] = {}
        images: list[Any] = []
        for attempt in range(2):
            body = self._post(
                model=model,
                secret=secret,
                messages=[{"role": "user", "content": user_content}],
                timeout_seconds=max(timeout_seconds, 540),
                tools=tools,
                output_type="image",
            )
            raw_images = body.get("images") or []
            candidates = raw_images if isinstance(raw_images, list) else []
            images = [item for item in candidates if isinstance(item, dict) and self._is_generated_image(item)]
            if images:
                break
            response_text = self._text_from_body(body)
            lowered = response_text.lower()
            if "free plan limit" in lowered or "image generations requests" in lowered or "limit resets" in lowered:
                raise ProviderError("ChatGPT Space image generation quota is exhausted", error_class="quota", status_code=429, retryable=False)
            if attempt < 1:
                time.sleep(20)
        if not images:
            raise ProviderError("ChatGPT Space returned no generated image data after 2 attempts", error_class="invalid_or_unknown", retryable=False)
        first = next(
            (item for item in images if isinstance(item.get("data_url") or item.get("dataUrl"), str)),
            None,
        )
        if first:
            data_url = str(first.get("data_url") or first.get("dataUrl"))
            try:
                header, encoded = data_url.split(",", 1)
                mime_type = header.split(";", 1)[0].removeprefix("data:") or "image/png"
                base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as exc:
                raise ProviderError("ChatGPT Space returned malformed image data", error_class="invalid_or_unknown", retryable=False) from exc
        else:
            first = next(
                (item for item in images if item.get("src") or item.get("url") or item.get("image_url")),
                None,
            )
            if not first:
                raise ProviderError("ChatGPT Space returned no downloadable image data", error_class="invalid_or_unknown", retryable=False)
            image_url = first.get("src") or first.get("url") or first.get("image_url")
            if isinstance(image_url, dict):
                image_url = image_url.get("url")
            encoded, mime_type = self._download_src(str(image_url), secret=secret, timeout_seconds=timeout_seconds)
        return ProviderResponse(
            {
                "output_type": "image",
                "mime_type": mime_type,
                "data_base64": encoded,
                "text": self._text_from_body(body),
                "source": "chatgpt_space",
            },
            body.get("usage", {}),
        )

    @staticmethod
    def _is_generated_image(item: dict[str, Any]) -> bool:
        raw_data_url = item.get("data_url") or item.get("dataUrl")
        if isinstance(raw_data_url, str) and raw_data_url.lower().startswith("data:image/"):
            return True
        nested = item.get("image_url")
        if isinstance(nested, dict):
            nested = nested.get("url")
        raw_src = item.get("src") or item.get("url") or nested or ""
        src = str(raw_src).lower()
        alt = str(item.get("alt", "")).lower()
        blocked_markers = ("favicon", "avatar", "profile", "logo", "icon", "emoji", "thumbnail")
        if any(marker in src or marker in alt for marker in blocked_markers):
            return False
        if "generated image" in alt or "generated_image" in alt:
            return True
        if src.startswith("blob:"):
            return True
        return "backend-api" in src and any(marker in src for marker in ("file_", "estuary", "/content", "/files/"))

    @staticmethod
    def _download_src(src: str, *, secret: str, timeout_seconds: int) -> tuple[str, str]:
        if not src.startswith(("https://", "http://")):
            raise ProviderError("ChatGPT Space returned an unsupported image URL", error_class="invalid_or_unknown", retryable=False)
        try:
            response = requests.get(
                src,
                headers={"Authorization": f"Bearer {secret}"},
                timeout=max(timeout_seconds, 30),
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError("ChatGPT Space image URL could not be downloaded", error_class="transient") from exc
        mime_type = response.headers.get("content-type", "image/png").split(";", 1)[0]
        if not mime_type.startswith("image/"):
            raise ProviderError("ChatGPT Space image URL did not return an image", error_class="invalid_or_unknown", retryable=False)
        return base64.b64encode(response.content).decode("ascii"), mime_type

    def _post(
        self,
        *,
        model: str,
        secret: str,
        messages: list[dict[str, Any]],
        timeout_seconds: int,
        tools: list[dict[str, Any]] | None = None,
        output_type: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if output_type:
            payload["output_type"] = output_type
        if tools:
            payload["tools"] = tools
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderError(str(exc), error_class="transient") from exc
        body = self._body(response)
        if response.status_code >= 400:
            raise self._http_error(response.status_code, body)
        return body

    @staticmethod
    def _text_from_body(body: dict[str, Any]) -> str:
        try:
            content = body["choices"][0]["message"].get("content", "")
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("ChatGPT Space returned no assistant text", error_class="invalid_or_unknown", retryable=False) from exc

        def flatten(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                return "\\n".join(part for part in (flatten(item) for item in value) if part)
            if isinstance(value, dict):
                for key in ("text", "content", "value"):
                    if key in value:
                        extracted = flatten(value[key])
                        if extracted:
                            return extracted
                return json.dumps(value, ensure_ascii=False)
            return str(value)

        return flatten(content)

    @staticmethod
    def _body(response: requests.Response) -> dict[str, Any]:
        try:
            value = response.json()
            return value if isinstance(value, dict) else {"data": value}
        except ValueError:
            return {"raw": response.text[:2000]}

    @staticmethod
    def _strip_fences(text: str) -> str:
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1]
        return clean.removesuffix("```").strip()

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
