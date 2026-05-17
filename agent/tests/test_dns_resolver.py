"""Tests for process-local DNS resolver bootstrap."""

from __future__ import annotations

import socket

import pytest

from src import dns_resolver


def test_default_dns_server_parsing() -> None:
    assert dns_resolver.parse_dns_servers(None) == ["1.1.1.1", "8.8.8.8"]


def test_custom_dns_server_parsing_accepts_commas_and_spaces() -> None:
    assert dns_resolver.parse_dns_servers("9.9.9.9, 149.112.112.112 8.8.4.4") == [
        "9.9.9.9",
        "149.112.112.112",
        "8.8.4.4",
    ]


@pytest.mark.parametrize("raw", ["", "off", "false", "0", " no "])
def test_disabled_values_bypass_installation(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    original = object()
    monkeypatch.setattr(socket, "getaddrinfo", original)
    monkeypatch.setattr(dns_resolver, "_ORIGINAL_GETADDRINFO", None)
    monkeypatch.setattr(dns_resolver, "_INSTALLED_SERVERS", None)

    assert dns_resolver.install_dns_override(raw) is None
    assert socket.getaddrinfo is original


def test_disabled_value_restores_original_after_prior_install(monkeypatch: pytest.MonkeyPatch) -> None:
    original = object()
    wrapped = object()
    monkeypatch.setattr(socket, "getaddrinfo", wrapped)
    monkeypatch.setattr(dns_resolver, "_ORIGINAL_GETADDRINFO", original)
    monkeypatch.setattr(dns_resolver, "_INSTALLED_SERVERS", ("1.1.1.1", "8.8.8.8"))

    assert dns_resolver.install_dns_override("off") is None
    assert socket.getaddrinfo is original
    assert dns_resolver._ORIGINAL_GETADDRINFO is None
    assert dns_resolver._INSTALLED_SERVERS is None


def test_invalid_dns_server_value_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Invalid DNS server IP"):
        dns_resolver.parse_dns_servers("1.1.1.1 not-an-ip")


def test_localhost_uses_original_getaddrinfo() -> None:
    calls: list[tuple[object, ...]] = []
    resolver = _FakeResolver({"example.test": ["203.0.113.10"]})

    def original(host, port, family=0, type=0, proto=0, flags=0):
        calls.append((host, port, family, type, proto, flags))
        return [(socket.AF_INET, socket.SOCK_STREAM, proto, "", ("127.0.0.1", port))]

    wrapped = dns_resolver._make_getaddrinfo(resolver, original)

    result = wrapped("localhost", 8899, socket.AF_INET, socket.SOCK_STREAM)

    assert result == [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 8899))]
    assert calls == [("localhost", 8899, socket.AF_INET, socket.SOCK_STREAM, 0, 0)]
    assert resolver.calls == []


def test_ip_literal_uses_original_getaddrinfo() -> None:
    calls: list[str] = []
    resolver = _FakeResolver({"example.test": ["203.0.113.10"]})

    def original(host, port, family=0, type=0, proto=0, flags=0):
        calls.append(host)
        return [(socket.AF_INET, socket.SOCK_STREAM, proto, "", (host, port))]

    wrapped = dns_resolver._make_getaddrinfo(resolver, original)

    assert wrapped("203.0.113.5", 443, socket.AF_INET, socket.SOCK_STREAM)
    assert calls == ["203.0.113.5"]
    assert resolver.calls == []


def test_hostname_lookup_uses_resolver_and_returns_getaddrinfo_records() -> None:
    calls: list[tuple[object, ...]] = []
    resolver = _FakeResolver({"example.test": ["203.0.113.10"]})

    def original(host, port, family=0, type=0, proto=0, flags=0):
        calls.append((host, port, family, type, proto, flags))
        return [(socket.AF_INET, socket.SOCK_STREAM, proto, "", (host, port))]

    wrapped = dns_resolver._make_getaddrinfo(resolver, original)

    result = wrapped("example.test", 443, socket.AF_INET, socket.SOCK_STREAM)

    assert resolver.calls == [("example.test", "A")]
    assert calls == [
        (
            "203.0.113.10",
            443,
            socket.AF_INET,
            socket.SOCK_STREAM,
            0,
            socket.AI_NUMERICHOST,
        )
    ]
    assert result == [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.0.113.10", 443))]


class _FakeAnswer:
    def __init__(self, address: str) -> None:
        self.address = address


class _FakeResolver:
    def __init__(self, records: dict[str, list[str]]) -> None:
        self.records = records
        self.calls: list[tuple[str, str]] = []

    def resolve(self, host: str, query_type: str) -> list[_FakeAnswer]:
        self.calls.append((host, query_type))
        if query_type != "A":
            raise RuntimeError("unexpected query type")
        return [_FakeAnswer(address) for address in self.records.get(host, [])]
