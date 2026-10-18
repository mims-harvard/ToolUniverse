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

from pathlib import Path

import pytest

from tooluniverse.remote_resident import protocol as P
from tooluniverse.remote_resident import manifest as M
from tooluniverse.remote_resident import setup as S
from tooluniverse.remote_resident.supervisor import (
    ResidentWorker,
    WorkerRequestError,
    WorkerStartError,
    exit_hint,
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

    def test_verified_without_a_success_condition_is_refused(self, tmp_path):
        """The gap that let openfold3 be marked verified having folded nothing."""
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\nstatus = "verified"\n'
            'verified_on = "a card"\n\n[runtime]\nmode = "resident"\n'
        )
        with pytest.raises(M.ManifestError, match="outputs or output_keys"):
            M.load(p)

    def test_outputs_satisfies_the_success_condition(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\nstatus = "verified"\n'
            'verified_on = "a card"\n\n[runtime]\nmode = "resident"\n'
            'outputs = ["*.cif"]\n\n[env]\npython = "python3"\n'
        )
        assert M.load(p).outputs == ("*.cif",)

    def test_output_keys_satisfies_it_for_a_provider_that_writes_no_files(
        self, tmp_path
    ):
        """Enformer answers with arrays; a file glob would refuse it forever."""
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\nstatus = "verified"\n'
            'verified_on = "a card"\n\n[runtime]\nmode = "resident"\n'
            'output_keys = ["centre"]\n\n[env]\npython = "python3"\n'
        )
        assert M.load(p).output_keys == ("centre",)

    def test_untested_needs_no_success_condition(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[env]\npython = "python3"\n'
        )
        assert M.load(p).status == "untested"

    def test_kit_env_carries_a_kit_knob_the_provider_states(self, tmp_path):
        """openfold3 needs POST_RELEASE_NTOK=0 or it dies on request two."""
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[env]\npython = "python3"\n\n[kit.env]\n'
            'OPENFOLD3_OPT_POST_RELEASE_NTOK = "0"\n'
        )
        assert M.load(p).kit["env"]["OPENFOLD3_OPT_POST_RELEASE_NTOK"] == "0"

    def test_kit_env_refuses_a_nested_table(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[env]\npython = "python3"\n\n[kit.env.nested]\na = 1\n'
        )
        with pytest.raises(M.ManifestError, match="scalar"):
            M.load(p)

    def test_an_undeclared_absent_kit_row_is_not_silently_accepted(self, tmp_path):
        """openfold3 ran with 0 of its 37 variables and said nothing."""
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[env]\npython = "python3"\n\n[kit]\nenv_row = "none"\n'
        )
        with pytest.raises(M.ManifestError, match="env_row_reason"):
            M.load(p)

    def test_a_declared_absent_kit_row_states_where_the_variables_live(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[env]\npython = "python3"\n\n[kit]\nenv_row = "none"\n'
            'env_row_reason = "configs/<card>.env, and none ships for this card"\n'
        )
        assert M.load(p).kit["env_row"] == "none"

    def test_an_unknown_env_row_value_is_refused(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[env]\npython = "python3"\n\n[kit]\nenv_row = "maybe"\n'
        )
        with pytest.raises(M.ManifestError, match="env_row"):
            M.load(p)

    def test_a_weight_file_with_neither_size_nor_digest_is_refused(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "subprocess"\nmode_reason = "t"\n\n'
            '[[weights.files]]\nname = "model.ckpt"\n'
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


# ------------------------------------------------------------------------ setup
class TestSetup:
    def test_the_kit_checkout_is_addressed_by_its_commit(self, monkeypatch, tmp_path):
        from tooluniverse.remote_resident import setup as S

        monkeypatch.setenv("TOOLUNIVERSE_KIT_ROOT", str(tmp_path))
        m = M.load(BOLTZ_MANIFEST)
        path = S.kit_checkout(m)
        assert path.parent == tmp_path
        assert path.name.endswith("@" + m.kit["commit"])
        # Two providers pinning the same commit must land on one checkout.
        assert S.kit_checkout(m) == path

    def test_a_provider_without_a_kit_has_no_checkout(self, tmp_path):
        from tooluniverse.remote_resident import setup as S

        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "subprocess"\nmode_reason = "test"\n'
        )
        assert S.kit_checkout(M.load(p)) is None

    @pytest.mark.parametrize(
        "line,tampering",
        [
            (" M boltz2/opt/boltz2_opt/modes.py", True),
            ("?? boltz2/opt/forward/waste/__pycache__/", False),
            ("?? common/opt_core/opt_core.egg-info/", False),
            ("?? boltz2/opt/boltz2_opt/backdoor.py", True),
            ("?? boltz2/.jit/torch2.12.0-cu130-sm121/", False),
            ("", False),
        ],
    )
    def test_byproducts_are_not_tampering_but_new_code_is(self, line, tampering):
        """Running the kit leaves caches; refusing those would refuse every used tree."""
        from tooluniverse.remote_resident.setup import _is_tampering

        assert _is_tampering(line) is tampering

    def test_preflight_refuses_a_host_that_cannot_run_it(self, monkeypatch, tmp_path):
        import shutil as _shutil

        from tooluniverse.remote_resident import setup as S

        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[env]\npython = "$X_PY"\n\n'
            '[gpu]\npolicy = "required"\nvram_budget_gb = 1\n'
        )
        monkeypatch.setattr(S.shutil, "which", lambda name: None)
        monkeypatch.setattr(
            _shutil,
            "disk_usage",
            lambda p: type("U", (), {"free": 1 << 40, "total": 1 << 40})(),
        )
        r = S.step_preflight(M.load(p))
        assert r.verdict == S.REFUSED
        assert not r.ok
        # The first named reason is what a skill's table keys on.
        assert r.reason in ("no_nvidia_smi", "compiler_missing")

    def test_the_driver_stops_at_the_first_step_that_is_not_ok(self, monkeypatch):
        from tooluniverse.remote_resident import setup as S

        calls = []

        def ok(name):
            def step(manifest):
                calls.append(name)
                return S.StepResult(name, S.OK)

            step.__name__ = f"step_{name}"
            return step

        def bad(name):
            def step(manifest):
                calls.append(name)
                return S.StepResult(name, S.REFUSED, reason="nope")

            step.__name__ = f"step_{name}"
            return step

        monkeypatch.setattr(S, "STEPS", (ok("a"), bad("b"), ok("c")))
        results = S.run_setup(BOLTZ_MANIFEST)
        assert calls == ["a", "b"], "a cascade would bury the step that mattered"
        assert S.exit_code(results) == S.EXIT_REFUSED

    def test_exit_codes_are_branchable(self):
        from tooluniverse.remote_resident import setup as S

        assert S.exit_code([S.StepResult("a", S.OK)]) == S.EXIT_OK
        assert S.exit_code([S.StepResult("a", S.PRESENT)]) == S.EXIT_OK
        assert S.exit_code([S.StepResult("a", S.REFUSED)]) == S.EXIT_REFUSED
        assert S.exit_code([S.StepResult("a", S.FAILED)]) == S.EXIT_FAILED

    def test_boltz_declares_a_smoke_input_that_exists(self):
        """A provider with no smoke step can never be more than `untested`."""
        m = M.load(BOLTZ_MANIFEST)
        assert m.smoke, "a verified provider must declare how to prove itself"
        assert m.resolve(m.smoke).is_file()


# -------------------------------------------------------------------- kit_launch
class TestKitLaunch:
    def test_the_package_name_defaults_to_the_convention(self, tmp_path):
        """35 of the 36 kits name their package <kit>_opt."""
        from tooluniverse.remote_resident import kit_launch as KL

        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "chrombpnet"\n\n[runtime]\nmode = "subprocess"\nmode_reason = "t"\n\n[kit]\n'
            'upstream = "https://example.invalid/x"\n'
            f'commit = "{"a" * 40}"\nsubdir = "chrombpnet"\n'
        )
        assert KL.kit_package(M.load(p)) == "chrombpnet_opt"

    def test_the_one_kit_that_breaks_the_convention_can_say_so(self, tmp_path):
        from tooluniverse.remote_resident import kit_launch as KL

        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "protenix_v2"\n\n[runtime]\nmode = "subprocess"\nmode_reason = "t"\n\n[kit]\n'
            'upstream = "https://example.invalid/x"\n'
            f'commit = "{"a" * 40}"\nsubdir = "protenix_v2"\npackage = "protenix_opt"\n'
        )
        assert KL.kit_package(M.load(p)) == "protenix_opt"

    def test_boltz_uses_the_generic_launcher(self):
        """The template is only a template if the first provider is on it."""
        m = M.load(BOLTZ_MANIFEST)
        assert m.launch == "tooluniverse.remote_resident.kit_launch:build_command"
        assert "{socket}" in " ".join(m.worker_args)
        assert "{weights_root}" in " ".join(m.worker_args)

    def test_a_kit_that_is_not_installed_is_named_not_guessed(self, tmp_path):
        from tooluniverse.remote_resident import kit_launch as KL

        with pytest.raises(KL.KitUnavailable, match="mode row"):
            KL.ask_kit(sys.executable, "no_such_kit_opt", "fast")


# ---------------------------------------------------------------- two providers
ENFORMER_MANIFEST = os.path.join(
    os.path.dirname(BOLTZ_MANIFEST).replace("boltz", "enformer"), "provider.toml"
)


class TestSecondProvider:
    """What stops the standard being a description of one provider."""

    def test_both_providers_load_and_declare_what_they_measured(self):
        for path in (BOLTZ_MANIFEST, ENFORMER_MANIFEST):
            m = M.load(path)
            assert m.mode == "resident"
            assert m.vram_budget_gb and m.vram_budget_gb > 0
            if m.status == "verified":
                assert m.verified_on, f"{m.slug} claims verified without hardware"

    def test_they_do_not_share_an_environment(self):
        """The whole reason for the split: their stacks cannot coexist."""
        pins = {}
        for path in (BOLTZ_MANIFEST, ENFORMER_MANIFEST):
            m = M.load(path)
            lock = m.resolve(m.env_lock).read_text()
            pins[m.slug] = {
                line.split("==")[0]: line.split("==")[1]
                for line in lock.splitlines()
                if line and not line.startswith("#") and "==" in line
            }
        for pkg in ("torch", "numpy"):
            assert pins["boltz"][pkg] != pins["enformer"][pkg], (
                f"{pkg} happens to match; pick another to make the point"
            )

    def test_they_use_different_kit_activations(self):
        """boltz2 is the only kit of 36 with worker_launch; the rest use a variable."""
        boltz, enformer = M.load(BOLTZ_MANIFEST), M.load(ENFORMER_MANIFEST)
        assert boltz.launch == enformer.launch, "one launcher serves both"
        assert boltz.kit["package"] == "boltz2_opt"
        assert enformer.kit["package"] == "enformer_opt"

    def test_a_kit_turned_off_says_why(self):
        """An architecture that cannot load a kit is recorded, not silently dropped."""
        m = M.load(ENFORMER_MANIFEST)
        if m.kit.get("mode") == "off":
            assert m.kit.get("levers_declined"), (
                "off with nothing declined reads as a preference"
            )
            assert "x86-64" in m.resolve("provider.toml").read_text()

    @pytest.mark.parametrize(
        "head,foreign",
        [
            (b"\x7fELF\x02\x01\x01" + b"\x00" * 11 + b"\x3e\x00", "x86_64"),
            (b"\x7fELF\x02\x01\x01" + b"\x00" * 11 + b"\xb7\x00", "aarch64"),
        ],
    )
    def test_foreign_objects_are_read_from_the_elf_header(
        self, tmp_path, head, foreign
    ):
        """A kit's own check reports the GPU architecture, not the file's."""
        import platform

        from tooluniverse.remote_resident.setup import _foreign_objects

        (tmp_path / "kernel.so").write_bytes(head + b"\x00" * 64)
        found = _foreign_objects(tmp_path)
        assert bool(found) is (platform.machine() != foreign)


