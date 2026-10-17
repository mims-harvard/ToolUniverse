"""``load_tools(clear_existing=...)``: "load only this" vs "load this as well".

The two intents used to be inferred from ``include_tools``, and one argument
cannot carry both. The consequence was in SMCP, which sets
``self.include_tools = include_tools or []`` and passes that ``[]`` on every
load: the inference read it as "add", so the server's own filters kept
everything a workspace ``profile.yaml`` had loaded when ToolUniverse was
constructed. The same inference is what the compact-mode step relied on to ADD
its discovery categories, so it could not simply be reversed.

Each case here makes the precondition it needs -- a seeded, auto-applied
workspace profile, or an already-loaded category -- because what these guard
only goes wrong when something is already loaded.
"""

import json
from pathlib import Path

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.execute_function import default_tool_files

pytestmark = pytest.mark.unit


def _built_in_json_names():
    """Names the shipped JSON declares: the ones a category selects.

    Tools other tests register in-process with ``@register_tool(config=...)``
    have no category and load whatever the filter says, so only built-in names
    can witness a leak.
    """
    names = set()
    for path in default_tool_files.values():
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, list):
            names.update(t.get("name") for t in data if isinstance(t, dict))
    return names


def _built_ins_outside(tu, prefixes):
    loaded = set(tu.all_tool_dict)
    return sorted(
        name
        for name in (_built_in_json_names() & loaded)
        if not name.startswith(prefixes)
    )


@pytest.fixture
def tu_with_everything_loaded(tmp_path, monkeypatch):
    """An instance whose auto-applied workspace profile loaded the catalogue."""
    monkeypatch.setenv("TOOLUNIVERSE_HOME", str(tmp_path))
    tu = ToolUniverse()
    assert (tmp_path / "profile.yaml").is_file(), "no profile was seeded"
    assert len(tu.all_tool_dict) > 1000, (
        "this precondition is the point of these cases; the profile loaded "
        f"{len(tu.all_tool_dict)} tools"
    )
    return tu


def test_clear_existing_false_adds_to_what_is_loaded(tu_with_everything_loaded):
    """`clear_existing=False` means "as well", whatever the other arguments."""
    tu = tu_with_everything_loaded
    before = len(tu.all_tool_dict)

    tu.load_tools(categories=["opennih"], clear_existing=False)

    assert len(tu.all_tool_dict) >= before, "a request to add removed tools"


def test_clear_existing_true_loads_only_the_named_tools(tu_with_everything_loaded):
    """The shape `load_tools(include_tools=[...])` cannot express on its own."""
    tu = tu_with_everything_loaded
    names = ["UniProt_get_entry_by_accession", "OpenNIH_fetch"]

    tu.load_tools(include_tools=names, clear_existing=True)

    assert set(tu.all_tool_dict) & _built_in_json_names() == set(names)


def test_include_tools_still_merges_when_nothing_is_said(tu_with_everything_loaded):
    """The inferred default is unchanged: include_tools alone still adds."""
    tu = tu_with_everything_loaded
    before = len(tu.all_tool_dict)

    tu.load_tools(include_tools=["UniProt_get_entry_by_accession"])

    assert len(tu.all_tool_dict) >= before


class _FakeServer:
    """Enough of SMCP for the two load helpers, without starting a server."""

    def __init__(self, tu, compact_mode=False):
        self.tooluniverse = tu
        self.exclude_tools = []
        self.exclude_categories = []
        self.include_tools = []  # what SMCP's own constructor produces
        self.tools_file = None
        self.tool_config_files = None
        self.include_tool_types = []
        self.exclude_tool_types = []
        self.compact_mode = compact_mode
        self.tool_finder_available = False
        self.logger = _FakeServer._Logger()

    class _Logger:
        def debug(self, *a, **k):
            pass

        def info(self, *a, **k):
            pass

        def warning(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass


def _server(tu, compact_mode=False):
    """A ``_FakeServer`` carrying SMCP's own two load methods, unmodified.

    Named explicitly rather than inherited from SMCP, so that this stands in
    for no more of the server than the methods under test -- and so that a
    swallowed AttributeError cannot pass for "nothing was loaded", which is
    how an earlier revision of these cases fooled itself.
    """
    smcp = pytest.importorskip("tooluniverse.smcp").SMCP

    class _Server(_FakeServer):
        _load_tools_with_filters = smcp._load_tools_with_filters
        _ensure_compact_mode_categories = smcp._ensure_compact_mode_categories

    return _Server(tu, compact_mode=compact_mode)


def test_smcp_filtered_load_does_not_inherit_the_profile(tu_with_everything_loaded):
    """The server serves what its filters name, not that plus the profile's."""
    tu = tu_with_everything_loaded
    server = _server(tu)

    server._load_tools_with_filters(tool_type=["opennih"])

    assert any(name.startswith("OpenNIH_") for name in tu.all_tool_dict)
    leaked = _built_ins_outside(tu, ("OpenNIH_",))
    assert not leaked, f"{len(leaked)} tools the server was not asked to serve"


def test_smcp_compact_mode_categories_are_added_not_substituted(
    tu_with_everything_loaded,
):
    """Compact mode's discovery categories join the selection, not replace it."""
    tu = tu_with_everything_loaded
    server = _server(tu, compact_mode=True)
    server._load_tools_with_filters(tool_type=["opennih"])

    server._ensure_compact_mode_categories()

    assert any(name.startswith("OpenNIH_") for name in tu.all_tool_dict), (
        "the compact-mode step replaced the server's selection instead of adding to it"
    )
    assert any(name.startswith("Tool_Finder") for name in tu.all_tool_dict), (
        "no tool_finder tool was added"
    )
