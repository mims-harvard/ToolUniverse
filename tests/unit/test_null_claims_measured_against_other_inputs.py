"""The 111 remaining `type: "null"` result fields, measured against other inputs.

#843 and the commit before this one widened the declarations whose real type
could be measured from the tool's own test_examples, and from a sibling tool
that typed the same field. Both are exhausted. What is left is the case where
the example simply never reaches the value: a cryo-EM field on an X-ray entry,
a pathology note on a blood sample, a comet prefix on an asteroid.

So each tool was run over inputs chosen to reach it. 26 of the 111 then showed
a value, every one recorded below with the input that produced it:

    get_citation_info_by_pdb_id      ORCID ids, MeSH lineage         6VXX
    get_em_3d_fitting_and_recon..    algorithm 'FOURIER SPACE'       7A4M
                                     method 'SIRT', fitting list     3J3Q
                                     pixel sizes 0.637, details      5A1A
    get_assembly_info_by_pdb_id      method_details 'PISA'           5A1A
    get_host_organism_by_pdb_id      host_org_common_name 'Human'    6VXX
    get_structure_determination..    version '5.8.0352'              8SPL
                                     type 'package'                  2RH1
    get_core_refinement_statistics   bsol 78.49, ksol 0.33           3EML
    CryoET_get_dataset               gridPreparation                 dataset 10000
    CryoET_list_tomograms            processingSoftware 'tomo3D'     run 5000
    GTEx_get_sample_info             pathologyNotes, autolysisScore  Liver
    HPA_get_gene_basic_info..        RNA tissue specific nTPM        EGFR
    NASASBDB_get_body                object->prefix 'P'              1P/Halley
                                     orbit->comment                  Bennu
    odphp_myhealthfinder             RelatedItems, Sections          age 35, pregnant
    ols_get_ontology_info            domain, repository              go
    DrugSafetyAnalyzer               molecular_properties            Aspirin

GTEx is the clearest case: pathologyNotes and autolysisScore were non-null for
all 20 Liver samples measured. The declaration was null only because the one
example asked for Whole_Blood.

Each tool gained the input that reaches the value as a test_example, and all 14
of those fail on the parent commit, which is what makes them regression tests
rather than decoration.

Adding them exposed 12 more faults of the opposite kind, in four containers
where a field is declared non-null and the API leaves it empty. Those were not
guessed either -- every field of each container was measured across all the
inputs above:

    em_3d_reconstruction  resolution, resolution_method, num_particles
    safety_literature     pmid, abstract, doi, doi_url, year
    NASASBDB orbit        n_del_obs_used, n_dop_obs_used, condition_code
    odphp                 Sections/PlainSections Title

DrugSafetyAnalyzer was already failing its own test_example on that count,
before any input was added here.

The 85 that remain measured null on every input tried, and are left alone,
because nothing measured says what they hold. Three groups are worth naming,
since they are not all the same problem:

  - 9 are accurate and will stay so. em_3d_reconstruction's
    magnification_calibration, num_class_averages and refinement_type, and
    NASASBDB's orbit->two_body, not_valid_before and not_valid_after, were null
    for every entry and body probed (11 and 9 respectively).
  - some are unreachable through the tool rather than absent upstream.
    InterPro_get_domain_details asks only /entry/interpro/, so `integrated`,
    `wikipedia` and `set_info` can never be filled, while the raw API answers
    integrated='IPR000719', a wikipedia array and set_info={'accession':
    'CL0016'} for pfam/PF00069. InterPro_search_entries declares
    protein_count, structure_count and taxa_count and never requests
    extra_fields=counters, which returns proteins=37487.
  - two are the tool dropping what the API sent, which is a projection fault
    and not a schema one. ols_get_ontology_info reports version and
    number_of_terms as null while OLS answers numberOfClasses='85169' and
    owl#versionInfo='2026-07-26'; the model declares neither alias.

Those three groups are each their own fix and are not made here.
"""

import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _tool(stem, name):
    for entry in json.loads((DATA / f"{stem}.json").read_text()):
        if entry.get("name") == name:
            return entry
    raise AssertionError(f"{name} not in {stem}.json")


def _step(node, seg):
    """One path segment, looking through oneOf/anyOf/allOf wrappers."""
    if not isinstance(node, dict):
        return None
    if seg == "*":
        found = node.get("items")
    else:
        found = (node.get("properties") or {}).get(seg)
    if found is not None:
        return found
    for keyword in ("oneOf", "anyOf", "allOf"):
        for branch in node.get(keyword) or []:
            found = _step(branch, seg)
            if found is not None:
                return found
    return None


def _decl(schema, path):
    """The declaration at a schema path like 'a->*->b'."""
    node = schema
    for seg in path.split("->"):
        node = _step(node, seg)
        if node is None:
            return None
    return node


def _types(schema, path):
    decl = _decl(schema, path)
    assert decl is not None, f"{path} is not declared"
    declared = decl.get("type")
    return set(declared) if isinstance(declared, list) else {declared}