# ------------------------------------------------------------------- exec_env
class TestExecEnvironment:
    """Three routes to the same stack; only the argv that starts a worker differs."""

    def _env(self, kind, tmp_path, **kw):
        from tooluniverse.remote_resident.exec_env import ExecEnvironment

        (tmp_path / "weights").mkdir(exist_ok=True)
        return ExecEnvironment(kind=kind, binds=[tmp_path / "weights"], **kw)

    def test_a_venv_is_just_the_interpreter(self, tmp_path):
        e = self._env("venv", tmp_path, python="/opt/py/bin/python")
        argv, env = e.argv(["w.py", "--socket", "/s"], {"K": "V"})
        assert argv == ["/opt/py/bin/python", "w.py", "--socket", "/s"]
        assert env["K"] == "V"

    def test_docker_maps_paths_identity(self, tmp_path):
        """A path must mean the same thing on both sides, or everything needs translating."""
        e = self._env("docker", tmp_path, image="kit:dev")
        argv, _ = e.argv(["w.py"], {})
        mount = f"{(tmp_path / 'weights').resolve()}:{(tmp_path / 'weights').resolve()}"
        assert "-v" in argv and mount in argv

    def test_docker_passes_the_environment_into_the_container(self, tmp_path):
        """Popen's env would reach the client, not the model."""
        e = self._env("docker", tmp_path, image="kit:dev")
        argv, popen_env = e.argv(["w.py"], {"BOLTZ2_OPT": "fast"})
        assert "-e" in argv and "BOLTZ2_OPT=fast" in argv
        assert "BOLTZ2_OPT" not in popen_env

    def test_docker_runs_as_the_calling_user(self, tmp_path):
        """The kits' images create no unprivileged user; outputs land on a bind."""
        e = self._env("docker", tmp_path, image="kit:dev")
        argv, _ = e.argv(["w.py"], {})
        assert "--user" in argv
        assert f"{os.getuid()}:{os.getgid()}" in argv

    def test_docker_asks_for_the_gpu_and_shared_memory(self, tmp_path):
        e = self._env("docker", tmp_path, image="kit:dev", gpu=True)
        argv, _ = e.argv(["w.py"], {})
        assert "--gpus" in argv and "all" in argv
        assert "--ipc=host" in argv

    def test_a_missing_declaration_is_named(self, tmp_path):
        from tooluniverse.remote_resident.exec_env import ExecEnvironmentError

        with pytest.raises(ExecEnvironmentError, match="env. image"):
            self._env("docker", tmp_path).argv(["w.py"], {})
        with pytest.raises(ExecEnvironmentError, match="env. python"):
            self._env("venv", tmp_path).argv(["w.py"], {})

    def test_an_unknown_kind_is_refused(self, tmp_path):
        from tooluniverse.remote_resident.exec_env import ExecEnvironmentError

        with pytest.raises(ExecEnvironmentError, match="not one of"):
            self._env("podman", tmp_path)

    def test_nested_binds_collapse(self, tmp_path):
        """A parent already bound carries its children; repeating them is noise."""
        from tooluniverse.remote_resident.exec_env import ExecEnvironment

        (tmp_path / "a" / "b").mkdir(parents=True)
        e = ExecEnvironment(
            kind="docker", image="x", binds=[tmp_path / "a", tmp_path / "a" / "b"]
        )
        argv, _ = e.argv(["w.py"], {})
        # The identity files and the cache are bound too; count only these.
        mine = [
            argv[i + 1]
            for i, a in enumerate(argv)
            if a == "-v" and str(tmp_path) in argv[i + 1]
        ]
        assert len(mine) == 1 and str(tmp_path / "a") in mine[0]

    def test_a_container_needs_a_work_root(self, tmp_path):
        """Per-request output paths the caller invents are invisible without one."""
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[env]\nkind = "docker"\nimage = "kit:dev"\n'
        )
        with pytest.raises(M.ManifestError, match="work_root"):
            M.load(p)


class TestContainerHygiene:
    """What a container needs before a scientific stack will run in it as you."""

    def _docker(self, tmp_path):
        from tooluniverse.remote_resident.exec_env import ExecEnvironment

        return ExecEnvironment(kind="docker", image="kit:dev", binds=[tmp_path])

    def test_the_calling_uid_is_given_a_passwd_entry(self, tmp_path, monkeypatch):
        """pwd.getpwuid raises for a uid the image has never heard of."""
        monkeypatch.setenv("TOOLUNIVERSE_CONTAINER_ID_DIR", str(tmp_path / "id"))
        argv, _ = self._docker(tmp_path).argv(["w.py"], {})
        mounts = [argv[i + 1] for i, a in enumerate(argv) if a == "-v"]
        assert any(m.endswith("/etc/passwd:ro") for m in mounts)
        assert any(m.endswith("/etc/group:ro") for m in mounts)
        passwd = (tmp_path / "id" / "passwd").read_text()
        assert f":{os.getuid()}:{os.getgid()}:" in passwd
        # Only root and the caller: binding the host's own passwd would hand
        # the model every account on the machine.
        assert len(passwd.strip().splitlines()) == 2

    def test_the_container_gets_a_home_of_its_own(self, tmp_path, monkeypatch):
        """Not the host's: that path is a root-owned mount point inside."""
        monkeypatch.setenv("TOOLUNIVERSE_CONTAINER_CACHE_DIR", str(tmp_path / "c"))
        monkeypatch.setenv("TOOLUNIVERSE_CONTAINER_ID_DIR", str(tmp_path / "id"))
        argv, _ = self._docker(tmp_path).argv(["w.py"], {})
        home = [a for a in argv if a.startswith("HOME=")]
        assert home and home[0] != f"HOME={os.path.expanduser('~')}"
        assert str(tmp_path / "c") in home[0]

    @pytest.mark.parametrize(
        "var", ["NUMBA_CACHE_DIR", "TRITON_CACHE_DIR", "MPLCONFIGDIR", "XDG_CACHE_HOME"]
    )
    def test_every_compiler_cache_points_somewhere_writable(
        self, tmp_path, monkeypatch, var
    ):
        """site-packages is root-owned; numba refuses with 'no locator available'."""
        monkeypatch.setenv("TOOLUNIVERSE_CONTAINER_CACHE_DIR", str(tmp_path / "c"))
        monkeypatch.setenv("TOOLUNIVERSE_CONTAINER_ID_DIR", str(tmp_path / "id"))
        argv, _ = self._docker(tmp_path).argv(["w.py"], {})
        value = [a for a in argv if a.startswith(f"{var}=")]
        assert value, f"{var} is not set for the container"
        assert str(tmp_path / "c") in value[0]

    def test_a_host_user_site_cannot_shadow_the_pinned_stack(
        self, tmp_path, monkeypatch
    ):
        """The kits' own Apptainer recipe sets this for the same reason."""
        monkeypatch.setenv("TOOLUNIVERSE_CONTAINER_CACHE_DIR", str(tmp_path / "c"))
        monkeypatch.setenv("TOOLUNIVERSE_CONTAINER_ID_DIR", str(tmp_path / "id"))
        argv, _ = self._docker(tmp_path).argv(["w.py"], {})
        assert "PYTHONNOUSERSITE=1" in argv

    def test_the_worker_and_its_smoke_input_are_bound(self, tmp_path):
        """They are resolved from the manifest but need not live beside it."""
        from tooluniverse.remote_resident.exec_env import from_manifest

        m = M.load(BOLTZ_MANIFEST)
        object.__setattr__(m, "env_kind", "docker")
        object.__setattr__(m, "work_root", str(tmp_path))
        binds = {str(p) for p in from_manifest(m).binds}
        assert str(m.resolve(m.worker).parent) in binds
        assert str(m.resolve(m.smoke).parent) in binds


class TestApptainerRoute:
    """The route whose build needs privilege and whose run does not."""

    def _sif(self, tmp_path):
        from tooluniverse.remote_resident.exec_env import ExecEnvironment

        return ExecEnvironment(
            kind="apptainer", sif=str(tmp_path / "k.sif"), binds=[tmp_path]
        )

    def test_it_asks_for_the_gpu_and_a_clean_environment(self, tmp_path):
        import shutil

        if not (shutil.which("apptainer") or shutil.which("singularity")):
            pytest.skip("no apptainer or singularity on PATH")
        argv, _ = self._sif(tmp_path).argv(["w.py"], {})
        assert "--nv" in argv
        # The kits' own recipe uses it: the host's variables stay out, and the
        # ones the worker needs are passed explicitly.
        assert "--cleanenv" in argv
        assert "--bind" in argv

    def test_either_implementation_satisfies_the_kind(self, tmp_path, monkeypatch):
        """Apptainer (Linux Foundation, 1.x) and SingularityCE (Sylabs, 4.x) are
        forks of one project and the kits treat them as interchangeable."""
        import shutil

        from tooluniverse.remote_resident.exec_env import ExecEnvironmentError

        monkeypatch.setattr(
            shutil,
            "which",
            lambda n: "/usr/bin/singularity" if n == "singularity" else None,
        )
        argv, _ = self._sif(tmp_path).argv(["w.py"], {})
        assert argv[0].endswith("singularity")

        monkeypatch.setattr(shutil, "which", lambda n: None)
        with pytest.raises(ExecEnvironmentError, match="apptainer nor singularity"):
            self._sif(tmp_path).argv(["w.py"], {})

    def test_it_needs_no_synthetic_passwd(self, tmp_path):
        """It runs as the caller already; there is no uid to introduce."""
        import shutil

        if not (shutil.which("apptainer") or shutil.which("singularity")):
            pytest.skip("no apptainer or singularity on PATH")
        argv, _ = self._sif(tmp_path).argv(["w.py"], {})
        assert not any("/etc/passwd" in a for a in argv)
        assert not any(a == "--user" for a in argv)

    def test_the_manifest_records_which_implementation_ran(self):
        """`kind = "apptainer"` covers two projects; a claim should say which."""
        m = M.load(BOLTZ_MANIFEST)
        if m.status == "verified" and "apptainer" in m.verified_on.lower():
            assert any(
                word in m.verified_on
                for word in ("SingularityCE", "Apptainer", "singularity")
            ), "an apptainer claim must name the implementation it ran under"


class TestTorchTargetsThisGpu:
    """A stack can install perfectly and still not be able to drive the card."""

    def _verdict(self, arch_list, device_sm, monkeypatch, torch_version="2.13.0+cu130"):
        import json as _json

        from tooluniverse.remote_resident import setup as S

        payload = _json.dumps(
            {
                "torch": torch_version,
                "arch_list": arch_list,
                "device_sm": device_sm,
                "device": "TEST GPU",
            }
        )
        monkeypatch.setattr(
            S,
            "_run",
            lambda *a, **k: type(
                "P", (), {"stdout": "ARCH " + payload, "returncode": 0}
            )(),
        )
        env = type("E", (), {"argv": lambda self, args: (["python"], {})})()
        return S._check_torch_targets_this_gpu(env, True)

    def test_a_later_minor_of_the_same_major_is_binary_compatible(self, monkeypatch):
        """An sm_120 cubin runs on sm_121 — which is how both of this project's
        stacks drive a card neither of them lists. Getting this wrong refuses a
        provider that demonstrably works."""
        assert (
            self._verdict(
                ["sm_80", "sm_90", "sm_100", "sm_110", "sm_120"], "sm_121", monkeypatch
            )
            is None
        )

    def test_an_older_major_is_not(self, monkeypatch):
        """flashzoi pins torch 2.5.1, whose CUDA build stops at sm_90."""
        problem = self._verdict(
            ["sm_50", "sm_80", "sm_90"], "sm_121", monkeypatch, "2.5.1"
        )
        assert problem and "sm_121" in problem and "2.5.1" in problem

    def test_ptx_for_an_earlier_architecture_compiles_forward(self, monkeypatch):
        assert self._verdict(["sm_80", "compute_80"], "sm_90", monkeypatch) is None

    def test_an_exact_match_is_fine(self, monkeypatch):
        assert self._verdict(["sm_90"], "sm_90", monkeypatch) is None

    def test_a_newer_minor_in_the_build_than_the_card_is_not_claimed(self, monkeypatch):
        """sm_121 code does not run on an sm_120 card."""
        assert self._verdict(["sm_121"], "sm_120", monkeypatch) is not None

    def test_an_environment_without_torch_is_not_judged(self, monkeypatch):
        from tooluniverse.remote_resident import setup as S

        monkeypatch.setattr(
            S, "_run", lambda *a, **k: type("P", (), {"stdout": "", "returncode": 0})()
        )
        env = type("E", (), {"argv": lambda self, args: (["python"], {})})()
        assert S._check_torch_targets_this_gpu(env, True) is None


class TestRemoteListShowsTheStandard:
    """A rollout is only legible if you can see who is on the standard."""

    def _rows(self, capsys):
        import json as _json
        import sys as _sys

        from tooluniverse.cli import main

        argv = _sys.argv
        _sys.argv = ["tu", "remote", "list", "--json"]
        try:
            main()
        except SystemExit:
            pass
        finally:
            _sys.argv = argv
        return _json.loads(capsys.readouterr().out)["implementations"]

    def test_a_provider_with_a_manifest_reports_what_it_declares(self, capsys):
        rows = {r["implementation"]: r for r in self._rows(capsys)}
        assert "boltz" in rows
        m = rows["boltz"].get("manifest")
        assert m, "boltz declares a manifest and the listing should say so"
        assert m["mode"] == "resident"
        assert m["vram_budget_gb"] and m["status"] in ("verified", "untested")

    def test_a_provider_without_one_is_still_listed(self, capsys):
        rows = {r["implementation"]: r for r in self._rows(capsys)}
        plain = [r for r in rows.values() if "manifest" not in r]
        assert plain, "the providers not yet on the standard must not disappear"

    def test_a_manifest_without_an_entry_point_is_not_invisible(self, capsys):
        """Manifest first, entry point second, is the order a rollout goes in."""
        rows = self._rows(capsys)
        orphans = [r for r in rows if r.get("endpoint") is None]
        for r in orphans:
            assert r.get("note"), (
                "an unregistered provider should say why it has no endpoint"
            )
            assert r.get("manifest"), "it is only listed because it declares one"


