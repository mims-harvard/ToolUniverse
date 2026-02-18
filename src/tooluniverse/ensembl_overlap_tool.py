# ensembl_overlap_tool.py
"""
Ensembl Overlap tool for ToolUniverse.

The Ensembl Overlap API retrieves genomic features (genes, transcripts,
regulatory elements, variants, repeats) overlapping a given genomic region
or gene. This is fundamental for understanding what functional elements
exist in a region of interest.

API: https://rest.ensembl.org/overlap/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENSEMBL_REST_BASE = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


@register_tool("EnsemblOverlapTool")
class EnsemblOverlapTool(BaseTool):
    """
    Tool for querying Ensembl Overlap API.

    Supports:
    - Get features overlapping a genomic region (genes, transcripts, regulatory)
    - Get features overlapping an Ensembl gene ID

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "region")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl Overlap API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "error": f"Ensembl API timed out after {self.timeout}s. Try a smaller region."
            }
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 400:
                return {
                    "error": "Bad request. Check region format (e.g., '17:7661779-7687546') and feature types."
                }
            if status == 404:
                return {
                    "error": "Region or gene not found. Verify species and coordinates."
                }
            return {"error": f"Ensembl REST API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "region":
            return self._overlap_region(arguments)
        elif self.endpoint == "gene_id":
            return self._overlap_gene(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _overlap_region(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get features overlapping a genomic region."""
        species = arguments.get("species", "human")
        region = arguments.get("region", "")
        feature_types = arguments.get("feature_types", "gene")

        if not region:
            return {
                "error": "region is required (format: 'chr:start-end', e.g., '17:7661779-7687546')."
            }

        url = f"{ENSEMBL_REST_BASE}/overlap/region/{species}/{region}"

        # Build feature parameters
        params = {"content-type": "application/json"}
        features = [f.strip() for f in feature_types.split(",")]
        for f in features:
            params.setdefault("feature", [])
            if isinstance(params["feature"], list):
                params["feature"].append(f)
            else:
                params["feature"] = [params["feature"], f]

        # Use semicolon-separated params for Ensembl REST
        feature_str = ";".join([f"feature={f}" for f in features])
        full_url = f"{url}?{feature_str};content-type=application/json"

        response = requests.get(full_url, headers=ENSEMBL_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            return {"error": "Unexpected response format from Ensembl API."}

        # Categorize results by feature type
        by_type = {}
        for item in data:
            ft = item.get("feature_type", "unknown")
            by_type.setdefault(ft, [])
            by_type[ft].append(item)

        # Format results
        formatted_features = []
        for item in data[:100]:
            feature = {
                "feature_type": item.get("feature_type"),
                "id": item.get("id"),
                "start": item.get("start"),
                "end": item.get("end"),
                "strand": item.get("strand"),
                "seq_region_name": item.get("seq_region_name"),
                "biotype": item.get("biotype"),
                "source": item.get("source"),
            }
            if item.get("external_name"):
                feature["external_name"] = item["external_name"]
            if item.get("description"):
                feature["description"] = item["description"][:200]
            formatted_features.append(feature)

        type_summary = {k: len(v) for k, v in by_type.items()}

        return {
            "data": {
                "region": region,
                "species": species,
                "features": formatted_features,
                "type_summary": type_summary,
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "total_features": len(data),
                "returned": len(formatted_features),
            },
        }

    def _overlap_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get features overlapping an Ensembl gene ID."""
        gene_id = arguments.get("gene_id", "")
        feature_types = arguments.get("feature_types", "gene")

        if not gene_id:
            return {
                "error": "gene_id is required (Ensembl gene ID, e.g., 'ENSG00000141510' for TP53)."
            }

        features = [f.strip() for f in feature_types.split(",")]
        feature_str = ";".join([f"feature={f}" for f in features])
        url = f"{ENSEMBL_REST_BASE}/overlap/id/{gene_id}?{feature_str};content-type=application/json"

        response = requests.get(url, headers=ENSEMBL_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            return {"error": "Unexpected response format from Ensembl API."}

        # Categorize and format
        by_type = {}
        for item in data:
            ft = item.get("feature_type", "unknown")
            by_type.setdefault(ft, [])
            by_type[ft].append(item)

        formatted_features = []
        for item in data[:100]:
            feature = {
                "feature_type": item.get("feature_type"),
                "id": item.get("id"),
                "start": item.get("start"),
                "end": item.get("end"),
                "strand": item.get("strand"),
                "seq_region_name": item.get("seq_region_name"),
                "biotype": item.get("biotype"),
                "source": item.get("source"),
            }
            if item.get("external_name"):
                feature["external_name"] = item["external_name"]
            if item.get("description"):
                feature["description"] = item["description"][:200]
            if item.get("transcript_id"):
                feature["transcript_id"] = item["transcript_id"]
            formatted_features.append(feature)

        type_summary = {k: len(v) for k, v in by_type.items()}

        return {
            "data": {
                "gene_id": gene_id,
                "features": formatted_features,
                "type_summary": type_summary,
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "total_features": len(data),
                "returned": len(formatted_features),
            },
        }
