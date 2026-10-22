"""Live regressions for the silent-failure research report.

These tests call public upstream services and are intentionally opt-in:

    TOOLUNIVERSE_RUN_LIVE_SILENT_FAILURES=1 pytest -q --no-cov \
        tests/integration/test_silent_failure_report_live.py

They verify semantics that mocked unit tests cannot: true upstream totals,
non-overlapping subsequent pages, query discrimination, and preservation of
annotations that were previously discarded by wrappers.
"""

import os
import json
from pathlib import Path

import pytest
from jsonschema import validate as validate_json_schema

from tooluniverse.tools import (
    BioImageArchive_search_bioimages,
    BioSamples_search_by_filter,
    Bioregistry_search_registries,
    Bgee_get_gene_expression,
    Bgee_search_genes,
    BVBRC_get_genome,
    BVBRC_search_amr,
    BVBRC_search_epitopes,
    BVBRC_search_genome_features,
    BVBRC_search_genomes,
    BVBRC_search_pathways,
    BVBRC_search_protein_structures,
    BVBRC_search_specialty_genes,
    BVBRC_search_subsystems,
    BVBRC_search_surveillance,
    BVBRC_search_taxonomy,
    CATH_list_funfams,
    CellMarker_search_by_cell_type,
    ChEBI_search,
    ClinGen_get_gene_validity,
    ClinGen_get_dosage_sensitivity,
    ClinGen_get_actionability_adult,
    ClinGen_get_actionability_pediatric,
    DisProt_get_entry,
    DisProt_search,
    Dfam_search_families,
    EnsemblLD_get_ld_variants,
    EnsemblPheno_get_by_term,
    EnsemblPheno_get_by_variant,
    InterPro_search_domains,
    KEGG_find_compound,
    KEGG_get_compound,
    MyChem_query_chemicals,
    MyGene_query_genes,
    MyVariant_query_variants,
    MGnify_list_analyses,
    MGnify_search_studies,
    PRIDE_search_proteomics,
    ProtVar_get_function,
    ProtVar_map_variant,
    RNAcentral_search,
    SASBDB_search,
    SwissLipids_search,
    UniParc_get_entry,
    UniParc_search,
    UniProt_get_entry_by_accession,
    UniProt_get_function_by_accession,
    UniProt_get_ptm_processing_by_accession,
    UniProt_get_subcellular_location_by_accession,
    UniProt_id_mapping,
    UniProtLocations_search,
    UniProtRef_search_diseases,
    UniProtRef_get_proteome,
    UniProtRef_search_keywords,
    UniProtRef_search_proteomes,
    UniProt_search,
    UniProt_search_proteomes,
    UniProt_search_uniparc,
    UniProt_search_uniref,
    UniProtTaxonomy_search,
    UniRef_search_clusters,
    ClinVar_search_variants,
    CxGDisc_list_collections,
    CxGDisc_search_datasets,
    ConoServer_search_conopeptides,
    ENAPortal_search_samples,
    ENAPortal_search_studies,
    EBIProteins_get_hpp_peptides,
    EBIProteins_get_domains_sites,
    EBIProteins_get_structural_features,
    Ensembl_get_assembly_info,
    Ensembl_get_species_info,
    EnsemblReg_get_constrained_elements,
    EnsemblReg_get_motif_features,
    EOL_get_page,
    GMrepo_get_phenotypes,
    GMrepo_search_species,
    HPO_search_terms,
    MaveDB_search_score_sets,
    OMA_get_hog,
    ReactomeContent_get_contained_events,
    ReactomeContent_get_enhanced_pathway,
    ReactomeContent_search,
    ReactomeInteractors_search_entity,
    SGD_get_gene,
    SGD_get_interactions,
    SGD_get_regulation,
    FinnGen_list_phenotypes,
    Ensembl_get_region_features,
    ensembl_get_variants,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("TOOLUNIVERSE_RUN_LIVE_SILENT_FAILURES") != "1",
        reason="set TOOLUNIVERSE_RUN_LIVE_SILENT_FAILURES=1 to call live APIs",
    ),
]


def _ids(records, key):
    return {record[key] for record in records if record.get(key) is not None}


_DATA_DIR = Path(__file__).parents[2] / "src" / "tooluniverse" / "data"
_CONFIG_FILES = (
    "bioimage_archive_tools.json",
    "biosamples_tools.json",
    "bioregistry_tools.json",
    "bgee_tools.json",
    "biothings_tools.json",
    "clinvar_tools.json",
    "cellxgene_discovery_tools.json",
    "cellmarker_tools.json",
    "cath_tools.json",
    "chebi_tools.json",
    "clingen_tools.json",
    "conoserver_tools.json",
    "ebi_proteins_ext_tools.json",
    "ebi_proteins_features_tools.json",
    "ensembl_info_tools.json",
    "ensembl_regulation_tools.json",
    "eol_tools.json",
    "bvbrc_tools.json",
    "disprot_tools.json",
    "dfam_tools.json",
    "ensembl_tools.json",
    "ensembl_ld_tools.json",
    "ensembl_overlap_tools.json",
    "ensembl_phenotype_tools.json",
    "ena_portal_tools.json",
    "gmrepo_tools.json",
    "hpo_tools.json",
    "interpro_tools.json",
    "kegg_ext_tools.json",
    "mavedb_tools.json",
    "finngen_tools.json",
    "mgnify_tools.json",
    "pride_tools.json",
    "protvar_tools.json",
    "oma_tools.json",
    "reactome_content_tools.json",
    "reactome_interactors_tools.json",
    "rnacentral_tools.json",
    "sasbdb_tools.json",
    "sgd_tools.json",
    "swisslipids_tools.json",
    "uniprot_tools.json",
)
_CONFIGS = {
    config["name"]: config
    for filename in _CONFIG_FILES
    for config in json.loads((_DATA_DIR / filename).read_text())
}


def _assert_return_schema(tool_name, result):
    """Validate the documented data envelope against the live payload."""

    schema = _CONFIGS[tool_name].get("return_schema")
    if schema:
        validate_json_schema(instance=result["data"], schema=schema)