EM = "data->entries->*->em_3d_reconstruction->*"

# (stem, tool, path, expected types, the input that measured the non-null value)
MEASURED = [
    (
        "rcsb_pdb_tools",
        "get_citation_info_by_pdb_id",
        "data->entries->*->rcsb_primary_citation->rcsb_ORCID_identifiers",
        {"array", "null"},
        "6VXX",
    ),
    (
        "rcsb_pdb_tools",
        "get_citation_info_by_pdb_id",
        "data->entries->*->pubmed->rcsb_pubmed_mesh_descriptors_lineage",
        {"array", "null"},
        "6VXX",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        "data->entries->*->em_3d_fitting_list",
        {"array", "null"},
        "3J3Q",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->algorithm",
        {"string", "null"},
        "7A4M",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->method",
        {"string", "null"},
        "3J3Q",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->details",
        {"string", "null"},
        "5A1A",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->nominal_pixel_size",
        {"number", "null"},
        "5A1A",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->actual_pixel_size",
        {"number", "null"},
        "5A1A",
    ),
    (
        "rcsb_pdb_tools",
        "get_assembly_info_by_pdb_id",
        "data->entries->*->assemblies->*->pdbx_struct_assembly->method_details",
        {"string", "null"},
        "5A1A",
    ),
    (
        "rcsb_pdb_tools",
        "get_host_organism_by_pdb_id",
        "data->entries->*->polymer_entities->*->entity_src_gen->*->host_org_common_name",
        {"string", "null"},
        "6VXX",
    ),
    (
        "rcsb_pdb_tools",
        "get_structure_determination_software_by_pdb_id",
        "data->entries->*->software->*->version",
        {"string", "null"},
        "8SPL",
    ),
    (
        "rcsb_pdb_tools",
        "get_structure_determination_software_by_pdb_id",
        "data->entries->*->software->*->type",
        {"string", "null"},
        "2RH1",
    ),
    (
        "rcsb_pdb_tools",
        "get_core_refinement_statistics",
        "data->entries->*->refine->*->solvent_model_param_bsol",
        {"number", "null"},
        "3EML",
    ),
    (
        "rcsb_pdb_tools",
        "get_core_refinement_statistics",
        "data->entries->*->refine->*->solvent_model_param_ksol",
        {"number", "null"},
        "3EML",
    ),
    (
        "compose_tools",
        "DrugSafetyAnalyzer",
        "molecular_properties",
        {"object", "null"},
        "Aspirin",
    ),
    (
        "cryoet_tools",
        "CryoET_get_dataset",
        "dataset->gridPreparation",
        {"string", "null"},
        "dataset 10000",
    ),
    (
        "cryoet_tools",
        "CryoET_list_tomograms",
        "tomograms->*->processingSoftware",
        {"string", "null"},
        "run 5000",
    ),
    (
        "gtex_v2_tools",
        "GTEx_get_sample_info",
        "*->pathologyNotes",
        {"string", "null"},
        "Liver",
    ),
    (
        "gtex_v2_tools",
        "GTEx_get_sample_info",
        "*->autolysisScore",
        {"string", "null"},
        "Liver",
    ),
    (
        "hpa_tools",
        "HPA_get_gene_basic_info_by_ensembl_id",
        "RNA tissue specific nTPM",
        {"object", "null"},
        "ENSG00000146648",
    ),
    (
        "nasa_sbdb_tools",
        "NASASBDB_get_body",
        "orbit->comment",
        {"string", "null"},
        "Bennu",
    ),
    (
        "nasa_sbdb_tools",
        "NASASBDB_get_body",
        "object->prefix",
        {"string", "null"},
        "1P",
    ),
    (
        "odphp_tools",
        "odphp_myhealthfinder",
        "Callouts->All->Resource->*->RelatedItems",
        {"object", "null"},
        "age 35 pregnant",
    ),
    (
        "odphp_tools",
        "odphp_myhealthfinder",
        "Callouts->All->Resource->*->Sections",
        {"object", "null"},
        "age 35 pregnant",
    ),
    ("ols_tools", "ols_get_ontology_info", "domain", {"string", "null"}, "go"),
    ("ols_tools", "ols_get_ontology_info", "repository", {"string", "null"}, "go"),
]


@pytest.mark.parametrize(
    "stem,tool,path,expected,source",
    MEASURED,
    ids=[f"{t}:{p.split('->')[-1]}" for _, t, p, _, _ in MEASURED],
)
def test_a_measured_field_is_no_longer_declared_null_only(
    stem, tool, path, expected, source
):
    declared = _types(_tool(stem, tool)["return_schema"], path)
    assert declared == expected, (
        f"{tool} {path} declares {sorted(declared)}; measured {sorted(expected)} on {source}"
    )


