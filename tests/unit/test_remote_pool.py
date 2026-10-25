"""The on-demand provider pool: routing, admission, eviction and lazy discovery.

The pool exists so one command can advertise more models than the GPU could hold at
once, starting each only when a call for it arrives. These tests drive that with
injected lifecycle callables, so every rule is checked without a GPU, a provider
environment, or the platform. No network.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tooluniverse.remote_pool import (
    DEFAULT_MAX_ACTIVE,
    PoolError,
    ProviderPool,
    ProviderStarting,
    ProviderTooLarge,
    SchemaStore,
    build_tool_index,
    declared_footprint_mib,
    pool_free_mib,
    serve_pool,
)
from tooluniverse.remote_runtime import REMOTE_BY_SLUG


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Lifecycle:
    """Records provider start/stop instead of launching anything."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []
        self.warmed: list[str] = []
        self.fail: set[str] = set()

    def ensure(
        self,
        deployment,
        *,
        python,
        log_dir,
        startup_timeout,
        extra_env=(),
        warm_model=False,
    ):
        if deployment.slug in self.fail:
            raise RuntimeError(f"boom: {deployment.slug}")
        self.started.append(deployment.slug)
        if warm_model:
            self.warmed.append(deployment.slug)
        return object(), {"endpoint": deployment.endpoint, "ok": True}

    def stop(self, managed) -> None:
        self.stopped.append("stopped")


def make_pool(tmp_path: Path, slugs, lifecycle=None, **kwargs) -> ProviderPool:
    lifecycle = lifecycle or Lifecycle()
    # Whether a worker is up is read from the process table, and free memory from the
    # driver or from /proc: both are readings of this machine, and a test about routing
    # or eviction must not depend on what else is running on it -- nor pay for an
    # `nvidia-smi` subprocess per start. The tests that are about memory build their
    # pools with `vram_pool`, which injects a machine they control.
    kwargs.setdefault("read_holdings", lambda: {})
    kwargs.setdefault("read_free_vram", lambda: None)
    # Capacity is a reading of this machine as much as the two above, and `--max-active
    # 0` is refused when it cannot be read, so a test that says nothing about memory
    # gets a machine large enough to hold anything in the catalog rather than this host.
    kwargs.setdefault("read_capacity", lambda: 1 << 20)
    # And so is which kind of machine this is: on unified memory a declared 0 stops
    # meaning "free", so a test that says nothing about that gets a discrete device,
    # where a manifest's 0 is the whole answer.
    kwargs.setdefault("pool_shares_host_memory", lambda: False)
    pool = ProviderPool(
        allow=tuple(slugs),
        python="/nonexistent/python",
        log_dir=tmp_path / "logs",
        schemas=SchemaStore(tmp_path / "schemas"),
        ensure=lifecycle.ensure,
        stop=lifecycle.stop,
        **kwargs,
    )
    pool.lifecycle = lifecycle  # type: ignore[attr-defined]
    return pool


# ── routing ─────────────────────────────────────────────────────────────────────


def test_every_reviewed_tool_name_resolves_to_exactly_one_provider():
    """Name-based routing is only safe while tool names stay globally unique.

    The pool has no other way to decide which provider should serve a tools/call. If a
    new provider ever reuses an operation name, this fails here rather than silently
    sending calls to whichever provider was registered last.
    """
    index = build_tool_index(REMOTE_BY_SLUG)

    total_operations = sum(len(d.operations) for d in REMOTE_BY_SLUG.values())
    assert len(index) == total_operations
    assert index["boltz2_docking"].slug == "boltz"


def test_a_tool_name_claimed_by_two_providers_is_refused():
    first, second = REMOTE_BY_SLUG["boltz"], REMOTE_BY_SLUG["esm"]
    collided = second.__class__(
        slug="esm-clone",
        module=second.module,
        port=second.port + 1,
        operations=first.operations,
    )
    registry = {"boltz": first, "esm-clone": collided}

    import tooluniverse.remote_pool as module

    original = module.REMOTE_BY_SLUG
    module.REMOTE_BY_SLUG = registry
    try:
        with pytest.raises(PoolError, match="claimed by both"):
            build_tool_index(["boltz", "esm-clone"])
    finally:
        module.REMOTE_BY_SLUG = original


def test_unknown_slug_names_the_reviewed_alternatives():
    with pytest.raises(PoolError, match="unknown provider 'not-a-model'"):
        build_tool_index(["not-a-model"])


def test_unrouted_tool_name_is_reported_rather_than_guessed(tmp_path):
    pool = make_pool(tmp_path, ["boltz"])
    with pytest.raises(PoolError, match="no shared provider serves tool"):
        pool.provider_for_tool("run_borzoi_predict")


# ── lazy start and reuse ────────────────────────────────────────────────────────


def test_nothing_starts_until_a_call_arrives(tmp_path):
    pool = make_pool(tmp_path, ["boltz", "esm", "enformer"])

    assert pool.lifecycle.started == []
    assert pool.status() == []


def test_first_call_starts_the_owning_provider_and_second_reuses_it(tmp_path):
    pool = make_pool(tmp_path, ["boltz", "esm"], max_active=2)

    endpoint = pool.acquire(pool.provider_for_tool("boltz2_docking"))
    pool.release(pool.provider_for_tool("boltz2_docking"))
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert endpoint == REMOTE_BY_SLUG["boltz"].endpoint
    assert pool.lifecycle.started == ["boltz"], "second call must reuse, not restart"


def test_a_call_for_another_model_starts_only_that_model(tmp_path):
    pool = make_pool(tmp_path, ["boltz", "esm"], max_active=2)

    pool.acquire(pool.provider_for_tool("boltz2_docking"))
    pool.acquire(pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0]))

    assert sorted(pool.lifecycle.started) == ["boltz", "esm"]


def test_a_failed_start_does_not_leave_the_provider_marked_starting(tmp_path):
    """A transient start failure must not wedge the slug behind ProviderStarting."""
    lifecycle = Lifecycle()
    lifecycle.fail.add("boltz")
    pool = make_pool(tmp_path, ["boltz"], lifecycle=lifecycle)
    deployment = pool.provider_for_tool("boltz2_docking")

    with pytest.raises(RuntimeError, match="boom"):
        pool.acquire(deployment)

    lifecycle.fail.clear()
    assert pool.acquire(deployment) == deployment.endpoint


# ── admission and eviction ──────────────────────────────────────────────────────


def test_default_admission_keeps_one_model_resident(tmp_path):
    """The default exists because GPUs hold one large model, not because one is shared."""
    assert DEFAULT_MAX_ACTIVE == 1
    pool = make_pool(tmp_path, ["boltz", "esm"])

    boltz = pool.provider_for_tool("boltz2_docking")
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])
    pool.acquire(boltz)
    pool.release(boltz)
    pool.acquire(esm)

    resident = [row["provider"] for row in pool.status()]
    assert resident == ["esm"], "boltz must be evicted to make room"
    assert pool.lifecycle.stopped, "the evicted provider must actually be stopped"


def test_eviction_takes_the_least_recently_used_idle_provider(tmp_path):
    clock = FakeClock()
    pool = make_pool(tmp_path, ["boltz", "esm", "enformer"], max_active=2, clock=clock)
    boltz = pool.provider_for_tool("boltz2_docking")
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])
    enformer = pool.provider_for_tool(REMOTE_BY_SLUG["enformer"].operations[0])

    pool.acquire(boltz)
    pool.release(boltz)
    clock.advance(60)
    pool.acquire(esm)
    pool.release(esm)
    clock.advance(60)
    pool.acquire(enformer)

    resident = sorted(row["provider"] for row in pool.status())
    assert resident == ["enformer", "esm"], "the oldest idle provider goes first"


def test_a_provider_with_a_call_in_flight_is_never_evicted(tmp_path):
    """Eviction must not kill a running GPU job to admit a new one."""
    pool = make_pool(tmp_path, ["boltz", "esm"], max_active=1)
    boltz = pool.provider_for_tool("boltz2_docking")
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])

    pool.acquire(boltz)  # held, never released

    with pytest.raises(PoolError, match="busy"):
        pool.acquire(esm)
    assert [row["provider"] for row in pool.status()] == ["boltz"]


