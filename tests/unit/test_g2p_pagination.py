import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/gene2phenotype_tools.json"
)


def _config():
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(config for config in configs if config["name"] == "G2P_search")


def _response():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "count": 91,
        "next": "https://www.ebi.ac.uk/gene2phenotype/api/search/?page=3&query=epilepsy",
        "previous": "https://www.ebi.ac.uk/gene2phenotype/api/search/?query=epilepsy",
        "results": [{"stable_id": f"G2P{i:05d}"} for i in range(20)],
    }
    return response


def test_g2p_exposes_exact_one_based_page_continuation():
    tool = BaseRESTTool(_config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run({"query": "epilepsy", "page": 2})

    assert result["status"] == "success"
    assert result["metadata"]["returned"] == 20
    assert result["metadata"]["total_results"] == 91
    assert result["metadata"]["total_pages"] == 5
    assert result["metadata"]["page"] == 2
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["previous_url"]
    assert request.call_args.kwargs["params"]["page"] == 2


def test_g2p_defaults_to_page_one_and_rejects_invalid_pages():
    config = _config()
    assert config["parameter"]["properties"]["page"]["default"] == 1
    assert config["parameter"]["properties"]["page"]["minimum"] == 1

    tool = BaseRESTTool(config)
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"query": "epilepsy", "page": 0})["status"] == "error"
        assert tool.run({"query": "epilepsy", "page": -1})["status"] == "error"
        assert tool.run({"query": "epilepsy", "page": True})["status"] == "error"
    request.assert_not_called()
