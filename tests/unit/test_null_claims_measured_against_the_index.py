"""The null declarations left after #843's third commit, settled by asking the
authoritative index rather than by sampling.

The round before this one measured each field by running the tool over inputs
chosen to reach it, and left 85 declarations alone because every input tried
returned null. That reasoning has a hole, and four fields fell through it: a
field can be populated for 197 entries out of 37,607 and still be null in every
one of eleven you happen to look at.

Three of the databases involved will answer the question directly. RCSB's
search API reports how many entries populate an attribute, and names them; JPL's
small-body query API does the same across 1.4 million bodies. One request each
replaces any amount of sampling:

    em_3d_reconstruction.num_class_averages        3,934 of 37,607 EM entries
    em_3d_reconstruction.refinement_type              45 of 37,607 EM entries
    em_3d_reconstruction.magnification_calibration   197 of 37,607 EM entries
    refine.occupancy_max / occupancy_min             5 of 6,000 X-ray sampled
    rcsb_polymer_entity_annotation.description      2,435 polymer entities
    NASASBDB orbit->two_body                        59,881 small bodies

The first four of those this file's predecessor had called accurate and said
would stay accurate. They were not, and the correction is recorded in that
file's docstring as well as here. The same instrument settles the other
direction: rcsb_nonpolymer_instance_feature_summary is null for every one of
the 20,134 non-polymer entity instances across 3,000 entries, so its null
declaration stays, now with the measurement written down.

Where no index exists, the tools were run over a wide input set and every path
in the result compared against what the schema declares at that same path --
which found eleven more fields wrong in the opposite direction, declared
non-null where the API returns null. Those are in WIDENED_BY_CENSUS below with
the sample size behind each.

Three were not schema faults at all. The tool was discarding what the API sent:

  - ols_get_ontology_info reported version and number_of_terms as null. OLS v2
    publishes the release as the OWL versionInfo annotation and the count as
    numberOfClasses; the model declared an alias for neither. v1's flat
    `version` and `numberOfTerms` carried the identical values, checked on go,
    hp, efo, mondo, chebi and uberon.
  - IMPC_get_gene_summary read latest_phenotype_status, latest_production_status,
    latest_phenotyping_centre and latest_production_centre. The 'gene' core has
    no such keys. It has phenotype_status, phenotyping_centre and
    production_centre, which it sets on 140 of 300 genes measured, and
    mouse_production_status on 151, with assignment_status covering 57 more.
    IMPC_search_genes read two of the same non-existent keys, and nothing
    anywhere caught it: its schema already said ["string", "null"], so a field
    that was null for every gene satisfied every check. It is fixed here too,
    but no schema test could have found it -- only reading the core's own
    field list did.
  - InterPro_search_entries declared protein_count, structure_count and
    taxa_count and read them from metadata.counters, which the listing never
    sends. The API names the field itself when asked for a bogus one: it is
    `counts`, not `counters`, and it arrives under `extra_fields` rather than
    inside `metadata`. With it requested, all 450 entries from 10 queries carry
    all three as integers.

Last, InterPro_get_domain_details named eleven literature records as schema
properties -- PUB00001530, PUB00003568 and nine more -- which is the generator
writing down one entry's citation ids. Measured over 250 entries: 1,143
distinct ids across 1,423 records, 0 to 46 per entry. They are data, and are
now a patternProperties key, which also types the twelve record fields from
those 1,423 records instead of from one. That collapses 24 of the remaining
declarations to 2: ISBN and URL, null in all 1,423.

Two are left unreachable and are deliberately not touched.
ExpressionAtlas_get_experiment declares assay_count and last_update, and
/json/experiments/{accession} carries neither; the only source is the
unfiltered /json/experiments listing, 2.6 MB and 18 to 38 seconds per call,
which is too much to spend on two metadata fields. InterPro's `wikipedia` and
`set_info` are null for all 258 integrated entries measured because they are
member-database properties, and InterPro_get_member_signature already serves
that route.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"
SRC = ROOT / "src" / "tooluniverse"


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
    elif seg.startswith("~"):
        found = (node.get("patternProperties") or {}).get(seg[1:])
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


def _examples(stem, name):
    return _tool(stem, name).get("test_examples") or []


EM = "data->entries->*->em_3d_reconstruction->*"
REFINE = "data->entries->*->refine->*"
ANNOT = "data->polymer_entities->*->rcsb_polymer_entity_annotation->*"

# (stem, tool, path, expected types, the index answer, a reaching example)
MEASURED_BY_ASKING_THE_INDEX = [
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->num_class_averages",
        {"integer", "null"},
        "3,934 of 37,607 EM entries",
        {"pdb_id": "10GD"},
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->refinement_type",
        {"string", "null"},
        "45 of 37,607 EM entries",
        {"pdb_id": "3J79"},
    ),
    (
        "rcsb_pdb_tools",
        "get_em_3d_fitting_and_reconstruction_details",
        f"{EM}->magnification_calibration",
        {"string", "null"},
        "197 of 37,607 EM entries",
        {"pdb_id": "1PDL"},
    ),
    (
        "rcsb_pdb_tools",
        "get_core_refinement_statistics",
        f"{REFINE}->occupancy_max",
        {"number", "null"},
        "5 of 6,000 X-ray entries sampled",
        {"pdb_id": "1DN8"},
    ),
    (
        "rcsb_pdb_tools",
        "get_core_refinement_statistics",
        f"{REFINE}->occupancy_min",
        {"number", "null"},
        "5 of 6,000 X-ray entries sampled",
        {"pdb_id": "1DN8"},
    ),
    (
        "rcsb_pdb_tools",
        "get_polymer_entity_annotations",
        f"{ANNOT}->description",
        {"string", "null"},
        "2,435 polymer entities",
        {"entity_id": "11TS_1"},
    ),
    (
        "nasa_sbdb_tools",
        "NASASBDB_get_body",
        "orbit->two_body",
        {"string", "null"},
        "59,881 small bodies",
        {"sstr": "1939 RR", "phys-par": "true"},
    ),
]


@pytest.mark.parametrize(
    "stem,tool,path,types,evidence,example",
    MEASURED_BY_ASKING_THE_INDEX,
    ids=[
        f"{t}:{p.split('->')[-1]}" for _, t, p, _, _, _ in MEASURED_BY_ASKING_THE_INDEX
    ],
)
def test_a_field_the_index_says_is_populated_is_not_declared_null(
    stem, tool, path, types, evidence, example
):
    """RCSB and JPL both report how many records populate a field. Four of
    these were declared null on a sample of about ten, and the index says
    otherwise."""
    assert _types(_tool(stem, tool)["return_schema"], path) == types, evidence


@pytest.mark.parametrize(
    "stem,tool,path,types,evidence,example",
    MEASURED_BY_ASKING_THE_INDEX,
    ids=[
        f"{t}:{p.split('->')[-1]}" for _, t, p, _, _, _ in MEASURED_BY_ASKING_THE_INDEX
    ],
)
def test_the_input_that_reaches_the_value_is_a_test_example(
    stem, tool, path, types, evidence, example
):
    """A widening nothing exercises is a claim, not a measurement. The entry the
    index named is kept as a test_example so the sweep runs it."""
    assert example in _examples(stem, tool), (
        f"{tool} should keep {example} as a test_example; it is the input that "
        f"reaches {path.split('->')[-1]} ({evidence})"
    )


# (stem, tool, path, expected types, what the census measured)
WIDENED_BY_CENSUS = [
    (
        "interpro_tools",
        "InterPro_get_domain_details",
        "metadata->go_terms",
        {"array", "null"},
        "null for entries with no GO terms, over 64 entries",
    ),
    (
        "interpro_tools",
        "InterPro_get_domain_details",
        "metadata->overlaps_with",
        {"array", "null"},
        "null for entries that overlap nothing, over 64 entries",
    ),
    (
        "interpro_tools",
        "InterPro_get_domain_details",
        "metadata->representative_structure",
        {"object", "null"},
        "null where InterPro has picked no structure, over 64 entries",
    ),
    (
        "cryoet_tools",
        "CryoET_get_dataset",
        "dataset->samplePreparation",
        {"string", "null"},
        "null for dataset 10295, over 24 datasets",
    ),
    (
        "cryoet_tools",
        "CryoET_get_dataset",
        "dataset->datasetPublications",
        {"string", "null"},
        "null for dataset 10463, over 24 datasets",
    ),
    (
        "cryoet_tools",
        "CryoET_get_dataset",
        "dataset->relatedDatabaseEntries",
        {"string", "null"},
        "null for dataset 10515, over 24 datasets",
    ),
    (
        "cryoet_tools",
        "CryoET_get_dataset",
        "dataset->otherSetup",
        {"string", "null"},
        "'Cryo-FIB milling' for dataset 10437, null for 10053",
    ),
    (
        "cryoet_tools",
        "CryoET_list_annotations",
        "annotations->*->objectState",
        {"string", "null"},
        "'free' for run 36153, null for run 16126",
    ),
    (
        "cryoet_tools",
        "CryoET_list_annotations",
        "annotations->*->annotationPublication",
        {"string", "null"},
        "null for run 16126, over 24 runs",
    ),
    (
        "ols_tools",
        "ols_get_ontology_info",
        "description",
        {"string", "null"},
        "null for 'skos', of the 287 ontologies OLS lists",
    ),
    (
        "ols_tools",
        "ols_get_ontology_info",
        "homepage",
        {"string", "null"},
        "null for 25 of 287 ontologies",
    ),
    (
        "ols_tools",
        "ols_get_ontology_info",
        "preferredPrefix",
        {"string", "null"},
        "null for 30 of 287 ontologies",
    ),
    (
        "uniprot_locations_tools",
        "UniProtLocations_get_location",
        "note",
        {"string", "null"},
        "a curator note on SL-0147, null on the other 11 measured",
    ),
    (
        "pubtator3_ext_tools",
        "PubTator3_get_annotations",
        "PubTator3->*->passages->*->annotations->*->infons->normalized_id",
        {"integer", "number", "string", "null"},
        "two unnormalised annotations in PMID 32015507",
    ),
    (
        "doaj_tools",
        "DOAJ_search_articles",
        "*->authors",
        {"array", "string"},
        "the tool's own 'Author information not available' sentinel, 8 of 500 articles",
    ),
    (
        "doaj_tools",
        "DOAJ_search_articles",
        "*->keywords",
        {"array", "string"},
        "the same substitution three lines below it in doaj_tool.py",
    ),
    (
        "drugcentral_tools",
        "DrugCentral_search",
        "*->drugbank_id",
        {"string", "array", "null"},
        "['DB09564', 'DB00030'] for 'insulin'",
    ),
    (
        "drugcentral_tools",
        "DrugCentral_search",
        "*->pubchem_cid",
        {"string", "integer", "array", "null"},
        "['118984462', '118984375'] for 'insulin'",
    ),
]


@pytest.mark.parametrize(
    "stem,tool,path,types,evidence",
    WIDENED_BY_CENSUS,
    ids=[f"{t}:{p.split('->')[-1]}" for _, t, p, _, _ in WIDENED_BY_CENSUS],
)
def test_a_declaration_agrees_with_every_type_the_census_saw(
    stem, tool, path, types, evidence
):
    """Walking the live result and comparing the type at every path against the
    declaration at that same path catches both directions at once. Eleven of
    these were wrong the other way round -- declared non-null, returned null."""
    assert _types(_tool(stem, tool)["return_schema"], path) == types, evidence


LITERATURE_FIELDS = {
    "PMID": {"integer", "number"},
    "ISBN": {"null"},
    "volume": {"string", "null"},
    "issue": {"string", "null"},
    "year": {"integer", "number"},
    "title": {"string"},
    "URL": {"null"},
    "raw_pages": {"string", "null"},
    "medline_journal": {"string"},
    "ISO_journal": {"string", "null"},
    "authors": {"array"},
    "DOI_URL": {"string", "null"},
}


def test_the_literature_keys_are_a_pattern_not_eleven_hardcoded_ids():
    """1,143 distinct PUB ids appear across 250 entries and the schema named
    eleven of them as properties, so it described one entry's citations and
    nothing else's."""
    schema = _tool("interpro_tools", "InterPro_get_domain_details")["return_schema"]
    literature = _decl(schema, "metadata->literature")
    assert literature is not None
    assert "patternProperties" in literature
    assert set(literature["patternProperties"]) == {"^PUB[0-9]+$"}
    named = set(literature.get("properties") or {})
    assert not {k for k in named if k.startswith("PUB")}, (
        f"publication ids are still schema properties: {sorted(named)}"
    )