def test_bvbrc_real_pagination_filters_and_complete_genome():
    first = BVBRC_search_genomes(
        keyword="Staphylococcus aureus",
        limit=2,
        offset=0,
        genome_status="WGS",
        genome_quality="Good",
        min_checkm_completeness=90,
    )
    second = BVBRC_search_genomes(
        keyword="Staphylococcus aureus",
        limit=2,
        offset=first["metadata"]["next_offset"],
        genome_status="WGS",
        genome_quality="Good",
        min_checkm_completeness=90,
    )

    assert first["status"] == second["status"] == "success"
    _assert_return_schema("BVBRC_search_genomes", first)
    assert first["metadata"]["total_results"] > len(first["data"])
    assert first["metadata"]["next_offset"] == 2
    assert _ids(first["data"], "genome_id").isdisjoint(
        _ids(second["data"], "genome_id")
    )
    assert all(record["checkm_completeness"] >= 90 for record in first["data"])
    assert all(record["genome_status"] == "WGS" for record in first["data"])
    assert all(record["genome_quality"] == "Good" for record in first["data"])

    genome = BVBRC_get_genome(
        genome_id="83332.12", include_related=True, related_limit=2
    )
    record = genome["data"]
    assert genome["status"] == "success"
    _assert_return_schema("BVBRC_get_genome", genome)
    assert record["genome_id"] == "83332.12"
    assert record["assembly_accession"] == "GCA_000195955.2"
    assert record["checkm_completeness"] == 100
    assert len(record) > 50
    for collection in ("amr", "specialty_genes"):
        related = record["related_records"][collection]
        page = genome["metadata"]["related_pagination"][collection]
        assert related
        assert all(item["genome_id"] == "83332.12" for item in related)
        assert page["total_results"] >= page["returned"] == len(related)
        assert page["next_offset"] == len(related)

    amr_first = BVBRC_search_amr(antibiotic="methicillin", limit=2, offset=0)
    amr_second = BVBRC_search_amr(
        antibiotic="methicillin",
        limit=2,
        offset=amr_first["metadata"]["next_offset"],
    )
    assert amr_first["metadata"]["total_results"] > len(amr_first["data"])
    _assert_return_schema("BVBRC_search_amr", amr_first)
    assert amr_first["data"] != amr_second["data"]

    specialty_first = BVBRC_search_specialty_genes(
        genome_id="83332.12", limit=2, offset=0
    )
    specialty_second = BVBRC_search_specialty_genes(
        genome_id="83332.12",
        limit=2,
        offset=specialty_first["metadata"]["next_offset"],
    )
    assert specialty_first["metadata"]["total_results"] > len(specialty_first["data"])
    _assert_return_schema("BVBRC_search_specialty_genes", specialty_first)
    assert _ids(specialty_first["data"], "feature_id").isdisjoint(
        _ids(specialty_second["data"], "feature_id")
    )


def test_disprot_real_query_semantics_and_region_pages():
    tp53 = DisProt_search(query="TP53", page_size=2, page=0)
    brca1 = DisProt_search(query="BRCA1", page_size=2, page=0)

    assert tp53["status"] == brca1["status"] == "success"
    _assert_return_schema("DisProt_search", tp53)
    assert _ids(tp53["data"], "acc") != _ids(brca1["data"], "acc")
    assert "P04637" in _ids(tp53["data"], "acc")
    assert "P38398" in _ids(brca1["data"], "acc")
    assert tp53["metadata"]["total_results"] > len(tp53["data"])

    first = DisProt_get_entry(accession="P04637", region_offset=0, region_limit=30)
    second = DisProt_get_entry(
        accession="P04637",
        region_offset=first["metadata"]["next_region_offset"],
        region_limit=30,
    )
    assert first["metadata"]["total_regions"] > len(first["data"]["regions"])
    _assert_return_schema("DisProt_get_entry", first)
    assert (
        first["metadata"]["reported_regions_counter"]
        >= first["metadata"]["total_regions"]
    )
    assert _ids(first["data"]["regions"], "region_id").isdisjoint(
        _ids(second["data"]["regions"], "region_id")
    )


def test_interpro_real_cursor_page_is_distinct():
    first = InterPro_search_domains(query="kinase", page_size=2)
    cursor = first["metadata"]["next_cursor"]
    second = InterPro_search_domains(query="kinase", page_size=2, cursor=cursor)

    assert first["status"] == second["status"] == "success"
    _assert_return_schema("InterPro_search_domains", first)
    assert first["metadata"]["total_results"] > len(first["data"])
    assert cursor
    first_ids = {item["metadata"]["accession"] for item in first["data"]}
    second_ids = {item["metadata"]["accession"] for item in second["data"]}
    assert first_ids.isdisjoint(second_ids)


def test_ensembl_real_local_pages_cover_distinct_variants():
    arguments = {
        "region": "17:7661779-7687538",
        "species": "homo_sapiens",
        "limit": 3,
    }
    first = ensembl_get_variants(**arguments, offset=0)
    second = ensembl_get_variants(**arguments, offset=first["metadata"]["next_offset"])

    assert first["status"] == second["status"] == "success"
    _assert_return_schema("ensembl_get_variants", first)
    assert first["metadata"]["total_results"] > len(first["data"])
    assert first["metadata"]["total_results"] == second["metadata"]["total_results"]
    assert _ids(first["data"], "id").isdisjoint(_ids(second["data"], "id"))


def test_protvar_real_structural_and_predictive_annotations():
    result = ProtVar_get_function(accession="P04637", position=175, variant_aa="H")
    data = result["data"]

    assert result["status"] == "success"
    _assert_return_schema("ProtVar_get_function", result)
    assert data["accession"] == "P04637"
    assert data["position"] == 175
    assert data["variant_aa"] == "H"
    assert data["pockets"]
    assert data["interactions"]
    assert data["conservation_score"] is not None
    assert data["foldx_predictions"]
    assert result["metadata"]["pocket_count"] == len(data["pockets"])
    assert result["metadata"]["prediction_fields_present"]["foldx"] is True


def test_uniprot_real_computational_publication_pages():
    first = UniProt_get_entry_by_accession(
        accession="P05067",
        compact=True,
        include_publications=True,
        publication_source="computational",
        publication_limit=2,
    )
    cursor = first["metadata"]["next_publication_cursor"]
    second = UniProt_get_entry_by_accession(
        accession="P05067",
        compact=True,
        include_publications=True,
        publication_source="computational",
        publication_limit=2,
        publication_cursor=cursor,
    )

    assert first["status"] == second["status"] == "success"
    _assert_return_schema("UniProt_get_entry_by_accession", first)
    assert first["metadata"]["publication_source"] == "computational"
    assert first["metadata"]["total_publications"] > 2
    assert first["metadata"]["publications_returned"] == 2
    assert cursor
    assert first["data"]["references"]
    assert (
        first["data"]["additional_publications"]
        != second["data"]["additional_publications"]
    )


