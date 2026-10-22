import json
from pathlib import Path
from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool


_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "src/tooluniverse/data/litvar_tools.json"
)


def _config():
    configs = json.loads(_CONFIG_PATH.read_text())
    return next(
        config
        for config in configs
        if config["name"] == "LitVar_get_variant_publications"
    )


def _response():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "pmids": [101, 102, 103, 104, 105],
        "pmcids": ["PMC1", "PMC2", "PMC3", "PMC4"],
        "pmids_count": 5,
    }
    return response


def test_publication_lists_are_locally_paged_with_separate_exact_totals():
    tool = BaseRESTTool(_config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run({"rsid": "rs429358", "format": "json", "max": 2, "offset": 2})

    assert result["status"] == "success"
    assert result["data"]["pmids"] == [103, 104]
    assert result["data"]["pmcids"] == ["PMC3", "PMC4"]
    assert result["data"]["pmids_count"] == 5
    assert result["data"]["pmcids_count"] == 4
    assert result["metadata"]["total_pmids"] == 5
    assert result["metadata"]["total_pmcids"] == 4
    assert result["metadata"]["next_offset"] == 4
    assert result["metadata"]["upstream_supports_pagination"] is False
    sent_params = request.call_args.kwargs["params"]
    assert "max" not in sent_params
    assert "offset" not in sent_params
    assert "format" not in sent_params


def test_second_list_can_end_before_first_without_false_completion():
    tool = BaseRESTTool(_config())
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ):
        result = tool.run({"rsid": "rs429358", "max": 2, "offset": 4})

    assert result["data"]["pmids"] == [105]
    assert result["data"]["pmcids"] == []
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


def test_invalid_local_publication_page_fails_before_network():
    tool = BaseRESTTool(_config())
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({"rsid": "rs1", "max": 0})["status"] == "error"
        assert tool.run({"rsid": "rs1", "max": True})["status"] == "error"
        assert tool.run({"rsid": "rs1", "offset": -1})["status"] == "error"
        assert tool.run({"rsid": "rs1", "offset": False})["status"] == "error"
    request.assert_not_called()


def test_config_no_longer_claims_upstream_honors_max():
    config = _config()

    assert config["fields"]["pagination"] == "litvar_publications_local"
    assert set(config["fields"]["client_only_params"]) == {"format", "max", "offset"}
    assert "ignores max/limit/offset" in config["description"]
