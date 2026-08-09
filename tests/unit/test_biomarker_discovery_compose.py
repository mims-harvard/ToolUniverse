"""Regression guard for Fix Round 12 / Feature-12A-2.

BiomarkerDiscoveryWorkflow's Step 2 (HPA gene search) checked for a
top-level "genes" key on the result of call_tool("HPA_search_genes_by_query",
...), but call_tool() returns the tool's raw envelope
({"status": "success", "data": {"genes": [...]}}), not the unwrapped
payload. The check therefore never matched a real response, always fell
through to a hardcoded fallback of unrelated cancer genes (BRCA1/BRCA2/
TP53/EGFR/MYC) regardless of the actual disease queried, and printed a
misleading "✅ Using fallback cancer genes" success line while doing so.

This test exercises the fix directly: `_extract_genes` must correctly pull
genes out of the real (wrapped) response shape, and the compose script must
no longer contain the hardcoded fallback gene list at all.
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_MODULE_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "tooluniverse"
    / "compose_scripts"
    / "biomarker_discovery.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "biomarker_discovery_under_test", _MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def module():
    return _load_module()


class TestExtractGenes:
    def test_extracts_genes_from_wrapped_envelope(self, module):
        # This is the real shape call_tool() returns for
        # HPA_search_genes_by_query: {"status": ..., "data": {"genes": [...]}}
        result = {
            "status": "success",
            "data": {"genes": [{"gene_name": "BCAS1", "ensembl_id": "ENSG1"}]},
        }
        genes = module._extract_genes(result)
        assert genes == [{"gene_name": "BCAS1", "ensembl_id": "ENSG1"}]

    def test_extracts_genes_from_unwrapped_dict(self, module):
        result = {"genes": [{"gene_name": "TP53"}]}
        assert module._extract_genes(result) == [{"gene_name": "TP53"}]

    def test_extracts_genes_from_bare_list(self, module):
        result = [{"gene_name": "EGFR"}]
        assert module._extract_genes(result) == [{"gene_name": "EGFR"}]

    def test_returns_empty_list_when_no_genes_present(self, module):
        assert module._extract_genes({"status": "success", "data": {}}) == []
        assert module._extract_genes(None) == []
        assert module._extract_genes({"error": "not found"}) == []


class TestNoHardcodedFallback:
    def test_source_no_longer_contains_hardcoded_cancer_genes(self):
        source = _MODULE_PATH.read_text()
        # These gene names must not appear anywhere as a hardcoded
        # substitute -- any mention of them should only come from real API
        # results, never from source-level fallback data.
        for stale_marker in (
            "fallback cancer genes",
            "Breast cancer type 1 susceptibility protein",
        ):
            assert stale_marker not in source


class TestGeneSearchStrategy:
    """End-to-end exercise of compose()'s Step 2 with a fake call_tool that
    mimics the real wrapped envelope shape.
    """

    def test_finds_real_genes_via_wrapped_response(self, module):
        calls = []

        def fake_call_tool(name, args):
            calls.append((name, args))
            if name == "HPA_search_genes_by_query":
                return {
                    "status": "success",
                    "data": {
                        "genes": [
                            {"gene_name": "BCAS1", "ensembl_id": "ENSG00000064787"}
                        ]
                    },
                }
            return {"status": "success", "data": {}}

        result = module.compose(
            {"disease_condition": "breast cancer", "sample_type": "tissue"},
            tooluniverse=None,
            call_tool=fake_call_tool,
        )

        assert result["expression_data"]["genes_found"] == 1
        assert result["expression_data"]["all_candidates"][0]["gene_name"] == "BCAS1"

    def test_no_genes_found_is_reported_honestly_not_faked(self, module):
        def fake_call_tool(name, args):
            if name == "HPA_search_genes_by_query":
                return {"status": "success", "data": {"genes": []}}
            return {"status": "success", "data": {}}

        result = module.compose(
            {"disease_condition": "healthy aging", "sample_type": "blood"},
            tooluniverse=None,
            call_tool=fake_call_tool,
        )

        # Must not silently contain the old fallback genes.
        expr = result["expression_data"]
        assert expr.get("error") == "No genes found with any search strategy"
        candidates = expr.get("all_candidates", [])
        gene_names = {g.get("gene_name") for g in candidates}
        assert not gene_names & {"BRCA1", "BRCA2", "TP53", "EGFR", "MYC"}
