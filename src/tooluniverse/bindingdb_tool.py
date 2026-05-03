"""
BindingDB Tool - Query protein-ligand binding affinity data.

BindingDB contains 3.2M data points for 1.4M compounds and 11.4K targets.
Provides binding affinities (Ki, IC50, Kd) for drug discovery research.
"""

from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("BindingDBTool")
class BindingDBTool(BaseTool):
    """Tool for querying BindingDB binding affinity database."""

    BASE_URL = "https://www.bindingdb.org/rest"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_ligands_by_uniprot"
        )

    _BROKEN_MSG = (
        "BindingDB REST API is currently unavailable (requests time out). "
        "Use ChEMBL (ChEMBL_get_target_activities) or PubChem BioAssay for binding affinity data."
    )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "error", "error": self._BROKEN_MSG}
