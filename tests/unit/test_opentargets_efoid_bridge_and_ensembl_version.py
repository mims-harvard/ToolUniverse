"""Unit tests for two OpenTargets input-normalization fixes.

- efoId -> diseaseIds bridge: OpenTargets_search_gwas_studies_by_disease keys on
  the diseaseIds ARRAY, but every other OT disease tool uses `efoId`, so passing
  efoId was silently ignored and returned a plausible "0 studies" success
  (Parkinson's MONDO_0005180: efoId -> 0, diseaseIds -> 103).
- Versioned Ensembl id: UniProt_id_mapping emits 'ENSG00000120659.16', which
  OpenTargets rejects -- only the unversioned form works.
"""
from unittest.mock import patch

import pytest

from tooluniverse.graphql_tool import OpentargetTool


def _tool(query):
    return OpentargetTool(
        {
            "name": "t",
            "query_schema": query,
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _vars_for(query, arguments):
    tool = _tool(query)
    captured = {}

    def fake_exec(endpoint_url, query, variables=None):
        captured["variables"] = variables
        return {"data": {"x": 1}}

    with patch("tooluniverse.graphql_tool.execute_query", side_effect=fake_exec):
        tool.run(arguments)
    return captured["variables"]


@pytest.mark.unit
def test_efoid_bridged_to_diseaseids_array():
    query = "query q($diseaseIds: [String!]) { x(diseaseIds: $diseaseIds) }"
    variables = _vars_for(query, {"efoId": "MONDO_0005180"})
    assert variables.get("diseaseIds") == ["MONDO_0005180"]
    assert "efoId" not in variables


@pytest.mark.unit
def test_explicit_diseaseids_not_overridden():
    query = "query q($diseaseIds: [String!]) { x(diseaseIds: $diseaseIds) }"
    variables = _vars_for(query, {"diseaseIds": ["MONDO_0000001"]})
    assert variables["diseaseIds"] == ["MONDO_0000001"]


@pytest.mark.unit
def test_efoid_left_alone_when_query_uses_efoId():
    query = "query q($efoId: String!) { x(efoId: $efoId) }"
    variables = _vars_for(query, {"efoId": "MONDO_0005180"})
    assert variables["efoId"] == "MONDO_0005180"
    assert "diseaseIds" not in variables


@pytest.mark.unit
def test_versioned_ensembl_id_stripped():
    query = "query q($ensemblId: String!) { x(ensemblId: $ensemblId) }"
    variables = _vars_for(query, {"ensemblId": "ENSG00000120659.16"})
    assert variables["ensemblId"] == "ENSG00000120659"


@pytest.mark.unit
def test_unversioned_ensembl_id_unchanged():
    query = "query q($ensemblId: String!) { x(ensemblId: $ensemblId) }"
    variables = _vars_for(query, {"ensemblId": "ENSG00000120659"})
    assert variables["ensemblId"] == "ENSG00000120659"