@pytest.mark.parametrize("field,types", sorted(LITERATURE_FIELDS.items()))
def test_a_literature_record_field_is_typed_from_all_1423_records(field, types):
    """Each of the twelve was typed from one record before. raw_pages, volume,
    issue, ISO_journal and DOI_URL are nullable and were declared as plain
    strings; ISBN and URL are null in all 1,423 and stay declared null."""
    schema = _tool("interpro_tools", "InterPro_get_domain_details")["return_schema"]
    assert _types(schema, f"metadata->literature->~^PUB[0-9]+$->{field}") == types


def test_the_ols_model_reads_the_keys_ols_v2_actually_sends():
    """version and number_of_terms came back null for every ontology because
    the model named neither of the keys the v2 payload carries."""
    from tooluniverse.ols_tool import OntologyInfo

    version = OntologyInfo.model_fields["version"].validation_alias
    assert "http://www.w3.org/2002/07/owl#versionInfo" in version.choices
    terms = OntologyInfo.model_fields["number_of_terms"].validation_alias
    assert "numberOfClasses" in terms.choices


def test_the_impc_projection_reads_the_gene_cores_own_keys():
    """The four fields were read from latest_* keys that the 'gene' core does
    not have. IMPC_search_genes read two of the same non-existent keys and had
    nothing to show it: its schema already allowed strings, so a field that was
    null on every gene broke no check anywhere."""
    source = (SRC / "impc_tool.py").read_text()
    for absent in (
        "latest_phenotype_status",
        "latest_production_status",
        "latest_phenotyping_centre",
        "latest_production_centre",
    ):
        assert absent not in source, absent
    for key in (
        "phenotype_status",
        "phenotyping_centre",
        "production_centre",
        "mouse_production_status",
        "assignment_status",
    ):
        assert f'gene_data.get("{key}")' in source, key
    for key in ("phenotype_status", "mouse_production_status", "assignment_status"):
        assert f'doc.get("{key}")' in source, key


