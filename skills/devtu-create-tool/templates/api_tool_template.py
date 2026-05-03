"""
API Tool Template with Retry Logic

Use this template for tools that interact with external APIs
and need robust error handling and retry logic.
"""

from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool
import requests
import time


@register_tool("APIToolTemplate")
class APIToolTemplate(BaseTool):
    """
    API tool with comprehensive error handling and retry logic.
    
    This tool [ACTION] from [API_NAME] API.
    """
    
    def __init__(self):
        """Initialize the tool with base configuration."""
        super().__init__()
        self.base_url = "https://api.example.com"
        self.timeout = 30
        self.max_retries = 3
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with given arguments.
        
        Args:
            arguments: Dictionary containing tool parameters
            
        Returns:
            Dictionary containing results or error information
        """
        try:
            # Extract parameters
            query = arguments.get('query')
            limit = arguments.get('limit', 20)
            
            # Validate parameters
            if not query:
                return {
                    "status": "error",
                    "error": "Missing required parameter: query"
                }
            
            # Build request URL
            endpoint = f"{self.base_url}/search"
            params = {
                'q': query,
                'limit': limit
            }
            
            # Make request with retry logic
            response = self._request_with_retry(endpoint, params)
            data = response.json()
            
            # Process and return results
            return {
                "status": "success",
                "count": len(data.get('results', [])),
                "data": data
            }
            
        except requests.Timeout:
            return {
                "status": "error",
                "error": f"Request timed out after {self.timeout} seconds",
                "suggestion": "Try again or use a more specific query"
            }
        
        except requests.ConnectionError as e:
            return {
                "status": "error",
                "error": "Failed to connect to API",
                "detail": str(e),
                "suggestion": "Check network connection and API availability"
            }
        
        except requests.HTTPError as e:
            return {
                "status": "error",
                "error": f"API request failed: {e.response.status_code}",
                "detail": e.response.text,
                "url": e.response.url
            }
        
        except ValueError as e:
            return {
                "status": "error",
                "error": "Invalid response from API",
                "detail": str(e)
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {type(e).__name__}",
                "detail": str(e)
            }
    
    def _request_with_retry(
        self,
        url: str,
        params: Dict[str, Any],
        max_retries: int = None
    ) -> requests.Response:
        """
        Make HTTP request with exponential backoff retry logic.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If all retries fail
        """
        max_retries = max_retries or self.max_retries
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response
                
            except (requests.ConnectionError, requests.Timeout):
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                time.sleep(wait_time)
                
            except requests.HTTPError as e:
                # Don't retry 4xx client errors
                if 400 <= e.response.status_code < 500:
                    raise
                # Retry 5xx server errors
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                time.sleep(wait_time)
    
    def validate_parameters(self, arguments: Dict[str, Any]) -> None:
        """
        Validate parameters beyond JSON schema constraints.
        
        Args:
            arguments: Dictionary containing tool parameters
            
        Raises:
            ValueError: If validation fails
        """
        query = arguments.get('query', '')
        limit = arguments.get('limit', 20)
        
        if not query:
            raise ValueError("query cannot be empty")
        
        if not isinstance(limit, int):
            raise ValueError("limit must be an integer")
        
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
