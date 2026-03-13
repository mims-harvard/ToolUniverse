"""Tests for bugs found during researcher persona simulations.

Covers:
- Orphanet_get_gene_diseases: gene symbol resolution (FBN1 -> fibrillin 1)
- IntAct network: fallback to EBI Search when direct API returns 404
- SemanticScholar: error responses are proper dicts, not fake paper results
- BioGRID chemical interactions: rejects chemical-only queries
- ChEMBL_search_mechanisms: test example uses correct parameter name
- ClinVar condition search: uses [dis] field tag
- Enrichr: output size limited to prevent combinatorial explosion
- PMC: include_abstract warns when no PMIDs available
- PharmGKB: example annotation ID is valid
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Orphanet gene symbol resolution
# ---------------------------------------------------------------------------
class TestOrphanetGeneSymbolResolution(unittest.TestCase):
    """Orphanet_get_gene_diseases should accept gene symbols like FBN1."""

    def _make_tool(self):
        from tooluniverse.orphanet_tool import OrphanetTool

        config = {
            "name": "Orphanet_get_gene_diseases",
            "type": "OrphanetTool",
            "parameter": {"required": ["operation", "gene_name"]},
        }
        return OrphanetTool(config)

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_gene_symbol_resolved_to_full_name(self, mock_get):
        """When gene name search returns 404, resolve symbol and retry."""
        tool = self._make_tool()

        # First call: /genes/names/FBN1 -> 404
        resp_404 = MagicMock()
        resp_404.status_code = 404
        resp_404.raise_for_status = MagicMock(
            side_effect=__import__("requests").exceptions.HTTPError(response=resp_404)
        )

        # Second call: /genes?page=1 -> gene list with FBN1 symbol
        resp_genes = MagicMock()
        resp_genes.status_code = 200
        resp_genes.json.return_value = {
            "data": {
                "results": [
                    {"HGNC": "3603", "name": "fibrillin 1", "symbol": "FBN1"},
                    {"HGNC": "1234", "name": "other gene", "symbol": "OTHER"},
                ]
            }
        }

        # Third call: /genes/names/fibrillin%201 -> success
        resp_success = MagicMock()
        resp_success.status_code = 200
        resp_success.raise_for_status = MagicMock()
        resp_success.json.return_value = {
            "data": {
                "results": [
                    {
                        "ORPHAcode": "558",
                        "Preferred term": "Marfan syndrome",
                        "DisorderGeneAssociation": [
                            {
                                "Gene": {
                                    "Symbol": "FBN1",
                                    "name": "fibrillin 1",
                                    "GeneType": "gene with protein product",
                                    "Locus": [],
                                },
                                "DisorderGeneAssociationType": "Disease-causing germline mutation(s) in",
                                "DisorderGeneAssociationStatus": "Assessed",
                            }
                        ],
                    }
                ]
            }
        }

        mock_get.side_effect = [resp_404, resp_genes, resp_success]

        result = tool.run(
            {"operation": "get_gene_diseases", "gene_name": "FBN1"}
        )

        self.assertEqual(result["status"], "success")
        self.assertGreater(result["data"]["disease_count"], 0)
        self.assertEqual(result["data"]["diseases"][0]["genes"][0]["symbol"], "FBN1")

    @patch("tooluniverse.orphanet_tool.requests.get")
    def test_full_gene_name_works_directly(self, mock_get):
        """Full gene names like 'fibrillin' should work on first try."""
        tool = self._make_tool()

        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "data": {
                "results": [
                    {
                        "ORPHAcode": "558",
                        "Preferred term": "Marfan syndrome",
                        "DisorderGeneAssociation": [],
                    }
                ]
            }
        }
        mock_get.return_value = resp

        result = tool.run(
            {"operation": "get_gene_diseases", "gene_name": "fibrillin"}
        )
        self.assertEqual(result["status"], "success")
        # Should only make 1 API call (no symbol resolution needed)
        self.assertEqual(mock_get.call_count, 1)


# ---------------------------------------------------------------------------
# IntAct network fallback to EBI Search
# ---------------------------------------------------------------------------
class TestIntActNetworkFallback(unittest.TestCase):
    """intact_get_interaction_network should fall back to EBI Search."""

    def _make_tool(self):
        from tooluniverse.intact_tool import IntActRESTTool

        config = {
            "name": "intact_get_interaction_network",
            "type": "IntActRESTTool",
            "fields": {
                "endpoint": "https://www.ebi.ac.uk/intact/ws/interaction/network/{identifier}"
            },
        }
        return IntActRESTTool(config)

    @patch("tooluniverse.intact_tool.IntActRESTTool._use_ebi_search")
    def test_network_uses_ebi_search(self, mock_ebi):
        """Network queries should route to EBI Search for reliability."""
        mock_ebi.return_value = {
            "status": "success",
            "data": [{"id": "EBI-123"}],
            "count": 1,
            "hitCount": 100,
            "interaction_ids": ["EBI-123"],
        }

        tool = self._make_tool()
        result = tool.run({"identifier": "BRCA1"})

        mock_ebi.assert_called_once()
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["count"], 0)


# ---------------------------------------------------------------------------
# SemanticScholar proper error format
# ---------------------------------------------------------------------------
class TestSemanticScholarErrorFormat(unittest.TestCase):
    """SemanticScholar should return proper error dicts, not fake paper results."""

    def _make_tool(self):
        from tooluniverse.semantic_scholar_tool import SemanticScholarTool

        config = {
            "name": "SemanticScholar_search_papers",
            "type": "SemanticScholarTool",
        }
        return SemanticScholarTool(config)

    def test_missing_query_returns_error_list(self):
        """Missing query should return a list with one error item (consistent with EuropePMC/PMC)."""
        tool = self._make_tool()
        result = tool.run({})

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertIn("query", result[0]["error"])
        self.assertFalse(result[0].get("retryable", True))

    @patch("tooluniverse.semantic_scholar_tool.request_with_retry")
    def test_api_error_returns_error_list(self, mock_request):
        """API errors should return list with one error item (consistent contract)."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.reason = "Too Many Requests"
        mock_request.return_value = mock_resp

        result = tool._search("test query", 5)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("429", result[0]["error"])
        self.assertTrue(result[0]["retryable"])

    @patch("tooluniverse.semantic_scholar_tool.request_with_retry")
    def test_invalid_json_returns_error_list(self, mock_request):
        """Invalid JSON response should return list with one error item."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_request.return_value = mock_resp

        result = tool._search("test query", 5)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("invalid JSON", result[0]["error"])


# ---------------------------------------------------------------------------
# BioGRID chemical interaction guard
# ---------------------------------------------------------------------------
class TestBioGRIDChemicalGuard(unittest.TestCase):
    """BioGRID_get_chemical_interactions should reject chemical-only queries."""

    def _make_tool(self):
        from tooluniverse.biogrid_tool import BioGRIDRESTTool

        config = {
            "name": "BioGRID_get_chemical_interactions",
            "type": "BioGRIDRESTTool",
            "fields": {"endpoint": "/interactions/", "return_format": "JSON"},
            "parameter": {"required": []},
        }
        return BioGRIDRESTTool(config)

    def test_chemical_only_returns_error(self):
        """Chemical-only search should return an error, not misleading PPI data."""
        tool = self._make_tool()
        result = tool.run({"chemical_names": ["Imatinib"]})

        self.assertEqual(result["status"], "error")
        self.assertIn("chemical-only", result["error"])

    def test_no_params_returns_error(self):
        """No gene or chemical names should return an error."""
        tool = self._make_tool()
        result = tool.run({})

        self.assertEqual(result["status"], "error")
        self.assertIn("gene_names", result["error"])


# ---------------------------------------------------------------------------
# ChEMBL_search_mechanisms test example parameter
# ---------------------------------------------------------------------------
class TestChEMBLMechanismsTestExample(unittest.TestCase):
    """ChEMBL_search_mechanisms test examples should use documented params."""

    def test_test_examples_use_documented_params(self):
        """Verify test_examples use drug_chembl_id, not drug_chembl_id__exact."""
        import os

        json_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "chembl_tools.json",
        )
        with open(json_path) as f:
            tools = json.load(f)

        mechanisms_tool = None
        for tool in tools:
            if tool["name"] == "ChEMBL_search_mechanisms":
                mechanisms_tool = tool
                break

        self.assertIsNotNone(mechanisms_tool, "ChEMBL_search_mechanisms not found")

        for i, example in enumerate(mechanisms_tool.get("test_examples", [])):
            self.assertNotIn(
                "drug_chembl_id__exact",
                example,
                f"test_examples[{i}] uses drug_chembl_id__exact instead of drug_chembl_id",
            )


# ---------------------------------------------------------------------------
# ClinVar condition search uses [dis] field tag
# ---------------------------------------------------------------------------
class TestClinVarConditionFieldTag(unittest.TestCase):
    """ClinVar condition searches must use [dis] field tag for eSearch."""

    def _make_tool(self):
        from tooluniverse.clinvar_tool import ClinVarSearchVariants

        config = {
            "name": "ClinVarSearchVariants",
            "type": "ClinVarSearchVariants",
            "fields": {},
        }
        return ClinVarSearchVariants(config)

    @patch("tooluniverse.clinvar_tool.ClinVarRESTTool._make_request")
    def test_condition_uses_dis_field_tag(self, mock_request):
        """Condition searches should append [dis] field tag."""
        mock_request.return_value = {
            "status": "success",
            "data": {
                "esearchresult": {
                    "count": "5",
                    "idlist": ["1", "2", "3", "4", "5"],
                    "querytranslation": "",
                }
            },
        }
        tool = self._make_tool()
        tool.run({"gene": "TP53", "condition": "Li-Fraumeni syndrome"})

        call_args = mock_request.call_args
        term = call_args[1]["params"]["term"] if "params" in (call_args[1] or {}) else call_args[0][1]["term"]
        self.assertIn("[dis]", term)
        self.assertIn("[gene]", term)

    @patch("tooluniverse.clinvar_tool.ClinVarRESTTool._make_request")
    def test_condition_only_uses_dis_field_tag(self, mock_request):
        """Condition-only search should use [dis] field tag."""
        mock_request.return_value = {
            "status": "success",
            "data": {
                "esearchresult": {
                    "count": "10",
                    "idlist": [],
                    "querytranslation": "",
                }
            },
        }
        tool = self._make_tool()
        tool.run({"condition": "Breast cancer"})

        call_args = mock_request.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
        self.assertIn("[dis]", params["term"])
        self.assertIn('"Breast cancer"', params["term"])


# ---------------------------------------------------------------------------
# GxA gene_id client-side filter uses exact match
# ---------------------------------------------------------------------------
class TestGxAGeneFilter(unittest.TestCase):
    """GxA_get_experiment_expression should filter genes by exact ID match."""

    def _make_tool(self):
        from tooluniverse.gxa_tool import GxATool

        config = {
            "name": "GxA_get_experiment_expression",
            "type": "GxATool",
            "fields": {"endpoint": "get_experiment_expression"},
        }
        return GxATool(config)

    @patch("tooluniverse.gxa_tool.requests.get")
    def test_gene_id_filters_exactly(self, mock_get):
        """gene_id filter should match only the exact gene, not substrings."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "experiment": {"description": "Test experiment"},
            "columnHeaders": [
                {"assayGroupId": "g1", "factorValue": "brain", "factorValueOntologyTermId": "", "assayGroupSummary": {"replicates": 3}},
            ],
            "profiles": {
                "rows": [
                    {"id": "ENSG00000130234", "name": "ACE2", "expressions": [{"value": 5.0}]},
                    {"id": "ENSG00000999999", "name": "OTHER", "expressions": [{"value": 3.0}]},
                    {"id": "ENSG00000130234X", "name": "NOTACE2", "expressions": [{"value": 1.0}]},
                ]
            },
        }
        mock_get.return_value = mock_resp

        result = tool.run({"experiment_accession": "E-MTAB-2836", "gene_id": "ENSG00000130234"})

        profiles = result["data"]["gene_profiles"]
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["gene_id"], "ENSG00000130234")


# ---------------------------------------------------------------------------
# Enrichr output size limit
# ---------------------------------------------------------------------------
class TestEnrichrOutputLimit(unittest.TestCase):
    """Enrichr should limit path output to prevent combinatorial explosion."""

    def _make_tool(self):
        from tooluniverse.enrichr_tool import EnrichrTool

        config = {
            "name": "enrichr_gene_enrichment_analysis",
            "type": "EnrichrTool",
        }
        return EnrichrTool(config)

    @patch("tooluniverse.enrichr_tool.EnrichrTool.get_official_gene_name",
           side_effect=lambda g: g)
    @patch("tooluniverse.enrichr_tool.EnrichrTool.submit_gene_list",
           return_value="12345")
    @patch("tooluniverse.enrichr_tool.EnrichrTool.get_enrichment_results")
    def test_paths_limited_to_prevent_explosion(self, mock_enrich, mock_submit, mock_gene):
        """ranked_paths and connections should be truncated."""
        # Mock enrichment results with many terms to create many paths
        mock_enrich.return_value = {
            "TestLib": [
                # [rank, term_name, p-value, z-score, combined_score, genes, ...]
                [1, f"Term_{i}", 0.001, -2.0, 10.0 - i * 0.1, ["GENE1", "GENE2"], 0, 0, 0]
                for i in range(30)
            ]
        }
        tool = self._make_tool()
        connected_path, connections = tool.enrichr_api(
            ["GENE1", "GENE2"], ["TestLib"]
        )

        # connected_path limited to 20
        self.assertLessEqual(len(connected_path), 20)

        # Each connection limited to 5 paths
        for key, paths in connections.items():
            self.assertLessEqual(len(paths), 5)


# ---------------------------------------------------------------------------
# PMC include_abstract warning
# ---------------------------------------------------------------------------
class TestPMCAbstractWarning(unittest.TestCase):
    """PMC should warn when include_abstract fails due to missing PMIDs."""

    def _make_tool(self):
        from tooluniverse.pmc_tool import PMCTool

        config = {"name": "PMC_search_papers", "type": "PMCTool"}
        return PMCTool(config)

    @patch("tooluniverse.pmc_tool.request_with_retry")
    def test_abstract_note_when_no_pmids(self, mock_request):
        """When no PMIDs available, results should have abstract_note."""
        tool = self._make_tool()

        # Mock search response
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {
            "esearchresult": {"idlist": ["123456"]}
        }

        # Mock summary response (XML with no PMID in ArticleIds)
        summary_resp = MagicMock()
        summary_resp.status_code = 200
        summary_resp.raise_for_status = MagicMock()
        summary_resp.text = """<?xml version="1.0"?>
<eSummaryResult>
  <DocSum>
    <Id>123456</Id>
    <Item Name="Title" Type="String">Test Article</Item>
    <Item Name="ArticleIds" Type="List">
      <Item Name="pmc" Type="String">PMC123456</Item>
    </Item>
  </DocSum>
</eSummaryResult>"""

        mock_request.side_effect = [search_resp, summary_resp]

        results = tool._search("test query", limit=5, include_abstract=True)

        self.assertEqual(len(results), 1)
        self.assertIn("abstract_note", results[0])
        self.assertIn("PubMed_search_articles", results[0]["abstract_note"])


