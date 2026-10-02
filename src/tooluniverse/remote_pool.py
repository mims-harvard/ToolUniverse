"""On-demand provider pool behind one multiplexed local MCP endpoint.

``tu remote run``/``tu remote share`` bind one reviewed provider per invocation: the
command starts that provider, holds it in the foreground, and ``RelayAgent`` forwards
every relayed request to its single fixed endpoint. Sharing three models therefore
means three terminals, three processes resident the whole time, and three ports --
and a model nobody is calling still occupies its GPU.

This module serves the same providers from one process that starts nothing up front.
It exposes a normal Streamable-HTTP MCP endpoint, so the existing relay agent needs
no change and the platform needs no new protocol:

    tu remote pool --allow boltz,esm,enformer --share

    caller --relay--> RelayAgent --> pool :7999 --+--> boltz    :8080  (started on
                      (unchanged)   (this module) |                     first call)
                                                  +--> esm      :8008  (idle, stopped)
                                                  +--> enformer :8011  (never started)

``tools/list`` answers from cached per-provider snapshots without starting anything,
so a caller can discover every shared model while the GPU sits empty. ``tools/call``
resolves the tool name to its owning provider -- tool names are unique across the
reviewed catalog, which :func:`build_tool_index` asserts -- starts that provider if
it is not already up, and proxies the call. Providers idle longer than ``idle_ttl``
are stopped, and ``max_active`` bounds how many run at once with least-recently-used
eviction, so one host can advertise more models than its GPU could hold together.

The pool deliberately does not reach past what a local endpoint can do. It cannot be
asked to prewarm before a call arrives, because the tunnel carries only HTTP
request/response frames and has no control plane; a call that lands while a provider
is still starting gets 503 with Retry-After rather than being queued across the
relay. Admission counts providers, not VRAM. See
``docs/dev_docs/Remote_Provider_Pool_Design.md`` for why those belong to a later
protocol change rather than here.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .remote_runtime import (
    REMOTE_BY_SLUG,
    ManagedRemoteProcess,
    RemoteDeployment,
    ensure_provider,
    stop_provider,
)

# One provider's tools/list snapshot stays far below the relay's 1 MiB manifest cap; the
# whole reviewed catalog is 41 operations. Bound it anyway so a provider that returns a
# pathological manifest cannot be cached or published.
MAX_SNAPSHOT_BYTES = 256 << 10
MAX_TOOLS_PER_PROVIDER = 512

# A started provider is probed for readiness by remote_runtime.wait_until_ready; this is
# only the ceiling this module allows an operator to configure.
MIN_STARTUP_TIMEOUT = 10.0
MAX_STARTUP_TIMEOUT = 1800.0

# A measurement above this is a misread rather than a model: no single reviewed provider
# approaches it, and admitting against a bogus number would wedge the pool.
MAX_PLAUSIBLE_FOOTPRINT_MIB = 512 << 10  # 512 GiB

# Fragmentation, the CUDA context, and whatever else shares the device. Admitting a model
# into exactly its measured size reliably fails on the real allocation.
DEFAULT_VRAM_HEADROOM_MIB = 1024

DEFAULT_POOL_PORT = 7999
DEFAULT_IDLE_TTL = 900.0
DEFAULT_MAX_ACTIVE = 1
DEFAULT_STARTUP_TIMEOUT = 600.0

# Proxied tool calls can be long GPU jobs. The relay agent gives up at 25s and the
# platform enforces its own per-tool timeout, so this only prevents a wedged provider
# from pinning a pool thread forever.
PROXY_TIMEOUT = 900.0

_JSONRPC_PARSE_ERROR = -32700
_JSONRPC_INVALID_REQUEST = -32600
_JSONRPC_METHOD_NOT_FOUND = -32601
_JSONRPC_INVALID_PARAMS = -32602
_JSONRPC_INTERNAL_ERROR = -32603


class PoolError(RuntimeError):
    """A pool request failed in a way the caller should see."""


class ProviderStarting(PoolError):
    """A provider is being started by another in-flight request."""


def build_tool_index(slugs: Iterable[str]) -> dict[str, RemoteDeployment]:
    """Map every advertised tool name to the provider that serves it.

    Raises on an unknown slug, and on two providers claiming one tool name. The second
    check is what makes name-based routing safe: a collision would silently send calls
    to whichever provider happened to be registered last, so refuse to start instead.
    """

    index: dict[str, RemoteDeployment] = {}
    for slug in slugs:
        deployment = REMOTE_BY_SLUG.get(slug)
        if deployment is None:
            known = ", ".join(sorted(REMOTE_BY_SLUG))
            raise PoolError(f"unknown provider '{slug}'; reviewed providers: {known}")
        for operation in deployment.operations:
            previous = index.get(operation)
            if previous is not None and previous.slug != deployment.slug:
                raise PoolError(
                    f"tool '{operation}' is claimed by both '{previous.slug}' and "
                    f"'{deployment.slug}'; name-based routing cannot disambiguate them"
                )
            index[operation] = deployment
    return index


def gpu_free_mib(timeout: float = 5.0) -> int | None:
    """Free VRAM on the most free visible GPU, or None when there is no GPU to ask.

    Reports the maximum across devices rather than the sum: one provider lands on one
    GPU, so the sum would claim room that no single model can use. The pool does not
    choose placement -- CUDA_VISIBLE_DEVICES and the provider do -- so this is an upper
    bound on what the next model can expect, not a guarantee.

    None means "do not reason about VRAM": no nvidia-smi, no driver, or a machine with no
    GPU at all, which is the case for twenty of the thirty reviewed providers.
    """

    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    values: list[int] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            values.append(int(line))
        except ValueError:
            # A driver error string in place of a number: treat the whole reading as
            # unavailable rather than admitting on a partial view of the hardware.
            return None
    return max(values) if values else None


@dataclass
class FootprintStore:
    """Measured VRAM cost per provider, cached on disk.

    Nothing declares how much memory a reviewed provider needs -- no provider.toml, no
    README figure, nothing in RemoteDeployment -- so inventing a table would be guessing
    about other people's hardware. Instead the pool measures: free VRAM before a start,
    free VRAM once the provider answers, and the difference is what that model costs on
    this machine. The first load of a provider is therefore admitted on count alone, and
    every later one can be admitted on memory.

    Measurements keep the largest value seen. A model that allocates lazily looks smaller
    on a run that only initialised it, and admitting on that smaller number would
    overcommit the GPU the next time it is actually used.
    """

    directory: Path

    def __post_init__(self) -> None:
        self.directory = Path(self.directory).expanduser()

    def _path(self) -> Path:
        return self.directory / "footprints.json"

    def _read(self) -> dict[str, int]:
        try:
            payload = json.loads(self._path().read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            slug: value
            for slug, value in payload.items()
            if isinstance(slug, str) and isinstance(value, int) and value > 0
        }

    def get(self, slug: str) -> int | None:
        return self._read().get(slug)

    def record(self, slug: str, mib: int) -> None:
        """Keep the largest plausible measurement for this provider."""

        if mib <= 0 or mib > MAX_PLAUSIBLE_FOOTPRINT_MIB:
            return
        known = self._read()
        if known.get(slug, 0) >= mib:
            return
        known[slug] = mib
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path()
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(known, separators=(",", ":"), sort_keys=True), encoding="utf-8"
        )
        temporary.replace(target)


@dataclass
class SchemaStore:
    """Per-provider ``tools/list`` snapshots, cached on disk.

    Most reviewed providers declare their schemas inside ``<slug>_tool.py``, so the only
    way to learn them is to ask a running provider. Snapshotting once and reusing the
    result is what lets ``tools/list`` answer without starting anything. The snapshot is
    keyed by the provider module's size and mtime so upgrading a provider invalidates it
    rather than publishing a stale schema.
    """

    directory: Path

    def __post_init__(self) -> None:
        self.directory = Path(self.directory).expanduser()

    def _path(self, slug: str) -> Path:
        return self.directory / f"{slug}.json"

    @staticmethod
    def _fingerprint(deployment: RemoteDeployment) -> str:
        """Identify the provider implementation without importing it."""

        try:
            import importlib.util

            spec = importlib.util.find_spec(deployment.module)
        except (ImportError, ValueError, ModuleNotFoundError):
            spec = None
        origin = getattr(spec, "origin", None) if spec is not None else None
        if not origin:
            return "unknown"
        try:
            stat = Path(origin).stat()
        except OSError:
            return "unknown"
        return f"{stat.st_size}:{int(stat.st_mtime)}"

    def load(self, deployment: RemoteDeployment) -> list[dict[str, Any]] | None:
        try:
            raw = self._path(deployment.slug).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        try:
            payload = json.loads(raw)
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("fingerprint") != self._fingerprint(deployment):
            return None
        tools = payload.get("tools")
        if not isinstance(tools, list):
            return None
        return [tool for tool in tools if isinstance(tool, dict)]

    def save(self, deployment: RemoteDeployment, tools: list[dict[str, Any]]) -> None:
        if len(tools) > MAX_TOOLS_PER_PROVIDER:
            raise PoolError(
                f"provider '{deployment.slug}' advertised {len(tools)} tools; "
                f"refusing to cache more than {MAX_TOOLS_PER_PROVIDER}"
            )
        payload = {
            "slug": deployment.slug,
            "fingerprint": self._fingerprint(deployment),
            "tools": tools,
        }
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise PoolError(
                f"provider '{deployment.slug}' tools/list snapshot exceeds "
                f"{MAX_SNAPSHOT_BYTES} bytes"
            )
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(deployment.slug)
        # Write-then-rename: a crash mid-write must not leave a half-parsed snapshot that
        # load() would reject on every later start.
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(target)


@dataclass
class _ActiveProvider:
    deployment: RemoteDeployment
    managed: ManagedRemoteProcess | None
    last_used: float
    in_flight: int = 0


@dataclass
class ProviderPool:
    """Start reviewed providers on demand and stop them when they go idle.

    ``python`` is the interpreter from the provider environment, exactly as
    ``tu remote run`` resolves it. The lifecycle callables are injected so the routing,
    admission and eviction rules can be tested without a GPU or a real provider.
    """

    allow: tuple[str, ...]
    python: str
    log_dir: Path
    schemas: SchemaStore
    max_active: int = DEFAULT_MAX_ACTIVE
    idle_ttl: float = DEFAULT_IDLE_TTL
    startup_timeout: float = DEFAULT_STARTUP_TIMEOUT
    footprints: FootprintStore | None = None
    vram_headroom_mib: int = DEFAULT_VRAM_HEADROOM_MIB
    read_free_vram: Callable[[], int | None] = gpu_free_mib
    ensure: Callable[..., tuple[ManagedRemoteProcess | None, dict[str, Any]]] = (
        ensure_provider
    )
    stop: Callable[[ManagedRemoteProcess | None], None] = stop_provider
    discover: Callable[[RemoteDeployment], list[dict[str, Any]]] | None = None
    clock: Callable[[], float] = time.monotonic

    _active: dict[str, _ActiveProvider] = field(default_factory=dict, init=False)
    _starting: set[str] = field(default_factory=set, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        if not self.allow:
            raise PoolError("--allow must name at least one reviewed provider")
        self.tool_index = build_tool_index(self.allow)
        self.deployments = tuple(REMOTE_BY_SLUG[slug] for slug in self.allow)
        if self.max_active < 1:
            raise PoolError("--max-active must be at least 1")
        if self.idle_ttl <= 0:
            raise PoolError("--idle-ttl must be positive")
        if not MIN_STARTUP_TIMEOUT <= self.startup_timeout <= MAX_STARTUP_TIMEOUT:
            raise PoolError(
                f"--startup-timeout must be between {MIN_STARTUP_TIMEOUT:.0f} and "
                f"{MAX_STARTUP_TIMEOUT:.0f} seconds"
            )
        self.log_dir = Path(self.log_dir).expanduser()

    # ── discovery ────────────────────────────────────────────────────────────────

    def known_tools(self) -> list[dict[str, Any]]:
        """Every cached tool across the allowed providers, starting nothing.

        A provider with no snapshot yet contributes nothing rather than blocking the
        listing on a model load. ``warm`` fills those in, and the first call to such a
        tool still routes correctly because routing uses the static operation table, not
        this cache.
        """

        tools: list[dict[str, Any]] = []
        for deployment in self.deployments:
            tools.extend(self.schemas.load(deployment) or ())
        return tools

    def missing_snapshots(self) -> tuple[RemoteDeployment, ...]:
        return tuple(
            deployment
            for deployment in self.deployments
            if self.schemas.load(deployment) is None
        )

    def warm(self, report: Callable[[str], None] | None = None) -> dict[str, str]:
        """Snapshot ``tools/list`` for every provider that has no valid cache entry.

        Each provider is started, probed and stopped one at a time, so warming a host
        advertising many models never needs them resident together.
        """

        results: dict[str, str] = {}
        for deployment in self.missing_snapshots():
            if report:
                report(f"warming {deployment.slug}")
            try:
                tools = self._snapshot(deployment)
            except (PoolError, OSError, RuntimeError, ValueError) as exc:
                results[deployment.slug] = f"failed: {exc}"
                continue
            results[deployment.slug] = f"cached {len(tools)} tools"
        return results

    def _snapshot(self, deployment: RemoteDeployment) -> list[dict[str, Any]]:
        managed, _ = self.ensure(
            deployment,
            python=self.python,
            log_dir=self.log_dir,
            startup_timeout=self.startup_timeout,
        )
        try:
            tools = self._discover_tools(deployment)
            self.schemas.save(deployment, tools)
            return tools
        finally:
            # Only stop what this call started. A provider the operator is running in
            # another terminal must survive a warm.
            if managed is not None:
                self.stop(managed)

    def _discover_tools(self, deployment: RemoteDeployment) -> list[dict[str, Any]]:
        if self.discover is not None:
            return self.discover(deployment)
        return discover_tool_schemas(deployment.endpoint)

    # ── routing ──────────────────────────────────────────────────────────────────

    def provider_for_tool(self, tool_name: str) -> RemoteDeployment:
        deployment = self.tool_index.get(tool_name)
        if deployment is None:
            raise PoolError(f"no shared provider serves tool '{tool_name}'")
        return deployment

    def acquire(self, deployment: RemoteDeployment) -> str:
        """Make a provider ready and claim one in-flight slot on it."""

        with self._lock:
            active = self._active.get(deployment.slug)
            if active is not None:
                active.in_flight += 1
                active.last_used = self.clock()
                return deployment.endpoint
            if deployment.slug in self._starting:
                raise ProviderStarting(
                    f"provider '{deployment.slug}' is still starting; retry shortly"
                )

        # Read the GPU before taking the admission lock: nvidia-smi is a subprocess, and
        # holding the lock across it would serialize every other caller behind a driver
        # that can hang. The reading can go stale between here and the decision below;
        # the headroom is what absorbs that.
        free_before = self._free_vram_for(deployment)

        with self._lock:
            active = self._active.get(deployment.slug)
            if active is not None:
                active.in_flight += 1
                active.last_used = self.clock()
                return deployment.endpoint
            if deployment.slug in self._starting:
                raise ProviderStarting(
                    f"provider '{deployment.slug}' is still starting; retry shortly"
                )
            self._evict_for_locked(deployment, free_before)
            self._starting.add(deployment.slug)

        try:
            managed, _ = self.ensure(
                deployment,
                python=self.python,
                log_dir=self.log_dir,
                startup_timeout=self.startup_timeout,
            )
        except BaseException:
            with self._lock:
                self._starting.discard(deployment.slug)
            raise
        self._record_footprint(deployment, free_before)
        with self._lock:
            self._starting.discard(deployment.slug)
            self._active[deployment.slug] = _ActiveProvider(
                deployment=deployment,
                managed=managed,
                last_used=self.clock(),
                in_flight=1,
            )
        return deployment.endpoint

    def release(self, deployment: RemoteDeployment) -> None:
        with self._lock:
            active = self._active.get(deployment.slug)
            if active is None:
                return
            active.in_flight = max(0, active.in_flight - 1)
            active.last_used = self.clock()

    def _free_vram_for(self, deployment: RemoteDeployment) -> int | None:
        """Current free VRAM, but only when it could change this admission.

        Skipped entirely when nothing has measured this provider yet, so a first load
        never pays for an nvidia-smi call it cannot act on.
        """

        if self.footprints is None or self.footprints.get(deployment.slug) is None:
            return None
        try:
            return self.read_free_vram()
        except (OSError, ValueError):
            return None

    def _record_footprint(
        self, deployment: RemoteDeployment, free_before: int | None
    ) -> None:
        """Learn what this provider costs, by difference across its own start."""

        if self.footprints is None:
            return
        if free_before is None:
            # No reading was taken before the start (the usual case on a first load), so
            # take one now and measure against it on the next start instead of inventing
            # a delta from a baseline we never had.
            try:
                self.read_free_vram()
            except (OSError, ValueError):
                pass
            return
        try:
            free_after = self.read_free_vram()
        except (OSError, ValueError):
            return
        if free_after is None:
            return
        self.footprints.record(deployment.slug, free_before - free_after)

    def _evict_for_locked(
        self, incoming: RemoteDeployment, free_mib: int | None = None
    ) -> None:
        """Free room for ``incoming``, oldest idle provider first.

        Called with the lock held and ``incoming`` not yet active. A provider with
        requests in flight is never evicted; if nothing can be freed the caller is told to
        retry rather than having a running job killed under it.

        Two independent ceilings. ``max_active`` is a count, and applies always. Memory
        applies only once this provider has been measured and a GPU answered: two small
        models may fit where one large one does not, which a count can never express.

        Freed memory is estimated from the victims' own measurements rather than re-read
        from the driver, because a stopped process does not return its VRAM immediately --
        a fresh reading straight after a kill reports the memory as still in use. A victim
        nobody has measured yet counts as freeing nothing, so admission stays conservative
        instead of optimistic.
        """

        def lru_idle_victim() -> _ActiveProvider:
            idle = [active for active in self._active.values() if active.in_flight == 0]
            if not idle:
                raise PoolError(
                    f"all {self.max_active} provider slot(s) are busy; retry shortly"
                )
            return min(idle, key=lambda active: active.last_used)

        while len(self._active) + len(self._starting) >= self.max_active:
            self._stop_locked(lru_idle_victim().deployment.slug)

        if free_mib is None or self.footprints is None:
            return
        needed = self.footprints.get(incoming.slug)
        if needed is None:
            return
        required = needed + self.vram_headroom_mib
        while free_mib < required:
            if not any(active.in_flight == 0 for active in self._active.values()):
                raise PoolError(
                    f"provider '{incoming.slug}' needs {needed} MiB plus "
                    f"{self.vram_headroom_mib} MiB headroom and only {free_mib} MiB is "
                    "free; every resident provider is busy, so retry shortly"
                )
            victim = lru_idle_victim()
            free_mib += self.footprints.get(victim.deployment.slug) or 0
            self._stop_locked(victim.deployment.slug)

    def _stop_locked(self, slug: str) -> None:
        active = self._active.pop(slug, None)
        if active is None:
            return
        if active.managed is not None:
            self.stop(active.managed)

    def reap_idle(self) -> tuple[str, ...]:
        """Stop providers idle for longer than ``idle_ttl``. Returns what was stopped."""

        now = self.clock()
        stopped: list[str] = []
        with self._lock:
            for slug, active in list(self._active.items()):
                if active.in_flight == 0 and now - active.last_used >= self.idle_ttl:
                    self._stop_locked(slug)
                    stopped.append(slug)
        return tuple(stopped)

    def shutdown(self) -> None:
        with self._lock:
            for slug in list(self._active):
                self._stop_locked(slug)

    def status(self) -> list[dict[str, Any]]:
        now = self.clock()
        with self._lock:
            rows = [
                {
                    "provider": slug,
                    "in_flight": active.in_flight,
                    "idle_seconds": round(max(0.0, now - active.last_used), 1),
                    "adopted": active.managed is None,
                }
                for slug, active in sorted(self._active.items())
            ]
            starting = sorted(self._starting)
        return rows + [{"provider": slug, "starting": True} for slug in starting]

    # ── control plane ────────────────────────────────────────────────────────────

    def deployment_for_slug(self, slug: str) -> RemoteDeployment:
        """Resolve an allowed provider by name.

        The allowlist is the security boundary for the control plane: the platform relays
        a provider name chosen by a caller, and acting on it would otherwise let a member
        of a shared host start any reviewed provider on someone else's machine.
        """

        if slug not in self.allow:
            raise PoolError(f"provider '{slug}' is not shared by this host")
        return REMOTE_BY_SLUG[slug]

    def prewarm(self, slug: str) -> dict[str, Any]:
        """Start a provider ahead of the call that needs it, without waiting for it.

        Loading a model takes minutes and a control call is bounded in seconds, so this
        reports what it set in motion and leaves readiness to ``status``. A prewarm that
        is already resident is a no-op rather than a restart.
        """

        deployment = self.deployment_for_slug(slug)
        with self._lock:
            if deployment.slug in self._active:
                return {"provider": slug, "state": "ready"}
            if deployment.slug in self._starting:
                return {"provider": slug, "state": "starting"}

        def load() -> None:
            try:
                self.acquire(deployment)
            except (PoolError, OSError, RuntimeError, ValueError):
                # acquire already unwound its own state; the next status call reports the
                # provider as absent, which is the honest answer.
                return
            # Hold no slot: prewarming must not look like an in-flight call, or the
            # provider could never be evicted or reaped.
            self.release(deployment)

        threading.Thread(target=load, name=f"tu-prewarm-{slug}", daemon=True).start()
        return {"provider": slug, "state": "starting"}

    def unload(self, slug: str) -> dict[str, Any]:
        """Stop one provider if nothing is using it."""

        deployment = self.deployment_for_slug(slug)
        with self._lock:
            active = self._active.get(deployment.slug)
            if active is None:
                return {"provider": slug, "state": "absent"}
            if active.in_flight > 0:
                return {
                    "provider": slug,
                    "state": "busy",
                    "in_flight": active.in_flight,
                }
            self._stop_locked(deployment.slug)
        return {"provider": slug, "state": "stopped"}

    def control(self, op: str, args: Mapping[str, Any]) -> dict[str, Any]:
        """Answer one control operation from the platform.

        Pass this to ``RelayAgent(control_handler=...)``. Raising here would close the
        tunnel, so an operation the host declines is reported in the result instead.
        """

        if op == "status":
            answer: dict[str, Any] = {
                "providers": self.status(),
                "allowed": list(self.allow),
                "max_active": self.max_active,
                "idle_ttl": self.idle_ttl,
            }
            if self.footprints is not None:
                # Only what has actually been measured. A provider missing from this map
                # has never been loaded here, and is admitted on count alone until it has.
                answer["measured_vram_mib"] = {
                    slug: self.footprints.get(slug)
                    for slug in self.allow
                    if self.footprints.get(slug) is not None
                }
                answer["vram_headroom_mib"] = self.vram_headroom_mib
                try:
                    free = self.read_free_vram()
                except (OSError, ValueError):
                    free = None
                answer["free_vram_mib"] = free
            return answer
        slug = args.get("provider")
        if not isinstance(slug, str) or not slug:
            return {"error": "provider is required"}
        try:
            if op == "prewarm":
                return self.prewarm(slug)
            if op == "stop":
                return self.unload(slug)
        except PoolError as exc:
            return {"provider": slug, "error": str(exc)}
        return {"error": f"unsupported control operation '{op}'"}


def discover_tool_schemas(
    endpoint: str, timeout: float = 120.0
) -> list[dict[str, Any]]:
    """Read one provider's full tool definitions, schemas included.

    ``remote_runtime.discover_endpoint`` answers the different question of whether a
    provider serves exactly its expected operation names, so it returns names only.
    Publishing a usable manifest needs each tool's input schema too, otherwise callers
    can see a tool but cannot construct a valid call for it.
    """

    import asyncio

    async def read() -> list[dict[str, Any]]:
        from fastmcp import Client

        async with asyncio.timeout(timeout):
            async with Client(endpoint) as client:
                tools = await client.list_tools()
        definitions: list[dict[str, Any]] = []
        for tool in tools:
            definition: dict[str, Any] = {"name": tool.name}
            for attribute, key in (
                ("description", "description"),
                ("inputSchema", "inputSchema"),
                ("outputSchema", "outputSchema"),
            ):
                value = getattr(tool, attribute, None)
                if value:
                    definition[key] = value
            definitions.append(definition)
        return definitions

    return asyncio.run(read())


def proxy_call(
    endpoint: str, payload: Mapping[str, Any], timeout: float = PROXY_TIMEOUT
) -> tuple[int, bytes]:
    """Forward one JSON-RPC message to a provider endpoint."""

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        with exc:
            return int(exc.status or 502), exc.read()


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _jsonrpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


class PoolMCPHandler(BaseHTTPRequestHandler):
    """A sessionless Streamable-HTTP MCP endpoint in front of :class:`ProviderPool`.

    Sessionless on purpose: the relay agent treats a missing ``mcp-session-id`` as fine
    and the pool holds no per-caller state, so there is no session to lose when a
    provider underneath is stopped and restarted between two calls.
    """

    protocol_version = "HTTP/1.1"
    server_version = "tooluniverse-remote-pool/1"

    # Set by serve_pool.
    pool: ProviderPool

    def log_message(self, fmt: str, *args: Any) -> None:
        # BaseHTTPRequestHandler logs every request to stderr, which would bury the
        # provider lifecycle lines the operator actually needs.
        return

    def _respond(
        self, status: int, payload: Any, extra: Mapping[str, str] = {}
    ) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in extra.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _respond_raw(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_DELETE(self) -> None:
        # Session teardown. There is no session, so acknowledge without touching state.
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        # No server-initiated SSE stream. Deliberately not 405: the relay agent treats a
        # 405 on its POST route as endpoint loss, and keeping the two paths distinct
        # avoids any chance of a GET probe tearing down a healthy shared tunnel.
        self._respond(501, {"detail": "pool endpoint does not implement an SSE stream"})

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length < 0 or length > MAX_SNAPSHOT_BYTES:
            self._respond(413, {"detail": "request body too large"})
            return
        raw = self.rfile.read(length) if length else b""
        try:
            message = json.loads(raw or b"{}")
        except ValueError:
            self._respond(
                400, _jsonrpc_error(None, _JSONRPC_PARSE_ERROR, "invalid JSON")
            )
            return
        if not isinstance(message, dict):
            self._respond(
                400,
                _jsonrpc_error(
                    None, _JSONRPC_INVALID_REQUEST, "expected a JSON object"
                ),
            )
            return

        method = message.get("method")
        request_id = message.get("id")
        if not isinstance(method, str):
            self._respond(
                400,
                _jsonrpc_error(request_id, _JSONRPC_INVALID_REQUEST, "missing method"),
            )
            return

        # Notifications carry no id and expect no body.
        if request_id is None and method.startswith("notifications/"):
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if method == "initialize":
            self._respond(
                200,
                _jsonrpc_result(
                    request_id,
                    {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {
                            "name": "tooluniverse-remote-pool",
                            "version": "1",
                        },
                    },
                ),
            )
            return

        if method == "ping":
            self._respond(200, _jsonrpc_result(request_id, {}))
            return

        if method == "tools/list":
            # Answered entirely from cached snapshots: discovery never starts a model.
            self._respond(
                200, _jsonrpc_result(request_id, {"tools": self.pool.known_tools()})
            )
            return

        if method != "tools/call":
            self._respond(
                200,
                _jsonrpc_error(
                    request_id,
                    _JSONRPC_METHOD_NOT_FOUND,
                    f"unsupported method '{method}'",
                ),
            )
            return

        params = message.get("params")
        tool_name = params.get("name") if isinstance(params, Mapping) else None
        if not isinstance(tool_name, str) or not tool_name:
            self._respond(
                200,
                _jsonrpc_error(
                    request_id,
                    _JSONRPC_INVALID_PARAMS,
                    "tools/call requires params.name",
                ),
            )
            return

        try:
            deployment = self.pool.provider_for_tool(tool_name)
        except PoolError as exc:
            self._respond(
                200, _jsonrpc_error(request_id, _JSONRPC_METHOD_NOT_FOUND, str(exc))
            )
            return

        try:
            endpoint = self.pool.acquire(deployment)
        except ProviderStarting:
            # 503 rather than a JSON-RPC error: the caller should retry the same call, and
            # a protocol-level error would read as "this tool is broken".
            self._respond(
                503,
                {"detail": "the provider is loading this model; retry shortly"},
                {"Retry-After": "15"},
            )
            return
        except PoolError as exc:
            # The exception text carries this host's capacity and GPU numbers, which are
            # useful in the operator's log and must not be handed to whoever made the
            # call. A member who could read them could poll free VRAM and infer what
            # other people on this machine just loaded, so the caller is told only that
            # it should come back.
            print(f"  Admission refused: {exc}", flush=True)
            self._respond(
                503,
                {"detail": "the provider is at capacity; retry shortly"},
                {"Retry-After": "10"},
            )
            return
        except (OSError, RuntimeError, ValueError) as exc:
            # The slug is already public -- it is how the caller reached this tool -- but
            # the exception text can carry interpreter paths, log locations and ports.
            print(f"  Start failed for {deployment.slug}: {exc}", flush=True)
            self._respond(
                200,
                _jsonrpc_error(
                    request_id,
                    _JSONRPC_INTERNAL_ERROR,
                    f"provider '{deployment.slug}' could not be started on this host",
                ),
            )
            return

        try:
            status, body = proxy_call(endpoint, message)
        except (urllib.error.URLError, TimeoutError, OSError):
            self._respond(
                200,
                _jsonrpc_error(
                    request_id,
                    _JSONRPC_INTERNAL_ERROR,
                    f"provider '{deployment.slug}' did not answer",
                ),
            )
            return
        finally:
            self.pool.release(deployment)
        self._respond_raw(status, body)


def serve_pool(
    pool: ProviderPool, port: int = DEFAULT_POOL_PORT, host: str = "127.0.0.1"
) -> ThreadingHTTPServer:
    """Bind the multiplexed MCP endpoint. Loopback only; the relay is the public door."""

    handler = type("BoundPoolMCPHandler", (PoolMCPHandler,), {"pool": pool})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def start_reaper(pool: ProviderPool, interval: float = 30.0) -> threading.Event:
    """Run :meth:`ProviderPool.reap_idle` in the background. Returns its stop switch."""

    stop = threading.Event()

    def loop() -> None:
        while not stop.wait(interval):
            try:
                for slug in pool.reap_idle():
                    print(f"  Stopped idle provider: {slug}", flush=True)
            except (OSError, RuntimeError, ValueError) as exc:
                print(f"  Idle sweep failed: {exc}", flush=True)

    threading.Thread(target=loop, name="tu-remote-pool-reaper", daemon=True).start()
    return stop
