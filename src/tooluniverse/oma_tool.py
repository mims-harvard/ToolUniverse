# oma_tool.py
"""
OMA (Orthologous MAtrix) Browser API tool for ToolUniverse.

OMA is a comprehensive database of orthologs among complete genomes.
It provides orthology predictions using a rigorous algorithm applied to
2,600+ genomes. OMA offers protein lookup, pairwise orthologs,
Hierarchical Orthologous Groups (HOGs), and OMA Groups.

API: https://omabrowser.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

OMA_BASE_URL = "https://omabrowser.org/api"


@register_tool("OMATool")
class OMATool(BaseTool):
    """
    Tool for querying the OMA Orthology Browser.

    OMA provides orthology relationships among 2,600+ complete genomes
    using a highly reliable algorithm. Supports protein lookup, pairwise
    orthologs, Hierarchical Orthologous Groups (HOGs), and OMA Groups.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "protein")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OMA API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"OMA API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to OMA API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"OMA API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying OMA: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate OMA endpoint."""
        if self.endpoint == "protein":
            return self._get_protein(arguments)
        elif self.endpoint == "orthologs":
            return self._get_orthologs(arguments)
        elif self.endpoint == "hog":
            return self._get_hog(arguments)
        elif self.endpoint == "group":
            return self._get_group(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein information by UniProt accession or OMA ID."""
        protein_id = arguments.get("protein_id", "")
        if not protein_id:
            return {
                "status": "error",
                "error": "protein_id parameter is required (UniProt accession e.g. P04637, or OMA ID e.g. HUMAN31534)",
            }

        url = f"{OMA_BASE_URL}/protein/{protein_id}/"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        species = data.get("species", {})
        locus = data.get("locus", {})

        result = {
            "entry_nr": data.get("entry_nr"),
            "oma_id": data.get("omaid"),
            "canonical_id": data.get("canonicalid"),
            "sequence_length": data.get("sequence_length"),
            "species_code": species.get("code"),
            "species_name": species.get("species"),
            "taxon_id": species.get("taxon_id"),
            "oma_group": data.get("oma_group"),
            "oma_hog_id": data.get("oma_hog_id"),
            "chromosome": data.get("chromosome"),
            "locus_start": locus.get("start"),
            "locus_end": locus.get("end"),
            "locus_strand": locus.get("strand"),
            "is_main_isoform": data.get("is_main_isoform"),
            "roothog_id": data.get("roothog_id"),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "OMA Browser",
                "query": protein_id,
            },
        }

    def _get_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get pairwise orthologs for a protein."""
        protein_id = arguments.get("protein_id", "")
        if not protein_id:
            return {
                "status": "error",
                "error": "protein_id parameter is required (UniProt accession e.g. P04637)",
            }

        rel_type = arguments.get("rel_type")
        per_page = arguments.get("per_page", 20)

        url = f"{OMA_BASE_URL}/protein/{protein_id}/orthologs/"
        params = {"per_page": min(per_page, 100)}
        if rel_type:
            params["rel_type"] = rel_type

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        for orth in data:
            species = orth.get("species", {})
            results.append(
                {
                    "oma_id": orth.get("omaid"),
                    "canonical_id": orth.get("canonicalid"),
                    "species_name": species.get("species"),
                    "species_code": species.get("code"),
                    "taxon_id": species.get("taxon_id"),
                    "rel_type": orth.get("rel_type"),
                    "distance": orth.get("distance"),
                    "score": orth.get("score"),
                    "sequence_length": orth.get("sequence_length"),
                    "chromosome": orth.get("chromosome"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "OMA Browser",
                "query": protein_id,
                "total_orthologs": len(results),
            },
        }

    def _get_hog(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get Hierarchical Orthologous Group (HOG) information."""
        hog_id = arguments.get("hog_id", "")
        if not hog_id:
            return {
                "status": "error",
                "error": "hog_id parameter is required (e.g. HOG:E0739094)",
            }

        url = f"{OMA_BASE_URL}/hog/{hog_id}/"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        for hog in data:
            children = []
            for child in hog.get("children_hogs", []):
                children.append(
                    {
                        "hog_id": child.get("hog_id"),
                        "alternative_levels": child.get("alternative_levels", [])[:5],
                    }
                )

            results.append(
                {
                    "hog_id": hog.get("hog_id"),
                    "level": hog.get("level"),
                    "roothog_id": hog.get("roothog_id"),
                    "completeness_score": hog.get("completeness_score"),
                    "description": hog.get("description"),
                    "parent_hogs": hog.get("parent_hogs", []),
                    "children_hogs": children[:10],
                    "alternative_levels": hog.get("alternative_levels", [])[:10],
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "OMA Browser",
                "query": hog_id,
                "total_entries": len(results),
            },
        }

    def _get_group(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get OMA Group details (strict 1:1 orthologs across all genomes)."""
        group_id = arguments.get("group_id", "")
        if not group_id:
            return {
                "status": "error",
                "error": "group_id parameter is required (numeric group ID, e.g. 1388790)",
            }

        url = f"{OMA_BASE_URL}/group/{group_id}/"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        members = []
        for m in data.get("members", [])[:30]:  # Limit members
            species = m.get("species", {})
            members.append(
                {
                    "oma_id": m.get("omaid"),
                    "canonical_id": m.get("canonicalid"),
                    "species_name": species.get("species"),
                    "species_code": species.get("code"),
                    "taxon_id": species.get("taxon_id"),
                    "sequence_length": m.get("sequence_length"),
                    "chromosome": m.get("chromosome"),
                }
            )

        result = {
            "group_nr": data.get("group_nr"),
            "fingerprint": data.get("fingerprint"),
            "description": data.get("description"),
            "members": members,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "OMA Browser",
                "query": str(group_id),
                "total_members": len(data.get("members", [])),
                "returned_members": len(members),
            },
        }