# ---------------------------------------------------------------------------
# PharmGKB example annotation ID validity
# ---------------------------------------------------------------------------
class TestPharmGKBExampleID(unittest.TestCase):
    """PharmGKB description example IDs should match test_examples."""

    def test_description_example_id_matches_test_examples(self):
        """The example ID in the description should be a valid one."""
        import os

        json_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "src",
            "tooluniverse",
            "data",
            "pharmgkb_tools.json",
        )
        with open(json_path) as f:
            tools = json.load(f)

        for tool in tools:
            if tool["name"] != "PharmGKB_get_clinical_annotations":
                continue
            # Check the annotation_id description example matches a known-good ID
            ann_param = tool["parameter"]["properties"].get("annotation_id", {})
            desc = ann_param.get("description", "")
            # The example ID 1449309855 was broken; should now be 1447954390
            self.assertNotIn("1449309855", desc)
            self.assertIn("1447954390", desc)
            break


# ---------------------------------------------------------------------------
# ChEMBL target_chembl_id maps to __exact API param
# ---------------------------------------------------------------------------
class TestChEMBLTargetFilter(unittest.TestCase):
    """ChEMBL_search_mechanisms should map target_chembl_id to __exact."""

    def _make_tool(self):
        from tooluniverse.chem_tool import ChEMBLRESTTool

        config = {
            "name": "ChEMBL_search_mechanisms",
            "type": "ChEMBLRESTTool",
            "fields": {"endpoint": "mechanism"},
            "parameter": {"required": []},
        }
        return ChEMBLRESTTool(config)

    def test_target_chembl_id_mapped_to_exact(self):
        """target_chembl_id should be mapped to target_chembl_id__exact in params."""
        tool = self._make_tool()
        params = tool._build_params({"target_chembl_id": "CHEMBL4096", "limit": 5})

        self.assertIn("target_chembl_id__exact", params)
        self.assertEqual(params["target_chembl_id__exact"], "CHEMBL4096")
        # Should NOT have bare target_chembl_id (it's in the exclusion list)
        self.assertNotIn("target_chembl_id", params)

    def test_assay_chembl_id_mapped_to_exact(self):
        """assay_chembl_id should be mapped to assay_chembl_id__exact in params."""
        tool = self._make_tool()
        params = tool._build_params({"assay_chembl_id": "CHEMBL1000001", "limit": 5})

        self.assertIn("assay_chembl_id__exact", params)
        self.assertEqual(params["assay_chembl_id__exact"], "CHEMBL1000001")


# ---------------------------------------------------------------------------
# GTEx gene ID resolution and dataset defaults
# ---------------------------------------------------------------------------
class TestGTExGeneIdResolution(unittest.TestCase):
    """GTEx V2 should resolve gene symbols to versioned GENCODE IDs."""

    def _make_tool(self):
        from tooluniverse.gtex_v2_tool import GTExV2Tool

        config = {
            "name": "GTEx_get_median_gene_expression",
            "type": "GTExV2Tool",
            "parameter": {"required": ["operation"]},
        }
        return GTExV2Tool(config)

    @patch("tooluniverse.gtex_v2_tool.requests.get")
    def test_gene_symbol_resolved_to_versioned_id(self, mock_get):
        """Gene symbols like TP53 should be resolved to versioned GENCODE IDs."""
        tool = self._make_tool()

        # First call: /reference/gene resolves TP53 -> ENSG00000141510.18
        resolve_resp = MagicMock()
        resolve_resp.status_code = 200
        resolve_resp.json.return_value = {
            "data": [{"gencodeId": "ENSG00000141510.18", "geneSymbol": "TP53"}]
        }

        # Second call: /expression/medianGeneExpression with resolved ID
        expr_resp = MagicMock()
        expr_resp.status_code = 200
        expr_resp.json.return_value = {
            "data": [
                {
                    "gencodeId": "ENSG00000141510.18",
                    "tissueSiteDetailId": "Liver",
                    "median": 15.2,
                }
            ],
            "paging_info": {"numberOfPages": 1},
        }

        mock_get.side_effect = [resolve_resp, expr_resp]

        result = tool.run({
            "operation": "get_median_gene_expression",
            "gencode_id": "TP53",
        })

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["num_results"], 1)
        # Verify the resolution call was made
        first_call_url = mock_get.call_args_list[0][0][0]
        self.assertIn("/reference/gene", first_call_url)

    @patch("tooluniverse.gtex_v2_tool.requests.get")
    def test_versioned_id_not_re_resolved(self, mock_get):
        """Already versioned IDs (containing '.') should not trigger resolution."""
        tool = self._make_tool()

        expr_resp = MagicMock()
        expr_resp.status_code = 200
        expr_resp.json.return_value = {
            "data": [{"gencodeId": "ENSG00000141510.18", "median": 10.0}],
            "paging_info": {},
        }
        mock_get.return_value = expr_resp

        result = tool.run({
            "operation": "get_median_gene_expression",
            "gencode_id": "ENSG00000141510.18",
        })

        self.assertEqual(result["status"], "success")
        # Only 1 call (expression), no resolution call
        self.assertEqual(mock_get.call_count, 1)
        # Feature-80A: without tissue, uses clusteredMedianGeneExpression
        self.assertIn("GeneExpression", mock_get.call_args[0][0])

    def test_gene_expression_defaults_to_gtex_v8(self):
        """_get_gene_expression should default to gtex_v8 not gtex_v10."""
        tool = self._make_tool()
        # Check via the handler directly — dataset_id default
        import inspect
        source = inspect.getsource(tool._get_gene_expression)
        self.assertIn("gtex_v8", source)

    def test_median_expression_defaults_to_gtex_v8(self):
        """_get_median_gene_expression should default to gtex_v8."""
        tool = self._make_tool()
        import inspect
        source = inspect.getsource(tool._get_median_gene_expression)
        self.assertIn("gtex_v8", source)


