"""Wrappers that selected a fraction of a record and returned it as the record.

The row axis of "part of a result returned as all of it" was swept in #824:
~300 search/list tools now report `returned`, `total_results`, `has_more`,
`truncated` and `result_set_complete`. This file guards the other axis. A
wrapper can hand back a record whose fields it chose by hand, say
`status: success`, and give no sign that the upstream offered more -- and the
row-axis metadata makes it read as audited while it does so.

Measured against the live APIs on 2026-11-06, before the fix:

    civic_get_assertion            {description, id, status} of 45 Assertion
                                   fields. No assertionType, assertionDirection,
                                   ampLevel, acmgCodes, disease or evidenceItems
                                   -- the clinical substance of an assertion.
    civic_get_evidence_item        source was {"citation": "Vardiman et al.,
                                   2009"} of 32 Source fields: no citationId
                                   (the PMID), no journal, and no `retracted`,
                                   so an agent could not tell that evidence
                                   rested on a withdrawn paper.
    civic_get_variant              no coordinates, alleleRegistryId or
                                   maneSelectTranscript: the variant's position
                                   was absent from a variant record.
    OpenTargets_get_evidence_by_   accepts 23 datasourceIds and selected the
      datasource                   same 9 datasource-agnostic fields for all of
                                   them: eva gave 270 records with no
                                   clinicalSignificances, gwas_credible_sets
                                   rows with no credibleSet, impc none of the
                                   mouse-model fields.
    OpenNeuro_advanced_search      edges { node { id } } -- a faceted search
                                   returning bare accessions, less than the
                                   plain list tool beside it returns.
    ClinVar_get_submitted_records  7 fields per submission, while the efetch XML
                                   it already parses carries MethodType and
                                   Origin on all 45 submissions of
                                   VCV000013961, ContributesToAggregate-
                                   Classification 85 times, ClinicalFeatures 11,
                                   Age 8 and Sex 5.

WHY THIS IS A LIST AND NOT A RULE. Two static rules were tried first and both
are wrong in both directions, the way Lesson 13 warns. "Every field a
return_schema declares must appear in the query" flags 43 of 102 GraphQL tools,
nearly all legitimately: `details`/`expected`/`next_steps` belong to the error
envelope and the disease_target_score family synthesises `disease_info` and
`target_scores` in Python. The reverse, "every field the query selects must be
declared", flags 69 of 102, because a schema may describe a nested object as a
bare `{"type": "object"}` and a flat name comparison cannot see inside it. So
the shape is not derivable from the config, and these are the measured cases.
"""

import json
import pathlib
import re

import pytest

pytestmark = pytest.mark.unit

REPO = pathlib.Path(__file__).resolve().parents[2]
DATA = REPO / "src" / "tooluniverse" / "data"


def _config(tool_name):
    for path in sorted(DATA.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, list):
            continue
        for cfg in payload:
            if isinstance(cfg, dict) and cfg.get("name") == tool_name:
                return cfg
    raise AssertionError(f"{tool_name} is not in the catalogue")


def _query(tool_name):
    cfg = _config(tool_name)
    fields = cfg.get("fields") or {}
    for candidate in (
        fields.get("query") if isinstance(fields, dict) else None,
        cfg.get("query_schema"),
    ):
        if isinstance(candidate, str) and re.search(r"\b(query|mutation)\b", candidate):
            return candidate
    raise AssertionError(f"{tool_name} carries no GraphQL query")


# (tool, field, why it is the substance of what the tool answers)
SUBSTANCE = [
    ("civic_get_assertion", "assertionType", "what kind of claim the assertion makes"),
    ("civic_get_assertion", "assertionDirection", "whether it supports or refutes"),
    ("civic_get_assertion", "ampLevel", "the AMP/ASCO/CAP tier a clinician acts on"),
    ("civic_get_assertion", "acmgCodes", "the ACMG codes behind a germline call"),
    ("civic_get_assertion", "disease", "the disease the assertion is about"),
    ("civic_get_assertion", "therapies", "the therapies it concerns"),
    ("civic_get_assertion", "molecularProfile", "the profile it is made on"),
    ("civic_get_assertion", "evidenceItemsCount", "how much evidence it integrates"),
    (
        "civic_search_assertions",
        "ampLevel",
        "triage a result set without a call per row",
    ),
    (
        "civic_search_assertions",
        "assertionType",
        "triage a result set without a call per row",
    ),
    (
        "civic_get_evidence_item",
        "citationId",
        "the PMID, without which the citation cannot be resolved",
    ),
    (
        "civic_get_evidence_item",
        "retracted",
        "whether the evidence rests on a withdrawn paper",
    ),
    ("civic_get_evidence_item", "journal", "where it was published"),
    ("civic_get_evidence_item", "evidenceRating", "the curator's confidence"),
    ("civic_search_evidence_items", "citationId", "a resolvable citation per row"),
    (
        "civic_search_evidence_items",
        "retracted",
        "a retracted source must be visible in a list too",
    ),
    ("civic_get_variant", "coordinates", "where the variant is"),
    (
        "civic_get_variant",
        "alleleRegistryId",
        "the ClinGen allele id for cross-referencing",
    ),
    (
        "civic_get_variant",
        "maneSelectTranscript",
        "the transcript clinical reporting uses",
    ),
    (
        "OpenTargets_get_evidence_by_datasource",
        "clinicalSignificances",
        "the ClinVar payload",
    ),
    ("OpenTargets_get_evidence_by_datasource", "alleleOrigins", "the ClinVar payload"),
    ("OpenTargets_get_evidence_by_datasource", "credibleSet", "the GWAS statistics"),
    (
        "OpenTargets_get_evidence_by_datasource",
        "diseaseModelAssociatedHumanPhenotypes",
        "the IMPC payload",
    ),
    (
        "OpenTargets_get_evidence_by_datasource",
        "statisticalMethod",
        "the gene-burden payload",
    ),
    (
        "OpenTargets_get_evidence_by_datasource",
        "log2FoldChangeValue",
        "the expression-atlas payload",
    ),
    ("OpenTargets_get_evidence_by_datasource", "mutatedSamples", "the IntOGen payload"),
    ("OpenNeuro_advanced_search", "name", "a search result a human can read"),
    (
        "OpenNeuro_advanced_search",
        "latestSnapshot",
        "modalities, subjects and the BIDS description",
    ),
]


