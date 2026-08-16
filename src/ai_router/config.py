from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    kind: str
    base_url: str
    key_pool: str
    enabled: bool
    timeout_seconds: int


@dataclass(frozen=True)
class ModelSpec:
    provider_id: str
    model: str
    enabled: bool
    method: str = "json"
    input_types: tuple[str, ...] = ("text",)
    output_types: tuple[str, ...] = ("text",)
    tools: tuple[str, ...] = ()
    supports_response_format: bool = True


@dataclass(frozen=True)
class KeySpec:
    key_id: str
    secret: str
    project: str = "default"


@dataclass(frozen=True)
class RouterPolicy:
    max_attempts: int
    request_timeout_seconds: int
    cooldowns_seconds: dict[str, int]
    backoff_seconds: list[int]


class RouterConfig:
    def __init__(self, root: Path, providers: dict[str, ProviderSpec], chains: dict[str, list[ModelSpec]], output_routes: dict[str, list[ModelSpec]], key_pools: dict[str, str], fallback_envs: dict[str, str], key_pool_rotations: dict[str, str], policy: RouterPolicy) -> None:
        self.root = root
        self.providers = providers
        self.chains = chains
        self.output_routes = output_routes
        self.key_pools = key_pools
        self.fallback_envs = fallback_envs
        self.key_pool_rotations = key_pool_rotations
        self.policy = policy

    @classmethod
    def load(cls, root: str | Path | None = None) -> RouterConfig:
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env", override=False)
        config_root = Path(root or os.getenv("AI_ROUTER_CONFIG_DIR", project_root / "config")).resolve()
        providers_raw = cls._read_json(config_root / "providers.json")
        models_raw = cls._read_json(config_root / "models.json")
        keys_raw = cls._read_json(config_root / "key_pools.json")
        policy_raw = cls._read_json(config_root / "policies.json")

        providers = {
            item["id"]: ProviderSpec(
                provider_id=item["id"],
                kind=item["kind"],
                base_url=item["base_url"].rstrip("/"),
                key_pool=item["key_pool"],
                enabled=bool(item.get("enabled", True)),
                timeout_seconds=int(item.get("default_timeout_seconds", 90)),
            )
            for item in providers_raw.get("providers", [])
        }
        def parse_specs(items: list[dict[str, Any]]) -> list[ModelSpec]:
            return [
                ModelSpec(
                    provider_id=str(item["provider"]),
                    model=str(item["model"]),
                    enabled=bool(item.get("enabled", True)),
                    method=str(item.get("method", "json")),
                    input_types=tuple(str(value) for value in item.get("input_types", ["text"])),
                    output_types=tuple(str(value) for value in item.get("output_types", ["text"])),
                    tools=tuple(str(value) for value in item.get("tools", [])),
                    supports_response_format=bool(item.get("supports_response_format", True)),
                )
                for item in items
            ]

        chains: dict[str, list[ModelSpec]] = {
            chain_name: parse_specs(items)
            for chain_name, items in models_raw.get("model_chains", {}).items()
        }
        output_routes: dict[str, list[ModelSpec]] = {
            route_name: parse_specs(items)
            for route_name, items in models_raw.get("output_routes", {}).items()
        }
        key_pools = {
            pool_id: str(pool.get("env", ""))
            for pool_id, pool in keys_raw.get("key_pools", {}).items()
        }
        fallback_envs = {
            pool_id: str(pool.get("fallback_env"))
            for pool_id, pool in keys_raw.get("key_pools", {}).items()
            if pool.get("fallback_env")
        }
        key_pool_rotations = {
            pool_id: str(pool.get("rotation", "ordered"))
            for pool_id, pool in keys_raw.get("key_pools", {}).items()
        }
        defaults = policy_raw.get("defaults", {})
        policy = RouterPolicy(
            max_attempts=max(1, int(defaults.get("max_attempts", 24))),
            request_timeout_seconds=max(15, int(defaults.get("request_timeout_seconds", 90))),
            cooldowns_seconds={key: int(value) for key, value in defaults.get("cooldowns_seconds", {}).items()},
            backoff_seconds=[int(value) for value in defaults.get("backoff_seconds", [1, 2, 4, 8])],
        )
        config = cls(config_root, providers, chains, output_routes, key_pools, fallback_envs, key_pool_rotations, policy)
        config.validate()
        return config

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def validate(self) -> None:
        if "default" not in self.chains:
            raise ValueError("config/models.json must define a default model chain")
        for provider in self.providers.values():
            if provider.key_pool not in self.key_pools:
                raise ValueError(f"Provider {provider.provider_id} references unknown key pool {provider.key_pool}")
        for collection_name, collection in {**self.chains, **self.output_routes}.items():
            for item in collection:
                if item.provider_id not in self.providers:
                    raise ValueError(f"Model route {collection_name} references unknown provider {item.provider_id}")

    def model_chain(self, name: str = "default") -> list[ModelSpec]:
        if name not in self.chains:
            raise KeyError(f"Unknown model chain: {name}")
        return [item for item in self.chains[name] if item.enabled and self.providers[item.provider_id].enabled]

    def output_route(self, output_type: str, *, grounding: str | None = None) -> list[ModelSpec]:
        route_name = f"{output_type}_grounded_{grounding}" if grounding else output_type
        if route_name not in self.output_routes:
            raise KeyError(f"Unknown output route: {route_name}")
        return [item for item in self.output_routes[route_name] if item.enabled and self.providers[item.provider_id].enabled]

    def keys_for(self, provider_id: str) -> list[KeySpec]:
        provider = self.providers[provider_id]
        env_name = self.key_pools[provider.key_pool]
        raw = os.getenv(env_name, "").strip()
        fallback_env = self.fallback_envs.get(provider.key_pool)
        if not raw or raw == "[]":
            raw = os.getenv(fallback_env, "").strip() if fallback_env else ""
        if not raw:
            return []
        try:
            values = json.loads(raw)
        except json.JSONDecodeError:
            values = [{"id": f"{provider_id}-fallback-1", "key": raw, "project": "default"}]
        if isinstance(values, str) and values.strip():
            values = [{"id": f"{provider_id}-fallback-1", "key": values.strip(), "project": "default"}]
        if isinstance(values, dict):
            # Accept the documented array and common secret-wrapper forms without
            # changing the ordered rotation semantics.
            values = values.get("keys") or values.get("items") or values.get("entries") or [values]
        if not isinstance(values, list):
            raise TypeError(f"{env_name} or fallback token must be a JSON array or a single token")
        result: list[KeySpec] = []
        aliases = ("key", "api_key", "token", "secret", "value")
        for index, value in enumerate(values):
            if isinstance(value, str) and value.strip():
                result.append(KeySpec(f"{provider_id}-{index + 1}", value.strip()))
            elif isinstance(value, dict):
                secret = next((value.get(alias) for alias in aliases if value.get(alias)), None)
                if secret:
                    result.append(KeySpec(str(value.get("id") or value.get("name") or f"{provider_id}-{index + 1}"), str(secret).strip(), str(value.get("project") or "default")))
        return result

    def public_summary(self) -> dict[str, Any]:
        return {
            "config_dir": str(self.root),
            "providers": [provider.provider_id for provider in self.providers.values() if provider.enabled],
            "chains": {name: [{"provider": item.provider_id, "model": item.model} for item in chain if item.enabled] for name, chain in self.chains.items()},
            "output_routes": {name: [{"provider": item.provider_id, "model": item.model, "method": item.method} for item in route if item.enabled] for name, route in self.output_routes.items()},
            "key_pools": list(self.key_pools),
            "key_pool_rotations": dict(self.key_pool_rotations),
            "secrets_loaded": {provider_id: len(self.keys_for(provider_id)) for provider_id in self.providers},
        }
