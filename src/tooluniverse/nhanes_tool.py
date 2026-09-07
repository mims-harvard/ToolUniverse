"""
NHANES Tool

Provides information about NHANES (National Health and Nutrition Examination Survey) datasets.
Supports dataset discovery, search, and direct XPT download+parse for analysis.
"""

import io
import math
import re
from typing import Dict, Any, Optional

import pandas as pd
import requests

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("NHANESTool")
class NHANESTool(BaseTool):
    """NHANES data information tool."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]

    # Published NHANES continuous cycles, newest first. Each is a real CDC
    # release; note there is no standalone 2019-2020 cycle -- field work was
    # cut short by COVID-19 and those data ship as the "2017-2020 pre-pandemic"
    # files instead.
    _CYCLES = [
        "2021-2023",
        "2017-2018",
        "2015-2016",
        "2013-2014",
        "2011-2012",
        "2009-2010",
        "2007-2008",
        "2005-2006",
        "2003-2004",
        "2001-2002",
        "1999-2000",
    ]

    _COMPONENTS = [
        "Demographics",
        "Dietary",
        "Examination",
        "Laboratory",
        "Questionnaire",
    ]

    @staticmethod
    def _datapage_url(component: str, cycle: str) -> str:
        """Build the CDC data-listing URL for a component within a cycle."""
        return (
            "https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx"
            f"?Component={component}&CycleBeginYear={cycle.split('-')[0]}"
        )

    def _get_dataset_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get NHANES dataset information."""
        year = arguments.get("year")
        component = arguments.get("component")

        # An unrecognised cycle used to fall through to the two most recent
        # ones, so asking for 2021-2023 returned rows labelled 2017-2018 under
        # status "success". Reject it instead of answering about another year.
        if year and year not in self._CYCLES:
            return {
                "status": "error",
                "error": (
                    f"Unknown NHANES cycle '{year}'. Valid cycles: "
                    f"{', '.join(self._CYCLES)}. NHANES has no standalone "
                    "2019-2020 cycle; those data are published as the "
                    "'2017-2020 pre-pandemic' files."
                ),
            }

        cycles_to_show = [year] if year else self._CYCLES[:2]
        components = [component] if component else self._COMPONENTS

        datasets = [
            {
                "name": f"NHANES {comp} - {cycle}",
                "year": cycle,
                "component": comp,
                "download_url": self._datapage_url(comp, cycle),
                "description": f"NHANES {comp} data for {cycle}",
            }
            for cycle in cycles_to_show
            for comp in components
        ]

        return {
            "status": "success",
            "data": {
                "datasets": datasets,
                "count": len(datasets),
                "cycles_covered": cycles_to_show,
                "note": "download_url opens the CDC listing of data files for that component and cycle. Files are XPT (SAS transport); use NHANES_download_and_parse to fetch and parse one directly.",
            },
            "metadata": {
                "source": "CDC NHANES",
                "endpoint": self.endpoint,
                "query": arguments,
            },
        }

    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search NHANES variable list dynamically via CDC website.

        Queries the actual NHANES variable catalog at wwwn.cdc.gov instead
        of using hardcoded keyword lists.
        """
        search_term = arguments.get("search_term", "").lower()
        year = arguments.get("year")
        limit = arguments.get("limit", 20)

        # Omitting `year` used to silently restrict the search to a single
        # hardcoded cycle (2017-2018), which reported a false "no results"
        # for datasets renamed or dropped in that one cycle (e.g. searching
        # "phenols" found nothing even though other cycles measured them).
        # Search the two most recent cycles by default instead, matching
        # `_get_dataset_info`'s documented "omit year -> two most recent
        # cycles" behavior.
        cycles = [year] if year else self._CYCLES[:2]
        components = [
            "Demographics",
            "Dietary",
            "Examination",
            "Laboratory",
            "Questionnaire",
        ]

        datasets: list = []
        seen_files: set = set()
        cycles_searched: list = []
        for cycle in cycles:
            cycles_searched.append(cycle)
            self._search_cycle(cycle, components, search_term, limit, datasets, seen_files)
            if len(datasets) >= limit:
                break

        return {
            "status": "success",
            "data": {
                "datasets": datasets,
                "count": len(datasets),
                "search_term": search_term,
                "cycles_searched": cycles_searched,
            },
            "metadata": {
                "source": "NHANES Variable List (wwwn.cdc.gov)",
                "components_searched": components,
            },
        }

    def _search_cycle(
        self,
        cycle: str,
        components: list,
        search_term: str,
        limit: int,
        datasets: list,
        seen_files: set,
    ) -> None:
        """Search one NHANES cycle's variable list, appending hits in place."""
        cycle_year = cycle.split("-")[0]
        for component in components:
            url = (
                "https://wwwn.cdc.gov/Nchs/Nhanes/search/variablelist.aspx"
                f"?Component={component}&CycleBeginYear={cycle_year}"
            )
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code != 200:
                    continue
                html = resp.text
                # Each row has 8 <td> cells: VarName, VarDesc, FileName,
                # FileDesc, CycleBegin, CycleEnd, Component, Constraints
                rows = re.findall(
                    r"<td>([^<]+)</td>\s*<td>([^<]+)</td>"
                    r"<td>([^<]+)</td>\s*<td>([^<]+)</td>"
                    r"<td>[^<]*</td>\s*<td>[^<]*</td>"
                    r"<td>[^<]*</td>\s*<td>[^<]*</td>",
                    html,
                )
                for var_name, var_desc, file_name, file_desc in rows:
                    if search_term and not any(
                        search_term in s.lower() for s in [var_desc, var_name, file_desc]
                    ):
                        continue
                    if file_name not in seen_files:
                        seen_files.add(file_name)
                        datasets.append(
                            {
                                "file_name": file_name,
                                "file_description": file_desc,
                                "component": component,
                                "matching_variable": var_name,
                                "variable_description": var_desc,
                                "cycle": cycle,
                                "download_url": (
                                    f"https://wwwn.cdc.gov/Nchs/Nhanes/"
                                    f"{cycle}/DataFiles/{file_name}.XPT"
                                ),
                            }
                        )
                    if len(datasets) >= limit:
                        return
            except Exception:
                continue
            if len(datasets) >= limit:
                return

    # Cycle suffix mapping: cycle -> letter suffix for NHANES filenames
    _CYCLE_SUFFIX = {
        "2011-2012": "_G",
        "2013-2014": "_H",
        "2015-2016": "_I",
        "2017-2018": "_J",
        "2019-2020": "_K",
    }

    # Component -> default filename prefix (without suffix)
    _COMPONENT_PREFIX = {
        "Demographics": "DEMO",
        "Dietary": "DR1TOT",
        "DietaryDay2": "DR2TOT",
        "Examination": "BPX",  # Blood pressure as default exam
        "BodyMeasures": "BMX",
        "Questionnaire": "PFQ",  # Physical functioning as default
    }

    def _resolve_filename(
        self, component: str, cycle: str, dataset_name: Optional[str] = None
    ) -> str:
        """Resolve component + cycle to the XPT filename (without .XPT)."""
        suffix = self._CYCLE_SUFFIX.get(cycle, "")
        if not suffix:
            # Try to derive suffix from cycle year
            start_year = int(cycle.split("-")[0])
            # 2011=G(7th), each +2 years = +1 letter
            idx = (start_year - 2011) // 2
            if 0 <= idx < 26:
                suffix = f"_{chr(ord('G') + idx)}"
            else:
                return ""

        if dataset_name:
            # Fix-R16B-2: nhanes_search_datasets' own results carry the
            # cycle suffix already (e.g. file_name "BMX_J") -- confirmed
            # live that passing that value straight through here appended
            # the suffix a second time ("BMX_J" + "_J" -> 404 downloading
            # BMX_J_J.XPT). Don't double it if it's already present.
            if dataset_name.endswith(suffix):
                return dataset_name
            return f"{dataset_name}{suffix}"

        prefix = self._COMPONENT_PREFIX.get(component)
        if not prefix:
            return ""
        return f"{prefix}{suffix}"

    def _build_xpt_url(self, cycle: str, filename: str) -> str:
        """Build the CDC download URL for an XPT file."""
        start_year = cycle.split("-")[0]
        return (
            f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/"
            f"{start_year}/DataFiles/{filename}.XPT"
        )

    # pandas' XPORT reader converts an all-zero 8-byte IBM float to this exact
    # value instead of 0.0 -- its IBM-to-IEEE754 conversion (_parse_float_vec
    # in pandas.io.sas.sas_xport) has no special case for an all-zero byte
    # pattern, so the exponent-bias arithmetic produces a tiny denormalized
    # double rather than true zero. Confirmed by running that exact function
    # against an 8-zero-byte input: it returns 5.397605346934028e-79 every
    # time, not a range of "small" values, so this can be sanitized as an
    # exact match with no risk to genuine (always much larger) NHANES values.
    _SAS_XPORT_ZERO_ARTIFACT = 5.397605346934028e-79

    def _download_xpt(self, url: str) -> pd.DataFrame:
        """Download and parse an XPT file from CDC. Returns a DataFrame."""
        resp = requests.get(url, timeout=120)
        if resp.status_code != 200:
            raise ValueError(f"HTTP {resp.status_code} downloading {url}")
        # CDC returns XPT content (possibly gzip-transported, requests handles that)
        content = resp.content
        if len(content) < 100:
            raise ValueError(f"Empty or invalid response from {url}")
        # Check for HTML error page (CDC returns 200 with HTML for missing files)
        if content[:5] == b"<!DOC" or content[:5] == b"<html":
            raise ValueError(f"File not found at {url} (CDC returned HTML error page)")
        df = pd.read_sas(io.BytesIO(content), format="xport")
        return df.replace(self._SAS_XPORT_ZERO_ARTIFACT, 0.0)

    @staticmethod
    def _format_age_bounds(age_min, age_max) -> str:
        """Format age bounds into a human-readable string like '>= 60 and <= 80'."""
        parts = []
        if age_min is not None:
            parts.append(f">={age_min}")
        if age_max is not None:
            parts.append(f"<={age_max}")
        return " and ".join(parts)

    @staticmethod
    def _filter_by_age(df: pd.DataFrame, age_min, age_max) -> pd.DataFrame:
        """Filter DataFrame by RIDAGEYR bounds."""
        if age_min is not None:
            df = df[df["RIDAGEYR"] >= age_min]
        if age_max is not None:
            df = df[df["RIDAGEYR"] <= age_max]
        return df

    def _compute_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute summary statistics for numeric columns."""
        stats = {}
        for col in df.select_dtypes(include=["number"]).columns:
            series = df[col].dropna()
            n = len(series)
            if n == 0:
                stats[col] = {
                    "count": 0,
                    "mean": None,
                    "std": None,
                    "min": None,
                    "max": None,
                }
                continue
            stats[col] = {
                "count": n,
                "mean": round(float(series.mean()), 4),
                "std": round(float(series.std()), 4),
                "min": round(float(series.min()), 4),
                "max": round(float(series.max()), 4),
            }
        return stats

    def _download_and_parse(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Download an NHANES XPT file, parse it, and return structured data."""
        component = arguments.get("component", "")
        cycle = arguments.get("cycle", "")
        dataset_name = arguments.get("dataset_name")
        variables = arguments.get("variables")
        age_min = arguments.get("age_min")
        age_max = arguments.get("age_max")
        max_rows = arguments.get("max_rows", 5000)

        if not component or not cycle:
            return {
                "status": "error",
                "error": "Both 'component' and 'cycle' are required.",
            }

        if component == "Laboratory" and not dataset_name:
            return {
                "status": "error",
                "error": (
                    "Laboratory component requires 'dataset_name' "
                    "(e.g., 'CBC', 'BIOPRO', 'GHB', 'GLU', 'TRIGLY', 'HDL', 'TCHOL'). "
                    "Use nhanes_search_datasets to discover available dataset names."
                ),
            }
        # Fix-R16B-1: Examination and Questionnaire, like Laboratory, each
        # span many distinct files (Examination: BMX body measures, BPX
        # blood pressure, AUX audiometry, OHXDEN oral health, ...). The old
        # _COMPONENT_PREFIX fallback silently picked one arbitrary file
        # (BPX for Examination) regardless of which `variables` were
        # actually requested -- confirmed live that requesting BMXBMI/BMXWT
        # without dataset_name silently downloaded the blood-pressure file
        # instead and returned status:"success" with the requested
        # variables missing. Require dataset_name here too, matching the
        # precedent already set for Laboratory.
        if component in ("Examination", "Questionnaire") and not dataset_name:
            return {
                "status": "error",
                "error": (
                    f"'{component}' component has multiple distinct files and "
                    "requires 'dataset_name' to disambiguate which one to "
                    "download (e.g., 'BMX' for body measures, 'BPX' for blood "
                    "pressure under Examination). "
                    "Use nhanes_search_datasets to discover available dataset names."
                ),
            }

        filename = self._resolve_filename(component, cycle, dataset_name)
        if not filename:
            return {
                "status": "error",
                "error": (
                    f"Cannot resolve filename for component='{component}', "
                    f"cycle='{cycle}'. Supported cycles: "
                    f"{', '.join(sorted(self._CYCLE_SUFFIX.keys()))}"
                ),
            }

        url = self._build_xpt_url(cycle, filename)

        try:
            df = self._download_xpt(url)
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        except Exception as exc:
            return {
                "status": "error",
                "error": f"Failed to download/parse {url}: {exc}",
            }

        # Age filtering: merge with DEMO if needed
        age_filter_desc = None
        warnings = []
        if age_min is not None or age_max is not None:
            bounds = self._format_age_bounds(age_min, age_max)
            if component == "Demographics":
                if "RIDAGEYR" in df.columns:
                    df = self._filter_by_age(df, age_min, age_max)
                    age_filter_desc = f"RIDAGEYR {bounds}"
                else:
                    warnings.append("RIDAGEYR not found in Demographics")
            elif "SEQN" in df.columns:
                demo_filename = self._resolve_filename("Demographics", cycle)
                if demo_filename:
                    demo_url = self._build_xpt_url(cycle, demo_filename)
                    try:
                        demo_df = self._download_xpt(demo_url)
                        demo_subset = self._filter_by_age(
                            demo_df[["SEQN", "RIDAGEYR"]], age_min, age_max
                        )
                        valid_seqns = set(demo_subset["SEQN"].dropna())
                        df = df[df["SEQN"].isin(valid_seqns)]
                        age_filter_desc = (
                            f"RIDAGEYR {bounds} (merged with {demo_filename})"
                        )
                    except Exception as exc:
                        warnings.append(
                            f"Age filter failed (could not load DEMO): {exc}"
                        )

        # Variable selection
        if variables:
            cols_to_keep = list(dict.fromkeys(["SEQN"] + variables))
            available = [c for c in cols_to_keep if c in df.columns]
            missing = [c for c in cols_to_keep if c not in df.columns]
            df = df[available]
            if missing:
                warnings.append(f"Missing variables: {missing}")

        total_rows = len(df)
        summary = self._compute_summary_stats(df)

        # Convert to JSON-safe records (replace NaN/inf with None)
        records = df.head(max_rows).to_dict(orient="records")
        for row in records:
            for key, val in row.items():
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    row[key] = None

        metadata: Dict[str, Any] = {
            "source": "CDC NHANES",
            "download_url": url,
            "cycle": cycle,
            "component": component,
            "dataset_name": filename,
        }
        if age_filter_desc:
            metadata["age_filter"] = age_filter_desc
        if variables:
            metadata["variables_requested"] = variables
        if warnings:
            metadata["warnings"] = warnings

        return {
            "status": "success",
            "data": {
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "total_rows": total_rows,
                "returned_rows": len(records),
                "records": records,
                "summary_statistics": summary,
            },
            "metadata": metadata,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NHANES tool."""
        if self.endpoint == "dataset_info":
            return self._get_dataset_info(arguments)
        elif self.endpoint == "search":
            return self._search_datasets(arguments)
        elif self.endpoint == "download_and_parse":
            return self._download_and_parse(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}
