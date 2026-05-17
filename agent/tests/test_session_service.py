"""Regression tests for session attempt metadata."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from src.session.events import EventBus
from src.session.models import Attempt, Message, Session
from src.session.service import SessionService
from src.session.store import SessionStore


class _NoopSearchIndex:
    def index_message(self, *_: Any, **__: Any) -> None:
        return None

    def index_session(self, *_: Any, **__: Any) -> None:
        return None


class _StubSessionService(SessionService):
    def __init__(self, store: SessionStore, event_bus: EventBus, runs_dir: Path, run_dir: Path) -> None:
        super().__init__(store, event_bus, runs_dir)
        self._search_index = _NoopSearchIndex()
        self._run_dir = run_dir

    async def _run_with_agent(self, *_: Any, **__: Any) -> dict[str, Any]:
        metrics = self._load_metrics(self._run_dir)
        return {
            "status": "success",
            "content": "Strategy execution completed.",
            "run_dir": str(self._run_dir),
            "metrics": metrics,
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
        }


def test_run_attempt_persists_metrics_in_assistant_message_metadata(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "20260517_175530_86_ef7289"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)
    (artifacts_dir / "metrics.csv").write_text(
        "total_return,annual_return,max_drawdown,sharpe,win_rate,trade_count\n"
        "0.6876694442550799,0.6852579464970385,-0.11751697956636636,1.800446814616294,0.5833333333333334,12\n",
        encoding="utf-8",
    )

    store = SessionStore(tmp_path / "sessions")
    service = _StubSessionService(store, EventBus(), tmp_path / "runs", run_dir)
    session = Session(title="metrics session")
    store.create_session(session)
    user = Message(session_id=session.session_id, role="user", content="backtest btc")
    store.append_message(user)
    attempt = Attempt(session_id=session.session_id, prompt=user.content)
    store.create_attempt(attempt)

    asyncio.run(service._run_attempt(session, attempt))

    persisted_attempt = store.get_attempt(session.session_id, attempt.attempt_id)
    assert persisted_attempt is not None
    assert persisted_attempt.metrics == {
        "total_return": 0.6876694442550799,
        "annual_return": 0.6852579464970385,
        "max_drawdown": -0.11751697956636636,
        "sharpe": 1.800446814616294,
        "win_rate": 0.5833333333333334,
        "trade_count": 12.0,
    }

    messages = store.get_messages(session.session_id)
    assistant = messages[-1]
    assert assistant.role == "assistant"
    assert assistant.metadata["run_id"] == run_dir.name
    assert assistant.metadata["status"] == "completed"
    assert assistant.metadata["metrics"] == persisted_attempt.metrics
    assert assistant.metadata["provider"] == "groq"
    assert assistant.metadata["model"] == "llama-3.3-70b-versatile"
