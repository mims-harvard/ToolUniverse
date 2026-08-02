"""Build a ToolUniverse-native county heart-health evidence dossier.

The workflow combines a fixed CDC PLACES profile with bounded literature,
trial-registry, global-indicator, and regulatory context. It is a reproducible
population-health screening example, not a patient analysis or clinical tool.
"""

# ruff: noqa: I001

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_SRC = Path(__file__).resolve().parents[2] / "src"
if str(REPOSITORY_SRC) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_SRC))

from tooluniverse import ToolUniverse


SCHEMA_VERSION = 3
CASE_STUDY_ID = "autauga_county_chd_prevention_evidence_dossier"
ARTIFACT_DIR = Path(__file__).with_name("artifacts")
DEFAULT_JSON_PATH = ARTIFACT_DIR / "snapshot.json"
DEFAULT_MARKDOWN_PATH = ARTIFACT_DIR / "snapshot.md"
DEFAULT_TRACT_CSV_PATH = ARTIFACT_DIR / "tract_profiles.csv"
DEFAULT_MEASURE_CSV_PATH = ARTIFACT_DIR / "measure_summary.csv"
ASPIRIN_LABEL_SET_ID = "0058175f-3474-40c3-a046-6cfaec86d84b"

CDC_TOOL_NAME = "VSDCDCPlacesHeartHealthProfile"
VSD_SOURCE_TOOL_NAMES = (
    CDC_TOOL_NAME,
    "VSDWHOHypertensionIndicator",
    "VSDOpenFDALabelBySetId",
)
SUPPORTING_TOOL_NAMES = (
    "PubMed_search_articles",
    "ClinicalTrials_search_studies",
)
TOOL_NAMES = (
    "VSDDiscoverSources",
    *VSD_SOURCE_TOOL_NAMES,
    *SUPPORTING_TOOL_NAMES,
)

CDC_MEASURE_IDS = (
    "ACCESS2",
    "BPHIGH",
    "CHD",
    "CHECKUP",
    "CSMOKING",
    "HIGHCHOL",
    "LPA",
    "OBESITY",
)
CONTEXT_MEASURE_IDS = tuple(value for value in CDC_MEASURE_IDS if value != "CHD")
PUBMED_QUERY = (
    "census tract[Title/Abstract] AND coronary heart disease[Title/Abstract] "
    "AND (smoking[Title/Abstract] OR hypertension[Title/Abstract] OR "
    "obesity[Title/Abstract] OR physical activity[Title/Abstract])"
)
TRIAL_STATUS_FILTER = (
    "RECRUITING,NOT_YET_RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION"
)
TOOL_CALLS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("VSDDiscoverSources", {"query": ""}),
    (CDC_TOOL_NAME, {"state_abbr": "AL", "county_name": "Autauga", "limit": 500}),
    ("VSDWHOHypertensionIndicator", {}),
    ("VSDOpenFDALabelBySetId", {"set_id": ASPIRIN_LABEL_SET_ID}),
    (
        "PubMed_search_articles",
        {"query": PUBMED_QUERY, "limit": 8, "sort": "relevance"},
    ),
    (
        "ClinicalTrials_search_studies",
        {
            "query_cond": "Coronary Heart Disease",
            "query_term": "AREA[LocationState]Alabama",
            "filter_status": TRIAL_STATUS_FILTER,
            "page_size": 10,
        },
    ),
)


@dataclass(frozen=True)
class StudyRun:
    outputs: dict[str, Any]
    calls: list[dict[str, Any]]


def canonical_json(value: Any) -> str:
    """Return the stable JSON representation used for checked artifacts."""
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _warning_terms(warnings: Any) -> list[str]:
    if not isinstance(warnings, list) or not all(
        isinstance(value, str) for value in warnings
    ):
        raise ValueError("Normalized openFDA warnings must be a string list")
    text = " ".join(warnings).casefold()
    return sorted(
        term
        for term in ("blood thinning", "heart disease", "high blood pressure")
        if term in text
    )


def _clean_provider_text(value: Any) -> Any:
    """Repair common UTF-8-as-Latin-1 text and normalize whitespace."""
    if isinstance(value, list):
        return [_clean_provider_text(item) for item in value]
    if not isinstance(value, str):
        return value
    repaired = value
    if any(marker in value for marker in ("\u00c2", "\u00c3", "\u00e2")):
        try:
            repaired = value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            repaired = value
    return re.sub(r"\s+", " ", repaired).strip()


def _number(row: dict[str, Any], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"CDC {field} must be numeric") from exc
    if not math.isfinite(value):
        raise ValueError(f"CDC {field} must be finite")
    return value