def test_the_interpro_listing_asks_for_the_counts_it_declares():
    """The three count fields were read from metadata.counters, which the
    listing never sends. The field is `counts`, under `extra_fields`."""
    source = (SRC / "interpro_entry_tool.py").read_text()
    assert '"extra_fields": "counts"' in source
    assert '"extra_fields"' in source and '.get("counts")' in source


# (stem, tool, path, how large a sample says null)
STILL_NULL_AND_NOW_SAID_SO = [
    (
        "rcsb_pdb_tools",
        "get_ligand_bond_count_by_pdb_id",
        "data->entries->*->nonpolymer_entities->*->nonpolymer_entity_instances->*"
        "->rcsb_nonpolymer_instance_feature_summary",
        "20,134 non-polymer entity instances across 3,000 entries",
    ),
    (
        "interpro_tools",
        "InterPro_get_domain_details",
        "metadata->wikipedia",
        "258 integrated InterPro entries",
    ),
    (
        "interpro_tools",
        "InterPro_get_domain_details",
        "metadata->set_info",
        "258 integrated InterPro entries",
    ),
]


@pytest.mark.parametrize(
    "stem,tool,path,sample",
    STILL_NULL_AND_NOW_SAID_SO,
    ids=[f"{t}:{p.split('->')[-1]}" for _, t, p, _ in STILL_NULL_AND_NOW_SAID_SO],
)
def test_a_null_that_survives_a_large_sample_records_the_sample(
    stem, tool, path, sample
):
    """Leaving a null declaration alone is a measurement too, and it should say
    what it rests on. Guessing a type nobody has observed would read as fixed
    and fail exactly as before."""
    decl = _decl(_tool(stem, tool)["return_schema"], path)
    assert decl is not None
    assert decl.get("type") == "null"
    assert decl.get("description"), f"{path} should record the {sample} behind it"