# ---------------------------------------------------------------------------
# IntAct interactor uses correct endpoint
# ---------------------------------------------------------------------------
class TestIntActInteractorEndpoint(unittest.TestCase):
    """IntAct interactor should use findInteractor, not details."""

    def _make_tool(self, tool_name):
        from tooluniverse.intact_tool import IntActRESTTool

        config = {
            "name": tool_name,
            "type": "IntActRESTTool",
            "fields": {},
        }
        return IntActRESTTool(config)

    def test_interactor_url_uses_find(self):
        """intact_get_interactor URL should use /findInteractor/."""
        tool = self._make_tool("intact_get_interactor")
        url = tool._build_url({"identifier": "P04637"})
        self.assertIn("/interactor/findInteractor/P04637", url)
        self.assertNotIn("/details/", url)

    def test_network_url_uses_find_interactions(self):
        """intact_get_interaction_network URL should use /findInteractions/."""
        tool = self._make_tool("intact_get_interaction_network")
        url = tool._build_url({"identifier": "P04637"})
        self.assertIn("/interaction/findInteractions/P04637", url)
        self.assertNotIn("/network/", url)

    @patch("tooluniverse.intact_tool.IntActRESTTool._use_ebi_search")
    def test_interactor_not_routed_to_ebi_search(self, mock_ebi):
        """intact_get_interactor should NOT be routed to EBI Search."""
        tool = self._make_tool("intact_get_interactor")

        # Mock the session.get to return paginated interactor data
        with patch.object(tool.session, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "application/json"}
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "content": [
                    {
                        "interactorAc": "EBI-366083",
                        "interactorName": "p53",
                        "interactorType": "protein",
                        "interactionCount": 2243,
                    }
                ],
                "totalElements": 1,
            }
            mock_resp.url = "https://example.com"
            mock_get.return_value = mock_resp

            result = tool.run({"identifier": "P04637"})

        mock_ebi.assert_not_called()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["totalElements"], 1)

    @patch("tooluniverse.intact_tool.IntActRESTTool._use_ebi_search")
    def test_paginated_response_handled(self, mock_ebi):
        """Paginated responses should extract content and totalElements."""
        tool = self._make_tool("intact_get_interaction_network")

        with patch.object(tool.session, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "application/json"}
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                "content": [{"id": "1"}, {"id": "2"}],
                "totalElements": 500,
            }
            mock_resp.url = "https://example.com"
            mock_get.return_value = mock_resp

            result = tool.run({"identifier": "BRCA1"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["totalElements"], 500)
        self.assertIn("note", result)


# ---------------------------------------------------------------------------
# Response truncation
# ---------------------------------------------------------------------------
class TestResponseTruncation(unittest.TestCase):
    """MCP server should truncate oversized responses."""

    def setUp(self):
        try:
            from tooluniverse.smcp import _truncate_response
        except Exception as e:
            self.skipTest(f"SMCP not available: {e}")

        self._truncate_response = _truncate_response
        self._temp_files = []

    def tearDown(self):
        for path in self._temp_files:
            if os.path.isfile(path):
                os.unlink(path)

    def _truncate_and_parse(self, data, max_chars=50_000):
        """Helper: serialize, truncate, parse result, and track temp files."""
        serialized = json.dumps(data, ensure_ascii=False)
        result = self._truncate_response(data, serialized, max_chars)
        parsed = json.loads(result)
        if "_full_result_file" in parsed:
            self._temp_files.append(parsed["_full_result_file"])
        return parsed

    def test_truncate_list_response(self):
        big_list = [{"id": i, "data": "x" * 500} for i in range(500)]
        parsed = self._truncate_and_parse(big_list)

        self.assertTrue(parsed["_truncated"])
        self.assertEqual(parsed["_total"], 500)
        self.assertLess(parsed["_showing"], 500)

        # Full result file should be saved with all original data
        full_path = parsed["_full_result_file"]
        self.assertTrue(os.path.isfile(full_path))
        with open(full_path) as f:
            full_data = json.load(f)
        self.assertEqual(len(full_data), 500)

    def test_truncate_dict_with_large_list(self):
        big_dict = {
            "status": "success",
            "data": [{"id": i, "payload": "y" * 1000} for i in range(200)],
        }
        parsed = self._truncate_and_parse(big_dict)

        self.assertTrue(parsed["_truncated"])
        self.assertIn("_data_total", parsed)
        self.assertIn("_full_result_file", parsed)
        self.assertTrue(os.path.isfile(parsed["_full_result_file"]))

    def test_truncate_saves_full_result_to_file(self):
        """Full response file contains complete original data with metadata note."""
        big_list = [{"id": i, "value": "z" * 300} for i in range(400)]
        parsed = self._truncate_and_parse(big_list)

        full_path = parsed["_full_result_file"]
        self.assertTrue(full_path.endswith(".json"))

        with open(full_path) as f:
            restored = json.load(f)
        self.assertEqual(len(restored), 400)
        self.assertEqual(restored[0]["id"], 0)
        self.assertEqual(restored[399]["id"], 399)

        self.assertIn(full_path, parsed["_full_result_note"])

    def test_small_response_not_truncated(self):
        """Responses under the limit should still return valid JSON."""
        small = {"status": "success", "data": [1, 2, 3]}
        parsed = self._truncate_and_parse(small, max_chars=100_000)
        self.assertIsNotNone(parsed)


# ---------------------------------------------------------------------------
# ClinicalTrials search returns null fields
# ---------------------------------------------------------------------------
class TestClinicalTrialsSearchFields(unittest.TestCase):
    """ClinicalTrials_search_studies should return populated metadata fields."""

    def _make_tool(self):
        from tooluniverse.clinicaltrials_tool import CTGovAPITool

        config = {
            "name": "ClinicalTrials_search_studies",
            "type": "CTGovAPITool",
        }
        return CTGovAPITool(config)

    @patch("tooluniverse.clinicaltrials_tool.requests.get")
    def test_search_does_not_use_fields_param(self, mock_get):
        """Search should NOT pass 'fields' param (it breaks nested response format)."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "totalCount": 1,
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT00000001",
                            "briefTitle": "Test Study",
                        },
                        "statusModule": {
                            "overallStatus": "RECRUITING",
                            "startDateStruct": {"date": "2025-01-01"},
                            "completionDateStruct": {"date": "2026-12-31"},
                        },
                        "designModule": {
                            "studyType": "INTERVENTIONAL",
                            "phases": ["PHASE3"],
                            "enrollmentInfo": {"count": 500},
                        },
                        "conditionsModule": {"conditions": ["NSCLC"]},
                        "armsInterventionsModule": {
                            "interventions": [
                                {"name": "Pembrolizumab", "type": "DRUG"}
                            ]
                        },
                        "sponsorCollaboratorsModule": {
                            "leadSponsor": {"name": "NCI"}
                        },
                    }
                }
            ],
        }
        mock_get.return_value = mock_resp

        result = tool.run({"operation": "search", "query_cond": "NSCLC"})

        # Verify 'fields' param was NOT sent
        call_params = mock_get.call_args[1].get("params", {})
        self.assertNotIn("fields", call_params)

        # Verify nested data was extracted correctly
        study = result["data"]["studies"][0]
        self.assertEqual(study["nct_id"], "NCT00000001")
        self.assertEqual(study["start_date"], "2025-01-01")
        self.assertEqual(study["enrollment"], 500)
        self.assertEqual(study["sponsor"], "NCI")
        self.assertEqual(study["interventions"], ["Pembrolizumab"])


class TestGTExWrapperDefaults(unittest.TestCase):
    """GTEx wrapper functions should default to gtex_v8."""

    def test_median_wrapper_defaults_v8(self):
        """GTEx_get_median_gene_expression wrapper should default to gtex_v8."""
        import inspect
        from tooluniverse.tools.GTEx_get_median_gene_expression import (
            GTEx_get_median_gene_expression,
        )
        sig = inspect.signature(GTEx_get_median_gene_expression)
        default = sig.parameters["dataset_id"].default
        self.assertEqual(default, "gtex_v8")

    def test_gene_expression_wrapper_defaults_v8(self):
        """GTEx_get_gene_expression wrapper should default to gtex_v8."""
        import inspect
        from tooluniverse.tools.GTEx_get_gene_expression import (
            GTEx_get_gene_expression,
        )
        sig = inspect.signature(GTEx_get_gene_expression)
        default = sig.parameters["dataset_id"].default
        self.assertEqual(default, "gtex_v8")


# ---------------------------------------------------------------------------
# Operation auto-fill tests (redundant operation parameter removed from required)
# ---------------------------------------------------------------------------
class TestOperationAutoFill(unittest.TestCase):
    """Test that tools auto-fill 'operation' from config const when not provided."""

    def _load_config(self, json_file, tool_name):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../../src/tooluniverse/data",
            json_file,
        )
        with open(path) as f:
            tools = json.load(f)
        return [t for t in tools if t["name"] == tool_name][0]

    def test_orphanet_operation_not_required(self):
        """Orphanet tools should NOT require 'operation' in parameter schema."""
        config = self._load_config("orphanet_tools.json", "Orphanet_search_diseases")
        self.assertNotIn("operation", config["parameter"]["required"])

    def test_orphanet_auto_fills_operation(self):
        """Orphanet tool should auto-fill operation from config const."""
        from tooluniverse.orphanet_tool import OrphanetTool
        config = self._load_config("orphanet_tools.json", "Orphanet_search_diseases")
        tool = OrphanetTool(config)
        # Mock the _search_diseases method to verify routing works
        tool._search_diseases = MagicMock(return_value={"status": "success"})
        tool.run({"query": "Marfan"})  # No operation param
        tool._search_diseases.assert_called_once()

    def test_gencc_auto_fills_operation(self):
        """GenCC tool should auto-fill operation from config const."""
        from tooluniverse.gencc_tool import GenCCTool
        config = self._load_config("gencc_tools.json", "GenCC_search_disease")
        tool = GenCCTool(config)
        tool._search_disease = MagicMock(return_value={"status": "success"})
        tool.run({"disease": "Marfan"})  # No operation param
        tool._search_disease.assert_called_once()

    def test_gpcrdb_auto_fills_operation(self):
        """GPCRdb tool should auto-fill operation from config const."""
        from tooluniverse.gpcrdb_tool import GPCRdbTool
        config = self._load_config("gpcrdb_tools.json", "GPCRdb_get_protein")
        tool = GPCRdbTool(config)
        tool._get_protein = MagicMock(return_value={"status": "success"})
        tool.run({"protein": "adrb2_human"})  # No operation param
        tool._get_protein.assert_called_once()

    def test_omim_auto_fills_operation(self):
        """OMIM tool should auto-fill operation from config const."""
        from tooluniverse.omim_tool import OMIMTool
        config = self._load_config("omim_tools.json", "OMIM_search")
        tool = OMIMTool(config)
        tool.api_key = "fake_key"  # bypass API key check
        tool._search = MagicMock(return_value={"status": "success"})
        tool.run({"query": "Marfan"})  # No operation param
        tool._search.assert_called_once()

    def test_disgenet_auto_fills_operation(self):
        """DisGeNET tool should auto-fill operation from config const."""
        from tooluniverse.disgenet_tool import DisGeNETTool
        config = self._load_config("disgenet_tools.json", "DisGeNET_search_gene")
        tool = DisGeNETTool(config)
        tool.api_key = "fake_key"  # bypass API key check
        tool._search_gene = MagicMock(return_value={"status": "success"})
        tool.run({"gene_symbol": "FBN1"})  # No operation param
        tool._search_gene.assert_called_once()

    def test_all_fixed_jsons_no_operation_required(self):
        """All fixed JSON files should NOT have 'operation' in required."""
        fixed_jsons = [
            "orphanet_tools.json", "gencc_tools.json", "brenda_tools.json",
            "dailymed_tools.json", "disgenet_tools.json", "emolecules_tools.json",
            "enamine_tools.json", "faers_analytics_tools.json",
            "fda_orange_book_tools.json", "gpcrdb_tools.json", "hmdb_tools.json",
            "imgt_tools.json", "metacyc_tools.json", "ncbi_nucleotide_tools.json",
            "ols_tools.json", "omim_tools.json", "oncokb_tools.json",
            "sabdab_tools.json",
        ]
        import os
        data_dir = os.path.join(
            os.path.dirname(__file__), "../../src/tooluniverse/data"
        )
        for jf in fixed_jsons:
            path = os.path.join(data_dir, jf)
            if not os.path.exists(path):
                continue
            with open(path) as f:
                tools = json.load(f)
            for t in tools:
                req = t.get("parameter", {}).get("required", [])
                props = t.get("parameter", {}).get("properties", {})
                if props.get("operation", {}).get("const"):
                    self.assertNotIn(
                        "operation", req,
                        f"{t['name']} in {jf} still has operation in required"
                    )


# ---------------------------------------------------------------------------
# Monarch remove_empty_values preserves 0 and empty lists
# ---------------------------------------------------------------------------
class TestMonarchRemoveEmptyValues(unittest.TestCase):
    """Monarch tool should preserve 0 and [] in API responses."""

    def test_zero_total_preserved(self):
        """total: 0 should NOT be stripped from response."""
        from tooluniverse.restful_tool import MonarchTool

        config = {
            "name": "get_HPO_ID_by_phenotype",
            "type": "Monarch",
            "tool_url": "/search",
            "query_schema": {
                "query": None,
                "category": ["biolink:PhenotypicFeature"],
                "limit": 20,
                "offset": 0,
            },
            "parameter": {"properties": {}},
        }
        tool = MonarchTool(config)

        # Simulate Monarch API returning 0 results
        mock_response = {"total": 0, "items": [], "limit": 20, "offset": 0}

        with patch("tooluniverse.restful_tool.execute_RESTful_query",
                    return_value=mock_response):
            result = tool.run({"query": "nonexistent phenotype"})

        self.assertEqual(result["total"], 0)
        self.assertEqual(result["items"], [])
        self.assertIn("limit", result)

    def test_zero_descendant_count_preserved(self):
        """descendant_count: 0 should NOT be stripped."""
        from tooluniverse.restful_tool import MonarchTool

        config = {
            "name": "get_HPO_ID_by_phenotype",
            "type": "Monarch",
            "tool_url": "/search",
            "query_schema": {"query": None, "limit": 5},
            "parameter": {"properties": {}},
        }
        tool = MonarchTool(config)

        mock_response = {
            "total": 1,
            "items": [
                {
                    "id": "HP:0001250",
                    "name": "Seizure",
                    "has_descendant_count": 0,
                    "description": None,
                }
            ],
            "limit": 5,
        }

        with patch("tooluniverse.restful_tool.execute_RESTful_query",
                    return_value=mock_response):
            result = tool.run({"query": "seizure"})

        item = result["items"][0]
        self.assertEqual(item["has_descendant_count"], 0)
        # None values should still be stripped
        self.assertNotIn("description", item)


# ---------------------------------------------------------------------------
# CTD mitochondrial gene name normalization
# ---------------------------------------------------------------------------
class TestCTDMitoGeneNormalization(unittest.TestCase):
    """CTD tool should strip MT- prefix for mitochondrial gene queries."""

    def _make_tool(self, input_type="gene"):
        from tooluniverse.ctd_tool import CTDTool

        config = {
            "name": "CTD_get_gene_diseases",
            "type": "CTDTool",
            "fields": {"input_type": input_type, "report_type": "diseases_curated"},
        }
        return CTDTool(config)

    @patch("tooluniverse.ctd_tool.requests.get")
    def test_mt_prefix_stripped(self, mock_get):
        """MT-ND5 should be normalized to ND5 for CTD queries."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = '[{"GeneSymbol": "ND5", "DiseaseName": "MELAS"}]'
        mock_resp.json.return_value = [
            {"GeneSymbol": "ND5", "DiseaseName": "MELAS"}
        ]
        mock_get.return_value = mock_resp

        result = tool.run({"input_terms": "MT-ND5"})

        # Verify API was called with ND5, not MT-ND5
        call_params = mock_get.call_args[1].get("params", {})
        self.assertEqual(call_params["inputTerms"], "ND5")

        # Verify metadata includes normalization note
        self.assertIn("normalized_query", result["metadata"])
        self.assertEqual(result["metadata"]["normalized_query"], "ND5")

    @patch("tooluniverse.ctd_tool.requests.get")
    def test_non_mito_gene_unchanged(self, mock_get):
        """Non-mitochondrial genes should NOT be modified."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = '[{"GeneSymbol": "BRCA1"}]'
        mock_resp.json.return_value = [{"GeneSymbol": "BRCA1"}]
        mock_get.return_value = mock_resp

        result = tool.run({"input_terms": "BRCA1"})

        call_params = mock_get.call_args[1].get("params", {})
        self.assertEqual(call_params["inputTerms"], "BRCA1")
        self.assertNotIn("normalized_query", result["metadata"])

    @patch("tooluniverse.ctd_tool.requests.get")
    def test_mt_prefix_only_for_gene_type(self, mock_get):
        """MT- prefix stripping should only apply to gene input_type."""
        tool = self._make_tool(input_type="chem")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = "[]"
        mock_resp.json.return_value = []
        mock_get.return_value = mock_resp

        tool.run({"input_terms": "MT-ND5"})

        call_params = mock_get.call_args[1].get("params", {})
        # Chemical queries should NOT strip MT-
        self.assertEqual(call_params["inputTerms"], "MT-ND5")


# ---------------------------------------------------------------------------
# ClinGen variant classifications coverage note
# ---------------------------------------------------------------------------
class TestClinGenVariantClassificationNote(unittest.TestCase):
    """ClinGen should add helpful note when no variant classifications found."""

    def _make_tool(self):
        from tooluniverse.clingen_tool import ClinGenTool

        config = {
            "name": "ClinGen_get_variant_classifications",
            "type": "ClinGenTool",
            "fields": {"operation": "get_variant_classifications", "timeout": 30},
            "parameter": {"required": []},
        }
        return ClinGenTool(config)

    @patch("tooluniverse.clingen_tool.requests.get")
    def test_empty_results_include_note(self, mock_get):
        """When no classifications found for a gene, include helpful note."""
        tool = self._make_tool()

        # Mock TSV response with only header (no data for the gene)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = (
            "#Variation\tClinVar Variation Id\tHGNC Gene Symbol\n"
            "NM_000277.2:c.1A>G\t586\tPAH\n"
        )
        mock_get.return_value = mock_resp

        result = tool.run({"gene": "LRRK2"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total"], 0)
        self.assertIn("note", result)
        self.assertIn("VCEP", result["note"])
        self.assertIn("LRRK2", result["note"])

    @patch("tooluniverse.clingen_tool.requests.get")
    def test_results_found_no_note(self, mock_get):
        """When classifications are found, no note is needed."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = (
            "#Variation\tClinVar Variation Id\tHGNC Gene Symbol\tDisease\n"
            "NM_000277.2:c.1A>G\t586\tPAH\tphenylketonuria\n"
        )
        mock_get.return_value = mock_resp

        result = tool.run({"gene": "PAH"})

        self.assertEqual(result["status"], "success")
        self.assertGreater(result["total"], 0)
        self.assertNotIn("note", result)


# ---------------------------------------------------------------------------
# MyVariant query field path in description
# ---------------------------------------------------------------------------
class TestMyVariantQueryFieldPath(unittest.TestCase):
    """MyVariant tool description should use correct field paths."""

    def test_description_uses_gene_symbol_field(self):
        """The query description should use clinvar.gene.symbol, not clinvar.gene."""
        import os

        json_path = os.path.join(
            os.path.dirname(__file__),
            "../../src/tooluniverse/data/biothings_tools.json",
        )
        with open(json_path) as f:
            tools = json.load(f)

        for t in tools:
            if t["name"] == "MyVariant_query_variants":
                desc = t["parameter"]["properties"]["query"]["description"]
                self.assertIn("clinvar.gene.symbol", desc)
                self.assertNotIn("clinvar.gene:BRCA1", desc)
                break
        else:
            self.fail("MyVariant_query_variants not found")


# ---------------------------------------------------------------------------
# ClinicalTrials limit param maps to pageSize
# ---------------------------------------------------------------------------
class TestClinicalTrialsLimitMapping(unittest.TestCase):
    """ClinicalTrials_search_studies should map 'limit' to 'pageSize'."""

    def test_limit_in_search_param_map(self):
        """The _run_search method should map 'limit' to 'pageSize'."""
        from tooluniverse.ctg_tool import ClinicalTrialsTool

        config = {
            "name": "ClinicalTrials_search_studies",
            "type": "ClinicalTrialsTool",
            "fields": {"operation": "search"},
            "parameter": {"required": [], "properties": {}},
            "query_schema": {},
        }
        tool = ClinicalTrialsTool(config)

        # Verify _run_search maps limit to pageSize
        import inspect

        source = inspect.getsource(tool._run_search)
        self.assertIn('"limit": "pageSize"', source)

    @patch("requests.get")
    def test_limit_applied_as_pagesize(self, mock_get):
        """Passing limit=5 should result in pageSize=5 in API request."""
        from tooluniverse.ctg_tool import ClinicalTrialsTool

        config = {
            "name": "ClinicalTrials_search_studies",
            "type": "ClinicalTrialsTool",
            "fields": {"operation": "search"},
            "parameter": {"required": [], "properties": {}},
            "query_schema": {},
        }
        tool = ClinicalTrialsTool(config)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"studies": [], "totalCount": 0}
        mock_get.return_value = mock_resp

        tool.run({"query": "cancer", "limit": 5})

        call_params = mock_get.call_args[1].get("params", {})
        self.assertEqual(call_params.get("pageSize"), 5)
        self.assertNotIn("limit", call_params)