class TestWhatItProduced:
    """The check that an exit code is not evidence a model ran.

    OpenFold3's runner catches its own per-query exception, writes a summary
    reading "Failed Queries: 1" and returns normally. The smoke step saw a
    reply, a timing and a GPU peak, and recorded the provider as verified
    having produced no structure at all. These tests pin the assertion that
    now stands between those two things.
    """

    @staticmethod
    def _manifest(tmp_path, **runtime):
        rows = "".join(f"{k} = {v}\n" for k, v in runtime.items())
        p = tmp_path / "provider.toml"
        p.write_text(
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n'
            f"{rows}\n"
            '[env]\npython = "python3"\n'
        )
        return M.load(p)

    def test_a_declared_output_that_appeared_passes(self, tmp_path):
        out = tmp_path / "out"
        out.mkdir()
        (out / "pred.cif").write_text("data_")
        m = self._manifest(tmp_path, outputs='["*.cif"]')
        matched, refusal = S._what_it_produced(m, {"files": []}, out)
        assert refusal == ""
        assert matched["outputs"]

    def test_a_declared_output_that_never_appeared_is_refused(self, tmp_path):
        """openfold3's exact shape: a summary file and no structure."""
        out = tmp_path / "out"
        out.mkdir()
        (out / "summary.txt").write_text("Failed Queries: 1")
        m = self._manifest(tmp_path, outputs='["*.cif"]')
        _, refusal = S._what_it_produced(m, {"files": []}, out)
        assert "produced none of" in refusal
        # The refusal names what it DID write, so the reader can see the
        # summary file and go read it.
        assert "summary.txt" in refusal

    def test_the_worker_s_own_file_list_counts_too(self, tmp_path):
        """A provider need not write into out_dir for its output to be real."""
        elsewhere = tmp_path / "pred.cif"
        elsewhere.write_text("data_")
        m = self._manifest(tmp_path, outputs='["*.cif"]')
        _, refusal = S._what_it_produced(
            m, {"files": [str(elsewhere)]}, tmp_path / "empty"
        )
        assert refusal == ""

    def test_a_compound_extension_is_matched(self, tmp_path):
        """RFdiffusion3 gzips its backbones; "*.cif" would match nothing."""
        out = tmp_path / "out"
        out.mkdir()
        (out / "design_0.cif.gz").write_bytes(b"\x1f\x8b")
        m = self._manifest(tmp_path, outputs='["*.cif.gz"]')
        _, refusal = S._what_it_produced(m, {}, out)
        assert refusal == ""

    def test_an_empty_reply_key_is_refused(self, tmp_path):
        """Enformer writes no files, so its assertion is on the reply."""
        m = self._manifest(tmp_path, output_keys='["centre"]')
        _, refusal = S._what_it_produced(m, {"centre": []}, tmp_path)
        assert "centre" in refusal

    def test_a_filled_reply_key_passes(self, tmp_path):
        m = self._manifest(tmp_path, output_keys='["centre"]')
        matched, refusal = S._what_it_produced(m, {"centre": [0.1, 0.2]}, tmp_path)
        assert refusal == ""
        assert matched["output_keys"] == ["centre"]

    def test_a_provider_declaring_nothing_is_not_blocked(self, tmp_path):
        """status = "untested" needs no condition; the manifest enforces that."""
        m = self._manifest(tmp_path)
        _, refusal = S._what_it_produced(m, {}, tmp_path)
        assert refusal == ""


class TestTritonTargetsThisGpu:
    """Triton is a second toolchain and the torch arch check cannot see it.

    Both findings are NOTES. The first version of this check refused the LLVM
    one and that was a false refusal: evo2 runs on triton 3.3.1 on this card
    while atlasfold dies on the identical triton, because whether the abort
    happens depends on the provider's kernels and not on the version. A bare
    tl.sum kernel core-dumps in both environments, so the stack's inability is
    real -- it is the consequence that differs, and this layer cannot see it.
    """

    SM = "sm_121"

    def _info(self, version, llvm, ptxas):
        return {
            "device_sm": self.SM,
            "triton": version,
            "triton_llvm": llvm,
            "triton_ptxas": ptxas,
        }

    def test_a_triton_that_knows_the_card_and_ships_a_ptxas_says_nothing(self):
        """triton 3.6.0+ needs nothing: it bundles its own ptxas-blackwell."""
        assert (
            S._check_triton_targets_this_gpu(
                self._info(
                    "3.7.1",
                    ["sm_90", "sm_120", "sm_121", "sm_121a"],
                    {
                        "ptxas": ["sm_90", "sm_120"],
                        "ptxas-blackwell": ["sm_121", "sm_121a"],
                    },
                )
            )
            == []
        )

    def test_an_llvm_that_ignores_the_card_is_noted_not_refused(self):
        """atlasfold and evo2 share this triton; only one of them dies."""
        notes = S._check_triton_targets_this_gpu(
            self._info(
                "3.3.1",
                ["sm_90", "sm_120", "sm_120a"],
                {"ptxas": ["sm_90"], "ptxas-blackwell": ["sm_120", "sm_120a"]},
            )
        )
        joined = " ".join(notes)
        assert "LLVM ERROR" in joined and "AUDIT" in joined
        # Both stages fail for this version, and the ptxas half is the half a
        # provider can fix -- the first version short-circuited and hid it.
        assert "nvidia-cuda-nvcc-cu12" in joined
        assert len(notes) == 2

    def test_a_missing_ptxas_target_names_the_derived_variable(self):
        """e1's triton 3.4.0 works, because its worker supplies a 12.9 ptxas."""
        notes = S._check_triton_targets_this_gpu(
            self._info("3.4.0", ["sm_120", "sm_121", "sm_121a"], {"ptxas": ["sm_120"]})
        )
        assert len(notes) == 1
        # The name is built as TRITON_<BINARY>_PATH, so on this card it carries
        # a hyphen and a literal TRITON_PTXAS_PATH alone would do nothing.
        assert "TRITON_PTXAS-BLACKWELL_PATH" in notes[0]

    def test_an_environment_without_triton_says_nothing(self):
        assert S._check_triton_targets_this_gpu({"device_sm": self.SM}) == []

    def test_no_gpu_means_no_opinion(self):
        assert (
            S._check_triton_targets_this_gpu(
                {"triton": "3.3.1", "triton_llvm": ["sm_90"], "triton_ptxas": {}}
            )
            == []
        )


