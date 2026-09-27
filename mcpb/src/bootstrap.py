#!/usr/bin/env python3
"""Repair a lock left ahead of the environment, then start the server.

The launcher's daily update runs ``uv sync --upgrade-package tooluniverse``,
and uv writes uv.lock before it installs. src/run_stdio.py snapshots the lock
and puts it back if the sync reports failure, which covers every ordinary
error -- but not this process being killed inside the gap. Measured on the real
bundle by watching the lock's mtime and killing the process group 0.2 s after
it moved: both SIGTERM and SIGKILL leave lock=1.5.3 with 1.4.1 installed. The
next launch is ``--frozen``, so it has to reach the newer release, and offline
with a cold cache uv refuses and the extension never starts.

That repair cannot live in run_stdio.py: uv brings the environment up to the
lock before running it, so on the broken launch it never executes. This file
runs first instead, under ``uv run --no-project``, which needs no environment
at all -- measured at 30 ms. The killed run always leaves the snapshot behind,
so its presence is the signal, and putting it back is the whole repair.

Restoring is safe in the other case too. If the kill landed after the install
succeeded but before the snapshot was removed, the restore points the lock at
the version that is still cached, the next sync installs it from there, and
the upgrade happens again at the next check.
"""

import os
import shutil
import sys

BUNDLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_PIN = "3.12"


def _repair_lock():
    snapshot = os.path.join(BUNDLE, "uv.lock.pre-update")
    if not os.path.exists(snapshot):
        return
    try:
        os.replace(snapshot, os.path.join(BUNDLE, "uv.lock"))
        print(
            "ToolUniverse: an interrupted update left uv.lock ahead of the "
            "installed version; restored it.",
            file=sys.stderr,
        )
    except OSError as exc:  # pragma: no cover - read-only install
        print(f"ToolUniverse: could not restore uv.lock ({exc})", file=sys.stderr)


def main():
    _repair_lock()
    # uv exports its own absolute path to children, so this is the same binary
    # that started us; PATH is only a fallback.
    uv = os.environ.get("UV") or shutil.which("uv") or "uv"
    argv = [
        uv,
        "run",
        "--python",
        PYTHON_PIN,
        "--frozen",
        "--directory",
        BUNDLE,
        os.path.join("src", "run_stdio.py"),
    ]
    # Replace this process, so the server owns stdio directly and no wrapper
    # sits between Desktop and the protocol.
    try:
        os.execvp(uv, argv)
    except OSError as exc:
        print(f"ToolUniverse could not start: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
