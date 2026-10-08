"""Change-detection hashes must not depend on where the repo is checked out.

`source_file` holds the absolute path a tool config was loaded from. While it
fed the hash, the stored metadata could never match on another machine, so
the first build in any fresh checkout reported all 2718 tools as changed and
rewrote the whole metadata file.
"""

import pytest

from tooluniverse.build_optimizer import _EXCLUDED_FIELDS, calculate_tool_hash

pytestmark = pytest.mark.unit

CONFIG = {
    "name": "Example_tool",
    "type": "ExampleTool",
    "description": "does a thing",
    "parameter": {"type": "object", "properties": {"q": {"type": "string"}}},
}


def test_source_file_does_not_affect_the_hash():
    here = dict(CONFIG, source_file="/home/alice/repo/src/tooluniverse/data/x.json")
    there = dict(CONFIG, source_file="/build/ci/src/tooluniverse/data/x.json")
    assert calculate_tool_hash(here) == calculate_tool_hash(there)


def test_absent_source_file_hashes_the_same_as_any_path():
    bare = dict(CONFIG)
    with_path = dict(CONFIG, source_file="/anywhere/x.json")
    assert calculate_tool_hash(bare) == calculate_tool_hash(with_path)


def test_a_real_change_still_changes_the_hash():
    """The exclusion must not blunt the detection it exists to serve."""
    before = dict(CONFIG, source_file="/a/x.json")
    after = dict(CONFIG, source_file="/a/x.json", description="does another thing")
    assert calculate_tool_hash(before) != calculate_tool_hash(after)


def test_source_file_is_declared_excluded():
    assert "source_file" in _EXCLUDED_FIELDS