class TestDriverFloor:
    """The driver floor is a property of the pin, so the manifest declares it.

    It used to be the constant 580 with a message asserting "the pinned stack is
    CUDA 13.0". That sentence was false for seven of eleven providers -- cu128
    stacks run on the 570 series -- so a host that could run three of them would
    have been refused by a claim about a CUDA version they do not pin.
    """

    def _toml(self, extra):
        return (
            '[provider]\nslug = "x"\n\n[runtime]\nmode = "resident"\n\n'
            '[env]\npython = "python3"\n\n[gpu]\npolicy = "required"\n'
            "vram_budget_gb = 1.0\n" + extra
        )

    def test_a_declared_floor_needs_its_reason(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(self._toml("driver_min = 570\n"))
        with pytest.raises(M.ManifestError, match="driver_min_reason"):
            M.load(p)

    def test_a_declared_floor_with_a_reason_loads(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(
            self._toml(
                "driver_min = 570\n"
                'driver_min_reason = "its pinned stack is CUDA 12.8"\n'
            )
        )
        m = M.load(p)
        assert m.driver_min == 570.0 and "12.8" in m.driver_min_reason

    def test_no_floor_is_allowed_and_means_report_not_judge(self, tmp_path):
        p = tmp_path / "provider.toml"
        p.write_text(self._toml(""))
        assert M.load(p).driver_min is None

    def test_every_verified_gpu_provider_declares_one(self):
        """Scoped to `verified`, the way outputs and verified_on are.

        A provider still being written has not decided its floor yet, and a
        half-built manifest in the tree must not redden the suite -- that is
        what an in-progress rollout looks like. Claiming `verified` is where
        the obligation attaches.
        """
        import glob
        import os

        undeclared = []
        for f in sorted(glob.glob("src/tooluniverse/remote/*/provider.toml")):
            try:
                m = M.load(f)
            except M.ManifestError:
                # A provider mid-write -- its worker file not yet on disk, say.
                # During a parallel rollout the tree always holds a few, and a
                # test that globs every manifest must tolerate that or it
                # reddens on somebody else's half-finished work. Whether a
                # manifest loads at all is the loader's own business and has
                # its own tests; this one is about a policy on verified
                # providers.
                continue
            if (
                m.status == "verified"
                and m.gpu_policy == "required"
                and m.driver_min is None
            ):
                undeclared.append(os.path.basename(os.path.dirname(f)))
        assert undeclared == [], (
            f"these verified GPU providers declare no driver floor: {undeclared}"
        )


class TestTritonCompileProbe:
    """The measured answer, which the string reads only approximate.

    atlasfold passed every static read this layer can make and still aborted,
    because cuEquivariance ships Triton kernels of its own and nothing in
    Triton's own target list predicts a second consumer's.
    """

    def test_the_probe_program_defines_its_kernel_as_a_quoted_literal(self):
        """The first version inlined it unquoted and the child died on syntax.

        That produced the right verdict for the wrong reason, which is the
        failure mode a probe must not have.
        """
        prog = S._TRITON_COMPILE_PROBE
        assert "SRC = " + repr(S._REDUCE_SRC) in prog
        compile(prog, "<probe>", "exec")  # the program itself must parse

    def test_the_kernel_reduces_across_lanes(self):
        """tl.sum is the construct that emits the warp shuffle under test."""
        assert "tl.sum" in S._REDUCE_SRC
        compile(S._REDUCE_SRC, "<kernel>", "exec")

    def test_the_kernel_runs_as_a_file_not_as_dash_c(self):
        """@triton.jit reads its own body with inspect.getsource."""
        assert "tempfile.mkdtemp" in S._TRITON_COMPILE_PROBE
        assert "subprocess.run([sys.executable, f]" in S._TRITON_COMPILE_PROBE

    def test_a_stack_without_triton_is_skipped_rather_than_failed(self):
        assert "'skipped': 'no triton'" in S._TRITON_COMPILE_PROBE


class TestOrderedInstallPasses:
    """A lock may declare ordered pip passes, because pip ignores file order.

    protenix_v1's lock carries both the CUDA 12.9 and 13.0 runtimes and 27
    paths under nvidia/{cudnn,nccl,cusparselt} collide between them. One pip
    pass installs whichever of a colliding pair it reaches last, so the result
    imports fine and is simply not the stack that was measured -- the kind of
    wrong a smoke cannot see. The kit's own Dockerfile needs two passes.
    """

    @staticmethod
    def _batches(text, slug="x"):
        """What step_environment would install, in order, without running pip."""
        groups = [[]]
        for ln in text.splitlines():
            if ln.strip().startswith("#"):
                if "pass break" in ln:
                    groups.append([])
                continue
            if ln.strip():
                groups[-1].append(ln)
        pins = [ln for g in groups for ln in g]
        boot = [ln for ln in pins if ln.split("==")[0] in ("pip", "wheel")]
        passes = [g for g in ([x for x in g if x not in boot] for g in groups) if g]
        return boot, passes

    def test_a_lock_without_markers_is_one_pass(self):
        boot, passes = self._batches("pip==1.0\na==1\nb==2\n")
        assert boot == ["pip==1.0"]
        assert passes == [["a==1", "b==2"]]

    def test_a_marker_splits_the_install_in_file_order(self):
        boot, passes = self._batches(
            "pip==1.0\nnvidia-cudnn-cu12==9.10\n"
            "# --- pass break ---\n"
            "nvidia-cudnn-cu13==9.20\ntorch==2.13.0\n"
        )
        assert boot == ["pip==1.0"]
        # Order is the lock's: the CUDA 13 pass must come second so its files win.
        assert passes == [
            ["nvidia-cudnn-cu12==9.10"],
            ["nvidia-cudnn-cu13==9.20", "torch==2.13.0"],
        ]

    def test_ordinary_comments_are_not_markers(self):
        _, passes = self._batches("a==1\n# just a comment\nb==2\n")
        assert passes == [["a==1", "b==2"]]

    def test_every_shipped_lock_still_parses_to_at_least_one_pass(self):
        import glob

        for f in sorted(glob.glob("src/tooluniverse/remote/*/environment/*.lock")):
            _, passes = self._batches(Path(f).read_text())
            assert passes, f"{f} parsed to no installable pass"


class TestArchCheckAcrossFrameworks:
    """A provider's accelerator is not always torch's.

    af3_jax pins a CPU-only torch because its weights converter is a torch
    script, and `_arch_problem` refused it with `torch reports no usable GPU`
    while jax reported a CudaDevice and drove the card. That was the third false
    refusal this layer has produced from one framework's assumptions.
    """

    def test_a_working_torch_is_still_judged_by_torch(self):
        assert (
            S._arch_problem(
                {
                    "torch": "2.13.0+cu130",
                    "arch_list": ["sm_90", "sm_120"],
                    "device_sm": "sm_121",
                },
                True,
            )
            is None
        )

    def test_a_torch_that_cannot_reach_the_card_is_still_refused(self):
        problem = S._arch_problem(
            {"torch": "2.6.0", "arch_list": ["sm_80", "sm_90"], "device_sm": "sm_121"},
            True,
        )
        assert problem and "sm_121" in problem

    def test_a_cpu_only_torch_beside_a_gpu_jax_is_not_refused(self):
        """The af3_jax case: torch is incidental, jax holds the card."""
        assert (
            S._arch_problem(
                {
                    "torch": "2.7.1+cpu",
                    "arch_list": [],
                    "jax": "0.10.2",
                    "jax_backend": "gpu",
                    "jax_device": "cuda:0",
                },
                True,
            )
            is None
        )

    def test_a_cpu_only_torch_with_no_other_framework_is_still_refused(self):
        problem = S._arch_problem({"torch": "2.7.1+cpu", "arch_list": []}, True)
        assert problem and "no usable GPU" in problem

    def test_a_cpu_jax_does_not_rescue_a_cpu_torch(self):
        """A jax that fell back to the CPU backend is not an accelerator."""
        problem = S._arch_problem(
            {"torch": "2.7.1+cpu", "arch_list": [], "jax_backend": "cpu"}, True
        )
        assert problem and "no usable GPU" in problem

    def test_the_probe_asks_jax_too(self):
        prog = S._ARCH_PROBE
        assert "jax_backend" in prog and "local_devices" in prog
        compile(prog, "<probe>", "exec")


class TestRefusalsExitThree:
    """STANDARD section 8: `0` ok, `1` failed, `2` usage, `3` refused.

    `raise SystemExit("message")` prints the message and exits **1**, so every
    worker that refused that way was reporting a crash. These tests hold the
    corrected contract across all of them at once, by reading the source rather
    than by starting eighteen model environments.
    """

    @staticmethod
    def _workers():
        root = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "remote"
        found = sorted(root.glob("*/resident/*_resident_worker.py"))
        assert found, root
        return found

    def test_no_worker_refuses_with_a_bare_message(self):
        """A string argument to SystemExit is an exit-1 refusal, which is wrong.

        `raise SystemExit(WB.serve(...))` is fine -- it passes the server's own
        return code through -- and so is an explicit integer.
        """
        import ast

        offenders = []
        for path in self._workers():
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                    continue
                func = node.exc.func
                name = getattr(func, "id", getattr(func, "attr", None))
                if name != "SystemExit" or not node.exc.args:
                    continue
                arg = node.exc.args[0]
                if isinstance(arg, ast.Call):
                    continue
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                    continue
                offenders.append(f"{path.name}:{node.lineno}")
        assert not offenders, (
            "these refusals exit 1, which the standard reserves for "
            f'"failed"; raise _refuse(...) instead: {offenders}'
        )

    def test_every_worker_that_refuses_has_the_helper(self):
        for path in self._workers():
            src = path.read_text()
            if "raise _refuse(" not in src:
                continue
            assert "def _refuse(" in src, path
            assert "return SystemExit(3)" in src, path
            assert "import sys" in src, path

    def test_the_helper_exits_three_and_writes_the_message(self, capsys):
        namespace: dict = {"sys": sys}
        src = (self._workers()[0]).read_text()
        start = src.index("def _refuse(")
        end = src.index("return SystemExit(3)", start) + len("return SystemExit(3)")
        exec(compile(src[start:end], "<helper>", "exec"), namespace)
        exc = namespace["_refuse"]("nope: do the thing")
        assert isinstance(exc, SystemExit) and exc.code == 3
        assert "nope: do the thing" in capsys.readouterr().err

    def test_the_supervisor_names_a_refusal(self):
        """A refusal and a crash must not read the same.

        This asked for the literal `rc == 3` until the sentences moved into
        `EXIT_HINTS`, which is where a second named code (5, an expected
        accelerator absent) could be added without writing a second branch.
        What it was protecting is the distinction, so that is what it reads
        now -- and a distinction survives a refactor where a spelling does not.
        """
        import inspect

        from tooluniverse.remote_resident import supervisor

        assert "refusal" in exit_hint(3)
        assert exit_hint(1) == "", "an unnamed code must not read as a refusal"
        assert "exited {rc} before it bound" in inspect.getsource(supervisor)


class TestLauncherCanRemoveAVariable:
    """`build_command` maps a name to None to REMOVE it from the child.

    The supervisor builds the child's environment from `os.environ` and then
    applies the launcher's mapping, so a launcher cannot remove a name by
    returning a pruned copy: the pruned name comes back from `os.environ`.
    af3_jax's launcher did exactly that and its stripping silently did nothing
    -- an exported `AF3_JAX_BOGUS` made the worker exit 3 at
    `import alphafold3`, which is the failure the stripping existed to prevent.
    It passed review because the check read `build_command`'s RETURN VALUE,
    which is the one place the defect is invisible.
    """

    def test_a_none_value_removes_the_name(self):
        from tooluniverse.remote_resident.supervisor import child_env

        env = child_env({"KEEP": "1", "DROP": None}, {"DROP": "stray", "PATH": "/x"})
        assert "DROP" not in env
        assert env["KEEP"] == "1"
        assert env["PATH"] == "/x"

    def test_a_set_value_still_overrides(self):
        from tooluniverse.remote_resident.supervisor import child_env

        assert child_env({"MODE": "off"}, {"MODE": "fast"})["MODE"] == "off"

    def test_removing_a_name_that_is_not_set_is_not_an_error(self):
        from tooluniverse.remote_resident.supervisor import child_env

        assert "ABSENT" not in child_env({"ABSENT": None}, {"PATH": "/x"})

    def test_the_supervisor_uses_it(self):
        """Not a reimplementation: _start must call the function under test."""
        import inspect

        from tooluniverse.remote_resident import supervisor

        src = inspect.getsource(supervisor.ResidentWorker._start)
        assert "child_env(extra_env, os.environ)" in src

    def test_no_provider_launch_prunes_a_copy_of_the_environment(self):
        """The invariant, across every provider-local launcher.

        af3_jax was fixed when the defect was found; esm_if1, af3_torch and
        ef2inv had the same code and were not, because nothing looked. All four
        wrote `popen_env = dict(os.environ)` and then popped names out of it,
        which removes nothing: the supervisor rebuilds the child's environment
        from `os.environ` and applies the mapping over it. Proved on esm_if1 by
        exporting `ESM_IF1_OPT=off` against a manifest whose mode is `fast` and
        watching the worker exit 3 -- the exact refusal the strip existed to
        prevent -- and then watching it start once the launcher returned
        removals instead.
        """
        root = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "remote"
        offenders = []
        for path in sorted(root.glob("*/launch.py")):
            src = path.read_text()
            if "dict(os.environ)" not in src:
                continue
            # A copy is fine as long as nothing is removed from it; the defect is
            # the removal, which the supervisor cannot see.
            if ".pop(" in src or "del popen_env[" in src:
                offenders.append(path.parent.name)
        assert not offenders, (
            "these launchers remove names from a copy of os.environ, which "
            "removes nothing -- map the name to None instead: " + ", ".join(offenders)
        )


class TestManifestAndDeploymentAgree:
    """A manifest's `[env] python` variable must be in its `required_env`.

    Two sources of truth describe the same provider: the manifest, which the
    setup steps read, and the deployment table, which `tu remote check` and the
    preflight read. Nothing held them together, and boltz and enformer -- the
    two oldest resident providers -- declared
    `[env] python = "$TOOLUNIVERSE_<SLUG>_PYTHON"` while their `required_env`
    was empty. The consequence was quiet rather than loud: `tu remote check`
    could not know there was a model environment to look at, so it probed the
    SERVER's interpreter and printed a GPU verdict about the wrong process, and
    `--check-provider-env` never told an operator the variable was unset.
    """

    @staticmethod
    def _verified():
        from tooluniverse.remote_resident import manifest as M

        root = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "remote"
        for path in sorted(root.glob("*/provider.toml")):
            try:
                m = M.load(path)
            except Exception:
                continue
            if m.status == "verified":
                yield path.parent.name, path, m

    def test_every_interpreter_variable_is_declared(self):
        import re

        from tooluniverse.remote_runtime import REMOTE_DEPLOYMENTS

        by_slug = {d.slug: d for d in REMOTE_DEPLOYMENTS}
        problems = []
        for slug, path, _manifest in self._verified():
            wanted = set(
                re.findall(r'^python = "\$([A-Z0-9_]+)"', path.read_text(), re.M)
            )
            deployment = by_slug.get(slug)
            if deployment is None:
                problems.append(f"{slug}: verified but absent from REMOTE_DEPLOYMENTS")
                continue
            missing = wanted - set(deployment.required_env)
            if missing:
                problems.append(
                    f"{slug}: manifest's [env] python needs {sorted(missing)}, "
                    f"required_env is {deployment.required_env}"
                )
        assert not problems, "\n".join(problems)

    def test_the_preflight_catalog_declares_them_too(self):
        from scripts.remote_validation.setup_skill_preflight import DEPLOYMENTS
        from tooluniverse.remote_runtime import REMOTE_DEPLOYMENTS

        runtime = {d.slug: set(d.required_env) for d in REMOTE_DEPLOYMENTS}
        catalog = {d.slug: set(d.required_env) for d in DEPLOYMENTS}
        assert catalog == runtime, (
            "the preflight catalog and the runtime table must require the same "
            "variables; an operator preflights against one and runs against the "
            "other"
        )


class TestAcceptanceHarness:
    """`scripts/remote_validation/verify_provider.py` and its input shapers.

    The harness implements the acceptance test the standard describes, and
    until now it lived only in a session scratchpad -- so the standard's
    central method had no implementation anyone else could run. The shapers
    are the part that rots: one of them truncated PDB ATOM records at column
    54 and biotite raised `could not convert string to float: ''` on a record
    with no occupancy field, which is a bug in the test fixture that looks
    exactly like a bug in the provider.
    """

    @staticmethod
    def _harness():
        import importlib.util

        path = (
            Path(__file__).resolve().parents[2]
            / "scripts/remote_validation/verify_provider.py"
        )
        spec = importlib.util.spec_from_file_location("_verify_provider", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_it_imports_without_a_hardcoded_path(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "scripts/remote_validation/verify_provider.py"
        ).read_text()
        assert "/home/" not in source, "a path from one machine's scratchpad"
        assert self._harness().SHAPERS

    def test_every_shaper_resizes_its_provider_s_own_smoke_input(self):
        from tooluniverse.remote_resident import manifest as M

        harness = self._harness()
        root = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "remote"
        problems = []
        for slug, shaper in sorted(harness.SHAPERS.items()):
            tom = root / slug / "provider.toml"
            if not tom.is_file():
                continue
            try:
                manifest = M.load(tom)
            except Exception:
                continue  # a provider still being built
            smoke = root / slug / manifest.smoke if manifest.smoke else None
            if smoke is None or not smoke.is_file():
                problems.append(f"{slug}: no smoke input to resize")
                continue
            text = smoke.read_text()
            # A LADDER OF CANDIDATES, not a fixed pair. The first version of this
            # test asked for 60 and 240 and failed mosaic, whose input is a
            # target plus a binder of fixed length: at 60 there is no target
            # left, and refusing is the shaper doing its job rather than
            # failing. A provider's size axis has a floor and the floor differs,
            # so probe a range and require two distinct results from it.
            made, raised = {}, {}
            for n in (60, 100, 200, 240, 400, 800):
                try:
                    out = shaper(text, n)
                except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                    raised[n] = f"{type(exc).__name__}: {exc}"
                    continue
                if out:
                    made[n] = out
            if len(made) < 2:
                problems.append(
                    f"{slug}: fewer than two of six sizes produced an input; "
                    f"refusals were {raised}"
                )
            elif len(set(made.values())) < 2:
                problems.append(
                    f"{slug}: every size that worked produced the SAME input "
                    f"({sorted(made)}), so the ladder would measure one shape"
                )
        assert not problems, "\n".join(problems)

    def test_a_provider_with_no_shaper_is_not_silently_passed(self):
        """Exit 2, not 0, so nobody reads 4/4 as an acceptance."""
        source = (
            Path(__file__).resolve().parents[2]
            / "scripts/remote_validation/verify_provider.py"
        ).read_text()
        assert "NO SHAPER FOR" in source
        assert "return 2" in source


class TestKitProbeRunsWithoutStrayVariables:
    """`ask_kit`'s probe must not inherit the operator's undeclared kit names.

    Most kits' `.pth` kills any interpreter that inherits an undeclared
    `<PACKAGE>_*` name. A provider's launcher strips those from the WORKER by
    mapping them to None, but the supervisor applies that mapping to the command
    `kit_launch.build_command` helps build -- and `ask_kit` runs a probe INSIDE
    that call, before the command exists. So the probe inherited them and died,
    which surfaced as `KitUnavailable: could not read opendde_opt's mode row`
    carrying the kit's own `NOT ACTIVE: reason=undeclared variable(s)`.

    Found by running the ceiling test opendde's bring-up had listed as untested,
    with two hostile names exported. The function's own docstring already had
    the principle -- the probe must run under the conditions the worker will --
    applied to one variable only.
    """

    @staticmethod
    def _probe_env(package, environ):
        """What `ask_kit` hands the probe, without running a subprocess.

        `None` is a real and correct answer: it means "inherit", which is what
        `ask_kit` passes when there is nothing to strip and no ablation to set.
        """
        import inspect
        import re as _re

        from tooluniverse.remote_resident import kit_launch

        src = inspect.getsource(kit_launch.ask_kit)
        body = src[src.index("declared = package.upper()") :]
        body = body[: body.index("proc = subprocess.run")]
        scope = {
            "package": package,
            "env": None,
            "levers_off": (),
            "os": type("os", (), {"environ": dict(environ)}),
        }
        exec(_re.sub(r"^    ", "", body, flags=_re.M), scope)
        return scope["env"]

    def test_the_undeclared_names_are_removed(self):
        env = self._probe_env(
            "opendde_opt",
            {
                "OPENDDE_OPT": "off",
                "OPENDDE_OPT_BOGUS": "1",
                "OPENDDE_OPT_X": "stray",
                "PATH": "/usr/bin",
            },
        )
        assert env is not None, "a strip was needed, so the probe needs its own env"
        assert "OPENDDE_OPT_BOGUS" not in env
        assert "OPENDDE_OPT_X" not in env

    def test_the_declared_name_survives_the_strip(self):
        """The probe exists to read the row that name selects."""
        env = self._probe_env(
            "opendde_opt", {"OPENDDE_OPT": "off", "OPENDDE_OPT_X": "stray"}
        )
        assert env["OPENDDE_OPT"] == "off"

    def test_nothing_to_strip_means_inherit(self):
        """`None` here is deliberate: do not copy an environment for no reason."""
        assert (
            self._probe_env("opendde_opt", {"OPENDDE_OPT": "off", "PATH": "/usr/bin"})
            is None
        )

    def test_an_unrelated_name_is_untouched_when_a_strip_happens(self):
        env = self._probe_env(
            "opendde_opt",
            {"OPENDDE_OPT_X": "stray", "OPENDDE_ROOT_DIR": "/w", "HF_HOME": "/h"},
        )
        assert env["OPENDDE_ROOT_DIR"] == "/w"
        assert env["HF_HOME"] == "/h"

    def test_ask_kit_still_sets_levers_off_in_the_probe(self):
        """The behaviour the docstring was written for must survive the fix."""
        import inspect

        from tooluniverse.remote_resident import kit_launch

        src = inspect.getsource(kit_launch.ask_kit)
        assert 'env["MODEL_OPT_LEVERS_OFF"]' in src
        assert "declared = package.upper()" in src


class TestAdmission:
    """The decision the budgets exist for, which nothing made until now.

    Every case here is a reading this project actually took. The first is the
    one that wedged the host: four providers held, about 12 GiB of RSS between
    them, a 28 GiB smoke started on top, and five more workers on the card from
    a checkout this process could not see.
    """

    CAP = (121.6, "/proc/meminfo MemTotal (unified memory)")
    QUIET = {"MemTotal": 121.6, "MemFree": 100.0, "MemAvailable": 110.0}
    WEDGE = {"MemTotal": 121.6, "MemFree": 5.0, "MemAvailable": 60.4}

    def _decide(self, **kw):
        from tooluniverse.remote_resident import admission

        kw.setdefault("capacity", self.CAP)
        kw.setdefault("mem", self.QUIET)
        kw.setdefault("co_tenants", 0)
        return admission.decide(**kw)

    def test_the_wedge_is_refused(self):
        """5 GiB free, 60.4 available, co-tenants: the OOM reading exactly."""
        v = self._decide(
            slug="ef2inv",
            budget_gb=28.0,
            held={"boltzgen": 11.9},
            mem=self.WEDGE,
            co_tenants=5,
        )
        assert not v
        assert v.gate == "MemFree", "with co-tenants the narrow reading must gate"
        assert "5.0 GiB free" in v.reason and "60.4 GiB available" in v.reason

    def test_the_gate_widens_when_nothing_competes(self):
        """Reclaim is only a race when there is someone to lose it to."""
        v = self._decide(slug="ef2inv", budget_gb=28.0, held={}, mem=self.WEDGE)
        assert v.gate == "MemAvailable"

    def test_a_full_pool_is_refused_on_the_declared_sum_alone(self):
        """The machine looks idle; the budgets say it is not. Both gates matter."""
        v = self._decide(
            slug="opendde",
            budget_gb=22.55,
            held={
                "esmfold2": 25.28,
                "ef2inv": 28.0,
                "complexa": 20.25,
                "colabdesign": 12.0,
                "evo2": 18.0,
            },
        )
        assert not v
        assert "103.53 GiB is already declared held" in v.reason
        assert v.available_gib == 110.0, "refused with the machine looking empty"

    def test_an_undeclared_held_budget_is_not_treated_as_zero(self):
        v = self._decide(
            slug="opendde", budget_gb=22.55, held={"mystery": None, "boltz": 5.54}
        )
        assert not v
        assert v.unknown_budgets == ("mystery",)
        assert "would be a guess" in v.reason

    def test_a_provider_without_a_budget_is_never_admitted(self):
        v = self._decide(slug="newthing", budget_gb=None, held={})
        assert not v
        assert "declares no vram_budget_gb" in v.reason

    def test_restarting_what_is_held_frees_its_own_budget(self):
        """Otherwise a worker could never be restarted while the pool is tight."""
        v = self._decide(
            slug="complexa", budget_gb=20.25, held={"complexa": 20.25, "boltz": 5.54}
        )
        assert v
        assert v.declared_held_gb == 5.54

    def test_an_unknown_capacity_refuses_rather_than_assuming(self):
        v = self._decide(
            slug="boltz",
            budget_gb=5.54,
            held={},
            capacity=(None, "nvidia-smi did not run"),
        )
        assert not v
        assert "could not be established" in v.reason

    def test_unified_memory_is_read_as_a_capacity_not_an_error(self, monkeypatch):
        """`[N/A]` is the unified-memory answer, so MemTotal is the pool.

        This asserted the live host instead of the code path, and so it only
        held on a machine with unified memory and a driver: CI has no
        `nvidia-smi` at all, took the OSError branch, and read the None that
        branch is supposed to return as a bug in the branch above it. Fake the
        three answers and all three are checked anywhere.
        """
        import subprocess as sp

        from tooluniverse.remote_resident import admission

        def answering(value):
            def run(*_args, **_kwargs):
                return sp.CompletedProcess([], 0, value, "")

            return run

        # Unified memory: no device total of its own, so the pool is MemTotal.
        monkeypatch.setattr(admission.subprocess, "run", answering("[N/A]\n"))
        cap, source = admission.capacity_gib()
        assert cap is not None and cap > 1.0
        assert "MemTotal" in source

        # A discrete card does have one, and MemTotal is not the ceiling then.
        monkeypatch.setattr(admission.subprocess, "run", answering("81920\n"))
        cap, source = admission.capacity_gib()
        assert cap == pytest.approx(80.0)
        assert "memory.total" in source

        # No driver at all is neither of those, and must not become a number.
        def missing(*_args, **_kwargs):
            raise FileNotFoundError("nvidia-smi")

        monkeypatch.setattr(admission.subprocess, "run", missing)
        cap, source = admission.capacity_gib()
        assert cap is None
        assert "nvidia-smi did not run" in source

    def test_the_reason_always_carries_the_numbers(self):
        """Section 8: a refusal names what happened, not that something did."""
        import re

        for kw in (
            dict(
                slug="a", budget_gb=28.0, held={"b": 11.9}, mem=self.WEDGE, co_tenants=5
            ),
            dict(slug="a", budget_gb=130.0, held={}),
            dict(slug="a", budget_gb=None, held={}),
        ):
            v = self._decide(**kw)
            assert not v
            assert v.reason.strip()
            # A refusal quotes the figures it decided on -- except the one about
            # a figure that does not exist, which has to name the field instead.
            assert re.search(r"\d", v.reason) or "vram_budget_gb" in v.reason, v.reason

    def test_raise_if_refused_carries_the_same_message(self):
        from tooluniverse.remote_resident.admission import AdmissionRefused

        v = self._decide(slug="a", budget_gb=130.0, held={})
        try:
            v.raise_if_refused()
        except AdmissionRefused as exc:
            assert str(exc) == v.reason
        else:
            raise AssertionError("a refused verdict must raise")
        assert self._decide(slug="a", budget_gb=1.0, held={}).raise_if_refused()


class TestAdmissionIsWiredToTheStartPath:
    """A decision nothing consults is what this replaced, so check the wiring.

    `backend.running()`'s docstring said a scheduler above it reads the budgets,
    and for twenty-seven providers nothing did. A verdict function with no caller
    would have been the same gap one layer up.
    """

    def _worker(self, budget, monkeypatch, verdict_admits):
        from tooluniverse.remote_resident import admission, supervisor

        started = []

        def fake_decide(slug, budget_gb, held=None, **kw):
            return admission.Verdict(
                admit=verdict_admits,
                reason=f"stub verdict for {slug} at {budget_gb}",
                slug=slug,
                budget_gb=budget_gb,
            )

        monkeypatch.setattr(admission, "decide", fake_decide)
        monkeypatch.setattr(
            admission, "room_for", lambda slug, b, **kw: fake_decide(slug, b)
        )
        w = supervisor.ResidentWorker(
            slug="probe",
            build_command=lambda _w: (["/bin/true"], {}),
            vram_budget_gb=budget,
        )
        monkeypatch.setattr(w, "_start", lambda: started.append(True))
        return w, started

    def test_a_refusal_stops_the_start(self, monkeypatch):
        from tooluniverse.remote_resident.admission import AdmissionRefused

        w, started = self._worker(22.55, monkeypatch, verdict_admits=False)
        with pytest.raises(AdmissionRefused):
            w.ensure_started()
        assert not started, "the worker was started despite a refusal"

    def test_an_admission_lets_it_through(self, monkeypatch):
        w, started = self._worker(22.55, monkeypatch, verdict_admits=True)
        w.ensure_started()
        assert started == [True]

    def test_a_cpu_provider_is_not_asked(self, monkeypatch):
        """esm_if1's case: policy "none", no budget, nothing spent from the pool."""
        w, started = self._worker(None, monkeypatch, verdict_admits=False)
        w.ensure_started()
        assert started == [True], "a provider with no budget must not need admission"

    def test_the_escape_hatch_is_an_attribute_not_a_variable(self, monkeypatch):
        """A host with its own scheduler owns the decision, and says so in code.

        An environment variable would be the exact class of mistake the
        launchers in this package are full of.
        """
        w, started = self._worker(22.55, monkeypatch, verdict_admits=False)
        w.admit = False
        w.ensure_started()
        assert started == [True]

    def test_a_real_manifest_declares_what_admission_needs(self):
        """Every GPU resident provider on disk can be decided about."""
        import glob

        from tooluniverse.remote_resident import admission, manifest as M

        undecidable = []
        for path in sorted(glob.glob("src/tooluniverse/remote/*/provider.toml")):
            try:
                m = M.load(path)
            except Exception:  # noqa: BLE001 - a broken manifest is another test's
                continue
            if m.gpu_policy == "none" or m.mode != "resident":
                continue
            v = admission.decide(
                m.slug,
                m.vram_budget_gb,
                {},
                capacity=(121.6, "test"),
                mem={"MemTotal": 121.6, "MemFree": 110.0, "MemAvailable": 115.0},
                co_tenants=0,
            )
            if not v.admit:
                undecidable.append((m.slug, v.reason[:70]))
        assert not undecidable, (
            f"these providers cannot be admitted on an empty machine: {undecidable}"
        )


class TestRemoteRoomCommand:
    """`tu remote room` answers "what fits right now", which `list` cannot.

    `list` prints what a provider costs. Whether the machine can carry it is a
    different question with a different answer every few minutes, and it is the
    one an operator has before starting anything.
    """

    def _run(self, *argv):
        """The command through the real argument parser, output captured."""
        import contextlib
        import io
        import sys as _sys

        from tooluniverse import cli

        out, err = io.StringIO(), io.StringIO()
        code = 0
        argv = ["tu", "remote", "room", *argv]
        old = _sys.argv
        try:
            _sys.argv = argv
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    cli.main()
                except SystemExit as exc:
                    code = exc.code or 0
        finally:
            _sys.argv = old
        return code, out.getvalue(), err.getvalue()

    def test_it_lists_every_gpu_resident_provider_with_a_verdict(self):
        code, out, _ = self._run()
        assert code == 0
        assert "declared held by" in out, "the header must show what is held"
        lines = [ln for ln in out.splitlines() if " GiB   " in ln]
        assert len(lines) >= 20, f"only {len(lines)} providers judged"
        for ln in lines:
            assert ln.strip().startswith(("fits", "NO")), ln

    def test_the_unregistered_providers_are_included(self):
        """Registration is a later step than a manifest, and two are waiting.

        A provider you cannot ask about is one you will start without asking.
        """
        _, out, _ = self._run()
        for slug in ("opendde", "colabdesign"):
            assert slug in out, f"{slug} has a manifest and must be judged"

    def test_an_unknown_slug_exits_two_and_says_where_to_look(self):
        """main() drops a command's return value, so a refusal must sys.exit."""
        code, _, err = self._run("nosuch")
        assert code == 2, "a returned code would be a refusal nobody can detect"
        assert "tu remote list" in err

    def test_one_slug_prints_the_reason(self):
        code, out, _ = self._run("boltz")
        assert code == 0
        assert "boltz" in out
        assert "GiB" in out.splitlines()[-1] or "GiB" in out

    def test_json_carries_the_numbers_the_decision_used(self):
        code, out, _ = self._run("--json")
        assert code == 0
        doc = json.loads(out)
        for key in (
            "capacity_gib",
            "capacity_source",
            "declared_held_gb",
            "held",
            "mem_free_gib",
            "mem_available_gib",
            "processes_on_card",
            "reserve_gb",
            "providers",
        ):
            assert key in doc, f"{key} missing from the machine-readable form"
        assert doc["providers"], "no providers judged"
        assert {"slug", "fits", "reason", "vram_budget_gb", "status"} <= set(
            doc["providers"][0]
        )

    def test_a_bigger_reserve_can_only_narrow_what_fits(self):
        """The reserve is the host's room, so raising it never admits more."""

        small = json.loads(self._run("--json", "--reserve", "1")[1])
        large = json.loads(self._run("--json", "--reserve", "60")[1])
        fits_small = {r["slug"] for r in small["providers"] if r["fits"]}
        fits_large = {r["slug"] for r in large["providers"] if r["fits"]}
        assert fits_large <= fits_small, (
            f"a 60 GiB reserve admitted what a 1 GiB reserve did not: "
            f"{sorted(fits_large - fits_small)}"
        )


class TestMachineWideHoldings:
    """What the whole machine holds, which is the question that was being dodged.

    `backend.running()` sees this interpreter's workers. The ones that wedged
    this host belonged to another worktree of this same repository, and while
    these tests were written a `protenix_v1` worker from
    `worktrees/tnf-alpha-competition-20261008` was resident and invisible to it.
    """

    WORKER = (
        "/home/u/ws/tooluniverse/ToolUniverse/.venv/bin/python "
        "/home/u/ws/tooluniverse/ToolUniverse/src/tooluniverse/remote/{slug}/"
        "resident/{slug}_resident_worker.py --socket /run/user/1000/x.sock --slug {slug}"
    )
    FOREIGN = (
        "/home/u/ws/tooluniverse/worktrees/{tree}/.venv/bin/python "
        "/home/u/ws/tooluniverse/worktrees/{tree}/src/tooluniverse/remote/{slug}/"
        "resident/{slug}_resident_worker.py --socket /run/user/1000/x.sock --slug {slug}"
    )

    def _holdings(self, *lines, budgets=None):
        from tooluniverse.remote_resident import admission

        budgets = budgets or {}
        return admission.machine_holdings(
            ps_output="\n".join(lines), budget_of=lambda s: budgets.get(s)
        )

    def test_a_worker_in_this_tree_is_keyed_by_slug(self):
        held = self._holdings(self.WORKER.format(slug="boltz"), budgets={"boltz": 5.54})
        assert held == {"boltz": 5.54}

    def test_a_worker_in_another_worktree_names_the_tree(self):
        """Naming the tree was the guard script's lesson: not knowing was the mistake."""
        held = self._holdings(
            self.FOREIGN.format(slug="protenix_v1", tree="tnf_alpha"),
            budgets={"protenix_v1": 9.65},
        )
        assert held == {"protenix_v1@tnf_alpha": 9.65}

    def test_two_processes_of_one_slug_are_two_holders(self):
        """The second process is what turned 12 GiB into a wedged host."""
        held = self._holdings(
            self.FOREIGN.format(slug="boltzgen", tree="comp_a"),
            self.FOREIGN.format(slug="boltzgen", tree="comp_a"),
            budgets={"boltzgen": 7.89},
        )
        assert len(held) == 2, f"collapsed to {held}"
        assert sum(held.values()) == pytest.approx(15.78)

    def test_a_shell_quoting_a_worker_path_is_not_a_worker(self):
        """The first run of this scan reported a holder called `<slug>`.

        It was matched out of the `bash -c` that was writing the scan, whose
        comment carried the path template. Requiring a token with `/resident/`
        does not exclude it, because the template has one.
        """
        held = self._holdings(
            "/bin/bash -c echo .../remote/<slug>/resident/<slug>_resident_worker.py --socket x",
            budgets={},
        )
        assert held == {}

    def test_a_glob_or_template_slug_is_rejected_by_shape(self):
        for bogus in ("<slug>", "*", "SLUG", "$slug", ""):
            held = self._holdings(self.WORKER.format(slug=bogus))
            assert held == {}, f"{bogus!r} was accepted as a provider"

    def test_a_worker_whose_checkout_was_deleted_still_counts(self):
        """It is still holding the memory, so the file test cannot be existence."""
        held = self._holdings(
            self.FOREIGN.format(slug="esmfold2", tree="deleted_tree"),
            budgets={"esmfold2": 25.28},
        )
        assert held == {"esmfold2@deleted_tree": 25.28}

    def test_an_unknown_slug_is_none_not_zero(self):
        """A provider this checkout does not have is uncosted, not free."""
        held = self._holdings(self.WORKER.format(slug="somethingelse"), budgets={})
        assert held == {"somethingelse": None}

    def test_room_for_releases_only_its_own_trees_budget(self):
        """Restarting mine frees mine; another tree's worker is still holding."""
        from tooluniverse.remote_resident import admission

        ps = "\n".join(
            [
                self.WORKER.format(slug="boltz"),
                self.FOREIGN.format(slug="boltz", tree="other"),
            ]
        )
        held = admission.machine_holdings(ps_output=ps, budget_of=lambda s: 5.54)
        held.pop("boltz", None)  # what room_for does
        assert held == {"boltz@other": 5.54}, (
            "a restart must not release another checkout's budget"
        )

    def test_the_live_machine_is_readable(self):
        """Not what it returns -- that changes -- but that it answers in shape."""
        from tooluniverse.remote_resident import admission

        held = admission.machine_holdings()
        assert isinstance(held, dict)
        for key, value in held.items():
            assert admission.SLUG_RE.match(key.split("@")[0].split("#")[0]), key
            assert value is None or isinstance(value, float)


class TestTheCliAndTheGateAgree:
    """One question, one answer. Two code paths reading different holdings would
    tell an operator a provider fits and then refuse to start it, which is worse
    than either answer alone being wrong. The first version of `tu remote room`
    did exactly that: it read `backend.running()`, which in a fresh CLI process
    is always empty, while the gate read the process table.
    """

    def test_both_paths_read_the_same_holdings_function(self, monkeypatch):
        """Behavioural, not a grep: an earlier version of this test asserted the
        string "backend.running()" was absent from the source and failed on the
        comment explaining why it is not called. Patch the function and see who
        picks the patch up.
        """
        import json

        from tooluniverse.remote_resident import admission

        calls = []

        def fake_holdings(**kw):
            calls.append(True)
            return {"ghost@elsewhere": 100.0}

        monkeypatch.setattr(admission, "machine_holdings", fake_holdings)
        # The pool has to be pinned too. The arithmetic below is written against
        # a 121.6 GiB pool, and reading it off the live host made the test pass
        # only on the machine it was written on: CI has no `nvidia-smi`, so
        # capacity is None there and every refusal says so instead of naming the
        # holdings this test is about.
        monkeypatch.setattr(
            admission, "capacity_gib", lambda: (121.6, "pinned by the test")
        )

        doc = json.loads(_run_room("--json"))
        assert calls, "the command did not consult machine_holdings"
        assert doc["declared_held_gb"] == 100.0
        assert doc["held"] == {"ghost@elsewhere": 100.0}
        # The largest provider, because that one cannot fit under any reading:
        # 100 held + 38.63 + 4 reserved is past a 121.6 GiB pool. Asserting
        # that NOTHING fits would be wrong and was: with 100 GiB held, boltz's
        # 5.54 + 4 still leaves the sum under the pool, and it genuinely fits.
        biggest = max(doc["providers"], key=lambda r: r["vram_budget_gb"] or 0)
        assert not biggest["fits"], f"{biggest['slug']} fits with 100 GiB held"
        assert "already declared held" in biggest["reason"]

        before = len(calls)
        v = admission.room_for("boltz", 5.54)
        assert len(calls) > before, "the gate did not consult machine_holdings"
        # That the patched holdings reached the decision, not that boltz is
        # refused -- 100 held plus 5.54 plus 4 is still under a 121.6 pool, so
        # it fits, and asserting otherwise was arithmetic by intuition twice.
        assert v.declared_held_gb == 100.0

    def test_they_produce_the_same_verdict_for_the_same_provider(self):
        """The same logic over the same numbers, not two reads of a moving host.

        A first version called `admission.room_for` and then the CLI and
        asserted the two verdicts matched. They match on a quiet box and NOT on
        a busy one: each call reads `/proc/meminfo` at its own instant, and the
        first time this ran while another session was loading the machine the
        two readings straddled the reserve -- `MemFree` 1.8 GiB, a refusal on
        one side and an admission on the other. The test was right that the two
        should agree and wrong about what agreement means. So the CLI's OWN
        reported figures are fed back through `decide`, which compares the
        logic and cannot drift: if the CLI reaches a verdict its own numbers do
        not support, that is the defect this test is for.
        """
        import json

        from tooluniverse.remote_resident import admission

        doc = json.loads(_run_room("--json"))
        row = next(r for r in doc["providers"] if r["slug"] == "boltz")
        replayed = admission.decide(
            "boltz",
            row["vram_budget_gb"],
            {},
            reserve_gb=doc["reserve_gb"],
            mem={
                "MemFree": doc["mem_free_gib"],
                "MemAvailable": doc["mem_available_gib"],
            },
            capacity=(doc["capacity_gib"], doc["capacity_source"]),
            co_tenants=doc["processes_on_card"],
        )
        assert row["fits"] == replayed.admit, (
            f"the CLI said fits={row['fits']} where its own numbers give "
            f"{replayed.admit}: {replayed.reason}"
        )
        # and the holdings both sides read come from the process table, which is
        # the point of the pairing: a fresh CLI process has no backend state.
        held = admission.machine_holdings()
        assert doc["declared_held_gb"] == pytest.approx(
            round(sum(x for x in held.values() if x is not None), 2), abs=0.01
        )


def _run_room(*argv):
    import contextlib
    import io
    import sys as _sys

    from tooluniverse import cli

    out = io.StringIO()
    old = _sys.argv
    try:
        _sys.argv = ["tu", "remote", "room", *argv]
        with contextlib.redirect_stdout(out):
            try:
                cli.main()
            except SystemExit:
                pass
    finally:
        _sys.argv = old
    return out.getvalue()


class TestACpuProviderIsZeroNotUnknown:
    """`policy = "none"` holds no device memory, and the gate must know it.

    This class exists because the opposite shipped. `_declared_budget` returned
    the manifest's `vram_budget_gb` as-is, so a CPU provider -- whose manifest
    legally has none -- came back None, which the gate reads as "undeclared" and
    refuses to sum. A held proteinmpnn worker then refused every GPU provider on
    the host: `tu remote room boltz` printed `held: {"proteinmpnn": null}` and
    `proteinmpnn is already held without a declared budget, so what the card is
    carrying cannot be summed`. A CPU provider is the one thing that can safely
    be resident while the card is full, so that was exactly inverted.
    """

    def test_a_cpu_only_provider_declares_zero(self):
        from tooluniverse.remote_resident import admission

        # esm_if1 and proteinmpnn are the two `policy = "none"` providers; both
        # are read from their real manifests, so this fails if either grows a
        # budget without this rule being revisited.
        for slug in ("esm_if1", "proteinmpnn"):
            assert admission._declared_budget(slug) == 0.0, slug

    def test_a_gpu_provider_still_declares_its_budget(self):
        from tooluniverse.remote_resident import admission

        assert admission._declared_budget("boltz") == 5.54
        # and a slug with no manifest is still unknown rather than free
        assert admission._declared_budget("not-a-provider") is None

    def test_a_held_cpu_provider_does_not_block_a_gpu_one(self):
        from tooluniverse.remote_resident import admission

        v = admission.decide(
            "boltz",
            5.54,
            {"proteinmpnn": 0.0, "esm_if1": 0.0},
            mem={"MemFree": 60.0, "MemAvailable": 60.0},
            capacity=(121.6, "test"),
            co_tenants=0,
        )
        assert v.admit, v.reason
        assert v.declared_held_gb == 0.0
        assert "cannot be summed" not in v.reason

    def test_an_undeclared_budget_still_refuses(self):
        """The None path is the one being narrowed, not removed."""
        from tooluniverse.remote_resident import admission

        v = admission.decide(
            "boltz",
            5.54,
            {"mystery": None},
            mem={"MemFree": 60.0, "MemAvailable": 60.0},
            capacity=(121.6, "test"),
            co_tenants=0,
        )
        assert not v.admit
        assert "mystery" in v.reason


class TestApNovoFoldedStageLayout:
    """`apnovo_ingest_folded` writes what upstream's evaluator reads.

    This path cannot be exercised end to end here: it needs a real campaign,
    folded by a second provider, and the evaluation is a subprocess into a
    checkout that setup clones. So the filenames are pinned instead, against
    what `alphaprotein_novo/data/design_manifest.py` says at the commit
    `provider.toml` pins -- `folded_state_paths()` builds
    ``f"{sample}_{state}_folded_seed{n}.cif"`` and
    ``f"{sample}_{state}_confidences_seed{n}.json"``, and
    `find_state_confidences()` counts seeds up from 0 and stops at the first
    gap. A test that only said "it wrote some files" would not have caught
    the bug this operation exists because of.
    """

    @staticmethod
    def _worker_module():
        import importlib.util

        path = (
            Path(__file__).resolve().parents[2]
            / "src/tooluniverse/remote/apnovo/resident/apnovo_resident_worker.py"
        )
        spec = importlib.util.spec_from_file_location("_apnovo_worker_t", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _engine(mod):
        return mod.Engine.__new__(mod.Engine)

    def _campaign(self, tmp_path):
        run_dir = tmp_path / "campaign"
        (run_dir / "01_generation").mkdir(parents=True)
        (run_dir / "01_generation" / "kemp_0000.cif").write_text("data_kemp\n")
        return run_dir

    def test_filenames_are_upstreams(self, tmp_path):
        mod = self._worker_module()
        run_dir = self._campaign(tmp_path)
        out = self._engine(mod)._ingest_folded(
            {
                "run_dir": str(run_dir),
                "states": [
                    {
                        "sample_name": "kemp_0000",
                        "state": "apo",
                        "seed": 0,
                        "folded_cif": "data_folded\n",
                        "confidences": {"ptm": 0.81},
                        "designed_cif": "kemp_0000.cif",
                    }
                ],
            }
        )
        stage = run_dir / "03_folded"
        assert out["folded_dir"] == str(stage)
        assert (stage / "kemp_0000_apo_folded_seed0.cif").read_text() == "data_folded\n"
        conf = json.loads((stage / "kemp_0000_apo_confidences_seed0.json").read_text())
        # Only these two are load-bearing: `_load_metadata` reads `seed` and
        # `designed_cif` and nothing else from this file.
        assert conf["seed"] == 0
        assert conf["designed_cif"] == "kemp_0000.cif"
        # Everything else the predictor reported survives, because
        # `_load_confidences` turns each unrecognised key into a metric.
        assert conf["ptm"] == 0.81

    def test_the_designed_structure_is_reachable_from_the_folded_stage(self, tmp_path):
        """`designed_cif` resolves as `folded_dir / designed_cif`, not run root."""
        mod = self._worker_module()
        run_dir = self._campaign(tmp_path)
        self._engine(mod)._ingest_folded(
            {
                "run_dir": str(run_dir),
                "states": [
                    {
                        "sample_name": "kemp_0000",
                        "state": "apo",
                        "folded_cif": "x\n",
                        "designed_cif": "kemp_0000.cif",
                    }
                ],
            }
        )
        assert (run_dir / "03_folded" / "kemp_0000.cif").read_text() == "data_kemp\n"

    def test_a_named_design_that_is_not_there_is_reported(self, tmp_path):
        mod = self._worker_module()
        run_dir = self._campaign(tmp_path)
        out = self._engine(mod)._ingest_folded(
            {
                "run_dir": str(run_dir),
                "states": [
                    {
                        "sample_name": "kemp_0001",
                        "state": "apo",
                        "folded_cif": "x\n",
                        "designed_cif": "kemp_0001.cif",
                    }
                ],
            }
        )
        assert out["designed_cifs_missing"] == ["kemp_0001.cif"]

    def test_a_seed_gap_says_how_far_upstream_will_read(self, tmp_path):
        """Seeds 0 and 2: upstream stops at 1, so seed 2 is silently ignored."""
        mod = self._worker_module()
        run_dir = self._campaign(tmp_path)
        out = self._engine(mod)._ingest_folded(
            {
                "run_dir": str(run_dir),
                "states": [
                    {"sample_name": "k", "state": "apo", "seed": s, "folded_cif": "x\n"}
                    for s in (0, 2)
                ],
            }
        )
        assert len(out["seed_gaps"]) == 1
        assert "[0]" in out["seed_gaps"][0]
        assert out["n_states_written"] == 2

    def test_contiguous_seeds_raise_no_gap(self, tmp_path):
        mod = self._worker_module()
        run_dir = self._campaign(tmp_path)
        out = self._engine(mod)._ingest_folded(
            {
                "run_dir": str(run_dir),
                "states": [
                    {"sample_name": "k", "state": "apo", "seed": s, "folded_cif": "x\n"}
                    for s in (0, 1, 2)
                ],
            }
        )
        assert out["seed_gaps"] == []

    @pytest.mark.parametrize("bad", ["../escape", "a/b", ".hidden"])
    def test_a_name_that_becomes_a_path_is_refused(self, tmp_path, bad):
        mod = self._worker_module()
        run_dir = self._campaign(tmp_path)
        with pytest.raises(ValueError, match="refusing"):
            self._engine(mod)._ingest_folded(
                {
                    "run_dir": str(run_dir),
                    "states": [
                        {"sample_name": bad, "state": "apo", "folded_cif": "x\n"}
                    ],
                }
            )

    def test_evaluate_refuses_a_campaign_with_no_folded_stage(self, tmp_path):
        """And names the operation that fixes it, rather than only the licence."""
        mod = self._worker_module()
        run_dir = self._campaign(tmp_path)
        with pytest.raises(RuntimeError) as exc:
            self._engine(mod)._evaluate({"run_dir": str(run_dir)})
        assert "03_folded" in str(exc.value)
        assert "apnovo_ingest_folded" in str(exc.value)


class TestApNovoFixedInputShape:
    """A design above the model's fixed input shape is refused, actionably.

    `run_generator.parse_and_prepare_diffusion_input` passes `max_num_res=512`
    as a LITERAL at the commit `provider.toml` pins -- not from config, not
    from the manifest -- so there is no "bucket" a longer design moves up
    into. `motif_spec.create_designable_protein_features` raises, and its
    message says "Set max_num_res to a higher value", which names a knob that
    is reachable from neither a manifest nor the published operation. These
    tests pin the rewording, and pin that we did NOT paper over it by copying
    upstream's number into our own source, where it would drift the first time
    the pin moves.
    """

    @staticmethod
    def _worker_module():
        import importlib.util

        path = (
            Path(__file__).resolve().parents[2]
            / "src/tooluniverse/remote/apnovo/resident/apnovo_resident_worker.py"
        )
        spec = importlib.util.spec_from_file_location("_apnovo_worker_shape", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    class _Gen:
        """Stands in for upstream's run_generator module."""

        def __init__(self, exc=None):
            self.exc = exc
            self.calls = []

        def parse_and_prepare_diffusion_input(self, *, spec, seed, global_config):
            self.calls.append(seed)
            if self.exc is not None:
                raise self.exc
            return {"spec": spec, "seed": seed}

    def test_the_ceiling_refusal_is_reworded_into_advice_a_caller_can_take(self):
        mod = self._worker_module()
        gen = self._Gen(
            ValueError(
                "Number of residues in motif_spec > 512. Set max_num_res to a"
                " higher value."
            )
        )
        with pytest.raises(ValueError) as exc:
            mod._diffusion_input(gen, object(), 7, object())

        msg = str(exc.value)
        # upstream's own sentence is kept -- it names the real number
        assert "512" in msg
        # ... and contradicted where it misleads
        assert "not a budget this provider can raise" in msg
        # the two knobs that DO change the sampled length
        assert "seq_length" in msg and "motif_str" in msg
        # the seed, because the length is sampled per seed
        assert "seed 7" in msg
        # and the original is chained rather than swallowed
        assert isinstance(exc.value.__cause__, ValueError)

    def test_an_unrelated_value_error_is_not_dressed_up_as_a_length_problem(self):
        """The except clause must not swallow every ValueError the pipeline
        raises -- a motif that cannot be satisfied is a different failure and
        telling its caller to shorten the design would send them the wrong
        way."""
        mod = self._worker_module()
        gen = self._Gen(ValueError("motif atom OE2 not present in chain A"))
        with pytest.raises(ValueError) as exc:
            mod._diffusion_input(gen, object(), 0, object())
        assert str(exc.value) == "motif atom OE2 not present in chain A"
        assert "seq_length" not in str(exc.value)

    def test_a_design_that_fits_is_passed_straight_through(self):
        mod = self._worker_module()
        gen = self._Gen()
        spec = object()
        out = mod._diffusion_input(gen, spec, 3, object())
        assert out == {"spec": spec, "seed": 3}
        assert gen.calls == [3]

    def test_we_do_not_keep_our_own_copy_of_upstreams_ceiling(self):
        """The number belongs to upstream and lives in a function body there.
        A copy here would still read 512 after the pin moved."""
        import inspect

        mod = self._worker_module()
        src = inspect.getsource(mod._diffusion_input)
        # it may QUOTE upstream's message in the docstring, but must not
        # compare against a literal of its own
        body = src.split('"""')[-1]
        assert "512" not in body, body

    def test_validate_reports_the_lengths_it_actually_sampled(self):
        """`seq_length` is what the caller wrote; this is what was drawn."""
        mod = self._worker_module()

        class _Map:
            def __init__(self, n):
                self.source_residue_ids = list(range(n))

        class _Parsed:
            def __init__(self, n):
                self.residue_map = None if n is None else _Map(n)

        assert mod._sampled_lengths([_Parsed(131), _Parsed(147), _Parsed(None)]) == [
            131,
            147,
            None,
        ]


class TestCublasWorkspacesAreReleased:
    """The 32 MiB a request that no Python object held.

    torch keeps one cuBLAS workspace per (handle, stream) in a C++ static map
    that nothing clears. A kit that captures a CUDA graph warms it up on a
    fresh side stream, so every request abandoned a stream and left its
    workspace behind: measured at exactly
    `torch.backends.cuda.blas_workspace_size()` -- 32 MiB on the GB10 -- for
    `chai1` and `genie3`, linear, with no plateau in twenty requests, and for
    `rosettafold3`, found by a sweep of all 26 GPU providers afterwards.

    It was invisible to every ordinary check, which is why these tests exist
    at the call site rather than on a number: the bytes are in
    `memory_allocated` but reachable from no tensor, so `gc.collect()` freed
    nothing and `empty_cache()` freed nothing.
    """

    @staticmethod
    def _base():
        import importlib.util

        path = (
            Path(__file__).resolve().parents[2]
            / "src/tooluniverse/remote_resident/worker_base.py"
        )
        spec = importlib.util.spec_from_file_location("_wb_cublas", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _worker_src(slug: str) -> str:
        return (
            Path(__file__).resolve().parents[2]
            / f"src/tooluniverse/remote/{slug}/resident/{slug}_resident_worker.py"
        ).read_text()

    def test_the_helper_is_offered_by_the_shared_runtime(self):
        base = self._base()
        assert callable(base.release_cublas_workspaces)
        assert "release_cublas_workspaces" in base.__all__

    def test_a_build_without_the_call_gives_back_nothing_rather_than_raising(self):
        """Not every pinned stack has `_cuda_clearCublasWorkspaces`, and a
        worker must not die at the end of a successful request because of it."""
        base = self._base()
        assert base.release_cublas_workspaces() >= 0

    @staticmethod
    def _one_request(base, payload, **serve_kwargs):
        """Drive a real `serve` over a real socket and return (reply, calls).

        A source grep would only say the words are there. What matters is
        that a provider which does nothing itself still gets the release,
        because that is the whole point of moving it off the providers.
        """
        import socket as _socket
        import tempfile
        import threading

        freed = serve_kwargs.pop("freed", 32 * 2**20)
        calls = []

        def fake_release():
            calls.append(1)
            return freed

        base.release_cublas_workspaces = fake_release
        P = base.protocol()
        with tempfile.TemporaryDirectory() as d:
            sock_path = str(Path(d) / "s.sock")
            t = threading.Thread(
                target=base.serve,
                kwargs=dict(
                    slug="probe",
                    socket_path=sock_path,
                    on_predict=lambda req: {"echo": req.get("x")},
                    log=lambda msg: None,
                    **serve_kwargs,
                ),
                daemon=True,
            )
            t.start()
            for _ in range(200):
                if os.path.exists(sock_path):
                    break
                time.sleep(0.02)
            c = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            c.connect(sock_path)
            buf = bytearray()
            P.send_line(c, payload)
            reply = P.recv_line(c, buf)
            P.send_line(c, {"op": P.OP_SHUTDOWN})
            P.recv_line(c, buf)
            c.close()
            t.join(timeout=10)
        return reply, calls

    def test_serve_releases_for_a_provider_that_does_nothing_itself(self):
        base = self._base()
        reply, calls = self._one_request(base, {"op": "predict", "x": 7})
        assert reply["ok"] and reply["result"]["echo"] == 7
        assert len(calls) == 1, "serve did not release after the prediction"
        assert reply["result"]["cublas_workspaces_freed_mib"] == 32.0

    def test_serve_does_not_release_on_a_ping(self):
        base = self._base()
        _, calls = self._one_request(base, {"op": "ping"})
        assert calls == [], "a ping is not a request that stranded anything"

    def test_a_provider_can_turn_it_off_and_so_can_the_environment(self):
        """Both ways out exist so the leak stays reproducible on a provider
        that no longer has it -- which is how the fix was checked."""
        base = self._base()
        _, calls = self._one_request(
            base, {"op": "predict", "x": 1}, release_cublas=False
        )
        assert calls == []

        base = self._base()
        os.environ[base.NO_CUBLAS_RELEASE_ENV] = "1"
        try:
            _, calls = self._one_request(base, {"op": "predict", "x": 1})
        finally:
            os.environ.pop(base.NO_CUBLAS_RELEASE_ENV, None)
        assert calls == []

    def test_a_request_that_raised_still_releases(self):
        """A fold can get far enough to capture a graph and abandon its
        stream and then raise, and a worker answering a run of bad requests
        is where that adds up unnoticed."""
        import socket as _socket
        import tempfile
        import threading

        base = self._base()
        calls = []
        base.release_cublas_workspaces = lambda: (calls.append(1), 0)[1]
        P = base.protocol()

        def boom(req):
            raise RuntimeError("the fold failed after it captured")

        with tempfile.TemporaryDirectory() as d:
            sock_path = str(Path(d) / "s.sock")
            t = threading.Thread(
                target=base.serve,
                kwargs=dict(
                    slug="probe",
                    socket_path=sock_path,
                    on_predict=boom,
                    log=lambda msg: None,
                ),
                daemon=True,
            )
            t.start()
            for _ in range(200):
                if os.path.exists(sock_path):
                    break
                time.sleep(0.02)
            c = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            c.connect(sock_path)
            buf = bytearray()
            P.send_line(c, {"op": "predict"})
            reply = P.recv_line(c, buf)
            P.send_line(c, {"op": P.OP_SHUTDOWN})
            P.recv_line(c, buf)
            c.close()
            t.join(timeout=10)
        assert reply["ok"] is False and "the fold failed" in reply["error"]
        assert calls == [1], "the failure path skipped the release"

    def test_nothing_freed_adds_no_field(self):
        """Most requests of most providers strand nothing, and a 0.0 in every
        reply would read as a measurement rather than as silence."""
        base = self._base()
        reply, calls = self._one_request(base, {"op": "predict", "x": 1}, freed=0)
        assert calls == [1]
        assert "cublas_workspaces_freed_mib" not in reply["result"]

    def test_no_provider_makes_the_call_itself_any_more(self):
        """Two mechanisms doing the same thing is how one of them rots."""
        root = Path(__file__).resolve().parents[2] / "src/tooluniverse/remote"
        offenders = [
            str(p.relative_to(root))
            for p in root.rglob("*_resident_worker.py")
            if "WB.release_cublas_workspaces()" in p.read_text()
        ]
        assert offenders == [], (
            f"{offenders} still release on their own; serve does it for "
            f"everybody, and a second call site would hide the first"
        )

    def test_genie3_reports_a_per_request_peak_not_a_session_mark(self):
        """`max_memory_reserved` without a reset can only ever rise, so it
        reads as per-request growth whether or not any is happening -- and it
        is not what the other providers on this standard report."""
        src = self._worker_src("genie3")
        assert "torch.cuda.reset_peak_memory_stats()" in src
        assert "on_reset=_reset" in src


class TestARefusalEndsTheWorkerAndSaysSo:
    """A `SystemExit` out of a prediction, which is how the kits refuse.

    `af3_jax`, `rfdiffusion3` and `opendde` each define a
    `KernelsRefused(SystemExit)` and raise it from inside a prediction when
    the kernel route they required is not the route that loaded. All three
    carry code 5 -- STANDARD section 8's "an expected accelerator absent".

    The loop caught `Exception`, and a `SystemExit` is not one, so it unwound
    the whole worker: the caller's `recv_line` hit EOF and raised
    `ProtocolError: peer closed the connection mid-message`, and the KERNELS
    line naming the cause stayed in a transcript nobody was pointed at.

    The worker STILL dies -- that verdict is about the process, and swallowing
    it would not even keep the worker alive, because af3_jax arms an
    `os._exit(5)` sixty seconds out "should anything swallow the SystemExit"
    and rfdiffusion3's exit hook forces the same code at interpreter end. What
    these tests pin is that it no longer dies silently.
    """

    BASE = (
        Path(__file__).resolve().parents[2]
        / "src/tooluniverse/remote_resident/worker_base.py"
    )

    # The shape all three kits define: SystemExit(5) with the readable part on
    # an attribute, so `str(exc)` is the bare number "5".
    WORKER = textwrap.dedent(
        """
        import importlib.util, os, sys
        base_path, sock_path, mode = sys.argv[1], sys.argv[2], sys.argv[3]
        spec = importlib.util.spec_from_file_location("_wb", base_path)
        WB = importlib.util.module_from_spec(spec); spec.loader.exec_module(WB)

        class KernelsRefused(SystemExit):
            def __init__(self, reason):
                super().__init__(5)
                self.reason = reason

        def on_predict(req):
            if mode == "hardexit":
                sys.stderr.flush(); os._exit(5)
            raise KernelsRefused("KERNELS trimul=stock expected=kit")

        sys.exit(WB.serve(slug="probe", socket_path=sock_path,
                          on_predict=on_predict, release_cublas=False))
        """
    )

    @staticmethod
    def _base():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "_wb_refuse", TestARefusalEndsTheWorkerAndSaysSo.BASE
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _drive(base, on_predict, payloads, **serve_kwargs):
        """Run a real `serve` over a real socket; return (replies, what it raised).

        Driving the loop rather than reading the source, for the same reason
        the release tests do: the defect was never a missing word, it was a
        reply the caller did not get.
        """
        import tempfile

        raised = {}

        def run(**kw):
            try:
                base.serve(**kw)
            except BaseException as exc:  # noqa: BLE001 - that is the finding
                raised["exc"] = exc

        with tempfile.TemporaryDirectory() as d:
            sock_path = str(Path(d) / "s.sock")
            t = threading.Thread(
                target=run,
                kwargs=dict(
                    slug="probe",
                    socket_path=sock_path,
                    on_predict=on_predict,
                    log=lambda msg: None,
                    **serve_kwargs,
                ),
                daemon=True,
            )
            t.start()
            for _ in range(200):
                if os.path.exists(sock_path):
                    break
                time.sleep(0.02)
            c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            c.connect(sock_path)
            buf = bytearray()
            replies = []
            for payload in payloads:
                P.send_line(c, payload)
                try:
                    replies.append(P.recv_line(c, buf))
                except P.ProtocolError as exc:
                    replies.append(exc)
                    break
            c.close()
            t.join(timeout=10)
        return replies, raised.get("exc")

    class _Refused(SystemExit):
        def __init__(self, reason):
            super().__init__(5)
            self.reason = reason

    def test_a_refusal_is_answered_before_the_worker_goes(self):
        def on_predict(req):
            raise self._Refused("KERNELS trimul=stock expected=kit")

        base = self._base()
        replies, raised = self._drive(
            base, on_predict, [{"op": "predict"}], release_cublas=False
        )
        reply = replies[0]
        assert isinstance(reply, dict), "the caller got EOF instead of an answer"
        assert reply["ok"] is False
        assert reply["reason"] == "worker_exiting"
        assert reply["exit_code"] == 5
        assert isinstance(raised, SystemExit), "the refusal must still end the worker"
        assert raised.code == 5, "and with the code the kit chose"

    def test_the_readable_part_is_the_attribute_not_the_bare_code(self):
        """All three `KernelsRefused` classes pass the CODE to `SystemExit`,
        so `str(exc)` is "5" and the diagnosis is on `.reason` / `.line`."""

        def on_predict(req):
            raise self._Refused("KERNELS trimul=stock expected=kit")

        base = self._base()
        replies, _ = self._drive(
            base, on_predict, [{"op": "predict"}], release_cublas=False
        )
        assert "KERNELS trimul=stock expected=kit" in replies[0]["error"]
        assert "_Refused" in replies[0]["error"], "name the class that refused"

    def test_an_exception_with_neither_attribute_still_reports_as_it_prints(self):
        def on_predict(req):
            raise SystemExit("the plain form")

        base = self._base()
        replies, _ = self._drive(
            base, on_predict, [{"op": "predict"}], release_cublas=False
        )
        assert "the plain form" in replies[0]["error"]
        # SystemExit(str) prints it and exits 1; it is not an exit code.
        assert replies[0]["exit_code"] == 1

    def test_an_ordinary_exception_still_leaves_the_worker_serving(self):
        """The guard on the half that must NOT change: a bad request must not
        cost the minutes it took to build the model."""
        seen = []

        def on_predict(req):
            seen.append(req)
            if len(seen) == 1:
                raise ValueError("a bad request")
            return {"n": len(seen)}

        base = self._base()
        replies, raised = self._drive(
            base,
            on_predict,
            [{"op": "predict"}, {"op": "predict"}, {"op": "shutdown"}],
            release_cublas=False,
        )
        assert replies[0]["reason"] == "request_failed"
        assert replies[1]["ok"] and replies[1]["result"]["n"] == 2
        assert raised is None, "an ordinary failure must not end the worker"

    def test_the_workspaces_are_still_released_on_the_way_out(self):
        """The release is in a `finally`, and a refusal is exactly the request
        that got far enough to capture a graph and abandon its stream."""
        base = self._base()
        calls = []
        base.release_cublas_workspaces = lambda: (calls.append(1), 0)[1]

        def on_predict(req):
            raise self._Refused("refused")

        self._drive(base, on_predict, [{"op": "predict"}])
        assert calls == [1], "the fatal path skipped the release"

    # ------------------------------------------------------- through the supervisor
    @pytest.fixture
    def refusing_worker(self, tmp_path):
        script = tmp_path / "refusing_worker.py"
        script.write_text(self.WORKER)
        workers = []

        def make(mode):
            w = ResidentWorker(
                slug=f"refuse-{mode}-{os.getpid()}",
                build_command=lambda worker: (
                    [
                        sys.executable,
                        str(script),
                        str(self.BASE),
                        worker.socket_path,
                        mode,
                    ],
                    {},
                ),
                start_timeout_s=30.0,
                log_path=str(tmp_path / f"{mode}.log"),
            )
            workers.append(w)
            return w

        yield make
        for w in workers:
            w.stop(grace_s=5)

    def test_the_caller_is_told_what_refused_and_where_to_read_it(
        self, refusing_worker
    ):
        w = refusing_worker("refuse")
        with pytest.raises(WorkerRequestError) as exc:
            w.request({"op": "predict"})
        assert exc.value.reason == "worker_exiting"
        message = str(exc.value)
        assert "KERNELS trimul=stock expected=kit" in message
        # The two things the worker could not know itself.
        assert "transcript" in message and "refuse.log" in message
        assert "exit 5" in message
        for _ in range(100):  # it is on its way out
            if w._proc.poll() is not None:
                break
            time.sleep(0.05)
        assert w._proc.poll() == 5, "the kit's code must survive the reply"

    def test_a_worker_that_cannot_answer_is_named_by_its_exit_code(
        self, refusing_worker
    ):
        """`os._exit` leaves no chance to reply -- as do the OOM killer and a
        segfault. `ProtocolError: peer closed the connection mid-message` is
        true and useless; the code it exited with is not."""
        w = refusing_worker("hardexit")
        with pytest.raises(WorkerRequestError) as exc:
            w.request({"op": "predict"})
        assert exc.value.reason == "worker_died"
        assert "exited 5" in str(exc.value) and "exit 5" in str(exc.value)

    def test_the_exit_code_sentences_have_one_source(self):
        """STANDARD section 8 is only worth anything if what reads a code says
        what it means, and only stays worth anything if it says it once."""
        assert exit_hint(3) and exit_hint(5)
        assert exit_hint(1) == "" and exit_hint(None) == ""
        src = (
            Path(__file__).resolve().parents[2]
            / "src/tooluniverse/remote_resident/supervisor.py"
        ).read_text()
        assert src.count("that is a refusal (exit 3)") == 1
