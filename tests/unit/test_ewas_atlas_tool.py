"""EWAS Atlas tools: request shapes and the API quirks verified live.

Quirks (2026-10-09): chromosomes are numbers (X=23, Y=24) and "X" makes the
server drop the connection; unknown probes also drop it; study/publication
records spell their list "assocaitionList"; "not found" is code 1 with null
data; windows above ~1 Mb run into the server's own timeout.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from tooluniverse.ewas_atlas_tool import EWASAtlasTool

pytestmark = pytest.mark.unit

CONFIGS = {
    t["name"]: t
    for t in json.loads(
        (
            Path(__file__).parents[2] / "src/tooluniverse/data/ewas_atlas_tools.json"
        ).read_text()
    )
}


def _tool(name):
    return EWASAtlasTool(CONFIGS[name])


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _probe(probe_id, traits):
    return {
        "probeId": probe_id,
        "chrHg19": 5,
        "posHg19": 373378,
        "cpgIsland": "Shelf",
        "relatedTranscription": [
            {"geneName": "AHRR", "posToTss": 1, "ensemblTranscriptId": "T1"},
            {"geneName": "AHRR", "posToTss": 2, "ensemblTranscriptId": "T2"},
        ],
        "associationList": [
            {
                "studyId": f"ES{i:05d}",
                "trait": trait,
                "correlation": "neg",
                "rank": 1,
                "pmid": 100 + i,
            }
            for i, trait in enumerate(traits)
        ],
    }


def test_probe_lookup_flattens_record_and_bounds_associations():
    payload = {
        "code": 0,
        "msg": "success",
        "data": _probe("cg05575921", ["smoking"] * 8 + ["maternal smoking"] * 4),
    }
    with patch(
        "tooluniverse.ewas_atlas_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = _tool("EWASAtlas_get_probe").run(
            {"probe_id": "cg05575921", "limit": 5}
        )

    assert get.call_args.kwargs["params"] == {"probeId": "cg05575921"}
    data = result["data"]
    assert result["status"] == "success"
    assert data["genes"] == ["AHRR"]
    assert data["association_count"] == 12
    assert data["trait_count"] == 2
    assert len(data["associations"]) == 5
    assert data["associations"][0]["pmid"] == "100"


def test_unknown_probe_dropped_connection_is_explained():
    with patch(
        "tooluniverse.ewas_atlas_tool.requests.get",
        side_effect=requests.exceptions.ConnectionError("Remote end closed"),
    ):
        result = _tool("EWASAtlas_get_probe").run({"probe_id": "cg99999999"})

    assert result["status"] == "error"
    assert "does not hold" in result["error"]


@pytest.mark.parametrize(
    "given, sent", [("X", 23), ("chrX", 23), ("y", 24), ("chr5", 5), ("5", 5)]
)
def test_region_sends_numeric_chromosome(given, sent):
    payload = {"code": 0, "msg": "success", "data": [_probe("cg1", ["sex"])]}
    with patch(
        "tooluniverse.ewas_atlas_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = _tool("EWASAtlas_search_by_region").run(
            {"chromosome": given, "start": 100, "end": 200}
        )

    assert result["status"] == "success"
    assert get.call_args.kwargs["params"] == {"chr": sent, "start": 100, "end": 200}


@pytest.mark.parametrize(
    "arguments",
    [
        {"chromosome": "5", "start": 1, "end": 5_000_000},
        {"chromosome": "25", "start": 1, "end": 10},
        {"chromosome": "5", "start": 10, "end": 5},
        {"chromosome": "5", "start": True, "end": 5},
    ],
)
def test_region_rejects_bad_windows_without_calling_the_api(arguments):
    with patch("tooluniverse.ewas_atlas_tool.requests.get") as get:
        result = _tool("EWASAtlas_search_by_region").run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_gene_search_orders_probes_and_counts_traits_across_all_of_them():
    probes = [
        _probe("cg_few", ["asthma"]),
        _probe("cg_many", ["smoking", "smoking", "smoking"]),
    ]
    payload = {"code": 0, "data": {"probeList": probes, "geneSymbol": "AHRR"}}
    with patch(
        "tooluniverse.ewas_atlas_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool("EWASAtlas_search_by_gene").run(
            {"gene_symbol": "AHRR", "limit": 1, "max_associations_per_probe": 2}
        )

    assert [p["probe_id"] for p in result["data"]] == ["cg_many"]
    assert len(result["data"][0]["associations"]) == 2
    meta = result["metadata"]
    assert meta["total_probes"] == 2
    assert meta["total_associations"] == 4
    assert meta["top_traits"][0] == {"trait": "smoking", "associations": 3}
    assert {"trait": "asthma", "associations": 1} in meta["top_traits"]


def test_unknown_gene_is_an_empty_success():
    payload = {"code": 0, "data": {"probeList": [], "geneSymbol": "NOTAGENE"}}
    with patch(
        "tooluniverse.ewas_atlas_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool("EWASAtlas_search_by_gene").run({"gene_symbol": "NOTAGENE"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["total_probes"] == 0


def test_study_reads_the_misspelled_association_list():
    payload = {
        "code": 0,
        "data": {
            "studyId": "ES00033",
            "reportedTrait": "body mass index (BMI)",
            "caseGroup": "",
            "assocaitionList": [
                {
                    "probeId": "cg22891070",
                    "correlation": "hyper",
                    "rank": 1,
                    "pvalue": "4.0e-08",
                }
            ],
            "cohortList": [
                {
                    "stage": "Initial",
                    "sampleSize": 239,
                    "fullName": "Cardiogenics",
                    "cohortName": "",
                    "tissue": "whole blood",
                    "platform": "450K",
                }
            ],
        },
    }
    with patch(
        "tooluniverse.ewas_atlas_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool("EWASAtlas_get_study").run({"study_id": "ES00033"})

    data = result["data"]
    assert data["association_count"] == 1
    assert data["associations"][0]["p_value"] == "4.0e-08"
    assert data["case_group"] is None
    assert data["cohorts"][0]["cohort"] == "Cardiogenics"


@pytest.mark.parametrize(
    "name, arguments",
    [
        ("EWASAtlas_get_study", {"study_id": "ES99999"}),
        ("EWASAtlas_get_publication", {"pmid": "1"}),
    ],
)
def test_code_1_not_found_is_an_error(name, arguments):
    payload = {"code": 1, "msg": "Sorry, study couldn't be found.", "data": None}
    with patch(
        "tooluniverse.ewas_atlas_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool(name).run(arguments)

    assert result["status"] == "error"
    assert "couldn't be found" in result["error"]


@pytest.mark.parametrize(
    "name, arg",
    [
        ("EWASAtlas_get_probe", "probe_id"),
        ("EWASAtlas_search_by_gene", "gene_symbol"),
        ("EWASAtlas_get_study", "study_id"),
        ("EWASAtlas_get_publication", "pmid"),
    ],
)
def test_missing_identifier_is_rejected_locally(name, arg):
    with patch("tooluniverse.ewas_atlas_tool.requests.get") as get:
        result = _tool(name).run({})

    assert result["status"] == "error"
    assert arg in result["error"]
    get.assert_not_called()


@pytest.mark.network
def test_live_probe_lookup():
    result = _tool("EWASAtlas_get_probe").run({"probe_id": "cg05575921", "limit": 3})
    assert result["status"] == "success", result
    assert "AHRR" in result["data"]["genes"]
    assert result["data"]["association_count"] > 50
