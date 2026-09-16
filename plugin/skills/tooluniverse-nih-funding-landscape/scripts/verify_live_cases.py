#!/usr/bin/env python3
"""Run real-data contract checks for the NIH Funding Landscape skill."""

from __future__ import annotations

import sys
import time
from typing import Any

from tooluniverse.opennih_tool import OpenNIHTool


class LiveVerifier:
    """Small dependency-free live regression runner with actionable failures."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.called_operations: set[str] = set()

    def call_raw(self, operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.called_operations.add(operation)
        tool = OpenNIHTool(
            {
                "name": f"OpenNIH_{operation}",
                "type": "OpenNIHTool",
                "operation": operation,
                "timeout": 30,
            }
        )
        result: dict[str, Any] = {}
        for attempt in range(2):
            result = tool.run(arguments)
            if result.get("status") == "success":
                return result
            if attempt == 0:
                time.sleep(1)
        return result

    def call(self, operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.call_raw(operation, arguments)
        if result.get("status") != "success":
            raise RuntimeError(
                f"{operation} failed after one retry: {result.get('error', result)}"
            )
        data = result.get("data")
        if not isinstance(data, dict):
            raise RuntimeError(f"{operation} returned non-object data: {data!r}")
        return data

    def paginate_search(
        self, arguments: dict[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Fetch and reconcile one complete search_grants slice."""
        rows: list[dict[str, Any]] = []
        first_meta: dict[str, Any] | None = None
        for offset in range(0, 100001, 50):
            page = self.call(
                "search_grants",
                {**arguments, "limit": 50, "offset": offset},
            )
            meta = page["meta"]
            if first_meta is None:
                first_meta = meta
                if meta["total"] > 100050:
                    raise RuntimeError(
                        "search_grants slice exceeds the 100,050-row retrieval ceiling: "
                        f"{meta['total']} rows"
                    )
            rows.extend(page["results"])
            if len(rows) >= meta["total"]:
                break
        if first_meta is None or len(rows) != first_meta["total"]:
            raise RuntimeError(
                f"search_grants pagination mismatch: {len(rows)} rows, meta={first_meta}"
            )
        reported_amounts = [
            row["award_amount"] for row in rows if row.get("award_amount") is not None
        ]
        expected_funding = sum(reported_amounts) if reported_amounts else None
        distinct_awards = {
            row["core_project_num"]
            for row in rows
            if row.get("core_project_num") is not None
        }
        if (
            len(reported_amounts) != first_meta["reported_grant_count"]
            or expected_funding != first_meta["total_funding"]
            or len(distinct_awards) != first_meta["distinct_awards"]
        ):
            raise RuntimeError(
                "search_grants value reconciliation mismatch: "
                f"reported={len(reported_amounts)}, funding={expected_funding}, "
                f"distinct={len(distinct_awards)}, meta={first_meta}"
            )
        return first_meta, rows

    def check(self, name: str, condition: bool, detail: Any = None) -> None:
        if condition:
            self.passed += 1
            print(f"PASS {name}")
            return
        self.failed += 1
        print(f"FAIL {name}: {detail!r}")

    def run(self) -> int:
        source = self.call("source_status", {})
        project_source = source.get("project_source", {})
        years = set(project_source.get("fiscal_years", []))
        latest_year = max(years)
        self.check("source corpus loaded", project_source.get("loaded") is True)
        self.check("source covers analysis years", {2012, 2025} <= years, years)
        self.check(
            "source exposes snapshot lag",
            "snapshot" in str(source.get("corpus_lag_note", "")).lower(),
            source.get("corpus_lag_note"),
        )
        self.check(
            "source exposes a current maximum fiscal year",
            latest_year >= 2026,
            latest_year,
        )

        crispr_search = self.call(
            "search_grants",
            {
                "query": "CRISPR",
                "fiscal_year_start": 2012,
                "fiscal_year_end": 2025,
                "limit": 5,
                "offset": 0,
            },
        )
        search_meta = crispr_search["meta"]
        search_rows = crispr_search["results"]
        self.check("topic search returns rows", search_meta["total"] > 0, search_meta)
        self.check(
            "distinct awards do not exceed rows",
            0 < search_meta["distinct_awards"] <= search_meta["total"],
            search_meta,
        )
        self.check(
            "full-slice funding is reported",
            isinstance(search_meta["total_funding"], int)
            and search_meta["total_funding"] > 0,
            search_meta,
        )
        self.check(
            "representative titles match topic",
            bool(search_rows)
            and all("crispr" in row["title"].lower() for row in search_rows),
            [row.get("title") for row in search_rows],
        )

        crispr_trend = self.call(
            "topic_trend",
            {"query": "CRISPR", "fiscal_year_start": 2012, "fiscal_year_end": 2025},
        )
        trend_rows = crispr_trend["data"]
        self.check(
            "topic trend returns requested endpoints",
            trend_rows[0]["fiscal_year"] == 2012
            and trend_rows[-1]["fiscal_year"] == 2025,
            trend_rows,
        )
        self.check(
            "topic trend years stay in window",
            all(2012 <= row["fiscal_year"] <= 2025 for row in trend_rows),
        )
        self.check(
            "reported rows do not exceed rows",
            all(
                row["reported_grant_count"] <= row["grant_count"] for row in trend_rows
            ),
            trend_rows,
        )

        funding_trend = self.call(
            "funding_trend", {"fiscal_year_start": 2024, "fiscal_year_end": 2025}
        )
        funding_rows = funding_trend["data"]
        self.check(
            "system funding trend returns requested years",
            [row["fiscal_year"] for row in funding_rows] == [2024, 2025],
            funding_rows,
        )
        self.check(
            "system funding trend declares all-mechanism scope",
            funding_trend["provenance"]["funding_scope"] == "all_mechanisms",
            funding_trend["provenance"],
        )
        latest_trend = self.call(
            "funding_trend",
            {
                "fiscal_year_start": latest_year - 1,
                "fiscal_year_end": latest_year,
            },
        )
        latest_row = latest_trend["data"][-1]
        self.check(
            "latest fiscal year is explicitly partial",
            latest_row["fiscal_year"] == latest_year
            and latest_row.get("partial") is True,
            latest_trend,
        )
        partial_growth = self.call(
            "funding_growth",
            {
                "fiscal_year_start": latest_year - 1,
                "fiscal_year_end": latest_year,
            },
        )
        self.check(
            "growth endpoint can calculate across a partial year without flagging it",
            isinstance(partial_growth.get("cagr_pct"), (int, float))
            and latest_row.get("partial") is True
            and all("partial" not in row for row in partial_growth["yearly"]),
            {"growth": partial_growth, "trend": latest_trend},
        )

        early_trend = self.call(
            "funding_trend",
            {"fiscal_year_start": 1985, "fiscal_year_end": 1985},
        )
        early_cancer = self.call(
            "search_grants",
            {
                "query": "cancer",
                "fiscal_year_start": 1985,
                "fiscal_year_end": 1985,
                "limit": 5,
                "offset": 0,
            },
        )
        self.check(
            "all-null historical slice preserves counts and null dollars",
            early_trend["data"][0]["grant_count"] > 0
            and early_trend["data"][0]["reported_grant_count"] == 0
            and early_trend["data"][0]["total_funding"] is None
            and early_cancer["meta"]["total"] > 0
            and early_cancer["meta"]["reported_grant_count"] == 0
            and early_cancer["meta"]["total_funding"] is None
            and all(row["award_amount"] is None for row in early_cancer["results"]),
            {"trend": early_trend, "search": early_cancer},
        )

        empty_topic = self.call(
            "topic_trend",
            {
                "query": "zzzxqvnotarealtopic",
                "fiscal_year_start": latest_year - 2,
                "fiscal_year_end": latest_year,
            },
        )
        self.check(
            "unmatched topic window is empty rather than zero-filled",
            empty_topic["data"] == [],
            empty_topic,
        )

        broad_cancer = self.call(
            "search_grants", {"query": "cancer", "limit": 1, "offset": 0}
        )
        last_reachable = self.call(
            "search_grants", {"query": "cancer", "limit": 50, "offset": 100000}
        )
        unreachable = self.call_raw(
            "search_grants", {"query": "cancer", "limit": 50, "offset": 100001}
        )
        self.check(
            "broad search exposes a hard pagination ceiling",
            broad_cancer["meta"]["total"] > 100050
            and last_reachable["meta"]["returned"] > 0
            and unreachable.get("status") == "error"
            and "100000" in str(unreachable.get("error", "")),
            {
                "first": broad_cancer["meta"],
                "last_reachable": last_reachable["meta"],
                "unreachable": unreachable,
            },
        )

        citation_search = self.call("search", {"query": "CRISPR"})
        citation_rows = citation_search["results"]
        self.check(
            "citation search returns canonical hits",
            bool(citation_rows)
            and all(
                {"id", "title", "text", "url"} <= set(row) for row in citation_rows
            ),
            citation_rows,
        )
        component_search = self.call(
            "search_grants",
            {
                "query": "genomics core",
                "fiscal_year_start": latest_year,
                "fiscal_year_end": latest_year,
                "limit": 50,
                "offset": 0,
            },
        )
        canonical_component_search = self.call("search", {"query": "genomics core"})
        components_by_id = {
            row["project_num"]: row for row in component_search["results"]
        }
        canonical_pairs = [
            (components_by_id[row["id"]], row)
            for row in canonical_component_search["results"]
            if row["id"] in components_by_id
        ]
        self.check(
            "canonical parent can hide matching component terms",
            any(
                "genomics" in component["title"].lower()
                and "core" in component["title"].lower()
                and not all(
                    term
                    in f"{canonical.get('title', '')} {canonical.get('text', '')}".lower()
                    for term in ("genomics", "core")
                )
                for component, canonical in canonical_pairs
            ),
            canonical_pairs,
        )

        crispr_cross = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "CRISPR",
                "fiscal_year_start": 2020,
                "fiscal_year_end": 2025,
                "match_strategy": "auto",
            },
        )
        self.check(
            "topic cross reports selected strategy",
            crispr_cross.get("match_strategy") in {"text", "rcdc"},
            crispr_cross,
        )
        self.check(
            "topic cross returns category list",
            isinstance(crispr_cross.get("matched_rcdc_categories"), list),
            crispr_cross,
        )
        self.check(
            "ALL topic cross is one combined scope, not an IC table",
            crispr_cross["ic_scope"]["kind"] == "all_nih_ics"
            and isinstance(crispr_cross.get("top_institutions"), list)
            and not any(
                key in crispr_cross for key in ("ic_breakdown", "top_ics", "ics")
            ),
            crispr_cross,
        )
        paged_meta, paged_rows = self.paginate_search(
            {
                "query": "CRISPR",
                "fiscal_year_start": 2020,
                "fiscal_year_end": 2025,
            }
        )
        rpg_rows = [row for row in paged_rows if row.get("comparable") is True]
        rpg_awards = {
            row["core_project_num"]
            for row in rpg_rows
            if row.get("core_project_num") is not None
        }
        rpg_funding = sum(row.get("award_amount") or 0 for row in rpg_rows)
        self.check(
            "complete topic pagination reconciles to metadata",
            len(paged_rows) == paged_meta["total"]
            and sum(row.get("award_amount") or 0 for row in paged_rows)
            == paged_meta["total_funding"]
            and len(
                {
                    row["core_project_num"]
                    for row in paged_rows
                    if row.get("core_project_num") is not None
                }
            )
            == paged_meta["distinct_awards"],
            paged_meta,
        )
        self.check(
            "topic cross total_grants means distinct RPG awards",
            len(rpg_rows) > len(rpg_awards)
            and len(rpg_awards) == crispr_cross["total_grants"]
            and rpg_funding == crispr_cross["total_funding"],
            {
                "rpg_rows": len(rpg_rows),
                "rpg_awards": len(rpg_awards),
                "rpg_funding": rpg_funding,
                "cross": crispr_cross,
            },
        )
        self.check(
            "fully paginated RPG rows support a multi-IC ranking",
            len({row["ic"] for row in rpg_rows}) > 10,
            {row["ic"] for row in rpg_rows},
        )

        alzheimer_cross = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "Alzheimer",
                "fiscal_year_start": 2020,
                "fiscal_year_end": 2025,
                "match_strategy": "auto",
            },
        )
        alzheimer_categories = alzheimer_cross.get("matched_rcdc_categories", [])
        self.check(
            "distinctive Alzheimer seed selects RCDC",
            alzheimer_cross.get("match_strategy") == "rcdc",
            alzheimer_cross,
        )
        self.check(
            "Alzheimer categories remain on concept",
            bool(alzheimer_categories)
            and all(
                "alzheimer" in category.lower() for category in alzheimer_categories
            ),
            alzheimer_categories,
        )
        historical_rcdc = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "Alzheimer",
                "fiscal_year_start": 1985,
                "fiscal_year_end": 1990,
                "match_strategy": "rcdc",
            },
        )
        historical_auto = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "Alzheimer",
                "fiscal_year_start": 1985,
                "fiscal_year_end": 1990,
                "match_strategy": "auto",
            },
        )
        self.check(
            "forced historical RCDC zero is identified as a coverage floor",
            historical_rcdc["total_grants"] == 0
            and historical_rcdc["total_funding"] is None
            and historical_rcdc["alternate_surface_grants"] > 0
            and "coverage" in historical_rcdc["no_match_note"].lower()
            and historical_auto["match_strategy"] == "text"
            and historical_auto["total_grants"]
            == historical_rcdc["alternate_surface_grants"],
            {"forced": historical_rcdc, "auto": historical_auto},
        )

        ranking = self.call(
            "rank_institutions",
            {
                "fiscal_year_start": 2020,
                "fiscal_year_end": 2025,
                "sort_by": "funding_scale",
                "limit": 10,
                "offset": 0,
            },
        )
        by_name = {row["organization"]: row for row in ranking["rankings"]}
        required_institutions = {
            "JOHNS HOPKINS UNIVERSITY",
            "UNIVERSITY OF PENNSYLVANIA",
        }
        self.check(
            "ranking resolves comparison institutions",
            required_institutions <= set(by_name),
            list(by_name),
        )
        self.check(
            "ranking returns canonical entity IDs",
            all(
                by_name[name]["entity_id"].startswith("nih:duns:")
                for name in required_institutions
            ),
            by_name,
        )

        harvard_search = self.call(
            "search_grants",
            {
                "institution": "Harvard",
                "fiscal_year_start": 2025,
                "fiscal_year_end": 2025,
                "limit": 50,
                "offset": 0,
            },
        )
        harvard_raw_names = {row["org_name"] for row in harvard_search["results"]}
        self.check(
            "institution substring spans multiple raw organizations",
            {
                "HARVARD MEDICAL SCHOOL",
                "HARVARD UNIVERSITY",
                "HARVARD UNIVERSITY D/B/A HARVARD SCHOOL OF PUBLIC HEALTH",
            }
            <= harvard_raw_names
            and "NOT entity-resolved"
            in harvard_search["provenance"]["institution_filter_note"],
            {
                "names": sorted(harvard_raw_names),
                "provenance": harvard_search["provenance"],
            },
        )
        target_harvard_entities = {
            "HARVARD MEDICAL SCHOOL",
            "HARVARD UNIVERSITY",
            "HARVARD UNIVERSITY D/B/A HARVARD SCHOOL OF PUBLIC HEALTH",
        }
        resolved_harvard: dict[str, str] = {}
        funding_scale_top: list[dict[str, Any]] = []
        for offset in range(0, 100001, 50):
            page = self.call(
                "rank_institutions",
                {
                    "fiscal_year_start": 2025,
                    "fiscal_year_end": 2025,
                    "sort_by": "funding_scale",
                    "limit": 50,
                    "offset": offset,
                },
            )
            if offset == 0:
                funding_scale_top = page["rankings"][:5]
            for row in page["rankings"]:
                if row["organization"] in target_harvard_entities:
                    resolved_harvard[row["organization"]] = row["entity_id"]
            if target_harvard_entities <= set(resolved_harvard):
                break
            if offset + 50 >= page["meta"]["total"]:
                break
        self.check(
            "Harvard labels resolve to separate canonical entities",
            target_harvard_entities == set(resolved_harvard)
            and len(set(resolved_harvard.values())) == 3,
            resolved_harvard,
        )
        composite_top = self.call(
            "rank_institutions",
            {
                "fiscal_year_start": 2025,
                "fiscal_year_end": 2025,
                "sort_by": "composite",
                "limit": 5,
                "offset": 0,
            },
        )
        self.check(
            "funding-scale ranking is sorted by funding",
            all(
                left["total_funding"] >= right["total_funding"]
                for left, right in zip(funding_scale_top, funding_scale_top[1:])
            ),
            funding_scale_top,
        )
        self.check(
            "composite and top-funded rankings are distinct objectives",
            [row["organization"] for row in composite_top["rankings"]]
            != [row["organization"] for row in funding_scale_top]
            and composite_top["meta"]["sort_by"] == "composite",
            {
                "composite": composite_top["rankings"],
                "funding_scale": funding_scale_top,
            },
        )

        early_ranking = self.call(
            "rank_institutions",
            {
                "fiscal_year_start": 1985,
                "fiscal_year_end": 1985,
                "sort_by": "funding_scale",
                "limit": 1,
                "offset": 0,
            },
        )
        early_rank_row = early_ranking["rankings"][0]
        early_profile = self.call(
            "get_institution_profile",
            {
                "entity_id": early_rank_row["entity_id"],
                "fiscal_year_start": 1985,
                "fiscal_year_end": 1985,
            },
        )
        early_concentration = self.call(
            "institution_concentration",
            {"fiscal_year_start": 1985, "fiscal_year_end": 1985},
        )
        self.check(
            "pre-1999 ranking-dollar divergence remains detectable",
            early_rank_row["total_funding"] > 0
            and early_rank_row["reported_grant_count"] > 0
            and early_trend["data"][0]["total_funding"] is None
            and early_profile["profile"]["funding_trend"][0]["total_funding"] is None
            and early_concentration["total_funding"] is None,
            {
                "ranking": early_rank_row,
                "system_trend": early_trend,
                "profile": early_profile,
                "concentration": early_concentration,
            },
        )
        self.check(
            "missing historical concentration stays null, not zero",
            early_concentration["gini"] is None
            and early_concentration["hhi"] is None
            and early_concentration["top5_share"] is None
            and early_concentration["top5_institutions"] == []
            and early_concentration["total_institutions"] == 0,
            early_concentration,
        )

        jhu_id = by_name["JOHNS HOPKINS UNIVERSITY"]["entity_id"]
        penn_id = by_name["UNIVERSITY OF PENNSYLVANIA"]["entity_id"]
        jhu_profile = self.call(
            "get_institution_profile",
            {"entity_id": jhu_id, "fiscal_year_start": 2020, "fiscal_year_end": 2025},
        )
        penn_profile = self.call(
            "get_institution_profile",
            {"entity_id": penn_id, "fiscal_year_start": 2020, "fiscal_year_end": 2025},
        )
        self.check(
            "institution profiles resolve",
            jhu_profile["meta"]["found"] is True
            and penn_profile["meta"]["found"] is True,
        )
        self.check(
            "institution profile documents mixed scopes",
            "whole NIH" in jhu_profile["provenance"]["mechanism_mix_scope"]
            and "RPG" in jhu_profile["provenance"]["funding_trend_scope"],
            jhu_profile["provenance"],
        )

        penn_mix = self.call(
            "mechanism_mix",
            {"entity_id": penn_id, "fiscal_year_start": 2020, "fiscal_year_end": 2025},
        )
        shares = [row["share"] for row in penn_mix["classes"]]
        self.check(
            "mechanism shares use fraction units",
            shares and all(0 <= share <= 1 for share in shares),
            shares,
        )
        self.check(
            "mechanism shares reconcile",
            abs(sum(shares) - 1) < 0.001,
            sum(shares),
        )

        penn_growth = self.call(
            "funding_growth",
            {"entity_id": penn_id, "fiscal_year_start": 2020, "fiscal_year_end": 2025},
        )
        self.check(
            "growth percentage is numeric",
            isinstance(penn_growth.get("cagr_pct"), (int, float)),
            penn_growth,
        )
        self.check(
            "growth preserves organization identity",
            penn_growth["meta"]["organization"] == "UNIVERSITY OF PENNSYLVANIA",
            penn_growth["meta"],
        )

        pi_search = self.call(
            "search_grants", {"pi_name": "Bretl, Michelle", "limit": 20, "offset": 0}
        )
        profile_ids = {
            str(row["pi_profile_id"])
            for row in pi_search["results"]
            if row.get("pi_profile_id")
        }
        self.check(
            "PI name-order fallback resolves one ID",
            profile_ids == {"78918667"},
            profile_ids,
        )

        pi_profile = self.call(
            "get_pi_profile", {"profile_id": "78918667", "limit": 20, "offset": 0}
        )
        self.check(
            "PI profile identity matches",
            pi_profile["profile"]["name"] == "BRETL, MICHELLE",
            pi_profile["profile"],
        )
        pi_profile_warning_codes = {
            warning["code"]
            for warning in pi_profile.get("tooluniverse_contract_warnings", [])
        }
        self.check(
            "ordinary PI profile still declares row-level and publication limits",
            {
                "publications_not_exposed",
                "profile_row_counts_not_awards",
            }
            <= pi_profile_warning_codes,
            pi_profile.get("tooluniverse_contract_warnings"),
        )
        zero_window = self.call(
            "get_pi_profile",
            {
                "profile_id": "78918667",
                "fiscal_year_start": 2024,
                "fiscal_year_end": 2024,
                "limit": 20,
                "offset": 0,
            },
        )
        self.check(
            "PI zero-year window is successful and empty",
            zero_window["meta"]["total_grants"] == 0 and zero_window["grants"] == [],
            zero_window,
        )

        concentration_rows = []
        for year in (2000, 2010, 2025):
            concentration_rows.append(
                self.call(
                    "institution_concentration",
                    {"fiscal_year_start": year, "fiscal_year_end": year},
                )
            )
        self.check(
            "concentration returns three snapshots", len(concentration_rows) == 3
        )
        self.check(
            "concentration units are bounded",
            all(
                0 <= row["gini"] <= 1
                and 0 <= row["top5_share"] <= 1
                and 0 <= row["hhi"] <= 10000
                for row in concentration_rows
            ),
            concentration_rows,
        )
        self.check(
            "concentration includes denominator and top five",
            all(
                row["total_institutions"] > 0 and len(row["top5_institutions"]) == 5
                for row in concentration_rows
            ),
            concentration_rows,
        )

        exact_search = self.call(
            "search_grants",
            {"project_num": "1F31DC023096-01", "limit": 10, "offset": 0},
        )
        self.check(
            "exact award search returns one row",
            exact_search["meta"]["total"] == 1
            and exact_search["results"][0]["project_num"] == "1F31DC023096-01",
            exact_search,
        )
        exact_fetch = self.call("fetch", {"id": "1F31DC023096-01"})
        self.check(
            "exact award fetch returns public URL",
            exact_fetch["id"] == "1F31DC023096-01"
            and exact_fetch["url"].startswith("https://opennih.org/projects/"),
            exact_fetch,
        )

        absent_search = self.call(
            "search_grants",
            {"project_num": "1F31DC023096-99", "limit": 10, "offset": 0},
        )
        absent_fetch = self.call_raw("fetch", {"id": "1F31DC023096-99"})
        self.check(
            "snapshot absence stays qualified",
            absent_search["meta"]["total"] == 0
            and absent_fetch.get("status") == "error"
            and "snapshot" in str(absent_fetch.get("error", "")).lower(),
            {"search": absent_search, "fetch": absent_fetch},
        )

        nih_distribution = self.call(
            "activity_code_distribution",
            {"fiscal_year_start": 2025, "fiscal_year_end": 2025},
        )
        nci_distribution = self.call(
            "activity_code_distribution",
            {"fiscal_year_start": 2025, "fiscal_year_end": 2025, "ic": "NCI"},
        )
        self.check(
            "mechanism distribution returns research class",
            nih_distribution["distribution"]["research"]["count"] > 0,
            nih_distribution,
        )
        self.check(
            "NCI alias resolves exactly",
            nci_distribution["meta"]["ic_scope"]["kind"] == "alias"
            and nci_distribution["meta"]["ic_scope"]["matched_ic_names"]
            == ["National Cancer Institute"],
            nci_distribution["meta"],
        )
        annual_2025 = next(row for row in funding_rows if row["fiscal_year"] == 2025)
        class_rows = list(nih_distribution["distribution"].values())
        self.check(
            "mechanism classes reconcile to annual all-mechanism total",
            sum(row["count"] for row in class_rows) == annual_2025["grant_count"]
            and sum(row["total_funding"] for row in class_rows)
            == annual_2025["total_funding"],
            {
                "classes": nih_distribution["distribution"],
                "annual": annual_2025,
            },
        )

        # Public-value cases: these checks protect decision-relevant behavior,
        # not merely response shapes. Exact snapshot totals live in the casebook;
        # relational assertions are less brittle as the public corpus refreshes.
        friedreich_meta, friedreich_rows = self.paginate_search(
            {
                "query": "Friedreich ataxia",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
            }
        )
        self.check(
            "rare-disease public map is fully reconcilable",
            friedreich_meta["total"] >= 90
            and friedreich_meta["distinct_awards"] >= 30
            and friedreich_meta["reported_grant_count"] > 0
            and {row["mechanism_class"] for row in friedreich_rows}
            >= {"research", "intramural", "cooperative"},
            friedreich_meta,
        )
        friedreich_pi_stats: dict[str, dict[str, Any]] = {}
        for row in friedreich_rows:
            name = row.get("contact_pi_name")
            if not name:
                continue
            stats = friedreich_pi_stats.setdefault(
                name,
                {"funding": 0, "awards": set(), "mechanisms": set()},
            )
            stats["funding"] += row.get("award_amount") or 0
            if row.get("core_project_num"):
                stats["awards"].add(row["core_project_num"])
            if row.get("mechanism_class"):
                stats["mechanisms"].add(row["mechanism_class"])
        friedreich_funding_leader = max(
            friedreich_pi_stats, key=lambda name: friedreich_pi_stats[name]["funding"]
        )
        friedreich_award_leader = max(
            friedreich_pi_stats,
            key=lambda name: len(friedreich_pi_stats[name]["awards"]),
        )
        self.check(
            "funding-only expert ranking is detectably misleading",
            friedreich_funding_leader != friedreich_award_leader
            and friedreich_pi_stats[friedreich_funding_leader]["mechanisms"]
            == {"intramural"}
            and len(friedreich_pi_stats[friedreich_funding_leader]["awards"])
            < len(friedreich_pi_stats[friedreich_award_leader]["awards"]),
            {
                "funding_leader": friedreich_funding_leader,
                "funding_leader_stats": friedreich_pi_stats[friedreich_funding_leader],
                "award_leader": friedreich_award_leader,
                "award_leader_stats": friedreich_pi_stats[friedreich_award_leader],
            },
        )

        long_covid = self.call(
            "search_grants",
            {
                "query": "long COVID",
                "fiscal_year_start": 2020,
                "fiscal_year_end": 2025,
                "limit": 5,
                "offset": 0,
            },
        )
        pasc_meta, pasc_rows = self.paginate_search(
            {
                "query": "PASC",
                "fiscal_year_start": 2020,
                "fiscal_year_end": 2025,
            }
        )
        specific_pasc = self.call(
            "search_grants",
            {
                "query": "post-acute sequelae SARS-CoV-2",
                "fiscal_year_start": 2020,
                "fiscal_year_end": 2025,
                "limit": 5,
                "offset": 0,
            },
        )
        self.check(
            "Long-COVID acronym collision remains visible",
            pasc_meta["total_funding"] > 4 * long_covid["meta"]["total_funding"]
            and any("pascall" in row["title"].lower() for row in pasc_rows)
            and specific_pasc["meta"]["distinct_awards"] < pasc_meta["distinct_awards"],
            {
                "long_covid": long_covid["meta"],
                "pasc": pasc_meta,
                "specific": specific_pasc["meta"],
            },
        )

        maternal_meta, maternal_rows = self.paginate_search(
            {
                "query": "maternal mortality",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
            }
        )
        maternal_by_activity: dict[str, dict[str, Any]] = {}
        for row in maternal_rows:
            activity = row["activity_code"]
            stats = maternal_by_activity.setdefault(
                activity, {"funding": 0, "awards": set()}
            )
            stats["funding"] += row.get("award_amount") or 0
            if row.get("core_project_num"):
                stats["awards"].add(row["core_project_num"])
        ot2_share = (
            maternal_by_activity["OT2"]["funding"] / maternal_meta["total_funding"]
        )
        self.check(
            "maternal-mortality headline exposes its dominant outlier",
            ot2_share > 0.8
            and len(maternal_by_activity["OT2"]["awards"]) == 1
            and len(maternal_by_activity["R01"]["awards"])
            > len(maternal_by_activity["OT2"]["awards"]),
            {"ot2_share": ot2_share, "activities": maternal_by_activity},
        )
        maternal_text = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "maternal mortality",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
                "match_strategy": "text",
            },
        )
        maternal_rcdc = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "maternal mortality",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
                "match_strategy": "rcdc",
            },
        )
        self.check(
            "maternal text and RCDC surfaces stay definition-distinct",
            maternal_text["match_strategy"] == "text"
            and maternal_rcdc["match_strategy"] == "rcdc"
            and maternal_rcdc["total_grants"] > 20 * maternal_text["total_grants"]
            and "Maternal Morbidity and Mortality"
            in maternal_rcdc["matched_rcdc_categories"],
            {"text": maternal_text, "rcdc": maternal_rcdc},
        )

        gene_text = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "gene therapy",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
                "match_strategy": "text",
            },
        )
        gene_rcdc = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "gene therapy",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
                "match_strategy": "rcdc",
            },
        )
        broad_gene_categories = {"Genetics", "Immunotherapy", "Regenerative Medicine"}
        self.check(
            "broad gene-therapy category expansion is audited",
            gene_rcdc["total_grants"] > 3 * gene_text["total_grants"]
            and broad_gene_categories <= set(gene_rcdc["matched_rcdc_categories"]),
            {"text": gene_text, "rcdc": gene_rcdc},
        )

        nimh_k23_2015 = self.call(
            "search_grants",
            {
                "ic": "NIMH",
                "activity_code": "K23",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2015,
                "limit": 1,
                "offset": 0,
            },
        )
        nimh_k23_2025 = self.call(
            "search_grants",
            {
                "ic": "NIMH",
                "activity_code": "K23",
                "fiscal_year_start": 2025,
                "fiscal_year_end": 2025,
                "limit": 1,
                "offset": 0,
            },
        )
        nimh_k99_2025 = self.call(
            "search_grants",
            {
                "ic": "NIMH",
                "activity_code": "K99",
                "fiscal_year_start": 2025,
                "fiscal_year_end": 2025,
                "limit": 1,
                "offset": 0,
            },
        )
        nimh_r00_2025 = self.call(
            "search_grants",
            {
                "ic": "NIMH",
                "activity_code": "R00",
                "fiscal_year_start": 2025,
                "fiscal_year_end": 2025,
                "limit": 1,
                "offset": 0,
            },
        )
        self.check(
            "career mechanisms remain separate project-year populations",
            all(
                result["meta"]["ic_scope"]["kind"] == "alias"
                for result in (
                    nimh_k23_2015,
                    nimh_k23_2025,
                    nimh_k99_2025,
                    nimh_r00_2025,
                )
            )
            and nimh_k23_2015["meta"]["total"] > 0
            and nimh_k23_2025["meta"]["total"] > 0
            and nimh_k99_2025["meta"]["total"] > 0
            and nimh_r00_2025["meta"]["total"] > 0
            and nimh_k99_2025["meta"]["total"] != nimh_r00_2025["meta"]["total"],
            {
                "K23_2015": nimh_k23_2015["meta"],
                "K23_2025": nimh_k23_2025["meta"],
                "K99_2025": nimh_k99_2025["meta"],
                "R00_2025": nimh_r00_2025["meta"],
            },
        )

        massachusetts_name_search = self.call(
            "search_grants",
            {
                "institution": "Massachusetts",
                "fiscal_year_start": 2025,
                "fiscal_year_end": 2025,
                "limit": 5,
                "offset": 0,
            },
        )
        boston_name_search = self.call(
            "search_grants",
            {
                "institution": "Boston",
                "fiscal_year_start": 2025,
                "fiscal_year_end": 2025,
                "limit": 5,
                "offset": 0,
            },
        )
        geography_rows = (
            massachusetts_name_search["results"] + boston_name_search["results"]
        )
        self.check(
            "place-name institution filters do not masquerade as geography",
            massachusetts_name_search["meta"]["total"] > 0
            and boston_name_search["meta"]["total"] > 0
            and all(
                "not entity-resolved"
                in result["provenance"]["institution_filter_note"].lower()
                for result in (massachusetts_name_search, boston_name_search)
            )
            and all(
                not ({"city", "state", "zip", "congressional_district"} & set(row))
                for row in geography_rows
            ),
            {
                "Massachusetts": massachusetts_name_search["meta"],
                "Boston": boston_name_search["meta"],
                "sample_keys": sorted(geography_rows[0]),
            },
        )

        health_equity_auto = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "health equity",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
                "match_strategy": "auto",
            },
        )
        health_equity_text = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "health equity",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
                "match_strategy": "text",
            },
        )
        health_equity_rcdc = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "health equity",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
                "match_strategy": "rcdc",
            },
        )
        self.check(
            "modern RCDC vocabulary gap is not reported as topic absence",
            health_equity_auto["match_strategy"] == "text"
            and health_equity_text["total_grants"] > 0
            and health_equity_auto["total_grants"] == health_equity_text["total_grants"]
            and health_equity_rcdc["total_grants"] == 0
            and health_equity_rcdc["total_funding"] is None
            and health_equity_rcdc["matched_rcdc_categories"] == []
            and health_equity_rcdc["alternate_surface_grants"]
            == health_equity_text["total_grants"]
            and "vocabulary gap" in health_equity_rcdc["no_match_note"].lower(),
            {
                "auto": health_equity_auto,
                "text": health_equity_text,
                "rcdc": health_equity_rcdc,
            },
        )
        health_disparities_text = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "health disparities",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
                "match_strategy": "text",
            },
        )
        health_disparities_rcdc = self.call(
            "ic_topic_cross",
            {
                "ic": "ALL",
                "query": "health disparities",
                "fiscal_year_start": 2015,
                "fiscal_year_end": 2025,
                "match_strategy": "rcdc",
            },
        )
        self.check(
            "nearby health-disparities RCDC term remains visibly broader",
            health_disparities_rcdc["total_grants"]
            > 20 * health_disparities_text["total_grants"]
            and len(health_disparities_rcdc["matched_rcdc_categories"]) > 10,
            {
                "text": health_disparities_text,
                "rcdc": health_disparities_rcdc,
            },
        )

        small_business_by_query: dict[str, dict[str, Any]] = {}
        for query in ("artificial intelligence", "machine learning"):
            rows: list[dict[str, Any]] = []
            code_meta: dict[str, dict[str, Any]] = {}
            for activity_code in ("R41", "R42", "R43", "R44"):
                result = self.call(
                    "search_grants",
                    {
                        "query": query,
                        "activity_code": activity_code,
                        "fiscal_year_start": 2025,
                        "fiscal_year_end": 2025,
                        "limit": 50,
                        "offset": 0,
                    },
                )
                code_meta[activity_code] = result["meta"]
                rows.extend(result["results"])
            small_business_by_query[query] = {
                "rows": rows,
                "code_meta": code_meta,
                "awards": {
                    row["core_project_num"]
                    for row in rows
                    if row.get("core_project_num") is not None
                },
                "organizations": {row["org_name"] for row in rows},
            }
        ai_small_business = small_business_by_query["artificial intelligence"]
        ml_small_business = small_business_by_query["machine learning"]
        self.check(
            "small-business landscape covers all four activity codes",
            all(
                set(result["code_meta"]) == {"R41", "R42", "R43", "R44"}
                and all(
                    row["mechanism_class"] == "small_business" for row in result["rows"]
                )
                for result in (ai_small_business, ml_small_business)
            )
            and len(ai_small_business["awards"]) > 0
            and len(ml_small_business["awards"]) > 0,
            small_business_by_query,
        )
        small_business_union = ai_small_business["awards"] | ml_small_business["awards"]
        self.check(
            "AI small-business synonyms add distinct award coverage",
            len(small_business_union)
            > max(
                len(ai_small_business["awards"]),
                len(ml_small_business["awards"]),
            )
            and len(ml_small_business["rows"]) > len(ml_small_business["awards"]),
            {
                "artificial_intelligence_awards": ai_small_business["awards"],
                "machine_learning_awards": ml_small_business["awards"],
                "union": small_business_union,
            },
        )

        hiv_history = self.call(
            "topic_trend",
            {"query": "HIV", "fiscal_year_start": 1985, "fiscal_year_end": 2005},
        )
        aids_history = self.call(
            "topic_trend",
            {"query": "AIDS", "fiscal_year_start": 1985, "fiscal_year_end": 2005},
        )
        hiv_by_year = {row["fiscal_year"]: row for row in hiv_history["data"]}
        aids_by_year = {row["fiscal_year"]: row for row in aids_history["data"]}
        self.check(
            "historical HIV/AIDS title terminology visibly reverses",
            hiv_by_year[1985]["grant_count"] < aids_by_year[1985]["grant_count"]
            and hiv_by_year[2005]["grant_count"] > aids_by_year[2005]["grant_count"]
            and hiv_by_year[1985]["reported_grant_count"] == 0
            and aids_by_year[1985]["reported_grant_count"] == 0
            and hiv_by_year[1985]["total_funding"] is None
            and aids_by_year[1985]["total_funding"] is None,
            {"HIV": hiv_history, "AIDS": aids_history},
        )

        napierala_candidates = self.call(
            "search_grants",
            {
                "pi_name": "Napierala",
                "fiscal_year_start": 2010,
                "fiscal_year_end": 2025,
                "limit": 50,
                "offset": 0,
            },
        )
        napierala_profile_ids = {
            row["pi_profile_id"]
            for row in napierala_candidates["results"]
            if row.get("pi_profile_id") is not None
        }
        napierala_names = {
            row["contact_pi_name"] for row in napierala_candidates["results"]
        }
        self.check(
            "PI surname discovery exposes multiple identities",
            napierala_candidates["meta"]["total"]
            == len(napierala_candidates["results"])
            and len(napierala_profile_ids) >= 4
            and len(napierala_names) >= 4,
            {
                "meta": napierala_candidates["meta"],
                "profile_ids": napierala_profile_ids,
                "names": napierala_names,
            },
        )
        marek_napierala = self.call(
            "search_grants",
            {
                "pi_name": "NAPIERALA, MAREK",
                "fiscal_year_start": 2010,
                "fiscal_year_end": 2025,
                "limit": 50,
                "offset": 0,
            },
        )
        transferred_core_rows = [
            row
            for row in marek_napierala["results"]
            if row.get("core_project_num") == "R01NS121038"
        ]
        self.check(
            "one core award remains one award across an institution transfer",
            len(transferred_core_rows) >= 5
            and len({row["org_name"] for row in transferred_core_rows}) >= 2
            and any(row["project_num"].startswith("7") for row in transferred_core_rows)
            and {row["core_project_num"] for row in transferred_core_rows}
            == {"R01NS121038"},
            transferred_core_rows,
        )
        core_fetch = self.call_raw("fetch", {"id": "R01NS121038"})
        full_transfer_fetch = self.call("fetch", {"id": "5R01NS121038-05"})
        self.check(
            "core project number is a grouping key, not a fetch identifier",
            core_fetch.get("status") == "error"
            and "full project number" in core_fetch.get("error", "").lower()
            and full_transfer_fetch["metadata"]["core_project_num"] == "R01NS121038",
            {"core_fetch": core_fetch, "full_fetch": full_transfer_fetch},
        )

        multicomponent_search = self.call(
            "search_grants",
            {
                "project_num": "1U54AG099000-01",
                "fiscal_year_start": 2026,
                "fiscal_year_end": 2026,
                "limit": 50,
                "offset": 0,
            },
        )
        multicomponent_rows = multicomponent_search["results"]
        multicomponent_amounts = [
            row["award_amount"]
            for row in multicomponent_rows
            if row.get("award_amount") is not None
        ]
        parent_amount = max(multicomponent_amounts)
        search_warning_codes = {
            warning["code"]
            for warning in multicomponent_search.get(
                "tooluniverse_contract_warnings", []
            )
        }
        self.check(
            "multi-component row sum visibly doubles parent dollars",
            multicomponent_search["meta"]["total"] == 7
            and multicomponent_search["meta"]["unique_project_nums"] == 1
            and multicomponent_search["meta"]["distinct_awards"] == 1
            and len(multicomponent_amounts) == 7
            and sum(multicomponent_amounts) - parent_amount == parent_amount
            and multicomponent_search["meta"]["total_funding"] == 2 * parent_amount,
            multicomponent_search,
        )
        self.check(
            "adapter warns about duplicate full-project funding rows",
            "duplicate_full_project_rows" in search_warning_codes,
            multicomponent_search.get("tooluniverse_contract_warnings"),
        )
        multicomponent_first_row = self.call(
            "search_grants",
            {
                "project_num": "1U54AG099000-01",
                "fiscal_year_start": 2026,
                "fiscal_year_end": 2026,
                "limit": 1,
                "offset": 0,
            },
        )
        first_row_warnings = multicomponent_first_row.get(
            "tooluniverse_contract_warnings", []
        )
        self.check(
            "slice metadata warns even when duplicates fall outside the page",
            len(multicomponent_first_row["results"]) == 1
            and any(
                warning.get("code") == "duplicate_full_project_rows"
                and warning.get("slice_total_rows") == 7
                and warning.get("slice_unique_project_nums") == 1
                for warning in first_row_warnings
            ),
            multicomponent_first_row,
        )
        multicomponent_fetch = self.call("fetch", {"id": "1U54AG099000-01"})
        fetch_warning_codes = {
            warning["code"]
            for warning in multicomponent_fetch.get(
                "tooluniverse_contract_warnings", []
            )
        }
        self.check(
            "canonical fetch exposes matching component rows",
            multicomponent_fetch["metadata"]["award_amount"] == parent_amount
            and multicomponent_fetch["metadata"]["matching_rows"] == 7
            and "canonical_fetch_has_components" in fetch_warning_codes,
            multicomponent_fetch,
        )

        crimmins_profile = self.call(
            "get_pi_profile",
            {
                "profile_id": "1891769",
                "fiscal_year_start": 2026,
                "fiscal_year_end": 2026,
                "limit": 20,
                "offset": 0,
            },
        )
        crimmins_u54_rows = [
            row
            for row in crimmins_profile["grants"]
            if row.get("project_num") == "1U54AG099000-01"
        ]
        profile_warning_codes = {
            warning["code"]
            for warning in crimmins_profile.get("tooluniverse_contract_warnings", [])
        }
        self.check(
            "PI profile duplicate components inflate row-level totals",
            crimmins_profile["profile"]["grant_count"]
            == len(crimmins_profile["grants"])
            == 4
            and len(crimmins_u54_rows) == 3
            and all(
                row.get("award_amount") == parent_amount for row in crimmins_u54_rows
            )
            and crimmins_profile["profile"]["total_funding"]
            == sum(row.get("award_amount") or 0 for row in crimmins_profile["grants"]),
            crimmins_profile,
        )
        self.check(
            "PI profile warnings cover publications rows and collaborator semantics",
            {
                "publications_not_exposed",
                "profile_row_counts_not_awards",
                "shared_award_not_direct_collaboration",
                "collaborators_not_year_filtered",
            }
            <= profile_warning_codes
            and "publications" not in crimmins_profile
            and len(crimmins_profile["collaborators"]) >= 4,
            {
                "warning_codes": profile_warning_codes,
                "profile": crimmins_profile,
            },
        )

        crimmins_empty_window = self.call(
            "get_pi_profile",
            {
                "profile_id": "1891769",
                "fiscal_year_start": 2100,
                "fiscal_year_end": 2100,
                "limit": 20,
                "offset": 0,
            },
        )
        empty_window_warning_codes = {
            warning["code"]
            for warning in crimmins_empty_window.get(
                "tooluniverse_contract_warnings", []
            )
        }
        self.check(
            "PI collaborators are not filtered by the requested grant window",
            crimmins_empty_window["meta"]["total_grants"] == 0
            and crimmins_empty_window["grants"] == []
            and len(crimmins_empty_window["collaborators"]) >= 4
            and "collaborators_not_year_filtered" in empty_window_warning_codes,
            crimmins_empty_window,
        )

        fauci_history = self.call(
            "search_grants",
            {
                "pi_name": "Fauci",
                "fiscal_year_start": 1985,
                "fiscal_year_end": 1998,
                "limit": 50,
                "offset": 0,
            },
        )
        fauci_profile_ids = {
            str(row["pi_profile_id"])
            for row in fauci_history["results"]
            if row.get("contact_pi_name") == "FAUCI, A S"
            and row.get("pi_profile_id") is not None
        }
        self.check(
            "historical normalized PI identity can fragment across profile IDs",
            len(fauci_profile_ids) >= 5,
            {
                "profile_ids": sorted(fauci_profile_ids),
                "meta": fauci_history["meta"],
            },
        )

        legacy_ic = self.call(
            "search_grants",
            {
                "ic": "NIADDK",
                "fiscal_year_start": 1985,
                "fiscal_year_end": 1986,
                "limit": 3,
                "offset": 0,
            },
        )
        modern_ic = self.call(
            "search_grants",
            {
                "ic": "NIDDK",
                "fiscal_year_start": 1985,
                "fiscal_year_end": 1986,
                "limit": 3,
                "offset": 0,
            },
        )
        self.check(
            "legacy IC abbreviation is not treated as a historical crosswalk",
            legacy_ic["meta"]["total"] == 0
            and legacy_ic["meta"]["ic_scope"]["kind"] == "fragment"
            and modern_ic["meta"]["ic_scope"]["kind"] == "alias"
            and modern_ic["meta"]["ic_scope"]["n"] > 1,
            {"legacy": legacy_ic["meta"], "modern": modern_ic["meta"]},
        )
        fragment_ic = self.call(
            "search_grants",
            {
                "ic": "National Institute",
                "fiscal_year_start": 2025,
                "fiscal_year_end": 2025,
                "limit": 1,
                "offset": 0,
            },
        )
        fragment_scope = fragment_ic["meta"]["ic_scope"]
        self.check(
            "broad IC name is exposed as a multi-label fragment",
            fragment_scope["kind"] == "fragment"
            and fragment_scope["n"] > 1
            and "arbitrary subset" in fragment_scope["fragment_note"],
            fragment_scope,
        )
        self.check(
            "fragment IC count/list/display-name divergence remains detectable",
            fragment_scope["n"] != len(fragment_scope["matched_ic_names"])
            and len(set(fragment_scope["matched_ic_names"]))
            < len(fragment_scope["matched_ic_names"]),
            {
                "n": fragment_scope["n"],
                "matched_len": len(fragment_scope["matched_ic_names"]),
                "unique_display_names": len(set(fragment_scope["matched_ic_names"])),
            },
        )
        self.check(
            "live regression exercises every OpenNIH operation",
            OpenNIHTool.SUPPORTED_OPERATIONS <= self.called_operations,
            {
                "missing": sorted(
                    OpenNIHTool.SUPPORTED_OPERATIONS - self.called_operations
                ),
                "called": sorted(self.called_operations),
            },
        )

        print(
            f"\nTotal: {self.passed + self.failed} | PASS: {self.passed} | FAIL: {self.failed}"
        )
        return 0 if self.failed == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(LiveVerifier().run())
    except Exception as exc:
        print(f"FATAL live verification error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
