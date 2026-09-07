"""Shared helpers for the three case-study reproduction scripts.

Keeps the case-study scripts readable: they should read as the ordered list of
tool calls the AI scientist made, not as plumbing.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

from tooluniverse import ToolUniverse

# Loading all ~2,700 tools takes a while and none of the case studies need more
# than these categories. Together they supply every tool the three cases call.
CASE_STUDY_CATEGORIES = [
    "opentarget",
    "clinvar",
    "genebe",
    "alphafold",
    "pdbe_graph",
    "pubchem",
    "admetai",
    "ChEMBL",
    "compose",
    "EuropePMC",
    "clinical_trial_stats",
]


def load_universe(categories: Iterable[str] | None = None) -> ToolUniverse:
    """Return a ToolUniverse with just the categories the case studies need."""
    tu = ToolUniverse()
    tu.load_tools(list(categories or CASE_STUDY_CATEGORIES))
    return tu


def call(tu: ToolUniverse, tool_name: str, /, **arguments: Any) -> Any:
    """Run one tool and return its payload, unwrapping the status envelope.

    Tools return either ``{"status": "success", "data": ...}`` or a bare value.
    Errors are returned rather than raised so a single unavailable upstream
    service does not abort the whole case study.

    ``tool_name`` is positional-only so that tools taking a ``name`` argument
    (e.g. ``PubChem_get_CID_by_compound_name``) can still be called as
    ``call(tu, "...", name="ML216")``.
    """
    result = tu.run({"name": tool_name, "arguments": arguments})
    if isinstance(result, dict):
        if result.get("status") == "error":
            return {"__error__": result.get("error", "unknown error")}
        if "data" in result and result.get("status") == "success":
            return result["data"]
    return result


def is_error(payload: Any) -> bool:
    return isinstance(payload, dict) and "__error__" in payload


def step(number: int | str, title: str) -> None:
    print(f"\n[{number}] {title}")
    print("-" * 72)


def report(label: str, observed: Any, published: Any = None) -> None:
    """Print one observed value, and the published value when there is one."""
    if published is None:
        print(f"  {label}: {observed}")
    else:
        print(f"  {label}: {observed}   (published: {published})")


def note_unavailable(tool: str, payload: Any) -> None:
    """Report a step that could not run, without dumping an HTML error page."""
    message = " ".join(str(payload["__error__"]).split())
    if len(message) > 160:
        message = message[:160] + " ..."
    print(f"  [unavailable] {tool}: {message}")
    print("  This step depends on a live external service; see README.md.")


def header(title: str, question: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)
    print(f"Question: {question}")


def footer(lines: Dict[str, str]) -> None:
    print("\n" + "=" * 72)
    print("Result")
    print("=" * 72)
    for key, value in lines.items():
        print(f"  {key}: {value}")
