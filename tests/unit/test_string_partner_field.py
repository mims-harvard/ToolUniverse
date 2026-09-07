"""STRING edge orientation.

STRING orders every edge as A/B by internal ID, not by what was queried, so the
queried protein appears as `preferredName_A` on some rows and `preferredName_B`
on others. Reading `preferredName_B` alone -- the obvious approach -- silently
drops roughly half the partners.
"""

from tooluniverse.string_tool import STRINGRESTTool


def _rows():
    return [
        {"preferredName_A": "CDH1", "preferredName_B": "PIEZO1", "score": "0.386"},
        {"preferredName_A": "PIEZO1", "preferredName_B": "PIEZO2", "score": "0.432"},
        {"preferredName_A": "TSPAN5", "preferredName_B": "PIEZO1", "score": "0.414"},
    ]


def test_partner_is_the_other_end_regardless_of_side():
    out = STRINGRESTTool._label_partners(_rows(), {"protein_ids": ["PIEZO1"]})
    assert [r["partner"] for r in out] == ["CDH1", "PIEZO2", "TSPAN5"]


def test_reading_preferredName_B_alone_would_lose_partners():
    """Guards the actual defect: B-only misses the rows where the query is A."""
    out = STRINGRESTTool._label_partners(_rows(), {"protein_ids": ["PIEZO1"]})
    b_only = {r["preferredName_B"] for r in out} - {"PIEZO1"}
    assert {r["partner"] for r in out} - b_only == {"CDH1", "TSPAN5"}


def test_accepts_string_and_alias_argument_names():
    for args in ({"protein_ids": "PIEZO1"}, {"identifiers": ["PIEZO1"]}):
        out = STRINGRESTTool._label_partners(_rows(), args)
        assert {r["partner"] for r in out} == {"CDH1", "PIEZO2", "TSPAN5"}


def test_self_edge_and_unmatched_query_are_not_guessed():
    same = [{"preferredName_A": "PIEZO1", "preferredName_B": "PIEZO1", "score": "1"}]
    assert (
        STRINGRESTTool._label_partners(same, {"protein_ids": ["PIEZO1"]})[0]["partner"]
        is None
    )
    other = [{"preferredName_A": "X", "preferredName_B": "Y", "score": "1"}]
    assert (
        STRINGRESTTool._label_partners(other, {"protein_ids": ["PIEZO1"]})[0]["partner"]
        is None
    )


def test_non_dict_rows_are_left_alone():
    rows = ["unexpected", {"preferredName_A": "PIEZO1", "preferredName_B": "PIEZO2"}]
    out = STRINGRESTTool._label_partners(rows, {"protein_ids": ["PIEZO1"]})
    assert out[0] == "unexpected" and out[1]["partner"] == "PIEZO2"
