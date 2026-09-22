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