# ---------------------------------------------------------------------------
# GEO methylation/ChIP-seq search filters out GPL platform records
# ---------------------------------------------------------------------------
class TestGEOMethylationGPLFilter(unittest.TestCase):
    """GEO methylation search should filter out GPL platform records."""

    def _make_tool(self, endpoint):
        from tooluniverse.epigenomics_tool import EpigenomicsTool

        config = {
            "name": "GEO_search_methylation_datasets",
            "type": "EpigenomicsTool",
            "fields": {"endpoint": endpoint},
        }
        return EpigenomicsTool(config)

    @patch("tooluniverse.epigenomics_tool.requests.get")
    def test_gpl_records_filtered_out_methylation(self, mock_get):
        """GPL (platform) accessions should be excluded from methylation results."""
        tool = self._make_tool("geo_methylation_search")

        # Mock esearch response
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {
            "esearchresult": {"count": "3", "idlist": ["1", "2", "3"]}
        }

        # Mock esummary with mix of GSE and GPL records
        summary_resp = MagicMock()
        summary_resp.status_code = 200
        summary_resp.raise_for_status = MagicMock()
        summary_resp.json.return_value = {
            "result": {
                "1": {
                    "accession": "GSE12345",
                    "title": "Methylation study",
                    "summary": "Real dataset",
                    "taxon": "Homo sapiens",
                    "n_samples": 50,
                },
                "2": {
                    "accession": "GPL6244",
                    "title": "Affymetrix Platform",
                    "summary": "Platform record",
                    "taxon": "Homo sapiens",
                    "n_samples": 0,
                },
                "3": {
                    "accession": "GSE67890",
                    "title": "Another study",
                    "summary": "Another dataset",
                    "taxon": "Homo sapiens",
                    "n_samples": 30,
                },
            }
        }

        mock_get.side_effect = [search_resp, summary_resp]

        result = tool.run({"query": "arsenic methylation"})

        datasets = result["data"]["datasets"]
        # GPL record should be filtered out
        self.assertEqual(len(datasets), 2)
        accessions = [d["accession"] for d in datasets]
        self.assertIn("GSE12345", accessions)
        self.assertIn("GSE67890", accessions)
        self.assertNotIn("GPL6244", accessions)

    @patch("tooluniverse.epigenomics_tool.requests.get")
    def test_gpl_records_filtered_out_chipseq(self, mock_get):
        """GPL records should also be filtered from ChIP-seq results."""
        tool = self._make_tool("geo_chipseq_search")

        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.raise_for_status = MagicMock()
        search_resp.json.return_value = {
            "esearchresult": {"count": "2", "idlist": ["1", "2"]}
        }

        summary_resp = MagicMock()
        summary_resp.status_code = 200
        summary_resp.raise_for_status = MagicMock()
        summary_resp.json.return_value = {
            "result": {
                "1": {
                    "accession": "GPL570",
                    "title": "Platform",
                    "summary": "Platform record",
                    "taxon": "Homo sapiens",
                    "n_samples": 0,
                },
                "2": {
                    "accession": "GSE99999",
                    "title": "ChIP-seq study",
                    "summary": "Real dataset",
                    "taxon": "Homo sapiens",
                    "n_samples": 20,
                },
            }
        }

        mock_get.side_effect = [search_resp, summary_resp]

        result = tool.run({"query": "ESR1 ChIP-seq"})

        datasets = result["data"]["datasets"]
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0]["accession"], "GSE99999")