def blocking_lifecycle():
    """A lifecycle whose start blocks until the test lets it finish."""
    release = threading.Event()
    entered = threading.Event()
    lifecycle = Lifecycle()
    real_ensure = lifecycle.ensure

    def blocking_ensure(deployment, **kwargs):
        entered.set()
        release.wait(10)
        return real_ensure(deployment, **kwargs)

    lifecycle.ensure = blocking_ensure  # type: ignore[assignment]
    return lifecycle, entered, release


def test_by_default_a_start_in_progress_is_refused_at_once(tmp_path):
    """Behind a relay, waiting is worse than a 503, and that is measured.

    boltz's MCP server takes 12.5 s on this project's GB10 to bind its port, and a relay
    agent abandons a local request after 25 s -- a timeout that takes the tunnel down for
    every caller on the host, not just this one. So a wait long enough to cover a real
    start is most of the way to an outage, while the platform re-dispatches a 503 after
    2 s, 4 s and 8 s and costs one round trip.
    """
    from tooluniverse.remote_pool import DEFAULT_START_WAIT_S

    assert DEFAULT_START_WAIT_S == 0.0
    lifecycle, entered, release = blocking_lifecycle()
    pool = make_pool(tmp_path, ["boltz"], lifecycle=lifecycle)
    deployment = pool.provider_for_tool("boltz2_docking")

    thread = threading.Thread(target=lambda: pool.acquire(deployment))
    thread.start()
    assert entered.wait(5)
    try:
        with pytest.raises(ProviderStarting):
            pool.acquire(deployment)
    finally:
        release.set()
        thread.join(10)


def test_a_host_that_asks_to_wait_has_its_second_request_served(tmp_path):
    """Opt-in, for a pool serving its own endpoint rather than a shared tunnel.

    The second of two near-simultaneous first-calls is waiting for a CPU-only process to
    bind a port, and a client whose timeout is its operator's own business can afford to
    wait for it instead of being handed a 503 to retry.
    """
    lifecycle, entered, release = blocking_lifecycle()
    pool = make_pool(tmp_path, ["boltz"], lifecycle=lifecycle, start_wait_s=30)
    deployment = pool.provider_for_tool("boltz2_docking")

    first = threading.Thread(target=lambda: pool.acquire(deployment))
    first.start()
    assert entered.wait(5)
    answers: list[object] = []
    second = threading.Thread(target=lambda: answers.append(pool.acquire(deployment)))
    second.start()
    release.set()
    first.join(10)
    second.join(10)

    assert answers == [deployment.endpoint], "the waiting call must be served"
    assert lifecycle.started == ["boltz"], "only one start may happen"
    assert pool.status()[0]["in_flight"] == 2, "both callers hold a slot"


def test_a_start_that_outlasts_the_wait_is_told_to_retry(tmp_path):
    """The case waiting cannot absorb: a model loading, which is minutes."""
    lifecycle, entered, release = blocking_lifecycle()
    pool = make_pool(tmp_path, ["boltz"], lifecycle=lifecycle, start_wait_s=0.2)
    deployment = pool.provider_for_tool("boltz2_docking")

    thread = threading.Thread(target=lambda: pool.acquire(deployment))
    thread.start()
    assert entered.wait(5)
    try:
        with pytest.raises(ProviderStarting):
            pool.acquire(deployment)
    finally:
        release.set()
        thread.join(10)

    assert lifecycle.started == ["boltz"], "only one start may happen"


def test_a_waiting_call_is_released_by_a_start_that_fails(tmp_path):
    """A failed start must wake its waiters rather than hold them for the whole wait.

    The waiter then starts the provider itself and gets the real failure, which is a
    better answer than a 503 about a start that is already over.
    """
    lifecycle, entered, release = blocking_lifecycle()
    lifecycle.fail.add("boltz")
    pool = make_pool(tmp_path, ["boltz"], lifecycle=lifecycle, start_wait_s=30)
    deployment = pool.provider_for_tool("boltz2_docking")

    def start_and_swallow() -> None:
        try:
            pool.acquire(deployment)
        except RuntimeError:
            pass  # the start this test arranged to fail; the assertion is below

    thread = threading.Thread(target=start_and_swallow)
    thread.start()
    assert entered.wait(5)
    release.set()
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="boom"):
        pool.acquire(deployment)
    thread.join(10)

    assert time.monotonic() - started < 10, "it waited out the whole start window"


# ── idle reaping ────────────────────────────────────────────────────────────────


def test_idle_providers_are_stopped_so_the_gpu_comes_back(tmp_path):
    clock = FakeClock()
    pool = make_pool(tmp_path, ["boltz"], idle_ttl=300, clock=clock)
    deployment = pool.provider_for_tool("boltz2_docking")
    pool.acquire(deployment)
    pool.release(deployment)

    assert pool.reap_idle() == ()
    clock.advance(300)
    assert pool.reap_idle() == ("boltz",)
    assert pool.status() == []


def test_reaping_skips_a_provider_still_serving_a_call(tmp_path):
    clock = FakeClock()
    pool = make_pool(tmp_path, ["boltz"], idle_ttl=300, clock=clock)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))  # held
    clock.advance(10_000)

    assert pool.reap_idle() == ()


def test_shutdown_stops_everything_it_started(tmp_path):
    pool = make_pool(tmp_path, ["boltz", "esm"], max_active=2)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))
    pool.acquire(pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0]))

    pool.shutdown()

    assert pool.status() == []
    assert len(pool.lifecycle.stopped) == 2


def test_an_adopted_provider_is_not_stopped_by_the_pool(tmp_path):
    """ensure_provider returns None when it reused an already-running provider.

    That provider belongs to whoever started it -- another terminal, or systemd -- so
    shutdown must leave it alone.
    """
    lifecycle = Lifecycle()
    lifecycle.ensure = lambda deployment, **kwargs: (None, {"ok": True})  # type: ignore
    pool = make_pool(tmp_path, ["boltz"], lifecycle=lifecycle)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert pool.status()[0]["adopted"] is True
    pool.shutdown()
    assert lifecycle.stopped == []


# ── schema snapshots ────────────────────────────────────────────────────────────


def test_snapshot_roundtrips_and_survives_a_restart(tmp_path):
    store = SchemaStore(tmp_path / "schemas")
    deployment = REMOTE_BY_SLUG["boltz"]
    tools = [{"name": "boltz2_docking", "inputSchema": {"type": "object"}}]

    store.save(deployment, tools)

    assert SchemaStore(tmp_path / "schemas").load(deployment) == tools


def test_a_snapshot_from_a_different_provider_build_is_discarded(tmp_path):
    """Upgrading a provider must not keep publishing its old schema."""
    store = SchemaStore(tmp_path / "schemas")
    deployment = REMOTE_BY_SLUG["boltz"]
    store.save(deployment, [{"name": "boltz2_docking"}])
    path = tmp_path / "schemas" / "boltz.json"

    payload = json.loads(path.read_text())
    payload["fingerprint"] = "0:0"
    path.write_text(json.dumps(payload))

    assert store.load(deployment) is None


def test_a_corrupt_snapshot_is_ignored_rather_than_crashing_discovery(tmp_path):
    store = SchemaStore(tmp_path / "schemas")
    (tmp_path / "schemas").mkdir(parents=True)
    (tmp_path / "schemas" / "boltz.json").write_text("{not json")

    assert store.load(REMOTE_BY_SLUG["boltz"]) is None


def test_discovery_lists_cached_tools_across_providers_without_starting_any(tmp_path):
    pool = make_pool(tmp_path, ["boltz", "esm"], max_active=2)
    pool.schemas.save(REMOTE_BY_SLUG["boltz"], [{"name": "boltz2_docking"}])
    pool.schemas.save(
        REMOTE_BY_SLUG["esm"], [{"name": REMOTE_BY_SLUG["esm"].operations[0]}]
    )

    names = sorted(tool["name"] for tool in pool.known_tools())

    assert names == sorted(["boltz2_docking", REMOTE_BY_SLUG["esm"].operations[0]])
    assert pool.lifecycle.started == [], "listing must not load a model"


