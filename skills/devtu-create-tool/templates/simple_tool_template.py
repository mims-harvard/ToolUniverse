"""
Simple Tool Template

Use this template for basic tools that fetch and return data.
"""

from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool
import requests


@register_tool("SimpleToolTemplate")
class SimpleToolTemplate(BaseTool):
    """
    Brief description of what this tool does.
    
    This tool [ACTION] from [SOURCE].
    """
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with given arguments.
        
        Args:
            arguments: Dictionary containing tool parameters
            
        Returns:
            Dictionary containing results or error information
        """
        try:
            # 1. Extract and validate parameters
            param1 = arguments.get('param1')
            param2 = arguments.get('param2', 'default_value')
            
            if not param1:
                return {
                    "status": "error",
                    "error": "Missing required parameter: param1"
                }
            
            # 2. Perform operation
            result = self._fetch_data(param1, param2)
            
            # 3. Return structured response
            return {
                "status": "success",
                "data": result
            }
            
        except requests.HTTPError as e:
            return {
                "status": "error",
                "error": f"API request failed: {e.response.status_code}",
                "detail": e.response.text,
                "url": e.response.url
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _fetch_data(self, param1: str, param2: str) -> Dict[str, Any]:
        """
        Fetch data from the API.
        
        Args:
            param1: First parameter
            param2: Second parameter
            
        Returns:
            API response data
        """
        url = "https://api.example.com/endpoint"
        
        response = requests.get(
            url,
            params={
                'param1': param1,
                'param2': param2
            },
            timeout=30
        )
        response.raise_for_status()
        
        return response.json()
    
    def validate_parameters(self, arguments: Dict[str, Any]) -> None:
        """
        Optional: Custom validation logic beyond JSON schema.
        
        Args:
            arguments: Dictionary containing tool parameters
            
        Raises:
            ValueError: If validation fails
        """
        param1 = arguments.get('param1', '')
        
        if not param1:
            raise ValueError("param1 cannot be empty")
        
        if len(param1) < 2:
            raise ValueError("param1 must be at least 2 characters")
