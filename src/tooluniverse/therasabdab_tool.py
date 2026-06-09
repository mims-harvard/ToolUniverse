# therasabdab_tool.py
"""
Thera-SAbDab (Therapeutic Structural Antibody Database) API tool for ToolUniverse.

Thera-SAbDab is a database of therapeutic antibody sequences and structural information,
containing WHO INN (International Nonproprietary Names) antibody therapeutics.

Features:
- Therapeutic antibody sequences (heavy and light chains)
- Structural coverage from PDB
- Target antigen information
- Clinical trial status
- Format types (IgG, bispecific, ADC, etc.)

Website: https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/therasabdab/
"""

import requests
from typing import Dict, Any, List, Optional
import re
from urllib.parse import urlparse, parse_qs
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for Thera-SAbDab
THERASABDAB_BASE_URL = "https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/therasabdab"


@register_tool("TheraSAbDabTool")
class TheraSAbDabTool(BaseTool):
    """
    Tool for querying Thera-SAbDab therapeutic antibody database.

    Provides access to:
    - WHO INN therapeutic antibody names
    - Heavy/light chain sequences
    - Target antigens
    - Clinical trial status
    - PDB structural coverage

    No authentication required.
    """

    # Cache for all therapeutics (loaded once)
    _therapeutics_cache = None
    # Cache for the full per-therapeutic records parsed from the summary hrefs
    _sequences_cache = None

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_therapeutics"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Thera-SAbDab API call."""
        operation = self.operation

        if operation == "search_therapeutics":
            return self._search_therapeutics(arguments)
        elif operation == "get_all_therapeutics":
            return self._get_all_therapeutics(arguments)
        elif operation == "search_by_target":
            return self._search_by_target(arguments)
        elif operation == "get_therapeutic_sequences":
            return self._get_therapeutic_sequences(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    @staticmethod
    def _clean_value(value: Optional[str]) -> Optional[str]:
        """Normalize a parsed query-string value: blank / 'na' / 'None' -> None."""
        if value is None:
            return None
        cleaned = value.strip()
        if cleaned == "" or cleaned.lower() in ("na", "none"):
            return None
        return cleaned

    def _load_all_sequences(self) -> List[Dict[str, Any]]:
        """Load every therapeutic record (incl. VH/VL sequences) from Thera-SAbDab.

        The ``?all=true`` results page embeds the full curated record for each
        therapeutic inside the ``href`` of its detail link as URL query
        parameters (INN, format, isotype, heavy1/light1, heavy2/light2,
        struc100/99/95to98, target, companies, conditions, ...). We parse those
        hrefs rather than the visible table, which only shows a few columns.
        """
        if TheraSAbDabTool._sequences_cache is not None:
            return TheraSAbDabTool._sequences_cache

        url = f"{THERASABDAB_BASE_URL}/search/"
        response = requests.get(url, params={"all": "true"}, timeout=self.timeout)
        response.raise_for_status()

        href_pattern = re.compile(
            r'href="(/webapps/sabdab-sabpred/therasabdab/therasummary/\?[^"]+)"'
        )
        records = []
        seen = set()
        for href in href_pattern.findall(response.text):
            # The HTML escapes '&' as '&amp;'; restore before parsing.
            query = urlparse(href.replace("&amp;", "&")).query
            params = parse_qs(query, keep_blank_values=True)

            def get(key):
                vals = params.get(key)
                return self._clean_value(vals[0]) if vals else None

            inn = get("INN")
            if not inn or inn.lower() in seen:
                continue
            seen.add(inn.lower())

            records.append(
                {
                    "inn_name": inn,
                    "format": get("format"),
                    "clinical_trial": get("clintrial"),
                    "status": get("status"),
                    "target": get("target"),
                    "isotype": get("isotype"),
                    "year_proposed": get("yearprop"),
                    "year_recommended": get("yearrec"),
                    "heavy1": get("heavy1"),
                    "light1": get("light1"),
                    "heavy2": get("heavy2"),
                    "light2": get("light2"),
                    "struc100": get("struc100"),
                    "struc99": get("struc99"),
                    "struc95to98": get("struc95to98"),
                    "companies": get("companies"),
                    "conditions_approved": get("cond_approved"),
                    "conditions_active": get("cond_active"),
                    "conditions_discontinued": get("cond_disc"),
                    "development_technology": get("dev_tech"),
                    "notes": get("notes"),
                }
            )

        TheraSAbDabTool._sequences_cache = records
        return records

    def _get_therapeutic_sequences(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return full VH/VL sequences and metadata for a named therapeutic.

        Matches by WHO INN name (case-insensitive, exact match preferred,
        otherwise substring). Returns heavy1/light1 (and heavy2/light2 for
        bispecifics), isotype, PDB structural coverage, companies and
        approved/active/discontinued conditions.
        """
        name = arguments.get("name") or arguments.get("inn") or arguments.get("query")
        if not name:
            return {
                "status": "error",
                "error": "name parameter is required (WHO INN, e.g. 'adalimumab')",
            }

        try:
            records = self._load_all_sequences()
            name_lower = name.strip().lower()

            exact = [r for r in records if (r["inn_name"] or "").lower() == name_lower]
            matches = exact or [
                r for r in records if name_lower in (r["inn_name"] or "").lower()
            ]

            if not matches:
                return {
                    "status": "error",
                    "error": (
                        f"No therapeutic named '{name}' found in Thera-SAbDab. "
                        "Use the WHO INN (e.g. 'adalimumab', 'abciximab')."
                    ),
                }

            return {
                "status": "success",
                "data": {
                    "query": name,
                    "matched": matches[0]["inn_name"],
                    "therapeutic": matches[0],
                    "additional_matches": [m["inn_name"] for m in matches[1:10]],
                    "match_count": len(matches),
                },
                "metadata": {
                    "source": "Thera-SAbDab (Oxford OPIG)",
                    "total_records": len(records),
                    "note": (
                        "heavy2/light2 are populated for bispecifics; struc100/99/"
                        "95to98 list PDB structures at the given sequence-identity "
                        "tier as 'pdbid:chains'."
                    ),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Thera-SAbDab timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Thera-SAbDab request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Thera-SAbDab search results from HTML."""
        therapeutics = []

        # Simple regex-based parsing for table rows
        # Actual columns: Therapeutic, Format, Clinical Trial, Est. Status, Target, Year, ...
        table_pattern = r"<tr[^>]*>.*?</tr>"
        row_matches = re.findall(table_pattern, html, re.DOTALL)

        for row in row_matches:
            # Skip header rows
            if "<th" in row:
                continue

            # Extract cell data
            cell_pattern = r"<td[^>]*>(.*?)</td>"
            cells = re.findall(cell_pattern, row, re.DOTALL)

            if len(cells) >= 4:
                # Clean HTML from cells
                def clean_html(text):
                    # Remove HTML tags
                    clean = re.sub(r"<[^>]+>", "", text)
                    # Decode entities
                    clean = clean.replace("&nbsp;", " ").strip()
                    return clean

                therapeutic = {
                    "inn_name": clean_html(cells[0]) if len(cells) > 0 else None,
                    "format": clean_html(cells[1]) if len(cells) > 1 else None,
                    "clinical_trial": clean_html(cells[2]) if len(cells) > 2 else None,
                    "status": clean_html(cells[3]) if len(cells) > 3 else None,
                    "target": clean_html(cells[4]) if len(cells) > 4 else None,
                    "year_proposed": clean_html(cells[5]) if len(cells) > 5 else None,
                }

                # Only add if we have a name
                if therapeutic["inn_name"]:
                    therapeutics.append(therapeutic)

        return therapeutics

    def _load_all_therapeutics(self) -> List[Dict[str, Any]]:
        """Load all therapeutics from Thera-SAbDab (with caching)."""
        if TheraSAbDabTool._therapeutics_cache is not None:
            return TheraSAbDabTool._therapeutics_cache

        # Query the "all therapeutics" endpoint
        url = f"{THERASABDAB_BASE_URL}/search/"
        params = {"all": "true"}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        therapeutics = self._parse_search_results(response.text)
        TheraSAbDabTool._therapeutics_cache = therapeutics

        return therapeutics

    def _search_therapeutics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search therapeutic antibodies by name or keyword.

        Searches the Thera-SAbDab database for matching therapeutics.
        """
        query = arguments.get("query")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            # Load all therapeutics and filter locally
            all_therapeutics = self._load_all_therapeutics()

            # Filter by query (case-insensitive, hyphen-normalized search in name and target)
            # TheraSAbDab stores targets as "PDCD1/CD279/PD1" (no hyphens), so normalize
            query_lower = query.lower()
            query_nohyphen = query_lower.replace("-", "")
            filtered = [
                t
                for t in all_therapeutics
                if query_lower in (t.get("inn_name") or "").lower()
                or query_nohyphen in (t.get("target") or "").lower().replace("-", "")
                or query_lower in (t.get("target") or "").lower()
            ]

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "therapeutics": filtered[:20],  # Limit results
                    "count": len(filtered),
                    "source": "Thera-SAbDab (Oxford OPIG)",
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Thera-SAbDab timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Thera-SAbDab request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_all_therapeutics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of all therapeutic antibodies in Thera-SAbDab.

        Returns count and sample of therapeutics by format and phase.
        """
        try:
            therapeutics = self._load_all_therapeutics()

            # Summarize by format
            formats = {}
            phases = {}

            for t in therapeutics:
                fmt = t.get("format") or "Unknown"
                phase = t.get("phase") or "Unknown"

                formats[fmt] = formats.get(fmt, 0) + 1
                phases[phase] = phases.get(phase, 0) + 1

            return {
                "status": "success",
                "data": {
                    "total_count": len(therapeutics),
                    "by_format": formats,
                    "by_phase": phases,
                    "sample": therapeutics[:10],  # Sample of first 10
                    "source": "Thera-SAbDab (Oxford OPIG)",
                    "note": "Full data can be downloaded from the Thera-SAbDab website",
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Thera-SAbDab timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Thera-SAbDab request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_by_target(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search therapeutic antibodies by target antigen.

        Useful for finding all approved/clinical antibodies against a target.
        """
        target = arguments.get("target")

        if not target:
            return {"status": "error", "error": "target parameter is required"}

        try:
            # Load all therapeutics and filter by target
            all_therapeutics = self._load_all_therapeutics()

            # Filter by target (case-insensitive, hyphen-normalized)
            # TheraSAbDab stores targets as "PDCD1/CD279/PD1" (no hyphens)
            target_lower = target.lower()
            target_nohyphen = target_lower.replace("-", "")
            filtered = [
                t
                for t in all_therapeutics
                if target_lower in (t.get("target") or "").lower()
                or target_nohyphen in (t.get("target") or "").lower().replace("-", "")
            ]

            return {
                "status": "success",
                "data": {
                    "target": target,
                    "therapeutics": filtered[:20],
                    "count": len(filtered),
                    "source": "Thera-SAbDab (Oxford OPIG)",
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Thera-SAbDab timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Thera-SAbDab request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
