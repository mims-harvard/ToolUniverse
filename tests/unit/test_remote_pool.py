"""The on-demand provider pool: routing, admission, eviction and lazy discovery.

The pool exists so one command can advertise more models than the GPU could hold at
once, starting each only when a call for it arrives. These tests drive that with
injected lifecycle callables, so every rule is checked without a GPU, a provider
environment, or the platform. No network.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tooluniverse.remote_pool import (
    DEFAULT_MAX_ACTIVE,
    PoolError,
    ProviderPool,
    ProviderStarting,
    SchemaStore,
    build_tool_index,
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
        self.fail: set[str] = set()

    def ensure(self, deployment, *, python, log_dir, startup_timeout):
        if deployment.slug in self.fail:
            raise RuntimeError(f"boom: {deployment.slug}")
        self.started.append(deployment.slug)
        return object(), {"endpoint": deployment.endpoint, "ok": True}

    def stop(self, managed) -> None:
        self.stopped.append("stopped")


def make_pool(tmp_path: Path, slugs, lifecycle=None, **kwargs) -> ProviderPool:
    lifecycle = lifecycle or Lifecycle()
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


def test_a_second_request_while_a_provider_starts_is_told_to_retry(tmp_path):
    """Two concurrent first-calls must not both launch the same model."""
    release = threading.Event()
    entered = threading.Event()
    lifecycle = Lifecycle()
    real_ensure = lifecycle.ensure

    def blocking_ensure(deployment, **kwargs):
        entered.set()
        release.wait(5)
        return real_ensure(deployment, **kwargs)

    lifecycle.ensure = blocking_ensure  # type: ignore[assignment]
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
        thread.join(5)

    assert lifecycle.started == ["boltz"], "only one start may happen"


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
        ({"max_active": 0}, "--max-active"),
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
