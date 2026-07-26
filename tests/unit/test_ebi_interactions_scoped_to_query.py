"""EBI interaction tools attributed neighbours' partners to the query protein.

/proteins/interaction/{acc} answers with the queried protein *plus* about a
hundred neighbour proteins, each carrying its own complete interaction list.
Pooling every entry's interactions turned unrelated pairs into partners of the
query.

Confirmed live before the fix: TP53 (P04637) reported total_interactions 3258
against a true 185, and 44 of the 50 rows on the default page were not TP53
interactions at all -- AXIN1-GSK3B, BRCA2-RAD51 and PIK3CA-PIK3R1 among them.
Insulin (P01308) reported 735 partners against a true 9, listing huntingtin and
ataxin-1 -- partners of a chaperone hub in the same payload -- as insulin
binders.
"""

from unittest.mock import patch

from tooluniverse.ebi_proteins_interactions_tool import (
    EBIProteinsInteractionsTool,
    _entries_for_accession,
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


# Entry 0 is the query protein; entries 1-2 are neighbours whose own
# interactions must never be attributed to it.
_PAYLOAD = [
    {
        "accession": "P04637",
        "name": "P53_HUMAN",
        "interactions": [
            {
                "accession1": "P04637",
                "accession2": "Q00987",
                "gene": "MDM2",
                "experiments": 117,
                "interactor1": "EBI-366083",
                "interactor2": "EBI-389668",
            },
            {
                "accession1": "P04637",
                "accession2": "O15151",
                "gene": "MDM4",
                "experiments": 27,
                "interactor1": "EBI-366083",
                "interactor2": "EBI-398437",
            },
        ],
        "diseases": [{"diseaseId": "Li-Fraumeni syndrome"}],
        "subcellularLocations": [{"locations": [{"location": {"value": "Nucleus"}}]}],
    },
    {
        "accession": "O15169",
        "interactions": [
            {
                "accession1": "O15169",
                "accession2": "P49841",
                "gene": "GSK3B",
                "experiments": 52,
                "interactor1": "EBI-373586",
                "interactor2": "EBI-710484",
            }
        ],
        "diseases": [{"diseaseId": "SHOULD NOT APPEAR"}],
    },
    {
        "accession": "P51587",
        "interactions": [
            {
                "accession1": "P51587",
                "accession2": "Q06609",
                "gene": "RAD51",
                "experiments": 46,
                "interactor1": "EBI-297202",
                "interactor2": "EBI-79792",
            }
        ],
    },
]


def _make(operation):
    return EBIProteinsInteractionsTool(
        {
            "name": f"EBIProteins_{operation}",
            "type": "EBIProteinsInteractionsTool",
            "fields": {"operation": operation},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _run(operation, arguments):
    tool = _make(operation)
    with patch(
        "tooluniverse.ebi_proteins_interactions_tool.requests.get",
        return_value=_FakeResponse(_PAYLOAD),
    ):
        return tool.run(arguments)


def test_entries_helper_keeps_only_the_query_protein():
    entries = _entries_for_accession(_PAYLOAD, "P04637")

    assert [e["accession"] for e in entries] == ["P04637"]


def test_entries_helper_is_case_insensitive():
    assert len(_entries_for_accession(_PAYLOAD, "p04637")) == 1


def test_only_the_query_proteins_partners_are_returned():
    result = _run("get_interactions", {"accession": "P04637"})
    genes = {i["gene_name"] for i in result["data"]["interactions"]}

    assert genes == {"MDM2", "MDM4"}
    assert "GSK3B" not in genes
    assert "RAD51" not in genes


def test_total_counts_only_the_query_proteins_interactions():
    result = _run("get_interactions", {"accession": "P04637"})

    assert result["metadata"]["total_interactions"] == 2


def test_every_returned_row_involves_the_query_proteins_intact_id():
    result = _run("get_interactions", {"accession": "P04637"})

    for interaction in result["data"]["interactions"]:
        assert "EBI-366083" in (
            interaction["intact_id_a"],
            interaction["intact_id_b"],
        )


def test_sorting_by_experiment_count_is_preserved():
    result = _run("get_interactions", {"accession": "P04637"})
    counts = [i["experiments"] for i in result["data"]["interactions"]]

    assert counts == sorted(counts, reverse=True)


def test_interaction_details_is_scoped_the_same_way():
    result = _run("get_interaction_details", {"accession": "P04637"})
    payload = result["data"]
    genes = {i["gene_name"] for i in payload["interactions"]}

    assert genes == {"MDM2", "MDM4"}
    assert "SHOULD NOT APPEAR" not in str(payload.get("diseases"))


def test_details_metadata_comes_from_the_query_protein_even_if_not_first():
    reordered = [_PAYLOAD[1], _PAYLOAD[0], _PAYLOAD[2]]
    tool = _make("get_interaction_details")
    with patch(
        "tooluniverse.ebi_proteins_interactions_tool.requests.get",
        return_value=_FakeResponse(reordered),
    ):
        result = tool.run({"accession": "P04637"})

    genes = {i["gene_name"] for i in result["data"]["interactions"]}
    assert genes == {"MDM2", "MDM4"}
