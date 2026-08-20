"""Shared authentication helpers for ToolUniverse network servers.

ToolUniverse can expose tool execution (including the Python code executor) over
HTTP via several entry points: the FastAPI app (``http_api_server``) and the
FastMCP-based SMCP server (``smcp``). None of these should be reachable over the
network without authentication.

This module centralizes two controls used by every server entry point:

1. A Bearer token, read from the ``TOOLUNIVERSE_API_TOKEN`` environment variable.
   When set, callers must present ``Authorization: Bearer <token>`` on every
   request. The token is a server-side trust boundary and is never accepted from
   request bodies or tool arguments.

2. A bind guard (:func:`enforce_bind_security`) that refuses to expose a server
   on a non-loopback interface unless a token is configured. The shipped default
   bind address is loopback (``127.0.0.1``); operators must opt in to remote
   exposure *and* set a token to do so.

3. Fail-closed FastMCP helpers used by standalone remote-tool servers. When a
   token is configured but FastMCP authentication cannot be initialized, server
   construction raises instead of silently exposing an unauthenticated service.
"""

import hmac
import ipaddress
import os

API_TOKEN_ENV = "TOOLUNIVERSE_API_TOKEN"

# Hostnames that resolve to the local machine only.
_LOOPBACK_HOSTNAMES = {"localhost", ""}


def get_api_token():
    """Return the configured API token, or ``None`` if authentication is disabled.

    Whitespace is stripped; an empty value is treated as "no token".
    """
    token = os.getenv(API_TOKEN_ENV, "").strip()
    return token or None


def is_loopback_host(host):
    """Return ``True`` if ``host`` only accepts connections from the local machine."""
    if host is None:
        return True
    candidate = host.strip().lower()
    if candidate in _LOOPBACK_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        # A non-literal hostname other than "localhost": treat as remotely
        # reachable so we fail closed rather than open.
        return False


def token_matches(provided_header, expected_token):
    """Constant-time check of an ``Authorization`` header against the token.

    ``provided_header`` is the raw header value (e.g. ``"Bearer abc"``).
    Returns ``False`` for any malformed or missing header.
    """
    if not expected_token or not provided_header:
        return False
    parts = provided_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False
    return hmac.compare_digest(parts[1].strip(), expected_token)


def enforce_bind_security(host):
    """Refuse to expose the server on a non-loopback host without a token.

    Returns the configured token (or ``None`` for loopback-only runs) so callers
    can decide whether to install request authentication.

    Raises:
        RuntimeError: if ``host`` is remotely reachable and no token is set.
    """
    token = get_api_token()
    if not is_loopback_host(host) and token is None:
        raise RuntimeError(
            f"Refusing to bind to non-loopback host {host!r} without authentication. "
            f"Set the {API_TOKEN_ENV} environment variable to require a Bearer token "
            f"on every request, or bind to 127.0.0.1 for local-only access."
        )
    return token


def get_fastmcp_token_auth():
    """Build FastMCP bearer-token authentication from the provider environment.

    Returns None for a loopback-only deployment with no configured token. If a
    token is configured, inability to import or construct FastMCP's token
    verifier is a fatal configuration error: remote servers must never fall
    back to unauthenticated operation.
    """
    token = get_api_token()
    if token is None:
        return None
    try:
        from fastmcp.server.auth import StaticTokenVerifier

        return StaticTokenVerifier(
            tokens={token: {"client_id": "tooluniverse", "scopes": []}}
        )
    except Exception as exc:
        raise RuntimeError(
            "TOOLUNIVERSE_API_TOKEN is set but FastMCP bearer-token "
            "authentication could not be initialized."
        ) from exc


def run_fastmcp_server(
    server,
    *,
    host="127.0.0.1",
    port,
    transport="streamable-http",
    **kwargs,
):
    """Run a standalone FastMCP server after enforcing the network bind guard."""
    enforce_bind_security(host)
    return server.run(transport=transport, host=host, port=port, **kwargs)
