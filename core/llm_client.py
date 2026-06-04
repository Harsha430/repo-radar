"""
core/llm_client.py — Unified LLM client supporting Anthropic (Claude) and Groq.

Usage:
    from core.llm_client import chat

    text = chat(
        model=RESEARCH_MODEL,
        system="You are...",
        user="Analyse this...",
        max_tokens=2000,
    )

Provider is selected automatically based on LLM_PROVIDER in settings.py:
    LLM_PROVIDER = "anthropic"  →  uses anthropic SDK
    LLM_PROVIDER = "groq"       →  uses groq SDK (OpenAI-compatible)

You can also mix providers per call by passing provider= explicitly:
    chat(model="llama-3.3-70b-versatile", provider="groq", ...)
"""

import logging
from typing import Literal

from config.settings import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    GROQ_API_KEY,
)

logger = logging.getLogger(__name__)

Provider = Literal["anthropic", "groq"]

# ─── Lazy client singletons ───────────────────────────────────────────────────

_anthropic_client = None
_groq_client = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


# ─── Unified chat function ────────────────────────────────────────────────────

def chat(
    model: str,
    system: str,
    user: str,
    max_tokens: int = 2000,
    provider: Provider | None = None,
) -> str:
    """
    Call an LLM and return the text response.

    Args:
        model:      Model identifier string (provider-specific)
        system:     System prompt
        user:       User message
        max_tokens: Max tokens in response
        provider:   "anthropic" or "groq". Defaults to LLM_PROVIDER from settings.

    Returns:
        Response text string.

    Raises:
        RuntimeError: If the provider is unsupported or the API call fails.
    """
    resolved_provider: Provider = provider or LLM_PROVIDER  # type: ignore[assignment]

    logger.debug(f"[LLM] {resolved_provider}/{model} — max_tokens={max_tokens}")

    if resolved_provider == "anthropic":
        return _call_anthropic(model, system, user, max_tokens)
    elif resolved_provider == "groq":
        return _call_groq(model, system, user, max_tokens)
    else:
        raise RuntimeError(
            f"[LLM] Unknown provider: '{resolved_provider}'. "
            "Set LLM_PROVIDER to 'anthropic' or 'groq' in config/settings.py"
        )


# ─── Provider implementations ─────────────────────────────────────────────────

def _call_anthropic(model: str, system: str, user: str, max_tokens: int) -> str:
    client = _get_anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def _call_groq(model: str, system: str, user: str, max_tokens: int) -> str:
    client = _get_groq()
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content.strip()