# Declarations the census agreed with: null at every path, over the sample
# named. They are left alone, and the sample is written down here so the next
# pass over this does not mistake "null on the inputs tried" for a property of
# the data, which is the mistake the commit before this one made.
# (stem, tool, path, sample)
MEASURED_NULL_AND_LEFT_ALONE = [
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_guideline",
        "pdfSettings->pdfCoverPage->image",
        "24 guidelines",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_guideline",
        "pdfSettings->pdfLastPage->image",
        "24 guidelines",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_guideline",
        "pdfSettings->pdfHeadFont",
        "24 guidelines",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_guideline",
        "pdfSettings->pdfHeadSize",
        "24 guidelines",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_guideline",
        "pdfSettings->pdfHeadSub1Size",
        "24 guidelines",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_guideline",
        "pdfSettings->pdfHeadSub2Size",
        "24 guidelines",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_guideline",
        "pdfSettings->pdfHeadSub3Size",
        "24 guidelines",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_guideline",
        "pdfSettings->pdfTextFont",
        "24 guidelines",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_guideline",
        "pdfSettings->pdfTextSize",
        "24 guidelines",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->keyInfo->guidelineId",
        "16 recommendation sets",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->keyInfo->sectionId",
        "16 recommendation sets",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->references->*->usageCount",
        "16 recommendation sets",
    ),
    (
        "clinical_guidelines_tools",
        "MAGICapp_get_recommendations",
        "*->picos->*->references->*->usageCount",
        "16 recommendation sets",
    ),
    (
        "clinical_guidelines_tools",
        "NCI_expand_drugs_by_letter",
        "links",
        "all 26 letters",
    ),
    (
        "interpro_tools",
        "InterPro_get_domain_details",
        "metadata->entry_id",
        "64 entries",
    ),
    (
        "interpro_tools",
        "InterPro_get_domain_details",
        "metadata->integrated",
        "64 entries",
    ),
    (
        "interpro_tools",
        "InterPro_get_protein_domains",
        "*->metadata->integrated",
        "10 proteins",
    ),
    (
        "interpro_tools",
        "InterPro_get_protein_domains",
        "*->proteins->*->entry_protein_locations->*->model",
        "10 proteins",
    ),
    (
        "interpro_tools",
        "InterPro_get_protein_domains",
        "*->proteins->*->entry_protein_locations->*->score",
        "10 proteins",
    ),
    (
        "interpro_tools",
        "InterPro_search_domains",
        "*->metadata->integrated",
        "6 queries",
    ),
    ("cpic_tools", "CPIC_get_drug_info", "*->umlscui", "12 drugs"),
    ("artic_tools", "ArtIC_search_artworks", "preference", "6 queries"),
    (
        "ebi_proteins_ext_tools",
        "EBIProteins_get_mutagenesis",
        "gene_name",
        "8 accessions",
    ),
    (
        "ebi_proteins_ext_tools",
        "EBIProteins_get_proteomics_ptm",
        "features->*->description",
        "3 accessions, 233 features",
    ),
]


