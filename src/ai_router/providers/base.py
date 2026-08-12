from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


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

    def complete_json(self, *, model: str, secret: str, system_prompt: str, user_prompt: str, timeout_seconds: int) -> ProviderResponse:
        ...
