from unittest.mock import Mock

import pytest

from tooluniverse.biomodels_tool import BioModelsRESTTool


def _tool(parameter_search=False):
    endpoint = (
        "https://www.ebi.ac.uk/biomodels/parameterSearch/search"
        if parameter_search
        else "https://www.ebi.ac.uk/biomodels/search"
    )
    return BioModelsRESTTool(
        {
            "name": "test",
            "parameter": {
                "properties": {
                    "limit": {"default": 10},
                    "offset": {"default": 0},
                }
            },
            "fields": {
                "endpoint": endpoint,
                "method": "GET",
                "params": {"format": "json"},
                "pagination": "biomodels_offset",
            },
        }
    )


@pytest.mark.parametrize(
    ("parameter_search", "records_key", "total_key", "size_key", "offset_key"),
    [
        (False, "models", "matches", "numResults", "offset"),
        (True, "entries", "recordsFiltered", "size", "start"),
    ],
)
def test_biomodels_uses_endpoint_specific_offsets_and_trims_minimum_batch(
    parameter_search, records_key, total_key, size_key, offset_key, monkeypatch
):
    tool = _tool(parameter_search)
    response = Mock(status_code=200, headers={})
    response.json.return_value = {
        records_key: [{"id": i} for i in range(10)],
        total_key: 25,
    }
    request = Mock(return_value=response)
    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)

    result = tool.run({"query": "k1", "limit": 2, "offset": 4})

    sent = request.call_args.kwargs["params"]
    assert sent[size_key] == 10
    assert sent[offset_key] == 4
    assert len(result["data"][records_key]) == 2
    assert result["metadata"]["total_results"] == 25
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["has_more"] is True


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit": 0},
        {"limit": 101},
        {"limit": "2"},
        {"offset": -1},
        {"offset": True},
    ],
)
def test_biomodels_rejects_invalid_pagination(arguments):
    result = _tool().run({"query": "glycolysis", **arguments})

    assert result["status"] == "error"
