"""A failure's message is read wherever the tool put it.

Run 37273817054 quoted pypi_package_inspector as "Failed - None": the tool
returns {"status": "error", "data": {"error": ...}}, about 87 return sites in
the package do the same, and the runner only read the top-level "error".
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def _runner():
    spec = importlib.util.spec_from_file_location(
        "tnt_errors", ROOT / "scripts" / "test_new_tools.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("result", "message"),
    [
        ({"status": "error", "error": "top"}, "top"),
        ({"status": "error", "data": {"error": "PyPI API error: 503"}}, "PyPI API error: 503"),
        ({"status": "error", "data": {"message": "inner message"}}, "inner message"),
        ({"status": "error", "message": "outer message"}, "outer message"),
        ({"status": "error", "error": "top", "data": {"error": "inner"}}, "top"),
        ({"status": "error", "data": ["not", "a", "dict"]}, None),
        ({"status": "error"}, None),
    ],
)
def test_error_message_finds_the_message(result, message):
    assert _runner().error_message(result) == message


def test_the_runner_uses_it():
    source = (ROOT / "scripts" / "test_new_tools.py").read_text("utf-8")

    assert "error = error_message(result)" in source