def test_kegg_real_compound_preserves_unmodeled_sections():
    result = KEGG_get_compound(compound_id="C00002")
    data = result["data"]

    assert result["status"] == "success"
    _assert_return_schema("KEGG_get_compound", result)
    assert data["compound_id"] == "C00002"
    assert data["reactions"]
    assert data["modules"]
    assert data["networks"]
    assert len(data["atoms"]) > 30
    assert len(data["bonds"]) > 30
    for field in ("REACTION", "MODULE", "NETWORK", "ATOM", "BOND"):
        assert field in data["raw_fields"]
    assert data["raw_data"].startswith("ENTRY")
    assert result["metadata"]["all_upstream_fields_preserved"] is True


def test_remaining_bvbrc_searches_report_true_totals_and_reachable_pages():
    cases = [
        (
            "BVBRC_search_genome_features",
            lambda offset: BVBRC_search_genome_features(
                gene="mecA", limit=2, offset=offset
            ),
            "patric_id",
        ),
        (
            "BVBRC_search_epitopes",
            lambda offset: BVBRC_search_epitopes(
                taxon_id="2697049", limit=2, offset=offset
            ),
            "epitope_id",
        ),
        (
            "BVBRC_search_surveillance",
            lambda offset: BVBRC_search_surveillance(
                subtype="H5N1", limit=2, offset=offset
            ),
            "id",
        ),
        (
            "BVBRC_search_protein_structures",
            lambda offset: BVBRC_search_protein_structures(
                taxon_id="83332", limit=2, offset=offset
            ),
            "pdb_id",
        ),
        (
            "BVBRC_search_taxonomy",
            lambda offset: BVBRC_search_taxonomy(
                keyword="Staphylococcus", limit=2, offset=offset
            ),
            "taxon_id",
        ),
        (
            "BVBRC_search_pathways",
            lambda offset: BVBRC_search_pathways(
                genome_id="83332.12", limit=2, offset=offset
            ),
            "feature_id",
        ),
        (
            "BVBRC_search_subsystems",
            lambda offset: BVBRC_search_subsystems(
                genome_id="83332.12", limit=2, offset=offset
            ),
            "role_name",
        ),
    ]
    for tool_name, call, identifier in cases:
        first = call(0)
        second = call(first["metadata"]["next_offset"])
        assert first["status"] == second["status"] == "success"
        _assert_return_schema(tool_name, first)
        assert first["metadata"]["total_results"] > len(first["data"])
        assert first["metadata"]["next_offset"] == 2
        assert _ids(first["data"], identifier).isdisjoint(
            _ids(second["data"], identifier)
        )


def test_protvar_real_map_labels_predictions_as_nonclinical():
    result = ProtVar_map_variant(variant="P04637 R175H", assembly="GRCh38")
    _assert_return_schema("ProtVar_map_variant", result)
    canonical = next(
        item for item in result["data"]["isoform_mappings"] if item["canonical"]
    )
    prediction = canonical["alphamissense"]
    assert prediction["classification_scope"] == "model_prediction"
    assert prediction["is_clinical_classification"] is False
    assert prediction["class_thresholds"]["likely_pathogenic"] == "score > 0.564"
    assert (
        "not retrieved clinical classifications"
        in result["data"]["prediction_context"]["interpretation"]
    )


def test_uniprot_real_search_cursors_and_legacy_mapping_completeness():
    searches = [
        (
            "UniProt_search",
            lambda cursor=None: UniProt_search(
                query="beta-lactamase", limit=2, cursor=cursor
            ),
            "accession",
        ),
        (
            "UniProt_search_uniref",
            lambda cursor=None: UniProt_search_uniref(
                query="beta-lactamase", limit=2, cursor=cursor
            ),
            "id",
        ),
        (
            "UniProt_search_uniparc",
            lambda cursor=None: UniProt_search_uniparc(
                query="P04637", limit=2, cursor=cursor
            ),
            "uniParcId",
        ),
    ]
    for tool_name, call, identifier in searches:
        first = call()
        cursor = first["data"]["next_cursor"]
        second = call(cursor)
        _assert_return_schema(tool_name, first)
        assert first["data"]["total_results"] > first["data"]["returned"]
        assert cursor
        assert _ids(first["data"]["results"], identifier).isdisjoint(
            _ids(second["data"]["results"], identifier)
        )

    mapping = UniProt_id_mapping(
        ids=["P00533"],
        from_db="UniProtKB_AC-ID",
        to_db="PDB",
        max_wait_time=120,
        result_limit=500,
    )
    _assert_return_schema("UniProt_id_mapping", mapping)
    assert mapping["data"]["mapped_count"] > 25
    assert mapping["data"]["returned"] == mapping["data"]["mapped_count"]
    assert mapping["data"]["truncated"] is False


def test_uniprot_real_ptm_and_location_annotations_preserve_complete_semantics():
    ptm_features = UniProt_get_ptm_processing_by_accession(accession="P05067")
    validate_json_schema(
        instance=ptm_features,
        schema=_CONFIGS["UniProt_get_ptm_processing_by_accession"]["return_schema"],
    )
    feature_types = {feature["type"] for feature in ptm_features}
    assert len(ptm_features) > 40
    assert {
        "Signal",
        "Chain",
        "Peptide",
        "Modified residue",
        "Glycosylation",
        "Disulfide bond",
        "Cross-link",
    } <= feature_types

    locations = UniProt_get_subcellular_location_by_accession(accession="P04637")
    validate_json_schema(
        instance=locations,
        schema=_CONFIGS["UniProt_get_subcellular_location_by_accession"][
            "return_schema"
        ],
    )
    assert any(location["evidences"] for location in locations)
    assert any(location["location_id"] for location in locations)
    assert any(location["molecule"] == "Isoform 1" for location in locations)
    assert any(location["note"] for location in locations)

    functions = UniProt_get_function_by_accession(accession="P04637")
    validate_json_schema(
        instance=functions,
        schema=_CONFIGS["UniProt_get_function_by_accession"]["return_schema"],
    )
    assert len(functions) == 1
    assert any(
        evidence.get("source") == "PubMed" for evidence in functions[0]["evidences"]
    )
    assert len(functions[0]["evidences"]) >= 18


