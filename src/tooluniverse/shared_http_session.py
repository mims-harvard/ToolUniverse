"""Identity-free HTTP connection pooling for REST tools.

Each tool instance keeps its own ``requests.Session`` so headers, cookies, auth handlers, and
other mutable identity state remain isolated. Sessions mount one process-wide transport adapter,
which contains only urllib3 connection pools and can therefore reuse TCP/TLS connections without
carrying request credentials between tenants.
"""

from __future__ import annotations

import atexit
import os
import threading

import requests
from requests.adapters import HTTPAdapter


def _positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


class _SharedPoolAdapter(HTTPAdapter):
    """HTTP transport shared by identity-isolated sessions."""

    def __init__(self) -> None:
        self._proxy_lock = threading.Lock()
        super().__init__(
            pool_connections=_positive_int_env(
                "TOOLUNIVERSE_HTTP_POOL_CONNECTIONS", 64
            ),
            pool_maxsize=_positive_int_env("TOOLUNIVERSE_HTTP_POOL_MAXSIZE", 64),
            max_retries=0,
            pool_block=False,
        )

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        # HTTPAdapter lazily mutates proxy_manager. Protect that small piece when the adapter is
        # mounted by sessions used from multiple worker threads.
        with self._proxy_lock:
            return super().proxy_manager_for(proxy, **proxy_kwargs)

    def close(self) -> None:
        # A short-lived session must not close the process-wide pools used by other tenants.
        return None

    def shutdown(self) -> None:
        """Close shared pools once at process shutdown."""

        super().close()


_SHARED_POOL_ADAPTER = _SharedPoolAdapter()
atexit.register(_SHARED_POOL_ADAPTER.shutdown)


def create_shared_pool_session() -> requests.Session:
    """Create an identity-isolated Session backed by shared connection pools."""

    session = requests.Session()
    session.mount("http://", _SHARED_POOL_ADAPTER)
    session.mount("https://", _SHARED_POOL_ADAPTER)
    return session
