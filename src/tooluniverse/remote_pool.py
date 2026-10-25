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
``max_active`` 0 drops that count and leaves the decision to the memory ceiling below.

A call that lands while a provider is still starting gets 503 with Retry-After rather
than being queued across the relay, which the relay's own 25-second limit on a local
request makes the only safe answer there; ``start_wait_s`` lets a host serving its own
endpoint wait for that start instead, and is 0 by default. ``control`` answers
``prewarm``/``stop``/``status`` for a relay that offers a control plane, which
``tu serve`` wires up only when the installed ``RelayAgent`` takes one, and ``prewarm``
loads the model rather than only starting the server that will load it.

Admission applies two ceilings. ``max_active`` is a count, and ``--max-active 0`` drops
it so memory decides alone -- refused on a machine whose memory cannot be read, where
dropping it would leave nothing deciding at all. Memory
applies wherever the machine can be read, and the reading is per machine rather than
per card: a discrete device's own ``memory.free``, ``MemAvailable`` on unified memory
where the device has no memory of its own, and nothing at all on a host with no NVIDIA
driver, which stays count-only. What a model costs is the larger of its manifest's
measured ``[gpu] vram_budget_gb`` and what this host has measured it to cost here --
and the local measurement is taken after a call the provider answered, because nothing
in this catalog has its model in memory when its port starts answering. See
``docs/dev_docs/Remote_Provider_Pool_Design.md``.
"""

from __future__ import annotations

import json
import socket
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

from .remote_resident import admission
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

# ``--max-active 0``: no count ceiling, let memory decide. A count is the wrong unit for
# the question it is asked -- it cannot say that two 6 GiB models fit where one 38 GiB
# model does not -- and it was the only unit this pool had before it could read the
# machine. 0 is refused where the machine cannot be read, because that would leave
# nothing deciding at all, and it still bounds providers whose cost nobody knows: see
# :meth:`ProviderPool._evict_for_locked`.
NO_COUNT_CEILING = 0
DEFAULT_STARTUP_TIMEOUT = 600.0

# How long a call waits for a provider another call is already starting, and ZERO IS THE
# DEFAULT, which is the answer a measurement produced rather than the cautious-looking
# one. Waiting is the obvious improvement: the second of two near-simultaneous first-calls
# is refused while a CPU-only process binds a port, and it could simply have waited. The
# numbers say otherwise behind a relay. Starting boltz's MCP server on this project's GB10
# takes 12.5 s to bind (measured, and most of it is importing ToolUniverse in the child),
# while a relay agent abandons a local request after 25 s and that timeout takes the
# tunnel down for every caller on the host. So a wait long enough to be useful is most of
# the way to an outage, and the platform already absorbs the same delay the safe way, by
# re-dispatching a 503 after 2 s, 4 s and 8 s.
#
# It is a field rather than nothing at all because the cliff belongs to the relay, not to
# the pool: a host serving its own MCP endpoint without `--share` has a client whose
# timeout is its own business, and there a few seconds of waiting turn a failed first call
# into an answered one.
DEFAULT_START_WAIT_S = 0.0

# Proxied tool calls can be long GPU jobs. The platform enforces each call's own deadline and
# caps every one at 15 minutes, so this only prevents a wedged provider from pinning a pool
# thread forever.
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


class ProviderTooLarge(PoolError):
    """This machine could not hold this provider even with nothing else resident.

    Separate from the other refusals because it is permanent: no eviction and no
    retry changes it, so telling the caller to come back shortly would be wrong.
    """


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


def pool_free_mib(timeout: float = 15.0) -> int | None:
    """Free memory in the pool the next model allocates from, on whatever machine this is.

    Delegates to :func:`admission.pool_free_gib`, where this fleet's three kinds of
    machine are already told apart for the resident gate. Asking the device directly
    was this module's first answer and it stopped applying silently on unified memory:
    ``nvidia-smi --query-gpu=memory.free`` prints ``[N/A]`` on this fleet's GB10 --
    measured, not reasoned -- so the reading was None, so every ceiling built on it was
    skipped, on a host with 121 GiB worth reasoning about.

    None still means "do not reason about memory". That is the right answer on a host
    with no NVIDIA driver, where admission is the count alone, and the wrong answer to
    reach by accident on a host with memory it could have read.
    """

    free_gib, _source = admission.pool_free_gib(timeout=timeout)
    if free_gib is None:
        return None
    return int(round(free_gib * 1024))


def pool_capacity_mib() -> int | None:
    """The size of that pool, which bounds what this machine can ever hold.

    A provider measured at 38.63 GiB on the machine that verified it cannot run on a
    24 GiB card, and a count ceiling has no way to say so: it starts the model, waits
    out the load, and hands the caller whatever the kit says when the allocation fails.
    Capacity is the one memory fact that does not move, so it is read once and the
    refusal it supports is raised before anything is started or stopped.
    """

    capacity_gib, _source = admission.capacity_gib()
    if capacity_gib is None:
        return None
    return int(round(capacity_gib * 1024))


def declared_footprint_mib(slug: str) -> int | None:
    """What a provider's own manifest says it costs, as a prior for this machine.

    ``[gpu] vram_budget_gb`` is a measured peak -- ``tu remote room`` prints 28 of them
    -- but measured on the machine that verified the provider, which makes it a prior
    anywhere else and not a reading. It is what lets a provider's FIRST load here be
    admitted on memory instead of on count alone, and it never stands in for a larger
    local measurement.

    0 is an answer, not a gap: a manifest declaring ``[gpu] policy = "none"`` holds no
    device memory at all, so no memory ceiling applies to it and it evicts nobody.
    None means nothing declares this provider's cost -- 28 of the 60 reviewed slugs,
    all of them older non-resident providers -- and those are admitted on count alone,
    exactly as every provider was before this.
    """

    budget_gb = admission.declared_budget_gb(slug)
    if budget_gb is None:
        return None
    return int(round(budget_gb * 1024))


@dataclass
class FootprintStore:
    """What THIS host measured a provider to cost, cached on disk.

    The local reading, which is a different thing from the declared one. 28 manifests
    carry a measured ``[gpu] vram_budget_gb`` that :func:`declared_footprint_mib` reads,
    and that figure was measured on the machine which verified the provider -- so it is
    what makes a first load here memory-aware, and this store is what the pool learns
    about this machine: free memory before the provider started, free memory once it has
    answered a call, and the difference. Admission uses the larger of the two, because
    each can be the low one (see :meth:`ProviderPool.footprint_mib`).

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
    # Free memory as it was just before this provider's server started, and whether
    # what it holds has been measured against that baseline yet. Both belong to one
    # residency: a provider that is stopped and started again is measured again, from
    # a new baseline, because the machine around it has moved on.
    baseline_free_mib: int | None = None
    measured: bool = False


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
    start_wait_s: float = DEFAULT_START_WAIT_S
    # Names an operator chose to let providers see beyond what each one declares. Empty by
    # default: a provider's own declaration is the contract, and widening it is a decision
    # the machine's owner makes explicitly.
    extra_env: tuple[str, ...] = ()
    footprints: FootprintStore | None = None
    vram_headroom_mib: int = DEFAULT_VRAM_HEADROOM_MIB
    read_free_vram: Callable[[], int | None] = pool_free_mib
    read_capacity: Callable[[], int | None] = pool_capacity_mib
    declared_footprint: Callable[[str], int | None] = declared_footprint_mib
    # Whether a provider keeps its model in a worker of its own, which is what decides
    # WHEN this pool can measure what that model costs, and `machine_holdings`, which
    # says whether such a worker is up right now. Injected like the readings above so
    # the measurement rules can be tested without a provider environment.
    holds_model_in_worker: Callable[[str], bool] = admission.declares_resident_worker
    read_holdings: Callable[[], Mapping[str, float | None]] = admission.machine_holdings
    ensure: Callable[..., tuple[ManagedRemoteProcess | None, dict[str, Any]]] = (
        ensure_provider
    )
    stop: Callable[[ManagedRemoteProcess | None], None] = stop_provider
    discover: Callable[[RemoteDeployment], list[dict[str, Any]]] | None = None
    clock: Callable[[], float] = time.monotonic

    _active: dict[str, _ActiveProvider] = field(default_factory=dict, init=False)
    _starting: set[str] = field(default_factory=set, init=False)
    _capacity_cache: int | None = field(default=None, init=False)
    # A condition rather than a plain lock: it still guards every read and write of the
    # two collections above, and it is also where a call waits for a start another call
    # is already running, instead of being refused the moment it finds one in progress.
    _lock: threading.Condition = field(default_factory=threading.Condition, init=False)

    def __post_init__(self) -> None:
        if not self.allow:
            raise PoolError("--allow must name at least one reviewed provider")
        self.tool_index = build_tool_index(self.allow)
        self.deployments = tuple(REMOTE_BY_SLUG[slug] for slug in self.allow)
        if self.max_active < NO_COUNT_CEILING:
            raise PoolError("--max-active must not be negative")
        if self.max_active == NO_COUNT_CEILING and self._capacity_mib() is None:
            # Capacity rather than the free reading: both come from the same detection of
            # which kind of machine this is, and capacity is the one that does not move,
            # so a pool is not refused over a driver that was busy for a second. If this
            # answers, memory is readable here and is a ceiling; if it does not, there is
            # no second ceiling to fall back on and "0" would mean "unbounded".
            raise PoolError(
                "--max-active 0 leaves the decision to memory, and this machine's "
                "memory pool cannot be read, so nothing would bound what runs at "
                "once; pass a count instead"
            )
        if self.idle_ttl <= 0:
            raise PoolError("--idle-ttl must be positive")
        if self.start_wait_s < 0:
            raise PoolError("--start-wait must not be negative")
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
            extra_env=self.extra_env,
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

    def acquire(self, deployment: RemoteDeployment, *, warm_model: bool = False) -> str:
        """Make a provider ready and claim one in-flight slot on it.

        ``warm_model`` asks the provider to load its model as it starts rather than on
        the first request that needs it. Only :meth:`prewarm` passes it: a real call
        loads the model by being the request that loads it.
        """

        with self._lock:
            endpoint = self._claim_locked(deployment)
            if endpoint is not None:
                return endpoint

        # Both readings happen before the admission lock: each is a subprocess, and
        # holding the lock across one would serialize every other caller behind a driver
        # that can hang. The free reading can go stale between here and the decision
        # below; the headroom is what absorbs that.
        self._refuse_if_larger_than_the_machine(deployment)
        free_before = self._free_vram_for(deployment)

        with self._lock:
            endpoint = self._claim_locked(deployment)
            if endpoint is not None:
                return endpoint
            self._evict_for_locked(deployment, free_before)
            self._starting.add(deployment.slug)

        try:
            managed, _ = self.ensure(
                deployment,
                python=self.python,
                log_dir=self.log_dir,
                startup_timeout=self.startup_timeout,
                extra_env=self.extra_env,
                warm_model=warm_model,
            )
        except BaseException:
            with self._lock:
                self._starting.discard(deployment.slug)
                # Whoever was waiting for this start is better off attempting its own
                # than waiting out a start that is already over.
                self._lock.notify_all()
            raise
        with self._lock:
            self._starting.discard(deployment.slug)
            self._active[deployment.slug] = _ActiveProvider(
                deployment=deployment,
                managed=managed,
                last_used=self.clock(),
                in_flight=1,
                baseline_free_mib=free_before,
            )
            self._lock.notify_all()
        return deployment.endpoint

    def _claim_locked(self, deployment: RemoteDeployment) -> str | None:
        """Claim an in-flight slot on this provider, waiting out a start in progress.

        Called with the lock held. Returns the endpoint when a slot was claimed, and
        None when this caller is the one that has to start the provider.

        WHY THIS WAITS AT ALL. Two calls for the same cold provider arrive seconds
        apart all the time -- a platform fan-out, an agent retrying its own tool call --
        and the second one used to be refused the moment it found the first one's start
        in progress. Nothing was wrong with the pool at that moment: a CPU-only process
        was binding a port, which takes seconds. So the caller waits for it instead, up
        to ``start_wait_s``, and is told to retry only if the start is still running
        after that -- the case waiting cannot absorb, which is a model being loaded on
        a provider nobody prewarmed.

        The deadline is real time rather than ``clock``: ``clock`` is injected so that
        idle accounting can be driven by a test, and a wait honouring a frozen clock
        would never end.
        """

        deadline = time.monotonic() + self.start_wait_s
        while True:
            active = self._active.get(deployment.slug)
            if active is not None:
                active.in_flight += 1
                active.last_used = self.clock()
                return deployment.endpoint
            if deployment.slug not in self._starting:
                return None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderStarting(
                    f"provider '{deployment.slug}' is still starting; retry shortly"
                )
            self._lock.wait(remaining)

    def release(self, deployment: RemoteDeployment) -> None:
        with self._lock:
            active = self._active.get(deployment.slug)
            if active is None:
                return
            active.in_flight = max(0, active.in_flight - 1)
            active.last_used = self.clock()

    def footprint_mib(self, slug: str) -> int | None:
        """What this provider is expected to cost here, or None when nobody has said.

        The larger of the manifest's declared budget and this host's own measurement,
        and taking the maximum is deliberate in both directions:

        * a DECLARED budget can be low here, because it was measured on the machine
          that verified the provider and this is not that machine;
        * a MEASURED footprint can be low, because a resident provider loads its model
          on the first request rather than when its server binds -- ``wait_until_ready``
          waits for ``tools/list`` to match the reviewed contract, which it does with
          the card still empty -- so the difference across a start can be a fraction of
          what the model holds a second later.

        Neither is wrong often, and either being low overcommits the machine, so the
        conservative answer is the larger.
        """

        measured = self.footprints.get(slug) if self.footprints is not None else None
        declared = self.declared_footprint(slug)
        if measured is None:
            return declared
        if declared is None:
            return measured
        return max(measured, declared)

    def _capacity_mib(self) -> int | None:
        """This machine's pool size. Read once; a failed reading is not cached.

        Capacity does not move, but a driver that was briefly unavailable must not
        leave this pool admitting on count alone for the rest of its life.
        """

        if self._capacity_cache is None:
            try:
                self._capacity_cache = self.read_capacity()
            except (OSError, ValueError):
                return None
        return self._capacity_cache

    def _refuse_if_larger_than_the_machine(self, deployment: RemoteDeployment) -> None:
        """Refuse what this machine could not hold with nothing else resident.

        Raised before anything is evicted, because evicting first and failing anyway
        would cost someone else's loaded model for nothing. Silent when the capacity
        cannot be read, which keeps a host with no readable device on count alone.
        """

        needed = self.footprint_mib(deployment.slug)
        capacity = self._capacity_mib()
        if not needed or capacity is None:
            return
        if needed + self.vram_headroom_mib > capacity:
            raise ProviderTooLarge(
                f"provider '{deployment.slug}' needs {needed} MiB plus "
                f"{self.vram_headroom_mib} MiB headroom, and this machine's memory "
                f"pool is {capacity} MiB; nothing it could evict would make room"
            )

    def _free_vram_for(self, deployment: RemoteDeployment) -> int | None:
        """This machine's free memory, read once for this start, or None.

        Two things want it, and between them they are why it is not conditional on the
        provider's cost being known: the admission decision, which only a known cost
        can use, and the baseline this residency's own measurement is taken against,
        which is wanted precisely when the cost is NOT known yet.

        None for a provider that declares it holds no device memory: it can be refused
        for nothing and measured for nothing, so the reading would be spent to be
        discarded. None too when this pool records no measurements and this provider's
        cost is unknown -- nothing to decide and nowhere to put a reading.
        """

        if self.declared_footprint(deployment.slug) == 0:
            return None
        if self.footprints is None and not self.footprint_mib(deployment.slug):
            return None
        try:
            return self.read_free_vram()
        except (OSError, ValueError):
            return None

    def learn_footprint(self, deployment: RemoteDeployment) -> None:
        """Measure what this provider costs, now that it has answered a call.

        WHERE THIS USED TO BE AND WHY IT MOVED. Every measurement this pool took was a
        difference across a provider's START, and NOTHING IN THIS CATALOG HAS ITS MODEL
        IN MEMORY WHEN ITS PORT STARTS ANSWERING. A resident provider loads its weights
        in a worker, started by the first request. A provider with no manifest holds its
        model in the server process -- and loads it on the first request too, lazily:
        ``esm_tool`` says so in as many words ("lazy load on first use"), which is how
        anything serves `tools/list` before its weights exist. So the figure recorded
        was the MCP server's own memory, every time. The 28 providers whose manifest
        declares a budget were covered by :meth:`footprint_mib` taking the larger of the
        two; for a provider with nothing declared that small number was the only figure
        admission had, and being optimistic about a model's cost is the one direction
        that ends in an out-of-memory instead of a refusal.

        Measured here instead: after a call this provider answered, while it is still up
        and still holding what the call made it allocate. The baseline is the reading
        taken before its server started, so a model loaded at import is inside the
        difference as surely as one loaded by the call. That makes the figure a residency
        cost and not a request peak -- the peak is what a manifest's ``vram_budget_gb``
        carries, measured deliberately rather than off whichever call happened to be
        first.

        Once per residency. A call can be answered without a model ever loading -- a
        rejected argument, a cached answer -- and for a provider that keeps a worker the
        process table says which happened, so that is checked. For a provider holding its
        model in the server process there is no such evidence to be had: a call that
        loaded nothing records a small figure, and ``FootprintStore.record`` keeping the
        largest value ever seen is what corrects it on the first call that does load.
        That same rule makes a reading inflated by another tenant's allocation sticky,
        which is the conservative direction to be wrong in.
        """

        if self.footprints is None:
            return
        slug = deployment.slug
        if self.declared_footprint(slug) == 0:
            # Declared to hold no device memory, so a difference here would be whatever
            # else on the machine allocated meanwhile, attributed to a provider that
            # cannot have been the cause -- and then held against it as a ceiling.
            return
        with self._lock:
            active = self._active.get(slug)
            if active is None or active.measured:
                return
            baseline = active.baseline_free_mib
        if baseline is None:
            return
        if self.holds_model_in_worker(slug) and not self._worker_is_up(slug):
            return
        try:
            free_now = self.read_free_vram()
        except (OSError, ValueError):
            return
        if free_now is None:
            return
        with self._lock:
            active = self._active.get(slug)
            if active is None or active.measured:
                return
            active.measured = True
        self.footprints.record(slug, baseline - free_now)

    def _worker_is_up(self, slug: str) -> bool:
        """Whether a resident worker for ``slug`` is running on this machine.

        From the process table rather than from the worker's socket, for the reason
        ``admission.machine_holdings`` sets out: a stale socket outlives its worker, so a
        socket is evidence of a past one. Only a worker from THIS checkout counts --
        those are keyed by the bare slug, another checkout's by ``slug@tree`` -- because
        a difference measured while someone else's copy of the same provider is loading
        would charge their memory to this pool's model.
        """

        try:
            holdings = self.read_holdings()
        except (OSError, ValueError, RuntimeError):
            return False
        return slug in holdings

    def _evict_for_locked(
        self, incoming: RemoteDeployment, free_mib: int | None = None
    ) -> None:
        """Free room for ``incoming``, oldest idle provider first.

        Called with the lock held and ``incoming`` not yet active. A provider with
        requests in flight is never evicted; if nothing can be freed the caller is told to
        retry rather than having a running job killed under it.

        Two independent ceilings. ``max_active`` is a count, and ``--max-active 0`` drops
        it in favour of the one below. Memory
        applies once this provider's cost is known -- declared by its manifest or measured
        here, whichever is larger -- and the machine answered a free reading: two small
        models may fit where one large one does not, which a count can never express.

        Freed memory is estimated from the victims' own footprints rather than re-read
        from the driver, because a stopped process does not return its memory immediately
        -- a fresh reading straight after a kill reports it as still in use. A victim whose
        cost nobody declared or measured counts as freeing nothing, so admission stays
        conservative instead of optimistic.

        WHAT BOUNDS A POOL WITH NO COUNT CEILING. Memory can only decide about a provider
        somebody has costed, and 28 of the 60 reviewed slugs declare nothing: for those
        :meth:`footprint_mib` is None, the memory ceiling returns early, and with the
        count gone nothing at all would stop the next one. So an UNCOSTED provider keeps
        the ceiling every provider used to have -- one at a time -- until a call it
        answered has been measured here and memory can speak for it. That bound is on
        ignorance and not on size: a 6 GiB model and a 38 GiB model both have a figure,
        and memory is allowed to decide about both.
        """

        def lru_idle_victim(
            among: Iterable[_ActiveProvider] | None = None,
        ) -> _ActiveProvider:
            candidates = self._active.values() if among is None else among
            idle = [active for active in candidates if active.in_flight == 0]
            if not idle:
                raise PoolError(
                    f"provider '{incoming.slug}' needs room, and every provider that "
                    "could make room for it is busy with a request in flight; retry "
                    "shortly"
                )
            return min(idle, key=lambda active: active.last_used)

        def uncosted(slug: str) -> bool:
            # None is "nobody has said", which is not 0: a manifest declaring
            # `policy = "none"` says this provider holds no device memory, and that is
            # knowledge, not a gap. See :func:`declared_footprint_mib`.
            return self.footprint_mib(slug) is None

        if self.max_active == NO_COUNT_CEILING:
            while uncosted(incoming.slug) and (
                any(uncosted(slug) for slug in self._active)
                or any(uncosted(slug) for slug in self._starting)
            ):
                resident = [
                    active
                    for active in self._active.values()
                    if uncosted(active.deployment.slug)
                ]
                # Nothing resident to evict means the other uncosted provider is still
                # starting, and lru_idle_victim turns that into "retry shortly" rather
                # than killing a start in progress.
                self._stop_locked(lru_idle_victim(resident).deployment.slug)
        else:
            while len(self._active) + len(self._starting) >= self.max_active:
                self._stop_locked(lru_idle_victim().deployment.slug)

        if free_mib is None:
            return
        needed = self.footprint_mib(incoming.slug)
        if not needed:
            return
        required = needed + self.vram_headroom_mib
        while free_mib < required:
            if not any(active.in_flight == 0 for active in self._active.values()):
                # "Every resident provider is busy" is vacuously true of an empty
                # pool, and an operator reading that in a log would go looking for a
                # resident model that was never there. With nothing to evict, the
                # memory is being held by something this pool did not start.
                why = (
                    "every resident provider is busy"
                    if self._active
                    else "nothing of this pool's is resident to evict, so the memory "
                    "is held by something else on the machine"
                )
                raise PoolError(
                    f"provider '{incoming.slug}' needs {needed} MiB plus "
                    f"{self.vram_headroom_mib} MiB headroom and only {free_mib} MiB is "
                    f"free; {why}, so retry shortly"
                )
            victim = lru_idle_victim()
            free_mib += self.footprint_mib(victim.deployment.slug) or 0
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
        """What is resident, what is starting, and which of them hold their model.

        ``model_loaded`` is the fact ``prewarm`` would otherwise be taken on trust for.
        A resident provider counts as up once its server answers ``tools/list``, which
        it does with the card still empty, so "the provider is running" and "the model
        is in memory" are two different answers and anything deciding what to prewarm
        needs the second one. Present only for providers that keep a worker -- for the
        rest, running IS loaded -- and left out entirely when the process table cannot
        be read, rather than guessed at.
        """

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
        with_worker = [
            row for row in rows if self.holds_model_in_worker(row["provider"])
        ]
        if with_worker:
            try:
                holdings: Mapping[str, float | None] | None = self.read_holdings()
            except (OSError, ValueError, RuntimeError):
                holdings = None
            if holdings is not None:
                for row in with_worker:
                    row["model_loaded"] = row["provider"] in holdings
        return rows + [{"provider": slug, "starting": True} for slug in starting]

    def memory_plan(self) -> dict[str, Any]:
        """What the memory ceiling will decide on, for an operator to read at startup.

        Said once at startup rather than discovered through a refused call, because the
        declared budgets were measured on the machines that verified the providers: a
        host smaller than one of those is exactly where that difference surfaces, and
        `too_large` is the list a caller would otherwise find one 503 at a time.
        """

        capacity = self._capacity_mib()
        expected = {slug: self.footprint_mib(slug) for slug in self.allow}
        too_large = tuple(
            slug
            for slug, mib in expected.items()
            if mib and capacity is not None and mib + self.vram_headroom_mib > capacity
        )
        return {
            "capacity_mib": capacity,
            "expected_mib": expected,
            "too_large": too_large,
        }

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

        AND LOAD ITS MODEL. Starting a resident provider's server is seconds and loading
        its weights is minutes, and this used to do only the first: the server bound its
        port, ``status`` reported the provider ready, and the next real call still paid
        the whole load. So a prewarm asks for a warm start -- the provider loads its
        model as it comes up -- and ``status`` reports ``model_loaded`` for anything that
        keeps a worker, which is what tells the difference.

        Loading takes minutes and a control call is bounded in seconds, so this reports
        what it set in motion and leaves readiness to ``status``. A prewarm of a provider
        that is already running is a no-op rather than a restart, and that includes one
        whose server is up without its model: restarting it would be the one way to warm
        it, and it is also the way to kill a call that is about to arrive.
        """

        deployment = self.deployment_for_slug(slug)
        with self._lock:
            if deployment.slug in self._active:
                return {"provider": slug, "state": "ready"}
            if deployment.slug in self._starting:
                return {"provider": slug, "state": "starting"}

        def load() -> None:
            try:
                self.acquire(deployment, warm_model=True)
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
            # What admission will actually decide on, which is not the measured map: it
            # includes the manifests' declared budgets, and an operator comparing a
            # refusal against `measured_vram_mib` alone would be reading the wrong
            # column.
            expected = {}
            for slug in self.allow:
                mib = self.footprint_mib(slug)
                if mib is not None:
                    expected[slug] = mib
            answer["expected_vram_mib"] = expected
            answer["pool_capacity_mib"] = self._capacity_mib()
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



def suggest_free_port(avoid: int, deployments: Iterable[RemoteDeployment] = ()) -> int | None:
    """Find a port that is free right now and belongs to no reviewed provider.

    Offering a number without checking it is how one collision becomes two: 7999 + 1 is 8000,
    which is free of providers and is also the port a locally running platform listens on.
    Someone told to try it lands in the same error with a different number.
    """
    taken = {deployment.port for deployment in deployments}
    taken.add(avoid)
    for candidate in range(avoid + 1, avoid + 40):
        if candidate in taken or candidate > 65535:
            continue
        probe = socket.socket()
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", candidate))
        except OSError:
            continue
        finally:
            probe.close()
        return candidate
    return None

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
            # a protocol-level error would read as "this tool is broken". `acquire` has
            # already waited `start_wait_s` for that start, so what is left really is a
            # model being loaded and not a port being bound.
            self._respond(
                503,
                {"detail": "the provider is loading this model; retry shortly"},
                {"Retry-After": "15"},
            )
            return
        except ProviderTooLarge as exc:
            # Not a 503: this model does not fit on this host and will not fit later, so
            # a Retry-After would send the caller into a loop that cannot succeed. The
            # numbers stay in the operator's log for the same reason as below.
            print(f"  Refused {deployment.slug}: {exc}", flush=True)
            self._respond(
                200,
                _jsonrpc_error(
                    request_id,
                    _JSONRPC_INTERNAL_ERROR,
                    f"provider '{deployment.slug}' cannot run on this host",
                ),
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
        else:
            # The provider has answered, so a resident one is holding its model now:
            # this is the moment its cost on this machine can be measured, and the slot
            # is still in flight, so nothing can stop it between the reading and the
            # record.
            self.pool.learn_footprint(deployment)
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
