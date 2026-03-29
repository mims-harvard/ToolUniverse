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

    def _get_dataset_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get NHANES dataset information."""
        year = arguments.get("year")
        component = arguments.get("component")

        base_url = "https://wwwn.cdc.gov/Nchs/Nhanes"

        # Common NHANES cycles
        cycles = [
            "2017-2018",
            "2015-2016",
            "2013-2014",
            "2011-2012",
            "2009-2010",
            "2007-2008",
        ]

        datasets = []

        if year:
            cycles_to_show = [year] if year in cycles else cycles[:2]
        else:
            cycles_to_show = cycles[:2]  # Show most recent

        for cycle in cycles_to_show:
            if component:
                datasets.append(
                    {
                        "name": f"NHANES {component} - {cycle}",
                        "year": cycle,
                        "component": component,
                        "download_url": f"{base_url}/{cycle}/{component.lower()}_{cycle}.aspx",
                        "description": f"NHANES {component} data for {cycle}",
                    }
                )
            else:
                # Show all components
                for comp in [
                    "Demographics",
                    "Dietary",
                    "Examination",
                    "Laboratory",
                    "Questionnaire",
                ]:
                    datasets.append(
                        {
                            "name": f"NHANES {comp} - {cycle}",
                            "year": cycle,
                            "component": comp,
                            "download_url": f"{base_url}/{cycle}/{comp.lower()}_{cycle}.aspx",
                            "description": f"NHANES {comp} data for {cycle}",
                        }
                    )

        return {
            "status": "success",
            "data": {
                "datasets": datasets[:20],  # Limit results
                "note": "NHANES data is available as downloadable files (SAS, XPT formats) from the CDC website. Visit the download URLs to access datasets. Files may require SAS or conversion tools to read.",
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

        cycle_year = year.split("-")[0] if year else "2017"
        components = [
            "Demographics",
            "Dietary",
            "Examination",
            "Laboratory",
            "Questionnaire",
        ]

        datasets = []
        seen_files: set = set()
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
                        search_term in s.lower()
                        for s in [var_desc, var_name, file_desc]
                    ):
                        continue
                    if file_name not in seen_files:
                        seen_files.add(file_name)
                        end_year = str(int(cycle_year) + 1)
                        datasets.append(
                            {
                                "file_name": file_name,
                                "file_description": file_desc,
                                "component": component,
                                "matching_variable": var_name,
                                "variable_description": var_desc,
                                "cycle": year or f"{cycle_year}-{end_year}",
                                "download_url": (
                                    f"https://wwwn.cdc.gov/Nchs/Nhanes/"
                                    f"{cycle_year}-{end_year}/"
                                    f"DataFiles/{file_name}.XPT"
                                ),
                            }
                        )
                    if len(datasets) >= limit:
                        break
            except Exception:
                continue
            if len(datasets) >= limit:
                break

        return {
            "status": "success",
            "data": {
                "datasets": datasets,
                "count": len(datasets),
                "search_term": search_term,
                "cycle": year or f"{cycle_year}-{str(int(cycle_year) + 1)}",
            },
            "metadata": {
                "source": "NHANES Variable List (wwwn.cdc.gov)",
                "components_searched": components,
            },
        }

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
        return pd.read_sas(io.BytesIO(content), format="xport")

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