def test_independent_uniprot_searches_reach_distinct_cursor_pages():
    searches = [
        (
            lambda cursor=None: UniParc_search(
                query="gene:TP53 AND organism_id:9606", size=2, cursor=cursor
            ),
            "uniparc_id",
        ),
        (
            lambda cursor=None: UniRef_search_clusters(
                query="p53", cluster_type="UniRef90", size=2, cursor=cursor
            ),
            "cluster_id",
        ),
        (
            lambda cursor=None: UniProtTaxonomy_search(
                query="arabidopsis", size=2, cursor=cursor
            ),
            "taxon_id",
        ),
        (
            lambda cursor=None: UniProtLocations_search(
                query="membrane", size=2, cursor=cursor
            ),
            "id",
        ),
        (
            lambda cursor=None: UniProtRef_search_diseases(
                query="cancer", size=2, cursor=cursor
            ),
            "id",
        ),
        (
            lambda cursor=None: UniProtRef_search_keywords(
                query="kinase", size=2, cursor=cursor
            ),
            "id",
        ),
        (
            lambda cursor=None: UniProtRef_search_proteomes(
                query="Escherichia coli", size=2, cursor=cursor
            ),
            "id",
        ),
    ]
    for call, identifier in searches:
        first = call()
        cursor = first["metadata"]["next_cursor"]
        second = call(cursor)
        assert first["metadata"]["total_results"] > len(first["data"])
        assert first["metadata"]["returned"] == 2
        assert first["metadata"]["truncated"] is True
        assert cursor
        assert _ids(first["data"], identifier).isdisjoint(
            _ids(second["data"], identifier)
        )

    first = UniProt_search_proteomes(query="organism_name:escherichia coli", size=2)
    second = UniProt_search_proteomes(
        query="organism_name:escherichia coli",
        size=2,
        cursor=first["metadata"]["next_cursor"],
    )
    assert first["metadata"]["total_results"] > len(first["data"]["results"])
    assert first["metadata"]["returned"] == 2
    assert first["metadata"]["next_cursor"]
    assert _ids(first["data"]["results"], "id").isdisjoint(
        _ids(second["data"]["results"], "id")
    )


def test_uniparc_real_entry_exposes_all_active_xrefs_through_offsets():
    first = UniParc_get_entry(
        upi="UPI000002ED67", cross_reference_limit=25, cross_reference_offset=0
    )
    second = UniParc_get_entry(
        upi="UPI000002ED67",
        cross_reference_limit=25,
        cross_reference_offset=first["metadata"]["next_cross_reference_offset"],
    )
    assert first["metadata"]["active_cross_references"] > 500
    assert first["metadata"]["cross_references_returned"] == 25
    assert first["metadata"]["cross_references_truncated"] is True
    assert first["metadata"]["next_cross_reference_offset"] == 25
    assert _ids(first["data"]["cross_references"], "id").isdisjoint(
        _ids(second["data"]["cross_references"], "id")
    )


def test_uniprot_ref_real_proteome_total_covers_components_after_page_30():
    first = UniProtRef_get_proteome(
        proteome_id="UP000694402", component_offset=0, component_limit=30
    )
    second = UniProtRef_get_proteome(
        proteome_id="UP000694402",
        component_offset=first["metadata"]["next_component_offset"],
        component_limit=30,
    )
    assert first["metadata"]["total_components"] == 36
    assert first["metadata"]["components_truncated"] is True
    assert first["metadata"]["next_component_offset"] == 30
    assert len(second["data"]["components"]) == 6
    assert first["data"]["total_protein_count"] == 121708
    assert second["data"]["total_protein_count"] == 121708


def test_kegg_real_compound_search_reports_complete_total_and_next_page():
    first = KEGG_find_compound(formula="C6H12O6", max_results=2, offset=0)
    second = KEGG_find_compound(
        formula="C6H12O6", max_results=2, offset=first["data"]["next_offset"]
    )
    _assert_return_schema("KEGG_find_compound", first)
    assert first["data"]["total_results"] > first["data"]["count"]
    assert first["metadata"]["total_results"] == first["data"]["total_results"]
    assert _ids(first["data"]["compounds"], "compound_id").isdisjoint(
        _ids(second["data"]["compounds"], "compound_id")
    )


def test_third_wave_real_search_pages_are_reachable_and_distinct():
    biothings = [
        (
            "MyGene_query_genes",
            lambda offset: MyGene_query_genes(
                query="kinase",
                species="human",
                size=2,
                offset=offset,
                sort="entrezgene",
            ),
        ),
        (
            "MyVariant_query_variants",
            lambda offset: MyVariant_query_variants(
                query="dbsnp.rsid:rs123",
                size=2,
                offset=offset,
                sort="vcf.position",
            ),
        ),
        (
            "MyChem_query_chemicals",
            lambda offset: MyChem_query_chemicals(
                query="aspirin", size=2, offset=offset, sort="pubchem.cid"
            ),
        ),
    ]
    for tool_name, call in biothings:
        first = call(0)
        second = call(first["metadata"]["next_offset"])
        _assert_return_schema(tool_name, first)
        assert first["metadata"]["total_results"] > len(first["data"]["hits"])
        assert first["metadata"]["truncated"] is True
        assert first["metadata"]["next_offset"] == 2
        assert _ids(first["data"]["hits"], "_id").isdisjoint(
            _ids(second["data"]["hits"], "_id")
        )

    images_first = BioImageArchive_search_bioimages(
        query="microscopy", page_size=2, page=1
    )
    images_second = BioImageArchive_search_bioimages(
        query="microscopy", page_size=2, page=images_first["metadata"]["next_page"]
    )
    _assert_return_schema("BioImageArchive_search_bioimages", images_first)
    assert images_first["metadata"]["total_hits"] > len(images_first["data"])
    assert images_first["metadata"]["next_page"] == 2
    assert _ids(images_first["data"], "accession").isdisjoint(
        _ids(images_second["data"], "accession")
    )

    dfam_first = Dfam_search_families(name_prefix="Alu", limit=2, offset=0)
    dfam_second = Dfam_search_families(
        name_prefix="Alu", limit=2, offset=dfam_first["metadata"]["next_offset"]
    )
    _assert_return_schema("Dfam_search_families", dfam_first)
    assert dfam_first["metadata"]["total_count"] > len(dfam_first["data"])
    assert dfam_first["metadata"]["next_offset"] == 2
    assert _ids(dfam_first["data"], "accession").isdisjoint(
        _ids(dfam_second["data"], "accession")
    )


