"""Start a resident worker under an optimization kit's own launcher.

Every kit in ``anthropics/uplifting-biomolecular-modeling`` is built on one
shared core, and the uniformity is usable: all 36 carry ``run.sh``,
``environment/``, ``opt/`` and ``stock/PINS.json``, and 35 name their package
``<kit>_opt`` (``protenix_v2`` is the one that does not, which is why
``[kit] package`` can be stated). There are two ways a kit engages, and the common one is the simpler:

**Autoload (30 of 36).** The kit installs a ``.pth`` that imports its
``_autoload`` at interpreter start. With its mode variable set — ``modes.ENV``,
e.g. ``BORZOI_OPT=exact`` — a meta-path finder waits for the model package's
own import and patches it in place. Our worker is then just a script run by the
model's interpreter with that variable in the environment. Nothing else.

**worker_launch (1 of 36: boltz2).** That kit adds a launcher that runs an
arbitrary script under an explicit kernel route and attach list::

    <model python> -m boltz2_opt.worker_launch --route … --attach … -- <script> …

Either way a resident worker is a script of ours in a position the kit already
serves, and nothing in the kit is patched, copied or shadowed.

Which one a kit uses is detected, not declared: the probe reports whether
``<pkg>.worker_launch`` imports. That keeps the exception from becoming a
manifest field every other provider has to get right.

**One kit cannot be made resident with its levers at all.** ChromBPNet's own
autoload says it: "THE ONE DEVIATION from an in-process hook: the kit's form is
a replacement entry script; it offers no in-process patch." Its finder fires
only when ``sys.argv[0]`` is the stock console script, and then runs a child.
A provider like that declares ``mode = "subprocess"`` with the reason, rather
than pretending.

The options and the environment row are deliberately not written down here.
They belong to the kit, change with it, and cannot be read from this process at
all — ``<kit>_opt`` lives in the model's environment, whose pinned stack does
not coexist with ToolUniverse's. So the kit is asked, once per worker start, in
its own interpreter. A hard-coded copy would drift silently the first time the
kit was updated; this cannot.

One subtlety that looks like an oversight in a manifest and is not: a kit's row
may set a switch for an adapter that misbehaves on a given host. Leave it. An
adapter named in ``--attach`` whose switch is *missing* from the row refuses the
whole launch, whereas one whose switch is present and whose preconditions are
not met declines by its own name and the launch proceeds. Removing the variable
breaks the start; leaving it is what keeps the code out of the process.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .exec_env import from_manifest

KIT_PROBE_TIMEOUT_S = 180.0

# Runs in the model's interpreter. MODEL_OPT is the kit directory, derived from
# where the package was installed from rather than from a variable a deployment
# would have to keep in step with the checkout.
_PROBE = r"""
import json, os, pathlib, sys
pkg_name = sys.argv[1]
pkg = __import__(pkg_name)
os.environ.setdefault("MODEL_OPT", str(pathlib.Path(pkg.__file__).resolve().parents[2]))
mode = sys.argv[2]
out = {"model_opt": os.environ["MODEL_OPT"], "env": {}, "opts": [], "activation": "autoload"}
# The kit names its own mode variable. Guessing it from the slug is how a
# renamed kit would silently run stock, so it is read from wherever the kit
# keeps it: modes.ENV in the kits that have a modes module, _autoload.ENV in
# those that do not (enformer_opt is one).
# Two holders and two spellings. The ATTRIBUTE name varies as much as the
# value does: af3_torch and genie3 both keep it as `ENV_MODE`, and genie3
# cannot start at all without it being found -- the probe used to refuse with
# "exposes no modes.ENV ... the provider belongs in mode = subprocess", which
# is the wrong diagnosis for a kit whose mode is an in-process driver.
for _holder in (".modes", "._autoload", ".stack"):
    try:
        _mod = __import__(pkg_name + _holder, fromlist=["x"])
    except Exception:
        continue
    for _attr in ("ENV", "ENV_MODE"):
        if getattr(_mod, _attr, None):
            out["mode_env"] = getattr(_mod, _attr)
            break
    if out.get("mode_env"):
        break
