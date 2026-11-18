"""Live smoke test for the PubMLST tools (needs network)."""

from pathlib import Path

import pytest

from tooluniverse import ToolUniverse

pytestmark = [pytest.mark.integration, pytest.mark.network]

FASTA = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "pubmlst"
    / "neisseria_st11_mlst_loci.fasta"
)


@pytest.fixture(scope="module")
def tu():
    universe = ToolUniverse()
    universe.load_tools(
        include_tools=[
            "PubMLST_list_databases",
            "PubMLST_list_schemes",
            "PubMLST_get_profile",
            "PubMLST_type_sequence",
        ]
    )
    return universe


def test_neisseria_st11_round_trip(tu):
    dbs = tu.run(
        {"name": "PubMLST_list_databases", "arguments": {"query": "neisseria"}}
    )
    assert dbs["status"] == "success"
    database = dbs["data"][0]["seqdef_database"]
    assert database == "pubmlst_neisseria_seqdef"

    schemes = tu.run(
        {"name": "PubMLST_list_schemes", "arguments": {"database": database}}
    )
    assert {"scheme_id": 1, "description": "MLST"} in schemes["data"]

    profile = tu.run(
        {
            "name": "PubMLST_get_profile",
            "arguments": {"database": database, "scheme_id": 1, "st": 11},
        }
    )
    assert profile["data"]["clonal_complex"] == "ST-11 complex"
    assert profile["data"]["alleles"]["abcZ"] == "2"

    typed = tu.run(
        {
            "name": "PubMLST_type_sequence",
            "arguments": {
                "database": database,
                "scheme_id": 1,
                "sequence": FASTA.read_text(),
            },
        }
    )
    assert typed["data"]["fields"]["ST"] == "11"
