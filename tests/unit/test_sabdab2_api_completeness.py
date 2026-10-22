"""Round 221: SAbDab2 JSON API pagination and record-completeness guards."""

import inspect
import json
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import validate

from tooluniverse.sabdab_tool import SAbDabTool

pytestmark = pytest.mark.unit


def _response(payload, url="https://sabdab.opig.stats.ox.ac.uk/api/test"):
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.json.return_value = payload
    response.url = url
    response.raise_for_status.return_value = None
    return response


def _tool(operation):
    return SAbDabTool(
        {
            "parameter": {
                "properties": {"operation": {"type": "string", "const": operation}}
            }
        }
    )


def _config(name):
    with open("src/tooluniverse/data/sabdab_tools.json") as handle:
        return next(item for item in json.load(handle) if item["name"] == name)


def test_search_uses_filters_and_exposes_next_offset():
    """Filtered search must preserve exact totals and reveal the next page."""
    payload = {
        "results": [{"id": "pdb_00007f5h-C"}, {"id": "pdb_00007f5h-D"}],
        "total": 30,
        "limit": 2,
        "offset": 4,
    }
    with patch(
        "tooluniverse.sabdab_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = _tool("search_structures").run(
            {
                "query": "SARS-CoV-2",
                "species": "homo sapiens",
                "resolution_max": 3.0,
                "limit": 2,
                "offset": 4,
            }
        )

    assert result["status"] == "success"
    assert result["data"]["total"] == 30
    assert result["data"]["next_offset"] == 6
    assert result["data"]["result_set_complete"] is False
    validate(result["data"], _config("SAbDab_search_structures")["return_schema"])
    assert get.call_args.kwargs["params"] == {
        "limit": 2,
        "offset": 4,
        "binds_to_antigen": "SARS-CoV-2",
        "organism_scientific": "homo sapiens",
        "resolution": 3.0,
    }


@pytest.mark.parametrize("limit", [True, 0, 101])
def test_search_rejects_invalid_limits(limit):
    """Invalid limits cannot silently fall back to an upstream default."""
    result = _tool("search_structures").run({"limit": limit})
    assert result["status"] == "error"
    assert "limit" in result["error"]