def _row_of(resolution):
    # resolve() returns a mapping in some kits and a dataclass in others, and
    # the field holding the child's variables is spelled `env` in one and
    # `exports` in another. Neither spelling is wrong; only assuming one of
    # them is. Try what the kits actually use and give up visibly.
    for name in ("env", "exports"):
        value = getattr(resolution, name, None)
        if value is None:
            try:
                value = resolution[name]
            except Exception:
                continue
        if value is not None:
            return {k: str(v) for k, v in dict(value).items()}
    return None


try:
    modes = __import__(pkg_name + ".modes", fromlist=["modes"])
except Exception as exc:
    out["modes_error"] = "%s: %s" % (type(exc).__name__, exc)
else:
    out["modes"] = list(getattr(modes, "MODES", ()) or ())
    # resolve()'s signature differs too: openfold3_opt's takes a required
    # `home` after the mode. Try the shapes the kits actually use, in order,
    # and record which one answered so a silent empty row is impossible.
    _home = out["model_opt"]
    for _label, _call in (
        ("resolve(mode)", lambda: modes.resolve(mode)),
        ("resolve(mode, home)", lambda: modes.resolve(mode, _home)),
    ):
        try:
            _row = _row_of(_call())
        except Exception as _exc:
            out.setdefault("row_errors", []).append("%s: %s: %s" % (_label, type(_exc).__name__, _exc))
            continue
        if _row is not None:
            out["env"].update(_row)
            out["row_source"] = _label
            break
    else:
        out["row_error"] = "; ".join(out.get("row_errors") or ["no resolve() shape matched"])
    try:
        try:
            out["stack_key"] = modes.jit_cache_key()
        except AttributeError:
            # e1 and genie3 keep it on <pkg>.stack, which is where their own
            # configs/<card>.env call it from.
            _stack = __import__(pkg_name + ".stack", fromlist=["x"])
            out["stack_key"] = _stack.jit_cache_key()
    except Exception as _exc:
        # Recorded, not swallowed: some kits' jit_cache_key takes
        # (torch_version, cc) -- their configs/<card>.env calls it that way --
        # and a kit that HAS one and raised looked identical to a kit that
        # never had one.
        out["stack_key_error"] = "%s: %s" % (type(_exc).__name__, _exc)
# Some kits put the child's environment somewhere other than a mode row:
# chai1_opt keeps the allocator setting in alloc.env_row(), and it has to be in
# place BEFORE the process makes its first CUDA allocation, so the kit cannot
# apply it to itself. Each accessor below is the kit's own; only the names of
# the places to look are written here.
for _mod_name, _fn_name in ((".alloc", "env_row"),):
    try:
        _m = __import__(pkg_name + _mod_name, fromlist=["x"])
        out["env"].update({k: str(v) for k, v in dict(getattr(_m, _fn_name)()).items()})
    except Exception:
        pass
try:
    __import__(pkg_name + ".worker_launch", fromlist=["worker_launch"])
except Exception:
    pass
else:
    out["activation"] = "worker_launch"
    stack = __import__(pkg_name + ".stack", fromlist=["stack"])
    out["opts"] = stack.launch_opts(mode, 1, "defaults")
sys.stdout.write("KITROW " + json.dumps(out))
"""


class KitUnavailable(RuntimeError):
    """The kit is not installed on the model environment's interpreter."""


def kit_package(manifest) -> str:
    """``[kit] package``, else ``<subdir>_opt`` — the convention 35 of 36 follow."""
    declared = manifest.kit.get("package")
    if declared:
        return str(declared)
    subdir = manifest.kit.get("subdir") or manifest.slug
    return f"{subdir}_opt"


