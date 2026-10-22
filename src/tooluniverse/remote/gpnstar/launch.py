"""Build the command line that starts gpnstar's resident worker.

This is ``tooluniverse.remote_resident.kit_launch:build_command`` plus ONE thing,
and the one thing is why this file exists at all.

**It removes the names that would move this provider's numbers without moving
anything it reports.** The kit's ``stock/PINS.json`` states, under
``stock_environment``, that a stock process must have no TF32 override in its
environment (``numerics_must_be_absent``), and STOCK.md says the numerics are
"PyTorch's defaults: fp32, matmul TF32 off". ``exact`` is bitwise to stock *under
whatever numerics the caller runs* -- the kit follows the caller's setting rather
than choosing one -- so an ``NVIDIA_TF32_OVERRIDE=1`` inherited from an operator's
shell would put every score of this provider in TF32 matmuls while its reply, its
manifest and its skill all said fp32. Nothing would refuse; the numbers would simply
be a different model's. So the names are removed from the child, not merely left
unset by us.

**A name is removed by mapping it to ``None``.** ``supervisor._start`` builds the
child's environment as the operator's ``os.environ`` with this function's mapping
applied over it, and ``supervisor.child_env`` deletes any name whose value is
``None``. Returning a pruned COPY of ``os.environ`` removes nothing, because the
supervisor starts from the full environment again: af3_jax's launcher did exactly
that, its stripped names came straight back, and the check that called it verified
(the return value, where a pruned copy looks right) was looking at the wrong layer.
The end-to-end check is to export the names and read ``/proc/<worker pid>/environ``.

The list is read from the kit's own pins (``stock_environment.numerics_must_be_absent``)
rather than copied, with one addition the kit does not name and torch does honour:
``TORCH_ALLOW_TF32_CUBLAS_OVERRIDE`` turns TF32 on for cuBLAS from the environment,
which is the same hazard by a second door.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tooluniverse.remote_resident import kit_launch
from tooluniverse.remote_resident.setup import kit_checkout

# What the kit does not name and torch honours (see the module docstring).
_ALSO_NUMERIC = ("TORCH_ALLOW_TF32_CUBLAS_OVERRIDE",)
# If the pins cannot be read (a checkout the launcher cannot find), this is what
# they say today, so the strip never silently becomes empty.
_FALLBACK = ("NVIDIA_TF32_OVERRIDE",)


def _names_to_remove(manifest) -> List[str]:
    names = list(_FALLBACK)
    checkout = kit_checkout(manifest)
    if checkout is not None:
        pins = Path(checkout) / manifest.kit.get("subdir", "") / "stock" / "PINS.json"
        try:
            doc = json.loads(pins.read_text())
            names = list(
                (doc.get("stock_environment") or {}).get("numerics_must_be_absent")
                or names
            )
        except (OSError, ValueError):
            pass
    return sorted(set(names) | set(_ALSO_NUMERIC))


def build_command(worker) -> Tuple[List[str], Dict[str, Optional[str]]]:
    """``(argv, extra environment)`` for ``worker``. The supervisor calls this."""
    argv, env = kit_launch.build_command(worker)
    env = dict(env)
    for name in _names_to_remove(worker.manifest):
        env[name] = None
    return argv, env
