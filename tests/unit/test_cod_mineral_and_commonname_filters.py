"""COD_search_structures: `mineral` and `commonname` did nothing useful.

COD's server ignores both parameters: alone they match no record (`mineral=calcite`
-> []), and combined with an element filter they are dropped so every structure
with that element comes back (`mineral=Quartz&el1=Si` -> 51 MB). The tool now
runs a free-text search and keeps rows whose own mineral/commonname field
contains the value.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

ROWS = [
    {"file": "1", "mineral": "Nitrocalcite", "commonname": None},
    {"file": "2", "mineral": "Calcite", "commonname": None},
    {"file": "3", "mineral": None, "commonname": "Aspirin form II"},
    {"file": "4", "mineral": "Quartz low", "commonname": None},
]


def _run(arguments):
    from tooluniverse.cod_tool import CODTool

    tool = CODTool({"name": "COD_search_structures", "fields": {"endpoint": "x"}})
    seen = {}

    def fake_run(self, args):
        seen.update(args)
        return {"status": "success", "data": list(ROWS), "count": len(ROWS)}

    with patch("tooluniverse.cod_tool.BaseRESTTool.run", fake_run):
        return tool.run(arguments), seen


def test_mineral_becomes_text_search_and_filters_rows():
    result, sent = _run({"mineral": "Calcite"})
    assert sent == {"text": "calcite"}
    assert [r["file"] for r in result["data"]] == ["1", "2"]
    assert result["count"] == 2
    assert "mineral" in result["note"]


def test_commonname_filters_on_the_commonname_field():
    result, sent = _run({"commonname": "aspirin"})
    assert sent == {"text": "aspirin"}
    assert [r["file"] for r in result["data"]] == ["3"]


def test_mineral_is_not_forwarded_when_combined_with_other_filters():
    result, sent = _run({"mineral": "quartz", "el1": "Si", "results": 5})
    assert "mineral" not in sent
    assert sent["el1"] == "Si"
    assert [r["file"] for r in result["data"]] == ["4"]


def test_explicit_text_is_kept_and_result_limit_applies_after_filtering():
    result, sent = _run({"mineral": "calcite", "text": "carbonate", "results": 1})
    assert sent == {"text": "carbonate"}
    assert [r["file"] for r in result["data"]] == ["1"]
    assert result["total_before_limit"] == 2


def test_no_name_filter_leaves_results_untouched():
    result, _ = _run({"text": "aspirin"})
    assert len(result["data"]) == 4
    assert "note" not in result