def ask_kit(
    python_or_env, package: str, mode: str, levers_off: Sequence[str] = ()
) -> Dict:
    """The kit's own launch options and environment row, read in its interpreter.

    ``python_or_env`` is an interpreter path or an :class:`ExecEnvironment`. The
    probe has to run where the kit is installed, which for a container provider
    is inside the container: asking this process's interpreter would report a
    kit that is not the one the worker will load.

    ``levers_off`` is set in the PROBE's environment, not only in the worker's.
    The kits read ``MODEL_OPT_LEVERS_OFF`` when they resolve a mode, so a probe
    run without it reports the unablated row -- and a kit that then sees the
    ablated one refuses the whole activation over the mismatch. openfold3's
    worker carries a ``_reconcile_kit_row`` to work around exactly that, which
    is a workaround every later provider with both a row and an ablation would
    have had to re-derive.
    AND THE SAME PRINCIPLE APPLIES TO THE OPERATOR'S STRAY VARIABLES, which is
    a gap this function had until opendde's acceptance ran into it. Most kits'
    ``.pth`` kills any interpreter that inherits an UNDECLARED ``<PACKAGE>_*``
    name -- opendde's exits 3 on ``OPENDDE_OPT_X=1 python -c "print('x')"``. A
    provider's launcher strips those from the WORKER by mapping them to None,
    but the supervisor applies that mapping to the command this function helps
    build, so the probe had already inherited them and died:

        KitUnavailable: could not read opendde_opt's mode row for mode='off'
        (rc 3). Its own words:
        [opendde-opt] NOT ACTIVE: reason=undeclared variable(s)
          OPENDDE_OPT_BOGUS, OPENDDE_OPT_X

    The probe has to run under the conditions the worker will, and the stray
    names are one of those conditions. The policed prefix is mechanical: every
    kit package is ``<slug>_opt``, so ``package.upper()`` is the name the kit
    declares and anything extending it with an underscore is undeclared. The
    declared name itself is KEPT, because the probe exists to read the row that
    name selects.
    """
    if isinstance(python_or_env, (str, os.PathLike)):
        argv, env, python = (
            [os.fspath(python_or_env), "-c", _PROBE, package, mode],
            None,
            str(python_or_env),
        )
    else:
        argv, env = python_or_env.argv(["-c", _PROBE, package, mode])
        python = python_or_env.describe()
    declared = package.upper()
    undeclared = [
        name
        for name in (env if env is not None else os.environ)
        if name.startswith(declared + "_")
    ]
    if levers_off or undeclared:
        env = dict(env if env is not None else os.environ)
        for name in undeclared:
            env.pop(name, None)
    if levers_off:
        env = dict(env if env is not None else os.environ)
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in levers_off)
    proc = subprocess.run(
        argv,
        env=env,
        capture_output=True,
        text=True,
        timeout=KIT_PROBE_TIMEOUT_S,
    )
    marker = "KITROW "
    for line in proc.stdout.splitlines():
        if line.startswith(marker):
            return json.loads(line[len(marker) :])
    raise KitUnavailable(
        f"{python}: could not read {package}'s mode row for mode={mode!r} "
        f"(rc {proc.returncode}). Its own words:\n"
        f"{(proc.stderr or proc.stdout).strip()[-1500:]}"
    )