@pytest.mark.parametrize(
    "stem,tool,path,sample",
    MEASURED_NULL_AND_LEFT_ALONE,
    ids=[f"{t}:{p.split('->')[-1]}" for _, t, p, _ in MEASURED_NULL_AND_LEFT_ALONE],
)
def test_a_null_the_census_agreed_with_stays_null(stem, tool, path, sample):
    """Null over the sample named in the parameter. Widening one of these to a
    type nobody has observed would read as fixed and fail exactly as before."""
    assert _types(_tool(stem, tool)["return_schema"], path) == {"null"}, sample


def test_the_ols_model_does_not_require_a_title_ols_v2_may_not_send():
    """16 of the 287 ontologies OLS lists carry no plain `title`, and a required
    str made ols_get_ontology_info answer a validation error for every one of
    them -- biolink, coho, dcat, dc, dcterms, evorao, medgen, oio and the rest.
    ols_search_ontologies was worse off: it catches ValidationError per item and
    skips, so it returned 263 ontologies while its own pagination reported
    total_items: 287, and the 16 silently did not exist in any search result.
    It returns all 287 now.

    Twelve of the sixteen name the title under a Dublin Core or rdfs key, and
    for three of those it is a list ('dcat' lists two). medgen, oio and the two
    schemaorg entries have no title under any key, in v1 or v2, and now come
    back as title: null.

    The same list shape broke `version`: giving it the owl#versionInfo alias in
    the commit before this one turned 8 ontologies into validation errors,
    because foodon answers ['2026-02-02', '2026-09-20'] and 7 others likewise.
    One before-validator covers both fields. Measured over all 287: `label` is
    a list every one of the 199 times it is present, rdfs#label 3 of 20 times,
    the two Dublin Core titles once and twice, owl#versionInfo 8 times, and no
    other field the model reads is ever list-shaped."""
    from tooluniverse.ols_tool import OntologyInfo

    field = OntologyInfo.model_fields["title"]
    assert not field.is_required()
    for key in (
        "title",
        "http://purl.org/dc/terms/title",
        "http://purl.org/dc/elements/1.1/title",
        "label",
        "http://www.w3.org/2000/01/rdf-schema#label",
    ):
        assert key in field.validation_alias.choices, key
    assert (
        OntologyInfo.model_validate(
            {"ontologyId": "dcat", "label": ["The data catalog vocabulary", "other"]}
        ).title
        == "The data catalog vocabulary"
    )
    assert OntologyInfo.model_validate({"ontologyId": "medgen"}).title is None


def test_the_title_aliases_do_not_override_a_title_ols_does_send():
    """The aliases are a fallback, not a replacement: `title` comes first in the
    AliasChoices, so the 271 ontologies that do send one keep it even when they
    also send a label. Checked against the live listing when this was written:
    no drift on any of those 271 titles, none on the 163 plain versions, and
    exactly four ontologies end up with a null title."""
    from tooluniverse.ols_tool import OntologyInfo

    both = OntologyInfo.model_validate(
        {
            "ontologyId": "go",
            "title": "Gene Ontology",
            "label": ["GO", "something else"],
            "http://purl.org/dc/terms/title": "not this one",
        }
    )
    assert both.title == "Gene Ontology"
    plain = OntologyInfo.model_validate(
        {
            "ontologyId": "hp",
            "title": "Human Phenotype Ontology",
            "version": "2026-09-01",
            "http://www.w3.org/2002/07/owl#versionInfo": ["ignored"],
        }
    )
    assert plain.version == "2026-09-01"


def test_the_ols_title_declaration_allows_the_null_it_can_now_return():
    schema = _tool("ols_tools", "ols_get_ontology_info")["return_schema"]
    assert _types(schema, "title") == {"string", "null"}
