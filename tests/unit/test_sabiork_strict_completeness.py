import json
from unittest.mock import Mock, patch

import pytest

from tooluniverse.sabiork_tool import SABIORKTool


def _tool():
    return SABIORKTool(
        {
            "name": "SABIO_RK_search_reactions",
            "timeout": 30,
            "fields": {},
            "parameter": {
                "properties": {
                    "operation": {"type": "string", "const": "search_reactions"}
                }
            },
        }
    )


def _source_record(entry_id=3804):
    return {
        "id": entry_id,
        "general": {"organism": {"name": "Homo sapiens"}},
        "kineticlaw": {
            "parameter": [
                {
                    "name": "kcat",
                    "role": "Constant",
                    "parameter_type": {
                        "name": "kcat",
                        "sbo_term": "SBO:0000025",
                    },
                    "species": {"species_ref_type": "species"},
                    "start_value": 170.0,
                    "unit": {"name": "min^(-1)", "n_name": "s^(-1)"},
                    "n_start_value": 2.8333333333333335,
                    "comment": "-",
                },
                {
                    "name": "Km",
                    "role": "Constant",
                    "parameter_type": {
                        "name": "Km",
                        "sbo_term": "SBO:0000027",
                    },
                    "species": {"species_key": "1 | 1-Octanol | Substrate"},
                    "start_value": 550.0,
                    "unit": {"name": "µM", "n_name": "M"},
                    "n_start_value": 0.00055,
                },
            ]
        },
        "experimental_conditions": {
            "buffer": "0.1 M Glycine",
            "envvar_ph": {"start_value": 10.0},
        },
        "publication": {"pubmed_id": "2936344", "year": 1986},
        "enzyme_description": {
            "ec_number": "1.1.1.1",
            "enzyme_name": "alcohol dehydrogenase",
        },
        "future_field": {"preserved": True},
    }


def _doc(entry_id=3804):
    return {
        "EntryID": entry_id,
        "SabioReactionID": 2740,
        "ReactionEquation": "NAD+ + 1-Octanol = NADH + 1-Octanal",
        "ECNumber": ["1.1.1.1"],
        "EnzymeName": ["alcohol dehydrogenase"],
        "Organism": ["Homo sapiens"],
        "Substrate": ["NAD+", "1-Octanol"],
        "Product": ["NADH", "1-Octanal"],
        "ParameterType": ["kcat", "Km"],
        "PubMedID": ["2936344"],
        "Json": json.dumps(_source_record(entry_id)),
    }


def _response(*, total=768, start=0, docs=None):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "response": {"numFound": total, "start": start, "docs": docs or []}
    }
    return response


@pytest.mark.parametrize(
    "arguments",
    [
        {"ec_number": "1.1.1.1", "limit": True},
        {"ec_number": "1.1.1.1", "limit": 0},
        {"ec_number": "1.1.1.1", "limit": 101},
        {"ec_number": "1.1.1.1", "offset": True},
        {"ec_number": "1.1.1.1", "offset": -1},
        {"ec_number": " "},
        {"ec_number": "1.1.1.1 OR *:*"},
        {"ec_number": "1.1.1.1", "page": 2},
    ],
)
def test_invalid_controls_are_rejected_before_network(arguments):
    with patch("tooluniverse.sabiork_tool.requests.get") as get:
        result = _tool().run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_real_solr_json_restores_parameters_and_complete_source_record():
    with patch(
        "tooluniverse.sabiork_tool.requests.get",
        return_value=_response(start=20, docs=[_doc()]),
    ) as get:
        result = _tool().run({"ec_number": "1.1.1.1", "limit": 1, "offset": 20})

    assert result["status"] == "success"
    record = result["data"]["kinetic_laws"][0]
    assert record["entry_id"] == "3804"
    assert [parameter["type"] for parameter in record["parameters"]] == [
        "kcat",
        "Km",
    ]
    assert record["parameters"][0]["value"] == 170.0
    assert record["parameters"][0]["normalized_value"] == pytest.approx(
        2.8333333333333335
    )
    assert record["parameters"][1]["normalized_unit"] == "M"
    assert record["experimental_conditions"]["buffer"] == "0.1 M Glycine"
    assert record["publication"]["pubmed_id"] == "2936344"
    assert record["source_record"]["future_field"] == {"preserved": True}
    assert record["source_record_complete"] is True
    assert result["metadata"]["source_records_complete"] is True
    assert get.call_args.kwargs["params"]["start"] == 20
    assert "Json" in get.call_args.kwargs["params"]["fl"].split(",")


def test_pagination_metadata_exposes_next_disjoint_offset():
    with patch(
        "tooluniverse.sabiork_tool.requests.get",
        return_value=_response(total=768, start=2, docs=[_doc(3805), _doc(4512)]),
    ):
        result = _tool().run({"ec_number": "1.1.1.1", "limit": 2, "offset": 2})

    data = result["data"]
    assert [record["entry_id"] for record in data["kinetic_laws"]] == [
        "3805",
        "4512",
    ]
    assert data["total_count"] == 768
    assert data["offset"] == 2
    assert data["has_more"] is True
    assert data["next_offset"] == 4
    assert data["result_set_complete"] is False


def test_single_complete_page_is_explicit():
    with patch(
        "tooluniverse.sabiork_tool.requests.get",
        return_value=_response(total=1, docs=[_doc()]),
    ):
        result = _tool().run({"parameter_type": "Km", "limit": 10})

    assert result["data"]["has_more"] is False
    assert result["data"]["next_offset"] is None
    assert result["data"]["result_set_complete"] is True


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"response": {"numFound": "768", "start": 0, "docs": []}},
        {"response": {"numFound": 1, "start": 4, "docs": [_doc()]}},
        {"response": {"numFound": 2, "start": 0, "docs": []}},
    ],
)
def test_inconsistent_source_pagination_is_an_error(body):
    response = Mock(status_code=200)
    response.json.return_value = body
    with patch("tooluniverse.sabiork_tool.requests.get", return_value=response):
        result = _tool().run({"ec_number": "1.1.1.1", "limit": 1})

    assert result["status"] == "error"


def test_invalid_or_mismatched_source_json_is_an_error():
    invalid = _doc()
    invalid["Json"] = json.dumps(_source_record(9999))
    with patch(
        "tooluniverse.sabiork_tool.requests.get",
        return_value=_response(total=1, docs=[invalid]),
    ):
        result = _tool().run({"ec_number": "1.1.1.1", "limit": 1})

    assert result["status"] == "error"
    assert "identity mismatch" in result["error"]


def test_returned_record_must_satisfy_requested_filter():
    doc = _doc()
    doc["ECNumber"] = ["2.7.1.1"]
    with patch(
        "tooluniverse.sabiork_tool.requests.get",
        return_value=_response(total=1, docs=[doc]),
    ):
        result = _tool().run({"ec_number": "1.1.1.1", "limit": 1})

    assert result["status"] == "error"
    assert "does not satisfy requested ec_number filter" in result["error"]


def test_solr_quoted_values_are_escaped():
    query = _tool()._build_query({"enzyme_name": 'alpha "beta" \\ enzyme'})

    assert query == 'EnzymeName:"alpha \\"beta\\" \\\\ enzyme"'
