# scicrunch_rrid_tool.py
"""
SciCrunch RRID resolver tool for ToolUniverse.

RRIDs (Research Resource Identifiers) are the citation standard journals
increasingly require for antibodies, cell lines, model organisms,
plasmids, and software/tools, so a paper's methods section can be resolved
to exactly which resource was used. ToolUniverse already has a dedicated,
richer Antibody Registry tool for the AB_ prefix (the majority of RRIDs);
this tool resolves any RRID prefix through SciCrunch's own registry,
covering the categories that tool does not: SCR_ (software/tools),
cell lines, organisms, and plasmids, plus serving as a general fallback.

API: https://scicrunch.org/resolver
No authentication required.
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

RESOLVER_URL = "https://scicrunch.org/resolver"


def _names(entries: Any) -> List[str]:
    """Flatten SciCrunch's list-of-{name:...} fields to plain strings."""
    if not isinstance(entries, list):
        return []
    return [e.get("name") for e in entries if isinstance(e, dict) and e.get("name")]


@register_tool("SciCrunchRRIDTool")
class SciCrunchRRIDTool(BaseTool):
    """
    Tool for resolving Research Resource Identifiers (RRIDs) via SciCrunch.

    Supports any RRID prefix (antibodies, software/tools, cell lines,
    organisms, plasmids), returning the resource's name, description,
    category, and citation.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "resolve_rrid"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the RRID resolution."""
        try:
            if self.operation == "resolve_rrid":
                return self._resolve_rrid(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SciCrunch request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to SciCrunch. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"SciCrunch returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "SciCrunch returned a non-JSON response",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying SciCrunch: {str(e)}",
            }

    def _resolve_rrid(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve one RRID to its resource record."""
        rrid = (arguments.get("rrid") or "").strip()
        if not rrid:
            return {
                "status": "error",
                "error": "rrid is required, e.g. 'RRID:SCR_002526' or "
                "'SCR_002526'. Prefix is optional.",
            }

        identifier = rrid if rrid.upper().startswith("RRID:") else f"RRID:{rrid}"
        response = requests.get(
            f"{RESOLVER_URL}/{identifier}.json", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No SciCrunch record for '{rrid}'.",
            }
        response.raise_for_status()
        payload = response.json()
        hits = (payload.get("hits") or {}).get("hits") or []
        if not hits:
            return {
                "status": "error",
                "error": f"No SciCrunch record for '{rrid}'.",
            }

        source = hits[0].get("_source") or {}
        item = source.get("item") or {}
        rrid_info = source.get("rrid") or {}
        current_urls = [
            d.get("uri")
            for d in (source.get("distributions") or {}).get("current") or []
            if d.get("uri")
        ]

        return {
            "status": "success",
            "data": {
                "rrid": rrid_info.get("curie") or identifier,
                "name": item.get("name"),
                "description": item.get("description"),
                "categories": _names(item.get("types")),
                "keywords": [
                    k.get("keyword")
                    for k in item.get("keywords") or []
                    if isinstance(k, dict) and k.get("keyword")
                ],
                "synonyms": _names(item.get("synonyms")),
                "proper_citation": rrid_info.get("properCitation"),
                "landing_page_urls": current_urls,
            },
            "metadata": {
                "rrid": rrid,
                "note": "For antibody RRIDs (AB_ prefix), "
                "AntibodyRegistry_resolve_rrid returns richer "
                "antibody-specific fields (target, clonality, host).",
                "source": "SciCrunch Registry",
            },
        }