# ---------------------------------------------------------------------------
# GTEx expression summary provides helpful note on empty results
# ---------------------------------------------------------------------------
class TestGTExExpressionSummaryNote(unittest.TestCase):
    """GTEx expression summary should provide hints when results are empty."""

    def _make_tool(self):
        from tooluniverse.gtex_tool import GTExExpressionTool

        config = {
            "name": "GTEx_get_expression_summary",
            "type": "GTExExpressionTool",
            "settings": {"base_url": "https://gtexportal.org/api/v2", "timeout": 30},
        }
        return GTExExpressionTool(config)

    @patch("tooluniverse.gtex_tool._http_get")
    @patch("tooluniverse.gtex_tool._resolve_gene_id")
    def test_note_when_resolution_fails(self, mock_resolve, mock_http):
        """When gene ID resolution fails, include helpful note."""
        tool = self._make_tool()

        # Resolution fails - returns input as-is
        mock_resolve.return_value = "COL5A1"

        # Feature-80A: clusteredMedianGeneExpression returns under 'medianGeneExpression' key
        mock_http.return_value = {"medianGeneExpression": []}

        result = tool.run({"gene_symbol": "COL5A1"})

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["geneExpression"], [])
        self.assertIn("note", result)
        self.assertIn("Could not resolve", result["note"])

    @patch("tooluniverse.gtex_tool._http_get")
    @patch("tooluniverse.gtex_tool._resolve_gene_id")
    def test_note_when_version_mismatch(self, mock_resolve, mock_http):
        """When resolved but empty, suggest version mismatch."""
        tool = self._make_tool()

        # Resolution succeeds but returns wrong version
        mock_resolve.return_value = "ENSG00000130635.18"

        # Feature-80A: clusteredMedianGeneExpression returns under 'medianGeneExpression' key
        mock_http.return_value = {"medianGeneExpression": []}

        result = tool.run({"ensembl_gene_id": "ENSG00000130635"})

        self.assertTrue(result["success"])
        self.assertIn("note", result)
        self.assertIn("GENCODE version", result["note"])

    @patch("tooluniverse.gtex_tool._http_get")
    @patch("tooluniverse.gtex_tool._resolve_gene_id")
    def test_no_note_when_data_found(self, mock_resolve, mock_http):
        """When expression data is found, no note is needed."""
        tool = self._make_tool()

        mock_resolve.return_value = "ENSG00000141510.16"
        # Feature-80A: clusteredMedianGeneExpression returns under 'medianGeneExpression' key
        mock_http.return_value = {
            "medianGeneExpression": [{"gencodeId": "ENSG00000141510.16", "median": 15.0}]
        }

        result = tool.run({"gene_symbol": "TP53"})

        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]["geneExpression"]), 1)
        self.assertNotIn("note", result)

    def test_error_when_no_gene_input(self):
        """Should return error when neither gene_symbol nor ensembl_gene_id provided."""
        tool = self._make_tool()
        result = tool.run({})
        self.assertFalse(result["success"])
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# GDC mutation frequency now queries /ssm_occurrences
# ---------------------------------------------------------------------------
class TestGDCMutationFrequency(unittest.TestCase):
    """GDC_get_mutation_frequency should return real SSM occurrence data."""

    def _make_tool(self):
        from tooluniverse.gdc_tool import GDCMutationFrequencyTool

        config = {
            "name": "GDC_get_mutation_frequency",
            "type": "GDCMutationFrequencyTool",
            "settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30},
        }
        return GDCMutationFrequencyTool(config)

    @patch("tooluniverse.gdc_tool._http_get")
    def test_returns_ssm_occurrence_counts(self, mock_http):
        """Should return total_ssm_occurrences and per-project counts."""
        tool = self._make_tool()

        # First call: /genes for gene info
        gene_resp = {
            "data": {
                "hits": [
                    {
                        "symbol": "TP53",
                        "name": "tumor protein p53",
                        "is_cancer_gene_census": True,
                    }
                ]
            }
        }
        # Second call: /ssm_occurrences with facets
        ssm_resp = {
            "data": {
                "pagination": {"total": 15000},
                "aggregations": {
                    "cases.project.project_id": {
                        "buckets": [
                            {"key": "TCGA-OV", "doc_count": 1200},
                            {"key": "TCGA-BRCA", "doc_count": 950},
                            {"key": "TCGA-LUAD", "doc_count": 800},
                        ]
                    }
                },
            }
        }
        mock_http.side_effect = [gene_resp, ssm_resp]

        result = tool.run({"gene_symbol": "TP53"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["total_ssm_occurrences"], 15000)
        self.assertEqual(len(result["data"]["project_mutation_counts"]), 3)
        self.assertEqual(
            result["data"]["project_mutation_counts"][0]["project_id"], "TCGA-OV"
        )
        self.assertTrue(result["data"]["is_cancer_gene_census"])

    def test_missing_gene_symbol_returns_error(self):
        """Should return error when gene_symbol not provided."""
        tool = self._make_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("gene_symbol", result["error"])

    @patch("tooluniverse.gdc_tool._http_get")
    def test_gene_info_failure_still_returns_ssm_data(self, mock_http):
        """Should still return SSM data even if gene info call fails."""
        tool = self._make_tool()

        # Gene info call fails
        def side_effect(url, **kwargs):
            if "/genes?" in url:
                raise Exception("Gene endpoint down")
            return {
                "data": {
                    "pagination": {"total": 500},
                    "aggregations": {
                        "cases.project.project_id": {
                            "buckets": [{"key": "TCGA-GBM", "doc_count": 300}]
                        }
                    },
                }
            }

        mock_http.side_effect = side_effect

        result = tool.run({"gene_symbol": "KRAS"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["total_ssm_occurrences"], 500)


# ---------------------------------------------------------------------------
# COSMIC dedup and placeholder filtering
# ---------------------------------------------------------------------------
class TestCOSMICDedup(unittest.TestCase):
    """COSMIC search should skip placeholder entries and deduplicate properly."""

    def _make_tool(self):
        from tooluniverse.cosmic_tool import COSMICTool

        config = {
            "name": "COSMIC_search_mutations",
            "type": "COSMICTool",
            "parameter": {
                "properties": {
                    "operation": {"const": "search"},
                },
            },
        }
        return COSMICTool(config)

    @patch("tooluniverse.cosmic_tool.requests.get")
    def test_placeholder_entries_skipped(self, mock_get):
        """Entries with c.? and p.? should be skipped."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [
            5,  # total_count
            ["COSM1", "COSM2", "COSM3", "COSM4", "COSM5"],  # codes
            {
                "GeneName": ["KRAS", "KRAS", "KRAS", "KRAS", "KRAS"],
                "MutationCDS": ["c.34G>T", "c.?", "c.35G>A", "c.?", "c.34G>C"],
                "MutationAA": ["p.G12C", "p.?", "p.G12D", "p.?", "p.G12R"],
                "PrimarySite": ["lung", "lung", "lung", "lung", "pancreas"],
                "PrimaryHistology": [
                    "carcinoma", "carcinoma", "carcinoma", "carcinoma", "carcinoma"
                ],
            },
            [],  # display_strings
        ]
        mock_get.return_value = mock_resp

        result = tool.run({"terms": "KRAS"})

        mutations = result["data"]["results"]
        # Entries 2 and 4 (c.?/p.?) should be skipped
        self.assertEqual(len(mutations), 3)
        aa_changes = [m["mutation_aa"] for m in mutations]
        self.assertNotIn("p.?", aa_changes)
        self.assertIn("p.G12C", aa_changes)
        self.assertIn("p.G12D", aa_changes)
        self.assertIn("p.G12R", aa_changes)

    @patch("tooluniverse.cosmic_tool.requests.get")
    def test_dedup_uses_full_key(self, mock_get):
        """Dedup key should include gene, CDS, and AA (not just mutation_id+AA)."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        # Same mutation_id and AA but different CDS → keep both
        mock_resp.json.return_value = [
            3,
            ["COSM1", "COSM1", "COSM1"],
            {
                "GeneName": ["BRAF", "BRAF", "BRAF"],
                "MutationCDS": ["c.1799T>A", "c.1799T>A", "c.1798_1799GT>AA"],
                "MutationAA": ["p.V600E", "p.V600E", "p.V600E"],
                "PrimarySite": ["skin", "thyroid", "skin"],
                "PrimaryHistology": ["melanoma", "carcinoma", "melanoma"],
            },
            [],
        ]
        mock_get.return_value = mock_resp

        result = tool.run({"terms": "BRAF V600E"})

        mutations = result["data"]["results"]
        # First two are exact same key (COSM1, BRAF, c.1799T>A, p.V600E) → deduplicated
        # Third has different CDS → kept
        self.assertEqual(len(mutations), 2)
        cds_changes = [m["mutation_cds"] for m in mutations]
        self.assertIn("c.1799T>A", cds_changes)
        self.assertIn("c.1798_1799GT>AA", cds_changes)


# ---------------------------------------------------------------------------
# OncoKB demo mode note
# ---------------------------------------------------------------------------
class TestOncoKBDemoNote(unittest.TestCase):
    """OncoKB should clearly indicate demo mode limitations."""

    def _make_tool(self):
        from tooluniverse.oncokb_tool import OncoKBTool

        config = {
            "name": "OncoKB_get_cancer_genes",
            "type": "OncoKBTool",
            "parameter": {
                "properties": {"operation": {"const": "get_cancer_genes"}},
            },
        }
        return OncoKBTool(config)

    @patch("tooluniverse.oncokb_tool.requests.get")
    @patch.dict("os.environ", {}, clear=True)
    def test_demo_mode_includes_note(self, mock_get):
        """Demo mode response should include a note about limited results."""
        tool = self._make_tool()
        # Force demo mode
        tool.api_token = ""
        tool.use_demo = True
        tool.base_url = "https://demo.oncokb.org/api/v1"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [
            {"hugoSymbol": "BRAF", "oncogene": True, "tsg": False},
            {"hugoSymbol": "TP53", "oncogene": False, "tsg": True},
            {"hugoSymbol": "ROS1", "oncogene": True, "tsg": False},
        ]
        mock_get.return_value = mock_resp

        result = tool.run({})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["cancer_genes_count"], 3)
        self.assertIn("note", result["metadata"])
        self.assertIn("Demo mode", result["metadata"]["note"])
        self.assertIn("ONCOKB_API_TOKEN", result["metadata"]["note"])


# ---------------------------------------------------------------------------
# HumanBase PPI: handle None/error from get_entrez_ids
# ---------------------------------------------------------------------------
class TestHumanBaseEntrezIdHandling(unittest.TestCase):
    """HumanBase should handle None and error returns from get_entrez_ids."""

    def _make_tool(self):
        from tooluniverse.humanbase_tool import HumanBaseTool

        config = {
            "name": "humanbase_ppi_analysis",
            "type": "HumanBaseTool",
            "parameter": {},
        }
        return HumanBaseTool(config)

    @patch("tooluniverse.humanbase_tool.HumanBaseTool.get_entrez_ids")
    def test_error_string_from_get_entrez_ids(self, mock_ids):
        """When get_entrez_ids returns an error string, return error."""
        tool = self._make_tool()
        mock_ids.return_value = "Error fetching data for gene: INVALID"

        result = tool.run({"gene_list": ["INVALID"], "tissue": "brain"})

        self.assertEqual(result["status"], "error")
        self.assertIn("STRING_get_interaction_partners", result["error"])

    @patch("tooluniverse.humanbase_tool.HumanBaseTool.get_entrez_ids")
    def test_none_values_filtered_from_entrez_ids(self, mock_ids):
        """When get_entrez_ids returns [None, '7157'], filter out None and use '7157'."""
        tool = self._make_tool()
        mock_ids.return_value = [None, "7157"]

        # Mock the network and BP API calls
        with patch("tooluniverse.humanbase_tool.requests.get") as mock_get:
            # Network API response with one gene
            network_resp = MagicMock()
            network_resp.status_code = 200
            network_resp.json.return_value = {
                "genes": [
                    {"standard_name": "TP53", "entrez": "7157", "description": "tumor protein p53"}
                ],
                "edges": [],
            }
            network_resp.raise_for_status.return_value = None
            # BP API response
            bp_resp = MagicMock()
            bp_resp.status_code = 200
            bp_resp.json.return_value = []
            bp_resp.raise_for_status.return_value = None

            mock_get.side_effect = [network_resp, bp_resp]
            result = tool.run({"gene_list": ["INVALID", "TP53"], "tissue": "brain"})

        self.assertEqual(result["status"], "success")
        # Should not crash — None filtered out, only '7157' used
        self.assertIn("Total Proteins: 1", result["data"])

    @patch("tooluniverse.humanbase_tool.HumanBaseTool.get_entrez_ids")
    def test_all_none_returns_error(self, mock_ids):
        """When all genes resolve to None, return error with alternative suggestion."""
        tool = self._make_tool()
        mock_ids.return_value = [None, None]

        result = tool.run({"gene_list": ["FAKE1", "FAKE2"], "tissue": "brain"})

        self.assertEqual(result["status"], "error")
        self.assertIn("STRING_get_interaction_partners", result["error"])


# ---------------------------------------------------------------------------
# HumanBase JSON schema: interaction and string_mode not required
# ---------------------------------------------------------------------------
class TestHumanBaseSchemaOptionalParams(unittest.TestCase):
    """HumanBase schema should not require interaction or string_mode."""

    def test_required_only_gene_list(self):
        import json

        with open(
            "src/tooluniverse/data/humanbase_tools.json"
        ) as f:
            tools = json.load(f)

        tool = tools[0]
        required = tool["parameter"]["required"]
        self.assertIn("gene_list", required)
        self.assertNotIn("interaction", required)
        self.assertNotIn("string_mode", required)
        self.assertNotIn("tissue", required)
        self.assertNotIn("max_node", required)


# ---------------------------------------------------------------------------
# GxA: versioned Ensembl ID matching in client-side gene filter
# ---------------------------------------------------------------------------
class TestGxAVersionedEnsemblFilter(unittest.TestCase):
    """GxA should match versioned Ensembl IDs (ENSG00000142192.15 vs ENSG00000142192)."""

    def _make_tool(self):
        from tooluniverse.gxa_tool import GxATool

        config = {
            "name": "GxA_get_experiment_expression",
            "type": "GxATool",
            "parameter": {},
            "fields": {"endpoint": "get_experiment_expression"},
        }
        return GxATool(config)

    @patch("tooluniverse.gxa_tool.requests.get")
    def test_versioned_ensembl_id_match(self, mock_get):
        """Querying ENSG00000142192 should match row with id ENSG00000142192.15."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "experiment": {"description": "Brain expression"},
            "columnHeaders": [
                {"assayGroupId": "g1", "factorValue": "brain", "assayGroupSummary": {}}
            ],
            "profiles": {
                "rows": [
                    {
                        "id": "ENSG00000142192.15",
                        "name": "APP",
                        "expressions": [{"value": 42.5}],
                    },
                    {
                        "id": "ENSG00000099999.3",
                        "name": "OTHER",
                        "expressions": [{"value": 10.0}],
                    },
                ]
            },
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = tool.run(
            {"experiment_accession": "E-MTAB-2836", "gene_id": "ENSG00000142192"}
        )

        profiles = result["data"]["gene_profiles"]
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["gene_name"], "APP")

    @patch("tooluniverse.gxa_tool.requests.get")
    def test_gene_name_match(self, mock_get):
        """Querying by gene name should also work."""
        tool = self._make_tool()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "experiment": {"description": "Test"},
            "columnHeaders": [
                {"assayGroupId": "g1", "factorValue": "brain", "assayGroupSummary": {}}
            ],
            "profiles": {
                "rows": [
                    {
                        "id": "ENSG00000142192",
                        "name": "APP",
                        "expressions": [{"value": 42.5}],
                    },
                    {
                        "id": "ENSG00000099999",
                        "name": "OTHER",
                        "expressions": [{"value": 10.0}],
                    },
                ]
            },
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = tool.run({"experiment_accession": "E-MTAB-2836", "gene_id": "APP"})

        profiles = result["data"]["gene_profiles"]
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["gene_name"], "APP")


# ---------------------------------------------------------------------------
# Monarch_get_gene_diseases: deprecated category enum
# ---------------------------------------------------------------------------
class TestMonarchGeneDiseaseCategory(unittest.TestCase):
    """Monarch_get_gene_diseases should use CausalGeneToDiseaseAssociation."""

    def test_category_updated(self):
        import json

        with open("src/tooluniverse/data/monarch_tools.json") as f:
            tools = json.load(f)

        gene_disease_tool = None
        for t in tools:
            if t["name"] == "Monarch_get_gene_diseases":
                gene_disease_tool = t
                break

        self.assertIsNotNone(gene_disease_tool, "Monarch_get_gene_diseases not found")
        category = gene_disease_tool["query_schema"]["category"]
        self.assertNotIn(
            "biolink:GeneToDiseaseAssociation",
            category,
            "Deprecated category still used",
        )
        self.assertIn("biolink:CausalGeneToDiseaseAssociation", category)


# ---------------------------------------------------------------------------
# GTEx: versioned GENCODE ID resolution
# ---------------------------------------------------------------------------
class TestGTExVersionedGencodeId(unittest.TestCase):
    """GTEx should strip version from user-provided versioned Ensembl IDs and re-resolve."""

    @patch("tooluniverse.gtex_tool._http_get")
    def test_versioned_id_stripped_and_resolved(self, mock_get):
        from tooluniverse.gtex_tool import _resolve_gene_id

        mock_get.return_value = {
            "data": [{"gencodeId": "ENSG00000142192.16", "geneSymbol": "APP"}]
        }

        result = _resolve_gene_id("ENSG00000142192.21", "https://gtexportal.org/api/v2", 30)

        # Should strip .21 and query with base ID, getting correct .16 version
        self.assertEqual(result, "ENSG00000142192.16")
        call_url = mock_get.call_args[0][0]
        self.assertIn("geneId=ENSG00000142192", call_url)
        self.assertNotIn(".21", call_url)

    @patch("tooluniverse.gtex_tool._http_get")
    def test_unversioned_id_resolved(self, mock_get):
        from tooluniverse.gtex_tool import _resolve_gene_id

        mock_get.return_value = {
            "data": [{"gencodeId": "ENSG00000142192.16"}]
        }

        result = _resolve_gene_id("ENSG00000142192", "https://gtexportal.org/api/v2", 30)
        self.assertEqual(result, "ENSG00000142192.16")

    @patch("tooluniverse.gtex_tool._http_get")
    def test_gene_symbol_resolved(self, mock_get):
        from tooluniverse.gtex_tool import _resolve_gene_id

        mock_get.return_value = {
            "data": [{"gencodeId": "ENSG00000141510.18"}]
        }

        result = _resolve_gene_id("TP53", "https://gtexportal.org/api/v2", 30)
        self.assertEqual(result, "ENSG00000141510.18")


# ---------------------------------------------------------------------------
# ClinicalTrials: v2 API fields parameter removed
# ---------------------------------------------------------------------------
class TestClinicalTrialsV2Fields(unittest.TestCase):
    """ClinicalTrials _run_search should not send v1-style fields parameter."""

    def test_run_search_no_fields_param(self):
        """Verify _run_search does not include a 'fields' key in API params."""
        from tooluniverse.ctg_tool import ClinicalTrialsTool

        config = {
            "name": "ClinicalTrials_search_studies",
            "type": "ClinicalTrialsTool",
            "parameter": {"properties": {}},
            "query_schema": {},
            "fields": {"operation": "search"},
        }
        tool = ClinicalTrialsTool(config)

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "studies": [
                    {
                        "protocolSection": {
                            "identificationModule": {"nctId": "NCT12345678", "briefTitle": "Test"},
                            "statusModule": {"overallStatus": "RECRUITING"},
                            "designModule": {
                                "studyType": "INTERVENTIONAL",
                                "enrollmentInfo": {"count": 500},
                            },
                            "conditionsModule": {"conditions": ["Diabetes"]},
                            "armsInterventionsModule": {
                                "interventions": [{"name": "Drug A"}]
                            },
                            "sponsorCollaboratorsModule": {
                                "leadSponsor": {"name": "Pharma Corp"}
                            },
                        }
                    }
                ],
                "totalCount": 1,
            }
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            result = tool.run({"query_cond": "diabetes", "page_size": 1})

        study = result["data"]["studies"][0]
        self.assertEqual(study["enrollment"], 500)
        self.assertEqual(study["sponsor"], "Pharma Corp")
        self.assertEqual(study["interventions"], ["Drug A"])

        # Verify 'fields' not in the API request params
        call_params = mock_get.call_args[1].get("params", {})
        self.assertNotIn("fields", call_params)


# ---------------------------------------------------------------------------
# ChEMBL_search_mechanisms: target_chembl_id filter blocked
# ---------------------------------------------------------------------------
class TestChEMBLMechanismsTargetFilter(unittest.TestCase):
    """ChEMBL_search_mechanisms should reject target_chembl_id (silently ignored by API)."""

    def _make_tool(self):
        from tooluniverse.chem_tool import ChEMBLRESTTool

        config = {
            "name": "ChEMBL_search_mechanisms",
            "type": "ChEMBLRESTTool",
            "parameter": {},
            "fields": {"endpoint": "mechanism"},
        }
        return ChEMBLRESTTool(config)

    def test_target_chembl_id_rejected(self):
        tool = self._make_tool()
        result = tool.run({"target_chembl_id": "CHEMBL284", "limit": 10})

        self.assertEqual(result["status"], "error")
        self.assertIn("target_chembl_id", result["error"])
        self.assertIn("not supported", result["error"])


# ---------------------------------------------------------------------------
# ChEMBL mechanism_of_action__contains → __icontains mapping
# ---------------------------------------------------------------------------
class TestChEMBLMechanismContainsCaseSensitivity(unittest.TestCase):
    """mechanism_of_action__contains should be mapped to __icontains for case-insensitive search."""

    def _make_tool(self):
        from tooluniverse.chem_tool import ChEMBLRESTTool

        config = {
            "name": "ChEMBL_search_mechanisms",
            "parameter": {},
            "fields": {"endpoint": "mechanism"},
        }
        return ChEMBLRESTTool(config)

    def test_mechanism_of_action_contains_mapped_to_icontains(self):
        tool = self._make_tool()
        params = tool._build_params(
            {"mechanism_of_action__contains": "Tyrosine kinase inhibitor", "limit": 5}
        )
        # Should use case-insensitive __icontains, not case-sensitive __contains
        self.assertIn("mechanism_of_action__icontains", params)
        self.assertEqual(params["mechanism_of_action__icontains"], "Tyrosine kinase inhibitor")
        # The original __contains should NOT be passed through
        self.assertNotIn("mechanism_of_action__contains", params)


# ---------------------------------------------------------------------------
# STRING enrichment/annotation category client-side filtering
# ---------------------------------------------------------------------------
class TestSTRINGEnrichmentCategoryFilter(unittest.TestCase):
    """STRING /json/enrichment ignores category param server-side; verify client-side filter."""

    def test_enrichment_category_filter_applied(self):
        from tooluniverse.string_tool import STRINGRESTTool

        config = {
            "name": "STRING_functional_enrichment",
            "parameter": {"required": ["protein_ids"]},
            "fields": {"endpoint": "/json/enrichment", "return_format": "JSON"},
        }
        tool = STRINGRESTTool(config)

        # Mock API response with mixed categories
        mock_api_response = [
            {"category": "KEGG", "term": "hsa04010", "description": "MAPK signaling"},
            {"category": "Process", "term": "GO:0006915", "description": "apoptotic process"},
            {"category": "KEGG", "term": "hsa04115", "description": "p53 signaling"},
            {"category": "COMPARTMENTS", "term": "GOCC:0005634", "description": "nucleus"},
        ]

        with patch.object(tool, "_make_request", return_value=mock_api_response):
            result = tool.run({"protein_ids": ["TP53", "BRCA1", "EGFR"], "category": "KEGG"})

        self.assertEqual(result["status"], "success")
        # Should only contain KEGG entries
        data = result["data"]
        self.assertTrue(isinstance(data, list))
        self.assertEqual(len(data), 2)
        for item in data:
            self.assertEqual(item["category"], "KEGG")

    def test_enrichment_no_category_returns_all(self):
        from tooluniverse.string_tool import STRINGRESTTool

        config = {
            "name": "STRING_functional_enrichment",
            "parameter": {"required": ["protein_ids"]},
            "fields": {"endpoint": "/json/enrichment", "return_format": "JSON"},
        }
        tool = STRINGRESTTool(config)

        mock_api_response = [
            {"category": "KEGG", "term": "hsa04010"},
            {"category": "Process", "term": "GO:0006915"},
        ]

        with patch.object(tool, "_make_request", return_value=mock_api_response):
            result = tool.run({"protein_ids": ["TP53", "BRCA1", "EGFR"]})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(len(data), 2)


class TestSTRINGExtAnnotationCategoryFilter(unittest.TestCase):
    """STRING_get_functional_annotations should filter by category client-side."""

    def test_annotation_category_filter_applied(self):
        from tooluniverse.string_ext_tool import STRINGExtTool

        config = {
            "name": "STRING_get_functional_annotations",
            "fields": {"endpoint": "functional_annotation"},
        }
        tool = STRINGExtTool(config)

        mock_api_data = [
            {"category": "Process", "term": "GO:0006915", "description": "apoptosis", "number_of_genes": 5, "inputGenes": ["TP53"]},
            {"category": "KEGG", "term": "hsa04115", "description": "p53 signaling", "number_of_genes": 3, "inputGenes": ["TP53"]},
            {"category": "Process", "term": "GO:0008283", "description": "cell proliferation", "number_of_genes": 4, "inputGenes": ["TP53"]},
            {"category": "DISEASES", "term": "DOID:1612", "description": "breast cancer", "number_of_genes": 2, "inputGenes": ["TP53"]},
        ]

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_api_data
        mock_resp.raise_for_status.return_value = None

        with patch("tooluniverse.string_ext_tool.requests.get", return_value=mock_resp):
            result = tool.run({"identifiers": "TP53", "category": "Process"})

        # Should only contain Process annotations
        annotations = result["data"]["annotations"]
        self.assertIn("Process", annotations)
        self.assertNotIn("KEGG", annotations)
        self.assertNotIn("DISEASES", annotations)
        self.assertEqual(len(annotations["Process"]), 2)

    def test_annotation_no_category_returns_all(self):
        from tooluniverse.string_ext_tool import STRINGExtTool

        config = {
            "name": "STRING_get_functional_annotations",
            "fields": {"endpoint": "functional_annotation"},
        }
        tool = STRINGExtTool(config)

        mock_api_data = [
            {"category": "Process", "term": "GO:0006915", "description": "apoptosis", "number_of_genes": 5, "inputGenes": ["TP53"]},
            {"category": "KEGG", "term": "hsa04115", "description": "p53 signaling", "number_of_genes": 3, "inputGenes": ["TP53"]},
        ]

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_api_data
        mock_resp.raise_for_status.return_value = None

        with patch("tooluniverse.string_ext_tool.requests.get", return_value=mock_resp):
            result = tool.run({"identifiers": "TP53"})

        annotations = result["data"]["annotations"]
        self.assertIn("Process", annotations)
        self.assertIn("KEGG", annotations)


# ---------------------------------------------------------------------------
# OpenTargets_target_disease_evidence description accuracy
# ---------------------------------------------------------------------------
class TestOpenTargetsEvidenceDescription(unittest.TestCase):
    """OpenTargets_target_disease_evidence should clearly indicate IntOGen-only scope."""

    def test_description_mentions_intogen(self):
        with open("src/tooluniverse/data/opentarget_tools.json") as f:
            tools = json.load(f)

        evidence_tool = next(
            (t for t in tools if t["name"] == "OpenTargets_target_disease_evidence"), None
        )
        self.assertIsNotNone(evidence_tool)
        desc = evidence_tool["description"].lower()
        self.assertIn("intogen", desc)
        self.assertIn("openTargets_get_evidence_by_datasource".lower(), desc)


# ---------------------------------------------------------------------------
# GWAS disease_trait auto-resolution to efo_id
# ---------------------------------------------------------------------------
class TestGWASTraitResolution(unittest.TestCase):
    """GWAS /v2/associations ignores disease_trait param; must auto-resolve to efo_id."""

    def _make_associations_tool(self):
        from tooluniverse.gwas_tool import GWASAssociationsForTrait

        config = {
            "name": "gwas_get_associations_for_trait",
            "parameter": {},
        }
        return GWASAssociationsForTrait(config)

    def _make_variants_tool(self):
        from tooluniverse.gwas_tool import GWASVariantsForTrait

        config = {
            "name": "gwas_get_variants_for_trait",
            "parameter": {},
        }
        return GWASVariantsForTrait(config)

    @patch("tooluniverse.gwas_tool.requests.get")
    def test_disease_trait_resolved_to_efo_id(self, mock_get):
        """When disease_trait is provided, it should be resolved to efo_id via efoTraits search."""
        tool = self._make_associations_tool()

        # Mock: first call resolves trait, second call fetches associations
        efo_response = MagicMock()
        efo_response.status_code = 200
        efo_response.json.return_value = {
            "_embedded": {
                "efoTraits": [{"shortForm": "EFO_0001360", "trait": "Type 2 diabetes"}]
            }
        }
        efo_response.raise_for_status.return_value = None

        assoc_response = MagicMock()
        assoc_response.status_code = 200
        assoc_response.json.return_value = {
            "_embedded": {"associations": [{"id": 1, "pvalue": 1e-10}]},
            "page": {"totalElements": 1},
        }
        assoc_response.raise_for_status.return_value = None

        mock_get.side_effect = [efo_response, assoc_response]

        result = tool.run({"disease_trait": "type 2 diabetes", "size": 5})

        # Verify efo_id was resolved and used
        self.assertIn("resolved_efo_id", result)
        self.assertEqual(result["resolved_efo_id"], "EFO_0001360")

        # Verify the associations request used efo_id, not disease_trait
        assoc_call = mock_get.call_args_list[1]
        params = assoc_call.kwargs.get("params") or assoc_call[1].get("params", {})
        self.assertIn("efo_id", params)
        self.assertNotIn("disease_trait", params)

    @patch("tooluniverse.gwas_tool.requests.get")
    def test_efo_id_takes_precedence_over_disease_trait(self, mock_get):
        """When efo_id is already provided, don't resolve disease_trait."""
        tool = self._make_associations_tool()

        assoc_response = MagicMock()
        assoc_response.status_code = 200
        assoc_response.json.return_value = {
            "_embedded": {"associations": [{"id": 2}]},
            "page": {"totalElements": 1},
        }
        assoc_response.raise_for_status.return_value = None
        mock_get.return_value = assoc_response

        tool.run({"disease_trait": "diabetes", "efo_id": "EFO_0001360"})

        # Only one request made (no trait resolution needed)
        self.assertEqual(mock_get.call_count, 1)

    @patch("tooluniverse.gwas_tool.requests.get")
    def test_variants_tool_also_resolves_trait(self, mock_get):
        """GWASVariantsForTrait should also auto-resolve disease_trait."""
        tool = self._make_variants_tool()

        efo_response = MagicMock()
        efo_response.status_code = 200
        efo_response.json.return_value = {
            "_embedded": {
                "efoTraits": [{"shortForm": "EFO_0001360", "trait": "Type 2 diabetes"}]
            }
        }
        efo_response.raise_for_status.return_value = None

        assoc_response = MagicMock()
        assoc_response.status_code = 200
        assoc_response.json.return_value = {
            "_embedded": {"associations": []},
            "page": {"totalElements": 0},
        }
        assoc_response.raise_for_status.return_value = None

        mock_get.side_effect = [efo_response, assoc_response]

        result = tool.run({"disease_trait": "type 2 diabetes"})
        self.assertIn("resolved_efo_id", result)


# ---------------------------------------------------------------------------
# GTEx eQTL dataset default (Feature-69A-001)
# ---------------------------------------------------------------------------
class TestGTExEQTLDatasetDefault(unittest.TestCase):
    """GTEx_query_eqtl should default to gtex_v8, not gtex_v10 (which returns empty)."""

    def test_eqtl_defaults_to_v8(self):
        """Verify the eQTL tool uses gtex_v8 as default dataset."""
        from tooluniverse.gtex_tool import GTExEQTLTool

        config = {
            "name": "GTEx_query_eqtl",
            "description": "Query eQTL data",
            "fields": {},
            "parameter": {"required": []},
        }
        tool = GTExEQTLTool(config)

        with patch("tooluniverse.gtex_tool._resolve_gene_id", return_value="ENSG00000000001.1"):
            with patch("tooluniverse.gtex_tool._http_get") as mock_get:
                mock_get.return_value = {"data": [], "paging_info": {}}
                tool.run({"gene_symbol": "TP53"})
                called_url = mock_get.call_args[0][0]
                self.assertIn("gtex_v8", called_url)
                self.assertNotIn("gtex_v10", called_url)

    def test_eqtl_respects_explicit_dataset(self):
        """If user explicitly passes dataset_id, it should be used."""
        from tooluniverse.gtex_tool import GTExEQTLTool

        config = {
            "name": "GTEx_query_eqtl",
            "description": "Query eQTL data",
            "fields": {},
            "parameter": {"required": []},
        }
        tool = GTExEQTLTool(config)

        with patch("tooluniverse.gtex_tool._resolve_gene_id", return_value="ENSG00000000001.1"):
            with patch("tooluniverse.gtex_tool._http_get") as mock_get:
                mock_get.return_value = {"data": [], "paging_info": {}}
                tool.run({"gene_symbol": "TP53", "dataset_id": "gtex_v10"})
                called_url = mock_get.call_args[0][0]
                self.assertIn("gtex_v10", called_url)


# ---------------------------------------------------------------------------
# FDA drug label generic name salt form fallback (Feature-79D)
# ---------------------------------------------------------------------------
class TestFDALabelGenericNameFallback(unittest.TestCase):
    """FDA_get_drug_label should find drugs even when generic name includes salt form."""

    def _make_tool(self, query_type="get"):
        from tooluniverse.fda_label_tool import FDALabelTool

        config = {
            "name": "FDA_get_drug_label",
            "description": "Get FDA label",
            "fields": {"query_type": query_type},
            "parameter": {"required": ["drug_name"]},
        }
        return FDALabelTool(config)

    @patch("tooluniverse.fda_label_tool.requests.get")
    def test_get_label_falls_back_to_unquoted(self, mock_get):
        """When exact quoted search fails, unquoted search should match salt forms."""
        tool = self._make_tool("get")

        not_found = MagicMock()
        not_found.status_code = 404

        found = MagicMock()
        found.status_code = 200
        found.raise_for_status.return_value = None
        found.json.return_value = {
            "results": [
                {
                    "openfda": {
                        "brand_name": ["XELJANZ"],
                        "generic_name": ["TOFACITINIB CITRATE"],
                        "manufacturer_name": ["Pfizer"],
                        "route": ["ORAL"],
                        "pharm_class_epc": [],
                        "rxcui": [],
                    },
                    "indications_and_usage": ["Rheumatoid arthritis"],
                }
            ]
        }

        # Exact quoted generic fails (404), unquoted generic succeeds
        mock_get.side_effect = [not_found, found]

        result = tool.run({"drug_name": "tofacitinib"})
        self.assertNotIn("error", result)
        self.assertEqual(result["generic_name"], "TOFACITINIB CITRATE")

        # Verify: first call was exact quoted, second was unquoted
        calls = mock_get.call_args_list
        self.assertIn('"tofacitinib"', calls[0][1]["params"]["search"])
        self.assertNotIn('"', calls[1][1]["params"]["search"].split(":")[-1])

    @patch("tooluniverse.fda_label_tool.requests.get")
    def test_search_falls_back_to_unquoted(self, mock_get):
        """Search method should also fall back to unquoted for salt forms."""
        tool = self._make_tool("search")

        not_found = MagicMock()
        not_found.status_code = 404

        found = MagicMock()
        found.status_code = 200
        found.raise_for_status.return_value = None
        found.json.return_value = {
            "results": [
                {
                    "openfda": {
                        "brand_name": ["XELJANZ"],
                        "generic_name": ["TOFACITINIB CITRATE"],
                        "manufacturer_name": [],
                        "route": [],
                        "pharm_class_epc": [],
                        "rxcui": [],
                    }
                }
            ]
        }

        # All exact quoted searches fail, first unquoted succeeds
        mock_get.side_effect = [not_found, found]

        result = tool.run({"drug_name": "tofacitinib"})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["generic_name"], "TOFACITINIB CITRATE")

    @patch("tooluniverse.fda_label_tool.requests.get")
    def test_exact_match_preferred(self, mock_get):
        """When exact quoted search succeeds, it should not try unquoted."""
        tool = self._make_tool("get")

        found = MagicMock()
        found.status_code = 200
        found.raise_for_status.return_value = None
        found.json.return_value = {
            "results": [
                {
                    "openfda": {
                        "brand_name": ["XELJANZ"],
                        "generic_name": ["TOFACITINIB"],
                        "manufacturer_name": [],
                        "route": [],
                        "pharm_class_epc": [],
                        "rxcui": [],
                    }
                }
            ]
        }

        mock_get.return_value = found
        result = tool.run({"drug_name": "tofacitinib"})
        self.assertNotIn("error", result)
        # Only one call should be made (exact match succeeded)
        self.assertEqual(mock_get.call_count, 1)


