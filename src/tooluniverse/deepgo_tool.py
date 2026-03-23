"""
DeepGO Tool - Predict protein function using Gene Ontology terms.

DeepGO uses deep learning (DeepGOPlus method) to predict protein functions
from amino acid sequences. Returns GO term predictions across Biological Process,
Molecular Function, and Cellular Component ontologies with confidence scores.
"""

from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool
import requests


@register_tool("DeepGOTool")
class DeepGOTool(BaseTool):
    """Tool for predicting protein function using DeepGO."""

    BASE_URL = "https://deepgo.cbrc.kaust.edu.sa/deepgo"
    API_VERSION = "1.0.26"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.operation = tool_config.get("fields", {}).get(
            "operation", "predict_function"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate operation handler."""
        operation = self.operation

        if operation == "predict_function":
            return self._predict_function(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _predict_function(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Predict protein function from sequence."""
        sequence = arguments.get("sequence")
        if not sequence:
            return {"status": "error", "error": "Missing required parameter: sequence"}

        # Clean sequence - remove whitespace and convert to uppercase
        sequence = "".join(sequence.split()).upper()

        # Validate sequence
        valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
        if not all(aa in valid_aa for aa in sequence):
            return {
                "status": "error",
                "error": "Invalid sequence: contains non-amino acid characters",
            }

        if len(sequence) < 10:
            return {
                "status": "error",
                "error": "Sequence too short: minimum 10 amino acids required",
            }

        if len(sequence) > 5000:
            return {
                "status": "error",
                "error": "Sequence too long: maximum 5000 amino acids supported",
            }

        # Get threshold for predictions
        threshold = arguments.get("threshold", 0.3)
        if not 0.1 <= threshold <= 1.0:
            return {"status": "error", "error": "Threshold must be between 0.1 and 1.0"}

        # Prepare request
        protein_name = arguments.get("name", "query")
        fasta_data = f">{protein_name}\n{sequence}"

        try:
            response = requests.post(
                f"{self.BASE_URL}/api/create",
                json={
                    "version": self.API_VERSION,
                    "data_format": "fasta",
                    "data": fasta_data,
                    "threshold": threshold,
                },
                headers={"Content-Type": "application/json"},
                timeout=120,  # Longer timeout for prediction
            )
            response.raise_for_status()

            data = response.json()

            # Extract predictions
            predictions = data.get("predictions", [])

            if not predictions:
                return {
                    "status": "success",
                    "data": {
                        "sequence": sequence[:50] + "..."
                        if len(sequence) > 50
                        else sequence,
                        "predictions": [],
                        "threshold": threshold,
                    },
                    "message": "No predictions above threshold",
                }

            # Format results
            pred = predictions[0]
            functions = pred.get("functions", [])

            result = {
                "sequence_name": pred.get("protein_info", protein_name),
                "sequence_length": len(sequence),
                "threshold": threshold,
                "predictions": {},
            }

            for category in functions:
                cat_name = category.get("name", "Unknown")
                cat_functions = category.get("functions", [])

                # Format: [GO_ID, name, score]
                formatted = [
                    {"go_id": f[0], "name": f[1], "score": round(f[2], 4)}
                    for f in cat_functions
                ]

                result["predictions"][cat_name] = formatted

            return {"status": "success", "data": result, "uuid": data.get("uuid")}

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request timed out after 120s"}
        except requests.exceptions.HTTPError as e:
            body = e.response.text or ""
            if e.response.status_code == 500 and (
                "No space left on device" in body or "OperationalError" in body
            ):
                return {
                    "status": "error",
                    "error": "DeepGO server is temporarily unavailable (disk full). "
                    "Try again later at https://deepgo.cbrc.kaust.edu.sa/deepgo/",
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Error: {str(e)}"}
