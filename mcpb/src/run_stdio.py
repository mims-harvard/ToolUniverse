#!/usr/bin/env python3
"""Entry point for ToolUniverse MCP Server (stdio transport for Claude Desktop).

Compact mode exposes five tools -- list_tools, grep_tools, get_tool_info,
find_tools and execute_tool -- and keeps the whole catalogue (2,700+ tools)
behind execute_tool. Exposing them all would overflow the context window before
the conversation started.

The bundle carries no ToolUniverse source: mcpb/pyproject.toml declares it and
uv installs it, so a release reaches users without a new submission to the
extensions directory. This file is therefore the only code that ships.
"""

import os
import shutil
import subprocess
import sys
import time

# Claude Desktop substitutes every ``${user_config.*}`` entry in the manifest's
# env block, including the ones the user left blank. An empty string still
# counts as "set" to os.environ, and ToolUniverse loads its .env files with
# override=False, so a blank field would shadow a key the user had already put
# in ~/.tooluniverse/.env and silently disable those tools. Drop anything that
# arrived empty, and anything that arrived as an unexpanded placeholder.
for _name, _value in list(os.environ.items()):
    if _value == "" or _value.startswith("${user_config."):
        del os.environ[_name]

# Optional escape hatch for the keys that have no field of their own: point
# TOOLUNIVERSE_ENV_FILE at a .env file and its entries are loaded here, before
# ToolUniverse reads anything. Existing environment variables still win, which
# matches how the package treats its own .env files.
_env_file = os.environ.get("TOOLUNIVERSE_ENV_FILE", "").strip()
if _env_file and os.path.isfile(_env_file):
    try:
        with open(_env_file, encoding="utf-8") as _handle:
            for _line in _handle:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _key, _, _val = _line.partition("=")
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key and _val and _key not in os.environ:
                    os.environ[_key] = _val
    except OSError as _exc:  # pragma: no cover - unreadable file, keep starting
        print(f"Could not read TOOLUNIVERSE_ENV_FILE: {_exc}", file=sys.stderr)


# Pick up a published ToolUniverse release, without letting the network decide
# whether the server starts.
#
# The obvious way to do this is --upgrade-package on the launch command itself,
# and it is wrong: uv then has to reach the index before it runs anything, so an
# unreachable index stops a bundle that was already installed and working.
# Measured with a blackholed index: the launch failed after 49 s, which Desktop
# shows as "Server disconnected" -- the symptom this bundle exists to avoid.
#
# So the refresh happens here instead, bounded and optional. It runs before the
# first tooluniverse import, so replacing files under site-packages is safe, and
# any failure -- offline, hung proxy, index outage, uv missing -- leaves the
# installed version in place and the server starts anyway. A release therefore
# arrives at the first launch with a working network rather than never.
def _hold_update_lock(path, wait_seconds, stale_seconds=60.0):
    """Take the update lock, or wait for whoever has it and report failure.

    Two clients can share one install -- the extension in Desktop and a
    `claude mcp add` pointing at the same directory -- and they start
    independently. Without this, the second process reads the stamp the first
    one just wrote, decides an update is not due, and walks straight into a
    site-packages tree that `uv sync` is in the middle of replacing. Measured:
    one of two simultaneous launches died with dozens of "Error reading
    .../tooluniverse/<module>.py: No such file or directory" while the other
    upgraded 1.4.1 to 1.5.3 successfully.

    So the wait has to happen before the stamp is consulted, not after. A
    caller that does not get the lock has still waited for the tree to settle,
    which is the part that matters; skipping its own check costs nothing,
    because the process it waited for just did it.
    """
    deadline = time.time() + wait_seconds
    while True:
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            pass
        except OSError:
            # Nowhere to put a lock, so no safe way to update. A read-only
            # bundle directory lands here, and it could not be synced anyway.
            return False
        else:
            try:
                os.write(handle, str(os.getpid()).encode("ascii"))
            finally:
                os.close(handle)
            return True

        # A process killed mid-update leaves the file behind. Without this the
        # install would never update again. abs() for the same reason as the
        # stamp: a clock that moved backwards must not make it look recent.
        try:
            if abs(time.time() - os.path.getmtime(path)) > stale_seconds:
                os.remove(path)
                continue
        except OSError:
            continue

        if time.time() >= deadline:
            return False
        time.sleep(0.2)