# The opposite error, found by adding the inputs above.
NULLABLE_AFTER_ALL = [
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->resolution",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->resolution_method",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->num_particles",
    ),
    ("compose_tools", "DrugSafetyAnalyzer", "safety_literature->data->*->year"),
    ("compose_tools", "DrugSafetyAnalyzer", "safety_literature->data->*->pmid"),
    ("compose_tools", "DrugSafetyAnalyzer", "safety_literature->data->*->abstract"),
    ("compose_tools", "DrugSafetyAnalyzer", "safety_literature->data->*->doi"),
    ("compose_tools", "DrugSafetyAnalyzer", "safety_literature->data->*->doi_url"),
    ("nasa_sbdb_tools", "NASASBDB_get_body", "orbit->n_del_obs_used"),
    ("nasa_sbdb_tools", "NASASBDB_get_body", "orbit->n_dop_obs_used"),
    ("nasa_sbdb_tools", "NASASBDB_get_body", "orbit->condition_code"),
    (
        "odphp_tools",
        "odphp_myhealthfinder",
        "Resources->All->Resource->*->Sections->section->*->Title",
    ),
    (
        "odphp_tools",
        "odphp_myhealthfinder",
        "Resources->All->Resource->*->PlainSections->*->Title",
    ),
]


@pytest.mark.parametrize(
    "stem,tool,path",
    NULLABLE_AFTER_ALL,
    ids=[f"{t}:{p.split('->')[-1]}" for _, t, p in NULLABLE_AFTER_ALL],
)
def test_a_field_the_api_leaves_empty_admits_null(stem, tool, path):
    declared = _types(_tool(stem, tool)["return_schema"], path)
    assert "null" in declared, (
        f"{tool} {path} declares {sorted(declared)} and was measured null"
    )
    assert declared - {"null"}, f"{tool} {path} lost its real type"


# The input that reaches the value, kept as a test_example so the sweep sees it.
REACHING_EXAMPLES = [
    ("rcsb_pdb_tools", "get_citation_info_by_pdb_id", {"pdb_id": "6VXX"}),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        {"pdb_id": "3J3Q"},
    ),
    ("rcsb_pdb_tools", "get_assembly_info_by_pdb_id", {"pdb_id": "5A1A"}),
    ("rcsb_pdb_tools", "get_host_organism_by_pdb_id", {"pdb_id": "6VXX"}),
    (
        "rcsb_pdb_tools",
        "get_structure_determination_software_by_pdb_id",
        {"pdb_id": "2RH1"},
    ),
    ("rcsb_pdb_tools", "get_core_refinement_statistics", {"pdb_id": "3EML"}),
    (
        "cryoet_tools",
        "CryoET_get_dataset",
        {"operation": "get_dataset", "dataset_id": 10000},
    ),
    (
        "cryoet_tools",
        "CryoET_list_tomograms",
        {"operation": "list_tomograms", "run_id": 5000},
    ),
    (
        "gtex_v2_tools",
        "GTEx_get_sample_info",
        {
            "operation": "get_sample_info",
            "tissue_site_detail_id": ["Liver"],
            "items_per_page": 20,
        },
    ),
    (
        "hpa_tools",
        "HPA_get_gene_basic_info_by_ensembl_id",
        {"ensembl_id": "ENSG00000146648"},
    ),
    ("nasa_sbdb_tools", "NASASBDB_get_body", {"sstr": "1P", "phys-par": "true"}),
    ("nasa_sbdb_tools", "NASASBDB_get_body", {"sstr": "Bennu", "phys-par": "true"}),
    (
        "odphp_tools",
        "odphp_myhealthfinder",
        {
            "lang": "en",
            "age": 35,
            "sex": "female",
            "pregnant": "yes",
            "strip_html": True,
        },
    ),
    ("ols_tools", "ols_get_ontology_info", {"ontology_id": "go"}),
]


@pytest.mark.parametrize(
    "stem,tool,example",
    REACHING_EXAMPLES,
    ids=[f"{t}:{i}" for i, (_, t, _) in enumerate(REACHING_EXAMPLES)],
)
def test_the_reaching_input_is_a_test_example(stem, tool, example):
    assert example in _tool(stem, tool).get("test_examples", [])


ALWAYS_NULL_AND_LEFT_ALONE = [
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->magnification_calibration",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->num_class_averages",
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->refinement_type",
    ),
    ("nasa_sbdb_tools", "NASASBDB_get_body", "orbit->two_body"),
    ("nasa_sbdb_tools", "NASASBDB_get_body", "orbit->not_valid_before"),
    ("nasa_sbdb_tools", "NASASBDB_get_body", "orbit->not_valid_after"),
]


@pytest.mark.parametrize(
    "stem,tool,path",
    ALWAYS_NULL_AND_LEFT_ALONE,
    ids=[f"{t}:{p.split('->')[-1]}" for _, t, p in ALWAYS_NULL_AND_LEFT_ALONE],
)
def test_a_field_measured_null_everywhere_is_not_guessed_at(stem, tool, path):
    """Null on every entry and body probed. Widening these to a type nobody has
    observed would read as fixed and fail exactly as before."""
    assert _types(_tool(stem, tool)["return_schema"], path) == {"null"}
