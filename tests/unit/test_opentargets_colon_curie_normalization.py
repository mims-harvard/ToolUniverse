"""Unit test: OpenTargets disease-id colon->underscore normalization.

Regression: OpenTargets keys diseases/phenotypes as 'MONDO_0010315', but every
other tool (HPO, Monarch, and OpenTargets' OWN xref output) emits the canonical
colon CURIE 'MONDO:0010315'. Feeding the colon form to
OpenTargets_map_any_disease_id_to_all_other_ids returned a silent empty (just the
echoed term, no cross-refs) -- even the tool's documented 'OMIM:604302' example
was broken. The colon CURIE is now normalized to underscore before the query.
"""
from unittest.mock import patch

import pytest

from tooluniverse.graphql_tool import OpentargetTool


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("MONDO:0010315", "MONDO_0010315"),
        ("EFO:0005555", "EFO_0005555"),
        ("OMIM:604302", "OMIM_604302"),
        ("Orphanet:276", "Orphanet_276"),
        ("UMLS:C1279481", "UMLS_C1279481"),
    ],
)
def test_colon_curie_normalized_to_underscore(raw, expected):
    assert OpentargetTool._normalize_ot_disease_id(raw) == expected


@pytest.mark.unit
def test_underscore_and_non_curie_untouched():
    assert OpentargetTool._normalize_ot_disease_id("MONDO_0010315") == "MONDO_0010315"
    # Ensembl / ChEMBL ids have no colon -> unchanged.
    assert OpentargetTool._normalize_ot_disease_id("ENSG00000116745") == (
        "ENSG00000116745"
    )
    assert OpentargetTool._normalize_ot_disease_id("CHEMBL25") == "CHEMBL25"


def _tool(query, params_key):
    cfg = {
        "name": "t",
        "query_schema": f"query q(${params_key}: String!) {{ x({params_key}: ${params_key}) }}",
        "parameter": {"type": "object", "properties": {params_key: {"type": "string"}}},
    }
    return OpentargetTool(cfg)


@pytest.mark.unit
def test_run_normalizes_inputId_and_efoId():
    for key in ("inputId", "efoId"):
        tool = _tool("q", key)
        captured = {}

        def fake_exec(endpoint_url, query, variables=None):
            captured["variables"] = variables
            return {"data": {"x": 1}}

        with patch("tooluniverse.graphql_tool.execute_query", side_effect=fake_exec):
            tool.run({key: "MONDO:0010315"})
        assert captured["variables"][key] == "MONDO_0010315"
