"""Regression tests for OMA's two distinct pagination models."""

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.oma_tool import OMATool
from tooluniverse.tools.OMA_get_orthologs import OMA_get_orthologs


def _tool(endpoint):
    return OMATool({"name": f"OMA_{endpoint}", "fields": {"endpoint": endpoint}})


def _response(payload, headers=None):
    response = MagicMock()
    response.json.return_value = payload
    response.headers = headers or {}
    response.raise_for_status.return_value = None
    return response


def test_protein_orthologs_use_local_offset_because_upstream_ignores_per_page():
    payload = [
        {"omaid": f"MOUSE{i}", "species": {}, "rel_type": "1:1"} for i in range(5)
    ]
    with patch(
        "tooluniverse.oma_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = _tool("orthologs").run(
            {"protein_id": "P04637", "rel_type": "1:1", "per_page": 2, "offset": 2}
        )

    assert get.call_args.kwargs["params"] == {"rel_type": "1:1"}
    assert [item["oma_id"] for item in result["data"]] == ["MOUSE2", "MOUSE3"]
    metadata = dict(result["metadata"])
    assert "Showing 2 of 5" in metadata.pop("truncation_note")
    assert metadata == {
        "source": "OMA Browser",
        "query": "P04637",
        "count": 2,
        "total_count": 5,
        "per_page": 2,
        "offset": 2,
        "has_more": True,
        "truncated": True,
        "next_offset": 4,
        "pagination_mode": "local_complete_response",
    }


def test_genome_pairs_preserve_official_total_and_next_page():
    payload = [
        {
            "entry_1": {"omaid": "HUMAN1", "species": {}},
            "entry_2": {"omaid": "MOUSE1", "species": {}},
        }
    ]
    headers = {
        "x-total-count": "22292",
        "Link": '<https://omabrowser.org/api/pairs/HUMAN/MOUSE/?page=3>; rel="next"',
    }
    with patch(
        "tooluniverse.oma_tool.requests.get",
        return_value=_response(payload, headers),
    ) as get:
        result = _tool("genome_pairs").run(
            {"genome1": "HUMAN", "genome2": "MOUSE", "per_page": 101, "page": 2}
        )

    assert get.call_args.kwargs["params"] == {"per_page": 101, "page": 2}
    assert result["metadata"]["total_pairs"] == 22292
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3


@pytest.mark.parametrize(
    ("endpoint", "arguments"),
    [
        ("orthologs", {"protein_id": "P04637", "per_page": 0}),
        ("orthologs", {"protein_id": "P04637", "offset": -1}),
        (
            "genome_pairs",
            {"genome1": "HUMAN", "genome2": "MOUSE", "per_page": 10001},
        ),
        (
            "genome_pairs",
            {"genome1": "HUMAN", "genome2": "MOUSE", "page": 0},
        ),
    ],
)
def test_invalid_pagination_is_rejected(endpoint, arguments):
    with patch("tooluniverse.oma_tool.requests.get") as get:
        result = _tool(endpoint).run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_configs_and_wrapper_expose_the_real_models():
    config_path = (
        Path(__file__).parents[2] / "src" / "tooluniverse" / "data" / "oma_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}

    orthologs = configs["OMA_get_orthologs"]["parameter"]["properties"]
    assert orthologs["per_page"]["maximum"] == 1000
    assert "offset" in orthologs
    assert "offset" in inspect.signature(OMA_get_orthologs).parameters

    pairs = configs["OMA_get_genome_pair_orthologs"]["parameter"]["properties"]
    assert pairs["per_page"]["maximum"] == 10000
    assert pairs["page"]["minimum"] == 1
