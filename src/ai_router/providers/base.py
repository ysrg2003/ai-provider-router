from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Protocol


_URL_RE = re.compile(r"https?://[^\s<>\"']+")


def url_citations_from_text(text: str) -> list[str]:
    """Return unique explicit HTTP(S) URLs present in provider text, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in _URL_RE.findall(str(text or "")):
        url = raw.rstrip(".,;:!?)]}\\\"")
        if url and url not in seen:
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
                visit(child, citation_field=citation_field or str(key).lower() in {"url", "uri", "source_url", "link"})
        elif isinstance(node, list):
            for child in node:
                visit(child, citation_field=citation_field)
        elif citation_field and isinstance(node, str):
            for url in url_citations_from_text(node):
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