def test_warm_snapshots_each_provider_once_and_stops_it_again(tmp_path):
    pool = make_pool(
        tmp_path,
        ["boltz", "esm"],
        max_active=1,
        discover=lambda deployment: [{"name": deployment.operations[0]}],
    )

    results = pool.warm()

    assert results == {"boltz": "cached 1 tools", "esm": "cached 1 tools"}
    assert sorted(pool.lifecycle.started) == ["boltz", "esm"]
    assert len(pool.lifecycle.stopped) == 2, "warming must not leave models resident"
    assert pool.missing_snapshots() == ()
    assert pool.status() == [], "max_active=1 must not block warming two providers"


def test_a_provider_with_no_snapshot_still_routes_its_calls(tmp_path):
    """Routing uses the static operation table, so an uncached provider is callable."""
    pool = make_pool(tmp_path, ["boltz"])

    assert pool.known_tools() == []
    assert pool.provider_for_tool("boltz2_docking").slug == "boltz"


# ── configuration guards ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"max_active": -1}, "--max-active"),
        ({"idle_ttl": 0}, "--idle-ttl"),
        ({"startup_timeout": 1}, "--startup-timeout"),
        ({"startup_timeout": 10_000}, "--startup-timeout"),
    ],
)
def test_invalid_configuration_is_refused_at_construction(tmp_path, kwargs, message):
    with pytest.raises(PoolError, match=message):
        make_pool(tmp_path, ["boltz"], **kwargs)


def test_an_empty_allowlist_is_refused(tmp_path):
    with pytest.raises(PoolError, match="at least one"):
        make_pool(tmp_path, [])


# ── the multiplexed MCP endpoint ────────────────────────────────────────────────


def _rpc(port: int, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return int(response.status), json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        with exc:
            return int(exc.status), json.loads(exc.read() or b"{}")


@pytest.fixture
def served(tmp_path):
    pool = make_pool(tmp_path, ["boltz", "esm"], max_active=2)
    pool.schemas.save(REMOTE_BY_SLUG["boltz"], [{"name": "boltz2_docking"}])
    server = serve_pool(pool, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield pool, server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def test_initialize_answers_without_starting_a_provider(served):
    pool, port = served

    status, body = _rpc(port, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert status == 200
    assert body["result"]["serverInfo"]["name"] == "tooluniverse-remote-pool"
    assert pool.lifecycle.started == []


def test_tools_list_serves_the_cache_and_starts_nothing(served):
    pool, port = served

    status, body = _rpc(port, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert status == 200
    assert [tool["name"] for tool in body["result"]["tools"]] == ["boltz2_docking"]
    assert pool.lifecycle.started == []


def test_a_tools_call_starts_the_owning_provider(served, monkeypatch):
    pool, port = served
    seen: dict = {}

    def fake_proxy(endpoint, payload, timeout=0):
        seen["endpoint"] = endpoint
        return 200, json.dumps(
            {"jsonrpc": "2.0", "id": 3, "result": {"ok": True}}
        ).encode()

    monkeypatch.setattr("tooluniverse.remote_pool.proxy_call", fake_proxy)

    status, body = _rpc(
        port,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "boltz2_docking", "arguments": {}},
        },
    )

    assert status == 200
    assert body["result"] == {"ok": True}
    assert pool.lifecycle.started == ["boltz"]
    assert seen["endpoint"] == REMOTE_BY_SLUG["boltz"].endpoint


def measuring_pool(tmp_path, holdings):
    """A pool over a machine whose free memory and worker list the test decides."""
    from tooluniverse.remote_pool import FootprintStore

    return make_pool(
        tmp_path,
        ["boltz"],
        footprints=FootprintStore(tmp_path / "fp"),
        read_free_vram=falling_gpu(40_000, 24_000),
        read_holdings=lambda: holdings,
    )


def rpc_through(pool, payload):
    server = serve_pool(pool, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        return _rpc(server.server_address[1], payload)
    finally:
        server.shutdown()
        server.server_close()


CALL = {
    "jsonrpc": "2.0",
    "id": 9,
    "method": "tools/call",
    "params": {"name": "boltz2_docking", "arguments": {}},
}


def test_an_answered_call_is_where_the_model_gets_measured(tmp_path, monkeypatch):
    """The wiring an injected lifecycle cannot show: nothing else in the request path
    takes the reading, so if the handler does not, a resident provider is never measured
    on this host at all."""
    monkeypatch.setattr(
        "tooluniverse.remote_pool.proxy_call",
        lambda endpoint, payload, timeout=0: (
            200,
            json.dumps({"jsonrpc": "2.0", "id": 9, "result": {"ok": True}}).encode(),
        ),
    )
    pool = measuring_pool(tmp_path, {"boltz": 5.54})

    status, body = rpc_through(pool, CALL)

    assert (status, body["result"]) == (200, {"ok": True})
    assert pool.footprints.get("boltz") == 16_000


def test_a_call_the_provider_never_answered_measures_nothing(tmp_path, monkeypatch):
    """A provider that did not answer may be holding anything or nothing."""

    def dead(endpoint, payload, timeout=0):
        raise OSError("connection reset")

    monkeypatch.setattr("tooluniverse.remote_pool.proxy_call", dead)
    pool = measuring_pool(tmp_path, {"boltz": 5.54})

    status, body = rpc_through(pool, CALL)

    assert status == 200 and body["error"]["code"] == -32603
    assert pool.footprints.get("boltz") is None


def test_an_unknown_tool_is_a_method_error_not_a_dead_tunnel(served):
    """A 404/405/410 on POST makes the relay agent tear the tunnel down for everyone."""
    _, port = served

    status, body = _rpc(
        port,
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "no_such_tool"},
        },
    )

    assert status == 200
    assert body["error"]["code"] == -32601


def test_a_busy_pool_answers_503_with_retry_after(tmp_path):
    pool = make_pool(tmp_path, ["boltz", "esm"], max_active=1)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))  # held
    server = serve_pool(pool, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/mcp",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": REMOTE_BY_SLUG["esm"].operations[0]},
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=10)
        assert caught.value.status == 503
        assert caught.value.headers["Retry-After"] == "10"
    finally:
        server.shutdown()
        server.server_close()


def test_a_notification_is_accepted_with_no_body(served):
    _, port = served
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp",
        data=json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 202
        assert response.read() == b""


def test_session_delete_is_acknowledged(served):
    _, port = served
    request = urllib.request.Request(f"http://127.0.0.1:{port}/mcp", method="DELETE")
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 204


def test_malformed_json_is_a_parse_error(served):
    _, port = served
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp",
        data=b"{not json",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request, timeout=10)
    assert caught.value.status == 400
    assert json.loads(caught.value.read())["error"]["code"] == -32700


# ── control plane ───────────────────────────────────────────────────────────────


def wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_status_reports_what_the_host_shares_and_what_is_loaded(tmp_path):
    pool = make_pool(tmp_path, ["boltz", "esm"], max_active=2, idle_ttl=600)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    result = pool.control("status", {})

    assert result["allowed"] == ["boltz", "esm"]
    assert result["max_active"] == 2
    assert result["idle_ttl"] == 600
    assert [row["provider"] for row in result["providers"]] == ["boltz"]


def test_prewarm_is_refused_for_a_provider_this_host_does_not_share(tmp_path):
    """The allowlist is the control plane's security boundary.

    The platform relays a provider name a caller chose. Without this check, a member of a
    shared host could start any reviewed provider on someone else's machine.
    """
    pool = make_pool(tmp_path, ["boltz"])

    result = pool.control("prewarm", {"provider": "esm"})

    assert "not shared by this host" in result["error"]
    assert pool.lifecycle.started == []


