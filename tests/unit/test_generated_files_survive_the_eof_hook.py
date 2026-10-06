"""Generated files end with a newline, so the end-of-file-fixer hook keeps them.

.tool_metadata.json was written without one. The pre-commit hook added it on
commit and the next build took it away, so every PR that added a tool (#749,
#750, #757) carried a one-byte drift against the generator's own output.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.build_optimizer import load_metadata, save_metadata

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def test_save_metadata_ends_with_a_newline(tmp_path):
    path = tmp_path / ".tool_metadata.json"

    save_metadata({"b": "2", "a": "1"}, path)

    text = path.read_text("utf-8")
    assert text.endswith("}\n") and not text.endswith("\n\n")
    assert load_metadata(path) == {"a": "1", "b": "2"}


@pytest.mark.parametrize(
    "relative",
    [
        "src/tooluniverse/tools/.tool_metadata.json",
        "src/tooluniverse/tools/__init__.py",
        "src/tooluniverse/_lazy_registry_static.py",
    ],
)
def test_committed_generated_files_end_with_one_newline(relative):
    text = (ROOT / relative).read_text("utf-8")

    assert text.endswith("\n") and not text.endswith("\n\n"), relative


def test_the_committed_metadata_is_what_the_generator_writes(tmp_path):
    committed = ROOT / "src" / "tooluniverse" / "tools" / ".tool_metadata.json"
    rewritten = tmp_path / "m.json"

    save_metadata(json.loads(committed.read_text("utf-8")), rewritten)

    assert rewritten.read_bytes() == committed.read_bytes()