# ---------------------------------------------------------------------------
# ENCODE histone search graceful 404 fallback (Feature-79E)
# ---------------------------------------------------------------------------
class TestENCODEHistoneSearchGracefulFallback(unittest.TestCase):
    """ENCODE histone search should return empty result with hint on invalid biosample terms."""

    def _make_tool(self):
        from tooluniverse.epigenomics_tool import EpigenomicsTool

        config = {
            "name": "ENCODE_search_histone_experiments",
            "description": "Search ENCODE histone ChIP-seq",
            "fields": {"endpoint": "histone_chipseq"},
            "parameter": {"required": []},
        }
        return EpigenomicsTool(config)

    @patch("tooluniverse.epigenomics_tool.requests.get")
    def test_disease_name_returns_empty_with_hint(self, mock_get):
        """Disease names (not ENCODE ontology terms) should return empty with helpful note."""
        from requests.exceptions import HTTPError

        resp_404 = MagicMock()
        resp_404.status_code = 404
        resp_404.raise_for_status.side_effect = HTTPError(response=resp_404)

        mock_get.return_value = resp_404

        tool = self._make_tool()
        result = tool.run({"biosample_term_name": "acute myeloid leukemia"})

        self.assertEqual(result["data"], [])
        self.assertIn("note", result["metadata"])
        self.assertIn("ENCODE requires ontology", result["metadata"]["note"])

    @patch("tooluniverse.epigenomics_tool.requests.get")
    def test_valid_biosample_works(self, mock_get):
        """Valid cell line names should return results normally."""
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.raise_for_status.return_value = None
        resp_ok.json.return_value = {
            "@graph": [
                {
                    "accession": "ENCSR000AAA",
                    "assay_title": "Histone ChIP-seq",
                    "biosample_summary": "K562",
                    "target": {"label": "H3K27ac"},
                    "lab": {"title": "Test Lab"},
                    "status": "released",
                    "date_released": "2024-01-01",
                }
            ],
            "total": 1,
        }

        mock_get.return_value = resp_ok

        tool = self._make_tool()
        result = tool.run({"biosample_term_name": "K562", "histone_mark": "H3K27ac"})

        self.assertGreater(len(result["data"]["experiments"]), 0)