@pytest.mark.parametrize(
    "tool, field, why", SUBSTANCE, ids=[f"{t}:{f}" for t, f, _ in SUBSTANCE]
)
def test_the_query_asks_for_the_field_the_tool_is_about(tool, field, why):
    query = _query(tool)

    assert re.search(rf"\b{re.escape(field)}\b", query), (
        f"{tool} does not ask its API for {field!r} -- {why}. The tool would "
        "answer status: success without it and say nothing about the omission."
    )


CLINVAR_SUBMISSION_FIELDS = [
    (
        "contributes_to_aggregate_classification",
        "which submitters ClinVar counted; 23 of 45 on VCV000013961",
    ),
    ("collection_methods", "clinical testing versus literature curation"),
    ("origins", "germline versus somatic, as the submitter reported it"),
    ("affected_status", "whether the observed individuals were affected"),
    ("sex", "reported on 5 of 45 submissions"),
    ("ages", "reported on 4 of 45 submissions"),
    ("clinical_features", "the observed phenotypes, as HPO ids"),
    ("assertion_method", "the guideline the submitter classified under"),
    ("citations", "the PubMed ids the submission cites"),
]


@pytest.mark.parametrize(
    "field, why",
    CLINVAR_SUBMISSION_FIELDS,
    ids=[f for f, _ in CLINVAR_SUBMISSION_FIELDS],
)
def test_clinvar_submissions_declare_the_per_submitter_facts(field, why):
    """The aggregate record cannot carry these; only the SCV can."""
    cfg = _config("ClinVar_get_submitted_records")
    schema = cfg["return_schema"]["oneOf"][0]
    props = schema["properties"]["submissions"]["items"]["properties"]

    assert field in props, f"submissions[] does not declare {field!r} -- {why}"


def test_the_clinvar_parser_reads_those_fields_from_the_xml():
    """The schema would be a promise the parser does not keep otherwise."""
    source = (REPO / "src" / "tooluniverse" / "clinvar_submitted_tool.py").read_text()

    for path in (
        "ContributesToAggregateClassification",
        "Method/MethodType",
        "Sample",
        'TraitSet[@Type="Finding"]/Trait',
        "AttributeSet/Attribute",
    ):
        assert path in source, f"the parser no longer reads {path!r}"


def test_the_bigg_gene_endpoint_is_reachable_through_a_tool():
    """BiGGModelsTool implemented get_gene; no config exposed it.

    The paper that prompted this found "no wrapper for
    /api/v2/models/{model_id}/genes/{gene_id}" -- and the handler was there all
    along, registered in the operation table with nothing able to call it.
    """
    gene = _config("BiGG_get_gene")
    listing = _config("BiGG_list_model_genes")

    assert gene["fields"]["operation"] == "get_gene"
    assert listing["fields"]["operation"] == "get_model_genes"
    assert set(gene["parameter"]["required"]) == {"model_id", "gene_id"}
    declared = gene["return_schema"]["properties"]["gene"]["properties"]
    for field in ("protein_sequence", "dna_sequence", "strand", "leftpos", "rightpos"):
        assert field in declared, f"BiGG_get_gene does not declare {field!r}"


def test_no_tool_is_typed_against_the_retired_opentargets_genetics_host():
    """`api.genetics.opentargets.org` no longer resolves.

    `OpenTargetGenetics` was registered against it and used by 0 of 2820
    configs, so its only possible outcome was a DNS failure for whoever wrote
    the next config against it. The GWAS and variant tools that look like its
    successors are type OpenTarget and run against the platform endpoint.
    """
    # Code only. graphql_tool.py carries a comment naming the host and saying
    # why the type is gone, which is the thing that stops someone adding it
    # back; banning the name outright would delete that explanation.
    package = REPO / "src" / "tooluniverse"
    offenders = []
    for path in sorted(package.rglob("*.py")):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "api.genetics.opentargets.org" not in line:
                continue
            if line.lstrip().startswith("#"):
                continue
            offenders.append(f"{path.relative_to(REPO)}:{number}")
    assert offenders == [], (
        "the retired Open Targets Genetics host is used (not merely explained) "
        "in: " + ", ".join(offenders)
    )

    used = []
    for path in sorted(DATA.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(payload, list):
            used += [
                c.get("name")
                for c in payload
                if isinstance(c, dict) and c.get("type") == "OpenTargetGenetics"
            ]
    assert used == [], f"tools still typed OpenTargetGenetics: {used}"
