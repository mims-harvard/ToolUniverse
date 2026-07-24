"""Mocked-HTTP unit tests for the model-organism depth tools.

Covers the 15 tools added for the model-organism cluster (SGD regulation /
sequence / disease, WormBase orthologs / interactions / human diseases, RGD
QTLs / symbol-or-region resolution, Alliance orthologs / molecular
interactions / alleles+models, PomBase orthologs / interactions / GO, and the
InterMine PathQuery passthrough). Each tool gets a parse test against a
trimmed real-shape payload and an error-path test. No live network calls.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from tooluniverse.sgd_tool import SGDTool
from tooluniverse.wormbase_tool import WormBaseTool
from tooluniverse.rgd_tool import RGDTool
from tooluniverse.alliance_genome_tool import AllianceGenomeTool
from tooluniverse.pombase_tool import PomBaseTool
from tooluniverse.base_rest_tool import BaseRESTTool


def _resp(payload, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    r.headers = {"content-type": "application/json"}
    r.text = ""
    return r


def _tool(cls, endpoint_type, query_mode=None):
    fields = {"endpoint_type": endpoint_type}
    if query_mode is not None:
        fields = {"endpoint_type": endpoint_type, "query_mode": query_mode}
    return cls(
        {
            "name": "T",
            "type": cls.__name__,
            "fields": fields,
            "parameter": {"type": "object", "properties": {}},
        }
    )


# --------------------------------------------------------------------------
# SGD
# --------------------------------------------------------------------------
class TestSGDRegulation:
    def _make(self):
        return _tool(SGDTool, "locus", "regulation")

    def test_parse_success(self):
        """Covers parse success."""
        payload = [
            {
                "locus1": {"display_name": "IXR1", "link": "/locus/S000001515"},
                "locus2": {"display_name": "CDC28", "link": "/locus/S000000364"},
                "evidence": {
                    "display_name": "DNA to cDNA expression microarray evidence"
                },
                "regulation_of": "transcription",
                "direction": "positive",
                "happens_during": "cellular response to hypoxia",
                "annotation_type": "high-throughput",
                "reference": {
                    "display_name": "Vizoso-Vazquez A, et al. (2012)",
                    "pubmed_id": 22189861,
                },
            }
        ]
        with patch("tooluniverse.sgd_tool.requests.get", return_value=_resp(payload)):
            out = self._make().run({"sgd_id": "S000000364"})
        assert out["status"] == "success"
        row = out["data"][0]
        assert row["regulator"] == "IXR1"
        assert row["regulator_sgdid"] == "S000001515"
        assert row["target"] == "CDC28"
        assert row["regulation_of"] == "transcription"

    def test_missing_id(self):
        """Covers missing id."""
        out = self._make().run({})
        assert out["status"] == "error"

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.sgd_tool.requests.get",
            side_effect=Exception("boom"),
        ):
            out = self._make().run({"sgd_id": "S000000364"})
        assert out["status"] == "error"


class TestSGDSequence:
    def _make(self):
        return _tool(SGDTool, "locus", "sequence")

    def test_parse_success(self):
        """Covers parse success."""
        payload = {
            "genomic_dna": [
                {
                    "start": 560078,
                    "end": 560974,
                    "strand": "+",
                    "residues": "ATGAGCGGT",
                    "strain": {"display_name": "S288C"},
                }
            ],
            "coding_dna": [{"residues": "ATGAGC", "strain": {"display_name": "S288C"}}],
            "protein": [{"residues": "MSG", "strain": {"display_name": "S288C"}}],
        }
        with patch("tooluniverse.sgd_tool.requests.get", return_value=_resp(payload)):
            out = self._make().run({"sgd_id": "S000000364"})
        assert out["status"] == "success"
        g = out["data"]["genomic_dna"]
        assert g["start"] == 560078 and g["end"] == 560974
        assert g["residues"].startswith("ATGAGCGGT")
        assert out["data"]["protein"]["residues"] == "MSG"

    def test_error_path(self):
        """Covers error path."""
        with patch("tooluniverse.sgd_tool.requests.get", side_effect=Exception("x")):
            out = self._make().run({"sgd_id": "S000000364"})
        assert out["status"] == "error"


class TestSGDDisease:
    def _make(self):
        return _tool(SGDTool, "locus", "disease")

    def test_parse_success(self):
        """Covers parse success."""
        payload = [
            {
                "annotation_type": "manually curated",
                "disease": {"display_name": "cancer", "disease_id": "DOID:162"},
                "locus": {"display_name": "CDC28", "link": "/locus/S000000364"},
                "source": {"display_name": "SGD"},
                "reference": {
                    "display_name": "Mayi T, et al. (2015)",
                    "pubmed_id": 25541464,
                },
            }
        ]
        with patch("tooluniverse.sgd_tool.requests.get", return_value=_resp(payload)):
            out = self._make().run({"sgd_id": "S000000364"})
        assert out["status"] == "success"
        row = out["data"][0]
        assert row["disease_name"] == "cancer"
        assert row["disease_id"] == "DOID:162"
        assert row["annotation_type"] == "manually curated"

    def test_error_path(self):
        """Covers error path."""
        with patch("tooluniverse.sgd_tool.requests.get", side_effect=Exception("x")):
            out = self._make().run({"sgd_id": "S000000364"})
        assert out["status"] == "error"


# --------------------------------------------------------------------------
# WormBase
# --------------------------------------------------------------------------
class TestWormBaseOrthologs:
    def _make(self):
        return _tool(WormBaseTool, "gene_orthologs")

    def test_parse_success(self):
        """Covers parse success."""
        payload = {
            "fields": {
                "other_orthologs": {
                    "data": [
                        {
                            "species": {"genus": "D", "species": "rerio"},
                            "ortholog": {
                                "id": "ZFIN:ZDB-GENE-061215-70",
                                "label": "pou4f4",
                            },
                            "method": [
                                {"label": "Inparanoid"},
                                {"label": "EnsEMBL-Compara"},
                            ],
                        }
                    ]
                },
                "nematode_orthologs": {
                    "data": [
                        {
                            "species": {"genus": "C", "species": "tribulationis"},
                            "ortholog": {"id": "CSP40.g8217", "label": "CSP40.g8217"},
                            "method": [{"label": "WormBase-Compara"}],
                        }
                    ]
                },
                "paralogs": {"data": []},
            }
        }
        with patch(
            "tooluniverse.wormbase_tool.requests.get", return_value=_resp(payload)
        ):
            out = self._make().run({"gene_id": "WBGene00006818"})
        assert out["status"] == "success"
        data = out["data"]
        assert data["cross_species_ortholog_count"] == 1
        assert (
            data["cross_species_orthologs"][0]["ortholog_id"]
            == "ZFIN:ZDB-GENE-061215-70"
        )
        assert data["nematode_orthologs"][0]["ortholog_id"] == "CSP40.g8217"

    def test_missing_id(self):
        """Covers missing id."""
        assert self._make().run({})["status"] == "error"

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.wormbase_tool.requests.get", side_effect=Exception("x")
        ):
            out = self._make().run({"gene_id": "WBGene00006818"})
        assert out["status"] == "error"


class TestWormBaseInteractions:
    def _make(self):
        return _tool(WormBaseTool, "gene_interactions")

    def test_parse_and_classify(self):
        """Covers parse and classify."""
        payload = {
            "fields": {
                "interactions": {
                    "data": {
                        "edges": [
                            {
                                "effector": {"label": "die-1", "id": "WBGene00000995"},
                                "affected": {"label": "unc-86", "id": "WBGene00006818"},
                                "type": "physical:protein-DNA",
                                "citations": [{"label": "Some 2004"}],
                            },
                            {
                                "effector": {"label": "unc-86", "id": "WBGene00006818"},
                                "affected": {"label": "ttx-3", "id": "WBGene00006654"},
                                "type": "gi-module-three:diverging",
                                "citations": [{"label": "Baum 1999"}],
                            },
                        ]
                    }
                }
            }
        }
        with patch(
            "tooluniverse.wormbase_tool.requests.get", return_value=_resp(payload)
        ):
            out = self._make().run({"gene_id": "WBGene00006818"})
        assert out["status"] == "success"
        assert out["data"]["physical_count"] == 1
        assert out["data"]["genetic_count"] == 1
        gen = out["data"]["genetic_interactions"][0]
        assert gen["interactor_2_id"] == "WBGene00006654"

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.wormbase_tool.requests.get", side_effect=Exception("x")
        ):
            out = self._make().run({"gene_id": "WBGene00006818"})
        assert out["status"] == "error"


class TestWormBaseHumanDiseases:
    def _make(self):
        return _tool(WormBaseTool, "gene_human_diseases")

    def test_parse_success(self):
        """Covers parse success."""
        payload = {
            "human_diseases": {
                "data": {
                    "gene": ["602460"],
                    "potential_model": [
                        {
                            "id": "DOID:0110546",
                            "label": "autosomal dominant nonsyndromic deafness 15",
                            "ev": {
                                "Inferred_automatically": [
                                    "Inferred by orthology (HGNC:9220)"
                                ]
                            },
                        }
                    ],
                }
            }
        }
        with patch(
            "tooluniverse.wormbase_tool.requests.get", return_value=_resp(payload)
        ):
            out = self._make().run({"gene_id": "WBGene00006818"})
        assert out["status"] == "success"
        assert out["data"]["disease_count"] == 1
        d = out["data"]["diseases"][0]
        assert d["disease_id"] == "DOID:0110546"
        assert d["evidence"]

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.wormbase_tool.requests.get", side_effect=Exception("x")
        ):
            out = self._make().run({"gene_id": "WBGene00006818"})
        assert out["status"] == "error"


# --------------------------------------------------------------------------
# RGD
# --------------------------------------------------------------------------
class TestRGDQtls:
    def _make(self):
        return _tool(RGDTool, "get_qtls_in_region")

    def test_parse_success(self):
        """Covers parse success."""
        payload = [
            {
                "rgdId": 7387235,
                "symbol": "Uae41",
                "name": "Urinary albumin excretion QTL 41",
                "chromosome": "10",
                "lod": 5.26,
                "pvalue": 0.1874,
                "inheritanceType": "additive",
            }
        ]
        tool = self._make()
        with patch.object(tool.session, "get", return_value=_resp(payload)):
            out = tool.run(
                {"chromosome": "10", "start": 1, "stop": 50000000, "map_key": 360}
            )
        assert out["status"] == "success"
        q = out["data"][0]
        assert q["symbol"] == "Uae41" and q["rgd_id"] == 7387235
        assert q["lod"] == 5.26
        assert out["metadata"]["assembly"].startswith("rat")

    def test_missing_params(self):
        """Covers missing params."""
        out = self._make().run({"chromosome": "10"})
        assert out["status"] == "error"

    def test_error_path(self):
        """Covers error path."""
        tool = self._make()
        with patch.object(tool.session, "get", side_effect=Exception("x")):
            out = tool.run(
                {"chromosome": "10", "start": 1, "stop": 50000000, "map_key": 360}
            )
        assert out["status"] == "error"


class TestRGDResolve:
    def _make(self):
        return _tool(RGDTool, "resolve_symbol_or_region")

    def test_symbol_mode(self):
        """Covers symbol mode."""
        payload = {
            "key": 1887,
            "rgdId": 3889,
            "symbol": "Tp53",
            "name": "tumor protein p53",
            "type": "protein-coding",
            "speciesTypeKey": 3,
        }
        tool = self._make()
        with patch.object(tool.session, "get", return_value=_resp(payload)):
            out = tool.run({"symbol": "Tp53"})
        assert out["status"] == "success"
        assert out["data"]["key"] == 1887
        assert out["data"]["symbol"] == "Tp53"
        assert out["metadata"]["mode"] == "symbol"

    def test_region_mode(self):
        """Covers region mode."""
        payload = [
            {
                "start": 27845,
                "stop": 27921,
                "chromosome": "10",
                "strand": "-",
                "gene": {
                    "rgdId": 2325341,
                    "symbol": "Mir484",
                    "name": "microRNA 484",
                    "type": "ncrna",
                },
            }
        ]
        tool = self._make()
        with patch.object(tool.session, "get", return_value=_resp(payload)):
            out = tool.run(
                {"chromosome": "10", "start": 1, "stop": 5000000, "map_key": 360}
            )
        assert out["status"] == "success"
        assert out["data"][0]["rgd_id"] == 2325341
        assert out["metadata"]["mode"] == "region"

    def test_no_input(self):
        """Covers no input."""
        assert self._make().run({})["status"] == "error"

    def test_error_path(self):
        """Covers error path."""
        tool = self._make()
        with patch.object(tool.session, "get", side_effect=Exception("x")):
            out = tool.run({"symbol": "Tp53"})
        assert out["status"] == "error"


# --------------------------------------------------------------------------
# Alliance
# --------------------------------------------------------------------------
class TestAllianceOrthologs:
    def _make(self):
        return _tool(AllianceGenomeTool, "gene_orthologs_paralogs")

    def test_parse_success(self):
        """Covers parse success."""
        orth = {
            "total": 19,
            "results": [
                {
                    "stringencyFilter": "stringent",
                    "geneAnnotationsMap": {
                        "FB:FBgn0019650": {
                            "hasDiseaseAnnotations": False,
                            "hasExpressionAnnotations": True,
                        }
                    },
                    "geneToGeneOrthologyGenerated": {
                        "objectGene": {
                            "primaryExternalId": "FB:FBgn0019650",
                            "geneSymbol": {"displayText": "toy"},
                            "taxon": {"name": "Drosophila melanogaster"},
                        },
                        "predictionMethodsMatched": [{"name": "OrthoFinder"}],
                    },
                }
            ],
        }
        para = {
            "total": 42,
            "results": [
                {
                    "geneToGeneParalogy": {
                        "objectGene": {
                            "primaryExternalId": "MGI:97491",
                            "geneSymbol": {"displayText": "Pax7"},
                            "taxon": {"name": "Mus musculus"},
                        },
                        "predictionMethodsMatched": [{"name": "PANTHER"}],
                    }
                }
            ],
        }
        responses = [_resp(orth), _resp(para)]
        with patch(
            "tooluniverse.alliance_genome_tool.requests.get",
            side_effect=responses,
        ):
            out = self._make().run({"gene_id": "MGI:97490"})
        assert out["status"] == "success"
        assert out["data"]["ortholog_count"] == 19
        assert out["data"]["orthologs"][0]["ortholog_symbol"] == "toy"
        assert out["data"]["paralog_count"] == 42
        assert out["data"]["paralogs"][0]["paralog_symbol"] == "Pax7"

    def test_missing_id(self):
        """Covers missing id."""
        assert self._make().run({})["status"] == "error"

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.alliance_genome_tool.requests.get",
            side_effect=Exception("x"),
        ):
            out = self._make().run({"gene_id": "MGI:97490"})
        assert out["status"] == "error"


class TestAllianceMolecularInteractions:
    def _make(self):
        return _tool(AllianceGenomeTool, "gene_molecular_interactions")

    def test_parse_success(self):
        """Covers parse success."""
        payload = {
            "total": 29,
            "results": [
                {
                    "geneMolecularInteraction": {
                        "geneAssociationSubject": {
                            "primaryExternalId": "MGI:97490",
                            "geneSymbol": {"displayText": "Pax6"},
                        },
                        "geneGeneAssociationObject": {
                            "primaryExternalId": "MGI:1913208",
                            "geneSymbol": {"displayText": "Carm1"},
                            "taxon": {"name": "Mus musculus"},
                        },
                        "interactionType": {"name": "direct interaction"},
                        "evidence": [{"pubModID": "MGI:6822438", "curie": "AGRKB:1"}],
                    }
                }
            ],
        }
        with patch(
            "tooluniverse.alliance_genome_tool.requests.get",
            return_value=_resp(payload),
        ):
            out = self._make().run({"gene_id": "MGI:97490"})
        assert out["status"] == "success"
        row = out["data"][0]
        assert row["interactor_symbol"] == "Carm1"
        assert "MGI:6822438" in row["references"]

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.alliance_genome_tool.requests.get",
            side_effect=Exception("x"),
        ):
            out = self._make().run({"gene_id": "MGI:97490"})
        assert out["status"] == "error"


class TestAllianceAllelesAndModels:
    def _make(self):
        return _tool(AllianceGenomeTool, "gene_alleles_and_models")

    def test_parse_success(self):
        """Covers parse success."""
        alleles = {
            "total": 675,
            "results": [
                {
                    "allele": {"curie": "rs231853465"},
                    "symbol": "NC_000068.8:g.105516528T>C",
                    "category": "variant_summary",
                    "alterationType": "variant",
                    "hasDisease": False,
                    "hasPhenotype": False,
                    "variantList": [
                        {
                            "curatedVariantGenomicLocations": [
                                {"hgvs": "NC_000068.8:g.105516528T>C"}
                            ]
                        }
                    ],
                }
            ],
        }
        models = {
            "total": 183,
            "results": [
                {
                    "model": {
                        "primaryExternalId": "MGI:2680573",
                        "agmFullName": {"displayText": "Pax6<1Jrt>/Pax6<+>"},
                        "subtype": {"name": "genotype"},
                        "dataProvider": {"abbreviation": "MGI"},
                    }
                }
            ],
        }
        with patch(
            "tooluniverse.alliance_genome_tool.requests.get",
            side_effect=[_resp(alleles), _resp(models)],
        ):
            out = self._make().run({"gene_id": "MGI:97490"})
        assert out["status"] == "success"
        assert out["data"]["allele_count"] == 675
        assert out["data"]["alleles"][0]["allele_id"] == "rs231853465"
        assert out["data"]["models"][0]["model_id"] == "MGI:2680573"

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.alliance_genome_tool.requests.get",
            side_effect=Exception("x"),
        ):
            out = self._make().run({"gene_id": "MGI:97490"})
        assert out["status"] == "error"


# --------------------------------------------------------------------------
# PomBase
# --------------------------------------------------------------------------
_POMBASE_GENE = {
    "uniquename": "SPBC11B10.09",
    "name": "cdc2",
    "ortholog_annotations": [
        {"ortholog_uniquename": "HGNC:1722", "ortholog_taxonid": 9606},
        {"ortholog_uniquename": "YBR160W", "ortholog_taxonid": 4932},
    ],
    "physical_interactions": [
        {
            "gene_uniquename": "SPAC1006.03c",
            "interactor_uniquename": "SPBC11B10.09",
            "evidence": "Affinity Capture-MS",
            "reference_uniquename": "PMID:24713849",
            "throughput": "high",
            "source_database": "BIOGRID",
        }
    ],
    "genetic_interactions": [
        [
            {
                "gene_a_uniquename": "SPBC11B10.09",
                "gene_b_uniquename": "SPBC336.12c",
                "interaction_type": "Phenotypic Enhancement",
            },
            [
                {
                    "reference_uniquename": "PMID:11513869",
                    "throughput": "low",
                    "source_database": "BIOGRID",
                }
            ],
        ]
    ],
    "cv_annotations": {
        "biological_process": [{"term": "GO:0000082", "is_not": False}],
        "molecular_function": [{"term": "GO:0004693", "is_not": False}],
        "cellular_component": [{"term": "GO:0005634", "is_not": False}],
    },
    "terms_by_termid": {
        "GO:0000082": {"name": "G1/S transition of mitotic cell cycle"},
        "GO:0004693": {"name": "cyclin-dependent protein kinase activity"},
        "GO:0005634": {"name": "nucleus"},
    },
    "genes_by_uniquename": {
        "SPAC1006.03c": {"name": "red1"},
        "SPBC336.12c": {"name": "cdc13"},
    },
}


class TestPomBaseOrthologs:
    def _make(self):
        return _tool(PomBaseTool, "gene_orthologs")

    def test_parse_success(self):
        """Covers parse success."""
        with patch(
            "tooluniverse.pombase_tool.requests.get", return_value=_resp(_POMBASE_GENE)
        ):
            out = self._make().run({"gene_id": "SPBC11B10.09"})
        assert out["status"] == "success"
        ids = {o["ortholog_id"] for o in out["data"]["orthologs"]}
        assert "HGNC:1722" in ids and "YBR160W" in ids
        human = [
            o for o in out["data"]["orthologs"] if o["ortholog_id"] == "HGNC:1722"
        ][0]
        assert human["ortholog_species"] == "Homo sapiens"

    def test_missing_id(self):
        """Covers missing id."""
        assert self._make().run({})["status"] == "error"

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.pombase_tool.requests.get", side_effect=Exception("x")
        ):
            out = self._make().run({"gene_id": "SPBC11B10.09"})
        assert out["status"] == "error"


class TestPomBaseInteractions:
    def _make(self):
        return _tool(PomBaseTool, "gene_interactions")

    def test_parse_success(self):
        """Covers parse success."""
        with patch(
            "tooluniverse.pombase_tool.requests.get", return_value=_resp(_POMBASE_GENE)
        ):
            out = self._make().run({"gene_id": "SPBC11B10.09"})
        assert out["status"] == "success"
        phys = out["data"]["physical_interactions"][0]
        assert phys["interactor_id"] == "SPAC1006.03c"
        assert phys["interactor_name"] == "red1"
        assert phys["evidence"] == "Affinity Capture-MS"
        gen = out["data"]["genetic_interactions"][0]
        assert gen["interactor_id"] == "SPBC336.12c"
        assert gen["interaction_type"] == "Phenotypic Enhancement"

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.pombase_tool.requests.get", side_effect=Exception("x")
        ):
            out = self._make().run({"gene_id": "SPBC11B10.09"})
        assert out["status"] == "error"


class TestPomBaseGO:
    def _make(self):
        return _tool(PomBaseTool, "gene_go_annotations")

    def test_parse_success(self):
        """Covers parse success."""
        with patch(
            "tooluniverse.pombase_tool.requests.get", return_value=_resp(_POMBASE_GENE)
        ):
            out = self._make().run({"gene_id": "SPBC11B10.09"})
        assert out["status"] == "success"
        assert out["data"]["aspect_counts"]["biological_process"] == 1
        bp = [t for t in out["data"]["go_terms"] if t["aspect_code"] == "BP"][0]
        assert bp["term_id"] == "GO:0000082"
        assert bp["term_name"] == "G1/S transition of mitotic cell cycle"

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.pombase_tool.requests.get", side_effect=Exception("x")
        ):
            out = self._make().run({"gene_id": "SPBC11B10.09"})
        assert out["status"] == "error"


# --------------------------------------------------------------------------
# InterMine PathQuery (BaseRESTTool, config-only)
# --------------------------------------------------------------------------
class TestInterMinePathQuery:
    def _make(self):
        return BaseRESTTool(
            {
                "name": "InterMine_run_pathquery",
                "type": "BaseRESTTool",
                "fields": {
                    "endpoint": "https://www.humanmine.org/humanmine/service/query/results",
                    "params": {"format": "json"},
                },
                "parameter": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            }
        )

    def test_parse_success(self):
        """Covers parse success."""
        payload = {
            "views": ["Gene.symbol", "Gene.pathways.name"],
            "results": [["PAX6", "Activation of HOX genes during differentiation"]],
            "wasSuccessful": True,
        }
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_resp(payload),
        ):
            out = self._make().run({"query": "<query .../>"})
        assert out["status"] == "success"
        assert out["data"]["results"][0][0] == "PAX6"
        assert out["data"]["wasSuccessful"] is True

    def test_error_path(self):
        """Covers error path."""
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_resp({"error": "bad query"}, status_code=400),
        ):
            out = self._make().run({"query": "<bad/>"})
        assert out["status"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
