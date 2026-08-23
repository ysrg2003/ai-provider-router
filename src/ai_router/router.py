from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .config import ModelSpec, RouterConfig
from .intent import RequestIntent, detect_intent
from .providers.base import ProviderAdapter, ProviderError, url_citations_from_annotations, url_citations_from_text
from .response_contract import validate_response_envelope
from .providers.gemini import GeminiAdapter
from .providers.openai_compatible import OpenAICompatibleAdapter
from .store import RouterStore
from .tools import build_tools


class AllProvidersFailed(RuntimeError):
    pass


class UnsupportedOutputType(ValueError):
    pass


_PROVIDER_ALIASES = {
    "gemini": {"google_gemini"},
    "google_gemini": {"google_gemini"},
    "hf": {"huggingface"},
    "huggingface": {"huggingface"},
    "openrouter": {"openrouter"},
    "nvidia": {"nvidia"},
    "groq": {"groq"},
}


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
        self._last_selection: dict[str, Any] = {}
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
        provider: str | None = None,
        model: str | None = None,
        providers: str | list[str] | tuple[str, ...] | None = None,
        exclude_providers: str | list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        errors: list[str] = []
        attempts = 0
        chain_specs = self._select_specs(
            self._order_specs_by_capability(
                self._filter_specs(
                    self.config.model_chain(chain),
                    providers=providers,
                    exclude_providers=exclude_providers,
                )
            ),
            provider=provider,
            model=model,
        )
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
                    request_kwargs: dict[str, Any] = {
                        "model": model_spec.model,
                        "secret": key.secret,
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "timeout_seconds": provider_spec.timeout_seconds or self.config.policy.request_timeout_seconds,
                    }
                    if isinstance(adapter, OpenAICompatibleAdapter):
                        request_kwargs["supports_response_format"] = model_spec.supports_response_format
                        request_kwargs["invocation_profile"] = self.config.invocation_profile(model_spec)
                    elif not model_spec.supports_response_format:
                        request_kwargs["supports_response_format"] = False
                    response = adapter.complete_json(**request_kwargs)
                    self.store.record_success(
                        provider=model_spec.provider_id,
                        model=model_spec.model,
                        key_id=key.key_id,
                        project=key.project,
                        operation=operation,
                        usage=response.usage,
                    )
                    response.payload["provider"] = model_spec.provider_id
                    response.payload["model"] = model_spec.model
                    response.payload["route"] = chain
                    self._record_selection(model_spec.provider_id, model_spec.model, chain, operation)
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

    def complete_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
        parallel_tool_calls: bool | None = None,
        operation: str = "chat_completion",
        chain: str = "default",
        provider: str | None = None,
        model: str | None = None,
        providers: str | list[str] | tuple[str, ...] | None = None,
        exclude_providers: str | list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty array")
        errors: list[str] = []
        attempts = 0
        specs = [
            spec
            for spec in self.config.model_chain(chain)
            if isinstance(self.adapters[spec.provider_id], OpenAICompatibleAdapter)
        ]
        specs = self._select_specs(
            self._order_specs_by_capability(self._filter_specs(specs, providers=providers, exclude_providers=exclude_providers)),
            provider=provider,
            model=model,
        )
        for spec in specs:
            provider_spec = self.config.providers[spec.provider_id]
            adapter = self.adapters[spec.provider_id]
            provider_models = [item.model for item in specs if item.provider_id == spec.provider_id]
            model_index = provider_models.index(spec.model)
            keys = self._ordered_keys(
                provider=spec.provider_id,
                chain=chain,
                model=spec.model,
                model_names=provider_models,
                model_index=model_index,
            )
            for key in keys:
                if attempts >= self.config.policy.max_attempts:
                    break
                attempts += 1
                if self.store.is_cooling(spec.provider_id, spec.model, key.key_id, key.project):
                    continue
                try:
                    response = adapter.complete_chat(
                        model=spec.model,
                        secret=key.secret,
                        messages=messages,
                        timeout_seconds=provider_spec.timeout_seconds or self.config.policy.request_timeout_seconds,
                        tools=tools,
                        tool_choice=tool_choice,
                        parallel_tool_calls=parallel_tool_calls,
                        invocation_profile=self.config.invocation_profile(spec),
                    )
                    self.store.record_success(
                        provider=spec.provider_id,
                        model=spec.model,
                        key_id=key.key_id,
                        project=key.project,
                        operation=operation,
                        usage=response.usage,
                    )
                    response.payload["provider"] = spec.provider_id
                    response.payload["model"] = spec.model
                    response.payload["route"] = chain
                    self._record_selection(spec.provider_id, spec.model, chain, operation)
                    return response.payload
                except ProviderError as exc:
                    errors.append(f"{spec.provider_id}/{spec.model}/{key.key_id}: {exc}")
                    cooldown = self.config.policy.cooldowns_seconds.get(exc.error_class, 300)
                    self.store.record_failure(
                        provider=spec.provider_id,
                        model=spec.model,
                        key_id=key.key_id,
                        project=key.project,
                        operation=operation,
                        error_class=exc.error_class,
                        message=str(exc),
                        status_code=exc.status_code,
                        cooldown_seconds=cooldown,
                    )
                    self.store.advance_model_cursor(
                        provider=spec.provider_id,
                        chain=chain,
                        key_id=key.key_id,
                        project=key.project,
                        model_names=provider_models,
                        current_index=model_index,
                        error_class=exc.error_class,
                    )
                    if exc.retryable:
                        time.sleep(min(2.0, self._backoff(attempts)))
            if attempts >= self.config.policy.max_attempts:
                break
        self.store.checkpoint()
        raise AllProvidersFailed("All OpenAI-compatible chat attempts failed: " + " | ".join(errors[-12:]))

    def translate_text(
        self,
        *,
        text: str,
        target_language: str,
        source_language: str | None = None,
        operation: str = "translation",
        provider: str | None = None,
        model: str | None = None,
        providers: str | list[str] | tuple[str, ...] | None = None,
        exclude_providers: str | list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        source_hint = f" from {source_language}" if source_language else ""
        prompt = (
            f"Translate the following text{source_hint} to {target_language}. "
            "Return only the translation, with no explanation or quotation marks.\n\n"
            f"{text}"
        )
        return self.complete_auto(
            user_prompt=prompt,
            output_type="translation",
            operation=operation,
            provider=provider,
            model=model,
            providers=providers,
            exclude_providers=exclude_providers,
        )

    def complete_video_json(
        self,
        *,
        video_uri: str,
        system_prompt: str,
        user_prompt: str,
        operation: str = "video_completion",
        chain: str = "default",
        provider: str | None = None,
        model: str | None = None,
        providers: str | list[str] | tuple[str, ...] | None = None,
        exclude_providers: str | list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        """Run one public video through adapters that support video input."""
        errors: list[str] = []
        attempts = 0
        chain_specs = self.config.model_chain(chain)
        video_specs = self._select_specs(
            self._order_specs_by_capability(
                self._filter_specs(
                    [
                        spec
                        for spec in chain_specs
                        if getattr(self.adapters[spec.provider_id], "complete_video_json", None) is not None
                    ],
                    providers=providers,
                    exclude_providers=exclude_providers,
                )
            ),
            provider=provider,
            model=model,
        )
        for model_spec in video_specs:
            provider_spec = self.config.providers[model_spec.provider_id]
            adapter = self.adapters[model_spec.provider_id]
            complete_video = adapter.complete_video_json
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
                    response.payload["provider"] = model_spec.provider_id
                    response.payload["model"] = model_spec.model
                    response.payload["route"] = chain
                    self._record_selection(model_spec.provider_id, model_spec.model, chain, operation)
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

    def route_plan(
        self,
        *,
        user_prompt: str,
        output_type: str = "auto",
        grounding: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        providers: str | list[str] | tuple[str, ...] | None = None,
        exclude_providers: str | list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        intent = detect_intent(user_prompt, output_type=output_type, grounding=grounding)
        route_name, specs = self._resolve_route(intent)
        specs = self._select_specs(
            self._order_specs_by_capability(self._filter_specs(specs, providers=providers, exclude_providers=exclude_providers)),
            provider=provider,
            model=model,
        )
        return {
            "output_type": intent.output_type,
            "grounding": intent.grounding,
            "confidence": intent.confidence,
            "reason": intent.reason,
            "route": route_name,
            "models": [
                {
                    "provider": spec.provider_id,
                    "model": spec.model,
                    "method": spec.method,
                    "input_types": list(spec.input_types),
                    "output_types": list(spec.output_types),
                    "tools": list(spec.tools),
                    "invocation_profile": spec.invocation_profile or None,
                    "capability_rank": spec.capability_rank,
                    "capability_id": spec.capability_id or None,
                }
                for spec in specs
            ],
        }

    def prepare_live_session(
        self,
        *,
        user_prompt: str,
        grounding: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        providers: str | list[str] | tuple[str, ...] | None = None,
        exclude_providers: str | list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        plan = self.route_plan(
            user_prompt=user_prompt,
            output_type="live",
            grounding=grounding,
            provider=provider,
            model=model,
            providers=providers,
            exclude_providers=exclude_providers,
        )
        if not plan["models"]:
            raise UnsupportedOutputType("No Live model is configured")
        return {
            "output_type": "live",
            "route": plan["route"],
            "models": plan["models"],
            "transport": "websocket",
            "note": "Live requires a stateful WebSocket adapter; no HTTP request was made.",
        }

    def complete_auto(
        self,
        *,
        user_prompt: str,
        system_prompt: str = "",
        output_type: str = "auto",
        grounding: str | None = None,
        operation: str = "auto_completion",
        image_data: str | None = None,
        image_mime_type: str = "image/png",
        video_uri: str | None = None,
        voice: str = "Kore",
        output_dimensionality: int | None = None,
        input_parts: list[dict[str, Any]] | None = None,
        chain: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        providers: str | list[str] | tuple[str, ...] | None = None,
        exclude_providers: str | list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        intent = detect_intent(user_prompt, output_type=output_type, grounding=grounding)
        if chain:
            if grounding:
                raise ValueError("grounding cannot be combined with an explicit chain")
            try:
                specs = self.config.model_chain(chain)
            except KeyError as exc:
                raise UnsupportedOutputType(f"Unknown model chain: {chain}") from exc
            route_name = chain
        else:
            route_name, specs = self._resolve_route(intent)
        specs = self._select_specs(
            self._order_specs_by_capability(self._filter_specs(specs, providers=providers, exclude_providers=exclude_providers)),
            provider=provider,
            model=model,
        )
        if intent.output_type == "live":
            raise UnsupportedOutputType("Live is a WebSocket session; call prepare_live_session()")
        if intent.output_type == "video_generation":
            raise UnsupportedOutputType("Video generation is an asynchronous Veo job; no video-generation adapter is configured yet")
        if not specs:
            raise UnsupportedOutputType(f"No models configured for output type: {intent.output_type}")
        if intent.output_type == "video_analysis" and not video_uri:
            raise ValueError("video_uri is required for video_analysis")
        tools = build_tools(intent.grounding, latitude=latitude, longitude=longitude)
        return self._complete_route(
            specs=specs,
            route_name=route_name,
            intent=intent,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            operation=operation,
            tools=tools,
            image_data=image_data,
            image_mime_type=image_mime_type,
            video_uri=video_uri,
            voice=voice,
            output_dimensionality=output_dimensionality,
            input_parts=input_parts,
        )

    def _order_specs_by_capability(self, specs: list[ModelSpec]) -> list[ModelSpec]:
        if not specs or all(spec.capability_rank is None for spec in specs):
            return list(specs)
        indexed = list(enumerate(specs))
        return [
            spec
            for _, spec in sorted(
                indexed,
                key=lambda pair: (
                    pair[1].capability_rank if pair[1].capability_rank is not None else 10_000,
                    pair[1].capability_id,
                    list(self.config.providers).index(pair[1].provider_id),
                    pair[0],
                ),
            )
        ]

    def _select_specs(
        self,
        specs: list[ModelSpec],
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> list[ModelSpec]:
        if provider is None and model is None:
            return specs
        if not provider or not model:
            raise ValueError("provider and model must be supplied together")
        provider_ids = self._resolve_provider_ids(provider) or set()
        selected = [spec for spec in specs if spec.provider_id in provider_ids and spec.model == model]
        if not selected:
            raise ValueError(f"Selected provider/model is not available: {provider}/{model}")
        return selected

    def _record_selection(self, provider: str, model: str, route: str, operation: str) -> None:
        self._last_selection = {
            "provider": provider,
            "model": model,
            "route": route,
            "operation": operation,
        }

    def last_selection(self) -> dict[str, Any]:
        return dict(self._last_selection)

    def _resolve_provider_ids(self, selector: str | list[str] | tuple[str, ...] | None) -> set[str] | None:
        if selector is None:
            return None
        raw_items = [selector] if isinstance(selector, str) else list(selector)
        items = [item.strip().casefold() for value in raw_items for item in value.split(",") if item.strip()]
        if not items:
            raise ValueError("Provider selector cannot be empty")
        matched: set[str] = set()
        for item in items:
            if item in self.config.providers:
                matched.add(item)
                continue
            alias_ids = _PROVIDER_ALIASES.get(item)
            if alias_ids is None:
                available = ", ".join(sorted(self.config.providers))
                raise ValueError(f"Unknown provider selector '{item}'. Available provider IDs: {available}")
            matched.update(provider_id for provider_id in alias_ids if provider_id in self.config.providers)
        return matched

    def _filter_specs(
        self,
        specs: list[ModelSpec],
        *,
        providers: str | list[str] | tuple[str, ...] | None = None,
        exclude_providers: str | list[str] | tuple[str, ...] | None = None,
    ) -> list[ModelSpec]:
        allowed = self._resolve_provider_ids(providers)
        denied = self._resolve_provider_ids(exclude_providers) or set()
        if allowed is not None and allowed & denied:
            overlap = ", ".join(sorted(allowed & denied))
            raise ValueError(f"Provider is both allowed and excluded: {overlap}")
        filtered = [spec for spec in specs if (allowed is None or spec.provider_id in allowed) and spec.provider_id not in denied]
        if (providers is not None or exclude_providers is not None) and not filtered:
            raise UnsupportedOutputType("No configured models remain after provider filters")
        return filtered

    def _resolve_route(self, intent: RequestIntent) -> tuple[str, list[ModelSpec]]:
        grounded_name = f"{intent.output_type}_grounded_{intent.grounding}" if intent.grounding else intent.output_type
        if grounded_name in self.config.output_routes:
            return grounded_name, self.config.output_route(intent.output_type, grounding=intent.grounding)
        if intent.grounding:
            base = self.config.output_route(intent.output_type)
            supported = [spec for spec in base if intent.grounding in spec.tools]
            if supported:
                return f"{intent.output_type}_filtered_{intent.grounding}", supported
            raise UnsupportedOutputType(f"No configured model supports grounding tool: {intent.grounding}")
        if intent.output_type in self.config.output_routes:
            return intent.output_type, self.config.output_route(intent.output_type)
        if intent.output_type == "text":
            return "default", self.config.model_chain("default")
        raise UnsupportedOutputType(f"No configured output route: {intent.output_type}")

    def _complete_route(
        self,
        *,
        specs: list[ModelSpec],
        route_name: str,
        intent: RequestIntent,
        system_prompt: str,
        user_prompt: str,
        operation: str,
        tools: list[dict[str, Any]],
        image_data: str | None,
        image_mime_type: str,
        video_uri: str | None,
        voice: str,
        output_dimensionality: int | None,
        input_parts: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        errors: list[str] = []
        attempts = 0
        for spec in specs:
            provider_spec = self.config.providers[spec.provider_id]
            adapter = self.adapters[spec.provider_id]
            provider_models = [item.model for item in specs if item.provider_id == spec.provider_id]
            model_index = provider_models.index(spec.model)
            keys = self._ordered_keys(
                provider=spec.provider_id,
                chain=route_name,
                model=spec.model,
                model_names=provider_models,
                model_index=model_index,
            )
            for key in keys:
                if attempts >= self.config.policy.max_attempts:
                    break
                attempts += 1
                if self.store.is_cooling(spec.provider_id, spec.model, key.key_id, key.project):
                    continue
                try:
                    response = self._invoke_output(
                        spec=spec,
                        adapter=adapter,
                        secret=key.secret,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        timeout_seconds=provider_spec.timeout_seconds or self.config.policy.request_timeout_seconds,
                        tools=tools if not intent.grounding or intent.grounding in spec.tools else [],
                        image_data=image_data,
                        image_mime_type=image_mime_type,
                        video_uri=video_uri,
                        voice=voice,
                        output_dimensionality=output_dimensionality,
                        input_parts=input_parts,
                        supports_response_format=spec.supports_response_format,
                        invocation_profile=self.config.invocation_profile(spec) if isinstance(adapter, OpenAICompatibleAdapter) else {},
                    )
                    self.store.record_success(
                        provider=spec.provider_id,
                        model=spec.model,
                        key_id=key.key_id,
                        project=key.project,
                        operation=operation,
                        usage=response.usage,
                    )
                    existing_urls = response.payload.get("url_citations", [])
                    normalized_urls: list[str] = []
                    for url in [*(existing_urls if isinstance(existing_urls, list) else []), *url_citations_from_annotations(response.payload), *url_citations_from_text(response.payload.get("text") or response.payload.get("provider_text") or "")]:
                        if url not in normalized_urls:
                            normalized_urls.append(url)
                    response.payload["url_citations"] = normalized_urls
                    response.payload.setdefault("output_type", intent.output_type)
                    if intent.grounding == "search" and intent.output_type == "text" and not normalized_urls:
                        raise ProviderError(
                            "Grounded search returned no URL citations",
                            error_class="invalid_or_unknown",
                            retryable=True,
                        )
                    response.payload["route"] = route_name
                    response.payload["intent"] = intent.output_type
                    response.payload["provider"] = spec.provider_id
                    response.payload["model"] = spec.model
                    self._record_selection(spec.provider_id, spec.model, route_name, operation)
                    return validate_response_envelope(response.payload)
                except ProviderError as exc:
                    errors.append(f"{spec.provider_id}/{spec.model}/{key.key_id}: {exc.error_class}/{exc.status_code or '-'}: {exc}")
                    # Missing citations and invalid JSON are operation-specific contract failures,
                    # not provider outages. Do not cool the key before the next independent search.
                    cooldown = 0 if exc.error_class == "invalid_or_unknown" else self.config.policy.cooldowns_seconds.get(exc.error_class, 300)
                    self.store.record_failure(
                        provider=spec.provider_id,
                        model=spec.model,
                        key_id=key.key_id,
                        project=key.project,
                        operation=operation,
                        error_class=exc.error_class,
                        message=str(exc),
                        status_code=exc.status_code,
                        cooldown_seconds=cooldown,
                    )
                    self.store.advance_model_cursor(
                        provider=spec.provider_id,
                        chain=route_name,
                        key_id=key.key_id,
                        project=key.project,
                        model_names=provider_models,
                        current_index=model_index,
                        error_class=exc.error_class,
                    )
                    if exc.retryable:
                        time.sleep(min(2.0, self._backoff(attempts)))
            if attempts >= self.config.policy.max_attempts:
                break
        self.store.checkpoint()
        visible_errors = errors if len(errors) <= 24 else [*errors[:6], f"... {len(errors) - 18} intermediate attempts omitted ...", *errors[-12:]]
        raise AllProvidersFailed("All output-route attempts failed: " + " | ".join(visible_errors))

    @staticmethod
    def _invoke_output(
        *,
        spec: ModelSpec,
        adapter: ProviderAdapter,
        secret: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: int,
        tools: list[dict[str, Any]],
        image_data: str | None,
        image_mime_type: str,
        video_uri: str | None,
        voice: str,
        output_dimensionality: int | None,
        input_parts: list[dict[str, Any]] | None,
        supports_response_format: bool = True,
        invocation_profile: dict[str, Any] | None = None,
    ) -> Any:
        if spec.method == "json":
            return adapter.complete_json(
                model=spec.model,
                secret=secret,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_seconds=timeout_seconds,
                supports_response_format=supports_response_format,
                invocation_profile=invocation_profile or {},
            )
        if spec.method == "translation":
            return adapter.complete_text(
                model=spec.model,
                secret=secret,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_seconds=timeout_seconds,
            )
        if spec.method == "grounded_text":
            return adapter.complete_grounded_text(
                model=spec.model,
                secret=secret,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_seconds=timeout_seconds,
                tools=tools,
            )
        if spec.method == "interaction_text":
            return adapter.complete_interaction_text(
                model=spec.model,
                secret=secret,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_seconds=timeout_seconds,
                tools=tools,
            )
        if spec.method == "image":
            return adapter.generate_image(
                model=spec.model,
                secret=secret,
                prompt=user_prompt,
                timeout_seconds=timeout_seconds,
                image_data=image_data,
                image_mime_type=image_mime_type,
                tools=tools,
            )
        if spec.method == "tts":
            return adapter.generate_speech(
                model=spec.model,
                secret=secret,
                text=user_prompt,
                timeout_seconds=timeout_seconds,
                voice=voice,
            )
        if spec.method == "embedding":
            return adapter.embed_content(
                model=spec.model,
                secret=secret,
                text=user_prompt,
                timeout_seconds=timeout_seconds,
                output_dimensionality=output_dimensionality,
                content_parts=input_parts,
            )
        if spec.method == "video_analysis":
            if not video_uri:
                raise ValueError("video_uri is required for video_analysis")
            return adapter.complete_video_json(
                model=spec.model,
                secret=secret,
                video_uri=video_uri,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_seconds=timeout_seconds,
                tools=tools,
            )
        raise UnsupportedOutputType(f"Method {spec.method} is not executable by the current adapter")

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
        return {
            "config": self.config.public_summary(),
            "state": self.store.stats(),
            "last_selection": self.last_selection(),
        }

    def close(self) -> None:
        self.store.checkpoint()

    def _backoff(self, attempt: int) -> int:
        values = self.config.policy.backoff_seconds
        return values[min(max(attempt - 1, 0), len(values) - 1)] if values else 0