# ---------------------------------------------------------------------------
# GTEx v2 dataset defaults (Feature-69A-002)
# ---------------------------------------------------------------------------
class TestGTExV2DatasetDefaults(unittest.TestCase):
    """All GTEx v2 tool methods should default to gtex_v8."""

    def _make_tool(self):
        from tooluniverse.gtex_v2_tool import GTExV2Tool

        config = {
            "name": "GTEx_v2_test",
            "description": "GTEx v2 test",
            "fields": {"operation": "get_eqtl_genes"},
            "parameter": {"required": []},
        }
        return GTExV2Tool(config)

    @patch("tooluniverse.gtex_v2_tool.requests.get")
    def test_eqtl_genes_defaults_v8(self, mock_get):
        """_get_eqtl_genes should default to gtex_v8."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"data": [], "paging_info": {}}
        mock_get.return_value = resp

        tool = self._make_tool()
        tool._get_eqtl_genes({})

        called_params = mock_get.call_args[1].get("params", mock_get.call_args[0][0] if mock_get.call_args[0] else {})
        # Check the params dict passed to requests.get
        if isinstance(called_params, dict):
            self.assertEqual(called_params.get("datasetId"), "gtex_v8")
        else:
            # params may be in kwargs
            call_kwargs = mock_get.call_args[1]
            params = call_kwargs.get("params", {})
            self.assertEqual(params.get("datasetId"), "gtex_v8")


# ---------------------------------------------------------------------------
# GTEx expression summary uses clusteredMedianGeneExpression (Feature-80A)
# ---------------------------------------------------------------------------
class TestGTExExpressionSummaryEndpoint(unittest.TestCase):
    """GTEx_get_expression_summary uses clusteredMedianGeneExpression for all-tissue results."""

    def _make_tool(self):
        from tooluniverse.gtex_tool import GTExExpressionTool

        config = {
            "name": "GTEx_get_expression_summary",
            "type": "GTExExpressionTool",
            "settings": {"base_url": "https://gtexportal.org/api/v2", "timeout": 30},
            "parameter": {},
        }
        return GTExExpressionTool(config)

    @patch("tooluniverse.gtex_tool.urlopen")
    def test_uses_clustered_endpoint(self, mock_urlopen):
        """Should call clusteredMedianGeneExpression, not medianGeneExpression."""
        import json
        from urllib.request import Request

        gene_data = json.dumps({"data": [{"gencodeId": "ENSG00000012048.20"}]}).encode()
        expr_data = json.dumps({
            "medianGeneExpression": [
                {"tissueSiteDetailId": "Brain_Cortex", "median": 1.5}
            ]
        }).encode()

        # urlopen is called with Request objects; mock __enter__ to return readable responses
        call_count = {"n": 0}
        responses = [gene_data, expr_data]

        def fake_urlopen(req, **kwargs):
            idx = min(call_count["n"], len(responses) - 1)
            call_count["n"] += 1
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=responses[idx])))
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        mock_urlopen.side_effect = fake_urlopen

        tool = self._make_tool()
        tool.run({"gene_symbol": "BRCA1"})

        # Verify the second URL call used clusteredMedianGeneExpression
        calls = mock_urlopen.call_args_list
        self.assertTrue(len(calls) >= 2)
        second_req = calls[1][0][0]
        url = second_req.full_url if isinstance(second_req, Request) else str(second_req)
        self.assertIn("clusteredMedianGeneExpression", url)

    @patch("tooluniverse.gtex_tool.urlopen")
    def test_extracts_from_medianGeneExpression_key(self, mock_urlopen):
        """Should extract data from the 'medianGeneExpression' key in response."""
        import json
        from urllib.request import Request

        gene_data = json.dumps({"data": [{"gencodeId": "ENSG00000012048.20"}]}).encode()
        expr_data = json.dumps({
            "medianGeneExpression": [
                {"tissueSiteDetailId": "Brain_Cortex", "median": 1.5},
                {"tissueSiteDetailId": "Liver", "median": 0.8},
            ],
            "clusters": {"gene": "", "tissue": ""},
        }).encode()

        call_count = {"n": 0}
        responses = [gene_data, expr_data]

        def fake_urlopen(req, **kwargs):
            idx = min(call_count["n"], len(responses) - 1)
            call_count["n"] += 1
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=responses[idx])))
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        mock_urlopen.side_effect = fake_urlopen

        tool = self._make_tool()
        result = tool.run({"gene_symbol": "BRCA1"})

        self.assertTrue(result.get("success"))
        expr = result.get("data", {}).get("geneExpression", [])
        self.assertEqual(len(expr), 2)
        self.assertEqual(expr[0]["tissueSiteDetailId"], "Brain_Cortex")


# ---------------------------------------------------------------------------
# GTEx v2 median gene expression uses clustered endpoint when no tissue (Feature-80A)
# ---------------------------------------------------------------------------
class TestGTExV2MedianExpressionEndpoint(unittest.TestCase):
    """GTEx_get_median_gene_expression falls back to clusteredMedianGeneExpression."""

    def _make_tool(self):
        from tooluniverse.gtex_v2_tool import GTExV2Tool

        config = {
            "name": "GTEx_get_median_gene_expression",
            "type": "GTExV2Tool",
            "parameter": {"required": ["operation"]},
            "fields": {},
        }
        return GTExV2Tool(config)

    @patch("tooluniverse.gtex_v2_tool.requests.get")
    def test_no_tissue_uses_clustered(self, mock_get):
        """Without tissue, should use clusteredMedianGeneExpression endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "medianGeneExpression": [
                {"tissueSiteDetailId": "Brain_Cortex", "median": 1.5}
            ]
        }
        mock_get.return_value = mock_resp

        tool = self._make_tool()
        result = tool._get_median_gene_expression({
            "gencode_id": "ENSG00000012048.20",
            "dataset_id": "gtex_v8",
        })

        called_url = mock_get.call_args[0][0]
        self.assertIn("clusteredMedianGeneExpression", called_url)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)

    @patch("tooluniverse.gtex_v2_tool.requests.get")
    def test_with_tissue_uses_median(self, mock_get):
        """With specific tissue, should use medianGeneExpression endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"tissueSiteDetailId": "Breast_Mammary_Tissue", "median": 1.3}],
            "paging_info": {},
        }
        mock_get.return_value = mock_resp

        tool = self._make_tool()
        result = tool._get_median_gene_expression({
            "gencode_id": "ENSG00000012048.20",
            "dataset_id": "gtex_v8",
            "tissue_site_detail_id": "Breast_Mammary_Tissue",
        })

        called_url = mock_get.call_args[0][0]
        self.assertIn("medianGeneExpression", called_url)
        self.assertNotIn("clustered", called_url)
        self.assertEqual(result["status"], "success")


# ---------------------------------------------------------------------------
# LiteratureSearchTool PubTator uses 'query' not 'text' (Feature-80A)
# ---------------------------------------------------------------------------
class TestLiteratureToolPubTatorParam(unittest.TestCase):
    """LiteratureSearchTool should pass 'query' not 'text' to PubTator."""

    def test_pubtator_uses_query_param(self):
        """literature_tool.py should call PubTator3_LiteratureSearch with query=, not text=."""
        import ast

        with open("src/tooluniverse/compose_scripts/literature_tool.py") as f:
            source = f.read()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Look for call_tool("PubTator3_LiteratureSearch", {...})
                if (isinstance(node.func, ast.Name) and node.func.id == "call_tool"
                        and len(node.args) >= 2):
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant) and first_arg.value == "PubTator3_LiteratureSearch":
                        dict_arg = node.args[1]
                        if isinstance(dict_arg, ast.Dict):
                            keys = [k.value if isinstance(k, ast.Constant) else str(k) for k in dict_arg.keys]
                            self.assertIn("query", keys, "PubTator call should use 'query' param")
                            self.assertNotIn("text", keys, "PubTator call should NOT use 'text' param")
                            return
        self.fail("Could not find PubTator3_LiteratureSearch call in literature_tool.py")


# ---------------------------------------------------------------------------
# BaseRESTTool: HTML error pages should return error, not success
# ---------------------------------------------------------------------------
class TestBaseRESTToolHTMLDetection(unittest.TestCase):
    """BaseRESTTool should detect HTML error pages and return status=error."""

    def test_html_response_returns_error(self):
        """When a REST API returns HTML instead of JSON, treat it as an error."""
        from tooluniverse.base_rest_tool import BaseRESTTool

        config = {
            "name": "MSigDB_get_geneset",
            "type": "BaseRESTTool",
            "fields": {
                "endpoint": "https://example.com/api/{geneSetName}",
            },
            "parameter": {
                "type": "object",
                "properties": {
                    "geneSetName": {"type": "string"},
                },
                "required": ["geneSetName"],
            },
        }
        tool = BaseRESTTool(config)

        # Mock response with HTML error page
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_resp.text = "<html><body><h1>Gene Set Not Found</h1></body></html>"
        mock_resp.headers = {"content-type": "text/html; charset=utf-8"}

        result = tool._process_response(
            mock_resp, "https://example.com/api/NONEXISTENT_GENESET"
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("HTML page", result["error"])

    def test_json_response_returns_success(self):
        """Normal JSON responses should still return success."""
        from tooluniverse.base_rest_tool import BaseRESTTool

        config = {
            "name": "test_tool",
            "type": "BaseRESTTool",
            "fields": {"endpoint": "https://example.com/api"},
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = BaseRESTTool(config)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [1, 2, 3]}
        mock_resp.headers = {"content-type": "application/json"}

        result = tool._process_response(mock_resp, "https://example.com/api")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], {"data": [1, 2, 3]})

    def test_plain_text_response_returns_success(self):
        """Non-HTML text responses (e.g., BibTeX) should still return success."""
        from tooluniverse.base_rest_tool import BaseRESTTool

        config = {
            "name": "test_tool",
            "type": "BaseRESTTool",
            "fields": {"endpoint": "https://example.com/api"},
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = BaseRESTTool(config)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_resp.text = "@article{foo, title={Bar}}"
        mock_resp.headers = {"content-type": "text/plain"}

        result = tool._process_response(mock_resp, "https://example.com/api")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], "@article{foo, title={Bar}}")


# ---------------------------------------------------------------------------
# PMC: PMID extraction uses "pmid" key (not "pubmed")
# ---------------------------------------------------------------------------
class TestPMCPmidExtraction(unittest.TestCase):
    """PMC tool should extract PMIDs using the 'pmid' key from esummary XML."""

    def test_pmid_extracted_from_article_ids(self):
        from tooluniverse.pmc_tool import PMCTool

        tool = PMCTool({"name": "PMC_search_papers", "type": "PMCTool"})
        items = {
            "Title": "Test paper",
            "ArticleIds": {
                "pmid": "12345678",
                "doi": "10.1234/test",
                "pmcid": "PMC9999999",
            },
            "AuthorList": ["Smith J"],
            "PubDate": "2024 Jan 01",
            "Source": "Nature",
        }
        paper = tool._build_paper_from_summary("9999999", items)
        self.assertEqual(paper["pmid"], "12345678")
        self.assertEqual(paper["pmc_id"], "PMC9999999")
        self.assertEqual(paper["doi"], "10.1234/test")

    def test_pmid_fallback_to_pubmed_key(self):
        """Backwards compatible: also accept 'pubmed' key."""
        from tooluniverse.pmc_tool import PMCTool

        tool = PMCTool({"name": "PMC_search_papers", "type": "PMCTool"})
        items = {
            "Title": "Old format paper",
            "ArticleIds": {"pubmed": "87654321", "pmc": "PMC1111111"},
        }
        paper = tool._build_paper_from_summary("1111111", items)
        self.assertEqual(paper["pmid"], "87654321")
        self.assertEqual(paper["pmc_id"], "PMC1111111")


# ---------------------------------------------------------------------------
# HumanBase: returns error when network API is down
# ---------------------------------------------------------------------------
class TestHumanBaseErrorHandling(unittest.TestCase):
    """HumanBase should return error status when network API fails."""

    def test_empty_graph_returns_error(self):
        from tooluniverse.humanbase_tool import HumanBaseTool

        config = {
            "name": "humanbase_ppi_analysis",
            "type": "HumanBaseTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = HumanBaseTool(config)

        # Mock humanbase_ppi_retrieve to return empty graph
        import networkx as nx

        with patch.object(
            tool, "humanbase_ppi_retrieve", return_value=(nx.Graph(), None)
        ):
            result = tool.run(
                {"gene_list": ["EGFR", "ERBB2"], "tissue": "lung"}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("STRING_get_interaction_partners", result["error"])

    def test_empty_graph_with_bp_still_returns_error(self):
        """Even if biological processes are found, empty network is an error."""
        from tooluniverse.humanbase_tool import HumanBaseTool

        config = {
            "name": "humanbase_ppi_analysis",
            "type": "HumanBaseTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        tool = HumanBaseTool(config)

        import networkx as nx

        with patch.object(
            tool,
            "humanbase_ppi_retrieve",
            return_value=(nx.Graph(), ["regulation of cell growth"]),
        ):
            result = tool.run(
                {"gene_list": ["EGFR", "ERBB2"], "tissue": "lung"}
            )
        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["biological_processes"], ["regulation of cell growth"]
        )


class TestHumanBaseGiantVersion(unittest.TestCase):
    """HumanBase API requires giant_version parameter (v1 or v3)."""

    def _make_tool(self):
        from tooluniverse.humanbase_tool import HumanBaseTool

        config = {
            "name": "humanbase_ppi_analysis",
            "type": "HumanBaseTool",
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
        return HumanBaseTool(config)

    @patch("tooluniverse.humanbase_tool.requests.get")
    def test_network_url_includes_giant_version_v1(self, mock_get):
        """Plain tissue slugs (e.g., 'brain') should use giant_version=v1."""
        tool = self._make_tool()
        # Mock get_entrez_ids to skip API calls
        with patch.object(tool, "get_entrez_ids", return_value=["7157", "672"]):
            # Mock network request to return empty to short-circuit
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"genes": [], "edges": []}
            mock_resp.raise_for_status = MagicMock()
            # BP request
            mock_bp_resp = MagicMock()
            mock_bp_resp.status_code = 200
            mock_bp_resp.json.return_value = []
            mock_bp_resp.raise_for_status = MagicMock()
            mock_get.side_effect = [mock_resp, mock_bp_resp]

            tool.humanbase_ppi_retrieve(["TP53", "BRCA1"], "brain", max_node=5)

        # Check the network URL used giant_version=v1
        network_call_url = mock_get.call_args_list[0][0][0]
        self.assertIn("giant_version=v1", network_call_url)
        self.assertIn("/brain/network/", network_call_url)

    @patch("tooluniverse.humanbase_tool.requests.get")
    def test_network_url_includes_giant_version_v3(self, mock_get):
        """Tissue slugs ending in '-v3' should use giant_version=v3."""
        tool = self._make_tool()
        with patch.object(tool, "get_entrez_ids", return_value=["7157", "672"]):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"genes": [], "edges": []}
            mock_resp.raise_for_status = MagicMock()
            mock_bp_resp = MagicMock()
            mock_bp_resp.status_code = 200
            mock_bp_resp.json.return_value = []
            mock_bp_resp.raise_for_status = MagicMock()
            mock_get.side_effect = [mock_resp, mock_bp_resp]

            tool.humanbase_ppi_retrieve(
                ["TP53", "BRCA1"], "brain-v3", max_node=5
            )

        network_call_url = mock_get.call_args_list[0][0][0]
        self.assertIn("giant_version=v3", network_call_url)
        self.assertIn("/brain-v3/network/", network_call_url)

    @patch("tooluniverse.humanbase_tool.requests.get")
    def test_evidence_url_includes_giant_version(self, mock_get):
        """Edge evidence URL should also include giant_version."""
        tool = self._make_tool()
        with patch.object(tool, "get_entrez_ids", return_value=["7157", "672"]):
            # Network response with genes and edges
            mock_net_resp = MagicMock()
            mock_net_resp.status_code = 200
            mock_net_resp.json.return_value = {
                "genes": [
                    {"standard_name": "TP53", "entrez": "7157", "description": "tumor protein p53"},
                    {"standard_name": "BRCA1", "entrez": "672", "description": "BRCA1 DNA repair"},
                ],
                "edges": [{"source": 0, "target": 1, "weight": 0.9}],
            }
            mock_net_resp.raise_for_status = MagicMock()
            # Evidence response
            mock_ev_resp = MagicMock()
            mock_ev_resp.status_code = 200
            mock_ev_resp.json.return_value = {
                "datatypes": [{"title": "co-expression", "weight": 0.8}]
            }
            mock_ev_resp.raise_for_status = MagicMock()
            # BP response
            mock_bp_resp = MagicMock()
            mock_bp_resp.status_code = 200
            mock_bp_resp.json.return_value = []
            mock_bp_resp.raise_for_status = MagicMock()
            mock_get.side_effect = [mock_net_resp, mock_ev_resp, mock_bp_resp]

            tool.humanbase_ppi_retrieve(["TP53", "BRCA1"], "brain", max_node=2)

        # The second call should be the evidence URL
        evidence_call_url = mock_get.call_args_list[1][0][0]
        self.assertIn("giant_version=v1", evidence_call_url)
        self.assertIn("/brain/evidence/", evidence_call_url)


# ---------------------------------------------------------------------------
# iCite search publications: must use PubMed eSearch first, not raw iCite API
# ---------------------------------------------------------------------------
class TestICiteSearchPublications(unittest.TestCase):
    """iCite API has no keyword search — must search PubMed first for PMIDs."""

    def _make_tool(self):
        from tooluniverse.icite_tool import ICiteSearchPublicationsTool

        config = {
            "name": "iCite_search_publications",
            "fields": {"endpoint": "https://icite.od.nih.gov/api/pubs"},
            "parameter": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": ["integer", "null"]},
                    "offset": {"type": ["integer", "null"]},
                },
            },
        }
        return ICiteSearchPublicationsTool(config)

    def test_import_tool_class(self):
        from tooluniverse.icite_tool import ICiteSearchPublicationsTool

        self.assertTrue(callable(ICiteSearchPublicationsTool))

    @patch("tooluniverse.icite_tool.request_with_retry")
    def test_searches_pubmed_then_icite(self, mock_request):
        """Tool should call PubMed eSearch first, then iCite with returned PMIDs."""
        tool = self._make_tool()

        # Mock PubMed eSearch response
        pubmed_resp = MagicMock()
        pubmed_resp.status_code = 200
        pubmed_resp.json.return_value = {
            "esearchresult": {"idlist": ["12345", "67890"]}
        }

        # Mock iCite response
        icite_resp = MagicMock()
        icite_resp.status_code = 200
        icite_resp.json.return_value = {
            "data": [
                {"pmid": 12345, "title": "Paper A", "citation_count": 50},
                {"pmid": 67890, "title": "Paper B", "citation_count": 100},
            ]
        }

        mock_request.side_effect = [pubmed_resp, icite_resp]
        result = tool.run({"query": "CRISPR", "limit": 2})

        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 2)
        # Should be sorted by citation_count descending
        self.assertEqual(result["data"][0]["pmid"], 67890)
        self.assertEqual(result["data"][1]["pmid"], 12345)

        # Verify PubMed was called first
        first_call = mock_request.call_args_list[0]
        self.assertIn("eutils.ncbi.nlm.nih.gov", first_call.args[2])

        # Verify iCite was called with PMIDs
        second_call = mock_request.call_args_list[1]
        self.assertIn("icite.od.nih.gov", second_call.args[2])
        self.assertIn("12345", second_call.kwargs["params"]["pmids"])

    @patch("tooluniverse.icite_tool.request_with_retry")
    def test_empty_query_returns_error(self, mock_request):
        tool = self._make_tool()
        result = tool.run({"query": ""})
        self.assertIn("error", result)

    @patch("tooluniverse.icite_tool.request_with_retry")
    def test_no_pubmed_results(self, mock_request):
        tool = self._make_tool()
        pubmed_resp = MagicMock()
        pubmed_resp.status_code = 200
        pubmed_resp.json.return_value = {"esearchresult": {"idlist": []}}
        mock_request.return_value = pubmed_resp

        result = tool.run({"query": "xyznonexistent123"})
        self.assertEqual(result["data"], [])
        self.assertIn("message", result)

    @patch("tooluniverse.icite_tool.request_with_retry")
    def test_offset_applied(self, mock_request):
        """Offset should skip PMIDs from PubMed results."""
        tool = self._make_tool()

        pubmed_resp = MagicMock()
        pubmed_resp.status_code = 200
        pubmed_resp.json.return_value = {
            "esearchresult": {"idlist": ["111", "222", "333"]}
        }

        icite_resp = MagicMock()
        icite_resp.status_code = 200
        icite_resp.json.return_value = {
            "data": [
                {"pmid": 222, "title": "Paper 2", "citation_count": 10},
                {"pmid": 333, "title": "Paper 3", "citation_count": 20},
            ]
        }

        mock_request.side_effect = [pubmed_resp, icite_resp]
        tool.run({"query": "test", "limit": 2, "offset": 1})

        # iCite should be called with PMIDs 222, 333 (skipping 111)
        icite_call = mock_request.call_args_list[1]
        pmids_param = icite_call.kwargs["params"]["pmids"]
        self.assertNotIn("111", pmids_param)
        self.assertIn("222", pmids_param)

    def test_json_config_uses_custom_type(self):
        """icite_tools.json must specify ICiteSearchPublicationsTool type."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            "../../src/tooluniverse/data/icite_tools.json",
        )
        with open(config_path) as f:
            tools = json.load(f)
        search_tool = next(t for t in tools if t["name"] == "iCite_search_publications")
        self.assertEqual(search_tool["type"], "ICiteSearchPublicationsTool")

    @patch("tooluniverse.icite_tool.request_with_retry")
    def test_default_limit_is_10(self, mock_request):
        """Without explicit limit, should default to 10."""
        tool = self._make_tool()

        pubmed_resp = MagicMock()
        pubmed_resp.status_code = 200
        pubmed_resp.json.return_value = {
            "esearchresult": {"idlist": [str(i) for i in range(20)]}
        }

        icite_resp = MagicMock()
        icite_resp.status_code = 200
        icite_resp.json.return_value = {
            "data": [
                {"pmid": i, "title": f"Paper {i}", "citation_count": i}
                for i in range(20)
            ]
        }

        mock_request.side_effect = [pubmed_resp, icite_resp]
        result = tool.run({"query": "test"})
        self.assertEqual(len(result["data"]), 10)


