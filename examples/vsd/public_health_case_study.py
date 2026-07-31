"""Run a ToolUniverse-native coronary-heart-disease VSD case study.

The workflow retains normalized aggregate observations and provenance. It does
not persist raw upstream responses or use heterogeneous sources as joinable
patient-level evidence.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_SRC = Path(__file__).resolve().parents[2] / "src"
if str(REPOSITORY_SRC) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_SRC))

from tooluniverse import ToolUniverse  # noqa: E402


SCHEMA_VERSION = 2
CASE_STUDY_ID = "coronary_heart_disease_autauga_vsd_study"
DEFAULT_JSON_PATH = Path(__file__).with_name("artifacts") / "snapshot.json"
DEFAULT_MARKDOWN_PATH = Path(__file__).with_name("artifacts") / "snapshot.md"
ASPIRIN_LABEL_SET_ID = "0058175f-3474-40c3-a046-6cfaec86d84b"

TOOL_NAMES = (
    "VSDDiscoverSources",
    "VSDWHOHypertensionIndicator",
    "VSDCDCPlacesCoronaryHeartDisease",
    "VSDOpenFDALabelBySetId",
)
TOOL_CALLS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("VSDDiscoverSources", {"query": ""}),
    ("VSDWHOHypertensionIndicator", {}),
    (
        "VSDCDCPlacesCoronaryHeartDisease",
        {"state_abbr": "AL", "county_name": "Autauga", "limit": 500},
    ),
    ("VSDOpenFDALabelBySetId", {"set_id": ASPIRIN_LABEL_SET_ID}),
)


@dataclass(frozen=True)
class StudyRun:
    outputs: dict[str, dict[str, Any]]
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


def summarize_chd(tracts: Any) -> dict[str, Any]:
    """Compute descriptive statistics without individual-level inference."""
    if not isinstance(tracts, list) or not tracts:
        raise ValueError("CDC output must contain at least one census tract")
    ordered = sorted(tracts, key=lambda row: str(row["locationname"]))
    values = [float(row["data_value"]) for row in ordered]
    minimum = min(
        ordered, key=lambda row: (float(row["data_value"]), row["locationname"])
    )
    maximum = max(
        ordered, key=lambda row: (float(row["data_value"]), row["locationname"])
    )
    years = sorted({row["year"] for row in ordered})
    return {
        "tract_count": len(ordered),
        "years": years,
        "mean_estimate_pct": round(statistics.fmean(values), 2),
        "median_estimate_pct": round(statistics.median(values), 2),
        "minimum": {
            "census_tract": minimum["locationname"],
            "estimate_pct": float(minimum["data_value"]),
            "confidence_interval_pct": [
                float(minimum["low_confidence_limit"]),
                float(minimum["high_confidence_limit"]),
            ],
        },
        "maximum": {
            "census_tract": maximum["locationname"],
            "estimate_pct": float(maximum["data_value"]),
            "confidence_interval_pct": [
                float(maximum["low_confidence_limit"]),
                float(maximum["high_confidence_limit"]),
            ],
        },
        "observed_range_percentage_points": round(max(values) - min(values), 2),
    }


def summarize_tool_result(tool_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Record bounded proof values without copying full provider results."""
    if tool_name == "VSDDiscoverSources":
        return {"reviewed_source_count": len(data["sources"])}
    if tool_name == "VSDWHOHypertensionIndicator":
        return {"indicator_code": data["indicator"]["indicator_code"]}
    if tool_name == "VSDCDCPlacesCoronaryHeartDisease":
        return {
            "tract_count": len(data["tracts"]),
            "possibly_truncated": data["possibly_truncated"],
        }
    if tool_name == "VSDOpenFDALabelBySetId":
        return {"set_id": data["label"]["set_id"]}
    raise ValueError(f"Unexpected disease-study tool: {tool_name}")