def test_third_wave_real_biological_archive_pages_and_schemas():
    rna_first = RNAcentral_search(query="let-7", page_size=2, page=1)
    rna_second = RNAcentral_search(
        query="let-7", page_size=2, page=rna_first["metadata"]["next_page"]
    )
    _assert_return_schema("RNAcentral_search", rna_first)
    assert rna_first["metadata"]["next_page"] == 2
    assert _ids(rna_first["data"]["results"], "rnacentral_id").isdisjoint(
        _ids(rna_second["data"]["results"], "rnacentral_id")
    )

    studies_first = MGnify_search_studies(search="gut", size=2, page=1)
    studies_second = MGnify_search_studies(
        search="gut", size=2, page=studies_first["metadata"]["next_page"]
    )
    _assert_return_schema("MGnify_search_studies", studies_first)
    assert studies_first["metadata"]["total_results"] > len(studies_first["data"])
    assert studies_first["metadata"]["total_pages"] >= 2
    assert _ids(studies_first["data"], "id").isdisjoint(
        _ids(studies_second["data"], "id")
    )

    analyses_first = MGnify_list_analyses(
        study_accession="MGYS00006862", size=2, page=1
    )
    analyses_second = MGnify_list_analyses(
        study_accession="MGYS00006862",
        size=2,
        page=analyses_first["metadata"]["next_page"],
    )
    _assert_return_schema("MGnify_list_analyses", analyses_first)
    assert analyses_first["metadata"]["total_results"] > len(analyses_first["data"])
    assert _ids(analyses_first["data"], "id").isdisjoint(
        _ids(analyses_second["data"], "id")
    )

    pride_first = PRIDE_search_proteomics(query="cancer", page_size=2, page=0)
    pride_second = PRIDE_search_proteomics(
        query="cancer", page_size=2, page=pride_first["metadata"]["next_page"]
    )
    _assert_return_schema("PRIDE_search_proteomics", pride_first)
    assert pride_first["metadata"]["total_results"] > len(pride_first["data"])
    assert _ids(pride_first["data"], "accession").isdisjoint(
        _ids(pride_second["data"], "accession")
    )

    clinvar_first = ClinVar_search_variants(gene="BRCA1", max_results=2, offset=0)
    clinvar_second = ClinVar_search_variants(
        gene="BRCA1", max_results=2, offset=clinvar_first["data"]["next_offset"]
    )
    _assert_return_schema("ClinVar_search_variants", clinvar_first)
    assert clinvar_first["data"]["total_count"] > len(
        clinvar_first["data"]["variant_ids"]
    )
    assert clinvar_first["data"]["next_offset"] == 2
    assert set(clinvar_first["data"]["variant_ids"]).isdisjoint(
        clinvar_second["data"]["variant_ids"]
    )


def test_third_wave_real_cell_atlas_biosample_and_ena_truncation_contracts():
    collections_first = CxGDisc_list_collections(limit=2, offset=0)
    collections_second = CxGDisc_list_collections(
        limit=2, offset=collections_first["data"]["next_offset"]
    )
    _assert_return_schema("CxGDisc_list_collections", collections_first)
    assert collections_first["data"]["total_collections"] > 2
    assert collections_first["data"]["truncated"] is True
    assert _ids(collections_first["data"]["collections"], "collection_id").isdisjoint(
        _ids(collections_second["data"]["collections"], "collection_id")
    )

    datasets_first = CxGDisc_search_datasets(organism="Homo sapiens", limit=2, offset=0)
    datasets_second = CxGDisc_search_datasets(
        organism="Homo sapiens",
        limit=2,
        offset=datasets_first["data"]["next_offset"],
    )
    _assert_return_schema("CxGDisc_search_datasets", datasets_first)
    assert datasets_first["data"]["total_matching"] > 2
    assert _ids(datasets_first["data"]["datasets"], "dataset_id").isdisjoint(
        _ids(datasets_second["data"]["datasets"], "dataset_id")
    )

    biosamples_first = BioSamples_search_by_filter(
        attribute="Organism", value="Homo sapiens", limit=2, page=0
    )
    biosamples_second = BioSamples_search_by_filter(
        attribute="Organism", value="Homo sapiens", limit=2, page=1
    )
    _assert_return_schema("BioSamples_search_by_filter", biosamples_first)
    assert biosamples_first["metadata"]["total_elements"] > 2
    assert biosamples_first["metadata"]["next_page"] == 1
    assert _ids(biosamples_first["data"], "accession").isdisjoint(
        _ids(biosamples_second["data"], "accession")
    )

    ena_studies = ENAPortal_search_studies(query='description="cell-free RNA"', limit=2)
    _assert_return_schema("ENAPortal_search_studies", ena_studies)
    assert ena_studies["metadata"]["total_results"] > len(ena_studies["data"])
    assert ena_studies["metadata"]["truncated"] is True
    assert ena_studies["metadata"]["suggested_limit"] == 4

    ena_samples = ENAPortal_search_samples(query="tax_tree(562)", limit=2)
    _assert_return_schema("ENAPortal_search_samples", ena_samples)
    assert ena_samples["metadata"]["total_results"] > len(ena_samples["data"])
    assert ena_samples["metadata"]["truncated"] is True