def test_prewarm_loads_the_model_before_any_call_arrives(tmp_path):
    """Loads the MODEL. Starting the server is seconds and hides nothing: the weights
    load in a worker on the first request unless the start asks for them."""
    pool = make_pool(tmp_path, ["boltz"])

    acknowledged = pool.control("prewarm", {"provider": "boltz"})

    assert acknowledged == {"provider": "boltz", "state": "starting"}
    assert wait_until(lambda: pool.lifecycle.started == ["boltz"])
    assert wait_until(lambda: [r["provider"] for r in pool.status()] == ["boltz"])
    assert pool.lifecycle.warmed == ["boltz"], "the start did not ask for the model"


def test_a_call_does_not_ask_for_a_warm_start(tmp_path):
    """It is the request that loads the model, so asking would mean loading it twice."""
    pool = make_pool(tmp_path, ["boltz"])

    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert pool.lifecycle.started == ["boltz"]
    assert pool.lifecycle.warmed == []


def test_a_prewarmed_provider_holds_no_slot_so_it_can_still_be_reaped(tmp_path):
    """A prewarm that looked like an in-flight call would pin the GPU forever."""
    clock = FakeClock()
    pool = make_pool(tmp_path, ["boltz"], idle_ttl=100, clock=clock)
    pool.control("prewarm", {"provider": "boltz"})
    # Resident, not merely claimed: `status` lists a provider that is still starting too,
    # and waiting only for a row let this read the starting one and find no `in_flight`.
    assert wait_until(lambda: any(not r.get("starting") for r in pool.status()))

    assert pool.status()[0]["in_flight"] == 0
    clock.advance(100)
    assert pool.reap_idle() == ("boltz",)


def test_prewarming_something_already_loaded_does_not_restart_it(tmp_path):
    pool = make_pool(tmp_path, ["boltz"])
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    result = pool.control("prewarm", {"provider": "boltz"})

    assert result == {"provider": "boltz", "state": "ready"}
    assert pool.lifecycle.started == ["boltz"]


def test_stop_unloads_an_idle_provider(tmp_path):
    pool = make_pool(tmp_path, ["boltz"])
    deployment = pool.provider_for_tool("boltz2_docking")
    pool.acquire(deployment)
    pool.release(deployment)

    result = pool.control("stop", {"provider": "boltz"})

    assert result == {"provider": "boltz", "state": "stopped"}
    assert pool.status() == []


def test_stop_refuses_to_interrupt_a_running_call(tmp_path):
    pool = make_pool(tmp_path, ["boltz"])
    pool.acquire(pool.provider_for_tool("boltz2_docking"))  # held

    result = pool.control("stop", {"provider": "boltz"})

    assert result["state"] == "busy"
    assert result["in_flight"] == 1
    assert [row["provider"] for row in pool.status()] == ["boltz"]


def test_stopping_something_not_loaded_is_reported_not_an_error(tmp_path):
    pool = make_pool(tmp_path, ["boltz"])

    assert pool.control("stop", {"provider": "boltz"}) == {
        "provider": "boltz",
        "state": "absent",
    }


@pytest.mark.parametrize(
    "op, args",
    [
        ("prewarm", {}),
        ("stop", {"provider": ""}),
        ("prewarm", {"provider": 7}),
        ("exec", {"provider": "boltz"}),
        ("status/../etc", {}),
    ],
)
def test_a_malformed_control_operation_is_answered_not_raised(tmp_path, op, args):
    """Raising would propagate out of the agent and close the tunnel.

    Every in-flight tool call for this host would die because one control message was
    malformed, so the pool reports the problem in its result instead.
    """
    pool = make_pool(tmp_path, ["boltz"])

    result = pool.control(op, args)

    assert "error" in result
    assert pool.lifecycle.started == []


# ── VRAM-aware admission ────────────────────────────────────────────────────────


class FakeGPU:
    """A GPU whose free memory the test controls."""

    def __init__(self, free: int | None) -> None:
        self.free = free
        self.reads = 0

    def __call__(self) -> int | None:
        self.reads += 1
        return self.free


def vram_pool(tmp_path, slugs, gpu, lifecycle=None, **kwargs):
    from tooluniverse.remote_pool import FootprintStore

    # Nothing declared and no capacity unless the test is about one of those: these
    # cases are about what the pool measures here, and reading the real manifests
    # would quietly change what each one is asserting.
    kwargs.setdefault("declared_footprint", lambda slug: None)
    kwargs.setdefault("read_capacity", lambda: None)
    pool = make_pool(
        tmp_path,
        slugs,
        lifecycle=lifecycle,
        footprints=FootprintStore(tmp_path / "fp"),
        read_free_vram=gpu,
        **kwargs,
    )
    return pool


def test_a_provider_nothing_declares_has_its_first_load_admitted_on_count(
    tmp_path,
):
    """28 of the 60 reviewed slugs declare no budget, and nothing changes for them.

    The pool admits that first load on count and learns the cost from it, which is
    what every provider got before the resident manifests carried a measured figure.
    """
    gpu = FakeGPU(free=100)  # Far too little for anything, yet the load must proceed.
    pool = vram_pool(tmp_path, ["boltz"], gpu)

    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert pool.lifecycle.started == ["boltz"]
    assert pool.footprints.get("boltz") is None, "nothing was measurable yet"


def falling_gpu(*readings):
    """A machine whose free memory takes these values in turn, then stays at the last."""
    remaining = list(readings)
    last = [readings[-1]]

    def read() -> int | None:
        if remaining:
            last[0] = remaining.pop(0)
        return last[0]

    return read


@pytest.mark.parametrize("slug, tool", [("boltz", "boltz2_docking"), ("esm", None)])
def test_no_providers_start_is_measured_as_its_model(tmp_path, slug, tool):
    """The bug, and it was not only the resident providers.

    boltz keeps its model in a worker that its start does not touch. esm keeps its
    model in the server process -- and loads it on the first request too, lazily, as
    its own source says ("lazy load on first use"), which is how anything answers
    `tools/list` before its weights exist. So the 16 GiB difference below is not either
    provider's model, and recording it would hand admission a figure that is either far
    too small for a model or, as here, somebody else's allocation entirely --
    `FootprintStore` then keeps whichever figure was largest for the life of the host.
    """
    tool = tool or REMOTE_BY_SLUG[slug].operations[0]
    pool = vram_pool(tmp_path, [slug], falling_gpu(40_000, 24_000))

    pool.acquire(pool.provider_for_tool(tool))

    assert pool.footprints.get(slug) is None, "nothing had loaded to measure"


def test_a_provider_holding_its_model_in_its_server_is_measured_after_a_call(tmp_path):
    """esm has no worker to look for, so an answered call is all the evidence there is.

    A call that answered without loading anything therefore records something small,
    and the first call that does load corrects it, because the store keeps the largest
    figure it has seen.
    """
    pool = vram_pool(tmp_path, ["esm"], falling_gpu(40_000, 24_000))
    deployment = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])

    pool.acquire(deployment)
    pool.learn_footprint(deployment)

    assert pool.footprints.get("esm") == 16_000


def test_a_resident_provider_is_measured_after_the_call_that_loaded_it(tmp_path):
    """The same two readings, taken where the model is actually in memory."""
    pool = vram_pool(
        tmp_path,
        ["boltz"],
        falling_gpu(40_000, 24_000),
        read_holdings=lambda: {"boltz": 5.54},
    )
    deployment = pool.provider_for_tool("boltz2_docking")

    pool.acquire(deployment)
    assert pool.footprints.get("boltz") is None, "the start on its own measures nothing"
    pool.learn_footprint(deployment)

    assert pool.footprints.get("boltz") == 16_000


def test_a_call_answered_without_the_worker_loading_records_nothing(tmp_path):
    """A rejected argument is answered by the server and never reaches the worker.

    For a provider that keeps one, the process table says which happened, so an answer
    alone is not taken as evidence that a model loaded.
    """
    pool = vram_pool(
        tmp_path, ["boltz"], falling_gpu(40_000, 24_000), read_holdings=lambda: {}
    )
    deployment = pool.provider_for_tool("boltz2_docking")

    pool.acquire(deployment)
    pool.learn_footprint(deployment)

    assert pool.footprints.get("boltz") is None


