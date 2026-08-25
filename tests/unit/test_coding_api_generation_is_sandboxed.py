"""The integration suite must not regenerate the committed wrapper tree.

tests/integration/test_coding_api_integration.py calls generate_tools() whose
default output directory is src/tooluniverse/tools/ -- the tracked wrapper
tree. Running the integration suite therefore rewrote 2,604 tracked files as a
side effect, which is indistinguishable from a real change in `git status` and
has already cost a fix round. Each call site allocates a temp dir; this guards
that they actually use it.
"""

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

pytestmark = pytest.mark.unit

TARGET = Path(__file__).parent.parent / "integration" / "test_coding_api_integration.py"


def test_every_generate_tools_call_passes_an_output_dir():
    tree = ast.parse(TARGET.read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "generate_tools"
    ]

    assert calls, "expected the integration test to exercise generate_tools"
    for call in calls:
        keywords = {kw.arg for kw in call.keywords}
        assert "output_dir" in keywords, (
            f"generate_tools() at line {call.lineno} would write into the "
            "committed src/tooluniverse/tools/ tree"
        )
