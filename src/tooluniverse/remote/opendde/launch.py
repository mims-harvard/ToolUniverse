"""Build the command line that starts OpenDDE's resident worker.

This is `tooluniverse.remote_resident.kit_launch:build_command` with ONE
addition, and the addition is a property of the kit rather than a preference.

**The kit's `.pth` kills any interpreter that inherits a stray `OPENDDE_OPT*`
name -- including with the kit off, and including the model's own worker.**
`opendde_opt/_autoload.py` runs at interpreter start in every process of the
environment:

    undeclared = sorted(k for k in environ if k.startswith(ENV) and k not in DECLARED)
    if undeclared:
        _refuse(f"undeclared variable(s) {', '.join(undeclared)} ...")   # os._exit(3)

with `ENV = "OPENDDE_OPT"` and `DECLARED = (ENV,)`. It runs BEFORE the
`mode == "off"` return two lines below it, so `[kit] mode = "off"` is no
protection. Measured here, not read: `OPENDDE_OPT_X=1 python -c "print('x')"`
in this provider's interpreter prints the NOT ACTIVE line and exits 3, and so
does `OPENDDE_OPT=off OPENDDE_OPT_X=1 python ...`. `OPENDDE_BOGUS=1` and
`OPENDDE_FORCE_CONFIDENCE_AMP=1` do not -- the policed prefix is `OPENDDE_OPT`,
not `OPENDDE_`.

A resident worker is started by a supervisor the operator's shell started, and
the shell of the operator who has been running the kit's `run.sh` by hand is
exactly the one most likely to carry an `OPENDDE_OPT_*` it set for an
experiment. Without this wrapper such a worker exits 3 at interpreter start,
after the supervisor has committed to it, and the failure surfaces as a worker
that never became ready rather than as a named refusal.

So the inherited environment is STRIPPED, not merely left alone, and it is
stripped the one way `supervisor.child_env` acts on: a name mapped to None is
REMOVED. (af3_jax's launcher pruned a copy of `os.environ` and returned that;
the supervisor then rebuilt the child's environment from `os.environ` and every
removed name came straight back -- a check that read `build_command`'s return
value passed it. The test that counts is a real worker started with the hostile
variable exported and /proc/<pid>/environ read; that test is written
(see provider.toml) but had NOT been run when this was written.)

A SECOND TRAP, in the layer below. For a `venv` provider `exec_env.argv` returns
`{**os.environ, **env}` -- the operator's WHOLE environment, not only what the
kit adds -- so the mapping `kit_launch` returns already contains a stray
`OPENDDE_OPT_X`. Two consequences, both avoided here: the stray cannot be told
from a name this provider set by looking at that mapping (so the check on OUR
names reads `[kit.env]`, the only table this provider writes into it), and
"strip what is not in the mapping" removes nothing (so the removal set is built
from `os.environ` and the mapping together).

`OPENDDE_OPT` itself is the one policed name that stays: `kit_launch` sets it
from `[kit] mode`, over whatever the operator exported, so an inherited
`OPENDDE_OPT=fast` cannot contradict the manifest.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from tooluniverse.remote_resident.kit_launch import KitUnavailable, build_command as _kit

# `opendde_opt._autoload`: ENV = ENV_MODE = "OPENDDE_OPT"; DECLARED = (ENV,).
# Every name starting with it that is not exactly it is refused at interpreter
# start with exit 3.
POLICED_PREFIX = "OPENDDE_OPT"
DECLARED = ("OPENDDE_OPT",)


def build_command(worker) -> Tuple[List[str], Dict[str, Optional[str]]]:
    """``(argv, environment)`` for ``worker``; a None value is a removal."""
    argv, env = _kit(worker)

    # Our own names, checked against the kit's list rather than assumed: a typo
    # in [kit.env] would arm the very refusal this function exists to avoid, at
    # interpreter start in a process the supervisor has already committed to.
    own = set((worker.manifest.kit.get("env") or {}))
    undeclared = sorted(
        k for k in own if k.startswith(POLICED_PREFIX) and k not in DECLARED
    )
    if undeclared:
        raise KitUnavailable(
            f"{worker.manifest.slug}: [kit.env] sets {', '.join(undeclared)}, "
            f"which opendde_opt/_autoload.py does not declare; its start-up hook "
            f"exits any interpreter carrying an undeclared {POLICED_PREFIX}* "
            f"name with status 3. Declared: {', '.join(DECLARED)}"
        )

    # STRIP what the operator exported, and say it the one way the supervisor
    # acts on: map the name to None. `env` already holds the operator's whole
    # environment (see above), so both sources are walked.
    removals: Dict[str, Optional[str]] = {
        name: None
        for name in {*os.environ, *env}
        if name.startswith(POLICED_PREFIX) and name not in DECLARED
    }
    return argv, {**env, **removals}
