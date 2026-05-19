"""LLM factory and JSON extraction helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlsplit

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # type: ignore


if ChatOpenAI is not None:

    class ChatOpenAIWithReasoning(ChatOpenAI):  # type: ignore[misc,valid-type]
        """ChatOpenAI that preserves provider reasoning across invoke + stream.

        langchain-openai 0.3.x drops non-standard fields in three paths:
          * _convert_dict_to_message — invoke / ainvoke (inbound)
          * _convert_delta_to_message_chunk — stream / astream (inbound)
          * _convert_message_to_dict — request serialization (outbound)
        Moonshot/DeepSeek emit `reasoning_content`; OpenRouter relays as
        `reasoning`. Inbound paths normalize to additional_kwargs["reasoning_content"];
        outbound path re-injects it so strict providers (kimi-k2.5) accept
        multi-turn continuations.
        """

        @staticmethod
        def _capture(src: Any, msg: Any) -> None:
            if value := src.get("reasoning_content") or src.get("reasoning"):
                msg.additional_kwargs["reasoning_content"] = value

        def _create_chat_result(self, response, generation_info=None):  # type: ignore[override]
            result = super()._create_chat_result(response, generation_info)
            raw = response if isinstance(response, dict) else response.model_dump()
            for gen, choice in zip(result.generations, raw["choices"]):
                self._capture(choice["message"], gen.message)
            return result

        def _convert_chunk_to_generation_chunk(  # type: ignore[override]
            self,
            chunk: dict,
            default_chunk_class: type,
            base_generation_info: Optional[dict],
        ):
            gen = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
            if gen is None:
                return None
            choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices")
            if choices:
                self._capture(choices[0]["delta"], gen.message)
            return gen

        def _get_request_payload(  # type: ignore[override]
            self,
            input_: Any,
            *,
            stop: Optional[list[str]] = None,
            **kwargs: Any,
        ) -> dict:
            """Re-inject reasoning_content and normalize assistant content.

            LangChain strips ``reasoning_content`` when serializing AIMessages
            back to OpenAI wire format. Moonshot kimi-k2.5 also rejects
            assistant turns where ``content`` is null or ``reasoning_content``
            is absent, breaking ReAct continuations after a tool call (#39).
            """
            payload = super()._get_request_payload(input_, stop=stop, **kwargs)
            messages = super()._convert_input(input_).to_messages()
            for i, m in enumerate(payload["messages"]):
                if m.get("role") != "assistant":
                    continue
                if m.get("content") is None:
                    m["content"] = ""
                m["reasoning_content"] = messages[i].additional_kwargs.get("reasoning_content", "")
            return payload
else:
    ChatOpenAIWithReasoning = None  # type: ignore

AGENT_DIR = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)

DEFAULT_CODEX_URL = "https://chatgpt.com/backend-api/codex/responses"
DEFAULT_FALLBACK_CHAIN = ("openrouter", "openai-codex")
DEFAULT_FALLBACK_MODELS = {
    "openrouter": "deepseek/deepseek-v3.2",
    "groq": "llama-3.3-70b-versatile",
    "openai-codex": "openai-codex/gpt-5.3-codex",
}
RETRYABLE_STATUS_CODES = ("429", "402", "500", "502", "503", "504")
RETRYABLE_ERROR_MARKERS = (
    "rate limit",
    "rate_limit",
    "quota",
    "insufficient_quota",
    "overloaded",
    "temporarily unavailable",
    "capacity",
    "timeout",
    "timed out",
)
NON_RETRYABLE_ERROR_MARKERS = (
    "invalid api key",
    "incorrect api key",
    "unauthorized",
    "authentication",
    "permission denied",
    "not logged in",
    "provider login openai-codex",
    "bad request",
    "invalid request",
    "unsupported model",
    "content policy",
    "content_filter",
)

PROVIDER_MAP: dict[str, tuple[str | None, str]] = {
    "openai": ("OPENAI_API_KEY", "OPENAI_BASE_URL"),
    "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL"),
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_BASE_URL"),
    "groq": ("GROQ_API_KEY", "GROQ_BASE_URL"),
    "dashscope": ("DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL"),
    "qwen": ("DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL"),
    "zhipu": ("ZHIPU_API_KEY", "ZHIPU_BASE_URL"),
    "moonshot": ("MOONSHOT_API_KEY", "MOONSHOT_BASE_URL"),
    "minimax": ("MINIMAX_API_KEY", "MINIMAX_BASE_URL"),
    "mimo": ("MIMO_API_KEY", "MIMO_BASE_URL"),
    "zai": ("ZAI_API_KEY", "ZAI_BASE_URL"),
    "ollama": (None, "OLLAMA_BASE_URL"),
}

# .env search order: ~/.vibe-trading/.env → agent/.env → $CWD/.env
_ENV_CANDIDATES = [
    Path.home() / ".vibe-trading" / ".env",
    AGENT_DIR / ".env",
    Path.cwd() / ".env",
]

# Index-aligned with _ENV_CANDIDATES. CWE-209: never log the absolute
# .env path (it leaks the OS username / home / CWD). The label names
# which slot won - the entire P08 R1 signal - using compile-time
# constants only.
_ENV_LABELS = ("~/.vibe-trading/.env", "<AGENT_DIR>/.env", "<CWD>/.env")

logger = logging.getLogger(__name__)

_dotenv_loaded: bool = False


def _redact_env_source(loaded: Path | None) -> str:
    """Map a resolved `.env` candidate to a stable, leak-free label.

    Returns a symbolic slot label (never the absolute path) so a stale
    or shadowed `.env` stays diagnosable without exposing the OS
    username, home, or CWD (CWE-209). A candidate outside the fixed
    list (e.g. one injected by a test) collapses to a generic
    placeholder rather than echoing a real path.
    """
    if loaded is None:
        return "none (no .env file found)"
    for label, candidate in zip(_ENV_LABELS, _ENV_CANDIDATES):
        if loaded == candidate:
            return label
    return "<.env>"


def _redact_base_url_for_log(raw: str | None) -> str:
    """Return a diagnostic-safe base URL label for logs."""
    if not raw or not raw.strip():
        return "(unset)"

    try:
        parsed = urlsplit(raw.strip())
    except ValueError:
        return "<base-url>"

    if not parsed.scheme or not parsed.hostname:
        return "<base-url>"

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    try:
        port = parsed.port
    except ValueError:
        port = None
    if port is not None:
        host = f"{host}:{port}"

    return f"{parsed.scheme}://{host}"


def _load_env_file(path: Path) -> None:
    """Load a single .env file into os.environ (setdefault, no override)."""
    if load_dotenv is not None:
        load_dotenv(dotenv_path=path, override=False)
    else:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key:
                os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def _ensure_dotenv() -> None:
    """Load `.env` from the first found candidate path."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    loaded = None
    for candidate in _ENV_CANDIDATES:
        if candidate.exists():
            _load_env_file(candidate)
            loaded = candidate
            break
    _dotenv_loaded = True
    # P08 R1: one-time, behavior-preserving diagnostic so a stale or
    # shadowed .env is observable instead of costing hours. The path is
    # redacted to a symbolic slot label and the API key is never logged.
    logger.info(
        "dotenv resolved from %s | provider=%s model=%s base=%s",
        _redact_env_source(loaded),
        os.getenv("LANGCHAIN_PROVIDER", "(unset)"),
        os.getenv("LANGCHAIN_MODEL_NAME", "(unset)"),
        _redact_base_url_for_log(os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")),
    )


def _normalize_ollama_base_url(base_url: str) -> str:
    """Append ``/v1`` when missing so ChatOpenAI hits Ollama's OpenAI-compatible API."""
    url = base_url.strip().rstrip("/")
    if not url:
        return url
    if url.endswith("/v1"):
        return url
    return f"{url}/v1"


def _sync_provider_env() -> None:
    """Map provider-specific env vars to OPENAI_* for ChatOpenAI.

    Each entry: provider_name -> (api_key_env, base_url_env).
    All base URLs must be set explicitly in .env — no hardcoded defaults.
    api_key_env=None means no key required (e.g. Ollama local).
    """
    _ensure_dotenv()
    provider = os.getenv("LANGCHAIN_PROVIDER", "openai").lower()

    if provider in {"openai-codex", "openai_codex"}:
        codex_url = os.getenv("OPENAI_CODEX_BASE_URL", DEFAULT_CODEX_URL)
        os.environ["OPENAI_API_BASE"] = codex_url
        os.environ["OPENAI_BASE_URL"] = codex_url
        os.environ.pop("OPENAI_API_KEY", None)
        return

    spec = PROVIDER_MAP.get(provider, PROVIDER_MAP["openai"])
    key_env, base_env = spec

    # Resolve API key: provider-specific env → OPENAI_API_KEY fallback
    if key_env is not None:
        api_key = os.getenv(key_env, "") or os.getenv("OPENAI_API_KEY", "")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "") or "ollama"

    # Resolve base URL: provider-specific env → OPENAI_BASE_URL fallback
    base_url = os.getenv(base_env, "") or os.getenv("OPENAI_BASE_URL", "") or os.getenv("OPENAI_API_BASE", "")
    if provider == "ollama" and base_url:
        base_url = _normalize_ollama_base_url(base_url)

    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["OPENAI_API_BASE"] = base_url
        os.environ.setdefault("OPENAI_BASE_URL", base_url)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _provider_env(provider: str) -> tuple[str, str]:
    normalized = provider.replace("_", "-").lower()
    if normalized == "openai-codex":
        return "", os.getenv("OPENAI_CODEX_BASE_URL", DEFAULT_CODEX_URL)

    key_env, base_env = PROVIDER_MAP.get(normalized, PROVIDER_MAP["openai"])
    if key_env is not None:
        api_key = os.getenv(key_env, "") or os.getenv("OPENAI_API_KEY", "")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "") or "ollama"
    base_url = os.getenv(base_env, "") or os.getenv("OPENAI_BASE_URL", "") or os.getenv("OPENAI_API_BASE", "")
    return api_key, base_url


