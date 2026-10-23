from unittest.mock import MagicMock, patch

from tooluniverse.pharos_tool import PharosTool


def _tool(operation):
    return PharosTool({"name": operation, "fields": {"operation": operation}})


def _response(data):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"data": data}
    return response


def test_search_targets_marks_fixed_first_ten_window_and_locally_honors_top():
    captured = {}

    def fake_post(_url, json, **_kwargs):
        captured.update(json["variables"])
        return _response(
            {
                "targets": {
                    "count": 177,
                    "targets": [{"sym": f"K{i}", "tdl": "Tdark"} for i in range(10)],
                }
            }
        )

    with patch("tooluniverse.pharos_tool.requests.post", side_effect=fake_post):
        result = _tool("search_targets").run(
            {"query": "kinase", "tdl": "Tdark", "top": 2}
        )

    assert "skip" not in captured
    assert captured["top"] == 10
    assert captured["facets"] == [
        {"facet": "Target Development Level", "values": ["Tdark"]}
    ]
    assert len(result["data"]["targets"]) == 2
    assert result["metadata"]["total_results"] == 177
    assert result["metadata"]["accessible_results"] == 10
    assert result["metadata"]["upstream_truncated"] is True
    assert result["metadata"]["pagination_supported"] is False
    assert result["metadata"]["next_skip"] is None


def test_disease_target_tdl_is_applied_but_false_skip_is_not_exposed():
    captured = {}

    def fake_post(_url, json, **_kwargs):
        captured["query"] = json["query"]
        captured.update(json["variables"])
        return _response(
            {"targets": {"count": 3, "targets": [{"sym": "X", "tdl": "Tclin"}]}}
        )

    with patch("tooluniverse.pharos_tool.requests.post", side_effect=fake_post):
        result = _tool("get_disease_targets").run(
            {"disease": "breast cancer", "tdl": "Tclin", "top": 1}
        )

    assert "skip: $skip" not in captured["query"]
    assert "skip" not in captured
    assert captured["facets"] == [
        {"facet": "Target Development Level", "values": ["Tclin"]}
    ]
    assert result["metadata"]["pagination_supported"] is False


def test_target_ligands_uses_native_skip_and_ligand_count_as_exact_total():
    captured = {}

    def fake_post(_url, json, **_kwargs):
        captured["query"] = json["query"]
        captured.update(json["variables"])
        return _response(
            {
                "target": {
                    "sym": "DRD2",
                    "ligandCounts": [
                        {"name": "ligand", "value": 3210},
                        {"name": "drug", "value": 81},
                    ],
                    "ligands": [{"name": "A"}, {"name": "B"}],
                }
            }
        )

    with patch("tooluniverse.pharos_tool.requests.post", side_effect=fake_post):
        result = _tool("get_target_ligands").run({"gene": "DRD2", "top": 2, "skip": 2})

    assert "ligands(top: $top, skip: $skip)" in captured["query"]
    assert captured["skip"] == 2
    assert result["metadata"]["total_results"] == 3210
    assert result["metadata"]["next_skip"] == 4


def test_invalid_pharos_pages_fail_before_network():
    with patch("tooluniverse.pharos_tool.requests.post") as post:
        assert (
            _tool("search_targets").run({"query": "x", "top": True})["status"]
            == "error"
        )
        assert (
            _tool("get_disease_targets").run({"disease": "x", "top": 11})["status"]
            == "error"
        )
        assert (
            _tool("get_target_ligands").run({"gene": "DRD2", "top": 51})["status"]
            == "error"
        )
    post.assert_not_called()