def build_artifact(study_run: StudyRun, *, generated_at: str) -> dict[str, Any]:
    """Build the bounded study artifact from normalized ToolUniverse outputs."""
    missing = set(TOOL_NAMES) - set(study_run.outputs)
    if missing:
        raise ValueError(f"Missing ToolUniverse outputs: {sorted(missing)}")

    discovery = study_run.outputs["VSDDiscoverSources"]["sources"]
    reviewed_tools = {source["tool_name"]: source for source in discovery}
    used_source_tools = set(TOOL_NAMES) - {"VSDDiscoverSources"}
    if not used_source_tools <= set(reviewed_tools):
        raise ValueError("Discovery output did not identify every used source tool")

    who = study_run.outputs["VSDWHOHypertensionIndicator"]
    cdc = study_run.outputs["VSDCDCPlacesCoronaryHeartDisease"]
    fda = study_run.outputs["VSDOpenFDALabelBySetId"]
    if cdc["possibly_truncated"]:
        raise ValueError("CDC county result reached its limit and may be incomplete")
    label = fda["label"]
    tracts = sorted(cdc["tracts"], key=lambda row: row["locationname"])

    return {
        "schema_version": SCHEMA_VERSION,
        "case_study": {
            "id": CASE_STUDY_ID,
            "title": "Coronary heart disease estimates in Autauga County, Alabama",
            "generated_at": generated_at,
            "research_question": (
                "What variation does CDC PLACES report in modeled adult coronary "
                "heart disease prevalence across Autauga County census tracts, and "
                "how can related WHO indicator and public aspirin-label context be "
                "retrieved without treating the sources as joinable clinical evidence?"
            ),
            "study_design": (
                "Bounded descriptive retrieval demonstration using aggregate CDC "
                "small-area estimates and two independent context sources."
            ),
            "interpretation_limits": [
                "CDC PLACES values are modeled aggregate estimates, not individual observations.",
                "The descriptive mean is unweighted across retrieved census tracts.",
                "Differences between tracts do not establish causes or statistical significance.",
                "WHO metadata, CDC estimates, and the openFDA label are independent and are not joined.",
                "The aspirin label is safety context, not evidence of treatment efficacy or advice.",
                "A reviewed VSD adapter establishes a constrained technical contract, not scientific endorsement.",
            ],
        },
        "tooluniverse_execution": {
            "api": "ToolUniverse.run_one_function",
            "loaded_tools": list(TOOL_NAMES),
            "cache_requested": False,
            "call_count": len(study_run.calls),
            "calls": study_run.calls,
        },
        "vsd_contribution": [
            "Discovery maps packaged reviewed integrations to concrete ToolUniverse tool names.",
            "Each source tool fixes the provider endpoint and validates source-specific inputs and outputs.",
            "The shared transport pins a vetted public address, validates TLS hostname and peer, rejects redirects and encoded bodies, and caps responses at 1 MB.",
            "Each result carries endpoint, exact query, retrieval time, media type, size, redirect count, and payload hash.",
            "Mutable registration and generic JSON querying are available only through the explicit administration CLI, not the agent tool surface.",
        ],
        "reviewed_integrations": [
            reviewed_tools[name] for name in sorted(used_source_tools)
        ],
        "findings": {
            "cdc_places_summary": summarize_chd(tracts),
            "who_context": who["indicator"],
            "openfda_context": {
                "set_id": label["set_id"],
                "effective_time": label["effective_time"],
                "brand_name": label["brand_name"],
                "generic_name": label["generic_name"],
                "route": label["route"],
                "warning_terms_found": _warning_terms(label["warnings"]),
            },
        },
        "cdc_places_estimates": tracts,
        "provenance": [
            cdc["provenance"],
            fda["provenance"],
            who["provenance"],
        ],
    }


def _inline_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True).replace("|", "\\|")


