"""Process-local DNS resolver bootstrap for the API server."""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable
from typing import Any

DNS_SERVERS_ENV = "VIBE_TRADING_DNS_SERVERS"
DEFAULT_DNS_SERVERS = ("1.1.1.1", "8.8.8.8")
_DISABLED_VALUES = {"", "0", "false", "off", "no", "disabled"}

_ORIGINAL_GETADDRINFO: Callable[..., Any] | None = None
_INSTALLED_SERVERS: tuple[str, ...] | None = None


def parse_dns_servers(raw: str | None) -> list[str] | None:
    """Parse configured DNS servers.

    ``None`` means use Vibe-Trading's fixed defaults. Empty and common false-y
    values disable the process override so operators can fall back to OS DNS.
    """
    if raw is None:
        return list(DEFAULT_DNS_SERVERS)

    value = raw.strip()
    if value.lower() in _DISABLED_VALUES:
        return None

    servers = [part for part in re.split(r"[\s,]+", value) if part]
    if not servers:
        return None

    parsed: list[str] = []
    for server in servers:
        try:
            parsed.append(str(ipaddress.ip_address(server)))
        except ValueError as exc:
            raise ValueError(f"Invalid DNS server IP in {DNS_SERVERS_ENV}: {server!r}") from exc
    return parsed


def install_dns_override(raw: str | None = None) -> list[str] | None:
    """Install a process-local ``socket.getaddrinfo`` DNS override.

    Returns the active nameservers, or ``None`` when the override is disabled.
    The installation is idempotent for repeated server startup paths in tests.
    """
    servers = parse_dns_servers(raw)
    if not servers:
        _restore_original_getaddrinfo()
        return None

    global _ORIGINAL_GETADDRINFO, _INSTALLED_SERVERS
    if _ORIGINAL_GETADDRINFO is None:
        _ORIGINAL_GETADDRINFO = socket.getaddrinfo
    if _INSTALLED_SERVERS == tuple(servers):
        return servers

    try:
        import dns.resolver
    except ImportError as exc:
        raise RuntimeError("dnspython is required for VIBE_TRADING_DNS_SERVERS") from exc

    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = servers
    resolver.lifetime = 10.0
    resolver.timeout = 5.0

    socket.getaddrinfo = _make_getaddrinfo(resolver, _ORIGINAL_GETADDRINFO)  # type: ignore[method-assign]
    _INSTALLED_SERVERS = tuple(servers)
    return servers


def _restore_original_getaddrinfo() -> None:
    """Restore OS DNS resolution after a prior in-process installation."""
    global _ORIGINAL_GETADDRINFO, _INSTALLED_SERVERS
    if _ORIGINAL_GETADDRINFO is not None:
        socket.getaddrinfo = _ORIGINAL_GETADDRINFO  # type: ignore[method-assign]
    _ORIGINAL_GETADDRINFO = None
    _INSTALLED_SERVERS = None


def _make_getaddrinfo(resolver: Any, original_getaddrinfo: Callable[..., Any]) -> Callable[..., Any]:
    """Build a ``getaddrinfo`` wrapper backed by a dnspython resolver."""

    def getaddrinfo(
        host: str | bytes | None,
        port: str | int | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> list[tuple[Any, ...]]:
        if _should_use_original(host, flags):
            return original_getaddrinfo(host, port, family, type, proto, flags)

        try:
            addresses = _resolve_addresses(resolver, str(host), family)
            results: list[tuple[Any, ...]] = []
            seen: set[tuple[Any, ...]] = set()
            for address in addresses:
                for item in original_getaddrinfo(address, port, family, type, proto, flags | socket.AI_NUMERICHOST):
                    if item not in seen:
                        seen.add(item)
                        results.append(item)
            if results:
                return results
        except Exception:
            pass

        return original_getaddrinfo(host, port, family, type, proto, flags)

    return getaddrinfo


def _should_use_original(host: str | bytes | None, flags: int) -> bool:
    """Return whether a lookup should bypass custom DNS."""
    if host is None or isinstance(host, bytes):
        return True
    if flags & socket.AI_NUMERICHOST:
        return True

    normalized = host.strip().rstrip(".").lower()
    if normalized == "localhost":
        return True
    try:
        ipaddress.ip_address(normalized)
        return True
    except ValueError:
        return False


def _resolve_addresses(resolver: Any, host: str, family: int) -> list[str]:
    """Resolve host addresses for the requested socket family."""
    if family == socket.AF_INET:
        query_types = ("A",)
    elif family == socket.AF_INET6:
        query_types = ("AAAA",)
    elif family in (0, socket.AF_UNSPEC):
        query_types = ("A", "AAAA")
    else:
        return []

    addresses: list[str] = []
    for query_type in query_types:
        try:
            answers = resolver.resolve(host, query_type)
        except Exception:
            continue
        for answer in answers:
            address = getattr(answer, "address", str(answer))
            if address not in addresses:
                addresses.append(address)
    return addresses
