"""Regression tests for silent failures documented in SilentFailures report."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.bioimage_archive_tool import BioImageArchiveTool
from tooluniverse.bioregistry_tool import BioregistryTool
from tooluniverse.biosamples_tool import BioSamplesTool
from tooluniverse.bvbrc_tool import BVBRCTool
from tooluniverse.cath_tool import CATHTool
from tooluniverse.cellmarker_tool import CellMarkerTool
from tooluniverse.cellxgene_discovery_tool import CellxGeneDiscoveryTool
from tooluniverse.chebi_tool import ChEBITool
from tooluniverse.clinvar_tool import ClinVarSearchVariants
from tooluniverse.clingen_tool import ClinGenTool
from tooluniverse.conoserver_tool import ConoServerSearchConopeptidesTool
from tooluniverse.dfam_tool import DfamTool
from tooluniverse.disprot_tool import DisProtTool
from tooluniverse.ensembl_tool import EnsemblRESTTool
from tooluniverse.ena_portal_tool import ENAPortalTool
from tooluniverse.ensembl_ld_tool import EnsemblLDTool
from tooluniverse.ensembl_info_tool import EnsemblInfoTool
from tooluniverse.ensembl_overlap_tool import EnsemblOverlapTool
from tooluniverse.ensembl_phenotype_tool import EnsemblPhenotypeTool
from tooluniverse.ensembl_regulation_tool import EnsemblRegulationTool
from tooluniverse.europepmc_annotations_tool import EuroPMCAnnotationsTool
from tooluniverse.eol_tool import EOLTool
from tooluniverse.ebi_proteins_epitope_tool import EBIProteinsEpitopeTool
from tooluniverse.ebi_proteins_features_tool import EBIProteinsFeaturesTool
from tooluniverse.interpro_tool import InterProRESTTool
from tooluniverse.kegg_ext_tool import KEGGExtTool
from tooluniverse.gmrepo_tool import GmrepoTool
from tooluniverse.gdc_tool import GDCMutationFreqByProjectTool, GDCSurvivalTool
from tooluniverse.glygen_tool import GlyGenTool
from tooluniverse.finngen_tool import FinnGenTool
from tooluniverse.hpo_tool import HPOTool
from tooluniverse.mavedb_tool import MaveDBTool
from tooluniverse.mygene_tool import MyChemTool, MyGeneTool, MyVariantTool
from tooluniverse.ncbi_variation_tool import NCBIVariationTool
from tooluniverse.mgnify_tool import MGnifyAnalysesTool, MGnifyStudiesTool
from tooluniverse.pride_tool import PRIDERESTTool
from tooluniverse.protvar_tool import ProtVarFunctionTool, ProtVarMapTool
from tooluniverse.rnacentral_tool import RNAcentralSearchTool
from tooluniverse.rgd_tool import RGDTool
from tooluniverse.reactome_content_tool import ReactomeContentTool
from tooluniverse.reactome_interactors_tool import ReactomeInteractorsTool
from tooluniverse.sgd_tool import SGDTool
from tooluniverse.oma_tool import OMATool
from tooluniverse.pheweb_phewas_tool import GenebassTool, PheWebPheWASTool
from tooluniverse.uniparc_tool import UniParcTool
from tooluniverse.uniprot_locations_tool import UniProtLocationsTool
from tooluniverse.uniprot_ref_tool import UniProtRefTool
from tooluniverse.uniprot_taxonomy_tool import UniProtTaxonomyTool
from tooluniverse.uniprot_tool import UniProtRESTTool
from tooluniverse.uniref_tool import UniRefTool


pytestmark = pytest.mark.unit


def _response(payload, headers=None, text=""):
    response = MagicMock()
    response.status_code = 200
    response.headers = headers or {}
    response.json.return_value = payload
    response.text = text
    response.raise_for_status.return_value = None
    return response


def test_bvbrc_search_exposes_real_total_and_next_offset():
    tool = BVBRCTool(
        {
            "name": "BVBRC_search_genomes",
            "fields": {"data_type": "genome", "action": "search"},
        }
    )
    response = _response(
        [{"genome_id": "1"}, {"genome_id": "2"}],
        {"Content-Range": "items 20-21/31489"},
    )
    with patch("tooluniverse.bvbrc_tool.requests.get", return_value=response) as get:
        result = tool.run(
            {
                "keyword": "Staphylococcus aureus",
                "limit": 2,
                "offset": 20,
                "genome_quality": "Good",
            }
        )

    requested_url = get.call_args.args[0]
    assert "limit(2,20)" in requested_url
    assert "eq(genome_quality,Good)" in requested_url
    assert result["metadata"]["total_results"] == 31489
    assert result["metadata"]["truncated"] is True
    assert result["metadata"]["next_offset"] == 22


def test_bvbrc_get_genome_does_not_select_a_lossy_field_subset():
    tool = BVBRCTool(
        {
            "name": "BVBRC_get_genome",
            "fields": {"data_type": "genome", "action": "get"},
        }
    )
    full_record = {"genome_id": "83332.12", "checkm_completeness": 99.9}
    with patch(
        "tooluniverse.bvbrc_tool.requests.get",
        return_value=_response([full_record]),
    ) as get:
        result = tool.run({"genome_id": "83332.12"})

    assert "select(" not in get.call_args.args[0]
    assert result["data"]["checkm_completeness"] == 99.9


def test_bvbrc_get_genome_does_not_fan_out_to_related_collections_by_default():
    """The shipped default must stay one request.

    Fixing the dropped-fields silent failure does not require fetching AMR and
    specialty genes on every call; that would triple latency and failure
    surface.  Related data stays reachable through the documented dedicated
    tools and through include_related=true.
    """
    config = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "src/tooluniverse/data/bvbrc_tools.json"
        ).read_text()
    )
    shipped = next(t for t in config if t["name"] == "BVBRC_get_genome")
    assert shipped["parameter"]["properties"]["include_related"]["default"] is False

    tool = BVBRCTool(shipped)
    with patch(
        "tooluniverse.bvbrc_tool.requests.get",
        return_value=_response([{"genome_id": "83332.12"}]),
    ) as get:
        result = tool.run({"genome_id": "83332.12"})

    assert get.call_count == 1
    assert "related_records" not in result["data"]
    assert "related_data" in result["metadata"]


def test_bvbrc_get_genome_can_include_paginated_related_collections():
    tool = BVBRCTool(
        {
            "name": "BVBRC_get_genome",
            "parameter": {"properties": {"include_related": {"default": True}}},
            "fields": {"data_type": "genome", "action": "get"},
        }
    )
    responses = [
        _response([{"genome_id": "83332.12"}]),
        _response(
            [{"antibiotic": "isoniazid"}],
            {"Content-Range": "items 0-0/12"},
        ),
        _response(
            [{"gene": "katG"}],
            {"Content-Range": "items 0-0/37"},
        ),
    ]
    with patch("tooluniverse.bvbrc_tool.requests.get", side_effect=responses):
        result = tool.run(
            {"genome_id": "83332.12", "related_limit": 1, "related_offset": 0}
        )

    assert result["data"]["related_records"]["amr"] == [{"antibiotic": "isoniazid"}]
    assert result["data"]["related_records"]["specialty_genes"] == [{"gene": "katG"}]
    paging = result["metadata"]["related_pagination"]
    assert paging["amr"]["total_results"] == 12
    assert paging["specialty_genes"]["total_results"] == 37


@pytest.mark.parametrize(
    ("data_type", "action", "arguments"),
    [
        ("genome_feature", "search", {"gene": "mecA"}),
        ("epitope", "search", {"taxon_id": "2697049"}),
        ("surveillance", "search", {"subtype": "H5N1"}),
        ("protein_structure", "search", {"taxon_id": "83332"}),
        ("taxonomy", "search", {"keyword": "Staphylococcus"}),
        ("pathway", "search", {"genome_id": "83332.12"}),
        ("subsystem", "search", {"genome_id": "83332.12"}),
    ],
)
def test_all_bvbrc_collection_searches_expose_content_range_pagination(
    data_type, action, arguments
):
    tool = BVBRCTool(
        {
            "name": f"test_{data_type}",
            "fields": {"data_type": data_type, "action": action},
        }
    )
    response = _response([{"record_id": "page-2"}], {"Content-Range": "items 4-4/99"})
    with patch("tooluniverse.bvbrc_tool.requests.get", return_value=response) as get:
        result = tool.run({**arguments, "limit": 1, "offset": 4})

    assert "limit(1,4)" in get.call_args.args[0]
    assert result["metadata"]["total_results"] == 99
    assert result["metadata"]["returned"] == 1
    assert result["metadata"]["next_offset"] == 5


def test_disprot_uses_free_text_and_paginates_regions_without_losing_xrefs():
    search_tool = DisProtTool(
        {"name": "DisProt_search", "fields": {"endpoint": "search"}}
    )
    search_payload = {
        "size": 7,
        "data": [{"disprot_id": "DP00086", "genes": []}],
    }
    with patch(
        "tooluniverse.disprot_tool.requests.get",
        return_value=_response(search_payload),
    ) as get:
        search = search_tool.run({"query": "TP53", "page_size": 1, "page": 2})

    params = get.call_args.kwargs["params"]
    assert params["free_text"] == "TP53"
    assert "q" not in params
    assert params["page"] == 2
    assert search["metadata"]["total_results"] == 7

    entry_tool = DisProtTool(
        {"name": "DisProt_get_entry", "fields": {"endpoint": "get_entry"}}
    )
    regions = [
        {
            "region_id": f"r{i}",
            "cross_refs": [{"db": "PDB", "id": str(j)} for j in range(8)],
        }
        for i in range(4)
    ]
    payload = {"data": [{"regions_counter": 4, "regions": regions, "genes": []}]}
    with patch(
        "tooluniverse.disprot_tool.requests.get", return_value=_response(payload)
    ):
        entry = entry_tool.run(
            {"accession": "P04637", "region_offset": 1, "region_limit": 2}
        )

    assert [r["region_id"] for r in entry["data"]["regions"]] == ["r1", "r2"]
    assert len(entry["data"]["regions"][0]["cross_refs"]) == 8
    assert entry["metadata"]["next_region_offset"] == 3


def test_interpro_preserves_count_and_cursor_navigation():
    tool = InterProRESTTool(
        {
            "name": "InterPro_search_domains",
            "parameter": {"properties": {"page_size": {"default": 2}, "cursor": {}}},
            "fields": {
                "endpoint": "https://www.ebi.ac.uk/interpro/api/entry/interpro?search={query}&page_size={page_size}",
                "extract_path": "results",
            },
        }
    )
    payload = {
        "count": 1133,
        "next": "https://www.ebi.ac.uk/interpro/api/entry/interpro?cursor=NEXT123",
        "previous": None,
        "results": [{"metadata": {"accession": "IPR1"}}],
    }
    tool.session.get = MagicMock(return_value=_response(payload))
    result = tool.run({"query": "kinase", "cursor": "CURRENT"})

    assert "cursor=CURRENT" in tool.session.get.call_args.args[0]
    assert result["count"] == 1
    assert result["metadata"]["total_results"] == 1133
    assert result["metadata"]["next_cursor"] == "NEXT123"


def test_ensembl_variant_pagination_is_local_and_explicit():
    tool = EnsemblRESTTool(
        {
            "name": "ensembl_get_variants",
            "endpoint": "/overlap/region/{species}/{region}",
            "parameter": {
                "properties": {"feature": {"default": "variation"}},
                "required": ["region"],
            },
        }
    )
    upstream = [{"id": f"rs{i}"} for i in range(10)]
    with patch(
        "tooluniverse.ensembl_tool.request_with_retry",
        return_value=_response(upstream),
    ) as request:
        result = tool.run(
            {"species": "human", "region": "17:1-100", "offset": 3, "limit": 4}
        )

    assert "offset" not in request.call_args.kwargs["params"]
    assert "limit" not in request.call_args.kwargs["params"]
    assert [x["id"] for x in result["data"]] == ["rs3", "rs4", "rs5", "rs6"]
    assert result["metadata"]["total_results"] == 10
    assert result["metadata"]["next_offset"] == 7


def test_protvar_function_preserves_structural_and_prediction_fields():
    payload = {
        "accession": "P04637",
        "position": 175,
        "gene": [{"name": {"value": "TP53"}}],
        "alternativeNames": "Antigen NY-CO-13; Tumor suppressor p53",
        "features": [],
        "comments": [],
        "pockets": [{"pocketId": 2}],
        "interactions": [{"b": "P12273"}],
        "conservScore": {"score": 0.945},
        "esmScore": {"score": -10.124},
        "eveScore": {"score": 0.502},
        "popEveScore": {"popeve": -3.658},
        "foldxs": [{"foldxDdg": 11.4}],
        "m3dPred": None,
    }
    tool = ProtVarFunctionTool({"name": "ProtVar_get_function"})
    with patch("tooluniverse.protvar_tool._get_json", return_value=payload):
        result = tool.run({"accession": "P04637", "position": 175, "variant_aa": "H"})

    data = result["data"]
    assert data["gene_names"] == payload["gene"]
    assert data["alternative_names"] == [
        "Antigen NY-CO-13",
        "Tumor suppressor p53",
    ]
    assert data["pockets"] == payload["pockets"]
    assert data["interactions"] == payload["interactions"]
    assert data["conservation_score"] == payload["conservScore"]
    assert data["foldx_predictions"] == payload["foldxs"]
    assert result["metadata"]["variant_specific_predictions_requested"] is True
    assert result["metadata"]["prediction_fields_present"]["foldx"] is True


def test_protvar_function_warns_when_variant_specific_scores_were_not_requested():
    payload = {
        "accession": "P04637",
        "position": 175,
        "features": [],
        "comments": [],
        "pockets": [],
        "interactions": [],
        "conservScore": {"score": 0.945},
    }
    tool = ProtVarFunctionTool({"name": "ProtVar_get_function"})
    with patch("tooluniverse.protvar_tool._get_json", return_value=payload):
        result = tool.run({"accession": "P04637", "position": 175})

    assert result["data"]["variant_aa"] is None
    assert result["metadata"]["variant_specific_predictions_requested"] is False
    assert "variant_aa was not supplied" in result["metadata"]["warning"]


def test_protvar_map_labels_model_classification_and_exposes_criteria():
    payload = {
        "content": {
            "inputs": [
                {
                    "messages": [],
                    "derivedGenomicVariants": [
                        {
                            "chromosome": "17",
                            "position": 7675088,
                            "refBase": "C",
                            "altBase": "T",
                            "genes": [
                                {
                                    "geneName": "TP53",
                                    "ensg": "ENSG00000141510.19",
                                    "caddScore": 25.9,
                                    "isoforms": [
                                        {
                                            "accession": "P04637",
                                            "canonical": True,
                                            "amScore": {
                                                "amPathogenicity": 0.9857,
                                                "amClass": "PATHOGENIC",
                                            },
                                            "popEveScore": {
                                                "eve": 5.982,
                                                "esm1v": -7.744,
                                                "popeve": -3.658,
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }
    tool = ProtVarMapTool({"name": "ProtVar_map_variant"})
    with patch("tooluniverse.protvar_tool._get_json", return_value=payload):
        result = tool.run({"variant": "P04637 R175H", "assembly": "GRCh37"})

    prediction = result["data"]["isoform_mappings"][0]["alphamissense"]
    assert prediction["class"] == "PATHOGENIC"
    assert prediction["classification_scope"] == "model_prediction"
    assert prediction["is_clinical_classification"] is False
    assert prediction["class_thresholds"]["likely_pathogenic"] == "score > 0.564"
    assert result["data"]["assembly"] == "GRCh37"
    assert (
        "not retrieved clinical classifications"
        in result["data"]["prediction_context"]["interpretation"]
    )


@pytest.mark.parametrize(
    "search_type",
    ["search", "uniref_search", "uniparc_search"],
)
def test_uniprot_searches_accept_and_return_official_cursors(search_type):
    tool = UniProtRESTTool(
        {
            "name": f"test_{search_type}",
            "fields": {
                "search_type": search_type,
                "endpoint": "https://rest.uniprot.org/search",
            },
            "parameter": {"properties": {}},
        }
    )
    response = _response(
        {"results": [{"primaryAccession": "P1"}]},
        {
            "x-total-results": "42",
            "Link": '<https://rest.uniprot.org/search?cursor=NEXT123&size=1>; rel="next"',
        },
    )
    with patch("tooluniverse.uniprot_tool.requests.get", return_value=response) as get:
        result = tool.run({"query": "kinase", "limit": 1, "cursor": "CURRENT"})

    assert get.call_args.kwargs["params"]["cursor"] == "CURRENT"
    assert result["data"]["total_results"] == 42
    assert result["data"]["next_cursor"] == "NEXT123"
    assert result["data"]["truncated"] is True


def test_legacy_uniprot_id_mapping_fetches_all_pages_then_paginates_locally():
    tool = UniProtRESTTool(
        {
            "name": "UniProt_id_mapping",
            "fields": {
                "mapping_type": "async",
                "endpoint": "https://rest.uniprot.org/idmapping",
            },
        }
    )
    post_response = _response({"jobId": "job123"})
    status_response = _response({"results": [{"from": "P00533", "to": "PREVIEW"}]})
    first_page = _response(
        {"results": [{"from": "P00533", "to": f"PDB{i}"} for i in range(500)]},
        {
            "Link": '<https://rest.uniprot.org/idmapping/results/job123?cursor=NEXT>; rel="next"'
        },
    )
    second_page = _response(
        {"results": [{"from": "P00533", "to": f"PDB{i}"} for i in range(500, 600)]}
    )

    def fake_get(url, **kwargs):
        if "/status/" in url:
            return status_response
        if "cursor=NEXT" in url:
            return second_page
        return first_page

    with (
        patch("tooluniverse.uniprot_tool.requests.post", return_value=post_response),
        patch("tooluniverse.uniprot_tool.requests.get", side_effect=fake_get),
    ):
        result = tool.run(
            {
                "ids": ["P00533"],
                "from_db": "UniProtKB_AC-ID",
                "to_db": "PDB",
                "result_offset": 500,
                "result_limit": 100,
            }
        )

    assert result["data"]["mapped_count"] == 600
    assert result["data"]["returned"] == 100
    assert result["data"]["results"][0]["to"] == "PDB500"
    assert result["data"]["truncated"] is False


def test_kegg_find_compound_reports_true_total_after_local_pagination():
    tool = KEGGExtTool(
        {"name": "KEGG_find_compound", "fields": {"endpoint": "find_compound"}}
    )
    text = "\n".join(f"cpd:C0000{i}\tC6H12O6" for i in range(1, 6))
    with patch(
        "tooluniverse.kegg_ext_tool.requests.get",
        return_value=_response({}, text=text),
    ):
        result = tool.run({"formula": "C6H12O6", "max_results": 2, "offset": 2})

    assert result["data"]["total_results"] == 5
    assert result["data"]["count"] == 2
    assert result["data"]["next_offset"] == 4
    assert [item["compound_id"] for item in result["data"]["compounds"]] == [
        "C00003",
        "C00004",
    ]


def test_uniprot_entry_adds_computational_publications_with_cursor():
    tool = UniProtRESTTool(
        {
            "name": "UniProt_get_entry_by_accession",
            "parameter": {
                "properties": {
                    "compact": {"default": True},
                    "include_publications": {"default": True},
                }
            },
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/{accession}.json"
            },
        }
    )
    entry = {"primaryAccession": "P05067", "references": []}
    mapped = {"results": [{"citation": {"id": "19754881"}}]}
    publication_headers = {
        "x-total-results": "2943",
        "Link": '<https://rest.uniprot.org/uniprotkb/P05067/publications?cursor=NEXT&size=1>; rel="next"',
    }
    with patch(
        "tooluniverse.uniprot_tool.requests.get",
        side_effect=[_response(entry), _response(mapped, publication_headers)],
    ) as get:
        result = tool.run(
            {
                "accession": "P05067",
                "publication_limit": 1,
                "publication_source": "computational",
            }
        )

    publication_call = get.call_args_list[1]
    assert publication_call.args[0].endswith("/P05067/publications")
    assert publication_call.kwargs["params"]["facetFilter"] == '(types:"1")'
    assert result["data"]["additional_publications"] == mapped["results"]
    assert result["metadata"]["total_publications"] == 2943
    assert result["metadata"]["next_publication_cursor"] == "NEXT"


def test_uniprot_compact_entry_pages_complete_features_comments_and_references():
    tool = UniProtRESTTool(
        {
            "name": "UniProt_get_entry_by_accession",
            "parameter": {"properties": {"compact": {"default": True}}},
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/{accession}.json"
            },
        }
    )
    entry = {
        "primaryAccession": "P04637",
        "comments": [
            {"commentType": "FUNCTION", "texts": [{"value": f"text-{index}"}]}
            for index in range(4)
        ]
        + [{"commentType": "INTERACTION", "interactions": [{"accession": "Q1"}]}],
        "features": [
            {
                "type": "Variant",
                "description": f"feature-{index}",
                "location": {"start": {"value": index}},
                "evidences": [{"evidenceCode": "ECO:0000269"}],
            }
            for index in range(5)
        ],
        "references": [
            {"citation": {"id": f"PMID{index}"}, "evidences": [{"code": index}]}
            for index in range(5)
        ],
    }
    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_response(entry)
    ):
        result = tool.run(
            {
                "accession": "P04637",
                "comment_limit": 2,
                "comment_offset": 3,
                "feature_limit": 2,
                "feature_offset": 2,
                "reference_limit": 2,
                "reference_offset": 1,
            }
        )

    assert result["data"]["comments"][1]["details"]["interactions"][0][
        "accession"
    ] == "Q1"
    assert result["data"]["features"][0]["description"] == "feature-2"
    assert result["data"]["features"][0]["evidences"][0]["evidenceCode"] == (
        "ECO:0000269"
    )
    assert result["data"]["references"][0]["citation"]["id"] == "PMID1"
    assert result["metadata"]["comments_total"] == 5
    assert result["metadata"]["features_next_offset"] == 4
    assert result["metadata"]["references_next_offset"] == 3


def test_uniprot_ptm_processing_includes_all_ptm_and_chain_feature_types():
    included_types = [
        "Modified residue",
        "Glycosylation",
        "Lipidation",
        "Disulfide bond",
        "Cross-link",
        "Signal",
        "Transit peptide",
        "Propeptide",
        "Peptide",
        "Chain",
        "Initiator methionine",
    ]
    entry = {
        "features": [
            *[{"type": feature_type} for feature_type in included_types],
            {"type": "Domain"},
        ]
    }
    tool = UniProtRESTTool(
        {
            "name": "UniProt_get_ptm_processing_by_accession",
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/{accession}.json",
                "extract_path": "ptm_and_processing_features",
            },
        }
    )
    with patch("tooluniverse.uniprot_tool.requests.get", return_value=_response(entry)):
        result = tool.run({"accession": "P05067"})

    assert [feature["type"] for feature in result] == included_types


def test_uniprot_subcellular_locations_preserve_evidence_and_isoform_qualifiers():
    entry = {
        "comments": [
            {
                "commentType": "SUBCELLULAR LOCATION",
                "molecule": "Isoform 1",
                "subcellularLocations": [
                    {
                        "location": {
                            "value": "Cell membrane",
                            "id": "SL-0039",
                            "evidences": [
                                {
                                    "evidenceCode": "ECO:0000269",
                                    "source": "PubMed",
                                    "id": "12345",
                                }
                            ],
                        },
                        "topology": {"value": "Single-pass type I membrane protein"},
                    }
                ],
                "note": {
                    "texts": [
                        {
                            "value": "The isoform-specific note must not be lost.",
                            "evidences": [{"evidenceCode": "ECO:0000305"}],
                        }
                    ]
                },
            }
        ]
    }
    tool = UniProtRESTTool(
        {
            "name": "UniProt_get_subcellular_location_by_accession",
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/{accession}.json",
                "extract_path": "subcellular_location_annotations",
            },
        }
    )
    with patch("tooluniverse.uniprot_tool.requests.get", return_value=_response(entry)):
        result = tool.run({"accession": "P04637"})

    assert result == [
        {
            "location": "Cell membrane",
            "location_id": "SL-0039",
            "evidences": [
                {
                    "evidenceCode": "ECO:0000269",
                    "source": "PubMed",
                    "id": "12345",
                }
            ],
            "molecule": "Isoform 1",
            "topology": {"value": "Single-pass type I membrane protein"},
            "orientation": None,
            "note": {
                "texts": [
                    {
                        "value": "The isoform-specific note must not be lost.",
                        "evidences": [{"evidenceCode": "ECO:0000305"}],
                    }
                ]
            },
        }
    ]


def test_uniprot_function_annotations_preserve_evidence():
    entry = {
        "comments": [
            {
                "commentType": "FUNCTION",
                "texts": [
                    {
                        "value": "Tumor suppressor function.",
                        "evidences": [
                            {
                                "evidenceCode": "ECO:0000269",
                                "source": "PubMed",
                                "id": "11025664",
                            }
                        ],
                    }
                ],
            }
        ]
    }
    tool = UniProtRESTTool(
        {
            "name": "UniProt_get_function_by_accession",
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/{accession}.json",
                "extract_path": "function_annotations",
            },
        }
    )
    with patch("tooluniverse.uniprot_tool.requests.get", return_value=_response(entry)):
        result = tool.run({"accession": "P04637"})

    assert result == [
        {
            "value": "Tumor suppressor function.",
            "evidences": [
                {
                    "evidenceCode": "ECO:0000269",
                    "source": "PubMed",
                    "id": "11025664",
                }
            ],
        }
    ]


def test_uniprot_annotation_tools_still_offer_the_legacy_flat_value_list():
    """format='values' keeps pre-existing callers working after the fix.

    The structured default stops silently dropping evidence and qualifiers, but
    it changes the element type from str to dict.  Callers written against the
    old shape must retain a supported way to ask for it.
    """
    entry = {
        "comments": [
            {
                "commentType": "FUNCTION",
                "texts": [{"value": "Tumor suppressor function.", "evidences": []}],
            },
            {
                "commentType": "SUBCELLULAR LOCATION",
                "molecule": "Isoform 1",
                "subcellularLocations": [
                    {"location": {"value": "Cell membrane", "id": "SL-0039"}}
                ],
            },
        ]
    }
    for tool_name, extract_path, expected in (
        (
            "UniProt_get_function_by_accession",
            "function_annotations",
            ["Tumor suppressor function."],
        ),
        (
            "UniProt_get_subcellular_location_by_accession",
            "subcellular_location_annotations",
            ["Cell membrane"],
        ),
    ):
        tool = UniProtRESTTool(
            {
                "name": tool_name,
                "fields": {
                    "endpoint": "https://rest.uniprot.org/uniprotkb/{accession}.json",
                    "extract_path": extract_path,
                },
            }
        )
        with patch(
            "tooluniverse.uniprot_tool.requests.get", return_value=_response(entry)
        ):
            legacy = tool.run({"accession": "P04637", "format": "values"})
            structured = tool.run({"accession": "P04637"})

        assert legacy == expected
        assert all(isinstance(item, dict) for item in structured)


@pytest.mark.parametrize(
    ("tool", "request_path", "payload"),
    [
        (
            UniParcTool({"name": "UniParc_search", "fields": {"endpoint": "search"}}),
            "tooluniverse.uniparc_tool.requests.get",
            {"results": [{"uniParcId": "UPI1"}]},
        ),
        (
            UniRefTool(
                {
                    "name": "UniRef_search_clusters",
                    "fields": {"endpoint": "search_clusters"},
                }
            ),
            "tooluniverse.uniref_tool.requests.get",
            {"results": [{"id": "UniRef90_P1"}]},
        ),
        (
            UniProtTaxonomyTool(
                {
                    "name": "UniProtTaxonomy_search",
                    "fields": {"endpoint": "search"},
                }
            ),
            "tooluniverse.uniprot_taxonomy_tool.requests.get",
            {"results": [{"taxonId": 9606}]},
        ),
        (
            UniProtLocationsTool(
                {
                    "name": "UniProtLocations_search",
                    "fields": {"endpoint": "search_locations"},
                }
            ),
            "tooluniverse.uniprot_locations_tool.requests.get",
            {"results": [{"id": "SL-0191", "name": "Nucleus"}]},
        ),
        (
            UniProtRefTool(
                {
                    "name": "UniProtRef_search_diseases",
                    "fields": {"endpoint": "search_diseases"},
                }
            ),
            "tooluniverse.uniprot_ref_tool.requests.get",
            {"results": [{"id": "DI-1"}]},
        ),
        (
            UniProtRefTool(
                {
                    "name": "UniProtRef_search_keywords",
                    "fields": {"endpoint": "search_keywords"},
                }
            ),
            "tooluniverse.uniprot_ref_tool.requests.get",
            {"results": [{"keyword": {"id": "KW-1"}}]},
        ),
        (
            UniProtRefTool(
                {
                    "name": "UniProtRef_search_proteomes",
                    "fields": {"endpoint": "search_proteomes"},
                }
            ),
            "tooluniverse.uniprot_ref_tool.requests.get",
            {"results": [{"id": "UP0001"}]},
        ),
    ],
)
def test_independent_uniprot_searches_expose_official_cursor_and_total(
    tool, request_path, payload
):
    response = _response(
        payload,
        {
            "x-total-results": "1234",
            "Link": '<https://rest.uniprot.org/search?cursor=NEXT456&size=1>; rel="next"',
        },
    )
    with patch(request_path, return_value=response) as get:
        result = tool.run({"query": "kinase", "size": 1, "cursor": "CURRENT"})

    assert get.call_args.kwargs["params"]["cursor"] == "CURRENT"
    assert result["metadata"]["total_results"] == 1234
    assert result["metadata"]["returned"] == 1
    assert result["metadata"]["truncated"] is True
    assert result["metadata"]["next_cursor"] == "NEXT456"


def test_uniparc_entry_pages_active_cross_references_without_silent_cutoff():
    entry = {
        "uniParcId": "UPI000002ED67",
        "sequence": {"value": "MPEPTIDE", "length": 8},
        "uniParcCrossReferences": [
            {"database": "PDB", "id": f"PDB{i}", "active": True} for i in range(120)
        ],
        "sequenceFeatures": [
            {"database": "InterPro", "databaseId": f"IPR{i}"} for i in range(8)
        ],
    }
    tool = UniParcTool(
        {"name": "UniParc_get_entry", "fields": {"endpoint": "get_entry"}}
    )
    with patch("tooluniverse.uniparc_tool.requests.get", return_value=_response(entry)):
        result = tool.run(
            {
                "upi": "UPI000002ED67",
                "cross_reference_offset": 30,
                "cross_reference_limit": 30,
                "feature_offset": 2,
                "feature_limit": 3,
            }
        )

    assert result["metadata"]["active_cross_references"] == 120
    assert result["metadata"]["cross_references_returned"] == 30
    assert result["metadata"]["next_cross_reference_offset"] == 60
    assert result["data"]["cross_references"][0]["id"] == "PDB30"
    assert result["metadata"]["total_sequence_features"] == 8
    assert result["metadata"]["next_feature_offset"] == 5
    assert result["data"]["sequence_features"][0]["database_id"] == "IPR2"


def test_base_rest_uniprot_pagination_preserves_header_total_and_cursor():
    tool = BaseRESTTool(
        {
            "name": "UniProt_search_proteomes",
            "parameter": {"properties": {"query": {"type": "string"}, "cursor": {}}},
            "fields": {
                "endpoint": "https://rest.uniprot.org/proteomes/search",
                "params": {"format": "json"},
                "pagination": "uniprot_cursor",
            },
        }
    )
    response = _response(
        {"results": [{"id": "UP0001"}, {"id": "UP0002"}]},
        {
            "x-total-results": "150323",
            "Link": '<https://rest.uniprot.org/proteomes/search?cursor=NEXT&size=2>; rel="next"',
        },
    )
    result = tool._process_response(
        response, "https://rest.uniprot.org/proteomes/search"
    )

    assert (
        tool._build_params({"query": "E. coli", "cursor": "CURRENT"})["cursor"]
        == "CURRENT"
    )
    assert result["metadata"] == {
        "total_results": 150323,
        "returned": 2,
        "has_more": True,
        "truncated": True,
        "next_cursor": "NEXT",
    }


def test_uniprot_ref_proteome_total_includes_components_beyond_first_page():
    entry = {
        "id": "UP000694402",
        "components": [
            {
                "name": f"component-{index}",
                "proteinCount": 0 if index < 30 else 10,
            }
            for index in range(36)
        ],
    }
    tool = UniProtRefTool(
        {
            "name": "UniProtRef_get_proteome",
            "fields": {"endpoint": "get_proteome"},
        }
    )
    with patch(
        "tooluniverse.uniprot_ref_tool.requests.get", return_value=_response(entry)
    ):
        result = tool.run(
            {
                "proteome_id": "UP000694402",
                "component_offset": 30,
                "component_limit": 3,
            }
        )

    assert result["data"]["total_protein_count"] == 60
    assert len(result["data"]["components"]) == 3
    assert result["data"]["components"][0]["name"] == "component-30"
    assert result["metadata"]["total_components"] == 36
    assert result["metadata"]["next_component_offset"] == 33


@pytest.mark.parametrize(
    ("tool_class", "name", "source"),
    [
        (MyGeneTool, "MyGene_query_genes", "MyGene.info"),
        (MyVariantTool, "MyVariant_query_variants", "MyVariant.info"),
        (MyChemTool, "MyChem_query_chemicals", "MyChem.info"),
    ],
)
def test_biothings_queries_expose_reachable_offsets(tool_class, name, source):
    tool = tool_class({"name": name, "fields": {"operation": "query"}})
    payload = {
        "total": 5,
        "hits": [{"_id": "page-2-a"}, {"_id": "page-2-b"}],
    }
    with patch(
        "tooluniverse.mygene_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = tool.run(
            {"query": "kinase", "size": 2, "offset": 2, "sort": "stable_field"}
        )

    assert get.call_args.kwargs["params"]["from"] == 2
    assert get.call_args.kwargs["params"]["sort"] == "stable_field"
    assert result["metadata"] == {
        "source": source,
        "total_results": 5,
        "accessible_results": 5,
        "returned": 2,
        "offset": 2,
        "limit": 2,
        "has_more": True,
        "truncated": True,
        "next_offset": 4,
        "upstream_truncated": False,
        "all_results_reachable": True,
        "warning": None,
    }


def test_bioimages_search_exposes_official_page_navigation():
    tool = BioImageArchiveTool(
        {
            "name": "BioImageArchive_search_bioimages",
            "fields": {"action": "search_bioimages"},
        }
    )
    payload = {
        "totalHits": 5,
        "hits": [{"accession": "S-BIAD2"}, {"accession": "S-BIAD3"}],
    }
    with patch(
        "tooluniverse.bioimage_archive_tool.requests.get",
        return_value=_response(payload),
    ) as get:
        result = tool.run({"query": "microscopy", "page_size": 2, "page": 2})

    assert get.call_args.kwargs["params"]["page"] == 2
    assert result["metadata"]["total_hits"] == 5
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["truncated"] is True
    assert result["metadata"]["next_page"] == 3


def test_dfam_search_exposes_official_start_as_offset():
    tool = DfamTool(
        {"name": "Dfam_search_families", "fields": {"endpoint": "search_families"}}
    )
    payload = {
        "total_count": 5,
        "results": [
            {"accession": "DF3", "name": "Alu3"},
            {"accession": "DF4", "name": "Alu4"},
        ],
    }
    with patch(
        "tooluniverse.dfam_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = tool.run({"name_prefix": "Alu", "limit": 2, "offset": 2})

    assert get.call_args.kwargs["params"]["start"] == 2
    assert result["metadata"]["total_count"] == 5
    assert result["metadata"]["next_offset"] == 4
    assert result["metadata"]["truncated"] is True


def test_rnacentral_search_exposes_next_page_and_url():
    tool = RNAcentralSearchTool(
        {
            "name": "RNAcentral_search",
            "settings": {"base_url": "https://rnacentral.org/api/v1"},
        }
    )
    payload = {
        "next": "https://rnacentral.org/api/v1/rna/?page=3&page_size=2",
        "results": [{"rnacentral_id": "URS3"}, {"rnacentral_id": "URS4"}],
    }
    with patch("tooluniverse.rnacentral_tool._http_get", return_value=payload) as get:
        result = tool.run({"query": "let-7", "page_size": 2, "page": 2})

    assert "page=2" in get.call_args.args[0]
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["truncated"] is True
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["next_url"] == payload["next"]


@pytest.mark.parametrize(
    ("tool_class", "endpoint", "arguments"),
    [
        (MGnifyStudiesTool, "studies", {"search": "gut"}),
        (
            MGnifyAnalysesTool,
            "analyses",
            {"study_accession": "MGYS00006862"},
        ),
    ],
)
def test_mgnify_searches_preserve_upstream_pagination(tool_class, endpoint, arguments):
    tool = tool_class(
        {
            "name": f"MGnify_{endpoint}",
            "settings": {"base_url": "https://www.ebi.ac.uk/metagenomics/api/v1"},
        }
    )
    payload = {
        "data": [{"id": "item-3"}, {"id": "item-4"}],
        "links": {"next": f"https://example/{endpoint}?page=3", "prev": "page=1"},
        "meta": {"pagination": {"page": 2, "pages": 10, "count": 20}},
    }
    with patch("tooluniverse.mgnify_tool._http_get", return_value=payload) as get:
        result = tool.run({**arguments, "size": 2, "page": 2})

    assert "page=2" in get.call_args.args[0]
    assert result["metadata"]["total_results"] == 20
    assert result["metadata"]["total_pages"] == 10
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["links"] == payload["links"]


def test_pride_search_uses_page_and_preserves_total_records_header():
    tool = PRIDERESTTool(
        {
            "name": "PRIDE_search_proteomics",
            "parameter": {"properties": {"page_size": {}, "page": {}}},
            "fields": {
                "endpoint": "https://www.ebi.ac.uk/pride/ws/archive/v2/search/projects?keyword={query}"
            },
        }
    )
    response = _response(
        [{"accession": "PXD3"}, {"accession": "PXD4"}],
        {"total_records": "7613"},
    )
    with patch("tooluniverse.pride_tool.request_with_retry", return_value=response):
        result = tool.run({"query": "cancer", "page_size": 2, "page": 1})

    assert "pageSize=2" in result["url"]
    assert "page=1" in result["url"]
    assert result["metadata"]["total_results"] == 7613
    assert result["metadata"]["next_page"] == 2


def test_clinvar_search_exposes_retstart_and_next_offset():
    tool = ClinVarSearchVariants({"name": "ClinVar_search_variants"})
    esearch = {
        "status": "success",
        "data": {
            "esearchresult": {
                "count": "5",
                "idlist": ["3", "4"],
                "querytranslation": "BRCA1[gene]",
            }
        },
    }
    esummary = {
        "status": "success",
        "data": {"result": {"3": {"uid": "3"}, "4": {"uid": "4"}}},
    }
    with patch.object(
        tool, "_make_request", side_effect=[esearch, esummary]
    ) as request:
        result = tool.run({"gene": "BRCA1", "max_results": 2, "offset": 2})

    assert request.call_args_list[0].args[1]["retstart"] == 2
    assert result["data"]["total_count"] == 5
    assert result["data"]["returned"] == 2
    assert result["data"]["truncated"] is True
    assert result["data"]["next_offset"] == 4


def test_kegg_compound_preserves_every_flat_file_field():
    flat_file = """ENTRY       C00002                      Compound
