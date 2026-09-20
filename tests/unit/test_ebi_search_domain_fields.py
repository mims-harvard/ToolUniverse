"""ebi_get_domain_fields returned [] for every EBI Search domain.

The tool read `fields` / `domain.fields`, but the current EBI Search response nests
the field list as {"domains": [{"id": ..., "fieldInfos": [...]}]}; uniprot has 228
fields and ensembl_gene 109, yet the tool reported none. Shape trimmed from the real
`GET /ebisearch/ws/rest/ensembl_gene?format=json` response.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ebi_search_tool import EBISearchRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return EBISearchRESTTool(
        {
            "name": "ebi_get_domain_fields",
            "fields": {"endpoint": "", "extract_path": "fields"},
        }
    )


REAL_SHAPE = {
    "domains": [
        {
            "id": "ensembl_gene",
            "name": "Ensembl Gene",
            "indexInfos": [{"name": "lastUpdate", "value": "2025-01-01"}],
            "fieldInfos": [
                {
                    "id": "UNIPROT_SWISSPROT",
                    "name": "UNIPROT_SWISSPROT",
                    "retrievable": "true",
                },
                {"id": "CHEMBL", "name": "CHEMBL", "retrievable": "true"},
            ],
        }
    ]
}


def test_fields_are_read_from_domains_fieldinfos():
    fields = _tool()._extract_data(REAL_SHAPE, "fields")
    assert [f["id"] for f in fields] == ["UNIPROT_SWISSPROT", "CHEMBL"]


def test_parent_domain_without_fieldinfos_returns_empty_list():
    parent = {"domains": [{"id": "ensembl", "name": "Ensembl", "subdomains": []}]}
    assert _tool()._extract_data(parent, "fields") == []


def test_legacy_shapes_still_work():
    assert _tool()._extract_data({"fields": [{"id": "a"}]}, "fields") == [{"id": "a"}]
    assert _tool()._extract_data({"domain": {"fields": [{"id": "b"}]}}, "fields") == [
        {"id": "b"}
    ]


def test_unexpected_payload_returns_empty_list():
    assert _tool()._extract_data({"domains": []}, "fields") == []
    assert _tool()._extract_data({}, "fields") == []
