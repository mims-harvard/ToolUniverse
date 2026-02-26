"""
SIDER Tool - Drug Side Effects Resource

Provides access to the SIDER (Side Effect Resource) database for retrieving drug
side effects, side effect frequencies from drug labels, therapeutic indications,
and reverse lookups from side effects to associated drugs.

SIDER 4.1 is maintained by EMBL (European Molecular Biology Laboratory) and
contains information on marketed medicines and their recorded adverse drug
reactions. Data is extracted from public documents and package inserts.

Source: http://sideeffects.embl.de
No authentication required.

Reference: Kuhn et al., Nucleic Acids Res. 2016; 44(D1): D1075-D1079
"""

import re
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool


SIDER_BASE_URL = "http://sideeffects.embl.de"


@register_tool("SiderTool")
class SiderTool(BaseTool):
    """
    Tool for querying the SIDER drug side effects database.

    SIDER contains information on marketed medicines and their recorded
    adverse drug reactions extracted from drug labels. It includes side
    effect frequencies, therapeutic indications, and MedDRA concept codes.

    Supported operations:
    - search_drug: Search for a drug by name and get its SIDER ID
    - get_side_effects: Get side effects for a drug (with frequencies if available)
    - get_indications: Get therapeutic indications for a drug
    - get_drugs_for_side_effect: Find drugs associated with a specific side effect
    - search_side_effect: Search for a side effect by name
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; ToolUniverse/1.0)"}
        )
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SIDER tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "search_drug": self._search_drug,
            "get_side_effects": self._get_side_effects,
            "get_indications": self._get_indications,
            "get_drugs_for_side_effect": self._get_drugs_for_side_effect,
            "search_side_effect": self._search_side_effect,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}".format(operation),
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "SIDER request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to SIDER"}
        except Exception as e:
            return {
                "status": "error",
                "error": "SIDER operation failed: {}".format(str(e)),
            }

    def _fetch_page(self, path: str) -> Optional[str]:
        """Fetch an HTML page from SIDER."""
        url = "{}/{}".format(SIDER_BASE_URL, path.lstrip("/"))
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code == 200:
            return response.text
        return None

    def _search_drug(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for a drug by name using SIDER's search endpoint."""
        query = arguments.get("drug_name")
        if not query:
            return {"status": "error", "error": "drug_name parameter is required"}

        html = self._fetch_page("/searchBox/?q={}".format(requests.utils.quote(query)))
        if not html:
            return {"status": "error", "error": "SIDER search endpoint unavailable"}

        # Extract drug results
        drug_matches = re.findall(r'href="/drugs/(\d+)/"[^>]*>([^<]+)</a>', html)
        # Extract side effect results
        se_matches = re.findall(r'href="/se/(C\d+)/"[^>]*>([^<]+)</a>', html)

        drugs = []
        for drug_id, name in drug_matches:
            drugs.append(
                {
                    "sider_drug_id": drug_id,
                    "drug_name": name.strip(),
                    "url": "{}/drugs/{}/".format(SIDER_BASE_URL, drug_id),
                }
            )

        related_side_effects = []
        for se_code, name in se_matches:
            related_side_effects.append(
                {
                    "meddra_code": se_code,
                    "side_effect_name": name.strip(),
                }
            )

        if not drugs and not related_side_effects:
            return {
                "status": "success",
                "data": {
                    "query": query,
                    "drugs": [],
                    "related_side_effects": [],
                    "message": "No results found for '{}'".format(query),
                },
            }

        return {
            "status": "success",
            "data": {
                "query": query,
                "drugs": drugs,
                "related_side_effects": related_side_effects,
            },
        }

    def _get_side_effects(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get side effects for a drug by SIDER drug ID or drug name."""
        drug_id = arguments.get("sider_drug_id")
        drug_name = arguments.get("drug_name")
        limit = arguments.get("limit", 50)

        if not drug_id and not drug_name:
            return {
                "status": "error",
                "error": "Either sider_drug_id or drug_name is required",
            }

        # If drug_name given, search first
        if not drug_id and drug_name:
            search_result = self._search_drug({"drug_name": drug_name})
            if search_result["status"] == "error":
                return search_result
            drugs = search_result["data"].get("drugs", [])
            if not drugs:
                return {
                    "status": "error",
                    "error": "Drug '{}' not found in SIDER".format(drug_name),
                }
            drug_id = drugs[0]["sider_drug_id"]

        html = self._fetch_page("/drugs/{}/".format(drug_id))
        if not html:
            return {
                "status": "error",
                "error": "Drug page not found for ID {}".format(drug_id),
            }

        # Extract drug name from <h1>
        name_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        resolved_name = name_match.group(1).strip() if name_match else "Unknown"

        # Find the boundary between side effects and indications sections
        ind_idx = html.lower().find("<h3 class='top'>indications")
        se_section = html[:ind_idx] if ind_idx > 0 else html

        # Extract side effect rows
        se_rows = re.findall(r'<tr\s+class="bg\d">(.*?)</tr>', se_section, re.DOTALL)

        side_effects = []
        for row in se_rows:
            # Extract MedDRA code and name
            se_match = re.search(
                r'href="/se/(C\d+)/"[^>]*title="([^"]*)"[^>]*>([^<]+)', row
            )
            if not se_match:
                se_match_simple = re.search(r'href="/se/(C\d+)/"[^>]*>([^<]+)', row)
                if not se_match_simple:
                    continue
                code = se_match_simple.group(1)
                name = se_match_simple.group(2).strip()
                description = None
            else:
                code = se_match.group(1)
                description = se_match.group(2)
                name = se_match.group(3).strip()

            # Extract frequency percentages
            pct_matches = re.findall(r"([\d.]+%\s*-\s*[\d.]+%|[\d.]+%)", row)
            frequency = pct_matches[0] if pct_matches else None
            placebo_frequency = pct_matches[1] if len(pct_matches) > 1 else None

            entry = {
                "meddra_code": code,
                "side_effect_name": name,
                "frequency": frequency,
                "placebo_frequency": placebo_frequency,
            }
            if description:
                entry["description"] = description

            side_effects.append(entry)

            if len(side_effects) >= limit:
                break

        return {
            "status": "success",
            "data": {
                "drug_name": resolved_name,
                "sider_drug_id": str(drug_id),
                "total_side_effects": len(se_rows),
                "side_effects": side_effects,
            },
        }

    def _get_indications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get therapeutic indications for a drug."""
        drug_id = arguments.get("sider_drug_id")
        drug_name = arguments.get("drug_name")

        if not drug_id and not drug_name:
            return {
                "status": "error",
                "error": "Either sider_drug_id or drug_name is required",
            }

        # If drug_name given, search first
        if not drug_id and drug_name:
            search_result = self._search_drug({"drug_name": drug_name})
            if search_result["status"] == "error":
                return search_result
            drugs = search_result["data"].get("drugs", [])
            if not drugs:
                return {
                    "status": "error",
                    "error": "Drug '{}' not found in SIDER".format(drug_name),
                }
            drug_id = drugs[0]["sider_drug_id"]

        html = self._fetch_page("/drugs/{}/".format(drug_id))
        if not html:
            return {
                "status": "error",
                "error": "Drug page not found for ID {}".format(drug_id),
            }

        # Extract drug name from <h1>
        name_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        resolved_name = name_match.group(1).strip() if name_match else "Unknown"

        # Find indications section
        ind_idx = html.lower().find("<h3 class='top'>indications")
        if ind_idx < 0:
            return {
                "status": "success",
                "data": {
                    "drug_name": resolved_name,
                    "sider_drug_id": str(drug_id),
                    "indications": [],
                    "message": "No indications section found",
                },
            }

        ind_section = html[ind_idx:]

        # Extract indication entries (linked to /se/CXXXXXX/ with title descriptions)
        ind_matches = re.findall(
            r'<a href="/se/(C\d+)/"[^>]*title="([^"]*)"[^>]*>([^<]+)',
            ind_section,
        )

        # Deduplicate by MedDRA code
        seen = set()
        indications = []
        for code, description, name in ind_matches:
            if code not in seen:
                seen.add(code)
                indications.append(
                    {
                        "meddra_code": code,
                        "indication_name": name.strip(),
                        "description": description if description else None,
                    }
                )

        return {
            "status": "success",
            "data": {
                "drug_name": resolved_name,
                "sider_drug_id": str(drug_id),
                "total_indications": len(indications),
                "indications": indications,
            },
        }

    def _search_side_effect(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for a side effect by name."""
        query = arguments.get("side_effect_name")
        if not query:
            return {
                "status": "error",
                "error": "side_effect_name parameter is required",
            }

        html = self._fetch_page("/searchBox/?q={}".format(requests.utils.quote(query)))
        if not html:
            return {"status": "error", "error": "SIDER search endpoint unavailable"}

        # Extract side effect results
        se_matches = re.findall(
            r'href="/se/(C\d+)/"[^>]*>([^<]+)</a>\s*\((\d+)\s+drugs?\)',
            html,
        )
        if not se_matches:
            # Try without drug count
            se_matches_simple = re.findall(r'href="/se/(C\d+)/"[^>]*>([^<]+)</a>', html)
            side_effects = []
            for code, name in se_matches_simple:
                side_effects.append(
                    {
                        "meddra_code": code,
                        "side_effect_name": name.strip(),
                    }
                )
        else:
            side_effects = []
            for code, name, drug_count in se_matches:
                side_effects.append(
                    {
                        "meddra_code": code,
                        "side_effect_name": name.strip(),
                        "drug_count": int(drug_count),
                    }
                )

        if not side_effects:
            return {
                "status": "success",
                "data": {
                    "query": query,
                    "side_effects": [],
                    "message": "No side effects found matching '{}'".format(query),
                },
            }

        return {
            "status": "success",
            "data": {
                "query": query,
                "side_effects": side_effects,
            },
        }

    def _get_drugs_for_side_effect(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find drugs associated with a specific side effect by MedDRA code."""
        meddra_code = arguments.get("meddra_code")
        side_effect_name = arguments.get("side_effect_name")
        limit = arguments.get("limit", 50)

        if not meddra_code and not side_effect_name:
            return {
                "status": "error",
                "error": "Either meddra_code or side_effect_name is required",
            }

        # If side_effect_name given, search first
        if not meddra_code and side_effect_name:
            search_result = self._search_side_effect(
                {"side_effect_name": side_effect_name}
            )
            if search_result["status"] == "error":
                return search_result
            se_list = search_result["data"].get("side_effects", [])
            if not se_list:
                return {
                    "status": "error",
                    "error": "Side effect '{}' not found".format(side_effect_name),
                }
            meddra_code = se_list[0]["meddra_code"]

        html = self._fetch_page("/se/{}/".format(meddra_code))
        if not html:
            return {
                "status": "error",
                "error": "Side effect page not found for {}".format(meddra_code),
            }

        # Extract SE name from <h1>
        name_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        se_name = name_match.group(1).strip() if name_match else "Unknown"

        # Extract drug list entries with frequency info
        # Pattern: <li><a href="/drugs/NNN/">drugname</a>: freq info </li>
        drug_entries = re.findall(
            r'<li><a href="/drugs/(\d+)/">([^<]+)</a>\s*(?::\s*([^<]*?))?</li>',
            html,
            re.DOTALL,
        )

        drugs = []
        for drug_id, drug_name, freq_info in drug_entries:
            freq_info = freq_info.strip() if freq_info else None
            entry = {
                "sider_drug_id": drug_id,
                "drug_name": drug_name.strip(),
                "frequency_info": freq_info if freq_info else None,
            }
            drugs.append(entry)

            if len(drugs) >= limit:
                break

        return {
            "status": "success",
            "data": {
                "meddra_code": meddra_code,
                "side_effect_name": se_name,
                "total_drugs": len(drug_entries),
                "drugs": drugs,
            },
        }
