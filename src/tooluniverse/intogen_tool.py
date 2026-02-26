"""
IntOGen cancer driver gene database tool for ToolUniverse.

IntOGen identifies cancer driver genes across tumor types using seven
complementary computational methods (dNdScv, OncodriveFML, OncodriveCLUSTL,
HotMAPS, smRegions, CBaSE, MutPanning) applied to thousands of tumor genomes.
It provides a consensus classification of driver genes per cancer type.

Data access: IntOGen embeds structured JSON data in its HTML pages.
This tool parses that embedded data from:
- /search (main page: all driver genes + all cohorts)
- /search?gene=X (gene detail: driver methods per cancer type)
- /search?cancer=X (cancer type detail: driver genes + cohorts)
- /find?t=gene|cancer|cohort&q=X&l=N (autocomplete search)

No authentication required. Public access.
Website: https://www.intogen.org
"""

import json
import re
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .base_tool import BaseTool
from .tool_registry import register_tool

INTOGEN_BASE_URL = "https://www.intogen.org"


def _intogen_get(url, timeout=30):
    """HTTP GET for IntOGen endpoints."""
    req = Request(url)
    req.add_header("User-Agent", "ToolUniverse/1.0 (IntOGen API client)")
    req.add_header("Accept", "text/html,application/json")
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _intogen_get_json(url, timeout=30):
    """HTTP GET returning parsed JSON (for /find endpoints)."""
    text = _intogen_get(url, timeout=timeout)
    return json.loads(text)


def _extract_constructor_data(html, constructor_name):
    """Extract JSON array from a JavaScript constructor call in HTML.

    IntOGen embeds data as: new ConstructorName([{...}, {...}, ...], ...)
    This function finds and parses the first JSON array argument.
    """
    marker = "new %s(" % constructor_name
    idx = html.find(marker)
    if idx < 0:
        return None

    # Find the opening bracket
    bracket_start = html.find("[", idx)
    if bracket_start < 0:
        return None

    # Match the bracket
    depth = 0
    for i in range(bracket_start, min(bracket_start + 500000, len(html))):
        if html[i] == "[":
            depth += 1
        elif html[i] == "]":
            depth -= 1
        if depth == 0:
            try:
                return json.loads(html[bracket_start : i + 1])
            except (json.JSONDecodeError, ValueError):
                return None
    return None


