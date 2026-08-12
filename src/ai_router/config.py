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
    def __init__(self, root: Path, providers: dict[str, ProviderSpec], chains: dict[str, list[ModelSpec]], key_pools: dict[str, str], policy: RouterPolicy) -> None:
        self.root = root
        self.providers = providers
        self.chains = chains
        self.key_pools = key_pools
        self.policy = policy

    @classmethod
    def load(cls, root: str | Path | None = None) -> "RouterConfig":
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
        chains: dict[str, list[ModelSpec]] = {}
        for chain_name, items in models_raw.get("model_chains", {}).items():
            chains[chain_name] = [
                ModelSpec(str(item["provider"]), str(item["model"]), bool(item.get("enabled", True)))
                for item in items
            ]
        key_pools = {
            pool_id: str(pool.get("env", ""))
            for pool_id, pool in keys_raw.get("key_pools", {}).items()
        }
        defaults = policy_raw.get("defaults", {})
        policy = RouterPolicy(
            max_attempts=max(1, int(defaults.get("max_attempts", 24))),
            request_timeout_seconds=max(15, int(defaults.get("request_timeout_seconds", 90))),
            cooldowns_seconds={key: int(value) for key, value in defaults.get("cooldowns_seconds", {}).items()},
            backoff_seconds=[int(value) for value in defaults.get("backoff_seconds", [1, 2, 4, 8])],
        )
        config = cls(config_root, providers, chains, key_pools, policy)
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
        for chain_name, chain in self.chains.items():
            for item in chain:
                if item.provider_id not in self.providers:
                    raise ValueError(f"Model chain {chain_name} references unknown provider {item.provider_id}")

    def model_chain(self, name: str = "default") -> list[ModelSpec]:
        if name not in self.chains:
            raise KeyError(f"Unknown model chain: {name}")
        return [item for item in self.chains[name] if item.enabled and self.providers[item.provider_id].enabled]

    def keys_for(self, provider_id: str) -> list[KeySpec]:
        provider = self.providers[provider_id]
        env_name = self.key_pools[provider.key_pool]
        raw = os.getenv(env_name, "").strip()
        if not raw:
            return []
        try:
            values = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{env_name} must contain a JSON array") from exc
        if not isinstance(values, list):
            raise ValueError(f"{env_name} must contain a JSON array")
        result: list[KeySpec] = []
        for index, value in enumerate(values):
            if isinstance(value, str) and value.strip():
                result.append(KeySpec(f"{provider_id}-{index + 1}", value.strip()))
            elif isinstance(value, dict) and value.get("key"):
                result.append(KeySpec(str(value.get("id") or f"{provider_id}-{index + 1}"), str(value["key"]).strip(), str(value.get("project") or "default")))
        return result

    def public_summary(self) -> dict[str, Any]:
        return {
            "config_dir": str(self.root),
            "providers": [provider.provider_id for provider in self.providers.values() if provider.enabled],
            "chains": {name: [{"provider": item.provider_id, "model": item.model} for item in chain if item.enabled] for name, chain in self.chains.items()},
            "key_pools": list(self.key_pools),
            "secrets_loaded": {provider_id: len(self.keys_for(provider_id)) for provider_id in self.providers},
        }