def test_continuous_scan_real_bulk_search_offsets_are_reachable():
    species_first = GMrepo_search_species(query="Bacteroides", limit=2, offset=0)
    species_second = GMrepo_search_species(
        query="Bacteroides",
        limit=2,
        offset=species_first["metadata"]["next_offset"],
    )
    _assert_return_schema("GMrepo_search_species", species_first)
    assert species_first["metadata"]["total_matches"] > len(species_first["data"])
    assert _ids(species_first["data"], "ncbi_taxon_id").isdisjoint(
        _ids(species_second["data"], "ncbi_taxon_id")
    )

    phenotypes_first = GMrepo_get_phenotypes(query="", limit=2, offset=0)
    phenotypes_second = GMrepo_get_phenotypes(
        query="",
        limit=2,
        offset=phenotypes_first["metadata"]["next_offset"],
    )
    _assert_return_schema("GMrepo_get_phenotypes", phenotypes_first)
    assert phenotypes_first["metadata"]["total_matches"] > len(phenotypes_first["data"])
    assert _ids(phenotypes_first["data"], "phenotype_id").isdisjoint(
        _ids(phenotypes_second["data"], "phenotype_id")
    )

    mavedb_first = MaveDB_search_score_sets(query="BRCA1", limit=2, offset=0)
    mavedb_second = MaveDB_search_score_sets(
        query="BRCA1",
        limit=2,
        offset=mavedb_first["metadata"]["next_offset"],
    )
    _assert_return_schema("MaveDB_search_score_sets", mavedb_first)
    assert mavedb_first["metadata"]["total_results"] > len(mavedb_first["data"])
    assert _ids(mavedb_first["data"], "urn").isdisjoint(
        _ids(mavedb_second["data"], "urn")
    )

    registry_first = Bioregistry_search_registries(query="protein", limit=2, offset=0)
    registry_second = Bioregistry_search_registries(
        query="protein",
        limit=2,
        offset=registry_first["data"]["next_offset"],
    )
    _assert_return_schema("Bioregistry_search_registries", registry_first)
    assert registry_first["data"]["total"] > len(registry_first["data"]["results"])
    assert _ids(registry_first["data"]["results"], "prefix").isdisjoint(
        _ids(registry_second["data"]["results"], "prefix")
    )

    cono_first = ConoServer_search_conopeptides(organism="Conus", limit=2, offset=0)
    cono_second = ConoServer_search_conopeptides(
        organism="Conus",
        limit=2,
        offset=cono_first["data"]["next_offset"],
    )
    _assert_return_schema("ConoServer_search_conopeptides", cono_first)
    assert cono_first["data"]["count"] > len(cono_first["data"]["results"])
    assert _ids(cono_first["data"]["results"], "id").isdisjoint(
        _ids(cono_second["data"]["results"], "id")
    )


def test_continuous_scan_real_lipid_and_scattering_catalog_offsets():
    lipids_first = SwissLipids_search(query="cholesterol", limit=2, offset=0)
    lipids_second = SwissLipids_search(
        query="cholesterol",
        limit=2,
        offset=lipids_first["metadata"]["next_offset"],
    )
    _assert_return_schema("SwissLipids_search", lipids_first)
    assert lipids_first["metadata"]["total_matches"] > len(lipids_first["data"])
    assert _ids(lipids_first["data"], "entity_id").isdisjoint(
        _ids(lipids_second["data"], "entity_id")
    )

    sasbdb_first = SASBDB_search(query="BSA", max_results=2, offset=0)
    sasbdb_second = SASBDB_search(
        query="BSA", max_results=2, offset=sasbdb_first["next_offset"]
    )
    _assert_return_schema("SASBDB_search", sasbdb_first)
    assert sasbdb_first["total_entries"] > len(sasbdb_first["data"])
    assert sasbdb_first["truncated"] is True
    assert _ids(sasbdb_first["data"], "code").isdisjoint(
        _ids(sasbdb_second["data"], "code")
    )


def test_continuous_scan_real_ontology_structure_and_gwas_offsets():
    finngen_first = FinnGen_list_phenotypes(query="diabetes", limit=2, offset=0)
    finngen_second = FinnGen_list_phenotypes(
        query="diabetes", limit=2, offset=finngen_first["metadata"]["next_offset"]
    )
    _assert_return_schema("FinnGen_list_phenotypes", finngen_first)
    assert finngen_first["metadata"]["total_matching"] > len(finngen_first["data"])
    assert _ids(finngen_first["data"], "phenocode").isdisjoint(
        _ids(finngen_second["data"], "phenocode")
    )

    cath_first = CATH_list_funfams(
        superfamily_id="1.10.510.10", max_results=2, offset=0
    )
    cath_second = CATH_list_funfams(
        superfamily_id="1.10.510.10",
        max_results=2,
        offset=cath_first["data"]["next_offset"],
    )
    _assert_return_schema("CATH_list_funfams", cath_first)
    assert cath_first["data"]["total_funfams"] > len(cath_first["data"]["funfams"])
    assert _ids(cath_first["data"]["funfams"], "funfam_number").isdisjoint(
        _ids(cath_second["data"]["funfams"], "funfam_number")
    )

    hpo_first = HPO_search_terms(query="seizure", max_results=2, offset=0)
    hpo_second = HPO_search_terms(
        query="seizure",
        max_results=2,
        offset=hpo_first["metadata"]["next_offset"],
    )
    _assert_return_schema("HPO_search_terms", hpo_first)
    assert hpo_first["metadata"]["total_available"] > len(hpo_first["data"])
    assert _ids(hpo_first["data"], "id").isdisjoint(_ids(hpo_second["data"], "id"))

    ld_first = EnsemblLD_get_ld_variants(
        variant_id="rs1042779",
        population="1000GENOMES:phase_3:KHV",
        limit=2,
        offset=0,
    )
    ld_second = EnsemblLD_get_ld_variants(
        variant_id="rs1042779",
        population="1000GENOMES:phase_3:KHV",
        limit=2,
        offset=ld_first["data"]["next_offset"],
    )
    _assert_return_schema("EnsemblLD_get_ld_variants", ld_first)
    assert ld_first["data"]["total_ld_count"] > len(ld_first["data"]["ld_variants"])
    assert _ids(ld_first["data"]["ld_variants"], "variant2").isdisjoint(
        _ids(ld_second["data"]["ld_variants"], "variant2")
    )

    chebi_first = ChEBI_search(query="glucose", limit=2, offset=0)
    chebi_second = ChEBI_search(
        query="glucose", limit=2, offset=chebi_first["data"]["next_offset"]
    )
    _assert_return_schema("ChEBI_search", chebi_first)
    assert chebi_first["data"]["total_matches"] > len(chebi_first["data"]["compounds"])
    assert _ids(chebi_first["data"]["compounds"], "chebi_accession").isdisjoint(
        _ids(chebi_second["data"]["compounds"], "chebi_accession")
    )


