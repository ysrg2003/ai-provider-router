from __future__ import annotations

import json
from typing import Any

import requests

from .base import ProviderError, ProviderResponse, url_citations_from_annotations


class GeminiAdapter:
    provider_id = "google_gemini"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def complete_json(self, *, model: str, secret: str, system_prompt: str, user_prompt: str, timeout_seconds: int, supports_response_format: bool = True) -> ProviderResponse:
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
                raise TypeError("response is not an object")
            return ProviderResponse(parsed, body.get("usageMetadata", {}))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Gemini returned invalid JSON", error_class="invalid_or_unknown", retryable=False) from exc

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
        combined_prompt = f"{system_prompt.strip()}\n\n{user_prompt.strip()}".strip()
        payload: dict[str, Any] = {"model": model, "input": combined_prompt}
        if tools:
            payload["tools"] = tools
        body = self._post_interactions(secret=secret, payload=payload, timeout_seconds=timeout_seconds)
        try:
            text = self._interaction_text(body)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Gemini interaction returned no text", error_class="invalid_or_unknown", retryable=False) from exc
        annotations = self._annotations(body)
        return ProviderResponse(
            {"output_type": "text", "text": text, "steps": body.get("steps", []), "annotations": annotations, "url_citations": url_citations_from_annotations(annotations)},
            body.get("usage", body.get("usageMetadata", {})),
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
        if model.startswith("imagen-"):
            return self._generate_imagen(
                model=model,
                secret=secret,
                prompt=prompt,
                timeout_seconds=timeout_seconds,
            )
        return self._generate_native_image(
            model=model,
            secret=secret,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            image_data=image_data,
            image_mime_type=image_mime_type,
            tools=tools,
        )

    def _generate_native_image(
        self,
        *,
        model: str,
        secret: str,
        prompt: str,
        timeout_seconds: int,
        image_data: str | None,
        image_mime_type: str,
        tools: list[dict[str, Any]] | None,
    ) -> ProviderResponse:
        parts: list[dict[str, Any]] = [{"text": prompt}]
        if image_data:
            parts.append({"inline_data": {"mime_type": image_mime_type, "data": image_data}})
        payload: dict[str, Any] = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }
        if tools:
            payload["tools"] = tools
        endpoint = f"{self.base_url}/models/{model}:generateContent"
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
        image: dict[str, Any] | None = None
        text_parts: list[str] = []
        for candidate in body.get("candidates", []) or []:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content") if isinstance(candidate.get("content"), dict) else {}
            for part in content.get("parts", []) or []:
                if not isinstance(part, dict):
                    continue
                if isinstance(part.get("text"), str) and part["text"].strip():
                    text_parts.append(part["text"])
                inline = part.get("inlineData") or part.get("inline_data")
                if isinstance(inline, dict) and inline.get("data"):
                    image = inline
        if not image:
            raise ProviderError("Gemini did not return an inline image", error_class="invalid_or_unknown", retryable=False)
        return ProviderResponse(
            {
                "output_type": "image",
                "mime_type": str(image.get("mimeType") or image.get("mime_type") or "image/png"),
                "data_base64": str(image["data"]),
                "text": "\\n".join(text_parts).strip(),
            },
            body.get("usageMetadata", body.get("usage", {})),
        )

    def _generate_imagen(self, *, model: str, secret: str, prompt: str, timeout_seconds: int) -> ProviderResponse:
        endpoint = f"{self.base_url}/models/{model}:predict"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1},
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
        predictions = body.get("predictions") or []
        first = predictions[0] if predictions else {}
        if not isinstance(first, dict):
            raise ProviderError("Imagen did not return an image prediction", error_class="invalid_or_unknown", retryable=False)
        encoded = first.get("bytesBase64Encoded") or first.get("bytes_base64_encoded")
        if not encoded:
            raise ProviderError("Imagen did not return image bytes", error_class="invalid_or_unknown", retryable=False)
        return ProviderResponse(
            {
                "output_type": "image",
                "mime_type": str(first.get("mimeType") or first.get("mime_type") or "image/png"),
                "data_base64": str(encoded),
            },
            body.get("usage", body.get("usageMetadata", {})),
        )

    def generate_speech(
        self,
        *,
        model: str,
        secret: str,
        text: str,
        timeout_seconds: int,
        voice: str = "Kore",
    ) -> ProviderResponse:
        payload = {
            "model": model,
            "input": text,
            "response_format": {"type": "audio"},
            "generation_config": {"speech_config": [{"voice": voice}]},
        }
        body = self._post_interactions(secret=secret, payload=payload, timeout_seconds=timeout_seconds)
        audio = self._interaction_audio(body)
        if not isinstance(audio, dict) or not audio.get("data"):
            raise ProviderError("Gemini did not return audio", error_class="invalid_or_unknown", retryable=False)
        return ProviderResponse(
            {
                "output_type": "audio",
                "mime_type": str(audio.get("mime_type") or "audio/pcm"),
                "data_base64": str(audio["data"]),
                "sample_rate_hz": 24000,
            },
            body.get("usage", body.get("usageMetadata", {})),
        )

    def embed_content(
        self,
        *,
        model: str,
        secret: str,
        text: str,
        timeout_seconds: int,
        output_dimensionality: int | None = None,
        content_parts: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        endpoint = f"{self.base_url}/models/{model}:embedContent"
        payload: dict[str, Any] = {
            "model": f"models/{model}",
            "content": {"parts": content_parts or [{"text": text}]},
        }
        if output_dimensionality:
            payload["output_dimensionality"] = output_dimensionality
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
        embeddings = body.get("embeddings") or body.get("embedding")
        if isinstance(embeddings, dict):
            embeddings = [embeddings]
        if not isinstance(embeddings, list):
            raise ProviderError("Gemini did not return embeddings", error_class="invalid_or_unknown", retryable=False)
        return ProviderResponse({"output_type": "embedding", "embeddings": embeddings}, body.get("usageMetadata", {}))

    def complete_video_json(
        self,
        *,
        model: str,
        secret: str,
        video_uri: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: int,
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderResponse:
        """Analyze one public video URI through Gemini Interactions API."""
        combined_prompt = f"{system_prompt.strip()}\n\n{user_prompt.strip()}".strip()
        payload: dict[str, Any] = {
            "model": model,
            "input": [
                {"type": "video", "uri": video_uri},
                {"type": "text", "text": combined_prompt},
            ],
        }
        if tools:
            payload["tools"] = tools
        body = self._post_interactions(secret=secret, payload=payload, timeout_seconds=timeout_seconds)
        try:
            text = self._interaction_text(body)
            parsed = json.loads(self._strip_fences(text))
            if not isinstance(parsed, dict):
                raise TypeError("response is not an object")
            usage = body.get("usage", body.get("usageMetadata", {}))
            return ProviderResponse(parsed, usage if isinstance(usage, dict) else {})
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Gemini video returned invalid JSON", error_class="invalid_or_unknown", retryable=False) from exc

    def _post_interactions(self, *, secret: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
        endpoint = f"{self.base_url}/interactions"
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
        return body

    @staticmethod
    def _body(response: requests.Response) -> dict[str, Any]:
        try:
            value = response.json()
            return value if isinstance(value, dict) else {"data": value}
        except ValueError:
            return {"raw": response.text[:2000]}

    @staticmethod
    def _interaction_audio(body: dict[str, Any]) -> dict[str, Any] | None:
        direct = body.get("output_audio")
        if isinstance(direct, dict) and direct.get("data"):
            return direct
        for step in body.get("steps", []) or []:
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            for block in step.get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "audio" and isinstance(block.get("audio"), dict):
                    return block["audio"]
                if block.get("type") == "audio" and block.get("data"):
                    return block
        return None

    @staticmethod
    def _interaction_text(body: dict[str, Any]) -> str:
        value = GeminiAdapter._interaction_text_optional(body)
        if not value:
            raise ValueError("no model output text")
        return value

    @staticmethod
    def _interaction_text_optional(body: dict[str, Any]) -> str:
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
        return "\n".join(chunks).strip()

    @staticmethod
    def _annotations(body: dict[str, Any]) -> list[dict[str, Any]]:
        annotations: list[dict[str, Any]] = []
        for step in body.get("steps", []) or []:
            for block in step.get("content", []) if isinstance(step, dict) else []:
                if isinstance(block, dict):
                    annotations.extend(item for item in block.get("annotations", []) if isinstance(item, dict))
        return annotations

    @staticmethod
    def _strip_fences(text: str) -> str:
        clean = str(text or "").strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1]
        return clean.removesuffix("```").strip()

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
