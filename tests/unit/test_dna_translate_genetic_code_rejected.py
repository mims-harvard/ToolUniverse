"""Regression guard: DNA_translate_reading_frames declared a `genetic_code`
parameter but never read it -- every request was translated with the standard
NCBI code 1 table. Asking for code 2 (vertebrate mitochondrial) on
"ATGTGATTAAGATAA" returned the standard-code protein "M*LR*" with
status=success, instead of the code-2 protein "MWL**" (TGA = Trp, AGA = stop).
Only code 1 is implemented, so a non-standard code is now rejected at input
rather than silently answered with the wrong table.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.scientific_calculator_tools import ScientificCalculatorTool

pytestmark = pytest.mark.unit

_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "scientific_calculator_tools.json"
)


def _tool():
    return ScientificCalculatorTool(
        {
            "name": "DNA_translate_reading_frames",
            "type": "ScientificCalculatorTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _run(**extra):
    args = {
        "operation": "translate_reading_frames",
        "sequence": "ATGTGATTAAGATAA",
    }
    args.update(extra)
    return _tool().run(args)


@pytest.mark.parametrize("code", [2, 3, 11, 0, -1])
def test_non_standard_genetic_code_is_rejected(code):
    result = _run(genetic_code=code)
    assert result["status"] == "error"
    error = result["error"]
    # The message must name the supplied value and say what is supported.
    assert str(code) in error
    assert "genetic code 1" in error
    assert "frames" not in result


def test_rejection_message_is_actionable():
    error = _run(genetic_code=2)["error"]
    assert "mitochondrial" in error
    assert "Omit genetic_code or pass 1" in error


@pytest.mark.parametrize("code", [1, None])
def test_standard_code_and_omitted_code_still_translate(code):
    result = _run(genetic_code=code)
    assert result["status"] == "success"
    assert result["data"]["frames"]["frame_1"]["protein"] == "M*LR*"


def test_absent_genetic_code_still_translates():
    result = _run()
    assert result["status"] == "success"
    assert result["data"]["frames"]["frame_1"]["protein"] == "M*LR*"


def test_config_declares_only_the_supported_code():
    configs = json.loads(_CONFIG_PATH.read_text())
    tool = next(c for c in configs if c["name"] == "DNA_translate_reading_frames")
    prop = tool["parameter"]["properties"]["genetic_code"]
    # The declared interface must match what the implementation can honour, so
    # schema validation rejects a non-standard code before it reaches the tool.
    assert prop["enum"] == [1, None]
