# dfam_tool.py
"""
Dfam tool for ToolUniverse.

Dfam is a comprehensive database of transposable element (TE) and repetitive
DNA families with consensus sequences, profile HMMs, and genome annotations.
Maintained by the Institute for Systems Biology and partners.

API: https://www.dfam.org/api/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

DFAM_BASE_URL = "https://www.dfam.org/api"


@register_tool("DfamTool")
class DfamTool(BaseTool):
    """
    Tool for querying Dfam transposable element / repeat element database.

    Supports:
    - Search TE families by name prefix, clade (taxon ID), and repeat type
    - Get detailed family info including consensus sequence and classification
    - Get TE annotation hits for genomic regions

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search_families")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Dfam API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Dfam API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Dfam API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "error": "Resource not found in Dfam. Check the accession or query."
                }
            return {"error": f"Dfam API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "search_families":
            return self._search_families(arguments)
        elif self.endpoint == "get_family":
            return self._get_family(arguments)
        elif self.endpoint == "get_annotations":
            return self._get_annotations(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _search_families(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search Dfam TE families by name prefix, clade, or repeat type."""
        params = {"format": "summary"}

        name_prefix = arguments.get("name_prefix")
        if name_prefix:
            params["name_prefix"] = name_prefix

        clade = arguments.get("clade")
        if clade:
            params["clade"] = clade

        repeat_type = arguments.get("repeat_type")
        if repeat_type:
            params["type"] = repeat_type

        limit = arguments.get("limit", 20)
        params["limit"] = min(limit, 50)

        url = f"{DFAM_BASE_URL}/families"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        families = []
        for fam in results:
            families.append(
                {
                    "accession": fam.get("accession"),
                    "name": fam.get("name"),
                    "title": fam.get("title"),
                    "description": fam.get("description"),
                    "length": fam.get("length"),
                    "repeat_type": fam.get("repeat_type_name"),
                    "repeat_subtype": fam.get("repeat_subtype_name"),
                    "classification": fam.get("classification"),
                }
            )

        return {
            "data": families,
            "metadata": {
                "source": "Dfam (dfam.org)",
                "total_count": data.get("total_count", len(families)),
                "returned": len(families),
            },
        }

    def _get_family(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed info for a specific Dfam TE family."""
        accession = arguments.get("accession", "")
        if not accession:
            return {"error": "accession is required (e.g., 'DF000000003' for AluSc)."}

        url = f"{DFAM_BASE_URL}/families/{accession}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        citations = []
        for c in data.get("citations", []):
            citations.append(
                {
                    "pmid": c.get("pmid"),
                    "title": c.get("title"),
                    "authors": c.get("authors"),
                }
            )

        return {
            "data": {
                "accession": data.get("accession"),
                "name": data.get("name"),
                "title": data.get("title"),
                "description": data.get("description"),
                "length": data.get("length"),
                "classification": data.get("classification"),
                "repeat_type": data.get("repeat_type_name"),
                "repeat_subtype": data.get("repeat_subtype_name"),
                "consensus_sequence": data.get("consensus_sequence"),
                "author": data.get("author"),
                "date_created": data.get("date_created"),
                "date_modified": data.get("date_modified"),
                "curation_state": data.get("curation_state_name"),
                "clades": data.get("clades", []),
                "citations": citations,
                "aliases": data.get("aliases", []),
            },
            "metadata": {
                "source": "Dfam (dfam.org)",
            },
        }

    def _get_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get TE annotation hits for a genomic region."""
        assembly = arguments.get("assembly", "hg38")
        chrom = arguments.get("chrom", "")
        start = arguments.get("start")
        end = arguments.get("end")

        if not chrom or start is None or end is None:
            return {
                "error": "chrom, start, and end are required (e.g., chrom='chr1', start=10000, end=50000)."
            }

        # Dfam API expects lowercase boolean strings
        nrph = arguments.get("nrph", True)
        params = {
            "assembly": assembly,
            "chrom": chrom,
            "start": int(start),
            "end": int(end),
            "nrph": "true" if nrph else "false",
        }

        url = f"{DFAM_BASE_URL}/annotations"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        hits = data.get("hits", [])
        annotations = []
        for hit in hits[:50]:  # Limit to 50 hits to avoid huge responses
            annotations.append(
                {
                    "accession": hit.get("accession"),
                    "query": hit.get("query"),
                    "type": hit.get("type"),
                    "strand": hit.get("strand"),
                    "bit_score": hit.get("bit_score"),
                    "e_value": hit.get("e_value"),
                    "seq_start": hit.get("seq_start"),
                    "seq_end": hit.get("seq_end"),
                    "ali_start": hit.get("ali_start"),
                    "ali_end": hit.get("ali_end"),
                    "model_start": hit.get("model_start"),
                    "model_end": hit.get("model_end"),
                }
            )

        return {
            "data": annotations,
            "metadata": {
                "source": "Dfam (dfam.org)",
                "assembly": assembly,
                "region": f"{chrom}:{start}-{end}",
                "total_hits": len(hits),
                "returned": len(annotations),
            },
        }
