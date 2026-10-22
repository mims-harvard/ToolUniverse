from unittest.mock import MagicMock

import pytest

from tooluniverse.sider_tool import SiderTool


pytestmark = pytest.mark.unit


def _response(text, status=200):
    response = MagicMock()
    response.status_code = status
    response.text = text
    return response


def _side_effect_html(count):
    rows = []
    for index in range(count):
        rows.append(
            '<tr class="bg1"><td><a href="/se/C{:07d}/" title="Effect {}">'
            "Effect {}</a></td><td>{}%</td></tr>".format(index, index, index, index + 1)
        )
    return "<h1>Example drug</h1>{}<h3 class='top'>Indications</h3>".format(
        "".join(rows)
    )


def _drug_html(count):
    rows = [
        '<li><a href="/drugs/{}/">Drug {}</a>: {}%</li>'.format(index, index, index + 1)
        for index in range(count)
    ]
    return "<h1>Headache</h1>{}".format("".join(rows))


def test_side_effect_pages_are_exact_and_disjoint():
    tool = SiderTool({"fields": {"operation": "get_side_effects"}})
    tool.session.get = MagicMock(return_value=_response(_side_effect_html(5)))
    first = tool.run({"sider_drug_id": "2244", "limit": 2})
    second = tool.run({"sider_drug_id": "2244", "limit": 2, "offset": 2})
    assert first["metadata"]["total_matches"] == 5
    assert first["metadata"]["next_offset"] == 2
    assert first["metadata"]["source_parse_complete"] is True
    first_codes = {item["meddra_code"] for item in first["data"]["side_effects"]}
    second_codes = {item["meddra_code"] for item in second["data"]["side_effects"]}
    assert first_codes.isdisjoint(second_codes)


def test_reverse_lookup_pages_are_exact_and_disjoint():
    tool = SiderTool({"fields": {"operation": "get_drugs_for_side_effect"}})
    tool.session.get = MagicMock(return_value=_response(_drug_html(5)))
    first = tool.run({"meddra_code": "C0018681", "limit": 2})
    second = tool.run({"meddra_code": "C0018681", "limit": 2, "offset": 2})
    assert first["data"]["total_drugs"] == 5
    assert first["metadata"]["next_offset"] == 2
    first_ids = {item["sider_drug_id"] for item in first["data"]["drugs"]}
    second_ids = {item["sider_drug_id"] for item in second["data"]["drugs"]}
    assert first_ids.isdisjoint(second_ids)


def test_reverse_lookup_deduplicates_drugs_without_losing_frequency():
    tool = SiderTool({"fields": {"operation": "get_drugs_for_side_effect"}})
    html = (
        '<h1>Headache</h1><li><a href="/drugs/1/">Drug 1</a>: common</li>'
        '<li><a href="/drugs/1/">Drug 1</a></li>'
        '<li><a href="/drugs/2/">Drug 2</a>: rare</li>'
    )
    tool.session.get = MagicMock(return_value=_response(html))
    result = tool.run({"meddra_code": "C0018681", "limit": 10})
    assert result["metadata"]["source_association_rows"] == 3
    assert result["metadata"]["unique_drugs"] == 2
    assert result["metadata"]["duplicate_source_rows"] == 1
    assert result["data"]["drugs"][0]["frequency_info"] == "common"
    assert result["data"]["drugs"][0]["source_row_count"] == 2


@pytest.mark.parametrize(
    "arguments",
    [
        {"sider_drug_id": "2244", "limit": 0},
        {"sider_drug_id": "2244", "limit": "2"},
        {"sider_drug_id": "2244", "offset": -1},
    ],
)
def test_invalid_paging_is_rejected_before_network(arguments):
    tool = SiderTool({"fields": {"operation": "get_side_effects"}})
    tool.session.get = MagicMock()
    result = tool.run(arguments)
    assert result["status"] == "error"
    tool.session.get.assert_not_called()


def test_conflicting_identifiers_are_not_silently_ignored():
    tool = SiderTool({"fields": {"operation": "get_side_effects"}})
    tool.session.get = MagicMock()
    result = tool.run({"sider_drug_id": "2244", "drug_name": "ibuprofen"})
    assert result["status"] == "error"
    assert "not both" in result["error"]
    tool.session.get.assert_not_called()


def test_http_status_is_preserved_in_error():
    tool = SiderTool({"fields": {"operation": "get_side_effects"}})
    tool.session.get = MagicMock(return_value=_response("unavailable", status=503))
    result = tool.run({"sider_drug_id": "2244"})
    assert result["status"] == "error"
    assert "HTTP 503" in result["error"]
