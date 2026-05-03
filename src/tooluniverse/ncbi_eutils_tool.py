"""
NCBI E-utilities Tool with Rate Limiting

This module provides a base class for NCBI E-utilities API tools with
built-in rate limiting and retry logic to handle 429 errors.
"""

import time
import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool


class NCBIEUtilsTool(BaseTool):
    """Base class for NCBI E-utilities tools with rate limiting."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.last_request_time = 0
        self.min_interval = 0.34  # ~3 requests/second (NCBI limit without API key)
        self.max_retries = 3
        self.initial_retry_delay = 1
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make request with rate limiting and retry logic."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            # Rate limiting
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)

            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                self.last_request_time = time.time()
                response.raise_for_status()

                # Try to parse JSON response
                try:
                    data = response.json()
                except ValueError:
                    # If not JSON, return text
                    data = response.text

                return {
                    "status": "success",
                    "data": data,
                    "url": url,
                    "content_type": response.headers.get(
                        "content-type", "application/json"
                    ),
                }

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    # Exponential backoff for rate limiting
                    delay = self.initial_retry_delay * (2**attempt)
                    print(
                        f"Rate limited, retrying in {delay} seconds... (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    continue
                else:
                    return {
                        "status": "error",
                        "error": f"NCBI E-utilities API request failed: {str(e)}",
                        "url": url,
                        "status_code": (
                            e.response.status_code if hasattr(e, "response") else None
                        ),
                    }
            except requests.exceptions.RequestException as e:
                return {
                    "status": "error",
                    "error": f"NCBI E-utilities API request failed: {str(e)}",
                    "url": url,
                }

        return {
            "status": "error",
            "error": f"NCBI E-utilities API request failed after {self.max_retries} attempts",
            "url": url,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(self.endpoint, arguments)
