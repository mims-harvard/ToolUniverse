"""
Health Disparities Tool

Provides information about health disparities data sources including:
- CDC Social Vulnerability Index (SVI)
- County Health Rankings

Note: Many of these data sources are file-based (CSV downloads) rather than REST APIs.
This tool provides information and links to access the data.
"""

from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("HealthDisparitiesTool")
class HealthDisparitiesTool(BaseTool):
    """Health disparities data information tool."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]

    def _get_svi_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get SVI data source information."""
        year = arguments.get("year")
        geography = arguments.get("geography", "county")

        # SVI is typically released every 2 years
        # Common years: 2020, 2018, 2016, 2014, etc.
        base_url = "https://www.atsdr.cdc.gov/placeandhealth/svi"

        data_sources = []

        # Provide information about available SVI datasets
        if year:
            data_sources.append(
                {
                    "year": year,
                    "geography": geography,
                    "download_url": f"{base_url}/data_documentation_download.html",
                    "documentation_url": f"{base_url}/index.html",
                }
            )
        else:
            # Provide info for recent years
            for y in [2020, 2018, 2016]:
                data_sources.append(
                    {
                        "year": y,
                        "geography": geography,
                        "download_url": f"{base_url}/data_documentation_download.html",
                        "documentation_url": f"{base_url}/index.html",
                    }
                )

        return {
            "status": "success",
            "data": {
                "data_sources": data_sources,
                "note": "SVI data is available as downloadable CSV files. Visit the download URL to access the data. Data includes social vulnerability indicators at county, census tract, and state levels.",
            },
            "metadata": {
                "source": "CDC ATSDR Social Vulnerability Index",
                "endpoint": self.endpoint,
                "query": arguments,
            },
        }

    def _get_county_rankings_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get County Health Rankings information."""
        year = arguments.get("year")
        state = arguments.get("state")

        base_url = "https://www.countyhealthrankings.org"

        data_sources = [
            {
                "year": year or "latest",
                "state": state or "all",
                "access_url": f"{base_url}/explore-health-rankings",
            }
        ]

        return {
            "status": "success",
            "data": {
                "data_sources": data_sources,
                "note": "County Health Rankings data is available through their website. Visit the access URL to explore and download county-level health data. Data includes health outcomes, health factors, and health behaviors by county.",
            },
            "metadata": {
                "source": "County Health Rankings & Roadmaps",
                "endpoint": self.endpoint,
                "query": arguments,
            },
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the health disparities tool."""
        if self.endpoint == "svi":
            return self._get_svi_info(arguments)
        elif self.endpoint == "county_rankings":
            return self._get_county_rankings_info(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}