def _index_cdc_profile(
    cdc: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]]]:
    definitions = cdc.get("measure_definitions")
    estimates = cdc.get("estimates")
    if not isinstance(definitions, list) or not isinstance(estimates, list):
        raise TypeError("CDC profile must contain definitions and estimates")

    by_measure = {
        definition.get("measure_id"): definition
        for definition in definitions
        if isinstance(definition, dict)
    }
    if set(by_measure) != set(CDC_MEASURE_IDS) or len(by_measure) != len(definitions):
        raise ValueError("CDC profile did not contain the fixed measure definition set")

    by_tract: dict[str, dict[str, dict[str, Any]]] = {}
    for row in estimates:
        if not isinstance(row, dict):
            raise TypeError("CDC profile contained a non-object estimate")
        tract = row.get("locationname")
        measure_id = row.get("measureid")
        if not isinstance(tract, str) or measure_id not in by_measure:
            raise ValueError("CDC profile contained an invalid tract or measure ID")
        if row.get("measure") != by_measure[measure_id].get("name"):
            raise ValueError("CDC estimate did not match its measure definition")
        tract_rows = by_tract.setdefault(tract, {})
        if measure_id in tract_rows:
            raise ValueError("CDC profile contained a duplicate tract measure")
        estimate = _number(row, "data_value")
        low = _number(row, "low_confidence_limit")
        high = _number(row, "high_confidence_limit")
        if not 0 <= low <= estimate <= high <= 100:
            raise ValueError("CDC estimate or confidence interval was invalid")
        tract_rows[measure_id] = row

    if not by_tract:
        raise ValueError("CDC profile must contain at least one census tract")
    incomplete = {
        tract: sorted(set(CDC_MEASURE_IDS) - set(rows))
        for tract, rows in by_tract.items()
        if set(rows) != set(CDC_MEASURE_IDS)
    }
    if incomplete:
        raise ValueError(
            f"CDC profile had incomplete tract measure grids: {incomplete}"
        )
    return by_measure, by_tract


def _bound(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "census_tract": row["locationname"],
        "estimate_pct": _number(row, "data_value"),
        "confidence_interval_pct": [
            _number(row, "low_confidence_limit"),
            _number(row, "high_confidence_limit"),
        ],
    }


