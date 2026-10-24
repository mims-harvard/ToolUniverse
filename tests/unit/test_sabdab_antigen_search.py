"""SAbDab_search_structures searches again, on /api/antibody-instances.

#701 concluded SAbDab 2 had no search route because every filter on /api/pdb
is accepted and ignored. /api/antibody-instances does filter. Checked live on
2026-10-23: no filter gave `total` 22671, binds_to_antigen=lysozyme 123,
"spike glycoprotein" 2008, "erbB-2" 31, "HER2" 0, and a made-up name 0.
Two limits of that route shape the tool: binds_to_antigen is rejected above
25 characters (HTTP 422), and a full record carries the residue numbering of
both chains, so rows are returned compact.
"""

from unittest.mock import patch

import pytest

from tooluniverse.sabdab_tool import SABDAB_API_URL, SAbDabTool

pytestmark = pytest.mark.unit


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


# One instance of 1a2y as /api/antibody-instances returns it, numbering trimmed.
_INSTANCE_1A2Y = {
    "id": "pdb_00001a2y-B-A",
    "antibody_id": "sabdab2_H000EL0014",
    "type": "FV",
    "antigen_bindings": [
        {"antigen_instance_id": "pdb_00001a2y-C", "distance": 4.15985},
        {"antigen_instance_id": "pdb_00001a2y-D", "distance": 3.71536},
    ],
    "heavy_like_segment": {
        "type": "H",
        "sabdab_auth_asym_id": "B",
        "cdr1": "GFSLTGYG",
        "cdr2": "IWGDGNT",
        "cdr3": "ARERDYRLDY",
        "v_gene": "IGHV2-6-7 (Musmus)",
        "j_gene": "IGHJ2 (Musmus)",
        "numbering": [[[1, " "], "Q"], [[2, " "], "V"]],
    },
    "light_like_segment": {
        "type": "K",
        "sabdab_auth_asym_id": "A",
        "cdr1": "GNIHNY",
        "cdr2": "YTT",
        "cdr3": "QHFWSTPRT",
        "v_gene": "IGKV12-41 (Musmus)",
        "j_gene": "IGKJ2 (Musmus),IGKJ1 (Musmus)",
        "numbering": [[[1, " "], "D"], [[2, " "], "I"]],
    },
    "pdb_entry": {
        "id": "pdb_00001a2y",
        "name": "HEN EGG WHITE LYSOZYME, D18A MUTANT, IN COMPLEX WITH MOUSE "
        "MONOCLONAL ANTIBODY D1.3",
        "resolution": 1.5,
        "structure_method": "X-ray diffraction",
        "release_date": "1998-01-13",
    },
}


def _search(arguments, payload=None, status_code=200):
    tool = SAbDabTool(
        {
            "name": "SAbDab_search_structures",
            "fields": {"operation": "search_structures"},
            "parameter": {
                "properties": {
                    "operation": {"type": "string", "const": "search_structures"}
                }
            },
        }
    )
    calls = []

    def fake_get(url, params=None, timeout=None, headers=None):
        calls.append((url, dict(params or {})))
        return _Response(payload, status_code)

    with patch("tooluniverse.sabdab_tool.requests.get", fake_get):
        return tool.run(arguments), calls


def _page(results, total, limit=20, offset=0):
    return {"results": results, "total": total, "limit": limit, "offset": offset}


def test_antigen_query_is_sent_as_binds_to_antigen():
    result, calls = _search({"query": "lysozyme"}, _page([_INSTANCE_1A2Y], 123))

    url, params = calls[0]
    assert url == f"{SABDAB_API_URL}/antibody-instances"
    assert params == {"binds_to_antigen": "lysozyme", "limit": 20, "offset": 0}
    assert result["status"] == "success"
    assert result["data"]["total_matches"] == 123


def test_rows_are_compact_and_name_the_pdb_entry():
    result, _ = _search({"query": "lysozyme"}, _page([_INSTANCE_1A2Y], 123))

    row = result["data"]["structures"][0]
    assert row["pdb_id"] == "1a2y"
    assert row["antibody_type"] == "FV"
    assert row["resolution"] == 1.5
    assert row["heavy"]["cdr3"] == "ARERDYRLDY"
    assert row["light"]["chain_type"] == "K"
    assert row["antigen_instance_ids"] == ["pdb_00001a2y-C", "pdb_00001a2y-D"]
    assert "numbering" not in row["heavy"]


def test_pagination_reports_the_next_offset_and_the_last_page():
    first, _ = _search(
        {"query": "lysozyme", "limit": 1}, _page([_INSTANCE_1A2Y], 123, limit=1)
    )
    assert first["data"]["count"] == 1
    assert first["data"]["has_more"] is True
    assert first["data"]["next_offset"] == 1
    assert first["data"]["result_set_complete"] is False

    last, calls = _search(
        {"query": "lysozyme", "offset": 122},
        _page([_INSTANCE_1A2Y], 123, offset=122),
    )
    assert calls[0][1]["offset"] == 122
    assert last["data"]["has_more"] is False
    assert last["data"]["next_offset"] is None


def test_filters_are_mapped_to_the_api_vocabulary():
    _, calls = _search(
        {
            "query": "spike",
            "species": "Lama glama",
            "method": "x-ray DIFFRACTION",
            "resolution_max": 2.5,
            "antigen_type": "protein",
            "antibody_type": "sd-h",
            "pdb_id": "7KKK",
        },
        _page([], 0),
    )
    params = calls[0][1]
    assert params["organism_scientific"] == "Lama glama"
    assert params["experimental_method"] == "X-ray diffraction"
    assert params["resolution"] == 2.5
    assert params["antigen_type"] == "PROTEIN"
    assert params["antibody_type"] == "SD-H"
    assert params["pdb_entry"] == "pdb_00007kkk"


def test_a_shorthand_that_matches_nothing_gets_a_way_forward():
    result, _ = _search({"query": "HER2"}, _page([], 0))

    assert result["status"] == "success"
    assert result["data"]["total_matches"] == 0
    assert "erbB-2" in result["data"]["note"]


@pytest.mark.parametrize(
    ("arguments", "parameter"),
    [
        ({"query": "Receptor tyrosine-protein kinase erbB-2"}, "query"),
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
        ({"limit": True}, "limit"),
        ({"offset": -1}, "offset"),
        ({"resolution_max": 0}, "resolution_max"),
        ({"method": "cryo-EM"}, "method"),
        ({"antibody_type": "IgG"}, "antibody_type"),
        ({"antigen_type": "small molecule"}, "antigen_type"),
    ],
)
def test_invalid_arguments_are_rejected_before_any_request(arguments, parameter):
    result, calls = _search(arguments, _page([], 0))

    assert calls == []
    assert result["status"] == "error"
    assert result["parameter"] == parameter


def test_a_response_without_results_and_total_is_an_error():
    result, _ = _search({"query": "lysozyme"}, {"detail": "unexpected"})

    assert result["status"] == "error"


def test_an_http_error_is_reported_not_returned_as_empty():
    result, _ = _search({"query": "lysozyme"}, {"detail": []}, status_code=422)

    assert result["status"] == "error"
    assert "422" in result["error"]