def test_search_rejects_conflicting_pagination_metadata():
    """An ignored offset must be surfaced instead of returning the wrong page."""
    payload = {"results": [], "total": 10, "limit": 2, "offset": 0}
    with patch(
        "tooluniverse.sabdab_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool("search_structures").run({"limit": 2, "offset": 2})
    assert result["status"] == "error"
    assert "pagination" in result["error"]


def test_unknown_parameter_is_not_silently_ignored():
    """A misspelled filter must fail instead of broadening the search."""
    result = _tool("search_structures").run({"resoultion_max": 2.0})
    assert result["status"] == "error"
    assert "resoultion_max" in result["error"]


def test_get_structure_preserves_source_and_enriches_antigens():
    """Structure retrieval must include full PDB, antibody and antigen records."""
    pdb = {
        "id": "pdb_00007d6i",
        "name": "Neutralizing antibody",
        "resolution": 3.41,
        "structure_method": "X-ray diffraction",
        "polymer_instances": [{"sabdab_auth_asym_id": "B"}],
        "non_polymer_instances": [],
        "extra_upstream_field": {"preserved": True},
    }
    antibody = {
        "id": "pdb_00007d6i-B-C",
        "heavy_like_segment": {"cdr3": "TRAGWVRGAFDI"},
        "antigen_bindings": [{"antigen_instance_id": "pdb_00007d6i-A"}],
    }
    antigen = {
        "id": "pdb_00007d6i-A",
        "polymer_instance": {"name": "Spike protein S1"},
    }
    responses = [
        _response(pdb, url="https://sabdab.opig.stats.ox.ac.uk/api/pdb/pdb_00007d6i"),
        _response({"results": [antibody], "total": 1, "limit": 100, "offset": 0}),
        _response(antigen),
    ]
    with patch("tooluniverse.sabdab_tool.requests.get", side_effect=responses):
        result = _tool("get_structure").run({"pdb_id": "7D6I"})

    assert result["status"] == "success"
    data = result["data"]
    assert data["pdb_id"] == "7d6i"
    assert data["source_record"]["extra_upstream_field"] == {"preserved": True}
    assert data["antibody_instances"][0]["heavy_like_segment"]["cdr3"]
    assert data["antigen_instances"][0]["polymer_instance"]["name"] == "Spike protein S1"
    assert data["source_record_complete"] is True
    validate(data, _config("SAbDab_get_structure")["return_schema"])


def test_get_structure_rejects_identity_mismatch():
    """A payload for another PDB ID cannot be presented as the requested entry."""
    with patch(
        "tooluniverse.sabdab_tool.requests.get",
        return_value=_response({"id": "pdb_00003hfm"}),
    ):
        result = _tool("get_structure").run({"pdb_id": "7d6i"})
    assert result["status"] == "error"
    assert "identity" in result["error"]


def test_current_summary_data_matches_declared_schema():
    """SAbDab2 summary output must satisfy the data-level return schema."""
    pdb = {
        "id": "pdb_00007d6i",
        "name": "Neutralizing antibody",
        "resolution": 3.41,
        "structure_method": "X-ray diffraction",
        "polymer_instances": [
            {"sabdab_auth_asym_id": "B", "organism_scientific": "homo sapiens"},
            {"sabdab_auth_asym_id": "C", "organism_scientific": "homo sapiens"},
        ],
    }
    antibody = {
        "id": "pdb_00007d6i-B-C",
        "type": "FAB",
        "heavy_like_segment": {"sabdab_auth_asym_id": "B", "v_gene": "IGHV3-7"},
        "light_like_segment": {"sabdab_auth_asym_id": "C", "v_gene": "IGLV6-57"},
        "antigen_bindings": [{"antigen_instance_id": "pdb_00007d6i-A"}],
    }
    antigen = {
        "id": "pdb_00007d6i-A",
        "polymer_instance": {
            "name": "Spike protein S1",
            "entity_type": "PROTEIN",
            "organism_scientific": "severe acute respiratory syndrome coronavirus 2",
        },
    }
    with patch(
        "tooluniverse.sabdab_tool.requests.get",
        side_effect=[
            _response(pdb),
            _response({"results": [antibody], "total": 1, "limit": 100, "offset": 0}),
            _response(antigen),
        ],
    ):
        result = _tool("get_structure_summary").run({"pdb_id": "7d6i"})
    assert result["status"] == "success"
    validate(result["data"], _config("SAbDab_get_structure_summary")["return_schema"])
    assert result["data"]["antigen_name"] == "Spike protein S1"


def test_relationship_pages_are_all_retrieved():
    """Structure details must traverse every antibody relationship page."""
    pdb = {"id": "pdb_00007d6i", "polymer_instances": []}
    first_page = {
        "results": [{"id": "pdb_00007d6i-B-C", "antigen_bindings": []}],
        "total": 2,
        "limit": 100,
        "offset": 0,
    }
    second_page = {
        "results": [{"id": "pdb_00007d6i-D-E", "antigen_bindings": []}],
        "total": 2,
        "limit": 100,
        "offset": 1,
    }
    with patch(
        "tooluniverse.sabdab_tool.requests.get",
        side_effect=[_response(pdb), _response(first_page), _response(second_page)],
    ) as get:
        result = _tool("get_structure").run({"pdb_id": "7d6i"})
    assert result["status"] == "success"
    assert [item["id"] for item in result["data"]["antibody_instances"]] == [
        "pdb_00007d6i-B-C",
        "pdb_00007d6i-D-E",
    ]
    assert get.call_args_list[2].kwargs["params"]["offset"] == 1


def test_live_statistics_require_real_fields():
    """Static placeholder prose cannot masquerade as live database statistics."""
    malformed = {"description": "SAbDab"}
    with patch(
        "tooluniverse.sabdab_tool.requests.get", return_value=_response(malformed)
    ):
        result = _tool("get_summary").run({})
    assert result["status"] == "error"
    assert "statistics" in result["error"]


def test_statistics_data_matches_declared_schema():
    """The declared schema must validate the live statistics shape, not an envelope."""
    payload = {
        "antibody_instances": 21914,
        "PDB_entries": 11458,
        "SAbDab2_entries": 6780,
        "with_antigen": 19560,
        "last_update": "Thu 06 Aug 2026 00:44:32",
        "experimental_methods": {"X-RAY DIFFRACTION": 12558},
    }
    with patch(
        "tooluniverse.sabdab_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool("get_summary").run({})
    assert result["status"] == "success"
    validate(result["data"], _config("SAbDab_get_summary")["return_schema"])


def test_config_and_wrapper_expose_all_search_controls():
    """Agents must be able to reach pagination and every implemented filter."""
    config = _config("SAbDab_search_structures")
    expected = {
        "query",
        "antigen",
        "limit",
        "offset",
        "pdb_id",
        "species",
        "resolution_max",
        "method",
        "antigen_type",
        "antibody_type",
        "construct_type",
    }
    assert expected <= set(config["parameter"]["properties"])

    from tooluniverse.tools.SAbDab_search_structures import SAbDab_search_structures

    assert expected <= set(inspect.signature(SAbDab_search_structures).parameters)
