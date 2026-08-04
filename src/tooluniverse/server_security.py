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
