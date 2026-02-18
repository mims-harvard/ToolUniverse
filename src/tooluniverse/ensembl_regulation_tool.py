# ensembl_regulation_tool.py
"""
Ensembl REST API Regulation and Conservation tool for ToolUniverse.

Provides access to:
- Transcription factor binding motif features (motif instances in genomic regions)
- Evolutionarily constrained elements (regions under purifying selection)
- Binding matrix details (position weight matrices for TF binding)

These endpoints complement the existing ensembl_get_regulatory_features tool
by adding TF-specific binding data and evolutionary conservation scores.

API: https://rest.ensembl.org/
No authentication required. Rate limit: 15 requests/second.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENSEMBL_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


@register_tool("EnsemblRegulationTool")
class EnsemblRegulationTool(BaseTool):
    """
    Tool for querying regulatory and conservation features from Ensembl REST API.

    Provides TF binding motifs, constrained elements, and binding matrices.
    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "motif_features"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl Regulation API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "error": f"Ensembl REST API request timed out after {self.timeout}s"
            }
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            if status == 400:
                return {"error": f"Bad request: check region format (chr:start-end)"}
            return {"error": f"Ensembl REST API HTTP error: {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint_type == "motif_features":
            return self._motif_features(arguments)
        elif self.endpoint_type == "constrained_elements":
            return self._constrained_elements(arguments)
        elif self.endpoint_type == "binding_matrix":
            return self._binding_matrix(arguments)
        return {"error": f"Unknown endpoint_type: {self.endpoint_type}"}

    def _motif_features(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get TF binding motif features in a genomic region."""
        species = arguments.get("species", "homo_sapiens")
        region = arguments.get("region", "")

        if not region:
            return {"error": "region is required (e.g., '7:140424943-140524564')"}

        url = f"{ENSEMBL_BASE_URL}/overlap/region/{species}/{region}"
        params = {"feature": "motif", "content-type": "application/json"}

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        if not isinstance(raw, list):
            raw = []

        motifs = []
        for entry in raw:
            motifs.append(
                {
                    "stable_id": entry.get("stable_id", ""),
                    "transcription_factor_complex": entry.get(
                        "transcription_factor_complex"
                    ),
                    "binding_matrix_stable_id": entry.get("binding_matrix_stable_id"),
                    "score": entry.get("score"),
                    "start": entry.get("start", 0),
                    "end": entry.get("end", 0),
                    "strand": entry.get("strand", 0),
                    "seq_region_name": entry.get("seq_region_name", ""),
                }
            )

        return {
            "data": {
                "region": region,
                "species": species,
                "motif_count": len(motifs),
                "motif_features": motifs[:200],
            },
            "metadata": {
                "source": "Ensembl REST API",
                "endpoint": f"overlap/region/{species}/{region}?feature=motif",
            },
        }

    def _constrained_elements(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get evolutionarily constrained elements in a genomic region."""
        species = arguments.get("species", "homo_sapiens")
        region = arguments.get("region", "")

        if not region:
            return {"error": "region is required (e.g., '17:7661779-7687538')"}

        url = f"{ENSEMBL_BASE_URL}/overlap/region/{species}/{region}"
        params = {"feature": "constrained", "content-type": "application/json"}

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        if not isinstance(raw, list):
            raw = []

        elements = []
        for entry in raw:
            elements.append(
                {
                    "id": entry.get("ID"),
                    "start": entry.get("start", 0),
                    "end": entry.get("end", 0),
                    "score": entry.get("score", 0),
                    "strand": entry.get("strand", 0),
                    "seq_region_name": entry.get("seq_region_name", ""),
                }
            )

        # Sort by score descending
        elements.sort(key=lambda x: x.get("score", 0), reverse=True)

        return {
            "data": {
                "region": region,
                "species": species,
                "element_count": len(elements),
                "constrained_elements": elements[:200],
            },
            "metadata": {
                "source": "Ensembl Compara",
                "endpoint": f"overlap/region/{species}/{region}?feature=constrained",
            },
        }

    def _binding_matrix(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a TF binding matrix by stable ID."""
        species = arguments.get("species", "homo_sapiens")
        matrix_id = arguments.get("binding_matrix_id", "")

        if not matrix_id:
            return {"error": "binding_matrix_id is required (e.g., 'ENSPFM0320')"}

        url = f"{ENSEMBL_BASE_URL}/species/{species}/binding_matrix/{matrix_id}"
        params = {"content-type": "application/json"}

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        # Extract associated TF names
        tfs = []
        for tf in raw.get("associated_transcription_factor_complexes", []):
            if isinstance(tf, dict):
                tfs.append(tf.get("name", str(tf)))
            else:
                tfs.append(str(tf))

        return {
            "data": {
                "stable_id": raw.get("stable_id", matrix_id),
                "name": raw.get("name"),
                "source": raw.get("source"),
                "length": raw.get("length", 0),
                "threshold": raw.get("threshold"),
                "unit": raw.get("unit"),
                "max_position_sum": raw.get("max_position_sum"),
                "elements_string": raw.get("elements_string"),
                "associated_tfs": tfs,
                "matrix": raw.get("elements", {}),
            },
            "metadata": {
                "source": "Ensembl REST API",
                "endpoint": f"species/{species}/binding_matrix/{matrix_id}",
            },
        }