def test_another_checkouts_worker_is_not_this_pools_measurement(tmp_path):
    """`machine_holdings` keys a worker from another checkout as `slug@tree`.

    Charging their load to this pool's model is how a figure measured on someone else's
    minutes becomes this host's permanent ceiling.
    """
    pool = vram_pool(
        tmp_path,
        ["boltz"],
        falling_gpu(40_000, 24_000),
        read_holdings=lambda: {"boltz@tu-other": 5.54},
    )
    deployment = pool.provider_for_tool("boltz2_docking")

    pool.acquire(deployment)
    pool.learn_footprint(deployment)

    assert pool.footprints.get("boltz") is None


def test_a_residency_is_measured_once_and_not_once_per_call(tmp_path):
    """Every later call would be measured against a baseline from before the load."""
    pool = vram_pool(
        tmp_path,
        ["boltz"],
        falling_gpu(40_000, 24_000, 8_000),
        read_holdings=lambda: {"boltz": 5.54},
    )
    deployment = pool.provider_for_tool("boltz2_docking")

    pool.acquire(deployment)
    pool.learn_footprint(deployment)
    pool.learn_footprint(deployment)

    assert pool.footprints.get("boltz") == 16_000, "the second call re-measured"


def test_a_measured_provider_is_refused_when_the_gpu_cannot_hold_it(tmp_path):
    gpu = FakeGPU(free=8_000)
    pool = vram_pool(tmp_path, ["boltz"], gpu, max_active=2)
    pool.footprints.record("boltz", 20_000)

    with pytest.raises(PoolError, match="needs 20000 MiB"):
        pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert pool.lifecycle.started == [], "a model that cannot fit must not be launched"


def test_headroom_is_required_on_top_of_the_measurement(tmp_path):
    """Admitting a model into exactly its measured size fails on the real allocation."""
    pool = vram_pool(tmp_path, ["boltz"], FakeGPU(free=20_000), vram_headroom_mib=1024)
    pool.footprints.record("boltz", 20_000)

    with pytest.raises(PoolError, match="headroom"):
        pool.acquire(pool.provider_for_tool("boltz2_docking"))


def test_two_small_models_coexist_where_a_count_of_one_would_not(tmp_path):
    """The whole point of measuring: a count cannot express that these both fit."""
    pool = vram_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=40_000), max_active=4)
    esm_tool = REMOTE_BY_SLUG["esm"].operations[0]
    pool.footprints.record("boltz", 4_000)
    pool.footprints.record("esm", 4_000)

    pool.acquire(pool.provider_for_tool("boltz2_docking"))
    pool.acquire(pool.provider_for_tool(esm_tool))

    assert sorted(row["provider"] for row in pool.status()) == ["boltz", "esm"]


# ── what a declared zero is worth on unified memory ─────────────────────────────


def unified_pool(tmp_path, slugs, gpu, **kwargs):
    """A pool of CPU-only providers on a machine with one pool for host and device."""
    kwargs.setdefault("read_capacity", lambda: 1 << 20)
    kwargs.setdefault("pool_shares_host_memory", lambda: True)
    kwargs.setdefault("declared_footprint", lambda slug: 0)
    return vram_pool(tmp_path, slugs, gpu, **kwargs)


def esm_of(pool):
    return pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])


def test_a_cpu_only_provider_on_unified_memory_is_measured_and_not_assumed_free(
    tmp_path,
):
    """`policy = "none"` says "no device memory", which here is not "no memory".

    Three manifests declare it, each off a measurement -- their kit has no GPU-capable
    wheel for this architecture -- and one of them draws the conclusion that it can
    therefore be "admitted while the card is full". On a discrete-GPU host that is right
    and worth having. On unified memory its ~10 GiB of host RSS comes out of the pool
    admission reads, and the old answer skipped the measurement as well as the ceiling,
    so the figure stayed unlearnable rather than merely unknown.
    """
    pool = unified_pool(tmp_path, ["esm"], falling_gpu(40_000, 30_000))
    deployment = esm_of(pool)

    pool.acquire(deployment)
    pool.learn_footprint(deployment)

    assert pool.footprints.get("esm") == 10_000


def test_on_a_discrete_device_a_declared_zero_costs_nothing_and_is_read_for_nothing(
    tmp_path,
):
    """The same manifest on the machine its claim is about: no ceiling, no reading."""
    gpu = FakeGPU(free=40_000)
    pool = unified_pool(tmp_path, ["esm"], gpu, pool_shares_host_memory=lambda: False)
    deployment = esm_of(pool)

    pool.acquire(deployment)
    pool.learn_footprint(deployment)

    assert pool.footprints.get("esm") is None
    assert gpu.reads == 0, "a provider known to hold nothing is measured for nothing"


def test_a_machine_that_cannot_say_which_kind_it_is_keeps_the_manifests_answer(
    tmp_path,
):
    """None is "cannot tell", and such a machine cannot read its free memory either.

    There is no memory ceiling to protect on a host that answers nothing, so the
    manifest's 0 is left as the answer rather than turned into a provider this pool
    would then bound one at a time for no gain.
    """
    gpu = FakeGPU(free=40_000)
    pool = unified_pool(tmp_path, ["esm"], gpu, pool_shares_host_memory=lambda: None)
    deployment = esm_of(pool)

    pool.acquire(deployment)
    pool.learn_footprint(deployment)

    assert pool.footprints.get("esm") is None
    assert gpu.reads == 0


def test_which_kind_of_machine_this_is_is_read_once_and_not_once_per_decision(tmp_path):
    """It cannot change while a pool runs, and asking costs an `nvidia-smi`."""
    asked = []
    pool = unified_pool(
        tmp_path,
        ["boltz", "esm"],
        FakeGPU(free=40_000),
        pool_shares_host_memory=lambda: asked.append(1) or True,
    )

    pool.acquire(esm_of(pool))
    pool.release(esm_of(pool))
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert len(asked) == 1


def test_a_machine_kind_that_could_not_be_read_is_asked_again(tmp_path):
    """A driver busy for a second must not decide this for the rest of a pool's life."""
    machine = {"shared": None}
    gpu = FakeGPU(free=40_000)
    pool = unified_pool(
        tmp_path, ["esm"], gpu, pool_shares_host_memory=lambda: machine["shared"]
    )
    deployment = esm_of(pool)

    pool.acquire(deployment)
    assert gpu.reads == 0, "unreadable: the manifest's 0 stands"

    machine["shared"] = True
    pool.release(deployment)
    pool.control("stop", {"provider": "esm"})
    pool.acquire(deployment)

    assert gpu.reads == 1, "asked again, and this time the cost is unknown here"


# ── no count ceiling: --max-active 0 ────────────────────────────────────────────


def countless_pool(tmp_path, slugs, gpu, **kwargs):
    """A pool with no count ceiling, on a machine whose memory it can read."""
    kwargs.setdefault("read_capacity", lambda: 1 << 20)
    return vram_pool(tmp_path, slugs, gpu, max_active=0, **kwargs)


def test_no_count_ceiling_is_refused_where_memory_cannot_be_read(tmp_path):
    """Dropping the count where there is no second ceiling leaves no ceiling at all.

    A capacity reading of None is `pool_capacity_mib`'s "do not reason about memory" --
    a host with no NVIDIA driver and no unified memory to fall back on. Admitting on
    nothing is worse than admitting on a count, so the operator is told at startup,
    while they can still pass one, rather than by an out-of-memory later.
    """
    with pytest.raises(PoolError, match="--max-active 0"):
        vram_pool(tmp_path, ["boltz"], FakeGPU(free=40_000), max_active=0)


