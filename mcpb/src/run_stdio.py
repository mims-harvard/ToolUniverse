#!/usr/bin/env python3
"""Entry point for ToolUniverse MCP Server (stdio transport for Claude Desktop).

This wrapper calls run_stdio_server with compact mode enabled.
Compact mode exposes only 5 core tools (list_tools, grep_tools, get_tool_info, execute_tool, find_tools)
while loading all 764+ tools in the background for execute_tool to access.
This prevents context window overflow from the massive tool list.
"""

import os
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
def _refresh_tooluniverse(timeout_seconds=8, http_timeout_seconds="3"):
    bundle_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.environ.get("TOOLUNIVERSE_SKIP_SELF_UPDATE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return

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
        if time.time() - os.path.getmtime(stamp) < interval_hours * 3600:
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
                "uv",
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
            detail = (completed.stderr or completed.stdout or "").strip()
            detail = detail[-500:].replace("\n", " ")
            print(
                "ToolUniverse stayed on the installed version: the update could "
                f"not be applied ({detail})",
                file=sys.stderr,
            )
    except subprocess.TimeoutExpired:
        print(
            "ToolUniverse update check timed out; keeping the installed version",
            file=sys.stderr,
        )
    except Exception as exc:  # noqa: BLE001 - never fatal, this is opportunistic
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
