"""XMLTool._search must rank matches by quality before truncating to `limit`.

Regression for Feature-27B-01: _search truncated the result page *while*
scanning records in document order, so callers got "the first N records in the
file that matched anything". Searching DrugBank for "Aspirin" answered with
caffeine's chemistry -- ten combination products that merely carry "Aspirin"
inside a brand name sit earlier in the file and filled the whole page, while
DB00945 Acetylsalicylic acid (an exact synonym hit) fell off it entirely.

The real DrugBank/MeSH datasets are large HF downloads that CI does not have,
so these tests drive XMLDatasetTool against a small synthetic XML file via the
`local_dataset_path` setting.
"""

import pytest

pytestmark = pytest.mark.unit


NS = "http://www.drugbank.ca"

# Document order deliberately mirrors the real symptom: several weak
# brand-name-only matches come first, the record the caller actually wants
# comes last, and there are more matches than `limit`.
RECORDS = [
    # (drugbank_id, name, synonyms, brand_names)
    ("DB00201", "Caffeine", ["1,3,7-trimethylxanthine"], ["Aspirin Complex", "Anacin"]),
    ("DB00316", "Acetaminophen", ["Paracetamol"], ["Aspirin Plus Tylenol"]),
    ("DB00318", "Codeine", ["Methylmorphine"], ["Codeine with Aspirin"]),
    ("DB00338", "Omeprazole", ["Omeprazolum"], ["Aspirin and Omeprazole"]),
    ("DB00497", "Oxycodone", ["Dihydrohydroxycodeinone"], ["Oxycodone and Aspirin"]),
    (
        "DB00945",
        "Acetylsalicylic acid",
        ["Acetylsalicylsaeure", "Aspirin"],
        ["Aspirin 81", "Bayer"],
    ),
    ("DB09999", "Aspirin-like decoy", ["decoy"], ["Nothing"]),
]


def _write_dataset(tmp_path):
    parts = [f'<drugbank xmlns="{NS}">']
    for db_id, name, synonyms, brands in RECORDS:
        syn = "".join(f"<synonym>{s}</synonym>" for s in synonyms)
        prod = "".join(f"<product><name>{b}</name></product>" for b in brands)
        parts.append(
            f'<drug><drugbank-id primary="true">{db_id}</drugbank-id>'
            f"<name>{name}</name>"
            f"<synonyms>{syn}</synonyms>"
            f"<products>{prod}</products></drug>"
        )
    parts.append("</drugbank>")
    path = tmp_path / "drugbank_sample.xml"
    path.write_text("".join(parts), encoding="utf-8")
    return str(path)


def _make_tool(tmp_path, limit_default=10):
    from tooluniverse.xml_tool import XMLDatasetTool

    config = {
        "name": "drugbank_get_drug_chemistry_by_drug_name_or_drugbank_id",
        "parameter": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": limit_default},
                "exact_match": {"type": "boolean", "default": False},
            },
            "required": ["query"],
        },
        "settings": {
            "local_dataset_path": _write_dataset(tmp_path),
            "record_xpath": "db:drug",
            "namespaces": {"db": NS},
            # Declared in identity-strength order, exactly as the real config.
            "search_fields": ["drug_name", "drugbank_id", "synonyms", "brand_names"],
            "field_mappings": {
                "drug_name": "db:name",
                "drugbank_id": "db:drugbank-id[@primary='true']",
                "synonyms": "db:synonyms/db:synonym",
                "brand_names": "db:products/db:product/db:name",
            },
        },
    }
    tool = XMLDatasetTool(config)
    assert tool.records, "synthetic dataset failed to load"
    return tool


def _names(result):
    return [r["drug_name"] for r in result["data"]["results"]]


def test_exact_synonym_hit_is_not_pushed_off_the_page_by_brand_name_hits(tmp_path):
    tool = _make_tool(tmp_path)
    result = tool.run({"query": "Aspirin", "limit": 3})

    assert result["status"] == "success"
    names = _names(result)
    # Feature-27B-01: previously this page was Caffeine/Acetaminophen/Codeine
    # and the record actually named by the query was absent entirely.
    assert "Acetylsalicylic acid" in names, names
    assert names[0] == "Acetylsalicylic acid", names


def test_field_priority_orders_the_substring_tier(tmp_path):
    tool = _make_tool(tmp_path)
    result = tool.run({"query": "Aspirin", "limit": 30})
    names = _names(result)

    # Tier 0 (exact whole-value hit) first, then substring hits ordered by the
    # declared search_fields index: drug_name before brand_names.
    assert names[0] == "Acetylsalicylic acid", names
    assert names[1] == "Aspirin-like decoy", names
    assert names[2:] == [
        "Caffeine",
        "Acetaminophen",
        "Codeine",
        "Omeprazole",
        "Oxycodone",
    ], names


def test_totals_and_search_parameters_are_unchanged(tmp_path):
    tool = _make_tool(tmp_path)
    result = tool.run({"query": "Aspirin", "limit": 3})
    data = result["data"]

    assert data["query"] == "Aspirin"
    assert data["total_matches"] == 7  # every match still counted
    assert data["total_returned_results"] == 3
    assert data["search_parameters"] == {
        "case_sensitive": False,
        "exact_match": False,
        "limit": 3,
    }
    assert data["results"][0]["matched_fields"] == ["synonyms", "brand_names"]
    assert data["results"][0]["drugbank_id"] == "DB00945"


def test_exact_match_mode_degrades_to_field_priority_then_document_order(tmp_path):
    tool = _make_tool(tmp_path)
    result = tool.run({"query": "Aspirin", "exact_match": True, "limit": 30})
    names = _names(result)

    # Only the whole-value synonym hit qualifies under exact_match.
    assert names == ["Acetylsalicylic acid"], names
    assert result["data"]["total_matches"] == 1


def test_ranking_is_generic_not_drugbank_specific(tmp_path):
    """A MeSH-shaped config with different fields gets the same treatment."""
    from tooluniverse.xml_tool import XMLDatasetTool

    path = tmp_path / "mesh_sample.xml"
    path.write_text(
        "<records>"
        "<rec><id>D1</id><term>Heart Diseases, Congenital</term></rec>"
        "<rec><id>D2</id><term>Heart Failure</term></rec>"
        "<rec><id>D3</id><term>Heart</term></rec>"
        "</records>",
        encoding="utf-8",
    )
    tool = XMLDatasetTool(
        {
            "name": "mesh_get_subjects_by_subject_name",
            "parameter": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "settings": {
                "local_dataset_path": str(path),
                "record_xpath": "rec",
                "search_fields": ["subject_name", "subject_id"],
                "field_mappings": {"subject_name": "term", "subject_id": "id"},
            },
        }
    )
    result = tool.run({"query": "Heart", "limit": 1})
    assert [r["subject_name"] for r in result["data"]["results"]] == ["Heart"]
    assert result["data"]["total_matches"] == 3