def test_without_a_count_ceiling_memory_still_evicts(tmp_path):
    """0 does not mean "admit everything": the ceiling it drops is the count."""
    pool = countless_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=10_000))
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])
    boltz = pool.provider_for_tool("boltz2_docking")
    pool.footprints.record("esm", 6_000)
    pool.footprints.record("boltz", 14_000)

    pool.acquire(esm)
    pool.release(esm)
    pool.acquire(boltz)  # 10000 free + 6000 reclaimed = 16000 >= 14000 + 1024

    assert [row["provider"] for row in pool.status()] == ["boltz"]


def test_a_provider_nobody_has_costed_is_still_admitted_one_at_a_time(tmp_path):
    """The 28 undeclared slugs are what the count ceiling was really covering.

    Memory cannot judge a provider whose cost nobody has said -- `footprint_mib` is
    None and the memory ceiling returns early on it -- so with the count gone its load
    would be admitted on no evidence, and so would the next one, and the machine would
    find out how many fit by running out.
    """
    pool = countless_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=40_000))
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])

    pool.acquire(esm)
    pool.release(esm)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert [row["provider"] for row in pool.status()] == ["boltz"], (
        "two providers of unknown cost must not be resident together"
    )


def test_an_uncosted_provider_mid_call_is_a_retry_and_not_an_eviction(tmp_path):
    """Same rule as every other ceiling: a running GPU job is not collateral."""
    pool = countless_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=40_000))
    pool.acquire(pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0]))  # held

    with pytest.raises(PoolError, match="busy"):
        pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert [row["provider"] for row in pool.status()] == ["esm"]


def test_a_second_uncosted_provider_is_refused_while_the_first_is_starting(tmp_path):
    """Nothing is resident to evict, because the other one is still coming up.

    Killing a start in progress is not eviction -- the call that asked for it is still
    waiting on it -- so the answer is the same retry a busy provider gets.
    """
    lifecycle, entered, release = blocking_lifecycle()
    pool = countless_pool(
        tmp_path, ["boltz", "esm"], FakeGPU(free=40_000), lifecycle=lifecycle
    )
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])

    thread = threading.Thread(target=lambda: pool.acquire(esm))
    thread.start()
    assert entered.wait(5)
    try:
        with pytest.raises(PoolError, match="busy"):
            pool.acquire(pool.provider_for_tool("boltz2_docking"))
    finally:
        release.set()
        thread.join(10)


def test_a_measured_provider_stops_being_bounded_one_at_a_time(tmp_path):
    """The bound is on ignorance, and one answered call is what ends it.

    The same two providers as the test above, with the one difference that this host
    has measured what they cost -- which is what `learn_footprint` records after a call
    each of them answered. Memory can speak for them now, and it says both fit.
    """
    pool = countless_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=40_000))
    pool.footprints.record("esm", 4_000)
    pool.footprints.record("boltz", 4_000)
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])

    pool.acquire(esm)
    pool.release(esm)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert sorted(row["provider"] for row in pool.status()) == ["boltz", "esm"]
    assert pool.lifecycle.stopped == [], "both fit, so nothing had to be stopped"


def test_cpu_only_providers_on_unified_memory_are_not_all_admitted_unmeasured(tmp_path):
    """Both new rules at once, which is the case this fleet's GB10 actually is.

    Nothing has costed these providers HERE -- their manifests speak about a card they
    do not touch -- so with the count ceiling gone they are admitted one at a time
    until a call each of them answered has been measured.
    """
    pool = unified_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=40_000), max_active=0)
    esm = esm_of(pool)

    pool.acquire(esm)
    pool.release(esm)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert [row["provider"] for row in pool.status()] == ["boltz"]


def test_a_provider_declaring_it_holds_no_device_memory_is_costed_and_not_unknown(
    tmp_path,
):
    """`[gpu] policy = "none"` is knowledge, not a gap, and 0 is not None.

    A provider that holds no device memory can share the machine with anything, and it
    would be the one hurt most by a bound meant for providers nobody has costed.
    """
    pool = countless_pool(
        tmp_path,
        ["boltz", "esm"],
        FakeGPU(free=40_000),
        declared_footprint=lambda slug: 0,
    )
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])

    pool.acquire(esm)
    pool.release(esm)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert sorted(row["provider"] for row in pool.status()) == ["boltz", "esm"]


def test_the_count_ceiling_a_pool_was_given_is_what_status_reports(tmp_path):
    """An operator reading `status` needs to see which ceiling is in force."""
    pool = countless_pool(tmp_path, ["boltz"], FakeGPU(free=40_000))

    assert pool.control("status", {})["max_active"] == 0


def test_a_large_model_evicts_an_idle_one_to_make_memory_room(tmp_path):
    pool = vram_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=10_000), max_active=4)
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])
    boltz = pool.provider_for_tool("boltz2_docking")
    pool.footprints.record("esm", 6_000)
    pool.footprints.record("boltz", 14_000)

    pool.acquire(esm)
    pool.release(esm)
    pool.acquire(boltz)  # 10000 free + 6000 reclaimed from esm = 16000 >= 14000 + 1024

    assert [row["provider"] for row in pool.status()] == ["boltz"]


def test_memory_pressure_never_evicts_a_provider_mid_call(tmp_path):
    """Same rule as the count ceiling: a running GPU job is not collateral."""
    pool = vram_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=2_000), max_active=4)
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])
    pool.acquire(esm)  # admitted on count, since nothing had measured it yet; held
    pool.footprints.record("esm", 4_000)
    pool.footprints.record("boltz", 20_000)

    with pytest.raises(PoolError, match="busy"):
        pool.acquire(pool.provider_for_tool("boltz2_docking"))
    assert [row["provider"] for row in pool.status()] == ["esm"]


def test_an_unmeasured_victim_is_assumed_to_free_nothing(tmp_path):
    """Conservative on purpose: guessing a victim's size could overcommit the GPU.

    The numbers matter. Free memory is short of what boltz needs, and one unmeasured
    resident is available to evict. Crediting that eviction with any plausible amount
    (8 GiB, say) would clear the requirement and admit boltz onto a GPU that cannot hold
    it; crediting it with nothing refuses. A test where both choices end in a refusal
    would prove nothing, so this one is sized so they differ.
    """
    pool = vram_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=4_000), max_active=4)
    esm = pool.provider_for_tool(REMOTE_BY_SLUG["esm"].operations[0])
    pool.acquire(esm)
    pool.release(esm)  # resident, idle, and never measured
    pool.footprints.record("boltz", 10_000)  # needs 11024 with headroom

    with pytest.raises(PoolError, match="needs 10000 MiB"):
        pool.acquire(pool.provider_for_tool("boltz2_docking"))
    assert pool.lifecycle.started == ["esm"], "boltz must not have been launched"


def test_a_machine_with_no_gpu_admits_on_count_alone(tmp_path):
    """Twenty of the thirty reviewed providers need no GPU at all."""
    pool = vram_pool(tmp_path, ["boltz"], FakeGPU(free=None))
    pool.footprints.record("boltz", 20_000)

    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert pool.lifecycle.started == ["boltz"]


def test_a_driver_error_is_treated_as_no_reading_rather_than_no_memory(tmp_path):
    def broken() -> int | None:
        raise OSError("nvidia-smi exploded")

    pool = vram_pool(tmp_path, ["boltz"], broken)
    pool.footprints.record("boltz", 20_000)

    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert pool.lifecycle.started == ["boltz"]


def test_a_first_load_takes_one_reading_and_keeps_it_as_its_baseline(tmp_path):
    """One reading per start, and nothing is decided on it.

    boltz's cost is unknown to this pool, so there is no admission decision to make
    here; the reading is taken anyway because it is the only baseline the measurement
    after the first call can be taken against, and it cannot be taken afterwards.
    """
    gpu = FakeGPU(free=50_000)
    pool = vram_pool(tmp_path, ["boltz"], gpu)

    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert gpu.reads == 1, f"expected one reading, got {gpu.reads}"
    assert pool.lifecycle.started == ["boltz"], "and nothing refused on it"


def test_status_reports_only_measurements_that_exist(tmp_path):
    pool = vram_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=31_000))
    pool.footprints.record("boltz", 12_000)

    answer = pool.control("status", {})

    assert answer["measured_vram_mib"] == {"boltz": 12_000}
    assert answer["free_vram_mib"] == 31_000
    assert answer["vram_headroom_mib"] == 1024


