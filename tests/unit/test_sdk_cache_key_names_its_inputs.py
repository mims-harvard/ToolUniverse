"""The SDK cache key has to name everything the wrappers come from.

`Cache SDK generation` restores all of `src/tooluniverse/tools` from a key
built with `hashFiles`. Whatever the key leaves out can change without
invalidating the cache, and then a restore serves the previous run's wrappers
over the ones the commit carries -- the suite tests the cache instead of the
branch.

That is not hypothetical. The key named `scripts/build_tools.py`, a 51-line
shim whose whole body is `from tooluniverse.generate_tools import main`. A
change to the generator that widened 235 return annotations therefore left the
key untouched, the stale tree came back over 235 committed files, and
`Generate SDK` (which runs without `--force`) found every config hash unchanged
and rewrote nothing. The only reason it surfaced at all is that the branch
added a test which reads the wrappers off disk.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"

# Every file the generated wrappers are a function of. `build_tools.py` is the
# entry point, `generate_tools.py` writes the files, `build_optimizer.py`
# decides which tools count as changed, and the configs are the input.
GENERATOR_INPUTS = (
    "scripts/build_tools.py",
    "src/tooluniverse/generate_tools.py",
    "src/tooluniverse/build_optimizer.py",
    "src/tooluniverse/data/*.json",
)


def _sdk_cache_key() -> str:
    text = WORKFLOW.read_text("utf-8")
    # the cache step whose path is the generated wrapper tree
    block = re.search(r"path:\s*src/tooluniverse/tools\s*\n\s*key:\s*(?P<key>.+)", text)
    assert block, "no cache step for src/tooluniverse/tools in tests.yml"
    return block.group("key")


@pytest.mark.parametrize("dependency", GENERATOR_INPUTS)
def test_the_key_names_every_generator_input(dependency):
    assert dependency in _sdk_cache_key(), (
        f"{dependency} can change without invalidating the wrapper cache, so a "
        "restore would serve wrappers generated before that change"
    )


def test_the_generator_entry_point_is_only_a_shim():
    """Why hashing build_tools.py alone was never enough.

    If this file ever grows real generation logic, the comment in the workflow
    and the reasoning above stop being true and should be revisited.
    """
    shim = (ROOT / "scripts" / "build_tools.py").read_text("utf-8")

    assert "from tooluniverse.generate_tools import main" in shim
    assert len(shim.splitlines()) < 120, (
        "build_tools.py is no longer a thin shim; re-check what the cache key "
        "has to name"
    )
