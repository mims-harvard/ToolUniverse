"""Round 93: BioGRID_get_interactions silently ignored its interaction_type filter.

`interaction_type` is declared with enum physical/genetic/both (description:
"Type of interaction: 'physical' (protein-protein), 'genetic' ..."), but the code
never applied it -- BioGRID's REST API can't filter on it server-side, and the
client-side filtering the code comment described was never implemented. So every
call returned all interaction types regardless of the one requested.

BioGRID's response is a dict keyed by interaction id; each record carries an
EXPERIMENTAL_SYSTEM_TYPE field ("physical"/"genetic") -- confirmed in this tool's
own return_schema (src/tooluniverse/data/biogrid_tools.json). These tests mock the
API response and assert the client-side filter now keeps only matching records.

Note: BioGRID's REST API requires an access key; the key available in CI/dev is
unauthorized (401), so this fix is verified via a mocked response shaped exactly
like the tool's declared return_schema rather than a live call.
"""

from unittest.mock import patch

from tooluniverse.biogrid_tool import BioGRIDRESTTool


def _make():
    cfg = {
        "type": "BioGRIDRESTTool",
        "name": "BioGRID_get_interactions",
        "parameter": {
            "required": ["gene_names"],
            "properties": {
                "gene_names": {"type": "array", "items": {"type": "string"}},
                "interaction_type": {"type": "string", "default": "both"},
            },
        },
        "fields": {"endpoint": "/interactions/", "return_format": "JSON"},
    }
    return BioGRIDRESTTool(cfg)


# Response shaped like BioGRID JSON: {interaction_id: {record...}}, EXPERIMENTAL_SYSTEM_TYPE present.
_FAKE_RESPONSE = {
    "1": {"OFFICIAL_SYMBOL_A": "TP53", "OFFICIAL_SYMBOL_B": "BRCA1", "EXPERIMENTAL_SYSTEM_TYPE": "physical"},
    "2": {"OFFICIAL_SYMBOL_A": "TP53", "OFFICIAL_SYMBOL_B": "MDM2", "EXPERIMENTAL_SYSTEM_TYPE": "physical"},
    "3": {"OFFICIAL_SYMBOL_A": "TP53", "OFFICIAL_SYMBOL_B": "ATM", "EXPERIMENTAL_SYSTEM_TYPE": "genetic"},
}


def _run(tool, interaction_type):
    args = {"gene_names": ["TP53"], "api_key": "k"}
    if interaction_type is not None:
        args["interaction_type"] = interaction_type
    with patch.object(tool, "_make_request", return_value=dict(_FAKE_RESPONSE)):
        return tool.run(args)


def test_physical_keeps_only_physical():
    res = _run(_make(), "physical")
    assert res["status"] == "success"
    assert set(res["data"].keys()) == {"1", "2"}
    assert res["metadata"]["interaction_count"] == 2
    assert "interaction_type_filter" in res["metadata"]


def test_genetic_keeps_only_genetic():
    res = _run(_make(), "genetic")
    assert set(res["data"].keys()) == {"3"}
    assert res["metadata"]["interaction_count"] == 1


def test_both_returns_all_unfiltered():
    res = _run(_make(), "both")
    assert set(res["data"].keys()) == {"1", "2", "3"}
    # no filter note when not filtering
    assert "interaction_type_filter" not in res["metadata"]


def test_omitted_returns_all_unfiltered():
    res = _run(_make(), None)
    assert set(res["data"].keys()) == {"1", "2", "3"}
    assert "interaction_type_filter" not in res["metadata"]


def test_filter_is_case_insensitive():
    tool = _make()
    resp = {"9": {"OFFICIAL_SYMBOL_A": "X", "EXPERIMENTAL_SYSTEM_TYPE": "Physical"}}
    with patch.object(tool, "_make_request", return_value=resp):
        res = tool.run({"gene_names": ["X"], "api_key": "k", "interaction_type": "physical"})
    assert set(res["data"].keys()) == {"9"}
