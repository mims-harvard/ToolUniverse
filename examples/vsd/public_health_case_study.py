"""Build a bounded, provenance-rich public-health snapshot with VSD.

The live workflow intentionally retains only aggregate or public product metadata.
Raw upstream responses are hashed for provenance and are not written to disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_SRC = Path(__file__).resolve().parents[2] / "src"
if str(REPOSITORY_SRC) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_SRC))

import tooluniverse.vsd_tool as vsd_tool  # noqa: E402


SCHEMA_VERSION = 1
CASE_STUDY_ID = "cardiovascular_public_health_snapshot"
DEFAULT_JSON_PATH = Path(__file__).with_name("artifacts") / "snapshot.json"
DEFAULT_MARKDOWN_PATH = Path(__file__).with_name("artifacts") / "snapshot.md"

SOURCES: tuple[dict[str, Any], ...] = (
    {
        "source_id": "who_gho",
        "provider": "WHO Global Health Observatory",
        "endpoint": "https://ghoapi.azureedge.net/api/Indicator",
        "description": "WHO hypertension indicator metadata.",
        "params": {
            "$filter": "IndicatorCode eq 'NCD_HYP_DIAGNOSIS_C'",
            "$select": "IndicatorCode,IndicatorName,Language",
            "$top": 1,
        },
    },
    {
        "source_id": "cdc_places",
        "provider": "CDC PLACES",
        "endpoint": "https://chronicdata.cdc.gov/resource/cwsq-ngmh.json",
        "description": "Aggregate Alabama census-tract coronary-heart-disease estimates.",
        "params": {
            "$select": (
                "year,stateabbr,countyname,locationname,measure,data_value,"
                "low_confidence_limit,high_confidence_limit"
            ),
            "$where": (
                "stateabbr='AL' AND measure='Coronary heart disease among adults'"
            ),
            "$order": "locationname ASC",
            "$limit": 5,
        },
    },
    {
        "source_id": "openfda_labels",
        "provider": "openFDA Drug Labels",
        "endpoint": "https://api.fda.gov/drug/label.json",
        "description": "One identified public aspirin product label.",
        "params": {
            "search": 'set_id:"0058175f-3474-40c3-a046-6cfaec86d84b"',
            "limit": 1,
        },
    },
)


@dataclass(frozen=True)
class SourceResult:
    definition: dict[str, Any]
    payload: Any
    request: dict[str, Any]


def canonical_json(value: Any) -> str:
    """Return the stable JSON representation used for artifacts and hashes."""
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def payload_sha256(payload: Any) -> str:
    compact = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(compact).hexdigest()


def _first_text(value: Any) -> str | None:
    if isinstance(value, list) and value and isinstance(value[0], str):
        return value[0]
    return value if isinstance(value, str) else None


def transform_who(payload: Any) -> dict[str, Any]:
    rows = payload.get("value") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError("WHO response must contain exactly one indicator row")
    row = rows[0]
    return {
        "indicator_code": row.get("IndicatorCode"),
        "indicator_name": row.get("IndicatorName"),
        "language": row.get("Language"),
    }


def transform_cdc(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("CDC response must be a list")
    fields = (
        "year",
        "stateabbr",
        "countyname",
        "locationname",
        "measure",
        "data_value",
        "low_confidence_limit",
        "high_confidence_limit",
    )
    rows = [
        {field: row.get(field) for field in fields}
        for row in payload
        if isinstance(row, dict)
    ]
    if len(rows) != len(payload) or len(rows) > 5:
        raise ValueError("CDC response must contain at most five object rows")
    return sorted(rows, key=lambda row: str(row["locationname"]))


def transform_openfda(payload: Any) -> dict[str, Any]:
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError("openFDA response must contain exactly one label")
    label = rows[0]
    metadata = label.get("openfda") if isinstance(label.get("openfda"), dict) else {}
    warning = " ".join(label.get("warnings") or []).casefold()
    warning_terms = sorted(
        term
        for term in ("blood thinning", "heart disease", "high blood pressure")
        if term in warning
    )
    return {
        "set_id": label.get("set_id"),
        "effective_time": label.get("effective_time"),
        "brand_name": _first_text(metadata.get("brand_name")),
        "generic_name": _first_text(metadata.get("generic_name")),
        "route": _first_text(metadata.get("route")),
        "warning_terms_found": warning_terms,
    }


def build_artifact(results: list[SourceResult], *, generated_at: str) -> dict[str, Any]:
    """Transform live or fixture responses into the checked artifact schema."""
    by_id = {item.definition["source_id"]: item for item in results}
    missing = {source["source_id"] for source in SOURCES} - set(by_id)
    if missing:
        raise ValueError(f"Missing source results: {sorted(missing)}")

    provenance = []
    for source_id in sorted(by_id):
        item = by_id[source_id]
        request = item.request
        provenance.append(
            {
                "source_id": source_id,
                "provider": item.definition["provider"],
                "endpoint": item.definition["endpoint"],
                "query_params": item.definition["params"],
                "http_status": request.get("status_code"),
                "content_type": request.get("content_type"),
                "response_bytes": request.get("response_bytes"),
                "redirects": request.get("redirects"),
                "payload_sha256": payload_sha256(item.payload),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "case_study": {
            "id": CASE_STUDY_ID,
            "title": "Cardiovascular public-health evidence snapshot",
            "generated_at": generated_at,
            "purpose": (
                "Demonstrate bounded, attributable retrieval across independent "
                "public scientific sources."
            ),
            "interpretation_limits": [
                "The three datasets are independent and must not be joined at record level.",
                "The snapshot does not establish causation, treatment efficacy, or clinical advice.",
                "CDC rows are aggregate model-based estimates, not individual observations.",
                "openFDA labeling is unvalidated upstream data and must not guide medical care.",
            ],
        },
        "observations": {
            "who_indicator": transform_who(by_id["who_gho"].payload),
            "cdc_places_estimates": transform_cdc(by_id["cdc_places"].payload),
            "openfda_label": transform_openfda(by_id["openfda_labels"].payload),
        },
        "provenance": provenance,
    }


def render_markdown(artifact: dict[str, Any]) -> str:
    case = artifact["case_study"]
    observations = artifact["observations"]
    who = observations["who_indicator"]
    label = observations["openfda_label"]
    lines = [
        f"# {case['title']}",
        "",
        f"Generated: `{case['generated_at']}`",
        "",
        "## Result",
        "",
        f"WHO indicator `{who['indicator_code']}` is **{who['indicator_name']}**.",
        "",
        "CDC PLACES aggregate estimates:",
        "",
        "| Year | State | County | Census tract | Estimate (%) | 95% interval |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in observations["cdc_places_estimates"]:
        interval = f"{row['low_confidence_limit']} to {row['high_confidence_limit']}"
        lines.append(
            f"| {row['year']} | {row['stateabbr']} | {row['countyname']} | "
            f"{row['locationname']} | {row['data_value']} | {interval} |"
        )
    lines.extend(
        [
            "",
            (
                f"The public openFDA label `{label['set_id']}` identifies "
                f"{label['brand_name']} ({label['generic_name']}, {label['route']})."
            ),
            "Warning phrases found: "
            + ", ".join(f"`{term}`" for term in label["warning_terms_found"])
            + ".",
            "",
            "## Interpretation Limits",
            "",
        ]
    )
    lines.extend(f"- {limit}" for limit in case["interpretation_limits"])
    lines.extend(["", "## Provenance", ""])
    for source in artifact["provenance"]:
        lines.append(
            f"- **{source['provider']}**: `{source['endpoint']}`; HTTP "
            f"{source['http_status']}; SHA-256 `{source['payload_sha256']}`."
        )
    return "\n".join(lines) + "\n"


def run_live() -> list[SourceResult]:
    """Exercise register/query/remove using an isolated temporary catalog."""
    results: list[SourceResult] = []
    previous_dir = os.environ.get("TOOLUNIVERSE_VSD_DIR")
    with tempfile.TemporaryDirectory(
        prefix="tooluniverse-vsd-case-study-"
    ) as directory:
        os.environ["TOOLUNIVERSE_VSD_DIR"] = directory
        try:
            for definition in SOURCES:
                registration = {
                    "source_id": definition["source_id"],
                    "endpoint": definition["endpoint"],
                    "name": definition["provider"],
                    "description": definition["description"],
                    "default_params": definition["params"],
                }
                vsd_tool.VSDRegisterSource({}).run(registration)
                response = vsd_tool.VSDQuerySource({}).run(
                    {"source_id": definition["source_id"]}
                )["data"]
                results.append(
                    SourceResult(definition, response["result"], response["request"])
                )
            for definition in SOURCES:
                vsd_tool.VSDRemoveSource({}).run({"source_id": definition["source_id"]})
        finally:
            if previous_dir is None:
                os.environ.pop("TOOLUNIVERSE_VSD_DIR", None)
            else:
                os.environ["TOOLUNIVERSE_VSD_DIR"] = previous_dir
    return results


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

    generated_at = utc_now()
    artifact = build_artifact(run_live(), generated_at=generated_at)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(canonical_json(artifact), encoding="utf-8")
    args.markdown.write_text(render_markdown(artifact), encoding="utf-8")
    print(f"Wrote {args.json}")
    print(f"Wrote {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
