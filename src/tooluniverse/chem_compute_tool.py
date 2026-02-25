"""
ChemCompute Tools

Provides local computational chemistry tools that require no external API calls.
Currently includes:
- SA Score: Synthetic Accessibility Score using RDKit SA_Score contribution
"""

from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("ChemComputeTool")
class ChemComputeTool(BaseTool):
    """
    Local computational chemistry tools using RDKit.

    No external API calls. Provides:
    - Synthetic Accessibility (SA) Score computation
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute chem compute tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "sa_score": self._sa_score,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    def _sa_score(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate the Synthetic Accessibility (SA) score for a SMILES string."""
        smiles = arguments.get("smiles")
        if not smiles:
            return {"status": "error", "error": "Missing required parameter: smiles"}

        try:
            from rdkit import Chem, RDConfig
            import os
            import sys

            sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
            import sascorer
        except ImportError as e:
            return {
                "status": "error",
                "error": f"RDKit is required for SA score calculation: {str(e)}",
            }

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"status": "error", "error": "Invalid SMILES string"}

        try:
            score = sascorer.calculateScore(mol)
        except Exception as e:
            return {
                "status": "error",
                "error": f"SA score calculation failed: {str(e)}",
            }

        if score < 3:
            interpretation = "easy"
        elif score <= 6:
            interpretation = "moderate"
        else:
            interpretation = "difficult"

        return {
            "status": "success",
            "data": {
                "smiles": smiles,
                "sa_score": round(score, 4),
                "interpretation": interpretation,
            },
        }