def summarize_measures(
    definitions: dict[str, dict[str, Any]],
    by_tract: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Compute unweighted descriptive summaries for each fixed measure."""
    summaries: dict[str, dict[str, Any]] = {}
    for measure_id in CDC_MEASURE_IDS:
        rows = [by_tract[tract][measure_id] for tract in sorted(by_tract)]
        values = [_number(row, "data_value") for row in rows]
        quartiles = statistics.quantiles(values, n=4, method="inclusive")
        minimum = min(
            rows, key=lambda row: (_number(row, "data_value"), row["locationname"])
        )
        maximum = max(
            rows, key=lambda row: (_number(row, "data_value"), row["locationname"])
        )
        summaries[measure_id] = {
            **definitions[measure_id],
            "tract_count": len(rows),
            "years": sorted({row["year"] for row in rows}),
            "mean_estimate_pct": round(statistics.fmean(values), 2),
            "median_estimate_pct": round(statistics.median(values), 2),
            "interquartile_range_pct": [round(quartiles[0], 2), round(quartiles[2], 2)],
            "minimum": _bound(minimum),
            "maximum": _bound(maximum),
            "observed_range_percentage_points": round(max(values) - min(values), 2),
        }
    return summaries


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("Correlation requires paired observations")
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right)
    )
    denominator = math.sqrt(
        sum((value - left_mean) ** 2 for value in left)
        * sum((value - right_mean) ** 2 for value in right)
    )
    return None if denominator == 0 else round(numerator / denominator, 3)


def build_tract_profiles(
    definitions: dict[str, dict[str, Any]],
    by_tract: dict[str, dict[str, dict[str, Any]]],
    summaries: dict[str, dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
    list[str],
]:
    """Build transparent screening flags and exploratory co-variation."""
    profiles = []
    for tract in sorted(by_tract):
        rows = by_tract[tract]
        values = {
            measure_id: {
                "estimate_pct": _number(rows[measure_id], "data_value"),
                "confidence_interval_pct": [
                    _number(rows[measure_id], "low_confidence_limit"),
                    _number(rows[measure_id], "high_confidence_limit"),
                ],
            }
            for measure_id in CDC_MEASURE_IDS
        }
        point_signals = []
        conservative_signals = []
        for measure_id in CONTEXT_MEASURE_IDS:
            median = summaries[measure_id]["median_estimate_pct"]
            estimate = values[measure_id]["estimate_pct"]
            low, high = values[measure_id]["confidence_interval_pct"]
            if definitions[measure_id]["direction"] == "higher_is_worse":
                point_signal = estimate > median
                conservative_signal = low > median
            else:
                point_signal = estimate < median
                conservative_signal = high < median
            if point_signal:
                point_signals.append(measure_id)
            if conservative_signal:
                conservative_signals.append(measure_id)

        chd_median = summaries["CHD"]["median_estimate_pct"]
        profile = {
            "census_tract": tract,
            "year": rows["CHD"]["year"],
            "estimates": values,
            "chd_above_county_tract_median": values["CHD"]["estimate_pct"] > chd_median,
            "chd_interval_entirely_above_median": (
                values["CHD"]["confidence_interval_pct"][0] > chd_median
            ),
            "context_signal_count": len(point_signals),
            "context_signal_measure_ids": point_signals,
            "conservative_signal_count": len(conservative_signals),
            "conservative_signal_measure_ids": conservative_signals,
        }
        profiles.append(profile)

    candidates = [
        {
            "census_tract": profile["census_tract"],
            "chd_estimate_pct": profile["estimates"]["CHD"]["estimate_pct"],
            "chd_confidence_interval_pct": profile["estimates"]["CHD"][
                "confidence_interval_pct"
            ],
            "context_signal_count": profile["context_signal_count"],
            "context_signal_measure_ids": profile["context_signal_measure_ids"],
            "conservative_signal_count": profile["conservative_signal_count"],
            "conservative_signal_measure_ids": profile[
                "conservative_signal_measure_ids"
            ],
        }
        for profile in profiles
        if profile["chd_above_county_tract_median"]
        and profile["context_signal_count"] >= 4
    ]
    sensitivity = []
    for minimum in range(3, 8):
        selected = [
            profile
            for profile in profiles
            if profile["chd_above_county_tract_median"]
            and profile["context_signal_count"] >= minimum
        ]
        sensitivity.append(
            {
                "minimum_context_signals": minimum,
                "candidate_count": len(selected),
                "census_tracts": [profile["census_tract"] for profile in selected],
            }
        )
    strict_candidates = [
        profile["census_tract"]
        for profile in profiles
        if profile["chd_interval_entirely_above_median"]
        and profile["conservative_signal_count"] >= 3
    ]

    chd_values = [profile["estimates"]["CHD"]["estimate_pct"] for profile in profiles]
    correlations = []
    for measure_id in CONTEXT_MEASURE_IDS:
        measure_values = [
            profile["estimates"][measure_id]["estimate_pct"] for profile in profiles
        ]
        correlations.append(
            {
                "measure_id": measure_id,
                "measure_name": definitions[measure_id]["name"],
                "pearson_r": _correlation(chd_values, measure_values),
            }
        )
    diagnostic = {
        "method": "Pearson correlation of tract point estimates",
        "tract_count": len(profiles),
        "uses_confidence_intervals": False,
        "interpretation": (
            "Exploratory co-variation only; shared modeling inputs, population "
            "differences, and spatial dependence are not adjusted."
        ),
        "correlations_with_chd": correlations,
    }
    return profiles, candidates, diagnostic, sensitivity, strict_candidates


def _normalize_articles(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        raise TypeError("PubMed output must be an article list")
    articles = []
    for row in data:
        if not isinstance(row, dict) or not re.fullmatch(
            r"\d+", str(row.get("pmid", ""))
        ):
            raise ValueError("PubMed output contained an invalid article")
        if not isinstance(row.get("title"), str) or not row["title"]:
            continue
        articles.append(
            {
                key: _clean_provider_text(row.get(key))
                for key in (
                    "pmid",
                    "title",
                    "authors",
                    "journal",
                    "pub_year",
                    "doi",
                    "article_type",
                    "url",
                )
            }
        )
    if not articles:
        raise ValueError("PubMed search returned no titled articles")
    return articles


def _normalize_trials(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(data.get("studies"), list):
        raise TypeError("ClinicalTrials.gov output must contain studies")
    studies = []
    for row in data["studies"]:
        nct_id = row.get("nct_id") if isinstance(row, dict) else None
        if not isinstance(nct_id, str) or not re.fullmatch(r"NCT\d{8}", nct_id):
            raise ValueError("ClinicalTrials.gov output contained an invalid NCT ID")
        studies.append(
            {
                key: _clean_provider_text(row.get(key))
                for key in (
                    "nct_id",
                    "brief_title",
                    "status",
                    "study_type",
                    "phases",
                    "enrollment",
                    "conditions",
                    "interventions",
                    "sponsor",
                    "start_date",
                    "completion_date",
                )
            }
            | {"url": f"https://clinicaltrials.gov/study/{nct_id}"}
        )
    total_count = data.get("total_count")
    if total_count is not None and (
        not isinstance(total_count, int) or total_count < 0
    ):
        raise ValueError("ClinicalTrials.gov total_count was invalid")
    return {
        "query_scope": "Active or upcoming records with an Alabama location match",
        "returned_count": len(studies),
        "total_count": total_count,
        "studies": studies,
    }


def summarize_tool_result(tool_name: str, data: Any) -> dict[str, Any]:
    """Record bounded proof values without copying full provider results."""
    if tool_name == "VSDDiscoverSources":
        return {"reviewed_source_count": len(data["sources"])}
    if tool_name == CDC_TOOL_NAME:
        return {
            "estimate_count": len(data["estimates"]),
            "measure_count": len(data["measure_definitions"]),
            "possibly_truncated": data["possibly_truncated"],
            "tract_count": len({row["locationname"] for row in data["estimates"]}),
        }
    if tool_name == "VSDWHOHypertensionIndicator":
        return {"indicator_code": data["indicator"]["indicator_code"]}
    if tool_name == "VSDOpenFDALabelBySetId":
        return {"set_id": data["label"]["set_id"]}
    if tool_name == "PubMed_search_articles":
        return {"article_count": len(data)}
    if tool_name == "ClinicalTrials_search_studies":
        return {
            "returned_count": len(data["studies"]),
            "total_count": data.get("total_count"),
        }
    raise ValueError(f"Unexpected disease-study tool: {tool_name}")


def build_artifact(study_run: StudyRun, *, generated_at: str) -> dict[str, Any]:
    """Build the bounded evidence dossier from ToolUniverse outputs."""
    missing = set(TOOL_NAMES) - set(study_run.outputs)
    if missing:
        raise ValueError(f"Missing ToolUniverse outputs: {sorted(missing)}")

    discovery = study_run.outputs["VSDDiscoverSources"]["sources"]
    reviewed_tools = {source["tool_name"]: source for source in discovery}
    if not set(VSD_SOURCE_TOOL_NAMES) <= set(reviewed_tools):
        raise ValueError("Discovery did not identify every used VSD source tool")

    cdc = study_run.outputs[CDC_TOOL_NAME]
    if cdc["possibly_truncated"]:
        raise ValueError("CDC county profile reached its limit and may be incomplete")
    definitions, by_tract = _index_cdc_profile(cdc)
    summaries = summarize_measures(definitions, by_tract)
    profiles, candidates, diagnostic, sensitivity, strict_candidates = (
        build_tract_profiles(definitions, by_tract, summaries)
    )

    who = study_run.outputs["VSDWHOHypertensionIndicator"]
    fda = study_run.outputs["VSDOpenFDALabelBySetId"]
    label = fda["label"]
    articles = _normalize_articles(study_run.outputs["PubMed_search_articles"])
    trials = _normalize_trials(study_run.outputs["ClinicalTrials_search_studies"])
    chd = summaries["CHD"]

    return {
        "schema_version": SCHEMA_VERSION,
        "case_study": {
            "id": CASE_STUDY_ID,
            "title": "Autauga County coronary heart disease prevention evidence dossier",
            "generated_at": generated_at,
            "decision_question": (
                "Which Autauga County census tracts show concurrent modeled CHD and "
                "heart-health context signals that merit local data review, and what "
                "literature, trial-registry, and safety records should analysts inspect next?"
            ),
            "intended_use": (
                "Reproducible population-health screening and evidence triage for human review."
            ),
            "screening_rule": (
                "Flag, without ranking, tracts whose CHD point estimate is above the "
                "county tract median and whose point estimates trigger at least four "
                "of seven direction-aware context signals."
            ),
            "interpretation_limits": [
                "CDC PLACES values are modeled aggregate estimates, not individual observations.",
                "CDC advises against using PLACES estimates to rank the overall health of geographic areas; this dossier applies a transparent screening rule and does not produce a rank or composite score.",
                "Means and medians are unweighted across retrieved census tracts and are not county population estimates.",
                "Measure populations differ: insurance covers adults aged 18-64 and high cholesterol covers adults who have ever been screened.",
                "Within-county correlations use point estimates only and do not adjust for confidence intervals, shared model inputs, demographics, or spatial dependence.",
                "A screening flag is not a statistically significant difference, causal finding, diagnosis, or resource-allocation recommendation.",
                "The conservative interval-vs-median signal is a sensitivity heuristic, not a hypothesis test or an interval for the county tract median.",
                "The literature and trial searches are bounded discovery scans, not systematic reviews or endorsements of returned studies.",
                "An Alabama registry match does not establish an Autauga County site, eligibility, availability, efficacy, or safety.",
                "WHO metadata, CDC estimates, PubMed records, trial records, and the openFDA label are independent and are not joined at person level.",
                "The aspirin label is safety context, not evidence of treatment efficacy or advice.",
                "A reviewed VSD adapter establishes a constrained technical contract, not scientific endorsement.",
            ],
        },
        "executive_summary": {
            "tract_count": len(profiles),
            "measure_count": len(CDC_MEASURE_IDS),
            "estimate_count": len(cdc["estimates"]),
            "years": chd["years"],
            "chd_unweighted_mean_pct": chd["mean_estimate_pct"],
            "chd_median_pct": chd["median_estimate_pct"],
            "chd_minimum_pct": chd["minimum"]["estimate_pct"],
            "chd_maximum_pct": chd["maximum"]["estimate_pct"],
            "screening_candidate_count": len(candidates),
            "strict_screening_candidate_count": len(strict_candidates),
            "pubmed_article_count": len(articles),
            "trial_records_returned": trials["returned_count"],
            "trial_records_total_match": trials["total_count"],
        },
        "tooluniverse_execution": {
            "api": "ToolUniverse.load_tools + ToolUniverse.run_one_function",
            "loaded_tools": list(TOOL_NAMES),
            "cache_requested": False,
            "call_count": len(study_run.calls),
            "calls": study_run.calls,
        },
        "vsd_contribution": [
            "Discovery maps packaged reviewed integrations to concrete ToolUniverse tool names.",
            "The CDC adapter exposes one fixed eight-measure heart-health contract rather than an arbitrary measure proxy.",
            "CDC responses are checked for reviewed measure IDs and names, county containment, unique tract-measure pairs, percentage bounds, and confidence-interval ordering.",
            "The shared transport pins a vetted public address, validates TLS hostname and peer, rejects redirects and encoded bodies, and caps responses at 1 MB.",
            "Each VSD result carries endpoint, exact query, retrieval time, media type, size, redirect count, and payload hash.",
            "Mutable registration and generic JSON querying remain in the explicit administration CLI, outside the agent tool surface.",
        ],
        "reviewed_integrations": [
            reviewed_tools[name] for name in VSD_SOURCE_TOOL_NAMES
        ],
        "supporting_integrations": [
            {
                "tool_name": "PubMed_search_articles",
                "role": "Bounded discovery of tract-level CHD literature",
                "contract_boundary": "Candidate records for human review, not a systematic review",
            },
            {
                "tool_name": "ClinicalTrials_search_studies",
                "role": "Bounded scan of active or upcoming Alabama-matched registry records",
                "contract_boundary": "Registry candidates, not local availability or treatment recommendations",
            },
        ],
        "findings": {
            "measure_summaries": summaries,
            "screening": {
                "is_ranking": False,
                "context_measure_count": len(CONTEXT_MEASURE_IDS),
                "minimum_context_signals": 4,
                "candidate_count": len(candidates),
                "candidates": candidates,
                "sensitivity_by_threshold": sensitivity,
                "strict_rule": (
                    "CHD confidence interval entirely above the county tract median "
                    "and at least three context confidence intervals entirely on "
                    "the attention side of their respective medians."
                ),
                "strict_candidate_count": len(strict_candidates),
                "strict_candidate_census_tracts": strict_candidates,
            },
            "exploratory_co_variation": diagnostic,
            "who_context": who["indicator"],
            "openfda_context": {
                "set_id": label["set_id"],
                "effective_time": label["effective_time"],
                "brand_name": label["brand_name"],
                "generic_name": label["generic_name"],
                "route": label["route"],
                "warning_terms_found": _warning_terms(label["warnings"]),
            },
            "evidence_scan": {
                "pubmed": {
                    "query": PUBMED_QUERY,
                    "sort": "relevance",
                    "articles": articles,
                },
                "clinical_trials": trials,
            },
        },
        "tract_profiles": profiles,
        "cdc_places_estimates": sorted(
            cdc["estimates"], key=lambda row: (row["locationname"], row["measureid"])
        ),
        "vsd_provenance": [
            cdc["provenance"],
            fda["provenance"],
            who["provenance"],
        ],
        "official_references": [
            {
                "title": "ToolUniverse Python API guide",
                "url": "https://zitniklab.hms.harvard.edu/ToolUniverse/getting_started.html",
            },
            {
                "title": "CDC PLACES methodology",
                "url": "https://www.cdc.gov/places/methodology/index.html",
            },
            {
                "title": "CDC PLACES measure definitions",
                "url": "https://www.cdc.gov/places/measure-definitions/index.html",
            },
            {
                "title": "CDC PLACES frequently asked questions",
                "url": "https://www.cdc.gov/places/faqs/index.html",
            },
            {
                "title": "ClinicalTrials.gov API",
                "url": "https://clinicaltrials.gov/data-about-studies/learn-about-api",
            },
            {
                "title": "openFDA drug-label API",
                "url": "https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/",
            },
        ],
    }


def _inline_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True).replace("|", "\\|")


def _markdown_text(value: Any) -> str:
    return str(value or "Not reported").replace("|", "\\|").replace("\n", " ")


def render_markdown(artifact: dict[str, Any]) -> str:
    """Render a decision-oriented report from the machine-readable artifact."""
    case = artifact["case_study"]
    executive = artifact["executive_summary"]
    findings = artifact["findings"]
    summaries = findings["measure_summaries"]
    screening = findings["screening"]
    evidence = findings["evidence_scan"]
    who = findings["who_context"]
    label = findings["openfda_context"]
    lines = [
        f"# {case['title']}",
        "",
        f"**Generated:** `{case['generated_at']}`",
        "",
        "**Status:** Reproducible population-health screening dossier for human review",
        "",
        "> This report identifies follow-up questions. It does not rank neighborhoods,",
        "> estimate individual risk, recommend treatment, or allocate resources.",
        "",
        "## Executive Brief",
        "",
        (
            f"ToolUniverse retrieved **{executive['estimate_count']}** validated CDC "
            f"estimates covering **{executive['measure_count']} measures** across "
            f"**{executive['tract_count']} census tracts**. The unweighted tract CHD "
            f"mean was **{executive['chd_unweighted_mean_pct']}%** and the observed "
            f"range was **{executive['chd_minimum_pct']}%-"
            f"{executive['chd_maximum_pct']}%**."
        ),
        "",
        (
            f"The reproducible screening rule identified **{executive['screening_candidate_count']} "
            "tracts** for local validation; the stricter interval heuristic retained "
            f"**{executive['strict_screening_candidate_count']}**. ToolUniverse also returned "
            f"**{executive['pubmed_article_count']} PubMed records** and "
            f"**{executive['trial_records_returned']} of "
            f"{executive['trial_records_total_match']} Alabama-matched trial records** "
            "as bounded follow-up material."
        ),
        "",
        "## Decision Question",
        "",
        case["decision_question"],
        "",
        "## Method At A Glance",
        "",
        "| Component | ToolUniverse tool | Role | Boundary |",
        "| --- | --- | --- | --- |",
        f"| Reviewed local surveillance | `{CDC_TOOL_NAME}` | Eight fixed tract-level measures with 95% confidence intervals | Modeled aggregate estimates |",
        "| Reviewed global metadata | `VSDWHOHypertensionIndicator` | Hypertension indicator definition | Not a local measurement |",
        "| Reviewed regulatory record | `VSDOpenFDALabelBySetId` | Public label safety context | Not efficacy evidence or advice |",
        "| Literature discovery | `PubMed_search_articles` | Candidate tract-level CHD literature | Not a systematic review |",
        "| Trial discovery | `ClinicalTrials_search_studies` | Active/upcoming Alabama-matched records | Site and eligibility require verification |",
        "",
        "The reproducible screening rule encoded by the script is:",
        "",
        f"> {case['screening_rule']}",
        "",
        "## Exactly How ToolUniverse Was Used",
        "",
        "```python",
        "tu = ToolUniverse()",
        "tu.load_tools(include_tools=list(TOOL_NAMES), quiet=True)",
        "result = tu.run_one_function(",
        '    {"name": tool_name, "arguments": arguments},',
        "    use_cache=False,",
        ")",
        "```",
        "",
        "| # | Tool | Exact arguments | Result proof |",
        "| ---: | --- | --- | --- |",
    ]
    for call in artifact["tooluniverse_execution"]["calls"]:
        lines.append(
            f"| {call['sequence']} | `{call['tool_name']}` | "
            f"`{_inline_json(call['arguments'])}` | "
            f"`{_inline_json(call['result_summary'])}` |"
        )

    lines.extend(
        [
            "",
            "## County Measure Profile",
            "",
            "All summaries are unweighted across census tracts.",
            "",
            "| ID | Measure | Population | Direction | Mean | Median | IQR | Observed range |",
            "| --- | --- | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for measure_id in CDC_MEASURE_IDS:
        item = summaries[measure_id]
        iqr = "-".join(str(value) for value in item["interquartile_range_pct"])
        observed = (
            f"{item['minimum']['estimate_pct']}-{item['maximum']['estimate_pct']}%"
        )
        lines.append(
            f"| `{measure_id}` | {_markdown_text(item['name'])} | "
            f"{_markdown_text(item['population'])} | `{item['direction']}` | "
            f"{item['mean_estimate_pct']}% | {item['median_estimate_pct']}% | "
            f"{iqr}% | {observed} |"
        )

    lines.extend(
        [
            "",
            "## Follow-Up Screening Set",
            "",
            (
                f"**{screening['candidate_count']} tracts** met the transparent rule. "
                "Rows are sorted by census tract ID, not by need or health. A context "
                "signal means an adverse measure was above its county tract median, or "
                "routine checkups were below their median."
            ),
            "",
            "| Census tract | CHD estimate (95% CI) | Context signals | Conservative signals | Signal IDs |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    if screening["candidates"]:
        for candidate in screening["candidates"]:
            interval = "-".join(
                str(value) for value in candidate["chd_confidence_interval_pct"]
            )
            signals = ", ".join(
                f"`{value}`" for value in candidate["context_signal_measure_ids"]
            )
            lines.append(
                f"| `{candidate['census_tract']}` | "
                f"{candidate['chd_estimate_pct']}% ({interval}%) | "
                f"{candidate['context_signal_count']}/7 | "
                f"{candidate['conservative_signal_count']}/7 | {signals} |"
            )
    else:
        lines.append("| None | - | - | - | - |")

    lines.extend(
        [
            "",
            "### Threshold Sensitivity",
            "",
            "| Minimum context signals | Candidate tracts | Census tract IDs |",
            "| ---: | ---: | --- |",
        ]
    )
    for row in screening["sensitivity_by_threshold"]:
        tracts = ", ".join(f"`{value}`" for value in row["census_tracts"]) or "None"
        lines.append(
            f"| {row['minimum_context_signals']}/7 | {row['candidate_count']} | {tracts} |"
        )
    strict_tracts = (
        ", ".join(f"`{value}`" for value in screening["strict_candidate_census_tracts"])
        or "None"
    )
    lines.extend(
        [
            "",
            (
                f"**Strict interval heuristic:** {screening['strict_candidate_count']} "
                f"tracts retained ({strict_tracts}). {screening['strict_rule']}"
            ),
            "This is a sensitivity check, not a statistical-significance test.",
        ]
    )

    lines.extend(
        [
            "",
            "### All Tract Profiles",
            "",
            "| Census tract | CHD (95% CI) | Above tract median | Context signals | Conservative signals |",
            "| --- | ---: | --- | ---: | ---: |",
        ]
    )
    for profile in artifact["tract_profiles"]:
        chd = profile["estimates"]["CHD"]
        interval = "-".join(str(value) for value in chd["confidence_interval_pct"])
        lines.append(
            f"| `{profile['census_tract']}` | {chd['estimate_pct']}% ({interval}%) | "
            f"{'Yes' if profile['chd_above_county_tract_median'] else 'No'} | "
            f"{profile['context_signal_count']}/7 | "
            f"{profile['conservative_signal_count']}/7 |"
        )

    diagnostic = findings["exploratory_co_variation"]
    lines.extend(
        [
            "",
            "## Exploratory Co-Variation",
            "",
            diagnostic["interpretation"],
            "",
            "| Context measure | Pearson r with CHD |",
            "| --- | ---: |",
        ]
    )
    for item in diagnostic["correlations_with_chd"]:
        value = "Undefined" if item["pearson_r"] is None else item["pearson_r"]
        lines.append(
            f"| `{item['measure_id']}` {_markdown_text(item['measure_name'])} | {value} |"
        )

    lines.extend(
        [
            "",
            "## Evidence Discovery",
            "",
            "### PubMed Candidates",
            "",
            f"Query: `{evidence['pubmed']['query']}`",
            "",
            "| PMID | Year | Article | Journal |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for article in evidence["pubmed"]["articles"]:
        title = _markdown_text(article["title"])
        lines.append(
            f"| [{article['pmid']}]({article['url']}) | "
            f"{_markdown_text(article['pub_year'])} | {title} | "
            f"{_markdown_text(article['journal'])} |"
        )

    trials = evidence["clinical_trials"]
    lines.extend(
        [
            "",
            "### ClinicalTrials.gov Candidates",
            "",
            (
                f"Returned {trials['returned_count']} of {trials['total_count']} records "
                "matching active/upcoming status, CHD, and an Alabama location-area query. "
                "The compact search output does not prove that an Alabama site is currently "
                "open or near Autauga County; verify each record before use."
            ),
            "",
            "| NCT ID | Status | Phase | Enrollment | Study |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for trial in trials["studies"]:
        phases = ", ".join(trial["phases"] or []) or "Not applicable"
        lines.append(
            f"| [{trial['nct_id']}]({trial['url']}) | `{trial['status']}` | "
            f"{_markdown_text(phases)} | {_markdown_text(trial['enrollment'])} | "
            f"{_markdown_text(trial['brief_title'])} |"
        )

    lines.extend(
        [
            "",
            "## Independent Context",
            "",
            f"- WHO indicator `{who['indicator_code']}`: {who['indicator_name']}.",
            (
                f"- openFDA label `{label['set_id']}`: {label['brand_name']} "
                f"({label['generic_name']}, {label['route']}); matched warning terms: "
                + ", ".join(f"`{term}`" for term in label["warning_terms_found"])
                + "."
            ),
            "",
            "## Why The VSD Layer Matters",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in artifact["vsd_contribution"])
    lines.extend(["", "## Guardrails And Limitations", ""])
    lines.extend(f"- {value}" for value in case["interpretation_limits"])
    lines.extend(["", "## VSD Provenance", ""])
    for source in artifact["vsd_provenance"]:
        lines.append(
            f"- **{source['provider']}**: `{source['endpoint']}`; HTTP "
            f"{source['http_status']}; {source['response_bytes']} bytes; "
            f"SHA-256 `{source['payload_sha256']}`."
        )
    lines.extend(["", "## Reproducibility", ""])
    lines.extend(
        [
            "Run `python examples/vsd/public_health_case_study.py` from the repository root.",
            "The command overwrites the checked JSON, Markdown, tract-profile CSV, and measure-summary CSV artifacts.",
            "",
            "Official references:",
            "",
        ]
    )
    lines.extend(
        f"- [{reference['title']}]({reference['url']})"
        for reference in artifact["official_references"]
    )
    return "\n".join(lines) + "\n"


def render_tract_csv(artifact: dict[str, Any]) -> str:
    """Render analyst-friendly tract estimates and screening flags."""
    columns = ["census_tract", "year"]
    for measure_id in CDC_MEASURE_IDS:
        columns.extend(
            [
                f"{measure_id}_estimate_pct",
                f"{measure_id}_low_95_pct",
                f"{measure_id}_high_95_pct",
            ]
        )
    columns.extend(
        [
            "chd_above_county_tract_median",
            "chd_interval_entirely_above_median",
            "context_signal_count",
            "context_signal_measure_ids",
            "conservative_signal_count",
            "conservative_signal_measure_ids",
        ]
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for profile in artifact["tract_profiles"]:
        row: dict[str, Any] = {
            "census_tract": profile["census_tract"],
            "year": profile["year"],
            "chd_above_county_tract_median": profile["chd_above_county_tract_median"],
            "chd_interval_entirely_above_median": profile[
                "chd_interval_entirely_above_median"
            ],
            "context_signal_count": profile["context_signal_count"],
            "context_signal_measure_ids": ";".join(
                profile["context_signal_measure_ids"]
            ),
            "conservative_signal_count": profile["conservative_signal_count"],
            "conservative_signal_measure_ids": ";".join(
                profile["conservative_signal_measure_ids"]
            ),
        }
        for measure_id in CDC_MEASURE_IDS:
            estimate = profile["estimates"][measure_id]
            row[f"{measure_id}_estimate_pct"] = estimate["estimate_pct"]
            row[f"{measure_id}_low_95_pct"] = estimate["confidence_interval_pct"][0]
            row[f"{measure_id}_high_95_pct"] = estimate["confidence_interval_pct"][1]
        writer.writerow(row)
    return output.getvalue()


def render_measure_csv(artifact: dict[str, Any]) -> str:
    """Render one compact row per CDC measure."""
    columns = [
        "measure_id",
        "name",
        "domain",
        "population",
        "direction",
        "tract_count",
        "years",
        "mean_estimate_pct",
        "median_estimate_pct",
        "q1_pct",
        "q3_pct",
        "minimum_pct",
        "minimum_tract",
        "maximum_pct",
        "maximum_tract",
        "observed_range_percentage_points",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    summaries = artifact["findings"]["measure_summaries"]
    for measure_id in CDC_MEASURE_IDS:
        summary = summaries[measure_id]
        writer.writerow(
            {
                "measure_id": measure_id,
                "name": summary["name"],
                "domain": summary["domain"],
                "population": summary["population"],
                "direction": summary["direction"],
                "tract_count": summary["tract_count"],
                "years": ";".join(summary["years"]),
                "mean_estimate_pct": summary["mean_estimate_pct"],
                "median_estimate_pct": summary["median_estimate_pct"],
                "q1_pct": summary["interquartile_range_pct"][0],
                "q3_pct": summary["interquartile_range_pct"][1],
                "minimum_pct": summary["minimum"]["estimate_pct"],
                "minimum_tract": summary["minimum"]["census_tract"],
                "maximum_pct": summary["maximum"]["estimate_pct"],
                "maximum_tract": summary["maximum"]["census_tract"],
                "observed_range_percentage_points": summary[
                    "observed_range_percentage_points"
                ],
            }
        )
    return output.getvalue()


def run_live() -> StudyRun:
    """Execute every dossier step through one ToolUniverse instance."""
    tooluniverse = ToolUniverse()
    tooluniverse.load_tools(include_tools=list(TOOL_NAMES), quiet=True)
    loaded = {tool["name"] for tool in tooluniverse.all_tools}
    if loaded != set(TOOL_NAMES):
        raise RuntimeError(f"Unexpected loaded study tools: {sorted(loaded)}")

    outputs: dict[str, Any] = {}
    calls: list[dict[str, Any]] = []
    try:
        for sequence, (tool_name, arguments) in enumerate(TOOL_CALLS, start=1):
            result = tooluniverse.run_one_function(
                {"name": tool_name, "arguments": arguments}, use_cache=False
            )
            if not isinstance(result, dict) or result.get("status") != "success":
                raise RuntimeError(f"{tool_name} failed: {result}")
            data = result.get("data")
            if not isinstance(data, (dict, list)):
                raise TypeError(f"{tool_name} returned an invalid data payload")
            outputs[tool_name] = data
            call = {
                "sequence": sequence,
                "tool_name": tool_name,
                "arguments": arguments,
                "status": "success",
                "result_summary": summarize_tool_result(tool_name, data),
            }
            if isinstance(result.get("metadata"), dict):
                call["source_metadata"] = result["metadata"]
            calls.append(call)
    finally:
        tooluniverse.close()
    return StudyRun(outputs=outputs, calls=calls)


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--tract-csv", type=Path, default=DEFAULT_TRACT_CSV_PATH)
    parser.add_argument("--measure-csv", type=Path, default=DEFAULT_MEASURE_CSV_PATH)
    args = parser.parse_args()

    artifact = build_artifact(run_live(), generated_at=utc_now())
    outputs = {
        args.json: canonical_json(artifact),
        args.markdown: render_markdown(artifact),
        args.tract_csv: render_tract_csv(artifact),
        args.measure_csv: render_measure_csv(artifact),
    }
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
