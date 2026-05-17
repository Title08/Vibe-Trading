"""End-to-end smoke tests for the API server entry point."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from queue import Empty, Queue

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = REPO_ROOT / "agent"
STARTUP_TIMEOUT = 30.0
HEALTH_TIMEOUT = 30.0


def _free_loopback_port() -> int:
    """Return an available loopback TCP port for a short-lived test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _reader(stream, q: Queue[tuple[str, str | None]], name: str) -> None:
    """Pump every line from *stream* into *q*; signal EOF with ``None``."""
    try:
        for line in iter(stream.readline, ""):
            q.put((name, line))
    finally:
        q.put((name, None))


def _drain_output(q: Queue[tuple[str, str | None]]) -> str:
    lines: list[str] = []
    while True:
        try:
            name, line = q.get_nowait()
        except Empty:
            break
        if line is None:
            lines.append(f"[{name}] <EOF>\n")
        else:
            lines.append(f"[{name}] {line}")
    return "".join(lines)


def _wait_for_output(proc: subprocess.Popen, q: Queue[tuple[str, str | None]], needle: str, timeout: float) -> str:
    output = ""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            output += _drain_output(q)
            raise AssertionError(
                f"server exited before output contained {needle!r}; "
                f"returncode={proc.returncode}\n{output}"
            )
        try:
            name, line = q.get(timeout=0.2)
        except Empty:
            continue
        if line is None:
            output += f"[{name}] <EOF>\n"
            continue
        output += f"[{name}] {line}"
        if needle in line:
            return output
    output += _drain_output(q)
    raise AssertionError(f"timed out waiting for output {needle!r}\n{output}")


def _wait_for_health(url: str, proc: subprocess.Popen, q: Queue[tuple[str, str | None]], startup_output: str) -> dict:
    deadline = time.time() + HEALTH_TIMEOUT
    last_error = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            output = startup_output + _drain_output(q)
            raise AssertionError(
                f"server exited before /health responded; returncode={proc.returncode}; "
                f"last_error={last_error}\n{output}"
            )
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(0.25)

    output = startup_output + _drain_output(q)
    raise AssertionError(f"timed out waiting for /health; last_error={last_error}\n{output}")


@pytest.mark.integration
def test_vibe_trading_serve_starts_with_dns_override_and_health() -> None:
    """Spawn the real API server and verify DNS bootstrap plus liveness."""
    port = _free_loopback_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AGENT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    env["VIBE_TRADING_DNS_SERVERS"] = "1.1.1.1,8.8.8.8"
    env["VIBE_TRADING_SKIP_PREFLIGHT"] = "1"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "from api_server import serve_main; "
                f"raise SystemExit(serve_main(['--host', '127.0.0.1', '--port', '{port}']))"
            ),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
        cwd=str(AGENT_DIR),
    )
    q: Queue[tuple[str, str | None]] = Queue()
    stdout_reader = threading.Thread(target=_reader, args=(proc.stdout, q, "stdout"), daemon=True)
    stderr_reader = threading.Thread(target=_reader, args=(proc.stderr, q, "stderr"), daemon=True)
    stdout_reader.start()
    stderr_reader.start()

    try:
        output = _wait_for_output(
            proc,
            q,
            "DNS override: 1.1.1.1, 8.8.8.8",
            STARTUP_TIMEOUT,
        )
        health = _wait_for_health(f"http://127.0.0.1:{port}/health", proc, q, output)

        assert health["status"] == "healthy", output
        assert health["service"] == "Vibe-Trading API", output
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