NAME        ATP;
REACTION    R00086  ATP phosphohydrolase
MODULE      M00001  Glycolysis
NETWORK     N00001  Signaling
ATOM        31
            1 C1y C
BOND        33
            1 1 2 1
UNMODELED   future KEGG field
///
"""
    tool = KEGGExtTool(
        {"name": "KEGG_get_compound", "fields": {"endpoint": "get_compound"}}
    )
    with patch(
        "tooluniverse.kegg_ext_tool.requests.get",
        return_value=_response({}, text=flat_file),
    ):
        result = tool.run({"compound_id": "C00002"})

    data = result["data"]
    assert data["reactions"] == ["R00086  ATP phosphohydrolase"]
    assert data["atoms"] == ["31", "1 C1y C"]
    assert data["bonds"] == ["33", "1 1 2 1"]
    assert data["raw_fields"]["UNMODELED"] == ["future KEGG field"]
    assert data["raw_data"] == flat_file


def test_cellxgene_collections_expose_reachable_offsets():
    tool = CellxGeneDiscoveryTool(
        {"name": "CxGDisc_list_collections", "fields": {"endpoint": "list_collections"}}
    )
    payload = [
        {"collection_id": f"collection-{index}", "name": f"Collection {index}"}
        for index in range(5)
    ]
    with patch(
        "tooluniverse.cellxgene_discovery_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"limit": 2, "offset": 2})

    assert [item["collection_id"] for item in result["data"]["collections"]] == [
        "collection-2",
        "collection-3",
    ]
    assert result["data"]["total_collections"] == 5
    assert result["data"]["truncated"] is True
    assert result["data"]["next_offset"] == 4


def test_cellxgene_dataset_search_offsets_after_stable_sort():
    tool = CellxGeneDiscoveryTool(
        {"name": "CxGDisc_search_datasets", "fields": {"endpoint": "search_datasets"}}
    )
    payload = [
        {
            "id": f"dataset-{index}",
            "name": f"Dataset {index}",
            "cell_count": 500 - index,
            "organism": [{"label": "Homo sapiens"}],
        }
        for index in range(5)
    ]
    with patch(
        "tooluniverse.cellxgene_discovery_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"organism": "Homo sapiens", "limit": 2, "offset": 2})

    assert [item["dataset_id"] for item in result["data"]["datasets"]] == [
        "dataset-2",
        "dataset-3",
    ]
    assert result["data"]["total_matching"] == 5
    assert result["data"]["next_offset"] == 4


def test_biosamples_structured_filter_exposes_real_page_navigation():
    tool = BioSamplesTool(
        {
            "name": "BioSamples_search_by_filter",
            "fields": {"endpoint_type": "search_by_filter"},
        }
    )
    payload = {
        "_embedded": {
            "samples": [
                {"accession": "SAMEA3", "characteristics": {}},
                {"accession": "SAMEA4", "characteristics": {}},
            ]
        },
        "page": {"number": 1, "totalPages": 3, "totalElements": 5},
    }
    with patch(
        "tooluniverse.biosamples_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = tool.run(
            {
                "attribute": "Organism",
                "value": "Homo sapiens",
                "limit": 2,
                "page": 1,
            }
        )

    assert get.call_args.kwargs["params"]["page"] == 1
    assert result["metadata"]["total_elements"] == 5
    assert result["metadata"]["current_page"] == 1
    assert result["metadata"]["truncated"] is True
    assert result["metadata"]["next_page"] == 2


@pytest.mark.parametrize(
    ("endpoint_type", "result_type", "identifier"),
    [
        ("search_studies", "study", "study_accession"),
        ("search_samples", "sample", "sample_accession"),
        ("search_runs", "read_run", "run_accession"),
    ],
)
def test_ena_searches_report_exact_truncation_and_allow_more_than_100(
    endpoint_type, result_type, identifier
):
    tool = ENAPortalTool(
        {"name": f"ENA_{endpoint_type}", "fields": {"endpoint_type": endpoint_type}}
    )
    search_response = _response(
        [{identifier: f"record-{index}"} for index in range(101)]
    )
    count_response = _response({}, text="count\n500")
    with patch(
        "tooluniverse.ena_portal_tool.requests.get",
        side_effect=[search_response, count_response],
    ) as get:
        result = tool.run({"query": "tax_tree(9606)", "limit": 101})

    assert get.call_args_list[0].kwargs["params"]["limit"] == 101
    assert get.call_args_list[1].kwargs["params"]["result"] == result_type
    assert len(result["data"]) == 101
    assert result["metadata"]["total_results"] == 500
    assert result["metadata"]["truncation_known"] is True
    assert result["metadata"]["truncated"] is True
    # ENA has no offset pagination, so merely doubling the prefix would still
    # leave records unreachable. The exact count is the useful rerun limit.
    assert result["metadata"]["suggested_limit"] == 500


@pytest.mark.parametrize(
    ("endpoint_type", "arguments", "payload", "id_key"),
    [
        (
            "search_species",
            {"query": "Bacteroides"},
            {
                "code": "200",
                "all_species": [
                    {
                        "ncbi_taxon_id": index,
                        "name": f"Bacteroides {index}",
                        "presented_samples": str(100 - index),
                    }
                    for index in range(5)
                ],
            },
            "ncbi_taxon_id",
        ),
        (
            "get_phenotypes",
            {"query": ""},
            {
                "code": "200",
                "phenotypes": [
                    {
                        "id": index,
                        "term": f"Phenotype {index}",
                        "valid_runs": 100 - index,
                    }
                    for index in range(5)
                ],
            },
            "phenotype_id",
        ),
    ],
)
def test_gmrepo_bulk_searches_expose_reachable_offsets(
    endpoint_type, arguments, payload, id_key
):
    tool = GmrepoTool(
        {"name": f"GMrepo_{endpoint_type}", "fields": {"endpoint_type": endpoint_type}}
    )
    with patch(
        "tooluniverse.gmrepo_tool.requests.post", return_value=_response(payload)
    ):
        result = tool.run({**arguments, "limit": 2, "offset": 2})

    assert [item[id_key] for item in result["data"]] == [2, 3]
    assert result["metadata"]["total_matches"] == 5
    assert result["metadata"]["truncated"] is True
    assert result["metadata"]["next_offset"] == 4


def test_mavedb_search_exposes_reachable_offset_after_full_search_response():
    tool = MaveDBTool(
        {"name": "MaveDB_search_score_sets", "fields": {"operation": "search"}}
    )
    payload = {
        "scoreSets": [
            {"urn": f"urn:mavedb:test-{index}", "targetGenes": []} for index in range(5)
        ]
    }
    tool.session.post = MagicMock(return_value=_response(payload))
    result = tool.run({"query": "BRCA1", "limit": 2, "offset": 2})

    assert [item["urn"] for item in result["data"]] == [
        "urn:mavedb:test-2",
        "urn:mavedb:test-3",
    ]
    assert result["metadata"]["total_results"] == 5
    assert result["metadata"]["next_offset"] == 4


def test_bioregistry_search_schema_data_exposes_later_prefixes():
    tool = BioregistryTool(
        {
            "name": "Bioregistry_search_registries",
            "fields": {"operation": "search_registries"},
        }
    )
    payload = [[f"prefix-{index}", f"Name {index}"] for index in range(5)]
    with patch(
        "tooluniverse.bioregistry_tool.requests.get", return_value=_response(payload)
    ):
        result = tool.run(
            {
                "operation": "search_registries",
                "query": "protein",
                "limit": 2,
                "offset": 2,
            }
        )

    assert [item["prefix"] for item in result["data"]["results"]] == [
        "prefix-2",
        "prefix-3",
    ]
    assert result["data"]["total"] == 5
    assert result["data"]["truncated"] is True
    assert result["data"]["next_offset"] == 4


def test_conoserver_bulk_search_exposes_later_matches():
    tool = ConoServerSearchConopeptidesTool({"name": "ConoServer_search_conopeptides"})
    entries = [
        {"id": f"P{index:05d}", "organism_latin": "Conus test"} for index in range(5)
    ]
    with patch("tooluniverse.conoserver_tool._load_entries", return_value=entries):
        result = tool.run({"organism": "Conus", "limit": 2, "offset": 2})

    assert [item["id"] for item in result["data"]["results"]] == [
        "P00002",
        "P00003",
    ]
    assert result["data"]["count"] == 5
    assert result["data"]["truncated"] is True
    assert result["data"]["next_offset"] == 4


def test_finngen_phenotype_search_exposes_later_matches():
    tool = FinnGenTool(
        {
            "name": "FinnGen_list_phenotypes",
            "fields": {"endpoint_type": "list_phenotypes"},
        }
    )
    payload = [
        {
            "phenocode": f"P{index}",
            "phenostring": f"Phenotype {index}",
            "category": "test",
            "num_cases": 100 - index,
        }
        for index in range(5)
    ]
    with patch(
        "tooluniverse.finngen_tool.requests.get", return_value=_response(payload)
    ):
        result = tool.run({"limit": 2, "offset": 2})

    assert [item["phenocode"] for item in result["data"]] == ["P2", "P3"]
    assert result["metadata"]["total_matching"] == 5
    assert result["metadata"]["next_offset"] == 4


def test_cath_funfams_expose_later_matches():
    tool = CATHTool(
        {"name": "CATH_list_funfams", "fields": {"endpoint": "list_funfams"}}
    )
    payload = {
        "data": [
            {"funfam_number": str(index), "name": f"FunFam {index}"}
            for index in range(5)
        ]
    }
    with patch("tooluniverse.cath_tool.requests.get", return_value=_response(payload)):
        result = tool.run(
            {"superfamily_id": "1.10.510.10", "max_results": 2, "offset": 2}
        )

    assert [item["funfam_number"] for item in result["data"]["funfams"]] == [
        "2",
        "3",
    ]
    assert result["data"]["total_funfams"] == 5
    assert result["data"]["next_offset"] == 4


def test_hpo_search_maps_offset_to_upstream_page():
    tool = HPOTool({"name": "HPO_search_terms", "fields": {"endpoint": "search_terms"}})
    payload = {
        "terms": [
            {"id": "HP:0000003", "name": "Third"},
            {"id": "HP:0000004", "name": "Fourth"},
        ],
        "totalCount": 10,
    }
    with patch(
        "tooluniverse.hpo_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = tool.run({"query": "test", "max_results": 2, "offset": 2})

    assert get.call_args.kwargs["params"]["page"] == 1
    assert [item["id"] for item in result["data"]] == ["HP:0000003", "HP:0000004"]
    assert result["metadata"]["next_offset"] == 4


def test_ensembl_ld_exposes_later_sorted_partners():
    tool = EnsemblLDTool(
        {
            "name": "EnsemblLD_get_ld_variants",
            "fields": {"endpoint_type": "ld_variants"},
        }
    )
    payload = [
        {
            "variation1": "rs1",
            "variation2": f"rs{index + 2}",
            "r2": 1 - index / 10,
            "d_prime": 1,
        }
        for index in range(5)
    ]
    with patch(
        "tooluniverse.ensembl_ld_tool.requests.get", return_value=_response(payload)
    ):
        result = tool.run(
            {"variant_id": "rs1", "population": "POP", "limit": 2, "offset": 2}
        )

    assert [item["variant2"] for item in result["data"]["ld_variants"]] == [
        "rs4",
        "rs5",
    ]
    assert result["data"]["total_ld_count"] == 5
    assert result["data"]["next_offset"] == 4


def test_chebi_search_maps_offset_to_server_page_and_in_page_skip():
    tool = ChEBITool({"name": "ChEBI_search", "fields": {"endpoint_type": "search"}})
    payload = {
        "total": 100,
        "number_pages": 7,
        "results": [
            {"_source": {"chebi_accession": f"CHEBI:{index}"}}
            for index in range(15, 30)
        ],
    }
    with patch(
        "tooluniverse.chebi_tool.requests.post", return_value=_response(payload)
    ) as post:
        result = tool.run({"query": "test", "limit": 2, "offset": 17})

    assert post.call_args.kwargs["params"]["page"] == 2
    assert [item["chebi_accession"] for item in result["data"]["compounds"]] == [
        "CHEBI:17",
        "CHEBI:18",
    ]
    assert result["data"]["next_offset"] == 19


def test_ensembl_phenotype_term_exposes_later_associations():
    tool = EnsemblPhenotypeTool(
        {"name": "EnsemblPheno_get_by_term", "fields": {"endpoint_type": "term"}}
    )
    payload = [
        {"description": "Trait", "Variation": f"rs{index}", "attributes": {}}
        for index in range(5)
    ]
    with patch(
        "tooluniverse.ensembl_phenotype_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"term": "Trait", "limit": 2, "offset": 2})

    assert [item["variant"] for item in result["data"]["associations"]] == [
        "rs2",
        "rs3",
    ]
    assert result["data"]["association_count"] == 5
    assert result["data"]["next_offset"] == 4


def test_ensembl_gene_phenotypes_expose_later_associations():
    tool = EnsemblPhenotypeTool(
        {"name": "EnsemblPheno_get_by_gene", "fields": {"endpoint_type": "gene"}}
    )
    payload = [
        {"description": f"Trait {index}", "source": "GWAS", "attributes": {}}
        for index in range(5)
    ]
    with patch(
        "tooluniverse.ensembl_phenotype_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"gene": "TP53", "limit": 2, "offset": 2})

    assert [item["description"] for item in result["data"]["phenotypes"]] == [
        "Trait 2",
        "Trait 3",
    ]
    assert result["data"]["phenotype_count"] == 5
    assert result["data"]["next_offset"] == 4


def test_ensembl_region_phenotypes_expose_later_associations():
    tool = EnsemblPhenotypeTool(
        {
            "name": "EnsemblPheno_get_by_region",
            "fields": {"endpoint_type": "region"},
        }
    )
    payload = [
        {
            "id": f"rs{index}",
            "phenotype_associations": [
                {"description": f"Trait {index}", "source": "GWAS"}
            ],
        }
        for index in range(5)
    ]
    with patch(
        "tooluniverse.ensembl_phenotype_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"region": "7:1-100", "limit": 2, "offset": 2})

    assert [item["id"] for item in result["data"]["phenotypes"]] == ["rs2", "rs3"]
    assert result["data"]["phenotype_count"] == 5
    assert result["data"]["next_offset"] == 4


def test_ensembl_variant_phenotypes_expose_later_associations():
    tool = EnsemblPhenotypeTool(
        {
            "name": "EnsemblPheno_get_by_variant",
            "fields": {"endpoint_type": "variant"},
        }
    )
    payload = {"phenotypes": [{"trait": f"Trait {index}"} for index in range(5)]}
    with patch(
        "tooluniverse.ensembl_phenotype_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"variant_id": "rs1", "limit": 2, "offset": 2})

    assert [item["trait"] for item in result["data"]["phenotypes"]] == [
        "Trait 2",
        "Trait 3",
    ]
    assert result["data"]["phenotype_count"] == 5
    assert result["data"]["next_offset"] == 4


def test_ensembl_region_features_expose_later_upstream_records():
    tool = EnsemblOverlapTool(
        {"name": "Ensembl_get_region_features", "fields": {"endpoint": "region"}}
    )
    payload = [
        {
            "feature_type": "gene",
            "id": f"ENSG{index}",
            "start": index,
            "end": index + 1,
            "strand": 1,
        }
        for index in range(5)
    ]
    with patch(
        "tooluniverse.ensembl_overlap_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"region": "1:1-10", "limit": 2, "offset": 2})

    assert [item["id"] for item in result["data"]["features"]] == [
        "ENSG2",
        "ENSG3",
    ]
    assert result["data"]["total_features"] == 5
    assert result["data"]["next_offset"] == 4


def test_ensembl_gene_overlap_exposes_later_upstream_records():
    tool = EnsemblOverlapTool(
        {
            "name": "Ensembl_get_gene_overlapping_features",
            "fields": {"endpoint": "gene_id"},
        }
    )
    payload = [
        {
            "feature_type": "exon",
            "id": f"ENSE{index}",
            "start": index,
            "end": index + 1,
            "strand": 1,
        }
        for index in range(5)
    ]
    with patch(
        "tooluniverse.ensembl_overlap_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run(
            {
                "gene_id": "ENSG00000141510",
                "feature_types": "exon",
                "limit": 2,
                "offset": 2,
            }
        )

    assert [item["id"] for item in result["data"]["features"]] == [
        "ENSE2",
        "ENSE3",
    ]
    assert result["data"]["total_features"] == 5
    assert result["data"]["next_offset"] == 4


def test_clingen_gene_validity_catalog_exposes_later_curations():
    tool = ClinGenTool(
        {
            "name": "ClinGen_get_gene_validity",
            "fields": {"operation": "get_gene_validity"},
        }
    )
    csv_text = "GENE SYMBOL,DISEASE LABEL,CLASSIFICATION\n" + "\n".join(
        f"GENE{index},Disease {index},Definitive" for index in range(5)
    )
    with patch(
        "tooluniverse.clingen_tool.requests.get",
        return_value=_response({}, text=csv_text),
    ):
        result = tool.run({"limit": 2, "offset": 2})

    assert [item["GENE SYMBOL"] for item in result["data"]] == ["GENE2", "GENE3"]
    assert result["total"] == 5
    assert result["next_offset"] == 4
    assert result["metadata"]["has_more"] is True


def test_clingen_dosage_catalog_exposes_later_curations():
    tool = ClinGenTool(
        {
            "name": "ClinGen_get_dosage_sensitivity",
            "fields": {"operation": "get_dosage_sensitivity"},
        }
    )
    csv_text = "GENE SYMBOL,HGNC ID,HAPLOINSUFFICIENCY\n" + "\n".join(
        f"GENE{index},HGNC:{index},Sufficient" for index in range(5)
    )
    with patch(
        "tooluniverse.clingen_tool.requests.get",
        return_value=_response({}, text=csv_text),
    ):
        result = tool.run({"limit": 2, "offset": 2})

    assert [item["GENE SYMBOL"] for item in result["data"]] == ["GENE2", "GENE3"]
    assert result["total"] == 5
    assert result["next_offset"] == 4


@pytest.mark.parametrize(
    ("operation", "context"),
    [
        ("get_actionability_adult", "Adult"),
        ("get_actionability_pediatric", "Pediatric"),
    ],
)
def test_clingen_actionability_catalogs_expose_later_curations(operation, context):
    tool = ClinGenTool(
        {"name": f"ClinGen_{operation}", "fields": {"operation": operation}}
    )
    payload = [
        {"docId": f"AC{index}", "geneOrVariant": f"GENE{index}"} for index in range(5)
    ]
    with patch(
        "tooluniverse.clingen_tool.requests.get", return_value=_response(payload)
    ):
        result = tool.run({"limit": 2, "offset": 2})

    assert [item["docId"] for item in result["data"]] == ["AC2", "AC3"]
    assert result["context"] == context
    assert result["total"] == 5
    assert result["next_offset"] == 4


def _cellmarker_dataframe():
    pd = pytest.importorskip("pandas")
    rows = [
        ("T cell", "T1", "Normal cell"),
        ("CD8+ T cell", "T2", "Cancer cell"),
        ("Fat cell (adipocyte)", "FAT", "Normal cell"),
        ("Mast cell", "MAST", "Cancer cell"),
        ("T cell", "T3", "Cancer cell"),
    ]
    return pd.DataFrame(
        [
            {
                "species": "Human",
                "tissue_class": "Lung",
                "tissue_type": "Lung",
                "cancer_type": "Lung cancer",
                "cell_type": context,
                "cell_name": cell_name,
                "marker": symbol,
                "Symbol": symbol,
                "marker_source": "Experiment",
                "cell_marker": symbol,
                "source": "Experiment",
                "supports": 1,
            }
            for cell_name, symbol, context in rows
        ]
    )


def test_cellmarker_cell_type_uses_phrase_boundaries_and_paginates_both_lists():
    tool = CellMarkerTool(
        {
            "name": "CellMarker_search_by_cell_type",
            "fields": {"operation": "search_by_cell_type"},
        }
    )
    with patch(
        "tooluniverse.cellmarker_tool._load_dataframe",
        return_value=_cellmarker_dataframe(),
    ):
        result = tool.run(
            {
                "operation": "search_by_cell_type",
                "cell_name": "T cell",
                "limit": 1,
                "offset": 1,
            }
        )

    data = result["data"]
    assert data["total_records"] == 3
    assert data["records"][0]["cell_name"] == "CD8+ T cell"
    assert data["marker_genes"] == ["T2"]
    assert data["next_offset"] == 2
    assert all("Fat cell" not in record["cell_name"] for record in data["records"])


def test_cellmarker_gene_and_cancer_searches_expose_later_records():
    df = _cellmarker_dataframe()
    df.loc[:, "cell_marker"] = "CD68"
    tool = CellMarkerTool(
        {
            "name": "CellMarker_search_by_gene",
            "fields": {"operation": "search_by_gene"},
        }
    )
    with patch("tooluniverse.cellmarker_tool._load_dataframe", return_value=df):
        gene = tool.run(
            {
                "operation": "search_by_gene",
                "gene_symbol": "CD68",
                "limit": 2,
                "offset": 2,
            }
        )
        cancer = tool.run(
            {
                "operation": "search_cancer_markers",
                "cancer_type": "Lung",
                "limit": 1,
                "offset": 1,
            }
        )

    assert [item["cell_name"] for item in gene["data"]["records"]] == [
        "Fat cell (adipocyte)",
        "Mast cell",
    ]
    assert gene["data"]["next_offset"] == 4
    assert cancer["data"]["total_records"] == 3
    assert cancer["data"]["records"][0]["cell_name"] == "Mast cell"


def test_rgd_annotations_expose_later_records_and_preserve_full_notes():
    tool = RGDTool(
        {
            "name": "RGD_get_annotations",
            "fields": {"endpoint_type": "get_annotations"},
        }
    )
    payload = [
        {
            "term": f"Term {index}",
            "termAcc": f"DOID:{index}",
            "aspect": "D",
            "notes": "N" * 500,
        }
        for index in range(5)
    ]
    with patch.object(tool.session, "get", return_value=_response(payload)):
        result = tool.run({"rgd_id": "2218", "limit": 2, "offset": 2})

    assert [item["term_acc"] for item in result["data"]] == ["DOID:2", "DOID:3"]
    assert len(result["data"][0]["notes"]) == 500
    assert result["metadata"]["total_annotations"] == 5
    assert result["metadata"]["next_offset"] == 4


def test_rgd_qtl_region_exposes_later_loci():
    tool = RGDTool(
        {
            "name": "RGD_get_qtls_in_region",
            "fields": {"endpoint_type": "get_qtls_in_region"},
        }
    )
    payload = [{"rgdId": index, "symbol": f"QTL{index}"} for index in range(5)]
    with patch.object(tool.session, "get", return_value=_response(payload)):
        result = tool.run(
            {
                "chromosome": "10",
                "start": 1,
                "stop": 200_000_000,
                "map_key": 360,
                "limit": 2,
                "offset": 2,
            }
        )

    assert [item["symbol"] for item in result["data"]] == ["QTL2", "QTL3"]
    assert result["metadata"]["total_qtls"] == 5
    assert result["metadata"]["next_offset"] == 4


def test_rgd_region_gene_resolution_exposes_later_genes():
    tool = RGDTool(
        {
            "name": "RGD_resolve_symbol_or_region",
            "fields": {"endpoint_type": "resolve_symbol_or_region"},
        }
    )
    payload = [
        {
            "gene": {"rgdId": index, "symbol": f"GENE{index}"},
            "chromosome": "10",
            "start": index,
            "stop": index + 1,
        }
        for index in range(5)
    ]
    with patch.object(tool.session, "get", return_value=_response(payload)):
        result = tool.run(
            {
                "chromosome": "10",
                "start": 1,
                "stop": 200_000_000,
                "map_key": 360,
                "limit": 2,
                "offset": 2,
            }
        )

    assert [item["symbol"] for item in result["data"]] == ["GENE2", "GENE3"]
    assert result["metadata"]["total_genes"] == 5
    assert result["metadata"]["next_offset"] == 4


def _europepmc_annotation_payload(count=5):
    return [
        {
            "source": "MED",
            "extId": "25780448",
            "pmcid": "PMC4353746",
            "annotations": [
                {
                    "exact": f"GENE{index}",
                    "type": "Gene_Proteins",
                    "tags": [{"name": f"GENE{index}", "uri": f"urn:{index}"}],
                }
                for index in range(count)
            ],
        }
    ]


def test_europepmc_article_annotations_expose_later_mentions():
    tool = EuroPMCAnnotationsTool(
        {
            "name": "EuroPMCAnnot_get_article_annotations",
            "fields": {"endpoint_type": "by_article"},
        }
    )
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        return_value=_response(_europepmc_annotation_payload()),
    ):
        result = tool.run(
            {"article_id": "PMC:PMC4353746", "limit": 2, "offset": 2}
        )

    assert [item["exact"] for item in result["data"]["annotations"]] == [
        "GENE2",
        "GENE3",
    ]
    assert result["data"]["annotation_count"] == 5
    assert result["data"]["next_offset"] == 4


def test_europepmc_gene_protein_label_maps_to_real_api_token_and_batch_pages():
    tool = EuroPMCAnnotationsTool(
        {
            "name": "EuroPMCAnnot_get_annotations_by_type",
            "fields": {"endpoint_type": "batch_by_type"},
        }
    )
    with patch(
        "tooluniverse.europepmc_annotations_tool.requests.get",
        return_value=_response(_europepmc_annotation_payload()),
    ) as get:
        result = tool.run(
            {
                "article_ids": "PMC:PMC4353746",
                "annotation_type": "Genes & Proteins",
                "limit": 2,
                "offset": 2,
            }
        )

    params = get.call_args.kwargs["params"]
    assert params["type"] == "Gene_Proteins"
    assert params["pageSize"] == 1
    article = result["data"]["articles"][0]
    assert article["annotation_count"] == 5
    assert [item["exact"] for item in article["annotations"]] == ["GENE2", "GENE3"]
    assert article["next_offset"] == 4


def test_ensembl_species_info_exposes_true_matches_and_later_pages():
    tool = EnsemblInfoTool(
        {"name": "Ensembl_get_species_info", "fields": {"endpoint": "species"}}
    )
    payload = {
        "species": [
            {"name": f"species_{index}", "taxon_id": str(1000 + index)}
            for index in range(55)
        ]
    }
    with patch(
        "tooluniverse.ensembl_info_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"limit": 3, "offset": 50})

    assert result["data"]["matched_species"] == 55
    assert result["data"]["returned_species"] == 3
    assert [item["name"] for item in result["data"]["species"]] == [
        "species_50",
        "species_51",
        "species_52",
    ]
    assert result["data"]["next_offset"] == 53


def test_ensembl_assembly_recognizes_primary_assembly_karyotype_without_cap():
    tool = EnsemblInfoTool(
        {"name": "Ensembl_get_assembly_info", "fields": {"endpoint": "assembly"}}
    )
    karyotype = [str(index) for index in range(1, 40)] + ["W", "Z", "MT"]
    payload = {
        "karyotype": karyotype,
        "top_level_region": [
            {"name": name, "length": index + 1, "coord_system": "primary_assembly"}
            for index, name in enumerate(karyotype)
        ]
        + [{"name": "unplaced", "length": 1, "coord_system": "primary_assembly"}],
    }
    with patch(
        "tooluniverse.ensembl_info_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"species": "gallus_gallus"})

    assert result["data"]["total_chromosomes"] == 42
    assert len(result["data"]["chromosomes"]) == 42
    assert {item["name"] for item in result["data"]["chromosomes"]} == set(karyotype)


@pytest.mark.parametrize(
    ("endpoint_type", "count_key", "records_key"),
    [
        ("motif_features", "motif_count", "motif_features"),
        ("constrained_elements", "element_count", "constrained_elements"),
    ],
)
def test_ensembl_regulation_exposes_records_beyond_old_200_cap(
    endpoint_type, count_key, records_key
):
    tool = EnsemblRegulationTool(
        {
            "name": f"EnsemblReg_{endpoint_type}",
            "fields": {"endpoint_type": endpoint_type},
        }
    )
    if endpoint_type == "motif_features":
        payload = [
            {"stable_id": f"MOTIF{index}", "score": index} for index in range(205)
        ]
    else:
        payload = [
            {"ID": f"ELEMENT{index}", "score": index} for index in range(205)
        ]
    with patch(
        "tooluniverse.ensembl_regulation_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"region": "17:7000000-8000000", "limit": 3, "offset": 200})

    assert result["data"][count_key] == 205
    assert len(result["data"][records_key]) == 3
    assert result["data"]["returned"] == 3
    assert result["data"]["next_offset"] == 203


def _reactome_search_payload(total=1252, count=3):
    return {
        "numberOfMatches": total,
        "numberOfGroups": 1,
        "results": [
            {
                "typeName": "Pathway",
                "entriesCount": total,
                "entries": [
                    {"stId": f"R-HSA-{index}", "name": f"Pathway {index}"}
                    for index in range(count)
                ],
            }
        ],
    }


def test_reactome_content_search_uses_official_start_row_and_true_total():
    tool = ReactomeContentTool(
        {"name": "ReactomeContent_search", "fields": {"endpoint": "search"}}
    )
    with patch(
        "tooluniverse.reactome_content_tool.requests.get",
        return_value=_response(_reactome_search_payload()),
    ) as get:
        result = tool.run({"query": "cell cycle", "limit": 3, "offset": 50})

    assert get.call_args.kwargs["params"]["Start row"] == 50
    assert get.call_args.kwargs["params"]["rows"] == 3
    assert result["data"]["total_results"] == 1252
    assert result["data"]["returned"] == 3
    assert result["data"]["next_offset"] == 53


def test_reactome_entity_search_exposes_later_server_page():
    tool = ReactomeInteractorsTool(
        {
            "name": "ReactomeInteractors_search_entity",
            "fields": {"endpoint": "search_entity"},
        }
    )
    with patch(
        "tooluniverse.reactome_interactors_tool.requests.get",
        return_value=_response(_reactome_search_payload(total=5932)),
    ) as get:
        result = tool.run({"query": "kinase", "limit": 3, "offset": 50})

    assert get.call_args.kwargs["params"]["Start row"] == 50
    assert len(result["data"]) == 3
    assert result["metadata"]["total_matches"] == 5932
    assert result["metadata"]["next_offset"] == 53


def test_reactome_contained_events_pages_reactions_after_old_cap():
    tool = ReactomeContentTool(
        {
            "name": "ReactomeContent_get_contained_events",
            "fields": {"endpoint": "contained_events"},
        }
    )
    payload = [
        {
            "stId": f"R-HSA-{index}",
            "displayName": f"Reaction {index}",
            "schemaClass": "Reaction",
        }
        for index in range(55)
    ]
    with patch(
        "tooluniverse.reactome_content_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run(
            {"identifier": "R-HSA-69278", "reaction_limit": 3, "reaction_offset": 50}
        )

    assert result["data"]["reaction_count"] == 55
    assert [item["stId"] for item in result["data"]["reactions"]] == [
        "R-HSA-50",
        "R-HSA-51",
        "R-HSA-52",
    ]
    assert result["data"]["next_reaction_offset"] == 53


def test_reactome_enhanced_pathway_preserves_full_summary_and_literature():
    tool = ReactomeContentTool(
        {
            "name": "ReactomeContent_get_enhanced_pathway",
            "fields": {"endpoint": "enhanced_pathway"},
        }
    )
    payload = {
        "stId": "R-HSA-109581",
        "summation": [{"text": "S" * 2431}],
        "literatureReference": [
            {"title": f"Reference {index}", "pubMedIdentifier": index}
            for index in range(25)
        ],
    }
    with patch(
        "tooluniverse.reactome_content_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"identifier": "R-HSA-109581"})

    assert len(result["data"]["summation"]) == 2431
    assert result["data"]["summation_characters"] == 2431
    assert result["data"]["literature_count"] == 25
    assert len(result["data"]["literature"]) == 25


def test_eol_page_pages_names_synonyms_classifications_and_preserves_text():
    tool = EOLTool({"name": "EOL_get_page", "fields": {"endpoint": "pages"}})
    payload = {
        "taxonConcept": {
            "identifier": 327955,
            "scientificName": "Homo sapiens",
            "vernacularNames": [
                {"vernacularName": f"name-{index}", "language": "en"}
                for index in range(25)
            ],
            "synonyms": [{"synonym": f"synonym-{index}"} for index in range(25)],
            "taxonConcepts": [
                {"identifier": index, "nameAccordingTo": f"source-{index}"}
                for index in range(20)
            ],
            "dataObjects": [
                {"dataType": "Text", "description": "D" * 700},
                {"dataType": "StillImage", "description": "I" * 400},
            ],
        }
    }
    with patch("tooluniverse.eol_tool._eol_http_get", return_value=payload):
        result = tool.run(
            {
                "page_id": 327955,
                "common_name_limit": 2,
                "common_name_offset": 20,
                "synonym_limit": 2,
                "synonym_offset": 20,
                "classification_limit": 2,
                "classification_offset": 15,
            }
        )

    assert result["data"]["common_names"][0]["name"] == "name-20"
    assert result["data"]["synonyms"][0] == "synonym-20"
    assert result["data"]["classifications"][0]["source"] == "source-15"
    assert len(result["data"]["descriptions"][0]["text"]) == 700
    assert len(result["data"]["images"][0]["description"]) == 400
    assert result["metadata"]["num_common_names"] == 25
    assert result["metadata"]["next_common_name_offset"] == 22
    assert result["metadata"]["next_synonym_offset"] == 22
    assert result["metadata"]["next_classification_offset"] == 17


def test_sgd_gene_aliases_are_pageable_beyond_old_ten_item_cap():
    tool = SGDTool(
        {
            "name": "SGD_get_gene",
            "fields": {"endpoint_type": "locus", "query_mode": "overview"},
        }
    )
    payload = {
        "sgdid": "S000000364",
        "aliases": [{"display_name": f"alias-{index}"} for index in range(15)],
    }
    with patch("tooluniverse.sgd_tool.requests.get", return_value=_response(payload)):
        result = tool.run(
            {"sgd_id": "S000000364", "alias_limit": 2, "alias_offset": 10}
        )

    assert result["data"]["aliases"] == ["alias-10", "alias-11"]
    assert result["metadata"]["total_aliases"] == 15
    assert result["metadata"]["next_alias_offset"] == 12


@pytest.mark.parametrize(
    ("query_mode", "default_limit"),
    [
        ("phenotype", 50),
        ("go", 50),
        ("interaction", 50),
        ("regulation", 100),
        ("disease", 50),
    ],
)
def test_sgd_locus_collections_expose_records_after_old_caps(
    query_mode, default_limit
):
    tool = SGDTool(
        {
            "name": f"SGD_get_{query_mode}",
            "fields": {"endpoint_type": "locus", "query_mode": query_mode},
        }
    )
    payload = [{} for _ in range(default_limit + 5)]
    with patch("tooluniverse.sgd_tool.requests.get", return_value=_response(payload)):
        result = tool.run(
            {
                "sgd_id": "S000000364",
                "limit": 2,
                "offset": default_limit,
            }
        )

    assert len(result["data"]) == 2
    assert result["metadata"]["total_results"] == default_limit + 5
    assert result["metadata"]["offset"] == default_limit
    assert result["metadata"]["next_offset"] == default_limit + 2


def test_ebi_category_features_page_beyond_cap_and_keep_all_evidence():
    tool = EBIProteinsFeaturesTool(
        {
            "name": "EBIProteins_get_structural_features",
            "fields": {"category": "STRUCTURAL"},
        }
    )
    payload = {
        "accession": "P00533",
        "features": [
            {
                "type": "HELIX",
                "begin": str(index),
                "end": str(index + 1),
                "evidences": [
                    {
                        "code": f"ECO:{evidence_index}",
                        "source": {"name": "PDB", "id": str(evidence_index)},
                    }
                    for evidence_index in range(5)
                ],
            }
            for index in range(105)
        ],
    }
    with patch(
        "tooluniverse.ebi_proteins_features_tool.requests.get",
        return_value=_response(payload),
    ):
        result = tool.run({"accession": "P00533", "limit": 2, "offset": 100})

    assert result["data"]["total_features"] == 105
    assert result["data"]["returned"] == 2
    assert result["data"]["next_offset"] == 102
    assert len(result["data"]["features"][0]["evidences"]) == 5
    assert len(result["data"]["features"][0]["raw_evidences"]) == 5


def test_oma_hog_preserves_all_children_and_alternative_levels():
    tool = OMATool({"name": "OMA_get_hog", "fields": {"endpoint": "hog"}})
    payload = [
        {
            "hog_id": "HOG:F0782425",
            "alternative_levels": [f"level-{index}" for index in range(41)],
            "children_hogs": [
                {
                    "hog_id": f"child-{index}",
                    "alternative_levels": [
                        f"child-level-{level}" for level in range(78)
                    ],
                }
                for index in range(36)
            ],
        }
    ]
    with patch("tooluniverse.oma_tool.requests.get", return_value=_response(payload)):
        result = tool.run({"hog_id": "HOG:F0782425"})

    hog = result["data"][0]
    assert hog["children_hogs_count"] == 36
    assert len(hog["children_hogs"]) == 36
    assert hog["alternative_levels_count"] == 41
    assert len(hog["alternative_levels"]) == 41
    assert hog["children_hogs"][0]["alternative_levels_count"] == 78
    assert len(hog["children_hogs"][0]["alternative_levels"]) == 78


def test_oma_xref_exposes_matches_beyond_old_hundred_item_cap():
    tool = OMATool({"name": "OMA_resolve_xref", "fields": {"endpoint": "xref"}})
    payload = [
        {"xref": "BRCA2", "entry_nr": index, "omaid": f"OMA{index}"}
        for index in range(105)
    ]
    with patch("tooluniverse.oma_tool.requests.get", return_value=_response(payload)):
        result = tool.run({"search": "BRCA2", "limit": 2, "offset": 100})

    assert [item["entry_nr"] for item in result["data"]] == [100, 101]
    assert result["metadata"]["total_matches"] == 105
    assert result["metadata"]["next_offset"] == 102


def test_oma_group_exposes_members_beyond_old_thirty_item_cap():
    tool = OMATool({"name": "OMA_get_group", "fields": {"endpoint": "group"}})
    payload = {
        "group_nr": 904847,
        "members": [
            {"omaid": f"OMA{index}", "entry_nr": index} for index in range(35)
        ],
    }
    with patch("tooluniverse.oma_tool.requests.get", return_value=_response(payload)):
        result = tool.run({"group_id": "904847", "limit": 2, "offset": 30})

    assert [item["oma_id"] for item in result["data"]["members"]] == [
        "OMA30",
        "OMA31",
    ]
    assert result["metadata"]["total_members"] == 35
    assert result["metadata"]["next_offset"] == 32


def test_pheweb_variant_associations_expose_later_sorted_page():
    tool = PheWebPheWASTool(
        {"name": "UKBTOPMed_phewas_by_variant", "fields": {"biobank": "ukb_topmed"}}
    )
    payload = {
        "phenos": [
            {"phenocode": f"P{index}", "pval": float(100 - index)}
            for index in range(30)
        ]
    }
    tool._http = MagicMock()
    tool._http.get.return_value = _response(payload)
    result = tool.run(
        {"variant": "10:112998590:C:T", "limit": 2, "offset": 20}
    )

    assert result["metadata"]["total_associations"] == 30
    assert result["metadata"]["next_offset"] == 22
    assert [item["phenocode"] for item in result["data"]["associations"]] == [
        "P9",
        "P8",
    ]


def test_genebass_associations_expose_later_page_with_descriptions():
    tool = GenebassTool({"name": "Genebass_gene_burden_phewas"})
    rows = [
        {
            "phenocode": f"P{index}",
            "trait_type": "continuous",
            "pheno_sex": "both_sexes",
            "coding": "",
            "modifier": "",
            "Pvalue_Burden": float(100 - index),
        }
        for index in range(30)
    ]
    main_response = _response(
        {"gene": {"gene_id": "ENSG00000148737"}, "phewas": rows}
    )
    phenotype_response = _response(
        [
            {
                "phenocode": f"P{index}",
                "trait_type": "continuous",
                "pheno_sex": "both_sexes",
                "coding": "",
                "modifier": "",
                "description": f"description-{index}",
            }
            for index in range(30)
        ]
    )
    with patch(
        "tooluniverse.pheweb_phewas_tool.requests.get",
        side_effect=[main_response, phenotype_response],
    ):
        result = tool.run(
            {
                "gene": "ENSG00000148737",
                "limit": 2,
                "offset": 20,
            }
        )

    assert result["metadata"]["total_associations"] == 30
    assert result["metadata"]["next_offset"] == 22
    assert [item["description"] for item in result["data"]["associations"]] == [
        "description-9",
        "description-8",
    ]


def test_gdc_survival_exposes_later_donor_page():
    donors = [
        {
            "id": f"donor-{index}",
            "time": index,
            "censored": index % 2 == 0,
            "survivalEstimate": 1 - index / 100,
        }
        for index in range(60)
    ]
    tool = GDCSurvivalTool({"settings": {"base_url": "https://example.test"}})
    with patch(
        "tooluniverse.gdc_tool._http_get",
        return_value={"results": [{"donors": donors}]},
    ):
        result = tool.run(
            {"project_id": "TCGA-BRCA", "limit": 3, "offset": 50}
        )

    data = result["data"]
    assert data["total_donors"] == 60
    assert data["returned_donors"] == 3
    assert [donor["id"] for donor in data["donors"]] == [
        "donor-50",
        "donor-51",
        "donor-52",
    ]
    assert data["has_more"] is True
    assert data["next_offset"] == 53


def test_gdc_mutation_frequency_exposes_later_ranked_projects():
    occurrence_hits = [
        {
            "case": {
                "case_id": f"case-{index}",
                "project": {"project_id": f"PROJECT-{index}"},
            }
        }
        for index in range(8)
    ]
    project_hits = [
        {"project_id": f"PROJECT-{index}", "summary": {"case_count": 10}}
        for index in range(8)
    ]
    tool = GDCMutationFreqByProjectTool(
        {"settings": {"base_url": "https://example.test"}}
    )
    with patch(
        "tooluniverse.gdc_tool._http_get",
        side_effect=[
            {
                "data": {
                    "hits": occurrence_hits,
                    "pagination": {"total": len(occurrence_hits)},
                }
            },
            {"data": {"hits": project_hits}},
        ],
    ):
        result = tool.run({"gene_symbol": "KRAS", "size": 2, "offset": 5})

    data = result["data"]
    assert data["project_count"] == 8
    assert data["returned_project_count"] == 2
    assert [project["project_id"] for project in data["projects"]] == [
        "PROJECT-5",
        "PROJECT-6",
    ]
    assert data["has_more"] is True
    assert data["next_offset"] == 7


def test_ebi_epitope_preserves_all_supporting_evidence_and_cross_references():
    evidences = [
        {"source": {"name": "PubMed", "id": str(1000 + index)}}
        for index in range(17)
    ]
    xrefs = [{"name": "IEDB", "id": "20767"}, {"name": "Other", "id": "X1"}]
    response = _response(
        {
            "accession": "P04637",
            "features": [
                {
                    "type": "EPITOPE",
                    "begin": 1,
                    "end": 10,
                    "evidences": evidences,
                    "xrefs": xrefs,
                }
            ],
        }
    )
    tool = EBIProteinsEpitopeTool({"name": "EBIProteins_get_epitopes"})
    with patch(
        "tooluniverse.ebi_proteins_epitope_tool.requests.get",
        return_value=response,
    ):
        result = tool.run({"accession": "P04637"})

    epitope = result["data"]["epitopes"][0]
    assert len(epitope["pmids"]) == 17
    assert epitope["pmid_count"] == 17
    assert epitope["evidence_count"] == 17
    assert epitope["evidences"] == evidences
    assert epitope["iedb_ids"] == ["20767"]
    assert epitope["xrefs"] == xrefs


def test_glygen_protein_detail_preserves_all_sites_and_gene_qualifiers():
    gene_names = [
        {"name": f"GENE-{index}", "type": "synonym", "evidence": [{"id": index}]}
        for index in range(7)
    ]
    sites = [
        {
            "start_pos": index,
            "residue": "Asn",
            "type": "N-linked",
            "subtype": "other",
            "evidence": [{"database": "PubMed", "id": str(index)}],
        }
        for index in range(77)
    ]
    tool = GlyGenTool(
        {
            "name": "GlyGen_get_glycoprotein",
            "fields": {"endpoint_type": "protein", "query_mode": "detail"},
        }
    )
    with patch(
        "tooluniverse.glygen_tool.requests.post",
        return_value=_response({"gene_names": gene_names, "glycosylation": sites}),
    ):
        result = tool.run({"uniprot_ac": "P14210"})

    data = result["data"]
    assert len(data["gene_names"]) == 7
    assert data["gene_name_details"] == gene_names
    assert len(data["glycosylation_sites"]) == 77
    assert data["returned_glycosylation_count"] == 77
    assert data["glycosylation_sites"][-1]["evidence"] == sites[-1]["evidence"]


def test_glygen_glycan_detail_preserves_all_associations_and_qualifiers():
    glycoproteins = [
        {
            "uniprot_canonical_ac": f"P{index:05d}-1",
            "start_pos": index,
            "tax_id": 9606,
            "evidence": [{"database": "PubMed", "id": str(index)}],
        }
        for index in range(54)
    ]
    species = [
        {
            "taxid": 9606,
            "name": "Homo sapiens",
            "annotation_category": "direct",
            "evidence": [{"database": "GlyGen", "id": "G1"}],
        }
    ]
    tool = GlyGenTool(
        {
            "name": "GlyGen_get_glycan",
            "fields": {"endpoint_type": "glycan", "query_mode": "detail"},
        }
    )
    with patch(
        "tooluniverse.glygen_tool.requests.post",
        return_value=_response({"species": species, "glycoprotein": glycoproteins}),
    ):
        result = tool.run({"glytoucan_ac": "G17689DH"})

    data = result["data"]
    assert len(data["glycoproteins"]) == 54
    assert data["returned_glycoprotein_count"] == 54
    assert data["glycoproteins"][-1]["start_pos"] == 53
    assert data["glycoproteins"][-1]["evidence"] == glycoproteins[-1]["evidence"]
    assert data["species"][0]["annotation_category"] == "direct"
    assert data["species"][0]["evidence"] == species[0]["evidence"]


def test_ncbi_variation_combines_all_allele_clinical_assertions():
    allele_annotations = []
    expected_accessions = []
    for annotation_index, count in enumerate((0, 14, 10, 23)):
        clinical = []
        for record_index in range(count):
            accession = f"RCV-{annotation_index}-{record_index}"
            expected_accessions.append(accession)
            clinical.append(
                {
                    "accession_version": accession,
                    "allele_id": 100 + annotation_index,
                    "clinical_significances": ["pathogenic"],
                    "disease_ids": [{"organization": "MONDO", "accession": "1"}],
                    "origins": ["somatic"],
                }
            )
        allele_annotations.append(
            {"clinical": clinical, "assembly_annotation": []}
        )

    tool = NCBIVariationTool(
        {
            "name": "NCBIVariation_rsid_lookup",
            "fields": {"endpoint_type": "rsid_lookup"},
        }
    )
    with patch(
        "tooluniverse.ncbi_variation_tool.requests.get",
        return_value=_response(
            {"primary_snapshot_data": {"allele_annotations": allele_annotations}}
        ),
    ):
        result = tool.run({"rsid": "rs121913529"})

    data = result["data"]
    assert data["clinical_significance_count"] == 47
    assert len(data["clinical_significance"]) == 47
    assert [record["accession"] for record in data["clinical_significance"]] == (
        expected_accessions
    )
    assert data["clinical_significance"][0]["allele_annotation_index"] == 1
    assert data["clinical_significance"][-1]["allele_annotation_index"] == 3
    assert data["clinical_significance"][-1]["disease_ids"][0]["organization"] == (
        "MONDO"
    )


def test_cellxgene_list_preserves_complete_collection_description():
    description = "single-cell atlas " * 100
    collection = {
        "collection_id": "collection-1",
        "description": description,
        "datasets": [],
    }
    tool = CellxGeneDiscoveryTool(
        {
            "name": "CxGDisc_list_collections",
            "fields": {"endpoint": "list_collections"},
        }
    )
    with patch(
        "tooluniverse.cellxgene_discovery_tool.requests.get",
        return_value=_response([collection]),
    ):
        result = tool.run({"limit": 1})

    returned = result["data"]["collections"][0]
    assert returned["description"] == description
    assert returned["description_length"] == len(description)


def test_cellxgene_collection_preserves_all_cell_types():
    cell_types = [{"label": f"cell-type-{index}"} for index in range(26)]
    collection = {
        "collection_id": "collection-1",
        "datasets": [
            {
                "dataset_id": "dataset-1",
                "title": "Integrated atlas",
                "cell_type": cell_types,
            }
        ],
    }
    tool = CellxGeneDiscoveryTool(
        {
            "name": "CxGDisc_get_collection",
            "fields": {"endpoint": "get_collection"},
        }
    )
    with patch(
        "tooluniverse.cellxgene_discovery_tool.requests.get",
        return_value=_response(collection),
    ):
        result = tool.run({"collection_id": "collection-1"})

    dataset = result["data"]["datasets"][0]
    assert dataset["cell_type_count"] == 26
    assert dataset["cell_types"] == [item["label"] for item in cell_types]