def test_status_says_whether_a_resident_provider_holds_its_model_yet(tmp_path):
    """Up and loaded are two different facts, and prewarm is the reason to tell them
    apart: a provider reported ready is still minutes from answering if its worker has
    not started."""
    pool = make_pool(tmp_path, ["boltz"], read_holdings=lambda: {})
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert pool.status()[0]["model_loaded"] is False

    pool.read_holdings = lambda: {"boltz": 5.54}
    assert pool.status()[0]["model_loaded"] is True


def test_status_asks_nothing_about_a_model_a_provider_does_not_hold(tmp_path):
    """esm has no worker to look for: its server being up IS its model being loaded."""
    pool = make_pool(tmp_path, ["esm"], read_holdings=lambda: {})
    pool.acquire(pool.provider_for_tool("esm_embed_sequence"))

    assert "model_loaded" not in pool.status()[0]


def test_status_leaves_the_model_out_when_the_process_table_cannot_be_read(tmp_path):
    def broken():
        raise OSError("ps is not on this machine")

    pool = make_pool(tmp_path, ["boltz"], read_holdings=broken)
    pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert "model_loaded" not in pool.status()[0], "unknown is not False"


def test_a_pool_without_a_footprint_store_reports_no_vram_fields(tmp_path):
    pool = make_pool(tmp_path, ["boltz"])

    answer = pool.control("status", {})

    assert "measured_vram_mib" not in answer
    assert "free_vram_mib" not in answer


# ── footprint store ─────────────────────────────────────────────────────────────


def test_a_footprint_survives_a_restart(tmp_path):
    from tooluniverse.remote_pool import FootprintStore

    FootprintStore(tmp_path / "fp").record("boltz", 9_000)

    assert FootprintStore(tmp_path / "fp").get("boltz") == 9_000


def test_the_largest_measurement_wins(tmp_path):
    """A lazily-allocating model looks smaller on a run that only initialised it.

    Admitting on the smaller number would overcommit the GPU the next time it is used.
    """
    from tooluniverse.remote_pool import FootprintStore

    store = FootprintStore(tmp_path / "fp")
    store.record("boltz", 12_000)
    store.record("boltz", 4_000)

    assert store.get("boltz") == 12_000


@pytest.mark.parametrize("value", [0, -500])
def test_a_non_positive_measurement_is_discarded(tmp_path, value):
    from tooluniverse.remote_pool import FootprintStore

    store = FootprintStore(tmp_path / "fp")
    store.record("boltz", value)

    assert store.get("boltz") is None


def test_an_implausible_measurement_is_discarded(tmp_path):
    """A misread must not wedge admission behind a number no GPU can satisfy."""
    from tooluniverse.remote_pool import MAX_PLAUSIBLE_FOOTPRINT_MIB, FootprintStore

    store = FootprintStore(tmp_path / "fp")
    store.record("boltz", MAX_PLAUSIBLE_FOOTPRINT_MIB + 1)

    assert store.get("boltz") is None


def test_a_corrupt_footprint_file_is_ignored(tmp_path):
    from tooluniverse.remote_pool import FootprintStore

    (tmp_path / "fp").mkdir()
    (tmp_path / "fp" / "footprints.json").write_text("{not json")

    assert FootprintStore(tmp_path / "fp").get("boltz") is None


# ── reading the machine ─────────────────────────────────────────────────────────


def test_the_pool_reads_the_machine_rather_than_the_device(tmp_path, monkeypatch):
    """The default reader is per-machine, and that is the whole portability claim.

    This module's first reader asked the device: `nvidia-smi --query-gpu=memory.free`.
    On unified memory that answers `[N/A]`, so the reading was None, so every memory
    ceiling built on it was skipped -- on a host with 121 GiB to reason about. The
    matrix of machines (discrete, several cards, unified, mixed, broken driver, no
    driver) is checked in `test_remote_resident.py::TestAdmission`; what belongs here
    is that the pool uses that reader and keeps its MiB vocabulary.
    """
    import subprocess as sp

    from tooluniverse import remote_pool

    # A pool built as the CLI builds one, not through `make_pool`: the helper injects a
    # machine so that the other tests do not read this one, which would make this
    # assertion about the helper.
    plain = ProviderPool(
        allow=("boltz",),
        python="/nonexistent/python",
        log_dir=tmp_path / "logs",
        schemas=SchemaStore(tmp_path / "schemas"),
    )
    assert plain.read_free_vram is pool_free_mib

    monkeypatch.setattr(
        remote_pool.admission.subprocess,
        "run",
        lambda *a, **k: sp.CompletedProcess(a, 0, "[N/A]\n", ""),
    )
    monkeypatch.setattr(
        remote_pool.admission,
        "meminfo_gib",
        lambda: {"MemTotal": 121.6, "MemFree": 90.0, "MemAvailable": 101.1},
    )

    assert pool_free_mib() == 103_526

    def missing(*_a, **_k):
        raise FileNotFoundError("nvidia-smi")

    monkeypatch.setattr(remote_pool.admission.subprocess, "run", missing)
    assert pool_free_mib() is None, "a host with no driver stays count-only"


# ── the budgets the manifests already carry ─────────────────────────────────────


def declared_pool(tmp_path, slugs, gpu, capacity=None, **kwargs):
    """A pool reading the real manifests, which is what a host actually runs.

    `boltz` declares 5.54 GiB, `atlasfold` 38.63, `proteinmpnn` 0.0 (CPU-only) and
    `esm` nothing at all, so the four of them cover every case without inventing a
    fixture the shipped providers would not match.
    """
    kwargs.setdefault("declared_footprint", declared_footprint_mib)
    kwargs.setdefault("read_capacity", lambda: capacity)
    return vram_pool(tmp_path, slugs, gpu, **kwargs)


def test_a_declared_budget_makes_a_first_load_memory_aware(tmp_path):
    """The hole this closes.

    boltz's manifest carries a measured 5.54 GiB, and the pool started it anyway on
    a machine with 2 GiB free, because nothing had been measured HERE yet. For a
    resident provider "learn it from a load" never arrives on its own: the start
    measures the MCP server, not the model.
    """
    # The same machine, the same model, the only difference being whether the
    # manifest is read: this is the before and after, not a reading of the fixture.
    blind = vram_pool(tmp_path / "blind", ["boltz"], FakeGPU(free=2_000))
    blind.acquire(blind.provider_for_tool("boltz2_docking"))
    assert blind.lifecycle.started == ["boltz"], "what shipped: admitted on count"

    gpu = FakeGPU(free=2_000)
    pool = declared_pool(tmp_path / "declared", ["boltz"], gpu)

    with pytest.raises(PoolError, match="needs 5673 MiB"):
        pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert pool.lifecycle.started == [], "a model that cannot fit must not be launched"


def test_a_local_measurement_overrides_a_smaller_declared_budget(tmp_path):
    """This machine is the authority on this machine.

    The manifest's figure was measured on the machine that verified the provider,
    which makes it a prior here and not a reading.
    """
    pool = declared_pool(tmp_path, ["boltz"], FakeGPU(free=10_000))
    pool.footprints.record("boltz", 20_000)

    with pytest.raises(PoolError, match="needs 20000 MiB"):
        pool.acquire(pool.provider_for_tool("boltz2_docking"))


def test_a_declared_budget_overrides_a_smaller_local_measurement(tmp_path):
    """A resident provider's start measures its server, not its model.

    `wait_until_ready` returns when `tools/list` matches the reviewed contract, which
    it does with the card still empty, so the difference measured across a start can
    be a few hundred MiB for a model that holds gigabytes a second later. Admitting
    on that number is how a 5.5 GiB model gets admitted into 3 GiB.
    """
    pool = declared_pool(tmp_path, ["boltz"], FakeGPU(free=3_000))
    pool.footprints.record("boltz", 300)  # the server's context, not the model

    with pytest.raises(PoolError, match="needs 5673 MiB"):
        pool.acquire(pool.provider_for_tool("boltz2_docking"))