def test_continuous_scan_real_ensembl_hard_caps_are_pageable():
    term_first = EnsemblPheno_get_by_term(term="Alzheimer disease", limit=2, offset=0)
    term_second = EnsemblPheno_get_by_term(
        term="Alzheimer disease", limit=2, offset=term_first["data"]["next_offset"]
    )
    _assert_return_schema("EnsemblPheno_get_by_term", term_first)
    assert term_first["data"]["association_count"] > len(
        term_first["data"]["associations"]
    )
    assert _ids(term_first["data"]["associations"], "variant").isdisjoint(
        _ids(term_second["data"]["associations"], "variant")
    )

    variant_first = EnsemblPheno_get_by_variant(
        variant_id="rs429358", limit=2, offset=0
    )
    variant_second = EnsemblPheno_get_by_variant(
        variant_id="rs429358",
        limit=2,
        offset=variant_first["data"]["next_offset"],
    )
    _assert_return_schema("EnsemblPheno_get_by_variant", variant_first)
    assert variant_first["data"]["phenotype_count"] > len(
        variant_first["data"]["phenotypes"]
    )
    first_traits = {
        (item.get("trait"), item.get("study"))
        for item in variant_first["data"]["phenotypes"]
    }
    second_traits = {
        (item.get("trait"), item.get("study"))
        for item in variant_second["data"]["phenotypes"]
    }
    assert first_traits.isdisjoint(second_traits)

    region_first = Ensembl_get_region_features(
        region="7:140424943-140524564",
        feature_types="gene,regulatory,constrained",
        limit=5,
        offset=0,
    )
    region_second = Ensembl_get_region_features(
        region="7:140424943-140524564",
        feature_types="gene,regulatory,constrained",
        limit=5,
        offset=region_first["data"]["next_offset"],
    )
    _assert_return_schema("Ensembl_get_region_features", region_first)
    assert region_first["data"]["total_features"] > len(
        region_first["data"]["features"]
    )
    first_features = {
        (item.get("feature_type"), item.get("id"), item.get("start"), item.get("end"))
        for item in region_first["data"]["features"]
    }
    second_features = {
        (item.get("feature_type"), item.get("id"), item.get("start"), item.get("end"))
        for item in region_second["data"]["features"]
    }
    assert first_features.isdisjoint(second_features)


def test_continuous_scan_real_clingen_catalog_and_empty_argument_cli_path():
    first = ClinGen_get_gene_validity(limit=2, offset=0)
    second = ClinGen_get_gene_validity(limit=2, offset=first["next_offset"])

    _assert_return_schema("ClinGen_get_gene_validity", first)
    assert first["total"] > len(first["data"])
    assert first["truncated"] is True
    assert _ids(first["data"], "GENE SYMBOL").isdisjoint(
        _ids(second["data"], "GENE SYMBOL")
    )

    dosage_first = ClinGen_get_dosage_sensitivity(limit=2, offset=0)
    dosage_second = ClinGen_get_dosage_sensitivity(
        limit=2, offset=dosage_first["next_offset"]
    )
    _assert_return_schema("ClinGen_get_dosage_sensitivity", dosage_first)
    assert dosage_first["total"] > len(dosage_first["data"])
    assert _ids(dosage_first["data"], "GENE SYMBOL").isdisjoint(
        _ids(dosage_second["data"], "GENE SYMBOL")
    )

    for tool_name, tool in (
        ("ClinGen_get_actionability_adult", ClinGen_get_actionability_adult),
        ("ClinGen_get_actionability_pediatric", ClinGen_get_actionability_pediatric),
    ):
        action_first = tool(limit=2, offset=0)
        action_second = tool(limit=2, offset=action_first["next_offset"])
        _assert_return_schema(tool_name, action_first)
        assert action_first["total"] > len(action_first["data"])
        first_keys = {
            (item.get("docId"), item.get("outcome"), item.get("intervention"))
            for item in action_first["data"]
        }
        second_keys = {
            (item.get("docId"), item.get("outcome"), item.get("intervention"))
            for item in action_second["data"]
        }
        assert first_keys.isdisjoint(second_keys)


@pytest.mark.timeout(240)
def test_continuous_scan_real_bgee_ebi_and_cellmarker_offsets():
    bgee_first = Bgee_search_genes(query="kinase", species_id="9606", limit=3, offset=0)
    bgee_second = Bgee_search_genes(
        query="kinase",
        species_id="9606",
        limit=3,
        offset=bgee_first["metadata"]["next_offset"],
    )
    _assert_return_schema("Bgee_search_genes", bgee_first)
    assert bgee_first["metadata"]["total_matches"] > len(bgee_first["data"])
    assert bgee_first["metadata"]["upstream_truncated"] is False
    assert _ids(bgee_first["data"], "gene_id").isdisjoint(
        _ids(bgee_second["data"], "gene_id")
    )

    # This endpoint recomputes the complete expression call set on every
    # request and can be slow.  A single real page beyond the old hard cap is
    # sufficient to prove that offset 50 is now reachable without doubling
    # the expensive upstream request.
    expression_page = Bgee_get_gene_expression(
        gene_id="ENSG00000141510",
        species_id="9606",
        limit=3,
        offset=50,
    )
    _assert_return_schema("Bgee_get_gene_expression", expression_page)
    assert expression_page["metadata"]["total_calls"] > 53
    assert expression_page["metadata"]["offset"] == 50
    assert len(expression_page["data"]) == 3

    hpp_first = EBIProteins_get_hpp_peptides(accession="P04637", limit=3, offset=0)
    hpp_second = EBIProteins_get_hpp_peptides(
        accession="P04637", limit=3, offset=hpp_first["data"]["next_offset"]
    )
    _assert_return_schema("EBIProteins_get_hpp_peptides", hpp_first)
    assert hpp_first["data"]["total_peptides"] > len(hpp_first["data"]["peptides"])
    first_peptides = {
        (item.get("peptide"), item.get("position_start"), item.get("position_end"))
        for item in hpp_first["data"]["peptides"]
    }
    second_peptides = {
        (item.get("peptide"), item.get("position_start"), item.get("position_end"))
        for item in hpp_second["data"]["peptides"]
    }
    assert first_peptides.isdisjoint(second_peptides)

    cells_first = CellMarker_search_by_cell_type(
        cell_name="T cell", species="Human", limit=3, offset=0
    )
    cells_second = CellMarker_search_by_cell_type(
        cell_name="T cell",
        species="Human",
        limit=3,
        offset=cells_first["data"]["next_offset"],
    )
    _assert_return_schema("CellMarker_search_by_cell_type", cells_first)
    assert cells_first["data"]["total_records"] > len(cells_first["data"]["records"])
    assert all(
        "Fat cell" not in item["cell_name"] and "Mast cell" not in item["cell_name"]
        for item in cells_first["data"]["records"] + cells_second["data"]["records"]
    )
    first_cells = {
        (
            item.get("tissue_type"),
            item.get("cell_name"),
            item.get("cell_marker"),
            item.get("source"),
        )
        for item in cells_first["data"]["records"]
    }
    second_cells = {
        (
            item.get("tissue_type"),
            item.get("cell_name"),
            item.get("cell_marker"),
            item.get("source"),
        )
        for item in cells_second["data"]["records"]
    }
    assert first_cells.isdisjoint(second_cells)


