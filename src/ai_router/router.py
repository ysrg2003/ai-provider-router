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
    from independent JSON files. Each key also has a persistent cursor per
    provider and chain, so a key resumes at its next model after a failure.
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
        chain_specs = self.config.model_chain(chain)
        for model_spec in chain_specs:
            provider_spec = self.config.providers[model_spec.provider_id]
            adapter = self.adapters[model_spec.provider_id]
            model_names = [spec.model for spec in chain_specs if spec.provider_id == model_spec.provider_id]
            model_index = model_names.index(model_spec.model)
            keys = self._ordered_keys(
                provider=model_spec.provider_id,
                chain=chain,
                model=model_spec.model,
                model_names=model_names,
                model_index=model_index,
            )
            for key in keys:
                if attempts >= self.config.policy.max_attempts:
                    break
                attempts += 1
                if self.store.is_cooling(model_spec.provider_id, model_spec.model, key.key_id, key.project):
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
                    self.store.advance_model_cursor(
                        provider=model_spec.provider_id,
                        chain=chain,
                        key_id=key.key_id,
                        project=key.project,
                        model_names=model_names,
                        current_index=model_index,
                        error_class=exc.error_class,
                    )
                    if exc.retryable:
                        time.sleep(min(2.0, self._backoff(attempts)))
            if attempts >= self.config.policy.max_attempts:
                break
        self.store.checkpoint()
        raise AllProvidersFailed("All configured provider/model/key attempts failed: " + " | ".join(errors[-12:]))

    def complete_video_json(
        self,
        *,
        video_uri: str,
        system_prompt: str,
        user_prompt: str,
        operation: str = "video_completion",
        chain: str = "default",
    ) -> dict[str, Any]:
        """Run one public video through adapters that support video input."""
        errors: list[str] = []
        attempts = 0
        chain_specs = self.config.model_chain(chain)
        video_specs = [
            spec
            for spec in chain_specs
            if getattr(self.adapters[spec.provider_id], "complete_video_json", None) is not None
        ]
        for model_spec in video_specs:
            provider_spec = self.config.providers[model_spec.provider_id]
            adapter = self.adapters[model_spec.provider_id]
            complete_video = getattr(adapter, "complete_video_json")
            model_names = [spec.model for spec in video_specs if spec.provider_id == model_spec.provider_id]
            model_index = model_names.index(model_spec.model)
            keys = self._ordered_keys(
                provider=model_spec.provider_id,
                chain=chain,
                model=model_spec.model,
                model_names=model_names,
                model_index=model_index,
            )
            for key in keys:
                if attempts >= self.config.policy.max_attempts:
                    break
                attempts += 1
                if self.store.is_cooling(model_spec.provider_id, model_spec.model, key.key_id, key.project):
                    continue
                try:
                    response = complete_video(
                        model=model_spec.model,
                        secret=key.secret,
                        video_uri=video_uri,
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
                    self.store.advance_model_cursor(
                        provider=model_spec.provider_id,
                        chain=chain,
                        key_id=key.key_id,
                        project=key.project,
                        model_names=model_names,
                        current_index=model_index,
                        error_class=exc.error_class,
                    )
                    if exc.retryable:
                        time.sleep(min(2.0, self._backoff(attempts)))
            if attempts >= self.config.policy.max_attempts:
                break
        self.store.checkpoint()
        raise AllProvidersFailed("All video-capable provider/model/key attempts failed: " + " | ".join(errors[-12:]))

    def _ordered_keys(
        self,
        *,
        provider: str,
        chain: str,
        model: str,
        model_names: list[str],
        model_index: int,
    ) -> list[Any]:
        keys = self.config.keys_for(provider)
        if not keys:
            return []
        grouped: dict[str, list[Any]] = {}
        for key in keys:
            grouped.setdefault(key.project or "default", []).append(key)
        pool_id = self.config.providers[provider].key_pool
        rotation = self.config.key_pool_rotations.get(pool_id, "ordered")
        if rotation == "round_robin":
            project_order = self.store.reserve_project_order(provider, model, list(grouped))
            ordered = [key for project in project_order for key in grouped[project]]
        else:
            ordered = keys
        return [
            key
            for key in ordered
            if self.store.get_model_cursor(
                provider=provider,
                chain=chain,
                key_id=key.key_id,
                project=key.project or "default",
                model_names=model_names,
            ) <= model_index
        ]

    def summary(self) -> dict[str, Any]:
        return {"config": self.config.public_summary(), "state": self.store.stats()}

    def close(self) -> None:
        self.store.checkpoint()

    def _backoff(self, attempt: int) -> int:
        values = self.config.policy.backoff_seconds
        return values[min(max(attempt - 1, 0), len(values) - 1)] if values else 0
