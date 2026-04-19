import os

from apis.types import ProviderInfo
from apis.OpenRouter.query_model import query_model as query_openrouter
from apis.OpenAI.query_model import query_model as query_openai
from apis.Ollama.query_model import query_model as query_ollama
from apis.Codex.query_model import query_model as query_codex
from apis.Claude.query_model import query_model as query_claude


def _provider_enabled(config, provider_key, default=True):
    providers_cfg = config.get("providers", {})
    provider_cfg = providers_cfg.get(provider_key, {})
    return provider_cfg.get("enabled", default)


def _provider_roles(config, provider_key, default_roles):
    providers_cfg = config.get("providers", {})
    provider_cfg = providers_cfg.get(provider_key, {})
    return provider_cfg.get("roles", default_roles)


def _provider_priority(config, provider_key, default_priority):
    providers_cfg = config.get("providers", {})
    provider_cfg = providers_cfg.get(provider_key, {})
    return provider_cfg.get("priority", default_priority)


def discover_available_providers(config):
    providers = []

    if (
        _provider_enabled(config, "openrouter") and
        os.getenv("OPENROUTER_API_KEY", "").strip()
    ):
        providers.append(ProviderInfo(
            name="OpenRouter",
            available=True,
            roles=_provider_roles(config, "openrouter", ["generate"]),
            priority=_provider_priority(config, "openrouter", 40),
            query_fn=query_openrouter,
        ))

    if (
        _provider_enabled(config, "openai") and
        os.getenv("OPENAI_API_KEY", "").strip()
    ):
        providers.append(ProviderInfo(
            name="OpenAI",
            available=True,
            roles=_provider_roles(
                config, "openai", ["generate", "judge", "refine"]
            ),
            priority=_provider_priority(config, "openai", 70),
            query_fn=query_openai,
        ))

    if (
        _provider_enabled(config, "codex") and
        os.getenv("CODEX_API_KEY", "").strip()
    ):
        providers.append(ProviderInfo(
            name="Codex",
            available=True,
            roles=_provider_roles(
                config, "codex", ["generate", "judge", "refine"]
            ),
            priority=_provider_priority(config, "codex", 100),
            query_fn=query_codex,
        ))

    if (
        _provider_enabled(config, "claude") and
        os.getenv("ANTHROPIC_API_KEY", "").strip()
    ):
        providers.append(ProviderInfo(
            name="Claude",
            available=True,
            roles=_provider_roles(
                config, "claude", ["generate", "judge", "refine"]
            ),
            priority=_provider_priority(config, "claude", 95),
            query_fn=query_claude,
        ))

    if (
        _provider_enabled(config, "ollama") and
        os.getenv("OLLAMA_MODEL", config.get("ollama_model", "")).strip()
    ):
        providers.append(ProviderInfo(
            name="Ollama",
            available=True,
            roles=_provider_roles(config, "ollama", ["generate"]),
            priority=_provider_priority(config, "ollama", 30),
            query_fn=query_ollama,
        ))

    return providers


def get_available_provider_pairs(config):
    return [
        (provider.name, provider.query_fn)
        for provider in discover_available_providers(config)
    ]
