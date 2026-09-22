"""The resident-worker plumbing: wire protocol, provider manifest, supervisor.

No GPU and no model. The supervisor tests drive a stub worker -- a few lines of
standard-library Python that speak the same protocol -- because what is under
test is the lifecycle (start once, reuse, serialize, retire when idle), not what
any particular model computes.
"""

import json
import os
import socket
import sys
import textwrap
import threading
import time

import pytest

from tooluniverse.remote_resident import protocol as P
from tooluniverse.remote_resident import manifest as M
from tooluniverse.remote_resident.supervisor import (
    ResidentWorker,
    WorkerRequestError,
    WorkerStartError,
)

BOLTZ_MANIFEST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src",
    "tooluniverse",
    "remote",
    "boltz",
    "provider.toml",
)


# --------------------------------------------------------------------- protocol
class TestProtocol:
    def test_round_trip(self):
        a, b = socket.socketpair()
        try:
            P.send_line(a, {"op": "ping", "n": 1})
            assert P.recv_line(b, bytearray()) == {"op": "ping", "n": 1}
        finally:
            a.close()
            b.close()

    def test_two_messages_in_one_read_are_not_merged(self):
        """The buffer must carry bytes past the newline to the next call."""
        a, b = socket.socketpair()
        try:
            P.send_line(a, {"i": 1})
            P.send_line(a, {"i": 2})
            buf = bytearray()
            assert P.recv_line(b, buf) == {"i": 1}
            assert P.recv_line(b, buf) == {"i": 2}
        finally:
            a.close()
            b.close()

    def test_embedded_newline_survives(self):
        a, b = socket.socketpair()
        try:
            P.send_line(a, {"yaml": "line1\nline2\n"})
            assert P.recv_line(b, bytearray())["yaml"] == "line1\nline2\n"
        finally:
            a.close()
            b.close()

    def test_peer_closing_mid_message_is_named(self):
        a, b = socket.socketpair()
        a.sendall(b'{"op": "pi')
        a.close()
        with pytest.raises(P.ProtocolError, match="closed"):
            P.recv_line(b, bytearray())
        b.close()

    def test_non_json_line_is_named(self):
        a, b = socket.socketpair()
        try:
            a.sendall(b"not json at all\n")
            with pytest.raises(P.ProtocolError, match="not JSON"):
                P.recv_line(b, bytearray())
        finally:
            a.close()
            b.close()

    def test_socket_path_is_private_to_this_uid(self, tmp_path):
        path = P.socket_path("demo", runtime_dir=str(tmp_path))
        assert path.endswith("demo.sock")
        parent = os.path.dirname(path)
        assert os.path.isdir(parent)
        assert os.stat(parent).st_mode & 0o077 == 0


