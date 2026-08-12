from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .config import RouterConfig
from .providers.base import ProviderAdapter, ProviderError
from .providers.gemini import GeminiAdapter
from .providers.openai_compatible import OpenAICompatibleAdapter
from .store import RouterStore


class AllProvidersFailed(RuntimeError):
    pass


class AIRouter:
    """Reusable ordered multi-provider JSON router.

    Provider definitions, model chains, key pools, and retry policies are loaded
    from independent JSON files. Adding or removing a provider normally requires
    only configuration plus an adapter when the provider is not OpenAI-compatible.
    """

    def __init__(self, *, config_dir: str | Path | None = None, state_db: str | Path = "data/ai_router.db") -> None:
        self.config = RouterConfig.load(config_dir)
        self.store = RouterStore(state_db)
        self.adapters: dict[str, ProviderAdapter] = {}
        for provider_id, spec in self.config.providers.items():
            if spec.kind == "gemini_rest":
                self.adapters[provider_id] = GeminiAdapter(spec.base_url)
            elif spec.kind == "openai_compatible":
                self.adapters[provider_id] = OpenAICompatibleAdapter(provider_id, spec.base_url)
            else:
                raise ValueError(f"Unsupported provider kind: {spec.kind}")

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        operation: str = "completion",
        chain: str = "default",
    ) -> dict[str, Any]:
        errors: list[str] = []
        attempts = 0
        for model_spec in self.config.model_chain(chain):
            provider_spec = self.config.providers[model_spec.provider_id]
            adapter = self.adapters[model_spec.provider_id]
            keys = self.config.keys_for(model_spec.provider_id)
            for key in keys:
                if attempts >= self.config.policy.max_attempts:
                    break
                attempts += 1
                if self.store.is_cooling(model_spec.provider_id, model_spec.model, key.key_id):
                    continue
                try:
                    response = adapter.complete_json(
                        model=model_spec.model,
                        secret=key.secret,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        timeout_seconds=provider_spec.timeout_seconds or self.config.policy.request_timeout_seconds,
                    )
                    self.store.record_success(
                        provider=model_spec.provider_id,
                        model=model_spec.model,
                        key_id=key.key_id,
                        project=key.project,
                        operation=operation,
                        usage=response.usage,
                    )
                    return response.payload
                except ProviderError as exc:
                    errors.append(f"{model_spec.provider_id}/{model_spec.model}/{key.key_id}: {exc}")
                    cooldown = self.config.policy.cooldowns_seconds.get(exc.error_class, 300)
                    self.store.record_failure(
                        provider=model_spec.provider_id,
                        model=model_spec.model,
                        key_id=key.key_id,
                        project=key.project,
                        operation=operation,
                        error_class=exc.error_class,
                        message=str(exc),
                        status_code=exc.status_code,
                        cooldown_seconds=cooldown,
                    )
                    if exc.retryable:
                        time.sleep(min(2.0, self._backoff(attempts)))
            if attempts >= self.config.policy.max_attempts:
                break
        self.store.checkpoint()
        raise AllProvidersFailed("All configured provider/model/key attempts failed: " + " | ".join(errors[-12:]))

    def summary(self) -> dict[str, Any]:
        return {"config": self.config.public_summary(), "state": self.store.stats()}

    def close(self) -> None:
        self.store.checkpoint()

    def _backoff(self, attempt: int) -> int:
        values = self.config.policy.backoff_seconds
        return values[min(max(attempt - 1, 0), len(values) - 1)] if values else 0
