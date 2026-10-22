from typing import Any

import pytest

from tooluniverse.reactome_analysis_tool import ReactomeAnalysisTool


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "summary": {"token": "token-1", "type": "OVERREPRESENTATION"},
            "pathwaysFound": 10,
            "pathways": [
                {"stId": "R-HSA-1", "entities": {}, "reactions": {}},
                {"stId": "R-HSA-2", "entities": {}, "reactions": {}},
            ],
        }


@pytest.mark.parametrize(
    ("endpoint", "arguments"),
    [
        ("pathway_enrichment", {"identifiers": "TP53"}),
        ("species_comparison", {"identifiers": "P04637"}),
        ("token_result", {"token": "token-1"}),
        ("expression_analysis", {"identifiers": "TP53\t2.0"}),
        ("species_comparison_v2", {"species": 48892}),
    ],
)
def test_analysis_endpoints_forward_page_and_report_continuation(
    monkeypatch, endpoint: str, arguments: dict[str, Any]
) -> None:
    captured: dict[str, Any] = {}

    def fake_request(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr("tooluniverse.reactome_analysis_tool.requests.post", fake_request)
    monkeypatch.setattr("tooluniverse.reactome_analysis_tool.requests.get", fake_request)
    tool = ReactomeAnalysisTool({"fields": {"endpoint": endpoint}})

    result = tool.run({**arguments, "page": 2, "page_size": 2})

    assert captured["params"]["page"] == 2
    assert captured["params"]["pageSize"] == 2
    assert result["status"] == "success"
    assert result["data"]["page"] == 2
    assert result["data"]["page_size"] == 2
    assert result["data"]["returned"] == 2
    assert result["data"]["has_more"] is True
    assert result["data"]["next_page"] == 3
    assert result["data"]["truncated"] is True


@pytest.mark.parametrize(
    "pagination",
    [
        {"page_size": "2"},
        {"page_size": True},
        {"page_size": 0},
        {"page_size": 51},
        {"page": "2"},
        {"page": 0},
        {"page": False},
    ],
)
def test_analysis_rejects_coerced_or_clamped_pagination(
    monkeypatch, pagination: dict[str, Any]
) -> None:
    def unexpected_request(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("invalid pagination must not reach Reactome")

    monkeypatch.setattr(
        "tooluniverse.reactome_analysis_tool.requests.post", unexpected_request
    )
    tool = ReactomeAnalysisTool({"fields": {"endpoint": "pathway_enrichment"}})
    result = tool.run({"identifiers": "TP53", **pagination})
    assert result["status"] == "error"


def test_legacy_species_argument_is_rejected_instead_of_ignored(monkeypatch) -> None:
    def unexpected_request(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("ignored species filter must not reach Reactome")

    monkeypatch.setattr(
        "tooluniverse.reactome_analysis_tool.requests.post", unexpected_request
    )
    tool = ReactomeAnalysisTool({"fields": {"endpoint": "species_comparison"}})
    result = tool.run({"identifiers": "Trp53", "species": 10090})
    assert result["status"] == "error"
    assert "previously ignored" in result["error"]
    assert "species_comparison_v2" in result["error"]
