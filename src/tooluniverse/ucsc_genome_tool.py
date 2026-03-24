# ucsc_genome_tool.py
"""
UCSC Genome Browser REST API tool for ToolUniverse.

The UCSC Genome Browser provides access to genome assemblies, gene annotations,
regulatory elements, conservation scores, and hundreds of other tracks for
220+ organisms. The API enables genomic search, DNA sequence retrieval,
and annotation track data access.

API: https://api.genome.ucsc.edu
No authentication required. Rate limit: ~1 request/second recommended.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

UCSC_BASE_URL = "https://api.genome.ucsc.edu"


@register_tool("UCSCGenomeTool")
class UCSCGenomeTool(BaseTool):
    """
    Tool for querying the UCSC Genome Browser REST API.

    Provides genomic search, DNA sequence retrieval, and annotation
    track data for 220+ genome assemblies (hg38, mm39, etc.).

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UCSC Genome Browser API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"UCSC Genome Browser API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to UCSC Genome Browser API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"UCSC Genome Browser API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying UCSC Genome Browser: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "search":
            return self._search(arguments)
        elif self.endpoint_type == "get_sequence":
            return self._get_sequence(arguments)
        elif self.endpoint_type == "get_track":
            return self._get_track(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UCSC Genome Browser for genes, transcripts, or features."""
        search_term = arguments.get("search_term", "")
        genome = arguments.get("genome", "hg38")

        if not search_term:
            return {
                "status": "error",
                "error": "search_term parameter is required (e.g., 'TP53', 'BRCA1')",
            }

        url = f"{UCSC_BASE_URL}/search?search={search_term};genome={genome}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        # Extract position matches
        matches = []
        position_matches = raw.get("positionMatches", [])
        for track_match in position_matches:
            track_name = track_match.get("trackName", "")
            track_desc = track_match.get("description", "")
            for m in track_match.get("matches", [])[:20]:
                matches.append(
                    {
                        "track": track_name,
                        "track_description": track_desc,
                        "position": m.get("position", ""),
                        "name": m.get("posName", None),
                        "transcript_id": m.get("hgFindMatches", None),
                    }
                )

        result = {
            "genome": genome,
            "search_term": search_term,
            "match_count": len(matches),
            "matches": matches[:50],
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "UCSC Genome Browser",
                "query": search_term,
                "endpoint": "search",
            },
        }

    def _get_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get DNA sequence for a specified genomic region."""
        genome = arguments.get("genome", "")
        chrom = arguments.get("chrom", "")
        start = arguments.get("start", None)
        end = arguments.get("end", None)

        if not genome or not chrom or start is None or end is None:
            return {
                "status": "error",
                "error": "genome, chrom, start, and end parameters are all required",
            }

        if end <= start:
            return {"status": "error", "error": "end must be greater than start"}

        if end - start > 100000:
            return {
                "status": "error",
                "error": "Maximum sequence length is 100,000 bp. Please reduce the range.",
            }

        url = f"{UCSC_BASE_URL}/getData/sequence?genome={genome};chrom={chrom};start={start};end={end}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        dna = raw.get("dna", "")

        result = {
            "genome": genome,
            "chrom": chrom,
            "start": start,
            "end": end,
            "length": len(dna),
            "dna": dna,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "UCSC Genome Browser",
                "query": f"{genome}:{chrom}:{start}-{end}",
                "endpoint": "getData/sequence",
            },
        }

    def _get_track(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get annotation track data for a specified genomic region."""
        genome = arguments.get("genome", "")
        track = arguments.get("track", "")
        chrom = arguments.get("chrom", "")
        start = arguments.get("start", None)
        end = arguments.get("end", None)
        max_items = arguments.get("maxItemsOutput", 100)

        if not genome or not track or not chrom or start is None or end is None:
            return {
                "status": "error",
                "error": "genome, track, chrom, start, and end parameters are all required",
            }

        url = (
            f"{UCSC_BASE_URL}/getData/track?genome={genome};track={track};"
            f"chrom={chrom};start={start};end={end}"
        )
        if max_items:
            url += f";maxItemsOutput={max_items}"

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        # Track data is keyed by the track name
        track_type = raw.get("trackType", None)
        items = raw.get(track, [])
        if not isinstance(items, list):
            items = [items] if items else []

        result = {
            "genome": genome,
            "track": track,
            "track_type": track_type,
            "chrom": chrom,
            "start": start,
            "end": end,
            "item_count": len(items),
            "items": items,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "UCSC Genome Browser",
                "query": f"{genome}:{track}:{chrom}:{start}-{end}",
                "endpoint": "getData/track",
            },
        }
