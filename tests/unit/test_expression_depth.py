"""Expression-depth tools: parse + error-path coverage (mocked HTTP).

Covers six new tools that close confirmed expression-cluster capability gaps,
all reusing existing tool classes (no new @register_tool class):

GTExV2Tool (gtex_v2):
  * ``GTEx_get_single_tissue_sqtls`` — single-tissue splicing QTLs (sQTLs)
    + sGenes (/association/singleTissueSqtl, /association/sgene).
  * ``GTEx_get_median_transcript_expression`` — per-transcript (ENST) median
    TPM across tissues (/expression/medianTranscriptExpression).
  * ``GTEx_get_single_nucleus_expression`` — snRNA-seq expression by cell type
    (/expression/singleNucleusGeneExpression[Summary]).
  * ``GTEx_get_finemapping_and_independent_eqtl`` — DAP-G fine-mapping credible
    sets + conditionally-independent eQTLs (/association/fineMapping,
    /association/independentEqtl).

HarmonizomeTool (harmonizome):
  * ``Harmonizome_get_gene_set_members`` — gene-set members + per-gene
    associations (/gene_set/{attr}/{dataset}, /gene/{sym}?showAssociations).

SCExpressionAtlasTool (scxa):
  * ``SCXA_get_cluster_marker_genes`` — computed marker genes per cluster /
    cell type (/experiments/{acc}/marker-genes/clusters|cell-types).

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _resp(json_body, status=200, text=""):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.text = text
    r.raise_for_status = MagicMock()
    return r


# ---------------------------------------------------------------------------
# GTExV2Tool helpers
# ---------------------------------------------------------------------------


def _gtex_tool(operation):
    from tooluniverse.gtex_v2_tool import GTExV2Tool

    return GTExV2Tool(
        {
            "name": f"GTEx_{operation}",
            "parameter": {"required": []},
        }
    )


# The handlers call _resolve_gencode_id() (which hits /reference/gene). Tests
# always pass versioned GENCODE IDs so resolution is a no-op even if the mock
# returns an empty body for that endpoint.
def _gtex_side_effect(payload_by_path):
    """Return a side_effect routing requests.get by endpoint substring."""

    def _side(url, *args, **kwargs):
        for needle, payload in payload_by_path.items():
            if needle in url:
                return _resp(payload)
        # /reference/gene resolution and anything unmapped -> empty body
        return _resp({"data": []})

    return _side


# ---------------------------------------------------------------------------
# GTEx_get_single_tissue_sqtls
# ---------------------------------------------------------------------------

_SQTL_BODY = {
    "data": [
        {
            "snpId": "rs72772072",
            "variantId": "chr5_96659855_A_G_b38",
            "geneSymbol": "ERAP2",
            "gencodeId": "ENSG00000164308.16",
            "tissueSiteDetailId": "Whole_Blood",
            "pValue": 1.22229e-06,
            "nes": 0.439492,
            "phenotypeId": "chr5:96900189:96901506:clu_31758:ENSG00000164308.16",
        }
    ],
    "paging_info": {"totalNumberOfItems": 962},
}

_SGENE_BODY = {
    "data": [
        {
            "geneSymbol": "WASH7P",
            "gencodeId": "ENSG00000227232.5",
            "tissueSiteDetailId": "Whole_Blood",
            "qValue": 0.00215589,
            "phenotypeId": "chr1:15947:16607:clu_40980:ENSG00000227232.5",
        }
    ],
    "paging_info": {"totalNumberOfItems": 3013},
}


class TestGTExSqtls(unittest.TestCase):
    def test_sqtl_mode_parses_phenotype_cluster(self):
        """sQTL mode parses LeafCutter phenotypeId cluster and hits the sQTL endpoint."""
        tool = _gtex_tool("get_single_tissue_sqtls")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.side_effect = _gtex_side_effect({"singleTissueSqtl": _SQTL_BODY})
            res = tool.run(
                {
                    "operation": "get_single_tissue_sqtls",
                    "gencode_id": "ENSG00000164308.16",
                    "tissue_site_detail_id": ["Whole_Blood"],
                }
            )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["num_sqtls"], 1)
        row = res["data"][0]
        self.assertEqual(row["variantId"], "chr5_96659855_A_G_b38")
        self.assertIn("clu_31758", row["phenotypeId"])
        # Hit the sQTL endpoint, not the eQTL endpoint.
        called = " ".join(str(c) for c in g.call_args_list)
        self.assertIn("singleTissueSqtl", called)

    def test_sgene_mode_uses_sgene_endpoint(self):
        """sGene mode routes to /association/sgene and parses qValue."""
        tool = _gtex_tool("get_single_tissue_sqtls")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.side_effect = _gtex_side_effect({"/association/sgene": _SGENE_BODY})
            res = tool.run(
                {
                    "operation": "get_single_tissue_sqtls",
                    "result_type": "sgene",
                    "tissue_site_detail_id": ["Whole_Blood"],
                }
            )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["num_sgenes"], 1)
        self.assertEqual(res["data"][0]["geneSymbol"], "WASH7P")
        called = " ".join(str(c) for c in g.call_args_list)
        self.assertIn("/association/sgene", called)

    def test_error_path_http_500(self):
        """Non-200 HTTP status yields a structured error result."""
        tool = _gtex_tool("get_single_tissue_sqtls")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.return_value = _resp({}, status=500, text="boom")
            res = tool.run(
                {
                    "operation": "get_single_tissue_sqtls",
                    "gencode_id": "ENSG00000164308.16",
                    "tissue_site_detail_id": ["Whole_Blood"],
                }
            )
        self.assertEqual(res["status"], "error")
        self.assertIn("500", res["error"])

    def test_exception_never_raises(self):
        """An exception in requests.get is caught and returned as an error."""
        tool = _gtex_tool("get_single_tissue_sqtls")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.side_effect = RuntimeError("network down")
            res = tool.run(
                {
                    "operation": "get_single_tissue_sqtls",
                    "gencode_id": "ENSG00000164308.16",
                }
            )
        self.assertEqual(res["status"], "error")


# ---------------------------------------------------------------------------
# GTEx_get_median_transcript_expression
# ---------------------------------------------------------------------------

_TX_BODY = {
    "data": [
        {
            "transcriptId": "ENST00000352993.7",
            "median": 0.37,
            "unit": "TPM",
            "tissueSiteDetailId": "Whole_Blood",
            "gencodeId": "ENSG00000012048.20",
            "geneSymbol": "BRCA1",
        },
        {
            "transcriptId": "ENST00000354071.7",
            "median": 0.0,
            "unit": "TPM",
            "tissueSiteDetailId": "Whole_Blood",
            "gencodeId": "ENSG00000012048.20",
            "geneSymbol": "BRCA1",
        },
    ],
    "paging_info": {"totalNumberOfItems": 30},
}


class TestGTExMedianTranscript(unittest.TestCase):
    def test_parses_transcript_rows(self):
        """Per-transcript (ENST) median rows are parsed."""
        tool = _gtex_tool("get_median_transcript_expression")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.side_effect = _gtex_side_effect({"medianTranscriptExpression": _TX_BODY})
            res = tool.run(
                {
                    "operation": "get_median_transcript_expression",
                    "gencode_id": "ENSG00000012048.20",
                    "tissue_site_detail_id": ["Whole_Blood"],
                }
            )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["num_results"], 2)
        self.assertEqual(res["data"][0]["transcriptId"], "ENST00000352993.7")
        self.assertEqual(res["data"][0]["median"], 0.37)

    def test_missing_gene_is_error(self):
        """A missing gene identifier produces a structured error."""
        tool = _gtex_tool("get_median_transcript_expression")
        res = tool.run({"operation": "get_median_transcript_expression"})
        self.assertEqual(res["status"], "error")
        self.assertIn("gencode_id", res["error"])

    def test_error_path_http_404(self):
        """An HTTP 404 yields a structured error result."""
        tool = _gtex_tool("get_median_transcript_expression")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.return_value = _resp({}, status=404, text="not found")
            res = tool.run(
                {
                    "operation": "get_median_transcript_expression",
                    "gencode_id": "ENSG00000012048.20",
                }
            )
        self.assertEqual(res["status"], "error")


# ---------------------------------------------------------------------------
# GTEx_get_single_nucleus_expression
# ---------------------------------------------------------------------------

_SN_DETAIL_BODY = {
    "data": [
        {
            "tissueSiteDetailId": "Muscle_Skeletal",
            "gencodeId": "ENSG00000012048.20",
            "geneSymbol": "BRCA1",
            "datasetId": "gtex_snrnaseq_pilot",
            "cellTypes": [
                {
                    "cellType": "Myocyte (NMJ-rich)",
                    "count": 6,
                    "meanWithoutZeros": 1.455,
                    "meanWithZeros": 0.0919,
                    "numZeros": 89,
                },
                {
                    "cellType": "Endothelial cell (vascular)",
                    "count": 38,
                    "meanWithoutZeros": 2.264,
                    "meanWithZeros": 0.0765,
                    "numZeros": 1086,
                },
            ],
        }
    ],
    "paging_info": {"totalNumberOfItems": 1},
}

_SN_SUMMARY_BODY = {
    "data": [
        {
            "tissueSiteDetailId": "Muscle_Skeletal",
            "datasetId": "gtex_snrnaseq_pilot",
            "cellType": "Myocyte (sk. muscle, cytoplasmic)",
            "numCells": 769,
        }
    ],
    "paging_info": {"totalNumberOfItems": 14},
}


class TestGTExSingleNucleus(unittest.TestCase):
    def test_detail_mode_parses_cell_types(self):
        """Detail mode parses per-cell-type snRNA-seq stats."""
        tool = _gtex_tool("get_single_nucleus_expression")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.side_effect = _gtex_side_effect(
                {"singleNucleusGeneExpression": _SN_DETAIL_BODY}
            )
            res = tool.run(
                {
                    "operation": "get_single_nucleus_expression",
                    "gencode_id": "ENSG00000012048.20",
                    "tissue_site_detail_id": ["Muscle_Skeletal"],
                }
            )
        self.assertEqual(res["status"], "success")
        cts = res["data"][0]["cellTypes"]
        self.assertEqual(cts[0]["cellType"], "Myocyte (NMJ-rich)")
        self.assertEqual(cts[0]["count"], 6)

    def test_summary_mode_uses_summary_endpoint(self):
        """Summary mode routes to the snRNA-seq summary endpoint."""
        tool = _gtex_tool("get_single_nucleus_expression")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.side_effect = _gtex_side_effect(
                {"singleNucleusGeneExpressionSummary": _SN_SUMMARY_BODY}
            )
            res = tool.run(
                {
                    "operation": "get_single_nucleus_expression",
                    "result_type": "summary",
                    "gencode_id": "ENSG00000012048.20",
                    "tissue_site_detail_id": ["Muscle_Skeletal"],
                }
            )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"][0]["numCells"], 769)
        called = " ".join(str(c) for c in g.call_args_list)
        self.assertIn("singleNucleusGeneExpressionSummary", called)

    def test_missing_gene_is_error(self):
        """A missing gene identifier produces a structured error."""
        tool = _gtex_tool("get_single_nucleus_expression")
        res = tool.run({"operation": "get_single_nucleus_expression"})
        self.assertEqual(res["status"], "error")


# ---------------------------------------------------------------------------
# GTEx_get_finemapping_and_independent_eqtl
# ---------------------------------------------------------------------------

_FM_BODY = {
    "data": [
        {
            "gencodeId": "ENSG00000164308.16",
            "method": "DAP-G",
            "pip": 0.9468,
            "setId": 1,
            "setSize": 2,
            "tissueSiteDetailId": "Adipose_Subcutaneous",
            "variantId": "chr5_96916728_G_A_b38",
        }
    ],
    "paging_info": {"totalNumberOfItems": 150},
}

_IND_BODY = {
    "data": [
        {
            "gencodeId": "ENSG00000164308.16",
            "geneSymbol": "ERAP2",
            "variantId": "chr5_96916728_G_A_b38",
            "snpId": "rs2927608",
            "tissueSiteDetailId": "Esophagus_Gastroesophageal_Junction",
            "rank": 1,
            "pValue": 2.88e-123,
            "nes": 1.07644,
        }
    ],
    "paging_info": {"totalNumberOfItems": 50},
}


class TestGTExFineMapping(unittest.TestCase):
    def test_finemapping_mode_parses_pip(self):
        """Fine-mapping mode parses DAP-G PIP and setId."""
        tool = _gtex_tool("get_finemapping_and_independent_eqtl")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.side_effect = _gtex_side_effect({"/association/fineMapping": _FM_BODY})
            res = tool.run(
                {
                    "operation": "get_finemapping_and_independent_eqtl",
                    "gencode_id": "ENSG00000164308.16",
                }
            )
        self.assertEqual(res["status"], "success")
        row = res["data"][0]
        self.assertEqual(row["method"], "DAP-G")
        self.assertEqual(row["pip"], 0.9468)
        self.assertEqual(row["setId"], 1)

    def test_independent_mode_uses_independent_endpoint(self):
        """Independent mode routes to /association/independentEqtl."""
        tool = _gtex_tool("get_finemapping_and_independent_eqtl")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.side_effect = _gtex_side_effect(
                {"/association/independentEqtl": _IND_BODY}
            )
            res = tool.run(
                {
                    "operation": "get_finemapping_and_independent_eqtl",
                    "result_type": "independent",
                    "gencode_id": "ENSG00000164308.16",
                }
            )
        self.assertEqual(res["status"], "success")
        row = res["data"][0]
        self.assertEqual(row["snpId"], "rs2927608")
        self.assertEqual(row["rank"], 1)
        called = " ".join(str(c) for c in g.call_args_list)
        self.assertIn("/association/independentEqtl", called)

    def test_missing_gene_is_error(self):
        """A missing gene identifier produces a structured error."""
        tool = _gtex_tool("get_finemapping_and_independent_eqtl")
        res = tool.run({"operation": "get_finemapping_and_independent_eqtl"})
        self.assertEqual(res["status"], "error")

    def test_error_path_http_500(self):
        """Non-200 HTTP status yields a structured error result."""
        tool = _gtex_tool("get_finemapping_and_independent_eqtl")
        with patch("tooluniverse.gtex_v2_tool.requests.get") as g:
            g.return_value = _resp({}, status=500, text="boom")
            res = tool.run(
                {
                    "operation": "get_finemapping_and_independent_eqtl",
                    "gencode_id": "ENSG00000164308.16",
                }
            )
        self.assertEqual(res["status"], "error")


# ---------------------------------------------------------------------------
# Harmonizome_get_gene_set_members
# ---------------------------------------------------------------------------


def _harm_tool():
    from tooluniverse.harmonizome_tool import HarmonizomeTool

    return HarmonizomeTool(
        {
            "name": "Harmonizome_get_gene_set_members",
            "fields": {"endpoint": "get_gene_set_members"},
        }
    )


_HARM_GENE_SET_BODY = {
    "attribute": {"name": "heart"},
    "dataset": {"name": "GTEx Tissue Gene Expression Profiles"},
    "associations": [
        {
            "gene": {"symbol": "DTD2", "href": "/api/1.0/gene/DTD2"},
            "thresholdValue": -1.0,
            "standardizedValue": -1.05248,
        },
        {
            "gene": {"symbol": "MIR3180-4", "href": "/api/1.0/gene/MIR3180-4"},
            "thresholdValue": -1.0,
            "standardizedValue": -1.45829,
        },
    ],
}

_HARM_GENE_BODY = {
    "symbol": "DTD2",
    "name": "D-aminoacyl-tRNA deacylase 2",
    "ncbiEntrezGeneId": 92675,
    "associations": [
        {
            "geneSet": {
                "name": "facial motor nucleus, right/Allen Brain Atlas",
                "href": "/api/1.0/gene_set/facial+motor+nucleus%2C+right/x",
            },
            "thresholdValue": 1.0,
            "standardizedValue": 0.883513,
        }
    ],
}


class TestHarmonizomeGeneSetMembers(unittest.TestCase):
    def test_gene_set_mode_parses_members(self):
        """Gene-set mode parses member genes and encodes the dataset path."""
        tool = _harm_tool()
        with patch("tooluniverse.harmonizome_tool.requests.get") as g:
            g.return_value = _resp(_HARM_GENE_SET_BODY)
            res = tool.run(
                {
                    "mode": "gene_set",
                    "attribute": "heart",
                    "dataset": "GTEx Tissue Gene Expression Profiles",
                }
            )
        self.assertEqual(res["status"], "success")
        members = res["data"]["members"]
        self.assertEqual(members[0]["gene"], "DTD2")
        self.assertEqual(members[0]["standardized_value"], -1.05248)
        self.assertEqual(res["metadata"]["total_associations"], 2)
        # URL path encodes spaces as '+'.
        url = g.call_args[0][0]
        self.assertIn("/gene_set/heart/", url)
        self.assertIn("GTEx+Tissue+Gene+Expression+Profiles", url)

    def test_gene_mode_parses_associations(self):
        """Gene mode parses the per-gene association table with showAssociations."""
        tool = _harm_tool()
        with patch("tooluniverse.harmonizome_tool.requests.get") as g:
            g.return_value = _resp(_HARM_GENE_BODY)
            res = tool.run({"mode": "gene", "gene_symbol": "DTD2"})
        self.assertEqual(res["status"], "success")
        assoc = res["data"]["associations"]
        self.assertEqual(assoc[0]["standardized_value"], 0.883513)
        self.assertIn("facial motor nucleus", assoc[0]["gene_set"])
        # showAssociations=true must be sent.
        self.assertEqual(g.call_args.kwargs["params"]["showAssociations"], "true")

    def test_gene_set_mode_requires_attribute_and_dataset(self):
        """Gene-set mode requires both attribute and dataset."""
        tool = _harm_tool()
        res = tool.run({"mode": "gene_set", "attribute": "heart"})
        self.assertEqual(res["status"], "error")

    def test_gene_mode_requires_symbol(self):
        """Gene mode requires a gene symbol."""
        tool = _harm_tool()
        res = tool.run({"mode": "gene"})
        self.assertEqual(res["status"], "error")

    def test_http_error_is_handled(self):
        """A connection error is returned as a structured error."""
        tool = _harm_tool()
        with patch("tooluniverse.harmonizome_tool.requests.get") as g:
            import requests as _rq

            g.side_effect = _rq.exceptions.ConnectionError("down")
            res = tool.run(
                {
                    "mode": "gene_set",
                    "attribute": "heart",
                    "dataset": "GTEx Tissue Gene Expression Profiles",
                }
            )
        self.assertEqual(res["status"], "error")


# ---------------------------------------------------------------------------
# SCXA_get_cluster_marker_genes
# ---------------------------------------------------------------------------


def _scxa_tool():
    from tooluniverse.scxa_tool import SCExpressionAtlasTool

    return SCExpressionAtlasTool(
        {
            "name": "SCXA_get_cluster_marker_genes",
            "fields": {"operation": "cluster_marker_genes"},
        }
    )


_SCXA_CLUSTER_BODY = [
    {
        "x": 7,
        "y": 0,
        "geneName": "ENSG00000224981",
        "value": 0.0,
        "cellGroupValue": "8",
        "cellGroupValueWhereMarker": "1",
        "pValue": 4.37261792498723e-71,
        "expressionUnit": "CPM",
    },
    {
        "x": 1,
        "y": 0,
        "geneName": "Olfm4",
        "value": 0.0,
        "cellGroupValue": "2",
        "cellGroupValueWhereMarker": "1",
        "pValue": 3.0036957507712e-179,
        "expressionUnit": "CPM",
    },
]


class TestSCXAClusterMarkers(unittest.TestCase):
    def test_clusters_mode_parses_rows(self):
        """Clusters mode parses marker rows and routes with the k param."""
        tool = _scxa_tool()
        with patch("tooluniverse.scxa_tool.requests.get") as g:
            g.return_value = _resp(_SCXA_CLUSTER_BODY)
            res = tool.run({"experiment_accession": "E-MTAB-5061", "k": 8})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["metadata"]["num_markers"], 2)
        row = res["data"][0]
        self.assertEqual(row["gene_name"], "ENSG00000224981")
        self.assertEqual(row["cell_group_value_where_marker"], "1")
        self.assertEqual(row["expression_unit"], "CPM")
        # clusters route + k param.
        url = g.call_args[0][0]
        self.assertIn("/marker-genes/clusters", url)
        self.assertEqual(g.call_args.kwargs["params"]["k"], 8)

    def test_limit_truncates_rows(self):
        """The limit argument truncates the returned marker rows."""
        tool = _scxa_tool()
        with patch("tooluniverse.scxa_tool.requests.get") as g:
            g.return_value = _resp(_SCXA_CLUSTER_BODY)
            res = tool.run({"experiment_accession": "E-MTAB-5061", "k": 8, "limit": 1})
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["data"]), 1)

    def test_cell_types_mode_uses_cell_types_route(self):
        """Cell-types mode routes to /marker-genes/cell-types with organismPart."""
        tool = _scxa_tool()
        with patch("tooluniverse.scxa_tool.requests.get") as g:
            g.return_value = _resp([])
            res = tool.run(
                {
                    "experiment_accession": "E-MTAB-5061",
                    "marker_type": "cell_types",
                    "organism_part": "pancreas",
                }
            )
        self.assertEqual(res["status"], "success")
        url = g.call_args[0][0]
        self.assertIn("/marker-genes/cell-types", url)
        self.assertEqual(g.call_args.kwargs["params"]["organismPart"], "pancreas")

    def test_missing_accession_is_error(self):
        """A missing experiment accession produces a structured error."""
        tool = _scxa_tool()
        res = tool.run({"k": 8})
        self.assertEqual(res["status"], "error")

    def test_clusters_mode_requires_k(self):
        """Clusters mode requires the k clustering resolution."""
        tool = _scxa_tool()
        res = tool.run({"experiment_accession": "E-MTAB-5061"})
        self.assertEqual(res["status"], "error")

    def test_cell_types_mode_requires_organism_part(self):
        """Cell-types mode requires organism_part."""
        tool = _scxa_tool()
        res = tool.run(
            {"experiment_accession": "E-MTAB-5061", "marker_type": "cell_types"}
        )
        self.assertEqual(res["status"], "error")

    def test_error_dict_body_is_handled(self):
        """An error dict body from the API is returned as a structured error."""
        tool = _scxa_tool()
        with patch("tooluniverse.scxa_tool.requests.get") as g:
            g.return_value = _resp(
                {"error": "Required Set parameter 'organismPart' is not present"}
            )
            res = tool.run(
                {
                    "experiment_accession": "E-MTAB-5061",
                    "marker_type": "cell_types",
                    "organism_part": "pancreas",
                }
            )
        self.assertEqual(res["status"], "error")

    def test_exception_never_raises(self):
        """An exception in requests.get is caught and returned as an error."""
        tool = _scxa_tool()
        with patch("tooluniverse.scxa_tool.requests.get") as g:
            g.side_effect = RuntimeError("boom")
            res = tool.run({"experiment_accession": "E-MTAB-5061", "k": 8})
        self.assertEqual(res["status"], "error")


if __name__ == "__main__":
    unittest.main()
