"""Run five realistic demand-to-reviewed-tool VSD value studies."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import tooluniverse.vsd_discovery as vsd_discovery
import tooluniverse.vsd_dynamic_rest as vsd_dynamic_rest
import tooluniverse.vsd_lifecycle as lifecycle_module
import tooluniverse.vsd_promotion as promotion_module
from tooluniverse import ToolUniverse
from tooluniverse.vsd_coverage import resolve_capability
from tooluniverse.vsd_demand import (
    export_proposals,
    observe_capability_demand,
    rank_demands,
    record_plan_demands,
    remove_demand,
    validate_proposal_export,
)
from tooluniverse.vsd_lifecycle import (
    assess_openapi_drift,
    list_publication_states,
    set_publication_state,
)
from tooluniverse.vsd_openapi import inspect_openapi_document
from tooluniverse.vsd_planning import plan_workflow
from tooluniverse.vsd_promotion import (
    VSDPromotionError,
    approve_draft,
    create_openapi_draft,
    load_published_tools,
    publish_draft,
    verify_draft,
)

try:
    from . import cross_format_total_proof
except ImportError:  # Direct execution from examples/vsd.
    import cross_format_total_proof


HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "growth_value_portfolio.json"
DEFAULT_MARKDOWN = ARTIFACTS / "growth_value_portfolio.md"

OFFICIAL_REFERENCES = [
    {
        "label": "ToolUniverse overview",
        "url": "https://zitniklab.hms.harvard.edu/ToolUniverse/en/",
        "relevance": (
            "ToolUniverse standardizes scientific tools for agents, Python, CLI, "
            "and MCP use."
        ),
    },
    {
        "label": "Scientific workflow guidance",
        "url": (
            "https://zitniklab.hms.harvard.edu/ToolUniverse/guide/"
            "scientific_workflows.html"
        ),
        "relevance": (
            "ToolUniverse workflows combine existing tools for disease research, "
            "drug discovery, genomics, and literature synthesis."
        ),
    },
    {
        "label": "AI agent skills catalog",
        "url": (
            "https://zitniklab.hms.harvard.edu/ToolUniverse/en/guide/"
            "skills_showcase.html"
        ),
        "relevance": (
            "The five studies align with documented precision-oncology, safety, "
            "rare-disease, infectious-disease, and multi-omics workflows."
        ),
    },
    {
        "label": "Published drug-discovery case structure",
        "url": (
            "https://zitniklab.hms.harvard.edu/ToolUniverse/en/guide/"
            "tooluniverse_case_study.html"
        ),
        "relevance": (
            "The official case study uses target selection, characterization, drug "
            "selection, prediction, IP review, and human review as a multi-stage model."
        ),
    },
]


SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "precision_oncology_tumor_board",
        "title": "Precision Oncology Molecular Evidence Growth Study",
        "skill_alignment": [
            "precision oncology",
            "cancer variant interpretation",
            "clinical trial matching",
        ],
        "question": (
            "Can a molecular tumor-board workflow reuse ToolUniverse's variant and "
            "trial resources while safely adding one institution-reviewed evidence "
            "operation for therapy, resistance, and evidence-tier context?"
        ),
        "answer": (
            "Yes. Existing variant and trial capabilities remained reusable, while "
            "one provider-specific evidence gap moved through private demand, inert "
            "discovery, authenticated OpenAPI review, three-case verification, "
            "publication, fresh-runtime use, credential rotation, and drift recovery."
        ),
        "value": (
            "A research agent can assemble a reproducible tumor-board evidence packet "
            "without turning a hospital endpoint into an arbitrary proxy or treating "
            "fixture evidence as a treatment recommendation."
        ),
        "interpretation_boundary": (
            "The records demonstrate software governance only. They are not patient "
            "data, clinical recommendations, evidence grading, or proof of efficacy."
        ),
        "provider_host": "reviewed-oncology.example.org",
        "tool_name": "VSDPrecisionOncologyEvidenceByCase",
        "env_var": "TOOLUNIVERSE_VSD_ONCOLOGY_EVIDENCE_KEY",
        "header": "X-Oncology-Evidence-Key",
        "operation_id": "getReviewedMolecularEvidence",
        "record_argument": "caseId",
        "record_field": "case_id",
        "gap_step": "reviewed_molecular_evidence",
        "capability_description": (
            "retrieve one reviewed molecular oncology evidence packet with biomarker "
            "tiers therapies resistance signals and trial identifiers"
        ),
        "public_summary": (
            "Reviewed molecular oncology evidence packets for tumor-board workflows"
        ),
        "discovery_query": (
            "molecular oncology biomarkers evidence tiers resistance trials"
        ),
        "workflow_goal": (
            "Build a reviewed NSCLC molecular evidence packet from variant, label, "
            "trial, and institution-specific evidence"
        ),
        "reuse_capabilities": [
            {
                "step_id": "variant_interpretation",
                "description": (
                    "interpret EGFR L858R somatic cancer variant clinical significance"
                ),
                "required_inputs": ["gene", "variant"],
            },
            {
                "step_id": "trial_search",
                "description": (
                    "search clinical trials by cancer condition and molecular biomarker"
                ),
                "required_inputs": ["condition"],
            },
            {
                "step_id": "drug_label",
                "description": "retrieve FDA drug label by drug name",
                "provider": "FDA",
                "required_inputs": ["query"],
            },
        ],
        "records": {
            "ONC-NSCLC-EGFR": {
                "case_id": "ONC-NSCLC-EGFR",
                "cancer_type": "Non-small cell lung cancer",
                "biomarkers": [
                    {"gene": "EGFR", "variant": "L858R", "evidence_tier": "A"}
                ],
                "approved_therapies": ["osimertinib"],
                "resistance_signals": ["EGFR C797S"],
                "trial_ids": ["NCT04129502", "NCT05256290"],
                "evidence_limitations": [
                    "fixture record",
                    "requires specialist review",
                ],
            },
            "ONC-MEL-BRAF": {
                "case_id": "ONC-MEL-BRAF",
                "cancer_type": "Cutaneous melanoma",
                "biomarkers": [
                    {"gene": "BRAF", "variant": "V600E", "evidence_tier": "A"}
                ],
                "approved_therapies": ["dabrafenib", "trametinib"],
                "resistance_signals": ["MAP2K1 activation"],
                "trial_ids": ["NCT02902042"],
                "evidence_limitations": [
                    "fixture record",
                    "tumor context is required",
                ],
            },
            "ONC-CRC-KRAS": {
                "case_id": "ONC-CRC-KRAS",
                "cancer_type": "Colorectal cancer",
                "biomarkers": [
                    {"gene": "KRAS", "variant": "G12C", "evidence_tier": "B"}
                ],
                "approved_therapies": ["adagrasib"],
                "resistance_signals": ["EGFR pathway reactivation"],
                "trial_ids": ["NCT03785249", "NCT04720976"],
                "evidence_limitations": [
                    "fixture record",
                    "combination context is simplified",
                ],
            },
        },
        "required_paths": [
            "/biomarkers/0/gene",
            "/approved_therapies/0",
            "/trial_ids/0",
        ],
        "decision_outputs": [
            "which evidence needs specialist confirmation",
            "which resistance mechanisms require literature review",
            "which trial identifiers warrant eligibility checking",
        ],
    },
    {
        "id": "pregnancy_pharmacovigilance",
        "title": "Pregnancy Pharmacovigilance Signal Governance Study",
        "skill_alignment": [
            "pharmacovigilance",
            "adverse event detection",
            "chemical safety",
        ],
        "question": (
            "Can a drug-safety workflow reuse FAERS and FDA label tools while adding "
            "one reviewed longitudinal pregnancy-exposure signal operation without "
            "claiming that spontaneous reports prove causality?"
        ),
        "answer": (
            "Yes. ToolUniverse retained its FDA coverage, isolated the missing "
            "pregnancy-signal series, verified three exposure records, and governed "
            "the added operation through credentials, explicit loading, and drift."
        ),
        "value": (
            "Safety researchers can add a narrow institutional or jurisdictional "
            "signal feed to an existing FAERS workflow while preserving provenance, "
            "denominator caveats, and a reviewable shutdown path."
        ),
        "interpretation_boundary": (
            "Reporting odds ratios in these deterministic fixtures are not incidence "
            "rates, causal estimates, regulatory findings, or prescribing advice."
        ),
        "provider_host": "reviewed-safety.example.org",
        "tool_name": "VSDPregnancySafetySignalByExposure",
        "env_var": "TOOLUNIVERSE_VSD_PREGNANCY_SAFETY_KEY",
        "header": "X-Pregnancy-Safety-Key",
        "operation_id": "getPregnancyExposureSignal",
        "record_argument": "exposureId",
        "record_field": "exposure_id",
        "gap_step": "pregnancy_signal_series",
        "capability_description": (
            "retrieve a reviewed pregnancy exposure pharmacovigilance series with "
            "comparator counts disproportionality uncertainty and limitations"
        ),
        "public_summary": (
            "Reviewed pregnancy-exposure safety signal series with explicit caveats"
        ),
        "discovery_query": (
            "pregnancy exposure pharmacovigilance comparator disproportionality"
        ),
        "workflow_goal": (
            "Assess a pregnancy drug-safety question using FAERS, labels, literature, "
            "and one reviewed exposure series"
        ),
        "reuse_capabilities": [
            {
                "step_id": "faers_reports",
                "description": (
                    "FDA adverse event reports and disproportionality safety signals"
                ),
                "provider": "FDA",
            },
            {
                "step_id": "label_warnings",
                "description": "retrieve FDA drug label warnings and pregnancy section",
                "provider": "FDA",
            },
            {
                "step_id": "safety_literature",
                "description": (
                    "search biomedical literature for pregnancy drug safety evidence"
                ),
                "required_inputs": ["query"],
            },
        ],
        "records": {
            "EXP-SEMAGLUTIDE": {
                "exposure_id": "EXP-SEMAGLUTIDE",
                "ingredient": "semaglutide",
                "reporting_window": "2022-2025",
                "exposed_cases": 47,
                "comparator_cases": 512,
                "reporting_odds_ratio": 1.18,
                "confidence_interval": [0.81, 1.72],
                "seriousness_categories": ["hospitalization", "other serious"],
                "signal_status": "monitor",
                "evidence_limitations": [
                    "stimulated reporting",
                    "missing denominator",
                    "confounding by indication",
                ],
            },
            "EXP-VALPROATE": {
                "exposure_id": "EXP-VALPROATE",
                "ingredient": "valproate",
                "reporting_window": "2020-2025",
                "exposed_cases": 193,
                "comparator_cases": 488,
                "reporting_odds_ratio": 3.42,
                "confidence_interval": [2.71, 4.31],
                "seriousness_categories": ["congenital anomaly", "hospitalization"],
                "signal_status": "established_context",
                "evidence_limitations": [
                    "duplicate reports possible",
                    "outcome coding varies",
                ],
            },
            "EXP-ISOTRETINOIN": {
                "exposure_id": "EXP-ISOTRETINOIN",
                "ingredient": "isotretinoin",
                "reporting_window": "2020-2025",
                "exposed_cases": 121,
                "comparator_cases": 488,
                "reporting_odds_ratio": 2.89,
                "confidence_interval": [2.19, 3.81],
                "seriousness_categories": ["congenital anomaly"],
                "signal_status": "established_context",
                "evidence_limitations": [
                    "no exposed-pregnancy denominator",
                    "prevention-program adherence unavailable",
                ],
            },
        },
        "required_paths": [
            "/confidence_interval/0",
            "/seriousness_categories/0",
            "/evidence_limitations/0",
        ],
        "decision_outputs": [
            "which signals need formal epidemiologic follow-up",
            "which label sections should be compared",
            "which limitations prevent causal interpretation",
        ],
    },
    {
        "id": "rare_disease_natural_history",
        "title": "Rare-Disease Natural-History Cohort Growth Study",
        "skill_alignment": [
            "rare disease diagnosis",
            "clinical trial design",
            "disease research",
        ],
        "question": (
            "Can a rare-disease workflow reuse HPO, Monarch, and trial tools while "
            "adding one reviewed longitudinal cohort trajectory needed for endpoint "
            "and feasibility research?"
        ),
        "answer": (
            "Yes. Existing phenotype and trial resources were preserved, and the "
            "missing cohort trajectory became a narrow, verified, lifecycle-managed "
            "tool rather than a generic registry proxy."
        ),
        "value": (
            "Researchers can compare harmonized cohort trajectories across ALS, DMD, "
            "and SMA while retaining cohort definitions, attrition, and readiness "
            "flags needed to judge whether downstream comparisons are defensible."
        ),
        "interpretation_boundary": (
            "The fixture contains aggregate cohort summaries only. It cannot diagnose "
            "a person, estimate individual prognosis, or validate a clinical endpoint."
        ),
        "provider_host": "reviewed-natural-history.example.org",
        "tool_name": "VSDRareDiseaseTrajectoryByCohort",
        "env_var": "TOOLUNIVERSE_VSD_NATURAL_HISTORY_KEY",
        "header": "X-Natural-History-Key",
        "operation_id": "getRareDiseaseTrajectory",
        "record_argument": "cohortId",
        "record_field": "cohort_id",
        "gap_step": "longitudinal_trajectory",
        "capability_description": (
            "retrieve a reviewed rare disease natural history cohort trajectory with "
            "genotype phenotype timepoints motor scores attrition and readiness flags"
        ),
        "public_summary": (
            "Reviewed longitudinal rare-disease cohort trajectories for trial research"
        ),
        "discovery_query": (
            "rare disease natural history genotype motor score cohort attrition"
        ),
        "workflow_goal": (
            "Compare rare-disease phenotypes, trials, and longitudinal motor outcomes "
            "for endpoint feasibility"
        ),
        "reuse_capabilities": [
            {
                "step_id": "phenotype_annotations",
                "description": "rare disease registry phenotypes and HPO annotations",
                "required_inputs": ["disease"],
            },
            {
                "step_id": "disease_genes",
                "description": "rare disease genes and disease associations",
                "required_inputs": ["disease"],
            },
            {
                "step_id": "trial_landscape",
                "description": "search clinical trials by rare disease condition",
                "required_inputs": ["condition"],
            },
        ],
        "records": {
            "NH-ALS": {
                "cohort_id": "NH-ALS",
                "disease": "Amyotrophic lateral sclerosis",
                "genotypes": ["C9orf72", "SOD1", "sporadic"],
                "phenotype_terms": ["HP:0007354", "HP:0002460"],
                "timepoints_months": [0, 6, 12, 18],
                "motor_score_medians": [40.0, 36.5, 31.0, 26.0],
                "attrition_percent": 18.0,
                "trial_readiness_flags": [
                    "common scale",
                    "genotype strata incomplete",
                ],
            },
            "NH-DMD": {
                "cohort_id": "NH-DMD",
                "disease": "Duchenne muscular dystrophy",
                "genotypes": ["DMD exon 45-55 deletion", "other DMD variants"],
                "phenotype_terms": ["HP:0003323", "HP:0003560"],
                "timepoints_months": [0, 12, 24, 36],
                "motor_score_medians": [27.0, 25.0, 21.0, 16.0],
                "attrition_percent": 14.0,
                "trial_readiness_flags": [
                    "steroid exposure recorded",
                    "age stratification required",
                ],
            },
            "NH-SMA": {
                "cohort_id": "NH-SMA",
                "disease": "Spinal muscular atrophy",
                "genotypes": ["SMN1 deletion", "SMN2 copy strata"],
                "phenotype_terms": ["HP:0001290", "HP:0001324"],
                "timepoints_months": [0, 6, 12, 24],
                "motor_score_medians": [22.0, 21.0, 19.5, 17.0],
                "attrition_percent": 11.0,
                "trial_readiness_flags": [
                    "treatment-era confounding",
                    "copy-number strata available",
                ],
            },
        },
        "required_paths": [
            "/genotypes/0",
            "/timepoints_months/0",
            "/motor_score_medians/0",
        ],
        "decision_outputs": [
            "whether timepoints and outcomes can be harmonized",
            "which genotype strata are underrepresented",
            "which attrition and treatment-era caveats affect feasibility",
        ],
    },
    {
        "id": "infectious_disease_surveillance",
        "title": "Infectious-Disease Genomic Surveillance Growth Study",
        "skill_alignment": [
            "infectious disease",
            "sequence retrieval",
            "phylogenetics",
        ],
        "question": (
            "Can an outbreak research workflow reuse sequence and taxonomy tools while "
            "adding one reviewed jurisdictional cluster summary without exposing "
            "individual records or accepting an unreviewed live event stream?"
        ),
        "answer": (
            "Yes. Sequence and taxonomy capabilities stayed in place; one bounded "
            "aggregate cluster operation passed the full review and lifecycle path, "
            "with provider drift disabling fresh loading until explicit recovery."
        ),
        "value": (
            "An incident-analysis workflow can connect public sequence resources to a "
            "narrow reviewed cluster feed while retaining sample windows, coverage, "
            "quality flags, and action provenance needed for cautious interpretation."
        ),
        "interpretation_boundary": (
            "The deterministic records contain no individual data and do not establish "
            "transmission direction, outbreak magnitude, or public-health guidance."
        ),
        "provider_host": "reviewed-surveillance.example.org",
        "tool_name": "VSDPathogenClusterEvidenceById",
        "env_var": "TOOLUNIVERSE_VSD_SURVEILLANCE_KEY",
        "header": "X-Surveillance-Key",
        "operation_id": "getReviewedPathogenCluster",
        "record_argument": "clusterId",
        "record_field": "cluster_id",
        "gap_step": "jurisdictional_cluster",
        "capability_description": (
            "retrieve one reviewed pathogen genomic surveillance cluster with lineage "
            "mutation sample window coverage quality and public health action fields"
        ),
        "public_summary": (
            "Reviewed aggregate pathogen genomic-surveillance cluster summaries"
        ),
        "discovery_query": (
            "pathogen genomic surveillance cluster lineage mutations quality"
        ),
        "workflow_goal": (
            "Characterize a potential outbreak using taxonomy, sequences, literature, "
            "and one reviewed jurisdictional cluster summary"
        ),
        "reuse_capabilities": [
            {
                "step_id": "taxonomy",
                "description": "identify pathogen taxonomy and retrieve genome metadata",
                "required_inputs": ["query"],
            },
            {
                "step_id": "sequences",
                "description": "retrieve pathogen genome sequences by accession",
                "required_inputs": ["accession"],
            },
            {
                "step_id": "outbreak_literature",
                "description": "search literature for pathogen outbreak evidence",
                "required_inputs": ["query"],
            },
        ],
        "records": {
            "OUT-MPXV-01": {
                "cluster_id": "OUT-MPXV-01",
                "pathogen": "Mpox virus",
                "taxonomy_id": "10244",
                "region": "Region A",
                "sample_window": "2026-05-01/2026-05-21",
                "lineages": ["clade IIb"],
                "mutation_markers": ["APOBEC-context marker set"],
                "case_count": 28,
                "sequence_count": 19,
                "quality_flags": ["aggregate fixture", "nine cases unsequenced"],
                "public_health_actions": ["enhanced sequencing", "contact review"],
            },
            "OUT-NIPAH-01": {
                "cluster_id": "OUT-NIPAH-01",
                "pathogen": "Nipah virus",
                "taxonomy_id": "121791",
                "region": "Region B",
                "sample_window": "2026-06-03/2026-06-18",
                "lineages": ["Bangladesh lineage-like"],
                "mutation_markers": ["no reviewed escape marker"],
                "case_count": 11,
                "sequence_count": 7,
                "quality_flags": ["aggregate fixture", "short window"],
                "public_health_actions": ["diagnostic review", "sequence follow-up"],
            },
            "OUT-H5N1-01": {
                "cluster_id": "OUT-H5N1-01",
                "pathogen": "Influenza A H5N1",
                "taxonomy_id": "11320",
                "region": "Region C",
                "sample_window": "2026-04-10/2026-05-10",
                "lineages": ["2.3.4.4b"],
                "mutation_markers": ["PB2 E627K absent", "HA marker under review"],
                "case_count": 16,
                "sequence_count": 14,
                "quality_flags": ["aggregate fixture", "host mix recorded"],
                "public_health_actions": ["cross-sector review", "continued sampling"],
            },
        },
        "required_paths": [
            "/lineages/0",
            "/quality_flags/0",
            "/public_health_actions/0",
        ],
        "decision_outputs": [
            "which sequence gaps require follow-up",
            "which lineage statements are supported only at aggregate level",
            "which quality flags must accompany any incident brief",
        ],
    },
    {
        "id": "multiomics_drug_repurposing",
        "title": "Multi-Omics Drug-Repurposing Evidence Growth Study",
        "skill_alignment": [
            "multi-omics integration",
            "drug repurposing",
            "drug target validation",
        ],
        "question": (
            "Can a systems-biology workflow reuse target, pathway, and compound tools "
            "while adding one reviewed cross-study response signature and keeping "
            "local model provisioning outside the agent control plane?"
        ),
        "answer": (
            "Yes. Existing target and pathway resources remained available, the "
            "cross-study signature followed the full demand-to-lifecycle path, and "
            "the independent Docker evidence remained administrator-only."
        ),
        "value": (
            "A repurposing workflow can add a harmonized institutional signature to "
            "ToolUniverse without hiding cohort count, replication status, or modality "
            "coverage, then pass a bounded evidence packet to separately provisioned "
            "local inference infrastructure."
        ),
        "interpretation_boundary": (
            "The fixture does not validate differential-expression statistics, causal "
            "targets, compound efficacy, or local-model scientific reasoning."
        ),
        "provider_host": "reviewed-multiomics.example.org",
        "tool_name": "VSDMultiOmicResponseSignatureById",
        "env_var": "TOOLUNIVERSE_VSD_MULTIOMICS_KEY",
        "header": "X-MultiOmics-Key",
        "operation_id": "getReviewedMultiOmicSignature",
        "record_argument": "signatureId",
        "record_field": "signature_id",
        "gap_step": "cross_study_signature",
        "capability_description": (
            "retrieve one reviewed cross study multi omic response signature with "
            "genes proteins metabolites pathways cohorts replication and compounds"
        ),
        "public_summary": (
            "Reviewed cross-study multi-omic response signatures for repurposing"
        ),
        "discovery_query": (
            "cross study multi omics response genes proteins metabolites compounds"
        ),
        "workflow_goal": (
            "Prioritize drug-repurposing hypotheses using targets, pathways, compounds, "
            "and one reviewed cross-study multi-omic signature"
        ),
        "reuse_capabilities": [
            {
                "step_id": "target_association",
                "description": "disease target association and druggability evidence",
                "required_inputs": ["disease"],
            },
            {
                "step_id": "pathway_network",
                "description": "gene pathway enrichment and protein interaction network",
                "required_inputs": ["genes"],
            },
            {
                "step_id": "compound_search",
                "description": "find compounds and bioactivity for a protein target",
                "required_inputs": ["target"],
            },
        ],
        "records": {
            "MO-AD-TREM2": {
                "signature_id": "MO-AD-TREM2",
                "disease": "Alzheimer disease",
                "perturbation": "TREM2-high microglial state",
                "cell_types": ["microglia"],
                "genes": ["TREM2", "APOE", "TYROBP"],
                "proteins": ["TREM2", "APOE"],
                "metabolites": ["cholesteryl ester"],
                "pathways": ["lipid handling", "phagosome"],
                "effect_directions": ["TREM2 up", "homeostatic markers down"],
                "cohort_count": 4,
                "replication_status": "replicated_direction",
                "candidate_compounds": ["PPAR agonist class for review"],
            },
            "MO-CRC-KRAS": {
                "signature_id": "MO-CRC-KRAS",
                "disease": "KRAS-mutant colorectal cancer",
                "perturbation": "KRAS G12C inhibition",
                "cell_types": ["tumor epithelial", "fibroblast"],
                "genes": ["DUSP6", "ETV4", "FOSL1"],
                "proteins": ["pERK", "DUSP6"],
                "metabolites": ["lactate"],
                "pathways": ["MAPK signaling", "glycolysis"],
                "effect_directions": ["pERK down", "lactate down"],
                "cohort_count": 3,
                "replication_status": "partial_replication",
                "candidate_compounds": ["SHP2 inhibitor class for review"],
            },
            "MO-RA-TNFA": {
                "signature_id": "MO-RA-TNFA",
                "disease": "Rheumatoid arthritis",
                "perturbation": "TNF inhibition",
                "cell_types": ["synovial fibroblast", "monocyte"],
                "genes": ["TNFAIP3", "CXCL8", "IL6"],
                "proteins": ["TNF", "IL6"],
                "metabolites": ["kynurenine"],
                "pathways": ["TNF signaling", "tryptophan metabolism"],
                "effect_directions": ["CXCL8 down", "IL6 down"],
                "cohort_count": 5,
                "replication_status": "replicated_direction",
                "candidate_compounds": ["JAK inhibitor class for comparison"],
            },
        },
        "required_paths": [
            "/genes/0",
            "/pathways/0",
            "/candidate_compounds/0",
        ],
        "decision_outputs": [
            "which response directions replicate across cohorts",
            "which modalities or cell types remain missing",
            "which compound classes warrant independent target and safety review",
        ],
    },
]


EXPECTED_ASSERTIONS = {
    "assessment_does_not_auto_suspend",
    "breaking_drift_is_detected",
    "candidate_is_inert_and_authenticated",
    "credential_reference_excludes_secret_value",
    "credential_rotation_preserves_operation_identity",
    "demand_closure_is_explicit",
    "discovery_candidate_is_inert",
    "existing_registry_capabilities_are_reused",
    "fresh_runtime_executes_all_three_records",
    "initial_provider_specific_capability_is_missing",
    "missing_credential_fails_before_transport",
    "only_gap_routes_to_external_discovery",
    "private_demand_is_repeated_ranked_and_sanitized",
    "provider_transport_is_exact_and_bounded",
    "publication_is_absent_until_explicit_load",
    "published_capability_resolves_exactly",
    "repaired_contract_requires_explicit_reactivation",
    "replanning_reuses_published_tool",
    "secret_values_are_absent_from_artifacts",
    "suspension_prevents_fresh_loading",
    "three_representative_verification_cases_pass",
    "unapproved_draft_cannot_publish",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _secret(study_id: str, slot: str) -> str:
    return hashlib.sha256(f"vsd-value:{study_id}:{slot}".encode()).hexdigest()


def _schema(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}}
        item_schema = _schema(value[0])
        if any(_schema(item) != item_schema for item in value[1:]):
            raise ValueError("Study array fixtures must use one JSON item shape")
        return {"type": "array", "items": item_schema}
    if isinstance(value, dict):
        return {
            "type": "object",
            "properties": {key: _schema(item) for key, item in value.items()},
            "required": sorted(value),
            "additionalProperties": False,
        }
    raise ValueError(f"Unsupported fixture value: {type(value)!r}")


def _record_schema(study: dict[str, Any]) -> dict[str, Any]:
    records = list(study["records"].values())
    schema = _schema(records[0])
    if any(_schema(record) != schema for record in records[1:]):
        raise ValueError(f"{study['id']} records do not share one schema")
    return schema


def _capability(study: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": study["capability_description"],
        "provider": study["provider_host"],
        "method": "GET",
        "endpoint": (
            f"https://{study['provider_host']}/v1/records/"
            f"{{{study['record_argument']}}}"
        ),
        "required_inputs": [study["record_argument"]],
        "output_fields": sorted(next(iter(study["records"].values()))),
    }


def _workflow(study: dict[str, Any]) -> list[dict[str, Any]]:
    existing = copy.deepcopy(study["reuse_capabilities"])
    gap = {"step_id": study["gap_step"], **_capability(study)}
    synthesis = {
        "step_id": "reviewed_synthesis",
        "description": (
            "synthesize the reviewed evidence while preserving provenance and "
            "interpretation limits"
        ),
        "fulfillment": "agent",
        "depends_on": [item["step_id"] for item in existing] + [study["gap_step"]],
    }
    return [*existing, gap, synthesis]


def _openapi(study: dict[str, Any], *, version: str = "1.0.0", base: str = "v1"):
    record_ids = sorted(study["records"])
    return {
        "openapi": "3.1.0",
        "info": {"title": study["title"], "version": version},
        "servers": [{"url": f"https://{study['provider_host']}/{base}"}],
        "security": [{"reviewedKey": []}],
        "paths": {
            f"/records/{{{study['record_argument']}}}": {
                "get": {
                    "operationId": study["operation_id"],
                    "summary": study["capability_description"],
                    "parameters": [
                        {
                            "name": study["record_argument"],
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "enum": record_ids},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "One reviewed aggregate evidence record",
                            "content": {
                                "application/json": {"schema": _record_schema(study)}
                            },
                        }
                    },
                }
            }
        },
        "components": {
            "securitySchemes": {
                "reviewedKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": study["header"],
                }
            }
        },
    }


def _write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return path


def _verification_cases(study: dict[str, Any]) -> list[dict[str, Any]]:
    fields = sorted(next(iter(study["records"].values())))
    return [
        {
            "arguments": {study["record_argument"]: record_id},
            "expect": {
                "result_type": "object",
                "required_fields": fields,
                "equals": {study["record_field"]: record_id},
                "required_paths": study["required_paths"],
                "equals_paths": {},
            },
        }
        for record_id in sorted(study["records"])
    ]


def _catalog_payload(study: dict[str, Any]) -> dict[str, Any]:
    fields = sorted(next(iter(study["records"].values())))
    identity = _digest(study["id"])
    official_id = f"{identity[:4]}-{identity[4:8]}"
    community_id = f"{identity[8:12]}-{identity[12:16]}"

    def item(name: str, domain: str, dataset_id: str, provenance: str):
        return {
            "resource": {
                "name": name,
                "id": dataset_id,
                "description": study["capability_description"],
                "type": "dataset",
                "updatedAt": "2026-07-15T00:00:00Z",
                "provenance": provenance,
                "columns_name": [field.replace("_", " ").title() for field in fields],
                "columns_field_name": fields,
                "columns_datatype": ["Text"] * len(fields),
                "columns_description": [
                    f"Reviewed metadata hint for {field}" for field in fields
                ],
            },
            "metadata": {"domain": domain},
            "classification": {"domain_tags": study["skill_alignment"] + fields[:5]},
            "permalink": f"https://{domain}/d/{dataset_id}",
        }

    return {
        "results": [
            item(
                study["title"],
                study["provider_host"],
                official_id,
                "official",
            ),
            item(
                f"Community lead for {study['title']}",
                "community.example.org",
                community_id,
                "community",
            ),
        ],
        "resultSetSize": 2,
    }


def _tool_result(tooluniverse: ToolUniverse, name: str, arguments: dict[str, Any]):
    response = tooluniverse.run_one_function(
        {"name": name, "arguments": arguments}, use_cache=False
    )
    if not isinstance(response, dict) or response.get("status") != "success":
        raise RuntimeError(f"{name} failed: {response!r}")
    return response["data"]


def _step(plan: dict[str, Any], step_id: str) -> dict[str, Any]:
    return next(item for item in plan["steps"] if item["step_id"] == step_id)


def _run_study(study: dict[str, Any], workspace: Path, ordinal: int):
    workspace = Path(workspace)
    promotion_workspace = workspace / "promotion"
    demand_workspace = workspace / "demand"
    proposal_path = workspace / "reviewed-demand-proposal.json"
    contract_path = _write_json(
        workspace / "contracts" / "baseline.json", _openapi(study)
    )
    breaking_path = _write_json(
        workspace / "contracts" / "breaking.json",
        _openapi(study, version="2.0.0", base="v2"),
    )
    initial_secret = _secret(study["id"], "initial")
    rotated_secret = _secret(study["id"], "rotated")
    previous_secret = os.environ.get(study["env_var"])
    original_discovery = vsd_discovery._safe_get_json
    original_transport = vsd_dynamic_rest._safe_get_json
    original_runtime_datetime = vsd_dynamic_rest.datetime
    original_promotion_datetime = promotion_module.datetime
    original_lifecycle_timestamp = lifecycle_module._timestamp
    provider_log: list[dict[str, Any]] = []
    discovery_log: list[dict[str, Any]] = []
    promotion_tick = {"value": 0}
    runtime_tick = {"value": 0}
    lifecycle_tick = {"value": 0}
    start = datetime(2026, 8, 10 + ordinal, 12, 0, tzinfo=timezone.utc)

    class PromotionDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = start + timedelta(minutes=promotion_tick["value"] * 10)
            promotion_tick["value"] += 1
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    class RuntimeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = start + timedelta(days=1, minutes=runtime_tick["value"] * 5)
            runtime_tick["value"] += 1
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    def lifecycle_timestamp():
        value = start + timedelta(days=2, minutes=lifecycle_tick["value"] * 5)
        lifecycle_tick["value"] += 1
        return value.isoformat()

    def discovery_transport(url, params, *, timeout):
        if url != "https://api.us.socrata.com/api/catalog/v1":
            raise AssertionError("Discovery escaped the fixed catalog endpoint")
        discovery_log.append(
            {"url": url, "params": copy.deepcopy(params), "timeout": timeout}
        )
        payload = _catalog_payload(study)
        return payload, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(_canonical(payload)),
            "redirects": 0,
        }

    def provider_transport(url, params, *, timeout, headers):
        supplied = headers.get(study["header"])
        slot = {initial_secret: "initial", rotated_secret: "rotated"}.get(supplied)
        if set(headers) != {study["header"]} or slot is None:
            raise AssertionError("Provider did not receive the reviewed credential")
        record_id = url.rsplit("/", 1)[-1]
        if url != f"https://{study['provider_host']}/v1/records/{record_id}":
            raise AssertionError("Provider call escaped the reviewed endpoint")
        if record_id not in study["records"] or params:
            raise AssertionError("Provider call escaped the reviewed argument contract")
        provider_log.append(
            {
                "credential_slot": slot,
                "endpoint": url,
                "record_id": record_id,
                "params": copy.deepcopy(params),
                "timeout": timeout,
            }
        )
        payload = copy.deepcopy(study["records"][record_id])
        return payload, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(_canonical(payload)),
            "redirects": 0,
        }

    try:
        vsd_discovery._safe_get_json = discovery_transport
        vsd_dynamic_rest._safe_get_json = provider_transport
        vsd_dynamic_rest.datetime = RuntimeDateTime
        promotion_module.datetime = PromotionDateTime
        lifecycle_module._timestamp = lifecycle_timestamp
        os.environ[study["env_var"]] = initial_secret

        initial_universe = ToolUniverse()
        try:
            initial_universe.load_tools(
                include_tools=["VSDDiscoverAPICandidates"], quiet=True
            )
            reuse = {
                item["step_id"]: resolve_capability(initial_universe, item, limit=5)[
                    "data"
                ]
                for item in study["reuse_capabilities"]
            }
            initial_coverage = resolve_capability(
                initial_universe, _capability(study), limit=5
            )["data"]
            registry_tool_count = initial_coverage["registry_tool_count"]
            initial_plan = plan_workflow(
                initial_universe,
                goal=study["workflow_goal"],
                capabilities=_workflow(study),
                limit=5,
            )["data"]
            demand_batches = [
                record_plan_demands(
                    initial_plan,
                    {study["gap_step"]: study["public_summary"]},
                    workspace=demand_workspace,
                    source="scheduled_workflow_preflight",
                    run_id=f"{study['id']}-run-{index:03d}",
                    observed_at=(start - timedelta(days=4 - index)).isoformat(),
                    include_classifications=("missing",),
                )
                for index in range(1, 4)
            ]
            discovery = _tool_result(
                initial_universe,
                "VSDDiscoverAPICandidates",
                {"query": study["discovery_query"], "limit": 5},
            )
        finally:
            initial_universe.close()

        ranking = rank_demands(workspace=demand_workspace)["data"]
        demand_id = ranking["ranked_demands"][0]["demand_id"]
        proposal = export_proposals(
            [demand_id],
            proposal_path,
            reviewed_by="VSD Evaluation Maintainer",
            decision_note=(
                "Reviewed the aggregate capability gap before external contract review."
            ),
            workspace=demand_workspace,
            created_at=start.isoformat(),
        )
        inspection = inspect_openapi_document(contract_path)
        candidate = inspection["candidates"][0]
        draft = create_openapi_draft(
            candidate,
            tool_name=study["tool_name"],
            description=study["capability_description"],
            credential_env=study["env_var"],
            workspace=promotion_workspace,
        )

        os.environ.pop(study["env_var"], None)
        calls_before_missing_credential = len(provider_log)
        missing_credential_rejected = False
        try:
            verify_draft(
                draft["draft_id"],
                _verification_cases(study),
                workspace=promotion_workspace,
            )
        except VSDPromotionError as exc:
            missing_credential_rejected = "environment variable" in str(exc)
        os.environ[study["env_var"]] = initial_secret

        evidence = verify_draft(
            draft["draft_id"],
            _verification_cases(study),
            workspace=promotion_workspace,
        )
        unapproved_publish_rejected = False
        try:
            publish_draft(draft["draft_id"], workspace=promotion_workspace)
        except VSDPromotionError:
            unapproved_publish_rejected = True
        approval = approve_draft(
            draft["draft_id"],
            reviewed_by="VSD Evaluation Maintainer",
            decision_note=(
                "Approved the exact operation after all representative fixtures passed."
            ),
            workspace=promotion_workspace,
        )
        publication = publish_draft(draft["draft_id"], workspace=promotion_workspace)

        before_load = ToolUniverse()
        try:
            present_before_load = study["tool_name"] in before_load.all_tool_dict
        finally:
            before_load.close()

        active = ToolUniverse()
        try:
            active_loaded = load_published_tools(active, workspace=promotion_workspace)
            record_ids = sorted(study["records"])
            first = _tool_result(
                active,
                study["tool_name"],
                {study["record_argument"]: record_ids[0]},
            )
            post_coverage = resolve_capability(active, _capability(study), limit=5)[
                "data"
            ]
            post_plan = plan_workflow(
                active,
                goal=study["workflow_goal"],
                capabilities=_workflow(study),
                limit=5,
            )["data"]
            operation_sha256 = first["provenance"]["operation_sha256"]
            os.environ[study["env_var"]] = rotated_secret
            rotated = _tool_result(
                active,
                study["tool_name"],
                {study["record_argument"]: record_ids[1]},
            )
            exact_observation = observe_capability_demand(
                active,
                _capability(study),
                public_summary=study["public_summary"],
                source="post_publication_review",
                event_id=f"{study['id']}-resolved",
                observed_at=(start + timedelta(days=1)).isoformat(),
                workspace=demand_workspace,
            )["data"]["demand"]
        finally:
            active.close()

        removal = remove_demand(demand_id, workspace=demand_workspace, confirm=True)[
            "data"
        ]
        final_ranking = rank_demands(workspace=demand_workspace)["data"]

        unchanged = assess_openapi_drift(
            study["tool_name"], contract_path, workspace=promotion_workspace
        )
        breaking = assess_openapi_drift(
            study["tool_name"], breaking_path, workspace=promotion_workspace
        )
        assessment_only = ToolUniverse()
        try:
            loaded_after_assessment = load_published_tools(
                assessment_only, workspace=promotion_workspace
            )
        finally:
            assessment_only.close()
        suspended = set_publication_state(
            study["tool_name"],
            "suspended",
            changed_by="VSD Evaluation Maintainer",
            reason="Suspend the reviewed operation while breaking endpoint drift is reviewed.",
            assessment_sha256=breaking["assessment_sha256"],
            workspace=promotion_workspace,
        )
        suspended_universe = ToolUniverse()
        try:
            suspended_loaded = load_published_tools(
                suspended_universe, workspace=promotion_workspace
            )
        finally:
            suspended_universe.close()

        repaired = assess_openapi_drift(
            study["tool_name"], contract_path, workspace=promotion_workspace
        )
        activated = set_publication_state(
            study["tool_name"],
            "active",
            changed_by="VSD Evaluation Maintainer",
            reason="Reactivate only after the reviewed contract is unchanged again.",
            assessment_sha256=repaired["assessment_sha256"],
            workspace=promotion_workspace,
        )
        final_universe = ToolUniverse()
        try:
            final_loaded = load_published_tools(
                final_universe, workspace=promotion_workspace
            )
            final = _tool_result(
                final_universe,
                study["tool_name"],
                {study["record_argument"]: record_ids[2]},
            )
        finally:
            final_universe.close()

        lifecycle_status = list_publication_states(
            study["tool_name"], workspace=promotion_workspace
        )["tools"][0]
        persisted = "\n".join(
            path.read_text(encoding="utf-8") for path in workspace.rglob("*.json")
        )
    finally:
        vsd_discovery._safe_get_json = original_discovery
        vsd_dynamic_rest._safe_get_json = original_transport
        vsd_dynamic_rest.datetime = original_runtime_datetime
        promotion_module.datetime = original_promotion_datetime
        lifecycle_module._timestamp = original_lifecycle_timestamp
        if previous_secret is None:
            os.environ.pop(study["env_var"], None)
        else:
            os.environ[study["env_var"]] = previous_secret

    gap_before = _step(initial_plan, study["gap_step"])
    gap_after = _step(post_plan, study["gap_step"])
    discovery_candidate = next(
        item
        for item in discovery["candidates"]
        if item["catalog_domain"] == study["provider_host"]
    )
    first_record = first["result"]
    rotated_record = rotated["result"]
    final_record = final["result"]
    all_results_text = json.dumps([first, rotated, final], sort_keys=True)
    assertions = {
        "existing_registry_capabilities_are_reused": all(
            result["classification"] != "missing" and bool(result["matches"])
            for result in reuse.values()
        ),
        "initial_provider_specific_capability_is_missing": (
            initial_coverage["classification"] == "missing"
            and not initial_coverage["matches"]
        ),
        "only_gap_routes_to_external_discovery": (
            gap_before["classification"] == "missing"
            and gap_before["finder_handoff"]["next_tool"] == "VSDDiscoverAPICandidates"
            and all(
                _step(initial_plan, item["step_id"])["finder_handoff"]["next_tool"]
                != "VSDDiscoverAPICandidates"
                for item in study["reuse_capabilities"]
            )
        ),
        "private_demand_is_repeated_ranked_and_sanitized": (
            all(batch["data"]["recorded_count"] == 1 for batch in demand_batches)
            and ranking["ranked_demands"][0]["total_observations"] == 3
            and proposal["transmission"].startswith("none;")
            and study["capability_description"] not in json.dumps(proposal)
        ),
        "discovery_candidate_is_inert": (
            discovery_candidate["execution_allowed"] is False
            and discovery_candidate["approval_state"] == "unreviewed_candidate"
            and len(discovery_log) == 1
        ),
        "candidate_is_inert_and_authenticated": (
            inspection["promotable_count"] == 1
            and candidate["execution_allowed"] is False
            and candidate["auth"]
            == {
                "type": "api_key_header",
                "scheme_name": "reviewedKey",
                "header": study["header"],
            }
        ),
        "missing_credential_fails_before_transport": (
            missing_credential_rejected
            and len(provider_log) == calls_before_missing_credential + 6
        ),
        "three_representative_verification_cases_pass": (
            evidence["all_cases_passed"] is True and evidence["case_count"] == 3
        ),
        "unapproved_draft_cannot_publish": unapproved_publish_rejected,
        "credential_reference_excludes_secret_value": (
            publication["config"]["vsd_operation"]["auth"]
            == {
                "type": "api_key_header_env",
                "env_var": study["env_var"],
                "header": study["header"],
            }
            and initial_secret not in persisted
            and rotated_secret not in persisted
        ),
        "publication_is_absent_until_explicit_load": (
            present_before_load is False and active_loaded == [study["tool_name"]]
        ),
        "published_capability_resolves_exactly": (
            post_coverage["classification"] == "existing_exact"
            and post_coverage["matches"][0]["name"] == study["tool_name"]
        ),
        "replanning_reuses_published_tool": (
            gap_after["classification"] == "existing_exact"
            and gap_after["selected_match"]["name"] == study["tool_name"]
            and gap_after["finder_handoff"]["next_tool"] == "get_tool_info"
        ),
        "credential_rotation_preserves_operation_identity": (
            rotated["provenance"]["operation_sha256"] == operation_sha256
        ),
        "demand_closure_is_explicit": (
            exact_observation["demand_id"] == demand_id
            and exact_observation["observation_counts"]
            == {"exact": 1, "missing": 3, "partial": 0}
            and removal["removed"] is True
            and final_ranking["total_demand_count"] == 0
        ),
        "breaking_drift_is_detected": (
            unchanged["classification"] == "unchanged"
            and breaking["classification"] == "breaking"
            and breaking["changes"] == ["endpoint"]
            and breaking["suspension_recommended"] is True
        ),
        "assessment_does_not_auto_suspend": loaded_after_assessment
        == [study["tool_name"]],
        "suspension_prevents_fresh_loading": (
            suspended["state"] == "suspended" and suspended_loaded == []
        ),
        "repaired_contract_requires_explicit_reactivation": (
            repaired["classification"] == "unchanged"
            and activated["state"] == "active"
            and final_loaded == [study["tool_name"]]
            and lifecycle_status["state"] == "active"
            and lifecycle_status["revision"] == 2
        ),
        "fresh_runtime_executes_all_three_records": [
            first_record[study["record_field"]],
            rotated_record[study["record_field"]],
            final_record[study["record_field"]],
        ]
        == record_ids,
        "provider_transport_is_exact_and_bounded": (
            len(provider_log) == 6
            and all(
                item["endpoint"].startswith(
                    f"https://{study['provider_host']}/v1/records/"
                )
                and item["params"] == {}
                and item["timeout"] == 20
                for item in provider_log
            )
        ),
        "secret_values_are_absent_from_artifacts": (
            initial_secret not in persisted
            and rotated_secret not in persisted
            and initial_secret not in all_results_text
            and rotated_secret not in all_results_text
        ),
    }
    snapshot = {
        "format": "vsd_growth_value_case_study_v1",
        "version": 1,
        "study_id": study["id"],
        "title": study["title"],
        "research_question": study["question"],
        "answer": study["answer"],
        "tooluniverse_alignment": {
            "skills": study["skill_alignment"],
            "official_references": OFFICIAL_REFERENCES,
            "registry_tool_count": registry_tool_count,
        },
        "scientific_value": study["value"],
        "interpretation_boundary": study["interpretation_boundary"],
        "decision_outputs": study["decision_outputs"],
        "registry_reuse": {
            step_id: {
                "classification": result["classification"],
                "top_matches": [item["name"] for item in result["matches"][:5]],
            }
            for step_id, result in reuse.items()
        },
        "initial_gap": {
            "classification": initial_coverage["classification"],
            "capability_id": initial_coverage["capability_id"],
            "plan_id": initial_plan["plan_id"],
            "plan_sha256": initial_plan["plan_sha256"],
            "gap_step": study["gap_step"],
            "next_interface": gap_before["finder_handoff"]["next_tool"],
        },
        "private_demand": {
            "demand_id": demand_id,
            "observation_count": 3,
            "priority_score": ranking["ranked_demands"][0]["priority_score"],
            "proposal_id": proposal["proposals"][0]["proposal_id"],
            "proposal_sha256": proposal["export_sha256"],
            "transmission": proposal["transmission"],
            "closure_ledger_sha256": removal["ledger_sha256"],
        },
        "candidate_review": {
            "catalog_candidate_id": discovery_candidate["candidate_id"],
            "catalog_candidate_execution_allowed": discovery_candidate[
                "execution_allowed"
            ],
            "openapi_candidate_id": candidate["candidate_id"],
            "openapi_candidate_sha256": candidate["candidate_sha256"],
            "source_document_sha256": candidate["source_document_sha256"],
            "auth": candidate["auth"],
        },
        "promotion": {
            "tool_name": study["tool_name"],
            "draft_sha256": draft["draft_sha256"],
            "operation_sha256": draft["operation_sha256"],
            "verification_sha256": evidence["verification_sha256"],
            "approval_sha256": approval["approval_sha256"],
            "publication_sha256": publication["publication_sha256"],
            "verification_case_count": evidence["case_count"],
        },
        "runtime_evidence": {
            "record_ids": record_ids,
            "records": [first_record, rotated_record, final_record],
            "credential_slots": [item["credential_slot"] for item in provider_log],
            "operation_sha256": operation_sha256,
            "provider_call_count": len(provider_log),
            "expanded_registry_classification": post_coverage["classification"],
            "replanned_gap_classification": gap_after["classification"],
        },
        "negative_controls": {
            "missing_credential_rejected_before_transport": (
                missing_credential_rejected
            ),
            "verified_but_unapproved_publish_rejected": unapproved_publish_rejected,
            "breaking_assessment_did_not_change_state": loaded_after_assessment
            == [study["tool_name"]],
        },
        "lifecycle": {
            "unchanged_assessment_sha256": unchanged["assessment_sha256"],
            "breaking_assessment_sha256": breaking["assessment_sha256"],
            "suspension_event_sha256": suspended["event_sha256"],
            "repaired_assessment_sha256": repaired["assessment_sha256"],
            "activation_event_sha256": activated["event_sha256"],
            "suspended_loaded_tools": suspended_loaded,
            "final_loaded_tools": final_loaded,
        },
        "end_to_end_assertions": assertions,
    }
    snapshot["audit_sha256"] = _digest(snapshot)
    validate_study_snapshot(snapshot)
    return snapshot, proposal


def validate_study_snapshot(snapshot: dict[str, Any]) -> None:
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("format") != "vsd_growth_value_case_study_v1"
        or snapshot.get("version") != 1
    ):
        raise ValueError("Growth value study has an invalid format")
    body = {key: value for key, value in snapshot.items() if key != "audit_sha256"}
    if snapshot.get("audit_sha256") != _digest(body):
        raise ValueError("Growth value study audit digest does not match")
    assertions = snapshot.get("end_to_end_assertions")
    if not isinstance(assertions, dict) or set(assertions) != EXPECTED_ASSERTIONS:
        raise ValueError("Growth value study assertion set is incomplete")
    if not all(assertions.values()):
        failed = sorted(name for name, passed in assertions.items() if not passed)
        raise ValueError(f"Growth value study assertions failed: {failed!r}")
    if snapshot.get("promotion", {}).get("verification_case_count") != 3:
        raise ValueError("Growth value study requires three verification cases")
    if len(snapshot.get("runtime_evidence", {}).get("records", [])) != 3:
        raise ValueError("Growth value study requires three runtime records")


def _study_markdown(snapshot: dict[str, Any]) -> str:
    demand = snapshot["private_demand"]
    promotion = snapshot["promotion"]
    runtime = snapshot["runtime_evidence"]
    lifecycle = snapshot["lifecycle"]
    lines = [
        f"# {snapshot['title']}",
        "",
        "## Decision Question",
        "",
        snapshot["research_question"],
        "",
        f"**Result:** {snapshot['answer']}",
        "",
        "## Why This Fits ToolUniverse",
        "",
        snapshot["scientific_value"],
        "",
        "The study follows ToolUniverse's documented pattern of composing existing "
        "scientific resources before extending the environment. It audited "
        f"{snapshot['tooluniverse_alignment']['registry_tool_count']:,} configured "
        "tools and aligned the workflow with these documented skills: "
        + ", ".join(snapshot["tooluniverse_alignment"]["skills"])
        + ".",
        "",
        "## Existing Registry Reuse",
        "",
        "| Workflow step | Baseline coverage | Top existing tools |",
        "| --- | --- | --- |",
    ]
    for step_id, evidence in sorted(snapshot["registry_reuse"].items()):
        lines.append(
            f"| `{step_id}` | {evidence['classification']} | "
            + ", ".join(f"`{name}`" for name in evidence["top_matches"])
            + " |"
        )
    lines.extend(
        [
            "",
            "Those capabilities were not regenerated. The provider-specific step "
            f"`{snapshot['initial_gap']['gap_step']}` was missing and was the only "
            "step routed to inert external discovery.",
            "",
            "## Organic Demand And Candidate Review",
            "",
            f"Three independent workflow preflights produced demand `{demand['demand_id']}` "
            f"with priority score {demand['priority_score']}. A maintainer explicitly "
            "exported one sanitized proposal; its transmission state remained "
            f"`{demand['transmission']}`.",
            "",
            "The catalog lead and OpenAPI operation remained non-executable. The local "
            "contract supplied one exact read operation and an environment-backed "
            "header credential requirement; no credential value entered the candidate, "
            "draft, evidence, approval, publication, runtime result, or artifact.",
            "",
            "| Review identity | SHA-256 or ID |",
            "| --- | --- |",
            f"| Demand proposal | `{demand['proposal_sha256']}` |",
            f"| OpenAPI candidate | `{snapshot['candidate_review']['openapi_candidate_sha256']}` |",
            f"| Source document | `{snapshot['candidate_review']['source_document_sha256']}` |",
            f"| Draft | `{promotion['draft_sha256']}` |",
            f"| Operation | `{promotion['operation_sha256']}` |",
            f"| Verification | `{promotion['verification_sha256']}` |",
            f"| Approval | `{promotion['approval_sha256']}` |",
            f"| Publication | `{promotion['publication_sha256']}` |",
            "",
            "## Representative Verification And Fresh Runtime",
            "",
            "The draft failed before transport when its credential was absent, then "
            "passed three representative records after the environment reference was "
            "configured. Publication was also refused after verification but before "
            "explicit approval. A new ToolUniverse instance could not see the tool "
            "until `load_published_tools` was called.",
            "",
            "| Record | Key evidence retained |",
            "| --- | --- |",
        ]
    )
    for record in runtime["records"]:
        record_id = next(
            value
            for key, value in record.items()
            if key.endswith("_id") and isinstance(value, str)
        )
        evidence_fields = sorted(key for key in record if not key.endswith("_id"))
        lines.append(f"| `{record_id}` | {', '.join(evidence_fields)} |")
    lines.extend(
        [
            "",
            "The first and second records executed across credential rotation without "
            "changing operation identity. Capability resolution and workflow replanning "
            "then selected the published tool as exact coverage. The original local "
            "demand received one exact observation and was explicitly removed.",
            "",
            "## Drift, Suspension, And Recovery",
            "",
            "A contract endpoint move from `/v1` to `/v2` was classified as breaking. "
            "The assessment alone did not change runtime state: the tool still loaded "
            "until a maintainer explicitly suspended it. A fresh runtime then loaded "
            "nothing. A new unchanged assessment of the reviewed contract was required "
            "before explicit reactivation and the third execution.",
            "",
            "| Lifecycle evidence | SHA-256 |",
            "| --- | --- |",
            f"| Baseline assessment | `{lifecycle['unchanged_assessment_sha256']}` |",
            f"| Breaking assessment | `{lifecycle['breaking_assessment_sha256']}` |",
            f"| Suspension event | `{lifecycle['suspension_event_sha256']}` |",
            f"| Repaired assessment | `{lifecycle['repaired_assessment_sha256']}` |",
            f"| Activation event | `{lifecycle['activation_event_sha256']}` |",
            "",
            "## Research Decisions Enabled",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in snapshot["decision_outputs"])
    lines.extend(
        [
            "",
            "## End-to-End Assertions",
            "",
            "| Assertion | Result |",
            "| --- | --- |",
        ]
    )
    lines.extend(
        f"| `{name}` | {'PASS' if passed else 'FAIL'} |"
        for name, passed in sorted(snapshot["end_to_end_assertions"].items())
    )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            snapshot["interpretation_boundary"],
            "",
            "The provider and catalog are deterministic fixtures because the repository "
            "cannot bundle private credentials or controlled scientific data. Registry "
            "resolution, planning, demand, inspection, promotion, verification, "
            "publication, fresh loading, credential lookup, lifecycle, and audit logic "
            "all use production ToolUniverse paths.",
            "",
            f"**Audit SHA-256:** `{snapshot['audit_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_portfolio(workspace: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    workspace = Path(workspace)
    studies = []
    proposals = []
    for ordinal, scenario in enumerate(SCENARIOS):
        snapshot, proposal = _run_study(scenario, workspace / scenario["id"], ordinal)
        studies.append(snapshot)
        proposals.append(proposal)

    cross_format = json.loads(
        cross_format_total_proof.DEFAULT_JSON.read_text(encoding="utf-8")
    )
    cross_format_total_proof.validate_snapshot(cross_format)
    docker_path = (
        HERE.parent / "docker_llm" / "artifacts" / "docker_smoke_snapshot.json"
    )
    docker = json.loads(docker_path.read_text(encoding="utf-8"))
    docker_security = docker["provisioning"]["security"]
    assertions = {
        "all_five_domain_studies_pass": (
            len(studies) == 5
            and all(all(item["end_to_end_assertions"].values()) for item in studies)
        ),
        "all_studies_use_real_registry_reuse": all(
            item["registry_reuse"] for item in studies
        ),
        "fifteen_verification_cases_pass": sum(
            item["promotion"]["verification_case_count"] for item in studies
        )
        == 15,
        "fifteen_post_verification_executions_pass": sum(
            len(item["runtime_evidence"]["records"]) for item in studies
        )
        == 15,
        "one_hundred_ten_study_assertions_pass": sum(
            len(item["end_to_end_assertions"]) for item in studies
        )
        == 110,
        "six_format_total_proof_remains_valid": (
            cross_format["promotion_stage"]["promoted_format_count"] == 6
            and all(cross_format["end_to_end_assertions"].values())
        ),
        "docker_boundary_is_present_and_hardened": (
            docker_security["host_binding"].startswith("127.0.0.1:")
            and docker_security["read_only_rootfs"] is True
            and docker_security["privileged"] is False
            and docker_security["bind_mounts"] == 0
            and docker["lifecycle"]["absent_after_remove"] is True
            and docker["tooluniverse_inference"]["prompt_hash_verified"] is True
        ),
        "docker_remains_administrator_only": (
            docker["provisioning"]["tool_config"]["name"] == "DockerEvidenceSynthesizer"
            and "provision" not in docker["provisioning"]["tool_config"]["name"].lower()
        ),
        "every_study_has_a_distinct_provider_and_tool": (
            len({item["promotion"]["tool_name"] for item in studies}) == 5
            and len({scenario["provider_host"] for scenario in SCENARIOS}) == 5
            and len({scenario["header"] for scenario in SCENARIOS}) == 5
        ),
        "official_tooluniverse_alignment_is_documented": (
            len(OFFICIAL_REFERENCES) == 4
            and all(item["url"].startswith("https://") for item in OFFICIAL_REFERENCES)
        ),
    }
    manifest = {
        "format": "vsd_growth_value_portfolio_v1",
        "version": 1,
        "title": "Five-Domain ToolUniverse VSD Growth Evaluation Portfolio",
        "question": (
            "Does the complete pending VSD stack add useful, governed capabilities "
            "to realistic ToolUniverse research workflows rather than merely wrapping APIs?"
        ),
        "answer": (
            "Yes. Five distinct provider-specific gaps moved from real registry reuse "
            "and repeated private demand through review, verification, fresh-runtime "
            "use, credential rotation, demand closure, suspension, and recovery. The "
            "existing six-format proof and independent real-Docker evidence also remain valid."
        ),
        "official_references": OFFICIAL_REFERENCES,
        "study_count": len(studies),
        "study_summaries": [
            {
                "study_id": item["study_id"],
                "title": item["title"],
                "skills": item["tooluniverse_alignment"]["skills"],
                "tool_name": item["promotion"]["tool_name"],
                "verification_cases": item["promotion"]["verification_case_count"],
                "runtime_records": len(item["runtime_evidence"]["records"]),
                "assertion_count": len(item["end_to_end_assertions"]),
                "audit_sha256": item["audit_sha256"],
            }
            for item in studies
        ],
        "combined_metrics": {
            "registry_tool_count": studies[0]["tooluniverse_alignment"][
                "registry_tool_count"
            ],
            "new_study_assertions": 110,
            "new_verification_cases": 15,
            "new_post_verification_executions": 15,
            "cross_format_promotions": 6,
            "cross_format_assertions": len(cross_format["end_to_end_assertions"]),
            "cross_format_audit_sha256": cross_format["audit_sha256"],
            "docker_prompt_sha256": docker["tooluniverse_inference"]["prompt_sha256"],
            "docker_payload_sha256": docker["tooluniverse_inference"]["payload_sha256"],
        },
        "branch_scope": {
            "base": "current main at branch construction",
            "vsd_stack": "PRs 416-419, 421, and 423-432",
            "docker_boundary": "PR 420 merged only for reviewer evaluation",
            "review_intent": (
                "This branch is a test assembly; the logically isolated PRs remain "
                "the review and landing units."
            ),
        },
        "end_to_end_assertions": assertions,
    }
    manifest["audit_sha256"] = _digest(manifest)
    validate_portfolio(manifest)
    return manifest, studies


def validate_portfolio(manifest: dict[str, Any]) -> None:
    if (
        not isinstance(manifest, dict)
        or manifest.get("format") != "vsd_growth_value_portfolio_v1"
        or manifest.get("study_count") != 5
    ):
        raise ValueError("Growth value portfolio has an invalid format")
    body = {key: value for key, value in manifest.items() if key != "audit_sha256"}
    if manifest.get("audit_sha256") != _digest(body):
        raise ValueError("Growth value portfolio audit digest does not match")
    assertions = manifest.get("end_to_end_assertions")
    if not isinstance(assertions, dict) or len(assertions) != 10:
        raise ValueError("Growth value portfolio assertion set is incomplete")
    if not all(assertions.values()):
        failed = sorted(name for name, passed in assertions.items() if not passed)
        raise ValueError(f"Growth value portfolio assertions failed: {failed!r}")


def _portfolio_markdown(manifest: dict[str, Any]) -> str:
    metrics = manifest["combined_metrics"]
    lines = [
        "# Five-Domain ToolUniverse VSD Growth Evaluation Portfolio",
        "",
        "## Evaluation Question",
        "",
        manifest["question"],
        "",
        f"**Result:** {manifest['answer']}",
        "",
        "## Why These Studies",
        "",
        "ToolUniverse's official documentation emphasizes multi-tool scientific "
        "workflows and skills for disease research, precision oncology, drug safety, "
        "rare disease, infectious disease, and multi-omics. These studies test the "
        "specific VSD value inside that model: reuse the large existing registry first, "
        "then grow it only when one exact reviewed capability is missing.",
        "",
        "| Study | Documented workflow alignment | New reviewed tool | Assertions |",
        "| --- | --- | --- | ---: |",
    ]
    for item in manifest["study_summaries"]:
        filename = item["study_id"] + ".md"
        lines.append(
            f"| [{item['title']}]({filename}) | {', '.join(item['skills'])} | "
            f"`{item['tool_name']}` | {item['assertion_count']} |"
        )
    lines.extend(
        [
            "",
            "## Common End-to-End Path",
            "",
            "1. Audit the real ToolUniverse registry and retain existing partial or exact tools.",
            "2. Isolate one provider-specific missing step in a dependency-aware workflow.",
            "3. Record three private demand observations and explicitly export one sanitized proposal.",
            "4. Keep fixed-catalog and OpenAPI candidates inert and content-addressed.",
            "5. Bind an environment credential reference without persisting its value.",
            "6. Reject verification without the credential and reject publication without approval.",
            "7. Verify three representative records, approve, publish, and explicitly load into a fresh runtime.",
            "8. Execute across credential rotation, resolve exact coverage, replan, and explicitly close demand.",
            "9. Detect breaking drift without automatically changing state.",
            "10. Explicitly suspend, prove fresh loading fails closed, review repair, reactivate, and execute again.",
            "",
            "## Combined Evidence",
            "",
            f"- Real registry audited: {metrics['registry_tool_count']:,} configured tools.",
            f"- New domain studies: 5 with {metrics['new_study_assertions']} assertions.",
            f"- Representative verification executions: {metrics['new_verification_cases']}.",
            f"- Post-verification fresh-runtime executions: {metrics['new_post_verification_executions']}.",
            f"- Existing total proof: {metrics['cross_format_promotions']} promoted formats and {metrics['cross_format_assertions']} assertions.",
            "- Existing Docker proof: real administrator lifecycle, hardened loopback container, ToolUniverse call, and cleanup.",
            "",
            "## Branch And Review Boundary",
            "",
            manifest["branch_scope"]["review_intent"],
            "",
            "The branch combines the complete stacked VSD implementation with the "
            "independent Docker phase so reviewers can test the whole pending system. "
            "It does not collapse the PR review order or make Docker lifecycle control "
            "agent-callable.",
            "",
            "## Official References",
            "",
        ]
    )
    lines.extend(
        f"- [{item['label']}]({item['url']}): {item['relevance']}"
        for item in manifest["official_references"]
    )
    lines.extend(
        [
            "",
            "## Portfolio Assertions",
            "",
            "| Assertion | Result |",
            "| --- | --- |",
        ]
    )
    lines.extend(
        f"| `{name}` | {'PASS' if passed else 'FAIL'} |"
        for name, passed in sorted(manifest["end_to_end_assertions"].items())
    )
    lines.extend(
        [
            "",
            f"**Portfolio audit SHA-256:** `{manifest['audit_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    manifest: dict[str, Any],
    studies: list[dict[str, Any]],
    directory: Path = ARTIFACTS,
) -> None:
    validate_portfolio(manifest)
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(directory / DEFAULT_JSON.name, manifest)
    (directory / DEFAULT_MARKDOWN.name).write_text(
        _portfolio_markdown(manifest), encoding="utf-8"
    )
    for study in studies:
        validate_study_snapshot(study)
        _write_json(directory / f"{study['study_id']}.json", study)
        (directory / f"{study['study_id']}.md").write_text(
            _study_markdown(study), encoding="utf-8"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="tooluniverse-vsd-value-") as directory:
        manifest, studies = run_portfolio(Path(directory))
    write_artifacts(manifest, studies)
    print(
        json.dumps(
            {
                "status": "passed",
                "study_count": len(studies),
                "audit_sha256": manifest["audit_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
