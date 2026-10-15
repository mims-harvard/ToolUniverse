"""The summary-statistics API is gone; these tools moved to GWAS Catalog v2.

/gwas/summary-statistics/api answers 410 on every path. Study listing and
per-trait lookup moved to /gwas/api/v2; region queries did not, because v2
serves associations only per study and ignores chromosome, position and
p-value filters.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.gwas_sumstats_tool import (
    GWAS_BASE_URL,
    SUMSTATS_FTP_URL,
    GWASSumStatsTool,
)

pytestmark = pytest.mark.unit


def _tool(endpoint_type):
    return GWASSumStatsTool(
        {
            "name": f"GWASSumStats_{endpoint_type}",
            "fields": {"endpoint_type": endpoint_type},
        }
    )


def _response(studies, total=None):
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "_embedded": {"studies": studies},
        "page": {"totalElements": total if total is not None else len(studies)},
    }
    return response


STUDY = {
    "accessionId": "GCST004253",
    "reportedTrait": "Accelerated cognitive decline",
    "efoTraits": [{"key": "EFO_0000249", "label": "Alzheimer disease"}],
    "pubmedId": "28183528",
    "publicationDate": "2017-02-10",
    "firstAuthor": "Smith A",
    "associationCount": 12,
}


def test_the_retired_host_is_no_longer_used():
    assert "summary-statistics" not in GWAS_BASE_URL
    assert GWAS_BASE_URL == "https://www.ebi.ac.uk/gwas/api/v2"


def test_list_studies_reads_v2_fields():
    with patch(
        "tooluniverse.gwas_sumstats_tool.requests.get", return_value=_response([STUDY])
    ) as get:
        result = _tool("list_studies").run({"size": 5})

    assert get.call_args[0][0] == f"{GWAS_BASE_URL}/studies"
    record = result["data"][0]
    assert record["study_accession"] == "GCST004253"
    assert record["efo_traits"] == [{"id": "EFO_0000249", "label": "Alzheimer disease"}]
    assert record["association_count"] == 12


def test_trait_studies_filters_by_label():
    with patch(
        "tooluniverse.gwas_sumstats_tool.requests.get", return_value=_response([STUDY])
    ) as get:
        result = _tool("get_trait_studies").run({"trait": "alzheimer", "size": 3})

    assert get.call_args.kwargs["params"]["efoTrait"] == "alzheimer"
    assert result["status"] == "success"
    assert result["metadata"]["trait"] == "alzheimer"


def test_an_ontology_id_is_explained_not_answered_with_nothing():
    """v2 returns zero studies for an id, which reads as 'no studies exist'."""
    with patch("tooluniverse.gwas_sumstats_tool.requests.get") as get:
        result = _tool("get_trait_studies").run({"trait_id": "EFO_0000249"})

    assert result["status"] == "error"
    assert "EFO_0000249" in result["error"]
    assert "label" in result["error"]
    get.assert_not_called()


def test_no_match_says_how_the_matching_works():
    with patch(
        "tooluniverse.gwas_sumstats_tool.requests.get", return_value=_response([])
    ):
        result = _tool("get_trait_studies").run({"trait": "zzznotatrait"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert "substring" in result["metadata"]["note"]


def test_region_queries_report_where_the_data_went():
    with patch("tooluniverse.gwas_sumstats_tool.requests.get") as get:
        result = _tool("get_region_associations").run(
            {"chromosome": 19, "bp_lower": 44000000, "bp_upper": 44100000}
        )

    assert result["status"] == "error"
    assert "chr19:44000000-44100000" in result["error"]
    assert SUMSTATS_FTP_URL in result["error"]
    # No point calling an endpoint that answers 410.
    get.assert_not_called()