# --------------------------------------------------------------------- manifest
class TestManifest:
    def test_boltz_manifest_loads_and_states_its_facts(self):
        m = M.load(BOLTZ_MANIFEST)
        assert m.slug == "boltz"
        assert m.mode == "resident"
        assert m.gpu_policy == "required"
        # Measured peak reserved; a host adds these up to decide co-tenancy.
        assert m.vram_budget_gb and m.vram_budget_gb > 0
        assert m.isolation in M.ISOLATION
        assert {w.name for w in m.weights} >= {"boltz2_conf.ckpt", "boltz2_aff.ckpt"}
        assert all(w.sha256 and w.size for w in m.weights)

    def test_unknown_key_is_refused_rather_than_ignored(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text('[provider]\nslug = "x"\n\n[gpu]\npolicy = "none"\nvram = 3\n')
        with pytest.raises(M.ManifestError, match="unknown key"):
            M.load(p)

    def test_unknown_section_is_refused(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text('[provider]\nslug = "x"\n\n[scheduler]\nqueue = "fifo"\n')
        with pytest.raises(M.ManifestError, match="unknown section"):
            M.load(p)

    def test_subprocess_mode_must_say_why(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text('[provider]\nslug = "x"\n\n[runtime]\nmode = "subprocess"\n')
        with pytest.raises(M.ManifestError, match="mode_reason"):
            M.load(p)

    def test_resident_gpu_provider_must_state_a_budget(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[gpu]\npolicy = "required"\n'
        )
        with pytest.raises(M.ManifestError, match="vram_budget_gb"):
            M.load(p)

    def test_a_weight_file_with_neither_size_nor_digest_is_refused(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[[weights.files]]\nname = "model.ckpt"\n'
        )
        with pytest.raises(M.ManifestError, match="neither size nor"):
            M.load(p)

    def test_isolation_vocabulary_excludes_what_no_box_can_honour(self):
        assert "mig" not in M.ISOLATION

    def test_truncated_weight_file_is_caught_by_size(self, tmp_path):
        (tmp_path / "model.ckpt").write_bytes(b"x" * 10)
        w = M.WeightFile(name="model.ckpt", size=1000)
        problem = w.verify(tmp_path)
        assert problem and "1.0%" in problem

    def test_wrong_bytes_at_the_right_size_are_caught_by_digest(self, tmp_path):
        (tmp_path / "model.ckpt").write_bytes(b"y" * 10)
        w = M.WeightFile(name="model.ckpt", size=10, sha256="00" * 32)
        assert "sha256" in (w.verify(tmp_path) or "")

    def test_a_file_at_its_pin_reports_nothing(self, tmp_path):
        import hashlib

        (tmp_path / "model.ckpt").write_bytes(b"z" * 10)
        digest = hashlib.sha256(b"z" * 10).hexdigest()
        assert M.WeightFile("model.ckpt", 10, digest).verify(tmp_path) is None

    def test_the_digest_memo_skips_a_second_read(self, tmp_path):
        import hashlib

        from tooluniverse.remote_resident.manifest import DigestMemo

        blob = tmp_path / "model.ckpt"
        blob.write_bytes(b"w" * 4096)
        digest = hashlib.sha256(b"w" * 4096).hexdigest()
        w = M.WeightFile("model.ckpt", 4096, digest)
        memo = DigestMemo(tmp_path / "memo.json")

        assert w.verify(tmp_path, memo) is None
        assert memo.get("model.ckpt", blob.stat()) == digest
        memo.save()
        assert (
            DigestMemo(tmp_path / "memo.json").get("model.ckpt", blob.stat()) == digest
        )

    def test_the_memo_cannot_hide_an_edit(self, tmp_path):
        """The whole point: a shortcut that survives tampering is worse than none."""
        import hashlib
        import os

        from tooluniverse.remote_resident.manifest import DigestMemo

        blob = tmp_path / "model.ckpt"
        blob.write_bytes(b"w" * 4096)
        good = hashlib.sha256(b"w" * 4096).hexdigest()
        w = M.WeightFile("model.ckpt", 4096, good)
        memo = DigestMemo(tmp_path / "memo.json")
        assert w.verify(tmp_path, memo) is None  # memo now holds the good digest

        # Same length, different bytes, and a new modification time.
        blob.write_bytes(b"x" * 4096)
        st = blob.stat()
        os.utime(blob, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
        assert "sha256" in (w.verify(tmp_path, memo) or ""), (
            "the memo served a stale digest"
        )

    def test_an_unwritable_memo_costs_time_not_correctness(self, tmp_path):
        import hashlib

        from tooluniverse.remote_resident.manifest import DigestMemo

        blob = tmp_path / "model.ckpt"
        blob.write_bytes(b"w" * 64)
        w = M.WeightFile("model.ckpt", 64, hashlib.sha256(b"w" * 64).hexdigest())
        memo = DigestMemo(tmp_path / "nope" / "deeper" / "memo.json")
        (tmp_path / "nope").write_text("a file where a directory would go")
        assert w.verify(tmp_path, memo) is None
        memo.save()  # must not raise

    def test_python_from_an_unset_variable_is_named(self, tmp_path, monkeypatch):
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[env]\npython = "$TU_TEST_NO_SUCH_PYTHON"\n'
        )
        monkeypatch.delenv("TU_TEST_NO_SUCH_PYTHON", raising=False)
        with pytest.raises(M.ManifestError, match="TU_TEST_NO_SUCH_PYTHON"):
            M.load(p).python_executable()


# ------------------------------------------------------------------- supervisor
STUB_WORKER = textwrap.dedent(
    """
    import json, os, socket, sys, time
    sock_path = sys.argv[1]
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path); srv.listen(8)
    calls = 0
    while True:
        conn, _ = srv.accept()
        buf = b""
        while b"\\n" not in buf:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
        if not buf:
            conn.close(); continue
        req = json.loads(buf.split(b"\\n")[0])
        op = req.get("op")
        if op == "ping":
            reply = {"ok": True, "model": "stub", "ready": True, "pid": os.getpid()}
        elif op == "shutdown":
            conn.sendall((json.dumps({"ok": True}) + "\\n").encode()); conn.close()
            break
        elif op == "boom":
            reply = {"ok": False, "error": "asked to fail", "reason": "asked"}
        else:
            calls += 1
            time.sleep(float(req.get("sleep", 0)))
            reply = {"ok": True, "result": {"calls": calls, "pid": os.getpid()}}
        conn.sendall((json.dumps(reply) + "\\n").encode())
        conn.close()
    """
)


@pytest.fixture
def stub_worker(tmp_path):
    script = tmp_path / "stub_worker.py"
    script.write_text(STUB_WORKER)
    workers = []

    def make(**kwargs):
        w = ResidentWorker(
            slug=f"stub-{len(workers)}-{os.getpid()}",
            build_command=lambda worker: (
                [sys.executable, str(script), worker.socket_path],
                {},
            ),
            start_timeout_s=30.0,
            **kwargs,
        )
        workers.append(w)
        return w

    yield make
    for w in workers:
        w.stop(grace_s=5)


class TestSupervisor:
    def test_starts_on_first_request_and_reuses_the_process(self, stub_worker):
        w = stub_worker()
        assert w.ping() is None  # nothing running before the first request
        first = w.request({"op": "predict"})["result"]
        second = w.request({"op": "predict"})["result"]
        assert first["pid"] == second["pid"], "the model process must be reused"
        assert (first["calls"], second["calls"]) == (1, 2)

    def test_a_failed_request_does_not_kill_the_worker(self, stub_worker):
        w = stub_worker()
        w.request({"op": "predict"})
        with pytest.raises(WorkerRequestError) as exc:
            w.request({"op": "boom"})
        assert exc.value.reason == "asked"
        assert w.request({"op": "predict"})["result"]["calls"] == 2

    def test_requests_are_serialized_over_the_device(self, stub_worker):
        """A request in flight holds the worker's lock for its whole duration.

        Two requests inside one CUDA context would interleave their allocations
        and make an out-of-memory attributable to neither, so the guarantee is
        that a second caller waits. Timing cannot show this -- a stub accepting
        one connection at a time would serialize either way -- so the lock is
        what is asserted.
        """
        w = stub_worker()
        w.request({"op": "predict"})  # pay the start-up once
        held = threading.Event()
        released = []

        def slow_call():
            held.set()
            w.request({"op": "predict", "sleep": 1.0})
            released.append(True)

        t = threading.Thread(target=slow_call)
        t.start()
        held.wait(timeout=10)
        time.sleep(0.2)  # let the thread get inside request()
        assert not w.lock.acquire(blocking=False), (
            "a second caller could enter while a request was in flight"
        )
        t.join(timeout=30)
        assert released == [True]
        # And it is available again once the request is done.
        assert w.lock.acquire(blocking=False)
        w.lock.release()

    def test_stop_releases_the_socket_and_the_process(self, stub_worker):
        w = stub_worker()
        w.request({"op": "predict"})
        assert w.is_running() and os.path.exists(w.socket_path)
        w.stop(grace_s=5)
        assert not w.is_running()
        assert not os.path.exists(w.socket_path)

    def test_an_idle_worker_gives_the_card_back(self, stub_worker):
        w = stub_worker(idle_timeout_s=1.0)
        w.request({"op": "predict"})
        first_pid = w.ping()["pid"]
        deadline = time.time() + 30
        while w.is_running() and time.time() < deadline:
            time.sleep(0.5)
        assert not w.is_running(), "the worker should have retired while idle"
        # And it comes back for the next request, as a new process.
        assert w.request({"op": "predict"})["result"]["pid"] != first_pid

    def test_a_worker_that_never_binds_is_named(self, tmp_path):
        script = tmp_path / "exits.py"
        script.write_text("import sys; sys.exit(7)")
        w = ResidentWorker(
            slug=f"stub-exit-{os.getpid()}",
            build_command=lambda worker: ([sys.executable, str(script)], {}),
            start_timeout_s=10.0,
        )
        with pytest.raises(WorkerStartError, match="exited 7"):
            w.request({"op": "predict"})

    def test_a_stale_socket_from_a_killed_worker_is_cleared(self, stub_worker):
        w = stub_worker()
        w.request({"op": "predict"})
        pid = w.ping()["pid"]
        w._proc.kill()
        w._proc.wait(timeout=10)
        assert os.path.exists(w.socket_path), "a killed worker leaves its socket"
        assert w.request({"op": "predict"})["result"]["pid"] != pid