def test_a_cpu_only_provider_has_no_memory_ceiling(tmp_path):
    """0.0 is a declared answer, not a missing one.

    proteinmpnn declares `[gpu] policy = "none"`, so it holds no device memory: it
    cannot be refused for lack of it, it frees nothing when evicted, and measuring it
    by difference would attribute whatever else allocated meanwhile to a provider
    that cannot have been the cause.
    """
    gpu = FakeGPU(free=16)
    pool = declared_pool(tmp_path, ["proteinmpnn"], gpu)

    pool.acquire(pool.provider_for_tool("proteinmpnn_design"))

    assert pool.lifecycle.started == ["proteinmpnn"]
    assert gpu.reads == 0, "a provider holding no device memory needs no reading"
    assert pool.footprints.get("proteinmpnn") is None


def test_a_provider_no_manifest_declares_is_still_admitted_on_count(tmp_path):
    """esm is one of the 28 older slugs with no manifest: unchanged behaviour."""
    gpu = FakeGPU(free=100)
    pool = declared_pool(tmp_path, ["esm"], gpu)

    pool.acquire(pool.provider_for_tool("esm_embed_sequence"))

    assert pool.lifecycle.started == ["esm"]
    assert gpu.reads == 1, "one reading, the baseline a later measurement needs"


def test_a_model_larger_than_the_machine_is_refused_before_anything_is_evicted(
    tmp_path,
):
    """atlasfold measured 38.63 GiB. On a 24 GiB machine no eviction helps.

    So the resident model is not spent on a start that cannot succeed, and the
    refusal is its own kind rather than "at capacity, retry shortly".
    """
    pool = declared_pool(
        tmp_path,
        ["atlasfold", "boltz"],
        FakeGPU(free=24_000),
        capacity=24_576,
        max_active=4,
    )
    boltz = pool.provider_for_tool("boltz2_docking")
    pool.acquire(boltz)
    pool.release(boltz)

    with pytest.raises(ProviderTooLarge, match="39557 MiB"):
        pool.acquire(pool.provider_for_tool("atlasfold_predict"))

    assert [row["provider"] for row in pool.status()] == ["boltz"]
    assert pool.lifecycle.started == ["boltz"]


def test_a_machine_whose_capacity_cannot_be_read_still_admits(tmp_path):
    """A host with no readable device is the count-only host, not a refusing one."""
    pool = declared_pool(tmp_path, ["atlasfold"], FakeGPU(free=None), capacity=None)

    pool.acquire(pool.provider_for_tool("atlasfold_predict"))

    assert pool.lifecycle.started == ["atlasfold"]


def test_a_capacity_reading_that_failed_is_not_cached(tmp_path):
    """A driver briefly unavailable must not leave this pool count-only for life."""
    readings = [OSError("driver busy"), 24_576]

    def read_capacity():
        value = readings.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    pool = declared_pool(
        tmp_path, ["atlasfold"], FakeGPU(free=None), read_capacity=read_capacity
    )
    deployment = pool.provider_for_tool("atlasfold_predict")

    pool.acquire(deployment)  # unreadable capacity: admitted
    pool.release(deployment)
    pool.unload("atlasfold")

    with pytest.raises(ProviderTooLarge):
        pool.acquire(deployment)  # the second reading answers, and it is used


def test_status_reports_the_cost_admission_will_decide_on(tmp_path):
    """`measured_vram_mib` is this host's measurements; admission decides on more.

    An operator reading a refusal against the measured column alone would be looking
    at the wrong number -- 200 MiB, for a model refused at 5673.
    """
    pool = declared_pool(
        tmp_path, ["boltz", "esm"], FakeGPU(free=31_000), capacity=124_546
    )
    pool.footprints.record("boltz", 200)

    answer = pool.control("status", {})

    assert answer["measured_vram_mib"] == {"boltz": 200}
    assert answer["expected_vram_mib"] == {"boltz": 5673}, "esm declares nothing"
    assert answer["pool_capacity_mib"] == 124_546


def test_a_refusal_with_nothing_resident_does_not_blame_a_busy_provider(tmp_path):
    """A 24 GiB machine with 4 GiB free, and this pool holding nothing.

    boltz does not fit right now, which is transient and not permanent -- so it is a
    retry and not a `ProviderTooLarge` -- and the reason is not a busy provider of
    this pool's, because it has none.
    """
    pool = declared_pool(tmp_path, ["boltz"], FakeGPU(free=4_096), capacity=24_576)

    with pytest.raises(PoolError, match="held by something else on the machine"):
        pool.acquire(pool.provider_for_tool("boltz2_docking"))

    assert pool.lifecycle.started == []


def test_the_memory_plan_names_what_cannot_run_here(tmp_path):
    """`tu serve` prints this at startup, so a host learns before a caller does."""
    pool = declared_pool(
        tmp_path,
        ["atlasfold", "boltz", "esm"],
        FakeGPU(free=None),
        capacity=24_576,
        max_active=3,
    )

    plan = pool.memory_plan()

    assert plan["capacity_mib"] == 24_576
    assert plan["expected_mib"] == {"atlasfold": 39_557, "boltz": 5_673, "esm": None}
    assert plan["too_large"] == ("atlasfold",)


def test_a_model_that_cannot_fit_is_not_answered_with_a_retry(tmp_path, capsys):
    """503 + Retry-After means "come back"; this model will never fit here.

    The caller is told the provider cannot run on this host -- the slug is already
    public, it is how the call arrived -- and the numbers stay in the operator's log.
    """
    pool = declared_pool(tmp_path, ["atlasfold"], FakeGPU(free=None), capacity=24_576)
    server = serve_pool(pool, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    try:
        status, body = _rpc(
            port,
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": "atlasfold_predict", "arguments": {}},
            },
        )
    finally:
        server.shutdown()
        server.server_close()

    message = body["error"]["message"]
    assert status == 200, "a permanent refusal is not a 503 the caller should retry"
    assert "cannot run on this host" in message
    assert "39557" not in message and "24576" not in message, message
    assert "39557 MiB" in capsys.readouterr().out


# ── what a caller is allowed to learn about the host ────────────────────────────


def test_a_refused_call_is_not_told_the_hosts_gpu_numbers(tmp_path, capsys):
    """The exception carries capacity and GPU state; the HTTP reply must not.

    A member who could read free VRAM from an error could poll it and infer what other
    people on the same machine just loaded. The numbers belong in the operator's log.
    """
    pool = vram_pool(tmp_path, ["boltz", "esm"], FakeGPU(free=1_000), max_active=2)
    pool.footprints.record("boltz", 40_000)
    server = serve_pool(pool, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/mcp",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "boltz2_docking", "arguments": {}},
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=10)
        assert caught.value.status == 503
        detail = json.loads(caught.value.read())["detail"]
    finally:
        server.shutdown()
        server.server_close()

    assert "40000" not in detail and "1000" not in detail, detail
    assert "MiB" not in detail, detail
    assert "capacity" in detail
    # The operator still gets the full reason on the host's own console.
    assert "40000 MiB" in capsys.readouterr().out


def test_a_start_failure_does_not_hand_the_caller_local_detail(tmp_path, monkeypatch):
    """Interpreter paths, log locations and ports are the host's business."""
    lifecycle = Lifecycle()

    def explode(deployment, **kwargs):
        raise RuntimeError("/home/owner/envs/boltz/bin/python failed on port 8080")

    lifecycle.ensure = explode  # type: ignore[assignment]
    pool = make_pool(tmp_path, ["boltz"], lifecycle=lifecycle)
    server = serve_pool(pool, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    try:
        status, body = _rpc(
            port,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "boltz2_docking", "arguments": {}},
            },
        )
    finally:
        server.shutdown()
        server.server_close()

    message = body["error"]["message"]
    assert status == 200
    assert "/home/owner" not in message and "8080" not in message, message
    assert "boltz" in message, "the slug is already public; it is how the call arrived"
