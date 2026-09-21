"""Tools that fail without an API key must declare it.

Running every keyless tool's first example showed ten tools returning "API key
required" / HTTP 401 without declaring the key, while their siblings did: ICD11_get_entity
and ICD11_browse_hierarchy (ICDTool reads ICD_CLIENT_ID/ICD_CLIENT_SECRET), and the
UMLS-backed umls_get_concept_details, icd_search_codes, snomed_search_concepts and
loinc_search_codes (UMLSRESTTool reads UMLS_API_KEY). Undeclared keys are missing from
the key catalog and from any "missing key" handling. VEuPathDB_search_genes_by_organism
and VEuPathDB_get_gene_record now also answer 401, which the key's description used to
deny; their class sends no key, so they are documented rather than declared.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tools(filename):
    return json.loads((DATA / filename).read_text(encoding="utf-8"))


def test_every_umls_backed_tool_declares_the_umls_key():
    tools = [t for t in _tools("umls_tools.json") if t["type"] == "UMLSRESTTool"]
    assert len(tools) >= 5
    for tool in tools:
        assert "UMLS_API_KEY" in tool.get("optional_api_keys", []), tool["name"]


def test_every_icd11_tool_declares_both_client_credentials():
    tools = [t for t in _tools("icd_tools.json") if t["type"] == "ICDTool"]
    assert {t["name"] for t in tools} >= {
        "ICD11_search_diseases",
        "ICD11_get_entity",
        "ICD11_browse_hierarchy",
    }
    for tool in tools:
        assert {"ICD_CLIENT_ID", "ICD_CLIENT_SECRET"} <= set(
            tool.get("optional_api_keys", [])
        ), tool["name"]


def test_icd10_tools_that_need_no_key_do_not_claim_one():
    for tool in _tools("icd_tools.json"):
        if tool["type"] == "ICD10Tool":
            assert not tool.get("optional_api_keys"), tool["name"]


def test_veupathdb_key_description_no_longer_says_the_other_tools_are_keyless():
    tools = {t["name"]: t for t in _tools("veupathdb_tools.json")}
    without = tools["VEuPathDB_list_gene_searches"]["api_key_info"][
        "VEUPATHDB_API_KEY"
    ]["without"]
    assert "the other VEuPathDB tools work keyless" not in without
    for name in ("VEuPathDB_search_genes_by_organism", "VEuPathDB_get_gene_record"):
        assert "401" in tools[name]["description"], name