@pytest.mark.timeout(300)
def test_continuous_scan_real_ensembl_catalog_and_nested_entry_pages():
    species = Ensembl_get_species_info(limit=3, offset=50)
    _assert_return_schema("Ensembl_get_species_info", species)
    assert species["data"]["total_species"] == species["data"]["matched_species"]
    assert species["data"]["matched_species"] > 53
    assert species["data"]["returned_species"] == 3
    assert species["data"]["next_offset"] == 53

    chicken = Ensembl_get_assembly_info(species="gallus_gallus")
    _assert_return_schema("Ensembl_get_assembly_info", chicken)
    assert chicken["data"]["total_chromosomes"] == 42
    assert len(chicken["data"]["chromosomes"]) == 42

    entry = UniProt_get_entry_by_accession(
        accession="P04637",
        include_publications=False,
        comment_limit=2,
        comment_offset=25,
        feature_limit=2,
        feature_offset=100,
        reference_limit=2,
        reference_offset=25,
    )
    _assert_return_schema("UniProt_get_entry_by_accession", entry)
    assert entry["metadata"]["comments_total"] > 27
    assert entry["metadata"]["features_total"] > 102
    assert entry["metadata"]["references_total"] > 27
    assert entry["metadata"]["features_next_offset"] == 102
    assert any(
        "featureId" in feature or "alternativeSequence" in feature
        for feature in entry["data"]["features"]
    )


@pytest.mark.timeout(300)
def test_continuous_scan_real_ensembl_regulation_pages_after_200():
    motif = EnsemblReg_get_motif_features(
        region="17:7000000-8000000", limit=3, offset=200
    )
    constrained = EnsemblReg_get_constrained_elements(
        region="17:7000000-8000000", limit=3, offset=200
    )
    _assert_return_schema("EnsemblReg_get_motif_features", motif)
    _assert_return_schema("EnsemblReg_get_constrained_elements", constrained)
    assert motif["data"]["motif_count"] > 203
    assert motif["data"]["next_offset"] == 203
    assert constrained["data"]["element_count"] > 203
    assert constrained["data"]["next_offset"] == 203


@pytest.mark.timeout(300)
def test_continuous_scan_real_reactome_grouped_and_local_pages():
    pathways = ReactomeContent_search(query="cell cycle", limit=3, offset=10)
    assert pathways["data"]["total_results"] > 13
    assert pathways["data"]["next_offset"] == 13

    entities = ReactomeInteractors_search_entity(
        query="kinase", limit=3, offset=50
    )
    assert entities["metadata"]["total_matches"] > 1000
    assert entities["metadata"]["next_offset"] == 53
    assert len(entities["data"]) > 3  # three rows per still-active result group
    assert all(group["returned"] <= 3 for group in entities["metadata"]["result_groups"])

    events = ReactomeContent_get_contained_events(
        identifier="R-HSA-69278", reaction_limit=3, reaction_offset=50
    )
    assert events["data"]["reaction_count"] > 53
    assert events["data"]["next_reaction_offset"] == 53

    enhanced = ReactomeContent_get_enhanced_pathway(identifier="R-HSA-109581")
    assert enhanced["data"]["summation_characters"] > 2000
    assert len(enhanced["data"]["summation"]) == enhanced["data"][
        "summation_characters"
    ]


@pytest.mark.timeout(300)
def test_continuous_scan_real_eol_sgd_ebi_and_oma_nested_completeness():
    eol = EOL_get_page(
        page_id=327955,
        images_per_page=0,
        texts_per_page=0,
        common_name_limit=2,
        common_name_offset=20,
        synonym_limit=2,
        synonym_offset=20,
        classification_limit=2,
        classification_offset=15,
    )
    assert eol["metadata"]["num_common_names"] > 22
    assert eol["metadata"]["num_synonyms"] > 22
    assert eol["metadata"]["num_classifications"] > 17
    assert eol["metadata"]["next_common_name_offset"] == 22

    aliases = SGD_get_gene(
        sgd_id="S000000364", alias_limit=2, alias_offset=10
    )
    interactions = SGD_get_interactions(
        sgd_id="S000000364", limit=2, offset=50
    )
    regulation = SGD_get_regulation(
        sgd_id="S000000364", limit=2, offset=100
    )
    assert aliases["metadata"]["total_aliases"] > 12
    assert aliases["metadata"]["next_alias_offset"] == 12
    assert interactions["metadata"]["total_results"] > 52
    assert interactions["metadata"]["next_offset"] == 52
    assert regulation["metadata"]["total_results"] > 102
    assert regulation["metadata"]["next_offset"] == 102

    structural = EBIProteins_get_structural_features(
        accession="P00533", limit=2, offset=100
    )
    domains = EBIProteins_get_domains_sites(accession="P00533", limit=20)
    assert structural["data"]["total_features"] > 102
    assert structural["data"]["next_offset"] == 102
    assert max(
        len(feature.get("evidences", [])) for feature in domains["data"]["features"]
    ) > 3

    hog = OMA_get_hog(hog_id="HOG:F0782425")
    root = hog["data"][0]
    assert root["children_hogs_count"] == len(root["children_hogs"]) > 10
    assert root["alternative_levels_count"] == len(root["alternative_levels"]) > 10
    assert max(
        child["alternative_levels_count"] for child in root["children_hogs"]
    ) > 5
