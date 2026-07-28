"""Request-scoped credentials for multi-tenant ToolUniverse applications.

Environment variables remain the backwards-compatible default for local and single-user use.
Hosted applications can activate :func:`credential_context` around one request so tools resolve
only that request's credentials.  The values are immutable, are never copied to ``os.environ``,
and are restored automatically when the context exits.
"""

from __future__ import annotations

import contextvars
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import MappingProxyType
from typing import Iterator, Mapping, Optional


CredentialMapping = Mapping[str, str]

_CREDENTIAL_NAME_SUFFIXES = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "USERNAME",
    "EMAIL",
    "JWT",
)

# ``None`` means there is no request scope and tools may use their normal environment fallback.
# An active empty mapping is intentionally different: it masks all process-level credentials.
_request_credentials: contextvars.ContextVar[Optional[CredentialMapping]] = (
    contextvars.ContextVar("tooluniverse_request_credentials", default=None)
)


def _validated_copy(credentials: CredentialMapping) -> CredentialMapping:
    if not isinstance(credentials, Mapping):
        raise TypeError(
            "credentials must be a mapping of string names to string values"
        )

    copied = {}
    for name, value in credentials.items():
        if not isinstance(name, str) or not name:
            raise TypeError("credential names must be non-empty strings")
        if not isinstance(value, str):
            raise TypeError(f"credential {name!r} must have a string value")
        copied[name] = value
    return MappingProxyType(copied)


@contextmanager
def credential_context(credentials: CredentialMapping) -> Iterator[CredentialMapping]:
    """Activate an isolated credential mapping for the current execution context.

    Contexts may be nested and are safe across asyncio tasks.  Use
    :class:`ContextThreadPoolExecutor` when work crosses into a thread pool.
    """

    scoped = _validated_copy(credentials)
    token = _request_credentials.set(scoped)
    try:
        yield scoped
    finally:
        _request_credentials.reset(token)


def current_credentials() -> Optional[CredentialMapping]:
    """Return the immutable active mapping, or ``None`` outside a request scope."""

    return _request_credentials.get()


def has_credential_context() -> bool:
    """Return whether request-scoped credentials (including an empty scope) are active."""

    return _request_credentials.get() is not None


def is_credential_name(name: str) -> bool:
    """Distinguish provider credentials from process-level infrastructure config."""
    return isinstance(name, str) and name.endswith(_CREDENTIAL_NAME_SUFFIXES)


def get_credential(name: str, fallback: Optional[str] = None) -> Optional[str]:
    """Resolve a credential without exposing it as a tool argument.

    Outside a request credential context, ``fallback`` is used when supplied; otherwise the
    environment variable named by ``name`` is read. Inside an active context, a missing name
    returns ``None`` rather than falling back to a process-wide secret. This fail-closed behavior
    prevents one tenant from inheriting another deployment credential.
    """

    if not isinstance(name, str) or not name:
        raise TypeError("credential name must be a non-empty string")
    scoped = _request_credentials.get()
    if scoped is None:
        return fallback if fallback is not None else os.environ.get(name)
    return scoped.get(name)


class ContextThreadPoolExecutor(ThreadPoolExecutor):
    """ThreadPoolExecutor that propagates the submitting task's context variables."""

    def submit(self, fn, /, *args, **kwargs):
        context = contextvars.copy_context()
        return super().submit(context.run, fn, *args, **kwargs)