def _refresh_tooluniverse(timeout_seconds=8, http_timeout_seconds="3"):
    bundle_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.environ.get("TOOLUNIVERSE_SKIP_SELF_UPDATE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return

    # Wait a little longer than the sync is allowed to take, so a launch that
    # collides with one still sees a settled tree afterwards.
    update_lock = os.path.join(bundle_dir, ".update.lock")
    if not _hold_update_lock(update_lock, wait_seconds=timeout_seconds + 2):
        return
    try:
        _refresh_locked(bundle_dir, timeout_seconds, http_timeout_seconds)
    finally:
        try:
            os.remove(update_lock)
        except OSError:
            pass


def _refresh_locked(bundle_dir, timeout_seconds, http_timeout_seconds):
    """The update itself, with the update lock held."""
    # Check at most once a day. Releases do not arrive hourly, and the cost of
    # checking is only ever paid by the launch that checks: on a machine that
    # cannot reach the index that is the difference between every launch waiting
    # out the timeout and one launch a day doing so.
    stamp = os.path.join(bundle_dir, ".last-update-check")
    try:
        interval_hours = float(
            os.environ.get("TOOLUNIVERSE_UPDATE_INTERVAL_HOURS", "24")
        )
    except ValueError:
        interval_hours = 24.0
    try:
        # abs(), because a clock that moved backwards leaves a stamp dated in
        # the future, and a plain subtraction would then read as "checked
        # moments ago" for as long as the clock takes to catch up -- switching
        # updates off without saying so.
        if abs(time.time() - os.path.getmtime(stamp)) < interval_hours * 3600:
            return
    except OSError:
        pass  # never checked, or the stamp is unreadable: check now
    try:
        with open(stamp, "w", encoding="utf-8") as handle:
            handle.write(str(int(time.time())))
    except OSError:
        # A read-only bundle directory means no stamp and therefore a check on
        # every launch. That is the bounded path below, so it stays safe.
        pass
    # Two bounds, because they fail differently: uv's own HTTP timeout ends a
    # hanging connection, and the process timeout covers anything uv does not
    # bound itself. Both are small on purpose -- an update that cannot finish
    # quickly is simply retried at the next launch, while a startup that waits
    # is a startup the user experiences as broken. Measured against a
    # blackholed index: 26 s with a single 25 s bound, ~4 s with these.
    child_env = dict(os.environ)
    child_env.setdefault("UV_HTTP_TIMEOUT", http_timeout_seconds)
    # Use the uv that launched this process rather than whatever PATH offers.
    # `uv run` exports its own absolute path as UV, and Desktop may well invoke
    # uv by absolute path with a PATH that does not contain it -- in which case
    # looking up "uv" fails with FileNotFoundError and the bundle never updates
    # again, quietly, for the life of the install. Verified: with uv removed
    # from PATH the check used to be skipped; with UV it runs.
    uv_binary = os.environ.get("UV") or shutil.which("uv") or "uv"

    # Keep uv.lock describing something that is actually installed.
    #
    # `uv sync` resolves and writes the lock *before* it installs, so a sync
    # that dies partway leaves the lock naming the new release while the
    # environment still holds the old one. The launch command is `--frozen`, so
    # the next start has to make the environment match that lock -- and if the
    # machine is offline and the new wheels are not cached, it cannot, and uv
    # refuses to run. A bundle that worked offline a minute ago is then dead,
    # showing the "Server disconnected" this design exists to avoid. Verified
    # end to end: with the lock at 1.5.3, the venv at 1.4.1 and an empty cache,
    # an offline launch fails with "Network connectivity is disabled, but the
    # requested data wasn't found in the cache".
    #
    # The kill window is not narrow. uv writes the lock within a second or two
    # of starting, and the process bound below is 8 s; a slow connection, a
    # sleeping laptop, a full disk or a scanner holding a file open all land in
    # it. Verified by making the venv unwritable: the install failed and the
    # lock had already moved to 1.5.3.
    #
    # So snapshot the lock and put it back unless the sync reports success.
    #
    # What this cannot cover is this whole process being killed between uv's
    # write and the restore below -- power loss, the OOM killer, Desktop
    # stopping the server. That window is one call wide, where before the fix
    # every ordinary sync failure left the install poisoned. It cannot be
    # closed from here: uv brings the environment up to the lock before this
    # file is executed, so on the next launch there is no code of ours left to
    # run. Verified -- with a leftover snapshot in place and the lock ahead of
    # the venv, an offline launch still fails inside uv.
    #
    # The same ordering says a leftover snapshot is always stale: if this code
    # is running, uv already satisfied the current lock, so the lock is
    # installed and the older copy describes nothing worth going back to.
    # Restoring it would downgrade a working environment and then upgrade it
    # again on the next check. Drop it instead.
    lock_path = os.path.join(bundle_dir, "uv.lock")
    lock_snapshot = os.path.join(bundle_dir, "uv.lock.pre-update")

    def _restore_lock():
        try:
            os.replace(lock_snapshot, lock_path)
        except OSError:
            pass

    try:
        os.remove(lock_snapshot)
    except OSError:
        pass
    try:
        shutil.copy2(lock_path, lock_snapshot)
    except OSError as exc:
        # Without a snapshot there is no way back, so do not start. The reasons
        # a copy fails here -- no disk, no write permission -- are the same ones
        # that would strand the sync halfway.
        print(
            f"ToolUniverse update check skipped: cannot protect uv.lock ({exc})",
            file=sys.stderr,
        )
        return
    # Report a refused update rather than swallowing it. A release can be
    # uninstallable here for reasons the user cannot guess: it may require a
    # newer Python than the 3.12 this bundle pins, or pull a dependency with no
    # wheel for their platform. Silently staying on the old version would look
    # like the update mechanism working. stderr is the MCP log channel, so the
    # reason lands in Desktop's logs; stdout must stay clean because the
    # protocol runs over it.
    try:
        completed = subprocess.run(
            [
                uv_binary,
                "sync",
                "--python",
                "3.12",
                "--upgrade-package",
                "tooluniverse",
                "--directory",
                bundle_dir,
            ],
            timeout=timeout_seconds,
            env=child_env,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            _restore_lock()
            detail = (completed.stderr or completed.stdout or "").strip()
            detail = detail[-500:].replace("\n", " ")
            print(
                "ToolUniverse stayed on the installed version: the update could "
                f"not be applied ({detail})",
                file=sys.stderr,
            )
        else:
            try:
                os.remove(lock_snapshot)
            except OSError:
                pass
    except subprocess.TimeoutExpired:
        _restore_lock()
        print(
            "ToolUniverse update check timed out; keeping the installed version",
            file=sys.stderr,
        )
    except Exception as exc:  # noqa: BLE001 - never fatal, this is opportunistic
        _restore_lock()
        print(f"ToolUniverse update check skipped: {exc}", file=sys.stderr)


def _report_running_version():
    """Name the version in the log, so a support question has an answer.

    Desktop shows the bundle's manifest version, which is the launcher's, not
    the library's -- the two diverge by design as soon as the first update
    lands.
    """
    try:
        from importlib.metadata import version

        print(f"ToolUniverse {version('tooluniverse')}", file=sys.stderr)
    except Exception:  # noqa: BLE001 - a log line is never worth failing over
        pass


_refresh_tooluniverse()
_report_running_version()

# Enable compact mode by default
sys.argv = [
    sys.argv[0],
    "--compact-mode",
]

from tooluniverse.smcp_server import run_stdio_server  # noqa: E402

if __name__ == "__main__":
    run_stdio_server()