def render_markdown(artifact: dict[str, Any]) -> str:
    case = artifact["case_study"]
    summary = artifact["findings"]["cdc_places_summary"]
    who = artifact["findings"]["who_context"]
    label = artifact["findings"]["openfda_context"]
    lines = [
        f"# {case['title']}",
        "",
        f"Generated: `{case['generated_at']}`",
        "",
        "## Research Question",
        "",
        case["research_question"],
        "",
        "## Exactly How ToolUniverse Was Used",
        "",
        "The script created one `ToolUniverse` instance, selectively loaded four VSD tools, and executed every step through `run_one_function()` with caching disabled:",
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
            "## Descriptive Result",
            "",
            (
                f"CDC PLACES returned **{summary['tract_count']}** Autauga County "
                f"census-tract estimates for {', '.join(summary['years'])}. The "
                f"unweighted tract mean was **{summary['mean_estimate_pct']}%**, "
                f"the median was **{summary['median_estimate_pct']}%**, and the "
                f"observed range was **{summary['observed_range_percentage_points']} "
                "percentage points**."
            ),
            "",
            "| Bound | Census tract | Estimate | 95% confidence interval |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for label_name, key in (("Minimum", "minimum"), ("Maximum", "maximum")):
        item = summary[key]
        interval = " to ".join(str(value) for value in item["confidence_interval_pct"])
        lines.append(
            f"| {label_name} | {item['census_tract']} | "
            f"{item['estimate_pct']}% | {interval}% |"
        )

    lines.extend(
        [
            "",
            "Independent context retrieved by the other typed tools:",
            "",
            f"- WHO indicator `{who['indicator_code']}`: {who['indicator_name']}.",
            (
                f"- openFDA label `{label['set_id']}`: {label['brand_name']} "
                f"({label['generic_name']}, {label['route']}); matched warning terms: "
                + ", ".join(f"`{term}`" for term in label["warning_terms_found"])
                + "."
            ),
            "",
            "## Why VSD Was Useful",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in artifact["vsd_contribution"])
    lines.extend(["", "## What This Does Not Prove", ""])
    lines.extend(f"- {value}" for value in case["interpretation_limits"])
    lines.extend(["", "## Provenance", ""])
    for source in artifact["provenance"]:
        lines.append(
            f"- **{source['provider']}**: `{source['endpoint']}`; HTTP "
            f"{source['http_status']}; {source['response_bytes']} bytes; "
            f"SHA-256 `{source['payload_sha256']}`."
        )
    return "\n".join(lines) + "\n"


def run_live() -> StudyRun:
    """Execute every disease-study step through ToolUniverse."""
    tooluniverse = ToolUniverse()
    tooluniverse.load_tools(include_tools=list(TOOL_NAMES), quiet=True)
    loaded = {tool["name"] for tool in tooluniverse.all_tools}
    if loaded != set(TOOL_NAMES):
        raise RuntimeError(f"Unexpected loaded VSD tools: {sorted(loaded)}")

    outputs: dict[str, dict[str, Any]] = {}
    calls: list[dict[str, Any]] = []
    try:
        for sequence, (tool_name, arguments) in enumerate(TOOL_CALLS, start=1):
            result = tooluniverse.run_one_function(
                {"name": tool_name, "arguments": arguments}, use_cache=False
            )
            if not isinstance(result, dict) or result.get("status") != "success":
                raise RuntimeError(f"{tool_name} failed: {result}")
            data = result.get("data")
            if not isinstance(data, dict):
                raise RuntimeError(f"{tool_name} returned a non-object data payload")
            outputs[tool_name] = data
            calls.append(
                {
                    "sequence": sequence,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "status": "success",
                    "output_keys": sorted(data),
                    "result_summary": summarize_tool_result(tool_name, data),
                }
            )
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
    args = parser.parse_args()

    artifact = build_artifact(run_live(), generated_at=utc_now())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(canonical_json(artifact), encoding="utf-8")
    args.markdown.write_text(render_markdown(artifact), encoding="utf-8")
    print(f"Wrote {args.json}")
    print(f"Wrote {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
