"""A workspace ``profile.yaml`` must not disable ``load_tools()``'s filters.

ToolUniverse seeds ``.tooluniverse/profile.yaml`` from its own shipped default
the first time it sees a workspace, and auto-applies it at construction -- so a
fresh instance has the whole catalogue loaded before the caller asks for
anything. That default carries ``include_tools: []``, and the Profile-defaults
block turned the omitted argument into ``[]`` rather than ``None`` while the
full-reload branch tested for ``None``. The reload was therefore skipped and a
later ``load_tools(categories=[...])`` added to what the profile had loaded
instead of replacing it: every category filter returned all ~2.7k tools, and
``exclude_categories`` excluded nothing.

Nothing caught it because the leak needs a workspace profile to exist, and a
clean checkout has none. These cases make one.
"""

import json
from pathlib import Path

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.execute_function import default_tool_files

pytestmark = pytest.mark.unit


def _built_in_json_names():
    """Names the shipped JSON declares, which are the ones a category selects.

    Tools other tests register in-process with ``@register_tool(config=...)``
    have no category and load whatever the filter says, so only built-in names
    can witness a leak. A whole-suite run is where that distinction shows up.
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


@pytest.fixture
def tu_with_workspace_profile(tmp_path, monkeypatch):
    """An instance whose workspace profile has already loaded everything."""
    monkeypatch.setenv("TOOLUNIVERSE_HOME", str(tmp_path))
    tu = ToolUniverse()
    assert (tmp_path / "profile.yaml").is_file(), "no profile was seeded"
    assert len(tu.all_tool_dict) > 1000, (
        "this case is only meaningful if the auto-applied profile loaded the "
        f"catalogue first; it loaded {len(tu.all_tool_dict)}"
    )
    return tu


def test_category_filter_replaces_what_the_workspace_profile_loaded(
    tu_with_workspace_profile,
):
    tu = tu_with_workspace_profile
    tu.load_tools(categories=["opennih"])

    names = set(tu.all_tool_dict)
    assert any(name.startswith("OpenNIH_") for name in names), (
        "the filtered load returned none of the category it asked for"
    )
    leaked = sorted(
        (_built_in_json_names() & names)
        - {name for name in names if name.startswith("OpenNIH_")}
    )
    assert not leaked, (
        f"{len(leaked)} built-in tools outside the category: {leaked[:10]}"
    )


def test_exclude_categories_is_not_undone_by_the_workspace_profile(
    tu_with_workspace_profile,
):
    tu = tu_with_workspace_profile
    tu.load_tools(categories=["opennih", "gtex"], exclude_categories=["gtex"])

    assert not [name for name in tu.all_tool_dict if name.startswith("GTEx_")]
