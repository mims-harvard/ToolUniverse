"""Build the command line that starts Proteina-Complexa's resident worker.

``tooluniverse.remote_resident.kit_launch:build_command`` is what 15 of the 23
providers use, and it was tried here first. It does not fit, for three reasons
that are properties of this kit rather than preferences of this provider. Each
is stated so a later reader can check whether it still holds and move back to
the shared launcher if it does not.

**1. The hook refuses on names it does not read, and the shared launcher cannot
remove a name.** ``complexa_opt/_autoload.py`` runs in EVERY interpreter of this
environment -- it is laid by ``complexa_opt_autoload.pth`` -- and its second
statement is::

    _unread = sorted(k for k in os.environ if k.startswith(ENV) and k not in DECLARED)
    if _unread:
        sys.stderr.write("[complexa-opt] NOT ACTIVE: reason=%s is not a variable
                          this package reads ...")
        raise SystemExit(3)

with ``ENV = "COMPLEXA_OPT"`` and ``DECLARED = ("COMPLEXA_OPT",
"COMPLEXA_OPT_RECORD")``. So a single ``COMPLEXA_OPT_ANYTHING`` exported in the
operator's shell -- the shell of exactly the operator who has been running
``run.sh`` by hand -- exits the worker 3 at interpreter start, before it binds
its socket, after the supervisor has committed to the process. This is af3_jax's
shape and STANDARD.md section 13 records it: a launcher must STRIP undeclared
names, not merely decline to set them. ``kit_launch`` only ever adds names.

The removal is expressed the one way the executor acts on: a ``None`` value in
the returned mapping, which ``supervisor.child_env`` pops from the operator's
environment. A pruned copy of ``os.environ`` does NOT work and silently did
nothing for af3_jax, because ``supervisor._start`` builds the child's
environment as ``dict(os.environ)`` updated with this mapping. Verified by the
thing that executes rather than by this function's return value: see the
provider's ``verified_on``.

**2. This kit keeps no mode row, so the shared probe's own guard fires.**
``complexa_opt.modes`` has a ``resolve()``, but it is not the ``resolve()`` the
probe means: it takes ``(cli_value, environ)`` and returns the mode WORD, a
``str``. ``kit_launch._row_of`` then finds neither ``.env`` nor ``.exports`` on
a string, falls through to ``resolve(mode, home)`` -- which passes a path where
``environ`` is expected and raises ``AttributeError`` -- and reports an empty
row. That is correct about this kit and would be indistinguishable from a failure
to read one, which is what ``[kit] env_row = "none"`` exists to say. But the
row this kit genuinely needs is not empty: it lives in ``configs/h100.env`` and
its siblings, and it has to be APPLIED, not just declared absent. See
``_kit_row`` below, which is a transcription of that file's derived defaults and
says so line by line.

**3. Hydra resolves ``${oc.env:...}`` eagerly, so four of upstream's optional
variables are load-bearing even though nothing reads their values.**
``binder_generate.yaml`` interpolates ``${oc.env:AF2_DIR}`` in its reward-model
block and ``${oc.env:DATA_PATH}`` in the ``oc.select`` fallback for the target
path, and OmegaConf resolves both while composing even though this provider runs
``++generation.reward_model=null`` and always supplies an absolute
``target_path``. Unset, composition raises before the model is reached. The kit
hits the same wall and solves it the same way -- ``configs/*.env`` stubs seven
optional tool paths with ``/bin/true`` -- so this is the kit's own answer
applied, not an invention.

**4. The card needs a newer NVRTC than torch carries, and only the loader can
supply it.** torch 2.7.0+cu128 bundles NVRTC 12.8, which does not know sm_121, so
``torch.prod(x, dim=-1)`` -- which upstream's openfold transforms call on every
target's side-chain torsion features (data_transforms.py:980) -- fails on every
CUDA dtype with ``nvrtc: error: invalid value for --gpu-architecture (-arch)``.
``environment/requirements.lock`` carries ``nvidia-cuda-nvrtc-cu12==12.9.86`` for
that and this launcher puts its ``lib`` directory FIRST on ``LD_LIBRARY_PATH``,
which outranks the RUNPATH torch's own copy is found by. It has to be the
child's environment rather than the worker's ``os.environ``: the dynamic loader
reads ``LD_LIBRARY_PATH`` once, at process start. The lock header has the
measurement.

**What is NOT done here, deliberately.** No lever row is copied and no numeric
setting is chosen. The mode reaches the worker as ``COMPLEXA_OPT`` and the
kit's autoload hook resolves the lever set itself, inside the worker, from
``modes.KIT_MODES``. A hard-coded copy would drift the first time the kit moved.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable
from tooluniverse.remote_resident.setup import kit_checkout

# complexa_opt/_autoload.py DECLARED. Any environment name beginning
# "COMPLEXA_OPT" and outside this pair makes the start-up hook exit 3, in every
# interpreter of this environment.
DECLARED_ENV = ("COMPLEXA_OPT", "COMPLEXA_OPT_RECORD")
MODE_ENV = "COMPLEXA_OPT"
RECORD_ENV = "COMPLEXA_OPT_RECORD"

# Upstream's own two names (STOCK.md 'Variables'); neither has a default and
# the kit refuses by name without them.
UPSTREAM_ENV = "LOCAL_CODE_PATH"  # upstream's checkout at the pin
WEIGHTS_ENV = "CKPT_PATH"  # the directory holding the two checkpoints

# Upstream's optional reward / evaluation tools. Hydra resolves ${oc.env:...}
# eagerly while composing, so a name that is never read still has to EXIST.
# configs/*.env stubs each with /bin/true; so does this.
STUBBED_TOOLS = (
    "ESM_DIR",
    "RF3_CKPT_PATH",
    "RF3_EXEC_PATH",
    "FOLDSEEK_EXEC",
    "MMSEQS_EXEC",
    "DSSP_EXEC",
    "SC_EXEC",
)


def _clean_env() -> Dict[str, str]:
    """This process's environment without any ``COMPLEXA_OPT*`` name.

    Every interpreter of the model's environment runs the kit's start-up hook,
    and the hook exits 3 on a stray ``COMPLEXA_OPT_ANYTHING``. A probe this
    launcher runs in that interpreter would die of the operator's variable and
    report it as "cannot import proteinfoundation", which is a wrong diagnosis
    delivered with confidence.
    """
    return {k: v for k, v in os.environ.items() if not k.startswith(MODE_ENV)}


def _probe(python: str, code: str):
    import subprocess

    return subprocess.run(
        [python, "-c", code],
        capture_output=True,
        text=True,
        timeout=300,
        env=_clean_env(),
    )


def _nvrtc_dir(python: str) -> str:
    """``nvidia/cuda_nvrtc/lib`` of the model's environment, which must hold a
    NVRTC that knows this card -- see item 4 of the module docstring."""
    probe = _probe(
        python,
        "import sysconfig, pathlib; "
        "print(pathlib.Path(sysconfig.get_paths()['purelib']) / 'nvidia' / "
        "'cuda_nvrtc' / 'lib')",
    )
    path = Path((probe.stdout or "").strip() or "/nonexistent")
    if probe.returncode != 0 or not (path / "libnvrtc.so.12").is_file():
        raise KitUnavailable(
            f"complexa: {path} holds no libnvrtc.so.12. torch 2.7.0+cu128's own "
            f"NVRTC does not know sm_121 and torch.prod() fails on this card "
            f"without a newer one. `tu remote setup complexa --only environment` "
            f"installs nvidia-cuda-nvrtc-cu12==12.9.86 from the lock."
        )
    return os.fspath(path)


def _upstream_checkout(python: str) -> str:
    """Upstream's checkout at the pin: ``LOCAL_CODE_PATH``, else the editable
    install's own directory.

    The second route is the kit's own rule (``stock/check_pins.py``
    ``checkout_dir``): ``proteinfoundation`` is installed ``-e`` from the
    checkout, so the package's location names it and no per-machine variable is
    needed. Deriving it is better than requiring a variable, because the one
    thing a variable can be is out of step with the interpreter the lock built.
    """
    named = os.environ.get(UPSTREAM_ENV)
    if named:
        path = Path(named).expanduser()
    else:
        probe = _probe(
            python,
            "import proteinfoundation, pathlib; "
            "print(pathlib.Path(proteinfoundation.__file__).resolve().parents[2])",
        )
        if probe.returncode != 0:
            raise KitUnavailable(
                f"complexa: upstream's checkout cannot be located -- "
                f"{UPSTREAM_ENV} is unset and `import proteinfoundation` failed "
                f"on {python}:\n{(probe.stderr or '').strip()[-800:]}\n"
                f"Run `tu remote setup complexa --only environment`, or export "
                f"{UPSTREAM_ENV}=<the Proteina-Complexa checkout at the pin>."
            )
        path = Path(probe.stdout.strip())
    pipeline = path / "configs" / "search_binder_local_pipeline.yaml"
    if not pipeline.is_file():
        raise KitUnavailable(
            f"complexa: {UPSTREAM_ENV}={path} holds no "
            f"configs/search_binder_local_pipeline.yaml, so it is not upstream's "
            f"checkout at the pin. The lock installs it editable from "
            f"`-e git+https://github.com/NVIDIA-Digital-Bio/proteina-complexa"
            f"@916eaaed...#egg=proteinfoundation`."
        )
    return os.fspath(path)


def _kit_row(checkout: str, state: str) -> Dict[str, str]:
    """The kit's deployment row for this host.

    This kit keeps no mode row -- there is no ``modes.resolve()`` returning
    ``env``/``exports`` and no ``env_row()`` anywhere under
    ``opt/complexa_opt/`` (grep finds neither) -- and keeps its deployment
    variables in ``configs/h100.env`` / ``a100.env`` / ``h200.env`` instead.
    That is the esmfold2 / esmc / rosettafold3 shape STANDARD.md section 16
    names, and the manifest declares ``env_row = "none"`` for it.

    None of those three files is this card, so none is sourced. What is
    transcribed below is only the part of ``h100.env`` that the file itself
    DERIVES rather than states -- the checkout-relative paths, the state root,
    and the stubs -- each with the same rule the file uses. The one line that
    is genuinely per-card, ``MODEL_OPT_TARGET_GPU``, is set to the card found
    rather than to H100: the kit documents it as "a report, never a gate", its
    ACTIVE line prints ``gpu_class=other`` for any capability outside {9.0,
    8.0}, and claiming H100 on a GB10 would put a false fact in the kit's own
    record for no benefit.

    Nothing here selects a mode, a lever or a numeric setting; ``h100.env``
    says the same of itself in its second line.
    """
    row = {
        # upstream's CLI refuses to run before `complexa init` unless set
        "COMPLEXA_INIT": "1",
        # out-of-tree state root; AF2_DIR hangs off it, as in h100.env
        "MODEL_OPT_STATE": state,
        # upstream's two checkout-relative variables. The generation stage reads
        # neither value, but Hydra resolves DATA_PATH eagerly in
        # binder_generate.yaml's oc.select fallback for the target path.
        "COMMUNITY_MODELS_PATH": os.fspath(Path(checkout) / "community_models"),
        "DATA_PATH": os.fspath(Path(checkout) / "assets" / "target_data"),
        # The reward model's parameters. ++generation.reward_model=null means
        # the directory is never read; the NAME is still resolved eagerly while
        # composing, so it must exist as a variable.
        "AF2_DIR": os.fspath(Path(state) / "af2_params"),
        # no .pyc in the checkout (the kit's own PYTHONDONTWRITEBYTECODE line)
        "PYTHONDONTWRITEBYTECODE": "1",
        # The card this configuration targets. A report, never a gate.
        "MODEL_OPT_TARGET_GPU": os.environ.get("MODEL_OPT_TARGET_GPU") or "other",
    }
    for name in STUBBED_TOOLS:
        row[name] = os.environ.get(name) or "/bin/true"
    return row


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest

    python = manifest.python_executable()
    if not Path(python).is_file():
        raise KitUnavailable(
            f"[env] python points at {python}, which is not a file -- it must "
            f"be the interpreter of {manifest.slug}'s own environment "
            f"(set TOOLUNIVERSE_COMPLEXA_PYTHON)"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. 6.6 GiB of checkpoint that is short or off its
        # digest is named and the launch stops, rather than a model loading
        # whatever is on disk -- which is the failure STANDARD.md section 4 was
        # written for.
        raise KitUnavailable(
            f"{manifest.slug}: the weights under {root} are not at their pins:\n  "
            + "\n  ".join(problems)
            + f"\n  run `tu remote setup {manifest.slug}` after removing the named file"
        )

    checkout = kit_checkout(manifest)
    kit_home = checkout / manifest.kit.get("subdir", "") if checkout else None
    if kit_home is None or not kit_home.is_dir():
        raise KitUnavailable(
            f"{manifest.slug}: the kit checkout is not at {kit_home} -- "
            f"run `tu remote setup {manifest.slug} --only kit`"
        )

    upstream = _upstream_checkout(python)
    state = os.environ.get("MODEL_OPT_STATE") or os.path.expanduser(
        "~/.cache/complexa_opt"
    )
    os.makedirs(state, exist_ok=True)

    # The kit's own activation record for this process, read back for evidence:
    # one kit_<pid>.json carrying the lever census and the TALLY state. The hook
    # writes nothing without it, which would leave the ACTIVE line as the only
    # record of whether the mode engaged.
    record_dir = os.path.join(state, "kit_records", manifest.slug)
    os.makedirs(record_dir, exist_ok=True)

    jit_root = os.environ.get("MODEL_OPT_JIT_ROOT") or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-jit"
    )
    os.makedirs(jit_root, exist_ok=True)

    shared = (
        Path(
            __import__(
                "tooluniverse.remote_resident.worker_base", fromlist=["worker_base"]
            ).__file__
        )
        .resolve()
        .parent
    )

    fields = {
        "socket": worker.socket_path,
        "slug": manifest.slug,
        "kit": os.fspath(kit_home),
        "kit_mode": manifest.kit.get("mode", "fast"),
        "upstream": upstream,
        "weights_root": os.fspath(root) if root else "",
        "python": python,
    }
    worker_py = manifest.resolve(manifest.worker)
    argv = [python, os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]

    env: Dict[str, str] = dict(_kit_row(upstream, state))
    # run.sh's name for the kit directory; the package locates stock/ through it.
    env["MODEL_OPT"] = os.fspath(kit_home)
    env[UPSTREAM_ENV] = upstream
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)
    env[MODE_ENV] = manifest.kit.get("mode", "fast")
    env[RECORD_ENV] = record_dir
    env["MODEL_OPT_JIT_ROOT"] = jit_root

    # A PRIVATE Triton cache, empty by construction, so that "nothing on this
    # path compiles a Triton kernel" is a thing every reply can SHOW rather than
    # a thing the manifest argues. triton 3.3.0 cannot lower a cross-lane
    # reduction on this card and aborts the process uncatchably, so the day some
    # upstream edit reaches a Triton kernel the right outcome is a named
    # refusal, not a worker that dies between requests. `import triton` itself
    # happens (torch._dynamo's `has_triton_package`, reached through lightning)
    # and means nothing; a compiled kernel leaves files here.
    triton_cache = os.path.join(jit_root, "triton")
    os.makedirs(triton_cache, exist_ok=True)
    env["TRITON_CACHE_DIR"] = triton_cache

    # THE NEWER NVRTC, first on the loader's path. See item 4 of the docstring:
    # without it every request dies in torch.prod. The operator's own value is
    # kept, after ours.
    nvrtc = _nvrtc_dir(python)
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = nvrtc + (os.pathsep + existing if existing else "")

    # [kit.env] -- applied HERE because kit_launch, which normally reads that
    # table, is not on this provider's path. A provider with its own launcher
    # that forgets this ships settings that are silently inert.
    for name, value in (manifest.kit.get("env") or {}).items():
        env[str(name)] = str(value)

    off = manifest.kit.get("levers_off") or ()
    if off:
        # Declared unreachable for this kit -- see [kit] levers_off in
        # provider.toml -- so this is a door that is NOT wired for this kit. Setting
        # it when nothing reads it is how boltzgen shipped a setting that did
        # nothing, so the manifest states the finding and this stays empty.
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in off)

    # Both shared files are found by path: this package is not importable from
    # the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")

    # Our own names, checked against the kit's list rather than assumed. A typo
    # in one of the two COMPLEXA_OPT* names set above would arm the very refusal
    # this function exists to prevent, at interpreter start, in a process the
    # supervisor has already committed to.
    undeclared = sorted(
        k for k in env if k.startswith(MODE_ENV) and k not in DECLARED_ENV
    )
    if undeclared:
        raise KitUnavailable(
            f"{manifest.slug}: this launcher would set {', '.join(undeclared)}, "
            f"which complexa_opt/_autoload.py does not declare; its start-up "
            f"hook exits 3 in any interpreter carrying an undeclared "
            f"{MODE_ENV}* name. Declared: {', '.join(DECLARED_ENV)}"
        )

    # STRIP, do not merely omit. Every COMPLEXA_OPT* name the operator exported
    # and this launcher does not set must be REMOVED from the child: the hook
    # refuses the interpreter over it and exits 3 before the socket is bound.
    # Mapping a name to None is the removal `supervisor.child_env` honours; a
    # pruned copy of os.environ is NOT (af3_jax shipped one that did nothing,
    # and the check that passed read this function's return value, where a
    # pruned copy looks perfectly correct).
    removals = {
        name: None
        for name in os.environ
        if name.startswith(MODE_ENV) and name not in env
    }
    return argv, {**removals, **env}