def _apply_provider_env(provider: str) -> None:
    api_key, base_url = _provider_env(provider)
    if provider.replace("_", "-").lower() == "openai-codex":
        os.environ.pop("OPENAI_API_KEY", None)
    elif api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if base_url:
        os.environ["OPENAI_API_BASE"] = base_url
        os.environ["OPENAI_BASE_URL"] = base_url


def _fallback_model_env(provider: str) -> str:
    return provider.replace("-", "_").upper() + "_FALLBACK_MODEL"


@dataclass(frozen=True)
class LLMCandidate:
    provider: str
    model: str


def _fallback_chain(primary_provider: str, primary_model: str) -> list[LLMCandidate]:
    raw_chain = os.getenv("LLM_FALLBACK_CHAIN", ",".join(DEFAULT_FALLBACK_CHAIN))
    chain = [item.strip().replace("_", "-").lower() for item in raw_chain.split(",") if item.strip()]
    if not chain:
        return [LLMCandidate(primary_provider, primary_model)]

    primary = primary_provider.replace("_", "-").lower()
    if primary not in chain or primary != chain[0]:
        return [LLMCandidate(primary, primary_model)]

    ordered = list(chain)
    candidates: list[LLMCandidate] = []
    for provider in ordered:
        default_model = DEFAULT_FALLBACK_MODELS.get(provider, primary_model)
        model = os.getenv(_fallback_model_env(provider), "").strip() or default_model
        if provider == primary:
            model = primary_model
        candidates.append(LLMCandidate(provider, model))
    return candidates


