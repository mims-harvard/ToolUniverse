from typing import Dict, Any, List, Optional
import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("ClinicalTrialsGovTool")
class ClinicalTrialsGovTool(BaseTool):
    """
    Tool for searching clinical trials using ClinicalTrials.gov API v2.
    """

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the ClinicalTrials tool action.

        Args:
            arguments (Dict[str, Any]): Dictionary containing the action and its parameters.
                Expected keys:
                - action (str): "search_studies" or "get_study_details"
                - condition (str, optional): Condition to search for.
                - intervention (str, optional): Intervention/Drug to search for.
                - nct_id (str, optional): NCT ID for details.
                - limit (int, optional): Max results (default 10).

        Returns:
            Dict[str, Any]: The results.
        """
        action = arguments.get("action")

        if action == "search_studies":
            return self.search_studies(
                condition=arguments.get("condition"),
                intervention=arguments.get("intervention"),
                limit=arguments.get("limit", 10),
            )
        elif action == "get_study_details":
            nct_id = arguments.get("nct_id")
            if not nct_id:
                raise ValueError("nct_id is required for get_study_details")
            return self.get_study_details(nct_id)
        else:
            raise ValueError(f"Unknown action: {action}")

    def search_studies(
        self,
        condition: Optional[str] = None,
        intervention: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Search for clinical trials.
        """
        params = {"pageSize": limit, "format": "json"}

        if condition:
            params["query.cond"] = condition
        if intervention:
            params["query.intr"] = intervention

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            studies = []
            for study in data.get("studies", []):
                proto = study.get("protocolSection", {})
                ident = proto.get("identificationModule", {})
                status = proto.get("statusModule", {})

                studies.append(
                    {
                        "nctId": ident.get("nctId"),
                        "title": ident.get("officialTitle") or ident.get("briefTitle"),
                        "status": status.get("overallStatus"),
                        "conditions": proto.get("conditionsModule", {}).get(
                            "conditions", []
                        ),
                    }
                )

            return {"total_count": data.get("totalCount"), "studies": studies}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_study_details(self, nct_id: str) -> Dict[str, Any]:
        """
        Get full details for a study.
        """
        url = f"{self.BASE_URL}/{nct_id}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            proto = data.get("protocolSection", {})

            return {
                "nctId": nct_id,
                "title": proto.get("identificationModule", {}).get("officialTitle"),
                "summary": proto.get("descriptionModule", {}).get("briefSummary"),
                "eligibility": proto.get("eligibilityModule", {}),
                "contacts": proto.get("contactsLocationsModule", {}),
                "full_data_link": url,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