# ---------------------------------------------------------------------------
# Round 79A/B: ChEMBL drug name lookup, STITCH SSL, HMDB common name,
# MetabolomicsWorkbench empty result guidance, PDB text search metadata
# ---------------------------------------------------------------------------


class TestChEMBLDrugNameLookupIcontainsFirst(unittest.TestCase):
    """Feature-79B-001: ChEMBL_get_drug_mechanisms should find drugs by name
    using icontains (reliable) before iexact (often times out)."""

    def _make_tool(self):
        from tooluniverse.chem_tool import ChEMBLRESTTool

        config = {
            "name": "ChEMBL_get_drug_mechanisms",
            "base_url": "https://www.ebi.ac.uk/chembl/api/data",
            "fields": {"endpoint": "mechanism"},
        }
        return ChEMBLRESTTool(config)

    @patch("tooluniverse.chem_tool.requests.get")
    def test_icontains_finds_sotorasib(self, mock_get):
        """icontains lookup should find sotorasib and return parent ChEMBL ID."""
        tool = self._make_tool()

        # Mock icontains response
        icontains_resp = MagicMock()
        icontains_resp.status_code = 200
        icontains_resp.json.return_value = {
            "molecules": [
                {
                    "pref_name": "SOTORASIB",
                    "molecule_chembl_id": "CHEMBL4535757",
                    "molecule_hierarchy": {"parent_chembl_id": "CHEMBL4535757"},
                }
            ]
        }
        icontains_resp.raise_for_status = MagicMock()

        mock_get.return_value = icontains_resp

        result = tool._lookup_chembl_id_by_name("sotorasib")
        self.assertEqual(result, "CHEMBL4535757")

        # Verify icontains was tried (first param set)
        call_args = mock_get.call_args_list[0]
        self.assertIn("pref_name__icontains", call_args.kwargs.get("params", call_args[1].get("params", {})))

    @patch("tooluniverse.chem_tool.requests.get")
    def test_parent_compound_preferred(self, mock_get):
        """Should return parent compound ID for salt forms."""
        tool = self._make_tool()

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "molecules": [
                {
                    "pref_name": "DASATINIB MONOHYDRATE",
                    "molecule_chembl_id": "CHEMBL5416410",
                    "molecule_hierarchy": {"parent_chembl_id": "CHEMBL1421"},
                }
            ]
        }
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        result = tool._lookup_chembl_id_by_name("dasatinib")
        self.assertEqual(result, "CHEMBL1421")


class TestSTITCHSSLWarning(unittest.TestCase):
    """Feature-79B-006: STITCH should not crash with formatwarning error."""

    def _make_tool(self):
        from tooluniverse.stitch_tool import STITCHTool

        config = {
            "name": "STITCH_get_chemical_protein_interactions",
            "fields": {"operation": "get_interactions"},
        }
        return STITCHTool(config)

    @patch("tooluniverse.stitch_tool.requests.get")
    def test_404_returns_actionable_error(self, mock_get):
        """404 response should return helpful error, not crash."""
        tool = self._make_tool()

        resp = MagicMock()
        resp.status_code = 404
        mock_get.return_value = resp

        result = tool._get_interactions({"identifiers": ["sotorasib"]})
        self.assertIn("error", result)
        self.assertIn("No interactions found", result["error"])
        self.assertIn("CID", result["error"])

    @patch("tooluniverse.stitch_tool.requests.get")
    def test_success_returns_interactions(self, mock_get):
        """Successful response should return interactions."""
        tool = self._make_tool()

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [{"stringId_A": "CID1", "stringId_B": "ENSP001", "score": 900}]
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        result = tool._get_interactions({"identifiers": ["aspirin"]})
        self.assertIn("interactions", result)
        self.assertEqual(len(result["interactions"]), 1)


class TestHMDBCommonName(unittest.TestCase):
    """Feature-79A-006: HMDB should return common name, not just IUPAC."""

    def _make_tool(self):
        from tooluniverse.hmdb_tool import HMDBTool

        config = {"name": "HMDB_get_metabolite"}
        return HMDBTool(config)

    @patch("tooluniverse.hmdb_tool.requests.get")
    def test_common_name_returned(self, mock_get):
        """Should return Title (common name) as primary name field."""
        tool = self._make_tool()

        # Mock PubChem xref response
        xref_resp = MagicMock()
        xref_resp.status_code = 200
        xref_resp.json.return_value = {
            "PC_Compounds": [{"id": {"id": {"cid": 305}}}]
        }

        # Mock PubChem property response with Title
        props_resp = MagicMock()
        props_resp.status_code = 200
        props_resp.json.return_value = {
            "PropertyTable": {
                "Properties": [
                    {
                        "CID": 305,
                        "Title": "Choline",
                        "IUPACName": "2-hydroxyethyl(trimethyl)azanium",
                        "MolecularFormula": "C5H14NO+",
                        "MolecularWeight": "104.17",
                    }
                ]
            }
        }

        mock_get.side_effect = [xref_resp, props_resp]
        result = tool._get_metabolite({"hmdb_id": "HMDB0000097"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["name"], "Choline")
        self.assertEqual(result["data"]["iupac_name"], "2-hydroxyethyl(trimethyl)azanium")


class TestMetabolomicsWorkbenchEmptyGuidance(unittest.TestCase):
    """Feature-79A-001: MW should give guidance when RefMet returns empty results."""

    def _make_tool(self):
        from tooluniverse.metabolomics_workbench_tool import MetabolomicsWorkbenchTool

        config = {
            "name": "MetabolomicsWorkbench_search_compound_by_name",
            "fields": {"context": "refmet", "input_item": "name"},
        }
        return MetabolomicsWorkbenchTool(config)

    @patch("tooluniverse.metabolomics_workbench_tool.requests.get")
    def test_empty_array_includes_guidance(self, mock_get):
        """Empty array response should include guidance about exact names."""
        tool = self._make_tool()

        resp = MagicMock()
        resp.status_code = 200
        resp.text = "[]"
        resp.json.return_value = []
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        result = tool._make_request("refmet/name/bile acid/all")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], [])
        self.assertIn("message", result)
        self.assertIn("exact metabolite names", result["message"])
        self.assertIn("ChEBI_search", result["message"])


class TestPDBTextSearchMetadata(unittest.TestCase):
    """Feature-79B-003: PDB text search should include title and resolution."""

    def _make_tool(self):
        from tooluniverse.rcsb_search_tool import RCSBSearchTool

        config = {"name": "PDB_search_similar_structures"}
        return RCSBSearchTool(config)

    @patch("tooluniverse.rcsb_search_tool.requests.post")
    @patch("tooluniverse.rcsb_search_tool.requests.get")
    def test_text_results_enriched_with_metadata(self, mock_get, mock_post):
        """Text search results should have title, resolution, method."""
        tool = self._make_tool()

        # Patch _enrich via the post/get mocks
        # First: search API response
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.json.return_value = {
            "result_set": [
                {"identifier": "5V9O", "score": 1.0},
                {"identifier": "6GOG", "score": 0.9},
            ],
            "total_count": 2,
        }
        search_resp.raise_for_status = MagicMock()
        search_resp.content = b"data"

        mock_post.return_value = search_resp

        # Second: GraphQL metadata response
        graphql_resp = MagicMock()
        graphql_resp.status_code = 200
        graphql_resp.json.return_value = {
            "data": {
                "entries": [
                    {
                        "rcsb_id": "5V9O",
                        "struct": {"title": "KRAS G12C inhibitor"},
                        "rcsb_entry_info": {
                            "resolution_combined": [1.56],
                            "experimental_method": "X-ray",
                        },
                    },
                    {
                        "rcsb_id": "6GOG",
                        "struct": {"title": "KRAS-169 Q61H"},
                        "rcsb_entry_info": {
                            "resolution_combined": [2.05],
                            "experimental_method": "X-ray",
                        },
                    },
                ]
            }
        }

        # requests.post is used for search, requests.get is not used here
        # but _enrich uses requests.post for GraphQL
        mock_post.side_effect = [search_resp, graphql_resp]

        result = tool.run({"query": "KRAS", "search_type": "text", "max_results": 2})
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["results"][0]["title"], "KRAS G12C inhibitor")
        self.assertEqual(result["results"][0]["resolution"], 1.56)
        self.assertEqual(result["results"][0]["method"], "X-ray")


if __name__ == "__main__":
    unittest.main()
