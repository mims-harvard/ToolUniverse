from typing import Dict
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


@register_tool("FederalRegisterTool")
class FederalRegisterTool(BaseRESTTool):
    """REST tool for Federal Register API with bracket-notation parameter mapping."""

    def _get_param_mapping(self) -> Dict[str, str]:
        return {
            "term": "conditions[term]",
            "document_type": "conditions[type][]",
            "agency": "conditions[agencies][]",
        }
