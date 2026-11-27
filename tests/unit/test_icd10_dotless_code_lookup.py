"""ICD10_get_code_info finds a code written without its dot.

Claims files, HL7 v2 messages and OMOP source values often carry ICD-10-CM
codes without the dot ("E119" for E11.9). NLM Clinical Tables indexes the
dotted form only, so the lookup answered "success" with total 0 for every
dotless code. Measured 2026-11-24 with sf=code:

    E119      0 matches     E11.9      1
    J449      0             J44.9      1
    S72001A   0             S72.001A   1
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.icd_tool import ICD10Tool

pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]


def _tool():
    path = _ROOT / "src/tooluniverse/data/icd_tools.json"
    config = next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "ICD10_get_code_info"
    )
    return ICD10Tool(config)


def _response(code, name):
    response = Mock(status_code=200)
    response.json.return_value = [1, [code], None, [[code, name]]]
    return response


@pytest.mark.parametrize(
    "given, sent",
    [
        ("E119", "E11.9"),
        ("e119", "E11.9"),
        (" J449 ", "J44.9"),
        ("S72001A", "S72.001A"),
        ("E11.9", "E11.9"),
        ("I10", "I10"),
        ("E11", "E11"),
        # strip() and upper() now run on every code, not only the dotless
        # ones, so the dotted and three-character forms have to be pinned in
        # the spellings a claims file actually carries them in.
        ("e11.9", "E11.9"),
        (" E11.9 ", "E11.9"),
        ("i10", "I10"),
        ("c4a0", "C4A.0"),
    ],
)
def test_code_is_sent_in_the_dotted_form(given, sent):
    with patch(
        "tooluniverse.icd_tool.requests.get",
        return_value=_response(sent, "name"),
    ) as get:
        result = _tool().run({"code": given})

    assert get.call_args.args[0].endswith(f"sf=code&terms={sent}")
    assert result["data"]["results"] == [{"code": sent, "name": "name"}]


@pytest.mark.network
def test_live_dotless_code_is_found():
    result = _tool().run({"code": "E119"})

    assert result["status"] == "success"
    assert result["data"]["results"][0]["code"] == "E11.9"
