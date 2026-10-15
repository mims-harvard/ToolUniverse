"""OmniPath_get_tf_target_interactions' confidence_level filter never filtered anything.

OmniPath only includes a field in its response when it is named in the request's
``fields`` parameter; the tool never asked for ``dorothea_level``, so
``item.get("dorothea_level")`` was always None and the "only apply the filter when
dorothea_level is truthy" guard skipped every row. The API also answers
``dorothea_level`` as a list of letters, not a single string (a TF-target pair can
have evidence at more than one confidence level, e.g. ["A", "D"], confirmed live
for TP53), so a naive `dorothea_level != confidence_level` fix would still never
match.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

ROWS = [
    {
        "source": "P1",
        "target": "T1",
        "source_genesymbol": "TP53",
        "target_genesymbol": "A",
        "dorothea_level": ["A"],
        "sources": ["CollecTRI"],
        "curation_effort": 5,
    },
    {
        "source": "P1",
        "target": "T2",
        "source_genesymbol": "TP53",
        "target_genesymbol": "B",
        "dorothea_level": ["A", "D"],
        "sources": ["CollecTRI"],
        "curation_effort": 3,
    },
    {
        "source": "P1",
        "target": "T3",
        "source_genesymbol": "TP53",
        "target_genesymbol": "C",
        "dorothea_level": ["D"],
        "sources": ["CollecTRI"],
        "curation_effort": 2,
    },
    {
        "source": "P1",
        "target": "T4",
        "source_genesymbol": "TP53",
        "target_genesymbol": "D",
        "dorothea_level": [],
        "sources": ["CollecTRI"],
        "curation_effort": 1,
    },
]


def _run(arguments):
    from tooluniverse.omnipath_tool import OmniPathTool

    tool = OmniPathTool(
        {
            "name": "OmniPath_get_tf_target_interactions",
            "fields": {"endpoint": "tf_target"},
        }
    )
    sent = {}

    def fake_request(self, path, params):
        sent.update(params)
        return list(ROWS)

    with patch.object(OmniPathTool, "_make_request", fake_request):
        return tool.run(arguments), sent


def test_dorothea_level_is_requested_as_an_output_field():
    _, sent = _run({"tf_gene": "TP53"})
    assert "dorothea_level" in sent["fields"].split(",")


def test_confidence_level_a_excludes_rows_whose_level_list_lacks_a():
    result, _ = _run({"tf_gene": "TP53", "confidence_level": "A"})
    # A and B declare level A; C declares only D and is excluded; D (row
    # target_genesymbol "D") declares no level at all and passes through.
    assert {row["target_genesymbol"] for row in result["data"]} == {"A", "B", "D"}


def test_confidence_level_d_excludes_rows_that_declare_only_a():
    result, _ = _run({"tf_gene": "TP53", "confidence_level": "D"})
    assert {row["target_genesymbol"] for row in result["data"]} == {"B", "C", "D"}


def test_rows_with_no_declared_level_always_pass_through():
    result_no_filter, _ = _run({"tf_gene": "TP53"})
    assert {row["target_genesymbol"] for row in result_no_filter["data"]} == {
        "A",
        "B",
        "C",
        "D",
    }


def test_dorothea_level_is_returned_as_the_full_list():
    result, _ = _run({"tf_gene": "TP53", "confidence_level": "A"})
    row = next(r for r in result["data"] if r["target_genesymbol"] == "B")
    assert row["dorothea_level"] == ["A", "D"]
