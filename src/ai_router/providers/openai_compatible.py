from __future__ import annotations

import json
from typing import Any, Mapping

import requests

from .base import ProviderError, ProviderResponse


class OpenAICompatibleAdapter:
    def __init__(self, provider_id: str, base_url: str) -> None:
        self.provider_id = provider_id
        self.base_url = base_url.rstrip("/")

    def complete_json(
        self,
        *,
        model: str,
        secret: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: int,
        supports_response_format: bool = True,
        invocation_profile: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        profile = dict(invocation_profile or {})
        model_suffix = profile.get("model_suffix")
        if isinstance(model_suffix, str) and model_suffix:
            for known_suffix in (":fastest", ":cheapest", ":preferred"):
                if model.endswith(known_suffix):
                    model = model[: -len(known_suffix)]
                    break
            model = f"{model}{model_suffix}"
        endpoint = f"{self.base_url}/chat/completions"
        messages: list[dict[str, str]] = []
        if not profile.get("omit_system_prompt") and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        response_format = profile.get("response_format", "json_object" if supports_response_format else "none")
        if response_format == "json_object" and supports_response_format:
            payload["response_format"] = {"type": "json_object"}
        elif isinstance(response_format, dict) and supports_response_format:
            payload["response_format"] = response_format
        max_tokens_field = profile.get("max_tokens_field")
        if not max_tokens_field and self.provider_id == "groq":
            max_tokens_field = "max_completion_tokens"
        if max_tokens_field:
            payload[str(max_tokens_field)] = int(profile.get("max_tokens", 1024))
        reasoning_effort = profile.get("reasoning_effort")
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
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
            content = self._content_text(body["choices"][0]["message"].get("content"))
            if not content.strip():
                raise ValueError("empty content")
            parser = str(profile.get("response_parser", "json_object"))
            clean_content = content.strip()
            if parser in {"text_envelope", "json_or_text_envelope"} and parser == "text_envelope":
                return self._text_envelope(clean_content, body.get("usage", {}))
            try:
                parsed = json.loads(self._strip_fences(clean_content))
                if not isinstance(parsed, dict):
                    raise TypeError("response is not an object")
                return ProviderResponse(parsed, body.get("usage", {}))
            except (TypeError, ValueError, json.JSONDecodeError):
                if parser == "json_or_text_envelope":
                    return self._text_envelope(clean_content, body.get("usage", {}))
                raise
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError(
                "OpenAI-compatible provider returned an unusable response",
                error_class="invalid_or_unknown",
                retryable=False,
            ) from exc

    def complete_chat(
        self,
        *,
        model: str,
        secret: str,
        messages: list[dict[str, Any]],
        timeout_seconds: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
        parallel_tool_calls: bool | None = None,
        invocation_profile: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        profile = dict(invocation_profile or {})
        model_suffix = profile.get("model_suffix")
        if isinstance(model_suffix, str) and model_suffix:
            for known_suffix in (":fastest", ":cheapest", ":preferred"):
                if model.endswith(known_suffix):
                    model = model[: -len(known_suffix)]
                    break
            model = f"{model}{model_suffix}"
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
            if parallel_tool_calls is not None:
                payload["parallel_tool_calls"] = parallel_tool_calls
        max_tokens_field = profile.get("max_tokens_field")
        if not max_tokens_field and self.provider_id == "groq":
            max_tokens_field = "max_completion_tokens"
        if max_tokens_field:
            payload[str(max_tokens_field)] = int(profile.get("max_tokens", 1024))
        reasoning_effort = profile.get("reasoning_effort")
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
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
            choice = body["choices"][0]
            message = choice["message"]
            if not isinstance(message, dict):
                raise TypeError("assistant message is not an object")
            content = self._content_text(message.get("content"))
            tool_calls = message.get("tool_calls") or []
            if not content.strip() and not isinstance(tool_calls, list):
                raise ValueError("tool_calls is not an array")
            if not content.strip() and not tool_calls:
                raise ValueError("empty assistant message")
            return ProviderResponse(
                {
                    "role": str(message.get("role") or "assistant"),
                    "content": content or None,
                    "tool_calls": tool_calls,
                    "finish_reason": choice.get("finish_reason"),
                },
                body.get("usage", {}),
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(
                "OpenAI-compatible provider returned an unusable chat response",
                error_class="invalid_or_unknown",
                retryable=False,
            ) from exc

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
            content = self._content_text(body["choices"][0]["message"].get("content"))
            text = content.strip()
            if not text:
                raise ValueError("empty text content")
            return ProviderResponse({"output_type": "translation", "text": text, "translation": text}, body.get("usage", {}))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("OpenAI-compatible provider returned empty text", error_class="invalid_or_unknown", retryable=False) from exc

    @staticmethod
    def _text_envelope(content: str, usage: dict[str, Any]) -> ProviderResponse:
        if not content:
            raise ValueError("empty content")
        return ProviderResponse({"output_type": "text", "text": content, "response": content, "provider_text": content}, usage)

    @classmethod
    def _content_text(cls, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            for key in ("text", "content", "value"):
                value = content.get(key)
                if isinstance(value, str):
                    return value
            return "".join(cls._content_text(value) for value in content.values())
        if isinstance(content, list):
            return "".join(cls._content_text(value) for value in content)
        return ""

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
        if status_code == 402:
            return ProviderError(message, error_class="plan_or_credit", status_code=status_code, retryable=False)
        if status_code == 429:
            return ProviderError(message, error_class="quota", status_code=status_code)
        if status_code in {408, 409, 425, 500, 502, 503, 504}:
            return ProviderError(message, error_class="transient", status_code=status_code)
        return ProviderError(message, error_class="invalid_or_unknown", status_code=status_code, retryable=False)
