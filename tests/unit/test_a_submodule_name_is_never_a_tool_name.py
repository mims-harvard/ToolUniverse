"""
`from tooluniverse import <submodule>` must not pay for a full tool discovery.

Python calls the package's ``__getattr__`` before it imports a submodule, so
``from tooluniverse import http_api_server`` first asks the package for an
attribute named ``http_api_server``. That used to go straight to the tool
registry, which looks a *module* name up as a *tool* name, always misses, and
on the miss runs ``auto_discover_tools(lazy=False)`` -- importing every tool
module in the package -- before Python goes on to import the submodule anyway.
Measured on this tree: 8.16 s for ``from tooluniverse import http_api_server``
against 4.83 s for ``import tooluniverse.http_api_server``, which does not go
through ``__getattr__`` at all.

``__getattr__`` now resolves a submodule as a module first. That is only safe
while the two namespaces stay disjoint, which is what the first test pins:
tool names are class names, submodules are snake_case, so nothing collides
today (0 of 813 registered names is also one of the 644 submodules). Should a
tool ever be registered under a submodule's name, the submodule would shadow
it silently -- the first test is what turns that into a failure instead.
"""

import json
import pkgutil
import subprocess
import sys

import tooluniverse
from tooluniverse.tool_registry import auto_discover_tools


def _submodule_names() -> set:
    return {m.name for m in pkgutil.iter_modules(tooluniverse.__path__)}


def test_no_submodule_name_is_also_a_tool_name():
    submodules = _submodule_names()
    assert submodules, "no submodules found under tooluniverse.__path__"

    registered = set(auto_discover_tools(lazy=True))
    assert registered, "the lazy tool registry is empty"

    collisions = sorted(submodules & registered)
    assert not collisions, (
        "these names are both a tooluniverse submodule and a registered tool: "
        f"{collisions}. The package's __getattr__ resolves submodules before "
        "tools, so each of these tools has become unreachable as "
        "`from tooluniverse import <name>`. Rename the tool, or give the "
        "registry precedence back for these specific names."
    )


_CHILD = """
import json, pkgutil
import tooluniverse
from tooluniverse import tool_registry

bound = set(vars(tooluniverse))
available = {m.name for m in pkgutil.iter_modules(tooluniverse.__path__)}
candidates = [
    n
    for n in ("http_utils", "url_tool", "http_api_server")
    if n in available and n not in bound
]

out = {"candidates": candidates}
if len(candidates) >= 2:
    # The statement itself, not a stand-in: `from tooluniverse import <name>`
    # calls __getattr__ first and only falls back to the import machinery if
    # that raises AttributeError.
    ns = {}
    exec("from tooluniverse import " + candidates[0], ns)
    out["imported"] = getattr(ns[candidates[0]], "__name__", None)
    out["discovery_completed"] = tool_registry._discovery_completed

    # getattr() has no such fallback, so on a name __getattr__ does not
    # resolve it fails outright while the import statement succeeds. Use a
    # second, still-cold name: the first is now bound on the package by the
    # import above, which would mask the difference.
    try:
        out["getattr_ok"] = getattr(
            tooluniverse, candidates[1]
        ).__name__ == "tooluniverse." + candidates[1]
    except AttributeError as exc:
        out["getattr_ok"] = False
        out["getattr_error"] = str(exc)

# Full discovery registers a different set from the AST scan the first test
# reads, so check that one for collisions too. Safe to run here: this process
# is thrown away, so the eager import of every tool module does not leak into
# the rest of the suite.
full = set(tool_registry.auto_discover_tools(lazy=False))
out["full_registry_size"] = len(full)
out["full_collisions"] = sorted(full & available)
print("RESULT " + json.dumps(out))
"""


def test_importing_a_submodule_does_not_trigger_full_discovery():
    result = subprocess.run(
        [sys.executable, "-c", _CHILD],
        capture_output=True,
        text=True,
        timeout=180,
    )
    line = next(
        (ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")),
        None,
    )
    assert line, (
        "the child process produced no result.\n"
        f"returncode={result.returncode}\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    out = json.loads(line[len("RESULT ") :])

    assert len(out["candidates"]) >= 2, (
        "fewer than two candidate modules are still lazy -- "
        "tooluniverse/__init__.py now imports them eagerly, so this test can "
        "no longer observe the __getattr__ path. Point it at submodules that "
        "are still lazy."
    )
    first, second = out["candidates"][0], out["candidates"][1]

    assert out["imported"] == f"tooluniverse.{first}"
    assert out["discovery_completed"] is False, (
        f"`from tooluniverse import {first}` ran a full tool discovery. "
        "__getattr__ is looking the module name up as a tool name before "
        "resolving it as a module; that import costs ~3.3 s more than it "
        "needs to."
    )
    assert out["getattr_ok"], (
        f"getattr(tooluniverse, {second!r}) does not return the submodule, "
        f"although `from tooluniverse import {second}` does: "
        f"{out.get('getattr_error', out['getattr_ok'])!r}. The import "
        "statement falls back to the import machinery when __getattr__ "
        "raises; getattr does not, so the two forms must not disagree."
    )

    assert out["full_registry_size"], "full discovery registered no tools"
    assert not out["full_collisions"], (
        "these names are both a tooluniverse submodule and a tool registered "
        f"by full discovery: {out['full_collisions']}"
    )