def _is_retryable_llm_error(exc: Exception) -> bool:
    text = str(exc).lower()
    if any(marker in text for marker in NON_RETRYABLE_ERROR_MARKERS):
        return False
    if any(
        f"http {code}" in text or f"status {code}" in text or f" {code} " in text for code in RETRYABLE_STATUS_CODES
    ):
        return True
    return any(marker in text for marker in RETRYABLE_ERROR_MARKERS)


def _sanitize_error(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    return text[:240] + ("..." if len(text) > 240 else "")


def _build_provider_llm(
    *,
    provider: str,
    model_name: str,
    callbacks: Any = None,
    tools: Optional[list[dict[str, Any]]] = None,
) -> Any:
    provider = provider.replace("_", "-").lower()
    temperature = float(os.getenv("LANGCHAIN_TEMPERATURE", "0.0"))
    timeout = int(os.getenv("TIMEOUT_SECONDS", "120"))
    effort = os.getenv("LANGCHAIN_REASONING_EFFORT", "").strip().lower()
    api_key, base_url = _provider_env(provider)
    _apply_provider_env(provider)

    if provider == "openai-codex":
        from src.providers.openai_codex import OpenAICodexLLM

        return OpenAICodexLLM(
            model=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            reasoning_effort=effort or None,
        )

    if ChatOpenAI is None:
        raise RuntimeError("langchain-openai is not installed")
    if provider == "minimax" and temperature <= 0.0:
        temperature = 0.01
    kwargs: dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
        "timeout": timeout,
        "max_retries": int(os.getenv("MAX_RETRIES", "2")),
        "callbacks": callbacks,
        "extra_body": {"reasoning": {"effort": effort}} if effort else None,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    llm = ChatOpenAIWithReasoning(**kwargs)
    return llm.bind_tools(tools) if tools else llm


class FallbackChatLLM:
    """LangChain-like chat model that advances through provider candidates."""

    def __init__(
        self,
        candidates: Iterable[LLMCandidate],
        *,
        callbacks: Any = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self.candidates = list(candidates)
        self.callbacks = callbacks
        self.tools = tools
        self._clients = [
            _build_provider_llm(
                provider=c.provider,
                model_name=c.model,
                callbacks=callbacks,
                tools=tools,
            )
            for c in self.candidates
        ]

    @property
    def model_name(self) -> str:
        return self.candidates[0].model if self.candidates else ""

    def bind_tools(self, tools: list[dict[str, Any]]) -> "FallbackChatLLM":
        return FallbackChatLLM(self.candidates, callbacks=self.callbacks, tools=tools)

    @staticmethod
    def _tag_message(message: Any, candidate: LLMCandidate) -> Any:
        additional = getattr(message, "additional_kwargs", None)
        if isinstance(additional, dict):
            additional["provider"] = candidate.provider
            additional["model"] = candidate.model
        metadata = getattr(message, "response_metadata", None)
        if isinstance(metadata, dict):
            metadata["provider"] = candidate.provider
            metadata["model"] = candidate.model
        return message

    def _run_with_fallback(self, operation: str, runner: Any) -> Any:
        last_exc: Exception | None = None
        for idx, (candidate, client) in enumerate(zip(self.candidates, self._clients)):
            try:
                return self._tag_message(runner(client), candidate)
            except Exception as exc:
                last_exc = exc
                if idx == len(self._clients) - 1 or not _is_retryable_llm_error(exc):
                    raise
                next_candidate = self.candidates[idx + 1]
                logger.warning(
                    "LLM %s failed for %s/%s; falling back to %s/%s: %s",
                    operation,
                    candidate.provider,
                    candidate.model,
                    next_candidate.provider,
                    next_candidate.model,
                    _sanitize_error(exc),
                )
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("No LLM fallback candidates configured")

    def invoke(self, messages: list[dict[str, Any]], config: Optional[dict[str, Any]] = None) -> Any:
        return self._run_with_fallback("invoke", lambda client: client.invoke(messages, config=config))

    async def ainvoke(self, messages: list[dict[str, Any]], config: Optional[dict[str, Any]] = None) -> Any:
        return await asyncio.to_thread(self.invoke, messages, config)

    def stream(self, messages: list[dict[str, Any]], config: Optional[dict[str, Any]] = None) -> Iterable[Any]:
        for idx, (candidate, client) in enumerate(zip(self.candidates, self._clients)):
            yielded = False
            try:
                first = True
                for chunk in client.stream(messages, config=config):
                    yielded = True
                    if first:
                        yield self._tag_message(chunk, candidate)
                        first = False
                    else:
                        yield chunk
                return
            except Exception as exc:
                if yielded or idx == len(self._clients) - 1 or not _is_retryable_llm_error(exc):
                    raise
                next_candidate = self.candidates[idx + 1]
                logger.warning(
                    "LLM stream failed for %s/%s; falling back to %s/%s: %s",
                    candidate.provider,
                    candidate.model,
                    next_candidate.provider,
                    next_candidate.model,
                    _sanitize_error(exc),
                )


def build_llm(*, model_name: Optional[str] = None, callbacks: Any = None) -> Any:
    """Construct a ChatOpenAI instance.

    Args:
        model_name: Model name; defaults to LANGCHAIN_MODEL_NAME.
        callbacks: Optional LangChain callbacks.

    Returns:
        ChatOpenAI instance.

    Raises:
        RuntimeError: If langchain-openai is missing or LANGCHAIN_MODEL_NAME is unset.
    """
    _ensure_dotenv()
    name = model_name or os.getenv("LANGCHAIN_MODEL_NAME", "").strip()
    if not name:
        raise RuntimeError("LANGCHAIN_MODEL_NAME is not set")
    provider = os.getenv("LANGCHAIN_PROVIDER", "openai").strip().replace("_", "-").lower()
    candidates = (
        _fallback_chain(provider, name) if _env_flag("LLM_FALLBACK_ENABLED", True) else [LLMCandidate(provider, name)]
    )
    return FallbackChatLLM(candidates, callbacks=callbacks)
