#!/usr/bin/env python3
"""Verify one exact NIH grant-to-publication/trial evidence chain."""

from __future__ import annotations

import sys
import time
from typing import Any

from tooluniverse import ToolUniverse


class OutputLinkVerifier:
    """Exercise cross-source identifiers and semantic guardrails on live data."""

    TOOL_NAMES = [
        "PubMed_search_articles",
        "iCite_get_publications",
        "ClinicalTrials_search_studies",
        "ClinicalTrials_get_study",
    ]

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.tu = ToolUniverse()
        self.tu.load_tools(include_tools=self.TOOL_NAMES)

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        result: Any = None
        for attempt in range(2):
            result = self.tu.run({"name": name, "arguments": arguments})
            if not (isinstance(result, dict) and result.get("status") == "error"):
                return result
            if attempt == 0:
                time.sleep(1)
        raise RuntimeError(f"{name} failed after one retry: {result!r}")

    @staticmethod
    def unwrap_status(result: Any) -> Any:
        """Remove one generic success envelope without assuming tool internals."""
        if isinstance(result, dict) and result.get("status") == "success":
            return result.get("data")
        return result

    @classmethod
    def find_list(cls, result: Any, key: str) -> list[Any]:
        """Find a named list through generic REST and ToolUniverse envelopes."""
        current = cls.unwrap_status(result)
        for _ in range(4):
            if isinstance(current, dict):
                value = current.get(key)
                if isinstance(value, list):
                    return value
                current = current.get("data")
                continue
            break
        return []

    @classmethod
    def find_value(cls, result: Any, key: str) -> Any:
        """Find one named value through generic REST envelopes."""
        current = cls.unwrap_status(result)
        for _ in range(4):
            if isinstance(current, dict):
                if key in current:
                    return current[key]
                current = current.get("data")
                continue
            break
        return None

    def check(self, name: str, condition: bool, detail: Any = None) -> None:
        if condition:
            self.passed += 1
            print(f"PASS {name}")
            return
        self.failed += 1
        print(f"FAIL {name}: {detail!r}")

    def run(self) -> int:
        articles = self.call(
            "PubMed_search_articles",
            {"query": "R01NS121038[Grant Number]", "limit": 20},
        )
        article_rows = self.unwrap_status(articles)
        if not isinstance(article_rows, list):
            raise RuntimeError(f"PubMed returned an unexpected shape: {articles!r}")
        articles_by_pmid = {
            str(row.get("pmid")): row
            for row in article_rows
            if isinstance(row, dict) and row.get("pmid")
        }
        expected_pmids = {"37691621", "41514384"}
        self.check(
            "exact grant-number search preserves both PMIDs",
            expected_pmids <= set(articles_by_pmid),
            articles_by_pmid,
        )
        self.check(
            "exact linked papers retain distinct publication years",
            str(articles_by_pmid.get("37691621", {}).get("pub_year")) == "2023"
            and str(articles_by_pmid.get("41514384", {}).get("pub_year"))
            in {"2025", "2026"},
            articles_by_pmid,
        )

        icite = self.call("iCite_get_publications", {"pmids": "37691621,41514384"})
        metric_rows = self.find_list(icite, "data")
        metrics_by_pmid = {
            str(row.get("pmid")): row
            for row in metric_rows
            if isinstance(row, dict) and row.get("pmid") is not None
        }
        self.check(
            "iCite returns both exact publication records",
            expected_pmids <= set(metrics_by_pmid),
            icite,
        )
        older_metrics = metrics_by_pmid.get("37691621", {})
        self.check(
            "iCite fields remain metrics rather than outcome claims",
            isinstance(older_metrics.get("citation_count"), int)
            and older_metrics.get("citation_count") >= 7
            and isinstance(older_metrics.get("relative_citation_ratio"), (int, float))
            and 0 <= older_metrics.get("apt", -1) <= 1
            and older_metrics.get("is_clinical") is False,
            older_metrics,
        )

        exact_trials = self.call(
            "ClinicalTrials_search_studies",
            {"query_term": "R01NS121038", "page_size": 20},
        )
        self.check(
            "exact grant-number trial search returns no attributed trial",
            self.find_value(exact_trials, "total_count") == 0
            and self.find_list(exact_trials, "studies") == [],
            exact_trials,
        )

        topic_trials = self.call(
            "ClinicalTrials_search_studies",
            {"query_cond": "Friedreich ataxia", "page_size": 20},
        )
        self.check(
            "disease search returns topical candidates only",
            isinstance(self.find_value(topic_trials, "total_count"), int)
            and self.find_value(topic_trials, "total_count") >= 100,
            topic_trials,
        )

        trial_summary = self.call(
            "ClinicalTrials_search_studies",
            {"query_term": "NCT04102501", "page_size": 10},
        )
        summary_rows = self.find_list(trial_summary, "studies")
        summary = next(
            (row for row in summary_rows if row.get("nct_id") == "NCT04102501"),
            {},
        )
        self.check(
            "trial search summary visibly omits selected detail fields",
            bool(summary)
            and summary.get("sponsor") is None
            and summary.get("enrollment") is None
            and summary.get("interventions") == [],
            trial_summary,
        )

        study_result = self.call("ClinicalTrials_get_study", {"nct_id": "NCT04102501"})
        study = self.unwrap_status(study_result)
        if isinstance(study, dict) and "data" in study:
            study = study["data"]
        if not isinstance(study, dict):
            raise RuntimeError(
                f"ClinicalTrials_get_study returned an unexpected shape: {study_result!r}"
            )
        intervention_names = {
            str(item.get("name", "")).upper()
            for item in study.get("interventions", [])
            if isinstance(item, dict)
        }
        self.check(
            "trial detail restores phase enrollment sponsor and interventions",
            "PHASE3" in study.get("phases", [])
            and study.get("status") == "COMPLETED"
            and study.get("enrollment") == 65
            and "BIOJIVA" in str(study.get("sponsor", "")).upper()
            and {"RT001", "PLACEBO"} <= intervention_names,
            study,
        )
        self.check(
            "detail record remains a topical candidate without grant attribution",
            not any(
                "R01NS121038" in str(value)
                for value in (
                    study.get("brief_title"),
                    study.get("official_title"),
                    study.get("brief_summary"),
                    study.get("references"),
                )
            ),
            study,
        )

        print(
            f"\nTotal: {self.passed + self.failed} | "
            f"PASS: {self.passed} | FAIL: {self.failed}"
        )
        return 0 if self.failed == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(OutputLinkVerifier().run())
    except Exception as exc:
        print(f"FATAL output-link verification error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
