from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Protocol


_URL_RE = re.compile(r"https?://[^\s<>\"']+")


def url_citations_from_text(text: str) -> list[str]:
    """Return unique explicit HTTP(S) URLs, including JSON-escaped slash forms."""
    seen: set[str] = set()
    result: list[str] = []
    raw_text = str(text or "")
    variants = (
        raw_text,
        raw_text.replace("\\\\/", "/"),
        raw_text.replace("\\/", "/"),
        raw_text.replace("\\\\u002F", "/"),
        raw_text.replace("\\u002F", "/"),
    )
    for variant in variants:
        for raw in _URL_RE.findall(variant):
            url = raw.rstrip(".,;:!?)]}\\\"")
            if url and url not in seen:
                seen.add(url)
                result.append(url)
        structured_values: list[Any] = []
        try:
            structured_values.append(json.loads(variant))
        except (TypeError, ValueError):
            decoder = json.JSONDecoder()
            for index, char in enumerate(variant):
                if char not in "[{":
                    continue
                try:
                    value, _ = decoder.raw_decode(variant[index:])
                    structured_values.append(value)
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
        for structured in structured_values:
            for url in url_citations_from_annotations(structured):
                if url not in seen:
                    seen.add(url)
                    result.append(url)
    return result


def url_citations_from_annotations(value: Any) -> list[str]:
    """Return URLs from structured citation annotations without treating prose as citations."""
    seen: set[str] = set()
    result: list[str] = []

    def visit(node: Any, *, citation_field: bool = False) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                visit(child, citation_field=citation_field or str(key).lower() in {"url", "uri", "source_url", "link", "href", "source", "canonical_url", "website", "citation", "citations", "annotation", "annotations", "content", "tool_output", "search_result", "grounding_chunk", "sources", "videos", "results", "items", "data", "links"})
        elif isinstance(node, list):
            for child in node:
                visit(child, citation_field=citation_field)
        elif isinstance(node, str):
            candidate = node.strip().rstrip(".,;:!?)]}\"'")
            looks_like_url = "://" in candidate or bool(re.match(r"^(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:/|$)", candidate, flags=re.IGNORECASE))
            if (citation_field or looks_like_url) and candidate and "://" not in candidate and re.match(r"^(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:/|$)", candidate, flags=re.IGNORECASE):
                candidate = "https://" + candidate
            if citation_field or looks_like_url:
                for url in url_citations_from_text(candidate):
                    if url not in seen:
                        seen.add(url)
                        result.append(url)

    visit(value)
    return result


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, error_class: str, status_code: int | None = None, retryable: bool = True) -> None:
        super().__init__(message)
        self.error_class = error_class
        self.status_code = status_code
        self.retryable = retryable


@dataclass(frozen=True)
class ProviderResponse:
    payload: dict[str, Any]
    usage: dict[str, Any]


class ProviderAdapter(Protocol):
    provider_id: str

    def complete_json(self, *, model: str, secret: str, system_prompt: str, user_prompt: str, timeout_seconds: int, supports_response_format: bool = True) -> ProviderResponse:
        ...

    def complete_text(self, *, model: str, secret: str, system_prompt: str, user_prompt: str, timeout_seconds: int) -> ProviderResponse:
        ...

    def complete_video_json(self, *, model: str, secret: str, video_uri: str, system_prompt: str, user_prompt: str, timeout_seconds: int) -> ProviderResponse:
        ...
