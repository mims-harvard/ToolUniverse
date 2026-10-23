"""Regression test for reachable ChEBI compound names."""

from unittest.mock import Mock

from tooluniverse.chebi_tool import ChEBITool


def test_compound_pages_names_across_name_types(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "id": 15365,
        "names": {
            "SYNONYM": [{"name": f"syn-{i}"} for i in range(15)],
            "BRAND NAME": [{"name": f"brand-{i}"} for i in range(15)],
        },
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.chebi_tool.requests.get", lambda *a, **k: response
    )
    tool = ChEBITool(
        {
            "name": "ChEBI_get_compound",
            "fields": {"endpoint_type": "get_compound"},
        }
    )

    data = tool.run({"chebi_id": 15365, "synonym_offset": 12, "synonym_limit": 5})[
        "data"
    ]

    assert data["synonyms"] == ["syn-12", "syn-13", "syn-14", "brand-0", "brand-1"]
    assert data["synonyms_total"] == 30
    assert data["next_synonym_offset"] == 17
