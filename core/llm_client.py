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
    LLM_PROVIDER = "openai"     →  uses openai SDK

You can also mix providers per call by passing provider= explicitly:
    chat(model="llama-3.3-70b-versatile", provider="groq", ...)
"""

import logging
import threading
from typing import Literal

from config.settings import (
    ANTHROPIC_API_KEY,
    GROQ_API_KEYS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)

logger = logging.getLogger(__name__)

Provider = Literal["anthropic", "groq", "openai"]

# ─── Lazy client singletons ───────────────────────────────────────────────────

_anthropic_client = None
_groq_clients = []
_groq_lock = threading.Lock()
_groq_index = 0
_openai_client = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client


def _get_groq():
    global _groq_clients, _groq_index, _groq_lock
    if not _groq_clients:
        from groq import Groq
        for key in GROQ_API_KEYS:
            if key:
                _groq_clients.append(Groq(api_key=key))
        if not _groq_clients:
            _groq_clients.append(Groq(api_key=""))
    
    with _groq_lock:
        client = _groq_clients[_groq_index]
        key_snippet = client.api_key[-4:] if client.api_key and len(client.api_key) >= 4 else "None"
        logger.info(f"[LLM] Round-Robin: Using Groq API key ending in ...{key_snippet} (Index: {_groq_index + 1}/{len(_groq_clients)})")
        _groq_index = (_groq_index + 1) % len(_groq_clients)
        return client


def _get_openai():
    global _openai_client
    if _openai_client is None:
        import openai
        args = {"api_key": OPENAI_API_KEY}
        if OPENAI_BASE_URL:
            args["base_url"] = OPENAI_BASE_URL
        _openai_client = openai.OpenAI(**args)
    return _openai_client


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
        provider:   "anthropic", "groq", or "openai". MUST be specified.

    Returns:
        Response text string.

    Raises:
        RuntimeError: If the provider is unsupported or the API call fails.
    """
    if not provider:
        raise ValueError("provider MUST be explicitly passed to llm_chat now.")

    logger.debug(f"[LLM] {provider}/{model} — max_tokens={max_tokens}")

    if provider == "anthropic":
        return _call_anthropic(model, system, user, max_tokens)
    elif provider == "groq":
        return _call_groq(model, system, user, max_tokens)
    elif provider == "openai":
        return _call_openai(model, system, user, max_tokens)
    else:
        raise RuntimeError(
            f"[LLM] Unknown provider: '{provider}'."
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


def _call_openai(model: str, system: str, user: str, max_tokens: int) -> str:
    client = _get_openai()
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content.strip()
