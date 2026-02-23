"""
ClinicalTrials.gov REST API v2 tool for ToolUniverse.

ClinicalTrials.gov is the world's largest registry of clinical research studies,
maintained by the U.S. National Library of Medicine. It covers 572,000+ trials
across 200+ countries.

API: https://clinicaltrials.gov/data-api/api
No authentication required. Public access.
"""

import requests
from typing import Any

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

CLINICALTRIALS_BASE = "https://clinicaltrials.gov/api/v2"


@register_tool("CTGovAPITool")
class CTGovAPITool(BaseRESTTool):
    """
    Tool for querying the ClinicalTrials.gov API v2.

    Provides access to 572,000+ clinical trial records including:
    - Study protocol information (design, eligibility, interventions)
    - Recruitment status and enrollment data
    - Results and outcome measures
    - Sponsor and contact information

    No authentication required.
    """

    def __init__(self, tool_config: dict):
        super().__init__(tool_config)
        self.timeout = 30
        self.operation = tool_config.get("fields", {}).get("operation", "search")

    def run(self, arguments: dict) -> dict:
        """Execute the ClinicalTrials.gov API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "error": f"ClinicalTrials.gov request timed out after {self.timeout}s"
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "Failed to connect to ClinicalTrials.gov. Check network connectivity."
            }
        except requests.exceptions.HTTPError as e:
            return {"error": f"ClinicalTrials.gov HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying ClinicalTrials.gov: {str(e)}"}

    def _query(self, arguments: dict) -> dict:
        """Route to the appropriate endpoint."""
        op = self.operation
        if op == "search":
            return self._search_studies(arguments)
        elif op == "get_study":
            return self._get_study(arguments)
        elif op == "stats_size":
            return self._get_stats_size()
        elif op == "field_values":
            return self._get_field_values(arguments)
        else:
            return {"error": f"Unknown operation: {op}"}

    def _search_studies(self, arguments: dict) -> dict:
        """Search for clinical trials with various filters."""
        params: dict[str, Any] = {"format": "json"}

        # Map tool arguments to API query parameters
        if arguments.get("query_cond"):
            params["query.cond"] = arguments["query_cond"]
        if arguments.get("query_intr"):
            params["query.intr"] = arguments["query_intr"]
        if arguments.get("query_term"):
            params["query.term"] = arguments["query_term"]
        if arguments.get("intervention"):
            params["query.intr"] = arguments["intervention"]
        if arguments.get("sponsor"):
            params["query.spons"] = arguments["sponsor"]
        if arguments.get("filter_status"):
            params["filter.overallStatus"] = arguments["filter_status"]
        if arguments.get("filter_phase"):
            # API uses aggFilters for phase, not filter.phase
            # Format: "phase:1,2,3" -> map PHASE1->1, PHASE2->2, PHASE3->3, PHASE4->4
            phase_raw = arguments["filter_phase"]
            phase_nums = []
            for p in phase_raw.replace(" ", "").split(","):
                if "PHASE" in p.upper():
                    num = p.upper().replace("PHASE", "")
                    if num.isdigit():
                        phase_nums.append(num)
            if phase_nums:
                params["aggFilters"] = f"phase:{','.join(phase_nums)}"
        if arguments.get("filter_study_type"):
            params["filter.studyType"] = arguments["filter_study_type"]

        page_size = arguments.get("page_size", 10)
        params["pageSize"] = min(int(page_size), 1000)

        if arguments.get("next_page_token"):
            params["pageToken"] = arguments["next_page_token"]

        # Specify fields to return for efficiency
        params["fields"] = (
            "NCTId,BriefTitle,OfficialTitle,OverallStatus,StartDate,CompletionDate,"
            "StudyType,Phase,EnrollmentCount,Condition,InterventionName,LeadSponsorName,"
            "LocationCountry"
        )

        url = f"{CLINICALTRIALS_BASE}/studies"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        studies = []
        for s in data.get("studies", []):
            proto = s.get("protocolSection", {})
            id_mod = proto.get("identificationModule", {})
            status_mod = proto.get("statusModule", {})
            design_mod = proto.get("designModule", {})
            cond_mod = proto.get("conditionsModule", {})
            interv_mod = proto.get("armsInterventionsModule", {})
            sponsor_mod = proto.get("sponsorCollaboratorsModule", {})

            # Extract interventions
            interventions = [
                iv.get("name")
                for iv in interv_mod.get("interventions", [])
                if iv.get("name")
            ]

            studies.append(
                {
                    "nct_id": id_mod.get("nctId"),
                    "brief_title": id_mod.get("briefTitle"),
                    "official_title": id_mod.get("officialTitle"),
                    "status": status_mod.get("overallStatus"),
                    "start_date": status_mod.get("startDateStruct", {}).get("date"),
                    "completion_date": status_mod.get("completionDateStruct", {}).get(
                        "date"
                    ),
                    "study_type": design_mod.get("studyType"),
                    "phases": design_mod.get("phases", []),
                    "enrollment": design_mod.get("enrollmentInfo", {}).get("count"),
                    "conditions": cond_mod.get("conditions", []),
                    "interventions": interventions[:5],
                    "sponsor": sponsor_mod.get("leadSponsor", {}).get("name"),
                }
            )

        return {
            "data": {
                "studies": studies,
                "total_count": data.get("totalCount"),
                "next_page_token": data.get("nextPageToken"),
            },
            "metadata": {
                "source": "ClinicalTrials.gov",
                "api_version": "v2",
                "returned_count": len(studies),
            },
        }

    def _get_study(self, arguments: dict) -> dict:
        """Get full details for a single study by NCT ID."""
        nct_id = arguments.get("nct_id", "").strip()
        if not nct_id:
            return {"error": "nct_id parameter is required (e.g., 'NCT04280705')"}

        url = f"{CLINICALTRIALS_BASE}/studies/{nct_id}"
        resp = requests.get(url, params={"format": "json"}, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        proto = data.get("protocolSection", {})
        id_mod = proto.get("identificationModule", {})
        status_mod = proto.get("statusModule", {})
        desc_mod = proto.get("descriptionModule", {})
        design_mod = proto.get("designModule", {})
        cond_mod = proto.get("conditionsModule", {})
        interv_mod = proto.get("armsInterventionsModule", {})
        outcomes_mod = proto.get("outcomesModule", {})
        elig_mod = proto.get("eligibilityModule", {})
        contacts_mod = proto.get("contactsLocationsModule", {})
        sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
        refs_mod = proto.get("referencesModule", {})

        # Extract arms/interventions
        arms = []
        for arm in interv_mod.get("armGroups", [])[:10]:
            arms.append(
                {
                    "label": arm.get("label"),
                    "type": arm.get("type"),
                    "description": arm.get("description"),
                    "intervention_names": arm.get("interventionNames", []),
                }
            )

        interventions = []
        for iv in interv_mod.get("interventions", [])[:10]:
            interventions.append(
                {
                    "name": iv.get("name"),
                    "type": iv.get("type"),
                    "description": iv.get("description"),
                }
            )

        # Extract primary outcomes
        primary_outcomes = []
        for o in outcomes_mod.get("primaryOutcomes", [])[:5]:
            primary_outcomes.append(
                {
                    "measure": o.get("measure"),
                    "description": o.get("description"),
                    "time_frame": o.get("timeFrame"),
                }
            )

        # Extract locations (first 5)
        locations = []
        for loc in contacts_mod.get("locations", [])[:5]:
            locations.append(
                {
                    "facility": loc.get("facility"),
                    "city": loc.get("city"),
                    "country": loc.get("country"),
                    "status": loc.get("status"),
                }
            )

        # Extract references
        refs = []
        for ref in refs_mod.get("references", [])[:5]:
            refs.append(
                {
                    "pmid": ref.get("pmid"),
                    "citation": ref.get("citation"),
                }
            )

        return {
            "data": {
                "nct_id": id_mod.get("nctId"),
                "brief_title": id_mod.get("briefTitle"),
                "official_title": id_mod.get("officialTitle"),
                "organization": id_mod.get("organization", {}).get("fullName"),
                "status": status_mod.get("overallStatus"),
                "why_stopped": status_mod.get("whyStopped"),
                "start_date": status_mod.get("startDateStruct", {}).get("date"),
                "completion_date": status_mod.get("completionDateStruct", {}).get(
                    "date"
                ),
                "brief_summary": desc_mod.get("briefSummary"),
                "study_type": design_mod.get("studyType"),
                "phases": design_mod.get("phases", []),
                "enrollment": design_mod.get("enrollmentInfo", {}).get("count"),
                "allocation": design_mod.get("designInfo", {}).get("allocation"),
                "masking": design_mod.get("designInfo", {})
                .get("maskingInfo", {})
                .get("masking"),
                "primary_purpose": design_mod.get("designInfo", {}).get(
                    "primaryPurpose"
                ),
                "conditions": cond_mod.get("conditions", []),
                "keywords": cond_mod.get("keywords", []),
                "sponsor": sponsor_mod.get("leadSponsor", {}).get("name"),
                "eligibility_criteria": elig_mod.get("eligibilityCriteria"),
                "minimum_age": elig_mod.get("minimumAge"),
                "maximum_age": elig_mod.get("maximumAge"),
                "sex": elig_mod.get("sex"),
                "healthy_volunteers": elig_mod.get("healthyVolunteers"),
                "arms": arms,
                "interventions": interventions,
                "primary_outcomes": primary_outcomes,
                "locations": locations,
                "references": refs,
            },
            "metadata": {
                "nct_id": nct_id,
                "source": "ClinicalTrials.gov",
                "api_version": "v2",
                "has_results": data.get("resultsSection") is not None,
            },
        }

    def _get_stats_size(self) -> dict:
        """Get aggregate statistics about the ClinicalTrials.gov database."""
        url = f"{CLINICALTRIALS_BASE}/stats/size"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        return {
            "data": {
                "total_studies": data.get("totalStudies") or data.get("studiesCount"),
                "average_byte_size": data.get("averageByteSize"),
                "byte_size_percentiles": data.get("percentiles", {}),
                "largest_studies": data.get("largestStudies", [])[:5],
            },
            "metadata": {
                "source": "ClinicalTrials.gov",
                "api_version": "v2",
            },
        }

    def _get_field_values(self, arguments: dict) -> dict:
        """Get value distribution for a specific field across studies."""
        field = arguments.get("field", "")
        if not field:
            return {
                "error": "field parameter is required (e.g., 'Phase', 'OverallStatus')"
            }

        # The endpoint returns ALL fields - we filter client-side
        url = f"{CLINICALTRIALS_BASE}/stats/field/values"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        all_fields = resp.json()  # list of field objects

        # Find matching field (case-insensitive on 'piece' name)
        field_lower = field.lower()
        matching = [f for f in all_fields if f.get("piece", "").lower() == field_lower]

        if not matching:
            # Try partial match
            matching = [
                f for f in all_fields if field_lower in f.get("piece", "").lower()
            ]

        if not matching:
            available = sorted({f.get("piece") for f in all_fields if f.get("piece")})[
                :20
            ]
            return {
                "error": f"Field '{field}' not found. Available fields include: {available}"
            }

        field_obj = matching[0]
        top_values = field_obj.get("topValues", [])
        page_size = min(int(arguments.get("page_size", 50)), len(top_values))
        values = [
            {
                "value": v.get("value"),
                "studies_count": v.get("studiesCount"),
            }
            for v in top_values[:page_size]
        ]

        return {
            "data": {
                "field": field_obj.get("piece"),
                "field_path": field_obj.get("field"),
                "field_type": field_obj.get("type"),
                "unique_values_count": field_obj.get("uniqueValuesCount"),
                "missing_studies_count": field_obj.get("missingStudiesCount"),
                "values": values,
            },
            "metadata": {
                "source": "ClinicalTrials.gov",
                "api_version": "v2",
            },
        }