def build_command(worker) -> Tuple[List[str], Dict[str, str]]:
    """``(argv, extra environment)`` for ``worker``. The supervisor calls this."""
    manifest = worker.manifest
    exec_env = from_manifest(manifest)
    if manifest.env_kind == "venv" and not Path(manifest.python_executable()).is_file():
        raise KitUnavailable(
            f"[env] python points at {manifest.python_executable()}, which is not "
            f"a file — it must be the interpreter of {manifest.slug}'s own environment"
        )

    root = manifest.weights_root()
    if manifest.weights and root is None:
        raise KitUnavailable(f"no weights directory: set {manifest.weights_root_env}")
    problems = manifest.verify_weights()
    if problems:
        # Nothing is fetched here. A short or altered cache is named and the
        # launch stops, rather than a model loading whatever is on disk.
        raise KitUnavailable(
            f"{manifest.slug}: the weights under {root} are not at their pins:\n  "
            + "\n  ".join(problems)
            + f"\n  run `tu remote setup {manifest.slug}` after removing the named file"
        )

    package = kit_package(manifest)
    off = manifest.kit.get("levers_off") or ()
    row = ask_kit(exec_env, package, manifest.kit.get("mode", "fast"), off)

    worker_py = manifest.resolve(manifest.worker)
    shared = Path(__file__).resolve().parent
    fields = {
        "socket": worker.socket_path,
        "slug": manifest.slug,
        "weights_root": os.fspath(root) if root else "",
        "python": manifest.python_executable(),
        "kit": row["model_opt"],
        "work_root": manifest.work_root or "",
    }
    tail = [os.fspath(worker_py)] + [
        str(a).format(**fields) for a in (manifest.worker_args or ())
    ]
    if row.get("activation") == "worker_launch":
        python_args = ["-m", f"{package}.worker_launch", *row["opts"], "--", *tail]
    else:
        # The autoload path: the kit is engaged by its own mode variable and the
        # .pth it installed, so our script is run plainly.
        python_args = list(tail)

    env: Dict[str, str] = dict(row["env"])
    # An empty row is either a fact about the kit or a failure to read one, and
    # they are indistinguishable from here -- so the manifest says which.
    if not env and manifest.kit.get("env_row", "probe") != "none":
        raise KitUnavailable(
            f"{package}: the kit returned no environment row"
            + (f" ({row['row_error']})" if row.get("row_error") else "")
            + f". If this kit genuinely keeps none, declare it:\n"
            f'  [kit] env_row = "none"\n'
            f'  env_row_reason = "<where its variables live instead>"\n'
            f"Otherwise the probe needs the shape this kit's resolve() takes; "
            f"openfold3 ran with 0 of its 37 variables until this was checked"
        )
    env["MODEL_OPT"] = row["model_opt"]
    mode_env = row.get("mode_env")
    if row.get("activation") != "worker_launch":
        if not mode_env:
            raise KitUnavailable(
                f"{package} exposes no modes.ENV, so there is no way to engage it "
                f"in our own process; if its form is a replacement entry script "
                f'(ChromBPNet is), the provider belongs in mode = "subprocess"'
            )
        env[mode_env] = manifest.kit.get("mode", "fast")
    if row.get("stack_key"):
        env["MODEL_OPT_STACK_KEY"] = row["stack_key"]
    # Settings the provider states for this kit, applied before the process
    # starts. This is for a kit's own documented knobs -- a size gate, a cap, a
    # core pin -- which `levers_off` cannot express because they are not
    # levers. openfold3 needs OPENFOLD3_OPT_POST_RELEASE_NTOK = "0" or it dies
    # on the second request of a shape, and that belongs next to `levers_off`
    # in a file a reviewer reads, not in a line of Python in the worker.
    #
    # Not validated against the kit: a kit that polices its own namespace
    # (rosettafold3 exits 3 on any undeclared ROSETTAFOLD3_OPT_* name) will
    # refuse a wrong one by name, which is the better error than any guess
    # this could make.
    for key, value in (manifest.kit.get("env") or {}).items():
        env[str(key)] = str(value)

    if off:
        # A lever the provider asks the kit not to attempt. The kits read this
        # themselves (MODEL_OPT_LEVERS_OFF) and say so on their ACTIVE line as
        # a PARTIAL activation, which is the honest record: the run is an
        # ablation of the mode, not the mode.
        env["MODEL_OPT_LEVERS_OFF"] = ",".join(str(x) for x in off)
    if root is not None and manifest.weights_root_env:
        env[manifest.weights_root_env] = os.fspath(root)
    # Both shared files are found by path: this process's package is not
    # importable from the model's environment, and must not be.
    env["TOOLUNIVERSE_REMOTE_PROTOCOL"] = os.fspath(shared / "protocol.py")
    env["TOOLUNIVERSE_REMOTE_WORKER_BASE"] = os.fspath(shared / "worker_base.py")
    # Compiled kernels keyed by torch+CUDA+arch. Keeping them across worker
    # lifetimes is what stops a restart recompiling: on the first provider the
    # smoke prediction fell from 42 s to 12 s once the cache was warm.
    jit_root = os.environ.get("MODEL_OPT_JIT_ROOT") or os.path.expanduser(
        f"~/.cache/tooluniverse/{manifest.slug}-jit"
    )
    os.makedirs(jit_root, exist_ok=True)
    env["MODEL_OPT_JIT_ROOT"] = jit_root
    # A container must also see the JIT cache it writes, and the work root the
    # caller's output directories live under.
    exec_env.binds.append(Path(jit_root))
    argv, popen_env = exec_env.argv(python_args, env)
    return argv, popen_env