@register_tool("IntOGenTool")
class IntOGenTool(BaseTool):
    """
    Tool for querying IntOGen, the cancer driver gene database.

    IntOGen systematically identifies cancer driver genes using seven
    computational methods applied to somatic mutation data from 28,000+
    tumors across 87 cancer types from 271 cohorts. It classifies genes
    as cancer drivers when they are identified by at least one method.

    Endpoints:
    - get_drivers: get driver genes for a specific cancer type
    - get_gene_info: get driver info for a gene across cancer types
    - list_cohorts: list available cancer cohorts
    - list_cancer_types: list all cancer types

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_drivers")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the IntOGen query."""
        try:
            return self._query(arguments)
        except HTTPError as e:
            return {
                "status": "error",
                "error": "IntOGen HTTP error: %s" % e.code,
            }
        except URLError as e:
            return {
                "status": "error",
                "error": "Failed to connect to IntOGen: %s" % str(e.reason),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "Unexpected error querying IntOGen: %s" % str(e),
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint handler."""
        if self.endpoint == "get_drivers":
            return self._get_drivers(arguments)
        elif self.endpoint == "get_gene_info":
            return self._get_gene_info(arguments)
        elif self.endpoint == "list_cohorts":
            return self._list_cohorts(arguments)
        elif self.endpoint == "list_cancer_types":
            return self._list_cancer_types(arguments)
        else:
            return {"status": "error", "error": "Unknown endpoint: %s" % self.endpoint}

    def _get_drivers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get driver genes for a specific cancer type.

        Fetches the cancer type page and extracts the DriverGenes data.
        """
        cancer_type = arguments.get("cancer_type")
        if not cancer_type:
            return {"status": "error", "error": "cancer_type parameter is required"}

        url = "%s/search?cancer=%s" % (INTOGEN_BASE_URL, quote(cancer_type))
        html = _intogen_get(url, timeout=self.timeout)

        # Check if the page actually has data (valid cancer type)
        driver_data = _extract_constructor_data(html, "DriverGenes")
        if driver_data is None:
            return {
                "status": "error",
                "error": "No driver gene data found for cancer type '%s'. Use IntOGen_list_cancer_types to see available cancer types."
                % cancer_type,
            }

        # Also extract cohort data for metadata
        cohort_data = _extract_constructor_data(html, "Cohorts")

        # Build results
        drivers = []
        for entry in driver_data:
            drivers.append(
                {
                    "gene": entry.get("SYMBOL"),
                    "mutations": entry.get("MUTATIONS"),
                    "samples": entry.get("SAMPLES"),
                    "cohorts": entry.get("COHORTS"),
                }
            )

        return {
            "status": "success",
            "data": {
                "cancer_type": cancer_type,
                "driver_genes": drivers,
                "total_drivers": len(drivers),
                "total_cohorts": len(cohort_data) if cohort_data else 0,
            },
        }

    def _get_gene_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get driver classification for a gene across all cancer types.

        Fetches the gene page and extracts GeneMethods data showing
        which methods detected the gene as a driver in each cancer type.
        """
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "gene parameter is required"}

        url = "%s/search?gene=%s" % (INTOGEN_BASE_URL, quote(gene))
        html = _intogen_get(url, timeout=self.timeout)

        # Extract GeneMethods data
        methods_data = _extract_constructor_data(html, "GeneMethods")
        if methods_data is None:
            return {
                "status": "error",
                "error": "No data found for gene '%s'. It may not be a recognized cancer driver gene."
                % gene,
            }

        # Build results
        cancer_types = []
        for entry in methods_data:
            cancer_types.append(
                {
                    "cancer_type": entry.get("CANCER"),
                    "cancer_name": entry.get("CANCER_NAME"),
                    "methods": entry.get("METHODS", []),
                    "mutated_samples": entry.get("SAMPLES"),
                    "total_samples": entry.get("TOTAL_SAMPLES"),
                }
            )

        return {
            "status": "success",
            "data": {
                "gene": gene,
                "cancer_types": cancer_types,
                "num_cancer_types": len(cancer_types),
            },
        }

    def _list_cohorts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available cancer cohorts with sample counts.

        Fetches the main search page and extracts Release (cohort) data.
        """
        cancer_type = arguments.get("cancer_type")

        if cancer_type:
            # Get cohorts for a specific cancer type
            url = "%s/search?cancer=%s" % (INTOGEN_BASE_URL, quote(cancer_type))
            html = _intogen_get(url, timeout=self.timeout)
            cohort_data = _extract_constructor_data(html, "Cohorts")
            if cohort_data is None:
                return {
                    "status": "error",
                    "error": "No cohort data found for cancer type '%s'." % cancer_type,
                }
            cohorts = []
            for entry in cohort_data:
                cohorts.append(
                    {
                        "cohort_id": entry.get("ID"),
                        "name": entry.get("NAME"),
                        "nickname": entry.get("NICK"),
                        "samples": entry.get("SAMPLES"),
                        "source": entry.get("SOURCE"),
                        "tumor_type": entry.get("TYPE"),
                        "age_group": entry.get("AGE"),
                    }
                )
        else:
            # Get all cohorts from the main page (Release data)
            url = "%s/search" % INTOGEN_BASE_URL
            html = _intogen_get(url, timeout=self.timeout)
            release_data = _extract_constructor_data(html, "Release")
            if release_data is None:
                return {
                    "status": "error",
                    "error": "Failed to extract cohort data from IntOGen.",
                }
            cohorts = []
            for entry in release_data:
                cohorts.append(
                    {
                        "cohort_id": entry.get("ID"),
                        "name": entry.get("NAME"),
                        "nickname": entry.get("NICK"),
                        "cancer_type": entry.get("CANCER"),
                        "cancer_name": entry.get("CANCER_NAME"),
                        "samples": entry.get("SAMPLES"),
                        "drivers": entry.get("DRIVERS"),
                        "mutations": entry.get("MUTATIONS"),
                        "tumor_type": entry.get("TYPE"),
                        "age_group": entry.get("AGE"),
                    }
                )

        return {
            "status": "success",
            "data": {
                "cohorts": cohorts,
                "total_cohorts": len(cohorts),
            },
        }

    def _list_cancer_types(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available cancer types.

        Uses the /find endpoint which provides a clean JSON list of cancer types.
        """
        url = "%s/find?t=cancer&q=&l=1000" % INTOGEN_BASE_URL
        data = _intogen_get_json(url, timeout=self.timeout)

        cancer_types = []
        for entry in data:
            cancer_types.append(
                {
                    "cancer_type_id": entry.get("ID"),
                    "cancer_name": entry.get("NAME"),
                }
            )

        return {
            "status": "success",
            "data": {
                "cancer_types": cancer_types,
                "total_cancer_types": len(cancer_types),
            },
        }
