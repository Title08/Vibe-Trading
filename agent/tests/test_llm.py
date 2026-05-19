"""Tests for LLM provider mapping and JSON extraction."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.providers.llm import (
    FallbackChatLLM,
    LLMCandidate,
    _extract_balanced_json,
    _sync_provider_env,
    build_llm,
)


# ---------------------------------------------------------------------------
# _sync_provider_env
# ---------------------------------------------------------------------------


class TestSyncProviderEnv:
    """Provider-specific env vars → OPENAI_* mapping."""

    def _run_sync(self, env: dict[str, str]) -> dict[str, str]:
        """Run _sync_provider_env with a clean env and return relevant keys."""
        # Reset the dotenv guard so it doesn't skip
        import src.providers.llm as llm_mod
        llm_mod._dotenv_loaded = True  # pretend already loaded

        clean = {k: v for k, v in os.environ.items() if not k.startswith(("OPENAI_", "LANGCHAIN_", "DEEPSEEK_", "GROQ_", "OLLAMA_", "DASHSCOPE_", "ZAI_"))}
        clean.update(env)
        with patch.dict(os.environ, clean, clear=True):
            _sync_provider_env()
            return {
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
                "OPENAI_API_BASE": os.environ.get("OPENAI_API_BASE", ""),
                "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL", ""),
            }

    def test_openai_default(self) -> None:
        result = self._run_sync({
            "OPENAI_API_KEY": "sk-test",
        })
        assert result["OPENAI_API_KEY"] == "sk-test"

    def test_openai_codex_provider_does_not_map_oauth_token_to_api_key(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "openai-codex",
            "OPENAI_CODEX_BASE_URL": "https://chatgpt.com/backend-api/codex/responses",
        })
        assert result["OPENAI_API_KEY"] == ""
        assert result["OPENAI_API_BASE"] == "https://chatgpt.com/backend-api/codex/responses"

    def test_deepseek_provider(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "ds-key-123",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com/v1",
        })
        assert result["OPENAI_API_KEY"] == "ds-key-123"
        assert result["OPENAI_API_BASE"] == "https://api.deepseek.com/v1"

    def test_groq_provider(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "groq",
            "GROQ_API_KEY": "gsk-test",
            "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
        })
        assert result["OPENAI_API_KEY"] == "gsk-test"
        assert "groq" in result["OPENAI_API_BASE"]

    def test_ollama_no_key_required(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        })
        # Ollama uses "ollama" as fallback key
        assert result["OPENAI_API_KEY"] in ("ollama", "")
        assert result["OPENAI_API_BASE"] == "http://localhost:11434/v1"

    def test_ollama_base_url_appends_v1(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://23.152.56.42:11434/",
        })
        assert result["OPENAI_API_BASE"] == "http://23.152.56.42:11434/v1"
        assert result["OPENAI_BASE_URL"] == "http://23.152.56.42:11434/v1"

    def test_qwen_alias_to_dashscope(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "qwen",
            "DASHSCOPE_API_KEY": "qwen-key",
            "DASHSCOPE_BASE_URL": "https://dashscope.aliyuncs.com/v1",
        })
        assert result["OPENAI_API_KEY"] == "qwen-key"

    def test_zai_provider(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "zai",
            "ZAI_API_KEY": "zai-key-test",
            "ZAI_BASE_URL": "https://api.z.ai/api/coding/paas/v4",
        })
        assert result["OPENAI_API_KEY"] == "zai-key-test"
        assert result["OPENAI_API_BASE"] == "https://api.z.ai/api/coding/paas/v4"

    def test_unknown_provider_falls_back_to_openai(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "unknown_provider_xyz",
            "OPENAI_API_KEY": "sk-fallback",
        })
        assert result["OPENAI_API_KEY"] == "sk-fallback"

    def test_provider_key_fallback_to_openai_key(self) -> None:
        """If provider-specific key is missing, fall back to OPENAI_API_KEY."""
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "deepseek",
            "OPENAI_API_KEY": "sk-shared",
        })
        assert result["OPENAI_API_KEY"] == "sk-shared"

    def test_minimax_provider(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "minimax",
            "MINIMAX_API_KEY": "minimax-key-123",
            "MINIMAX_BASE_URL": "https://api.minimax.io/v1",
        })
        assert result["OPENAI_API_KEY"] == "minimax-key-123"
        assert result["OPENAI_API_BASE"] == "https://api.minimax.io/v1"

    def test_minimax_base_url_in_openai_base_url(self) -> None:
        result = self._run_sync({
            "LANGCHAIN_PROVIDER": "minimax",
            "MINIMAX_API_KEY": "minimax-key",
            "MINIMAX_BASE_URL": "https://api.minimax.io/v1",
        })
        assert "minimax.io" in result["OPENAI_BASE_URL"]


# ---------------------------------------------------------------------------
# MiniMax temperature clamping
# ---------------------------------------------------------------------------


class TestMinimaxTemperature:
    """MiniMax requires temperature > 0; build_llm should clamp the default."""

    def test_minimax_temperature_clamped_from_zero(self) -> None:
        """When LANGCHAIN_TEMPERATURE=0.0 and provider=minimax, temperature must be clamped to 0.01."""
        import src.providers.llm as llm_mod
        llm_mod._dotenv_loaded = True

        captured: dict[str, float] = {}

        class _FakeChatOpenAI:
            def __init__(self, **kwargs: object) -> None:
                captured["temperature"] = float(kwargs.get("temperature", -1))

        env = {
            "LANGCHAIN_PROVIDER": "minimax",
            "MINIMAX_API_KEY": "minimax-key",
            "MINIMAX_BASE_URL": "https://api.minimax.io/v1",
            "LANGCHAIN_MODEL_NAME": "MiniMax-M2.7",
            "LANGCHAIN_TEMPERATURE": "0.0",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.object(llm_mod, "ChatOpenAIWithReasoning", _FakeChatOpenAI):
                build_llm()
        assert captured["temperature"] == 0.01, (
            "MiniMax temperature must be clamped to 0.01 when 0.0 is configured"
        )

    def test_minimax_positive_temperature_preserved(self) -> None:
        """When an explicit positive temperature is set, it should be preserved."""
        import src.providers.llm as llm_mod
        llm_mod._dotenv_loaded = True

        captured: dict[str, float] = {}

        class _FakeChatOpenAI:
            def __init__(self, **kwargs: object) -> None:
                captured["temperature"] = float(kwargs.get("temperature", -1))

        env = {
            "LANGCHAIN_PROVIDER": "minimax",
            "MINIMAX_API_KEY": "minimax-key",
            "MINIMAX_BASE_URL": "https://api.minimax.io/v1",
            "LANGCHAIN_MODEL_NAME": "MiniMax-M2.7",
            "LANGCHAIN_TEMPERATURE": "0.7",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.object(llm_mod, "ChatOpenAIWithReasoning", _FakeChatOpenAI):
                build_llm()
        assert captured["temperature"] == 0.7


class TestReasoningEffortPassthrough:
    """LANGCHAIN_REASONING_EFFORT is forwarded as extra_body.reasoning.effort
    to the underlying OpenAI-compatible client. Used for OpenRouter-style
    relays that require opt-in to enable thinking."""

    def _capture(self, env: dict[str, str]) -> dict:
        import src.providers.llm as llm_mod
        llm_mod._dotenv_loaded = True

        captured: dict = {}

        class _FakeChatOpenAI:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

        with patch.dict(os.environ, env, clear=True):
            with patch.object(llm_mod, "ChatOpenAIWithReasoning", _FakeChatOpenAI):
                build_llm()
        return captured

    def test_effort_unset_leaves_extra_body_none(self) -> None:
        captured = self._capture({
            "LANGCHAIN_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test",
            "LANGCHAIN_MODEL_NAME": "gpt-4",
        })
        assert captured["extra_body"] is None

    def test_effort_medium_forwarded_as_extra_body(self) -> None:
        captured = self._capture({
            "LANGCHAIN_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": "or-test",
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "LANGCHAIN_MODEL_NAME": "moonshotai/kimi-k2-thinking",
            "LANGCHAIN_REASONING_EFFORT": "medium",
        })
        assert captured["extra_body"] == {"reasoning": {"effort": "medium"}}

    def test_effort_case_insensitive(self) -> None:
        captured = self._capture({
            "LANGCHAIN_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": "or-test",
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "LANGCHAIN_MODEL_NAME": "moonshotai/kimi-k2-thinking",
            "LANGCHAIN_REASONING_EFFORT": "HIGH",
        })
        assert captured["extra_body"]["reasoning"]["effort"] == "high"


class TestProviderFallback:
    """Fallback chain behavior for OpenRouter -> OpenAI Codex."""

    def _build_with_fake_provider(
        self,
        monkeypatch: pytest.MonkeyPatch,
        env: dict[str, str],
        *,
        failures: dict[str, Exception] | None = None,
    ) -> tuple[FallbackChatLLM, list[tuple[str, str, object]]]:
        import src.providers.llm as llm_mod

        llm_mod._dotenv_loaded = True
        failures = failures or {}
        calls: list[tuple[str, str, object]] = []

        class _FakeProviderLLM:
            def __init__(self, provider: str, model: str, tools: object = None) -> None:
                self.provider = provider
                self.model = model
                self.tools = tools

            def bind_tools(self, tools: object) -> "_FakeProviderLLM":
                return _FakeProviderLLM(self.provider, self.model, tools)

            def invoke(self, messages: object, config: object = None) -> str:
                calls.append((self.provider, self.model, self.tools))
                if self.provider in failures:
                    raise failures[self.provider]
                return f"ok:{self.provider}:{self.model}"

            def stream(self, messages: object, config: object = None):
                calls.append((self.provider, self.model, self.tools))
                if self.provider in failures:
                    raise failures[self.provider]
                yield f"chunk:{self.provider}:{self.model}"

        def _fake_build_provider_llm(*, provider: str, model_name: str, callbacks: object = None, tools: object = None):
            return _FakeProviderLLM(provider, model_name, tools)

        monkeypatch.setattr(llm_mod, "_build_provider_llm", _fake_build_provider_llm)
        with patch.dict(os.environ, env, clear=True):
            llm = build_llm()
        return llm, calls

    def test_default_chain_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        llm, _ = self._build_with_fake_provider(
            monkeypatch,
            {
                "LANGCHAIN_PROVIDER": "openrouter",
                "LANGCHAIN_MODEL_NAME": "deepseek/custom-primary",
                "OPENROUTER_API_KEY": "or-test",
            },
        )

        assert isinstance(llm, FallbackChatLLM)
        assert llm.candidates == [
            LLMCandidate("openrouter", "deepseek/custom-primary"),
            LLMCandidate("openai-codex", "openai-codex/gpt-5.3-codex"),
        ]

    def test_retryable_429_advances_to_codex(self, monkeypatch: pytest.MonkeyPatch) -> None:
        llm, calls = self._build_with_fake_provider(
            monkeypatch,
            {
                "LANGCHAIN_PROVIDER": "openrouter",
                "LANGCHAIN_MODEL_NAME": "deepseek/deepseek-v3.2",
            },
            failures={"openrouter": RuntimeError("HTTP 429: rate limit exceeded")},
        )

        assert llm.invoke([{"role": "user", "content": "hi"}]) == "ok:openai-codex:openai-codex/gpt-5.3-codex"
        assert [provider for provider, _, _ in calls] == ["openrouter", "openai-codex"]

    def test_all_candidates_fail_raises_last_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        llm, calls = self._build_with_fake_provider(
            monkeypatch,
            {
                "LANGCHAIN_PROVIDER": "openrouter",
                "LANGCHAIN_MODEL_NAME": "deepseek/deepseek-v3.2",
            },
            failures={
                "openrouter": RuntimeError("HTTP 429: quota exceeded"),
                "openai-codex": RuntimeError("HTTP 503: temporarily unavailable"),
            },
        )

        with pytest.raises(RuntimeError, match="HTTP 503: temporarily unavailable"):
            llm.invoke([{"role": "user", "content": "hi"}])
        assert [provider for provider, _, _ in calls] == ["openrouter", "openai-codex"]

    def test_non_retryable_error_does_not_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        llm, calls = self._build_with_fake_provider(
            monkeypatch,
            {
                "LANGCHAIN_PROVIDER": "openrouter",
                "LANGCHAIN_MODEL_NAME": "deepseek/deepseek-v3.2",
            },
            failures={"openrouter": RuntimeError("invalid api key")},
        )

        with pytest.raises(RuntimeError, match="invalid api key"):
            llm.invoke([{"role": "user", "content": "hi"}])
        assert [provider for provider, _, _ in calls] == ["openrouter"]

    def test_fallback_can_be_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        llm, _ = self._build_with_fake_provider(
            monkeypatch,
            {
                "LANGCHAIN_PROVIDER": "openrouter",
                "LANGCHAIN_MODEL_NAME": "deepseek/deepseek-v3.2",
                "LLM_FALLBACK_ENABLED": "false",
            },
        )

        assert isinstance(llm, FallbackChatLLM)
        assert llm.candidates == [LLMCandidate("openrouter", "deepseek/deepseek-v3.2")]

    def test_custom_fallback_models_are_honored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        llm, _ = self._build_with_fake_provider(
            monkeypatch,
            {
                "LANGCHAIN_PROVIDER": "openrouter",
                "LANGCHAIN_MODEL_NAME": "primary-model",
                "OPENAI_CODEX_FALLBACK_MODEL": "openai-codex/custom",
            },
        )

        assert isinstance(llm, FallbackChatLLM)
        assert llm.candidates == [
            LLMCandidate("openrouter", "primary-model"),
            LLMCandidate("openai-codex", "openai-codex/custom"),
        ]

    def test_bind_tools_preserves_tools_across_candidates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        llm, calls = self._build_with_fake_provider(
            monkeypatch,
            {
                "LANGCHAIN_PROVIDER": "openrouter",
                "LANGCHAIN_MODEL_NAME": "deepseek/deepseek-v3.2",
            },
            failures={"openrouter": RuntimeError("HTTP 429: rate limit exceeded")},
        )

        tools = [{"type": "function", "function": {"name": "lookup"}}]
        bound = llm.bind_tools(tools)
        assert bound.invoke([{"role": "user", "content": "hi"}]) == "ok:openai-codex:openai-codex/gpt-5.3-codex"
        assert calls == [("openrouter", "deepseek/deepseek-v3.2", tools), ("openai-codex", "openai-codex/gpt-5.3-codex", tools)]

    def test_successful_candidate_tags_provider_and_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import src.providers.llm as llm_mod

        llm_mod._dotenv_loaded = True

        class _FakeMessage:
            content = "done"
            tool_calls: list = []
            additional_kwargs: dict = {}
            response_metadata: dict = {"finish_reason": "stop"}
            usage_metadata = None

        class _FakeProviderLLM:
            def __init__(self, provider: str, model: str) -> None:
                self.provider = provider
                self.model = model

            def bind_tools(self, tools: object) -> "_FakeProviderLLM":
                return self

            def invoke(self, messages: object, config: object = None) -> _FakeMessage:
                if self.provider == "openrouter":
                    raise RuntimeError("HTTP 429: rate limit exceeded")
                return _FakeMessage()

            def stream(self, messages: object, config: object = None):
                yield self.invoke(messages, config=config)

        def _fake_build_provider_llm(*, provider: str, model_name: str, callbacks: object = None, tools: object = None):
            return _FakeProviderLLM(provider, model_name)

        monkeypatch.setattr(llm_mod, "_build_provider_llm", _fake_build_provider_llm)
        with patch.dict(os.environ, {
            "LANGCHAIN_PROVIDER": "openrouter",
            "LANGCHAIN_MODEL_NAME": "deepseek/deepseek-v3.2",
        }, clear=True):
            parsed = build_llm().invoke([{"role": "user", "content": "hi"}])

        from src.providers.chat import ChatLLM

        response = ChatLLM._parse_response(parsed)
        assert response.provider == "openai-codex"
        assert response.model == "openai-codex/gpt-5.3-codex"


class TestExtractBalancedJson:
    def test_simple_json(self) -> None:
        result = _extract_balanced_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_embedded_in_text(self) -> None:
        text = 'Here is the config: {"a": 1, "b": 2} and some more text.'
        result = _extract_balanced_json(text)
        assert result == {"a": 1, "b": 2}

    def test_nested_json(self) -> None:
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = _extract_balanced_json(text)
        assert result["outer"]["inner"] == [1, 2, 3]

    def test_escaped_quotes(self) -> None:
        text = r'{"msg": "he said \"hello\""}'
        result = _extract_balanced_json(text)
        assert result is not None
        assert "hello" in result["msg"]

    def test_no_json(self) -> None:
        assert _extract_balanced_json("no json here") is None

    def test_empty_string(self) -> None:
        assert _extract_balanced_json("") is None

    def test_braces_in_strings(self) -> None:
        text = '{"pattern": "if (x > 0) { return x; }"}'
        result = _extract_balanced_json(text)
        assert result is not None
        assert "return x" in result["pattern"]

    def test_multiple_objects_returns_first(self) -> None:
        text = '{"a": 1} {"b": 2}'
        result = _extract_balanced_json(text)
        assert result == {"a": 1}
