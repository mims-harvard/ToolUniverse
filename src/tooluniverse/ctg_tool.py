from copy import deepcopy
from urllib.parse import urljoin
from .restful_tool import RESTfulTool, execute_RESTful_query
from .tool_registry import register_tool


@register_tool("ClinicalTrialsTool")
class ClinicalTrialsTool(RESTfulTool):
    _BASE_URL = "https://clinicaltrials.gov/api/v2"

    _OPERATION_URLS = {
        "search": "/studies",
        "get_study": "/studies",
        "stats_size": "/stats/size",
        "field_values": "/stats/field-values",
    }

    def __init__(self, tool_config):
        base_url = self._BASE_URL
        self._operation = (tool_config.get("fields") or {}).get("operation")

        if "tool_url" in tool_config:
            url_path = tool_config["tool_url"]
        else:
            url_path = self._OPERATION_URLS.get(self._operation, "/studies")

        full_url = urljoin(base_url + "/", url_path.lstrip("/"))
        super().__init__(tool_config, full_url)

        self.list_params_to_join = [
            "filter.ids",
            "filter.overallStatus",
            "fields",
            "sort",
        ]

        self.param_name_mapper = {
            "condition": "query.cond",
            "title": "query.titles",
            "intervention": "query.intr",
            "outcome": "query.outc",
            "overall_status": "filter.overallStatus",
            "query_term": "query.term",
        }

    def _map_param_names(self, arguments):
        """
        Maps the parameter names in the arguments dictionary to the expected parameter names defined in the tool's JSON configuration.

        Args:
            arguments (dict): Runtime arguments provided to the tool's run method.

        Returns
            dict: A new dictionary with mapped parameter names.
        """

        mapped_arguments = {}
        for key, value in arguments.items():
            if key in self.param_name_mapper:
                mapped_key = self.param_name_mapper[key]
                mapped_arguments[mapped_key] = value
            else:
                mapped_arguments[key] = value
        return mapped_arguments

    def _prepare_api_params(self, arguments):
        """
        Prepares the dictionary of parameters for the API query string based on tool config and runtime arguments.

        Args:
            arguments (dict): Runtime arguments provided to the tool's run method.

        Returns
            dict: A dictionary of parameters ready for the API requests.
        """
        api_params = {}

        for param_name, value in arguments.items():
            if value is not None:
                # Handle parameters defined as lists that need joining
                if param_name in self.list_params_to_join and isinstance(value, list):
                    # Join list items into a comma-separated string
                    api_params[param_name] = ",".join(map(str, value))
                else:
                    api_params[param_name] = value

        return api_params

    def _format_endpoint_url(self, arguments):
        """
        Formats the endpoint URL by substituting path parameters (like {nctId}) with values from the arguments dictionary.

        Args:
            arguments (dict): Runtime arguments provided to the tool's run method.

        Returns
            str: The formatted endpoint URL.
        """
        url_to_format = self.endpoint_url
        try:
            # Find keys in arguments that match placeholders in the URL template
            # e.g., if url_to_format is ".../studies/{nctId}", find 'nctId' in arguments
            path_params = {
                k: v for k, v in arguments.items() if f"{{{k}}}" in url_to_format
            }
            # Perform the substitution
            return url_to_format.format(**path_params)
        except KeyError as e:
            # This might happen if a placeholder exists but the corresponding key is missing in arguments
            print(
                f"Warning: Missing key {e} in arguments for URL formatting: {url_to_format}"
            )
            # Return the original URL; the API call will likely fail, but avoids crashing here
            return url_to_format

    def run(self, arguments):
        if not self._operation:
            raise NotImplementedError(
                "The run method should be implemented in subclasses."
            )
        if self._operation == "search":
            return self._run_search(arguments)
        elif self._operation == "get_study":
            return self._run_get_study(arguments)
        elif self._operation == "stats_size":
            return self._run_stats_size(arguments)
        elif self._operation == "field_values":
            return self._run_field_values(arguments)
        else:
            return {"error": f"Unknown operation: {self._operation}"}

    def _run_search(self, arguments):
        """Handle search operations (search_studies, search_by_intervention, search_by_sponsor)."""
        import requests

        _SEARCH_PARAM_MAP = {
            "query_cond": "query.cond",
            "query_intr": "query.intr",
            "query_term": "query.term",
            "filter_status": "filter.overallStatus",
            "filter_study_type": "filter.studyType",
            "page_size": "pageSize",
            "next_page_token": "pageToken",
            "intervention": "query.intr",
            "sponsor": "query.spons",
        }

        params = {"format": "json", "countTotal": "true"}
        params["fields"] = ",".join(
            [
                "NCTId",
                "BriefTitle",
                "OverallStatus",
                "BriefSummary",
                "Condition",
                "Phase",
            ]
        )

        # Build advanced filter clauses (filter.advanced for phase/studytype)
        advanced_clauses = []

        for key, value in arguments.items():
            if value is None:
                continue
            if key == "filter_phase":
                # CTG API v2 uses filter.advanced for phase, not filter.phase
                phases = [p.strip() for p in value.split(",")]
                phase_clause = " OR ".join(f"AREA[Phase]{p}" for p in phases)
                if len(phases) > 1:
                    phase_clause = f"({phase_clause})"
                advanced_clauses.append(phase_clause)
            elif key in _SEARCH_PARAM_MAP:
                params[_SEARCH_PARAM_MAP[key]] = value

        if advanced_clauses:
            params["filter.advanced"] = " AND ".join(advanced_clauses)

        resp = requests.get(f"{self._BASE_URL}/studies", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        studies = []
        for s in data.get("studies", []):
            proto = s.get("protocolSection", {})
            studies.append(
                {
                    "nct_id": proto.get("identificationModule", {}).get("nctId"),
                    "brief_title": proto.get("identificationModule", {}).get(
                        "briefTitle"
                    ),
                    "status": proto.get("statusModule", {}).get("overallStatus"),
                    "study_type": proto.get("designModule", {}).get("studyType"),
                    "phases": proto.get("designModule", {}).get("phases", []),
                    "enrollment": (
                        proto.get("designModule", {}).get("enrollmentInfo") or {}
                    ).get("count"),
                    "conditions": proto.get("conditionsModule", {}).get(
                        "conditions", []
                    ),
                    "interventions": proto.get("armsInterventionsModule", {}).get(
                        "interventionNames", []
                    ),
                    "sponsor": (
                        proto.get("sponsorCollaboratorsModule", {}).get("leadSponsor")
                        or {}
                    ).get("name"),
                    "start_date": (
                        proto.get("statusModule", {}).get("startDateStruct") or {}
                    ).get("date"),
                    "completion_date": (
                        proto.get("statusModule", {}).get("completionDateStruct") or {}
                    ).get("date"),
                }
            )

        return {
            "data": {
                "studies": studies,
                "total_count": data.get("totalCount"),
                "next_page_token": data.get("nextPageToken"),
            },
            "metadata": {"source": "ClinicalTrials.gov API v2", "operation": "search"},
        }

    def _run_get_study(self, arguments):
        """Get full details for a single study by NCT ID."""
        import requests

        nct_id = arguments.get("nct_id")
        if not nct_id:
            return {"error": "nct_id is required"}

        resp = requests.get(
            f"{self._BASE_URL}/studies/{nct_id}",
            params={"format": "json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        proto = data.get("protocolSection", {})

        study = {
            "nct_id": proto.get("identificationModule", {}).get("nctId"),
            "brief_title": proto.get("identificationModule", {}).get("briefTitle"),
            "official_title": proto.get("identificationModule", {}).get(
                "officialTitle"
            ),
            "status": proto.get("statusModule", {}).get("overallStatus"),
            "study_type": proto.get("designModule", {}).get("studyType"),
            "phases": proto.get("designModule", {}).get("phases", []),
            "enrollment": (
                proto.get("designModule", {}).get("enrollmentInfo") or {}
            ).get("count"),
            "brief_summary": proto.get("descriptionModule", {}).get("briefSummary"),
            "conditions": proto.get("conditionsModule", {}).get("conditions", []),
            "interventions": [
                {"type": i.get("type"), "name": i.get("name")}
                for i in proto.get("armsInterventionsModule", {}).get(
                    "interventions", []
                )
            ],
            "primary_outcomes": [
                {"measure": o.get("measure"), "timeFrame": o.get("timeFrame")}
                for o in proto.get("outcomesModule", {}).get("primaryOutcomes", [])
            ],
            "eligibility_criteria": proto.get("eligibilityModule", {}).get(
                "eligibilityCriteria"
            ),
            "sponsor": (
                proto.get("sponsorCollaboratorsModule", {}).get("leadSponsor") or {}
            ).get("name"),
            "locations": [
                {
                    "facility": loc.get("facility"),
                    "city": loc.get("city"),
                    "country": loc.get("country"),
                }
                for loc in proto.get("contactsLocationsModule", {}).get("locations", [])
            ],
            "references": proto.get("referencesModule", {}).get("references", []),
        }

        return {
            "data": study,
            "metadata": {
                "source": "ClinicalTrials.gov API v2",
                "operation": "get_study",
            },
        }

    def _run_stats_size(self, arguments):
        """Get aggregate ClinicalTrials.gov database statistics."""
        import requests

        resp = requests.get(f"{self._BASE_URL}/stats/size", timeout=30)
        resp.raise_for_status()
        data = resp.json()

        return {
            "data": {
                "total_studies": data.get("totalStudiesCount"),
                "average_byte_size": data.get("averageByteSize"),
                "largest_studies": data.get("largestStudies"),
            },
            "metadata": {
                "source": "ClinicalTrials.gov API v2",
                "operation": "stats_size",
            },
        }

    def _run_field_values(self, arguments):
        """Get value distribution for a specific field."""
        import requests

        field = arguments.get("field")
        if not field:
            return {"error": "field is required"}

        # CTG API v2: endpoint is /stats/fieldValues (camelCase), param is 'fields' (plural)
        params = {"fields": field}
        if arguments.get("query_cond"):
            params["query.cond"] = arguments["query_cond"]

        resp = requests.get(
            f"{self._BASE_URL}/stats/fieldValues", params=params, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()  # Returns a list of field objects

        values = []
        if isinstance(data, list) and data:
            field_obj = data[0]
            values = [
                {"value": item.get("value"), "studies_count": item.get("studiesCount")}
                for item in field_obj.get("topValues", [])
            ]

        return {
            "data": {
                "field": field,
                "values": values,
                "total_count": len(values),
            },
            "metadata": {
                "source": "ClinicalTrials.gov API v2",
                "operation": "field_values",
            },
        }


@register_tool("ClinicalTrialsSearchTool")
# Searching studies (/studies)
class ClinicalTrialsSearchTool(ClinicalTrialsTool):
    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.default_params_not_shown = {
            "format": "json",  # Default format for the response
            "sort": "@relevance",  # Default sort order
            "fields": [
                "NCTId",
                "BriefTitle",
                # "OfficialTitle",
                "OverallStatus",
                # "StartDate",
                # "PrimaryCompletionDate",
                # "PrimaryOutcomeMeasure",
                # "DescriptionModule",
                "BriefSummary",
                "Condition",
                "Phase",
                # "Intervention",
                # "InterventionName",
                # "InterventionArmGroupLabel",
                # "InterventionOtherName",
                # "WhyStopped",
                # "HasResults",
            ],  # NOTE: Can change this one
            "countTotal": True,  # NOTE: Can change this one
            "filter.advanced": "AREA[HasResults]true AND (AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4)",
            # TODO: Consider adding a YEAR filter for the query to remove trials that are too early? E.g., "AREA[LastUpdatePostDate]RANGE[2000-01-01,MAX]"
        }
        # "title": {
        #             "type": "string",
        #             "description": "Query for study titles using Essie expression syntax (e.g., 'lung cancer').",
        #             "required": false
        #         },
        # "outcome": {
        #             "type": "string",
        #             "description": "Query for outcome measures using Essie expression syntax (e.g., 'overall survival', 'adverse events', 'progress-free survival').",
        #             "required": false
        #         },
        # "query.locn": {
        #     "type": "string",
        #     "description": "Query for location terms using Essie expression syntax (e.g., 'California')."
        # },
        # "overall_status": {
        #             "type": "array",
        #             "description": "Filter by a list of overall study statuses (e.g., ['RECRUITING', 'COMPLETED']). ",
        #             "items": {
        #                 "type": "string",
        #                 "enum": ["ACTIVE_NOT_RECRUITING", "COMPLETED", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING", "RECRUITING", "SUSPENDED", "TERMINATED", "WITHDRAWN", "AVAILABLE", "NO_LONGER_AVAILABLE", "TEMPORARILY_NOT_AVAILABLE", "APPROVED_FOR_MARKETING", "WITHHELD", "UNKNOWN"]
        #             },
        #             "required": false
        #         },
        # "filter.ids": {
        #     "type": "array",
        #     "description": "Filter by a list of NCT IDs (e.g., ['NCT04852770', 'NCT01728545']).",
        #     "items": {
        #         "type": "string"
        #     }
        # },
        # "sort": {
        #     "type": "array",
        #     "description": "Comma- or pipe-separated list of fields to sort by for the studies, with optional direction. The returning studies are not sorted by default. Every list item contains a field/piece name and an optional sort direction (asc for ascending or desc for descending) after colon character (e.g., ['LastUpdatePostDate:desc', 'EnrollmentCount'], [@relevance]). Default sort order varies by field type. Special value '@relevance' sorts by query relevance.",
        #     "items": {
        #         "type": "string"
        #     }
        # },
        # "fields": {
        #     "type": "array",
        #     "description": "List of fields to return (e.g., ['NCTId', 'BriefTitle', 'OverallStatus', 'Phase', 'PrimaryCompletionDate', 'PrimaryOutcomeMeasure']). By default, we look at the following fields: ['NCTId', 'BriefTitle', 'OfficialTitle', 'OverallStatus', 'StartDate', 'PrimaryCompletionDate', 'PrimaryOutcomeMeasure', 'DescriptionModule', 'Condition', 'Phase', 'WhyStopped', 'HasResults'].",
        #     "items": {
        #         "type": "string"
        #     },
        #     "required": false
        # },

    def run(self, arguments):
        """
        Executes the search query for clinical trials.

        Args:
            arguments (dict): A dictionary containing parameters provided by the user/LLM

        Returns
            dict or str: The JSON response from the API as a dictionary,
                         or raw text for non-JSON responses, or an error dictionary.
        """
        arguments = self._map_param_names(arguments)
        query_params = deepcopy(self.query_schema)
        expected_param_names = self._map_param_names(
            self.parameters
        ).keys()  # NOTE: Workaround for not having an aligned schema in the JSON config

        # Prepare API parameters from arguments
        for k in expected_param_names:
            if k in arguments and arguments[k] is not None:
                query_params[k] = arguments[k]

        # Add default parameters that are not shown in the schema
        for k, v in self.default_params_not_shown.items():
            if k not in query_params:
                query_params[k] = v

        # Process list parameters that need to be joined
        api_params = self._prepare_api_params(query_params)

        # Fix a bug where 'countTotal' is a boolean but should be a string as input to API
        if "countTotal" in api_params and isinstance(api_params["countTotal"], bool):
            api_params["countTotal"] = str(api_params["countTotal"]).lower()

        formatted_endpoint_url = self.endpoint_url

        response = execute_RESTful_query(
            endpoint_url=formatted_endpoint_url, variables=api_params
        )

        # Simplify the output if the response is valid
        if (
            response is not None
            and response
            and "studies" in response.keys()
            and len(response["studies"]) > 0
        ):
            response = self._simplify_output(response)
        else:
            return "No studies found for the given query parameters. Please examine your input and try different parameters."

        return response

    def _simplify_output(self, response):
        new_response = []

        for study in response["studies"]:
            new_study = {
                "NCT ID": study["protocolSection"]["identificationModule"].get("nctId"),
            }
            if "identificationModule" in study["protocolSection"]:
                new_study["brief_title"] = study["protocolSection"][
                    "identificationModule"
                ].get("briefTitle")
            if "descriptionModule" in study["protocolSection"]:
                new_study["brief_summary"] = study["protocolSection"][
                    "descriptionModule"
                ].get("briefSummary")
            if "statusModule" in study["protocolSection"]:
                new_study["overall_status"] = study["protocolSection"][
                    "statusModule"
                ].get("overallStatus")
            if "conditionsModule" in study["protocolSection"]:
                new_study["condition"] = study["protocolSection"][
                    "conditionsModule"
                ].get("conditions")
            if "designModule" in study["protocolSection"]:
                new_study["phase"] = study["protocolSection"]["designModule"].get(
                    "phases"
                )
            new_study = {
                k: v for k, v in new_study.items() if v is not None
            }  # Remove None values
            new_response.append(new_study)

        # def remove_empty_values(obj):
        #     if isinstance(obj, dict):
        #         return {k: remove_empty_values(v) for k, v in obj.items()
        #                 if v not in [0, [], None]}
        #     elif isinstance(obj, list):
        #         return [remove_empty_values(v) for v in obj if v not in [0, [], None]]
        #     else:
        #         return obj
        # new_response = remove_empty_values(new_response)

        new_response = {"studies": new_response}
        if "nextPageToken" in response:
            new_response["nextPageToken"] = response["nextPageToken"]
        if "totalCount" in response:
            new_response["total_count"] = response["totalCount"]

        return new_response


@register_tool("ClinicalTrialsDetailsTool")
class ClinicalTrialsDetailsTool(ClinicalTrialsTool):
    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.default_params_not_shown = {
            "format": "json",
        }

    def run(self, arguments):
        arguments = self._map_param_names(arguments)
        expected_param_names = self._map_param_names(self.parameters).keys()
        query_params = deepcopy(self.query_schema)

        nct_ids_list = arguments.get("nct_ids")
        if (
            not nct_ids_list
            or not isinstance(nct_ids_list, list)
            or len(nct_ids_list) == 0
        ):
            return {
                "error": "Missing or invalid required parameter: nct_ids (must be a non-empty list)"
            }
        del arguments[
            "nct_ids"
        ]  # Remove 'nct_ids' from query_params as it is not a valid API parameter

        # Prepare API parameters from arguments
        for k in expected_param_names:
            if k in arguments and arguments[k] is not None:
                query_params[k] = arguments[k]

        # Add default parameters that are not shown in the schema
        for k, v in self.default_params_not_shown.items():
            if k not in query_params:
                query_params[k] = v

        if "description_type" in expected_param_names:
            query_type = "description"
            if query_params["description_type"].lower() == "full":
                query_params["fields"] = [
                    "NCTId",
                    "BriefTitle",
                    "OfficialTitle",
                    "BriefSummary",
                    "DetailedDescription",
                    "Phase",
                ]
            else:
                query_params["fields"] = [
                    "NCTId",
                    "BriefTitle",
                    "BriefSummary",
                    "Phase",
                ]
            del query_params["description_type"]
        elif "status_and_date" in expected_param_names:
            query_type = "status_and_date"
            if "status_and_date" in query_params:
                del query_params["status_and_date"]
            query_params["fields"] = [
                "NCTId",
                "OverallStatus",
                "LastKnownStatus",
                "WhyStopped",
                "StartDate",
                "PrimaryCompletionDate",
                "CompletionDate",
            ]
        elif "condition_and_intervention" in expected_param_names:
            query_type = "condition_and_intervention"
            if "condition_and_intervention" in query_params:
                del query_params["condition_and_intervention"]
            query_params["fields"] = [
                "NCTId",
                "Condition",
                "ArmGroupLabel",
                "ArmGroupType",
                "ArmGroupDescription",
                "ArmGroupInterventionName",
                "InterventionType",
                "InterventionName",
                "InterventionOtherName",
                "InterventionDescription",
                # "InterventionArmGroupLabel",
            ]
        elif "eligibility_criteria" in expected_param_names:
            query_type = "eligibility_criteria"
            if "eligibility_criteria" in query_params:
                del query_params["eligibility_criteria"]
            query_params["fields"] = [
                "NCTId",
                "HealthyVolunteers",
                "Sex",
                "GenderBased",
                "GenderDescription",
                "MinimumAge",
                "MaximumAge",
                "StudyPopulation",
                "EligibilityCriteria",
                # "SamplingMethod",
            ]
        elif "location" in expected_param_names:
            query_type = "location"
            if "location" in query_params:
                del query_params["location"]
            query_params["fields"] = [
                "NCTId",
                "LocationFacility",
                "LocationStatus",
                "LocationCity",
                "LocationState",
                "LocationCountry",
            ]
        elif "outcome_measures" in expected_param_names:
            query_type = "outcome_measures"
            if query_params["outcome_measures"].lower() == "primary":
                query_params["fields"] = [
                    "NCTId",
                    "PrimaryOutcome",
                ]
            elif query_params["outcome_measures"].lower() == "secondary":
                query_params["fields"] = [
                    "NCTId",
                    "SecondaryOutcome",
                ]
            else:
                query_params["fields"] = [
                    "NCTId",
                    "PrimaryOutcome",
                    "SecondaryOutcome",
                    # "OtherOutcome",
                ]
            del query_params["outcome_measures"]
        elif "references" in expected_param_names:
            query_type = "references"
            if "references" in query_params:
                del query_params["references"]
            query_params["fields"] = [
                "NCTId",
                "Reference",
                "SeeAlsoLink",
            ]

        # more difficult extractions here
        elif "baseline_characteristics" in expected_param_names:
            query_type = "baseline_characteristics"
            del query_params["baseline_characteristics"]
            query_params["fields"] = [
                "NCTId",
                "BaselineCharacteristicsModule",
            ]
            # TODO: Add this to the schema

        elif "outcome_measure" in expected_param_names:
            query_type = "outcome"
            outcome_measure = query_params["outcome_measure"]
            del query_params["outcome_measure"]
            query_params["fields"] = [
                "NCTId",
                "OutcomeMeasure",
            ]

        elif "adverse_event_type" in expected_param_names:
            query_type = "safety"
            organs = query_params.get("organ_systems", [])
            adverse_event_type = query_params.get("adverse_event_type", "serious")
            if "organ_systems" in query_params:
                del query_params["organ_systems"]
            del query_params["adverse_event_type"]
            query_params["fields"] = [
                "NCTId",
                "AdverseEventsModule",
            ]

        api_params = self._prepare_api_params(query_params)
        formatted_endpoint_url = self.endpoint_url

        responses = []
        for nct_id in nct_ids_list:
            formatted_endpoint_url = self._format_endpoint_url({"nctId": nct_id})
            response = execute_RESTful_query(
                endpoint_url=formatted_endpoint_url, variables=api_params
            )
            if response:
                responses.append(response)

        if query_type not in {"outcome", "safety"}:
            responses = [
                self._simplify_output(response, query_type) for response in responses
            ]
        elif query_type == "outcome":
            responses = [
                self._extract_outcomes_from_output(response, outcome_measure)
                for response in responses
            ]
        elif query_type == "safety":
            responses = [
                self._extract_safety_from_output(response, organs, adverse_event_type)
                for response in responses
            ]

        if sum([len(response) > 1 for response in responses]) == 0:
            return "No relevant information found for the given NCT IDs."

        return responses

    def _simplify_output(self, study, query_type):
        """Manually extract generally most useful information"""
        new_study = {
            "NCT ID": study["protocolSection"]["identificationModule"].get("nctId"),
        }
        if "identificationModule" in study["protocolSection"]:
            if "briefTitle" in study["protocolSection"]["identificationModule"]:
                new_study["brief_title"] = study["protocolSection"][
                    "identificationModule"
                ].get("briefTitle")
            if "officialTitle" in study["protocolSection"]["identificationModule"]:
                new_study["official_title"] = study["protocolSection"][
                    "identificationModule"
                ].get("officialTitle")
        if "statusModule" in study["protocolSection"]:
            if "overallStatus" in study["protocolSection"]["statusModule"]:
                new_study["overall_status"] = study["protocolSection"][
                    "statusModule"
                ].get("overallStatus")
            if "lastKnownStatus" in study["protocolSection"]["statusModule"]:
                new_study["last_known_status"] = study["protocolSection"][
                    "statusModule"
                ].get("lastKnownStatus")
            if "whyStopped" in study["protocolSection"]["statusModule"]:
                new_study["why_stopped"] = study["protocolSection"]["statusModule"].get(
                    "whyStopped"
                )
            if "startDateStruct" in study["protocolSection"]["statusModule"]:
                new_study["start_date"] = study["protocolSection"]["statusModule"][
                    "startDateStruct"
                ].get("date")
            if (
                "primaryCompletionDateStruct"
                in study["protocolSection"]["statusModule"]
            ):
                new_study["primary_completion_date"] = study["protocolSection"][
                    "statusModule"
                ]["primaryCompletionDateStruct"].get("date")
            if "completionDateStruct" in study["protocolSection"]["statusModule"]:
                new_study["completion_date"] = study["protocolSection"]["statusModule"][
                    "completionDateStruct"
                ].get("date")
        if "descriptionModule" in study["protocolSection"]:
            if "briefSummary" in study["protocolSection"]["descriptionModule"]:
                new_study["brief_summary"] = study["protocolSection"][
                    "descriptionModule"
                ].get("briefSummary")
            if "detailedDescription" in study["protocolSection"]["descriptionModule"]:
                new_study["detailed_description"] = study["protocolSection"][
                    "descriptionModule"
                ].get("detailedDescription")
        if "conditionsModule" in study["protocolSection"]:
            if "conditions" in study["protocolSection"]["conditionsModule"]:
                new_study["condition"] = study["protocolSection"][
                    "conditionsModule"
                ].get("conditions")
        if "designModule" in study["protocolSection"]:
            if "phases" in study["protocolSection"]["designModule"]:
                new_study["phase"] = study["protocolSection"]["designModule"].get(
                    "phases"
                )
            if "patientRegistry" in study["protocolSection"]["designModule"]:
                new_study["patient_registry"] = study["protocolSection"][
                    "designModule"
                ].get("patientRegistry")
            if "enrollmentInfo" in study["protocolSection"]["designModule"]:
                new_study["enrollment_info"] = study["protocolSection"][
                    "designModule"
                ].get("enrollmentInfo")
        if "armsInterventionsModule" in study["protocolSection"]:
            if "armGroups" in study["protocolSection"]["armsInterventionsModule"]:
                new_study["arm_groups"] = study["protocolSection"][
                    "armsInterventionsModule"
                ].get("armGroups")
            if "interventions" in study["protocolSection"]["armsInterventionsModule"]:
                new_study["interventions"] = study["protocolSection"][
                    "armsInterventionsModule"
                ].get("interventions")
        if "outcomesModule" in study["protocolSection"]:
            if "primaryOutcomes" in study["protocolSection"]["outcomesModule"]:
                new_study["primary_outcomes"] = study["protocolSection"][
                    "outcomesModule"
                ].get("primaryOutcomes")
            if "secondaryOutcomes" in study["protocolSection"]["outcomesModule"]:
                new_study["secondary_outcomes"] = study["protocolSection"][
                    "outcomesModule"
                ].get("secondaryOutcomes")
            # if "otherOutcomes" in study["protocolSection"]["outcomesModule"]:
            #     new_study["other_outcomes"] = study["protocolSection"]["outcomesModule"].get("otherOutcomes")
        if "eligibilityModule" in study["protocolSection"]:
            if "eligibilityCriteria" in study["protocolSection"]["eligibilityModule"]:
                new_study["eligibility_criteria"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("eligibilityCriteria")
            if "healthyVolunteers" in study["protocolSection"]["eligibilityModule"]:
                new_study["healthy_volunteers"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("healthyVolunteers")
            if "sex" in study["protocolSection"]["eligibilityModule"]:
                new_study["sex"] = study["protocolSection"]["eligibilityModule"].get(
                    "sex"
                )
            if "genderBased" in study["protocolSection"]["eligibilityModule"]:
                new_study["gender_based"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("genderBased")
            if "genderDescription" in study["protocolSection"]["eligibilityModule"]:
                new_study["gender_description"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("genderDescription")
            if "minimumAge" in study["protocolSection"]["eligibilityModule"]:
                new_study["minimum_age"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("minimumAge")
            if "maximumAge" in study["protocolSection"]["eligibilityModule"]:
                new_study["maximum_age"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("maximumAge")
            if "studyPopulation" in study["protocolSection"]["eligibilityModule"]:
                new_study["study_population"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("studyPopulation")
            # if "samplingMethod" in study["protocolSection"]["eligibilityModule"]:
            #     new_study["sampling_method"] = study["protocolSection"]["eligibilityModule"].get("samplingMethod")
        if "contactsLocationsModule" in study["protocolSection"]:
            if "locations" in study["protocolSection"]["contactsLocationsModule"]:
                new_study["locations"] = study["protocolSection"][
                    "contactsLocationsModule"
                ].get("locations")
        if "referencesModule" in study["protocolSection"]:
            if "references" in study["protocolSection"]["referencesModule"]:
                new_study["references"] = study["protocolSection"][
                    "referencesModule"
                ].get("references")
            if "seeAlsoLinks" in study["protocolSection"]["referencesModule"]:
                new_study["see_also_links"] = study["protocolSection"][
                    "referencesModule"
                ].get("seeAlsoLinks")

        new_study = self._remove_empty_values(new_study)

        return new_study

    def _extract_outcomes_from_output(self, study, outcome_measure):
        new_study = {}
        outcome_measure = outcome_measure.lower()
        new_study["NCT ID"] = study["protocolSection"]["identificationModule"].get(
            "nctId"
        )

        if (
            "resultsSection" in study
            and "outcomeMeasuresModule" in study["resultsSection"]
            and "outcomeMeasures" in study["resultsSection"]["outcomeMeasuresModule"]
        ):
            raw_outcomes = study["resultsSection"]["outcomeMeasuresModule"][
                "outcomeMeasures"
            ]
            outcomes = []
            for outcome in raw_outcomes:
                new_outcome = {}

                if (outcome_measure == "primary") and outcome.get("type") != "PRIMARY":
                    continue
                if (outcome_measure == "secondary") and outcome.get(
                    "type"
                ) != "SECONDARY":
                    continue
                if (outcome_measure == "all") and outcome.get("type") not in [
                    "PRIMARY",
                    "SECONDARY",
                ]:
                    continue
                if outcome_measure not in ["primary", "secondary", "all"]:
                    outcome_measure_variants = [outcome_measure]
                    # TODO: Add more rules here
                    outcome_measure_variants.append(outcome_measure.replace("-", " "))
                    outcome_measure_variants.append(outcome_measure.replace(" ", "-"))
                    outcome_measure_variants.append(
                        outcome_measure.replace("progression", "progress")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("progress ", "progression ")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("progress-", "progression-")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("patient", "participant")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("participant", "patient")
                    )
                    outcome_measure_variants.append(outcome_measure.replace("_", " "))
                    outcome_measure_variants.append(
                        outcome_measure.replace("percentage", "percent")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("percent ", "percentage ")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("percent-", "percentage-")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("proportion", "percentage")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("percentage", "proportion")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("proportion", "percent")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("percent", "proportion")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("time to event", "time-to-event")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("time-to-event", "time to event")
                    )
                    outcome_measure_variants = list(set(outcome_measure_variants))
                    found_match = False
                    for o in outcome_measure_variants:
                        if (
                            o in outcome.get("title", "").lower()
                            or o in outcome.get("description", "").lower()
                        ):
                            found_match = True
                            break
                    if not found_match:
                        continue

                new_outcome["title"] = outcome.get("title")
                new_outcome["description"] = outcome.get("description")
                new_outcome["population"] = outcome.get("populationDescription")
                new_outcome["time_frame"] = outcome.get("timeFrame")
                new_outcome["unit_analyzed"] = outcome.get("typeUnitsAnalyzed")

                measurement_type = outcome.get("paramType")
                if measurement_type:
                    measurement_type = measurement_type.lower()
                # GEOMETRIC_MEAN - Geometric Mean
                # GEOMETRIC_LEAST_SQUARES_MEAN - Geometric Least Squares Mean
                # LEAST_SQUARES_MEAN - Least Squares Mean
                # LOG_MEAN - Log Mean
                # MEAN - Mean
                # MEDIAN - Median
                # NUMBER - Number
                # COUNT_OF_PARTICIPANTS - Count of Participants
                # COUNT_OF_UNITS - Count of Units

                unit = outcome.get("unitOfMeasure")

                new_outcome["groups"] = outcome.get("groups")

                denoms = outcome.get("denoms")
                if denoms is not None:
                    if len(denoms) > 1:
                        # TODO: Investigate such trials
                        return f"Warning: Multiple denoms found for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    denoms = denoms[0]["counts"]
                    new_outcome["denominators"] = denoms

                classes = outcome.get("classes")
                if classes is not None:
                    if len(classes) > 1:
                        # TODO: Investigate such trials
                        return f"Warning: Multiple classes found for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    if "title" in classes[0] or "denoms" in classes[0]:
                        # TODO: Investigate such trials
                        return f"Warning: Unexpected structure in classes for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                        classes = classes[0]
                    elif "categories" in classes[0]:
                        classes = classes[0]["categories"]
                        if len(classes) > 1:
                            # TODO: Investigate such trials
                            return f"Warning: Multiple classes-categories found for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                        if "title" in classes[0]:
                            # TODO: Investigate such trials
                            return f"Warning: Unexpected structure in classes-categories for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                            classes = classes[0]
                        elif "measurements" in classes[0]:
                            classes = classes[0]["measurements"]
                        else:
                            # TODO: Investigate such trials
                            return f"Warning: Unexpected structure in classes-categories for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    else:
                        # TODO: Investigate such trials
                        return f"Warning: Unexpected structure in classes for outcome {new_outcome['title']} in study {new_study['NCT ID']}."

                    if measurement_type and unit:
                        new_outcome[measurement_type + " (" + unit + ")"] = classes
                    else:
                        # TODO: Investigate such trials
                        return f"Warning: Missing paramType or unitOfMeasure for outcome {new_outcome['title']} in study {new_study['NCT ID']}."

                analyses = outcome.get("analyses")
                if analyses is not None:
                    if len(analyses) > 1:
                        # TODO: Investigate such trials
                        return f"Warning: Multiple analyses found for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    analyses = analyses[0]
                    pvalue = analyses.get("pValue")
                    pvalue_comment = analyses.get("pValueComment")
                    statistic_test = analyses.get("statisticalMethod")
                    statistic_comment = analyses.get("statisticalComment")

                    statistic_name = analyses.get("paramType")
                    statistic = analyses.get("paramValue")
                    if statistic_name and statistic_test and statistic and pvalue:
                        new_outcome["p-value (" + statistic_test + ")"] = pvalue
                        new_outcome[statistic_name] = statistic
                    else:
                        # TODO: Investigate such trials
                        return f"Warning: Missing paramType, paramValue, statisticalMethod or pvalue for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    if statistic_comment:
                        new_outcome["statistic_comment"] = statistic_comment
                    if pvalue_comment:
                        new_outcome["pvalue_comment"] = pvalue_comment

                    statistic_test_type = analyses.get("nonInferiorityType")
                    statistic_test_type_comment = analyses.get(
                        "nonInferiorityTypeComment"
                    )
                    if statistic_test_type and statistic_test_type_comment:
                        new_outcome["statistic_test_type"] = statistic_test_type
                        new_outcome["statistic_test_type_comment"] = (
                            statistic_test_type_comment
                        )

                outcomes.append(new_outcome)

            new_study["outcomes"] = outcomes
            new_study = self._remove_empty_values(new_study)

        return new_study

    def _extract_safety_from_output(self, study, organs, adverse_event_type):
        new_study = {}
        adverse_event_type = adverse_event_type.lower()
        organs = [org.lower() for org in organs]
        new_study["NCT ID"] = study["protocolSection"]["identificationModule"].get(
            "nctId"
        )

        if (
            "resultsSection" in study
            and "adverseEventsModule" in study["resultsSection"]
        ):
            ae_data = study["resultsSection"]["adverseEventsModule"]
            new_study["freq_threshold"] = (
                ae_data["frequencyThreshold"] + "%"
                if "frequencyThreshold" in ae_data
                else None
            )
            groups = ae_data["eventGroups"]
            for group in groups:
                if "deathsNumAffected" in group:
                    del group["deathsNumAffected"]
                if "deathsNumAtRisk" in group:
                    del group["deathsNumAtRisk"]
            #     if "seriousNumAffected" in group:
            #         del group["seriousNumAffected"]
            #     if "seriousNumAtRisk" in group:
            #         del group["seriousNumAtRisk"]
            #     if "otherNumAffected" in group:
            #         del group["otherNumAffected"]
            #     if "otherNumAtRisk" in group:
            #         del group["otherNumAtRisk"]

            new_study["groups"] = groups

            if "seriousEvents" in ae_data and adverse_event_type != "other":
                raw_aes = ae_data["seriousEvents"]
                serious_aes = []
                for ae in raw_aes:
                    if adverse_event_type not in {"serious", "all"}:
                        ae_name = ae.get("term", "").lower()
                        if adverse_event_type not in ae_name:
                            continue
                    if len(organs) > 0:
                        organ_system = ae.get("organSystem", "").lower()
                        if organ_system not in organs:
                            continue

                    if "sourceVocabulary" in ae:
                        del ae["sourceVocabulary"]
                    if "assessmentType" in ae:
                        del ae["assessmentType"]

                    if "stats" in ae and len(ae["stats"]) > 0:
                        for group_stats in ae["stats"]:
                            if (
                                group_stats.get("numAffected") is not None
                                and group_stats.get("numAtRisk") is not None
                                and group_stats.get("numAtRisk", 0) > 0
                            ):
                                group_stats["percentage"] = (
                                    str(
                                        round(
                                            group_stats.get("numAffected", 0)
                                            / group_stats.get("numAtRisk", 1)
                                            * 100,
                                            2,
                                        )
                                    )
                                    + "%"
                                )
                            elif (
                                group_stats.get("numEvents") is not None
                                and group_stats.get("numAtRisk") is not None
                                and group_stats.get("numAtRisk", 0) > 0
                            ):
                                group_stats["percentage"] = (
                                    str(
                                        round(
                                            group_stats.get("numEvents", 0)
                                            / group_stats.get("numAtRisk", 1)
                                            * 100,
                                            2,
                                        )
                                    )
                                    + "%"
                                )
                            else:
                                group_stats["percentage"] = None

                            if "numEvents" in group_stats:
                                del group_stats["numEvents"]

                    serious_aes.append(ae)

                new_study["serious_adverse_events"] = serious_aes

            if "otherEvents" in ae_data and adverse_event_type != "serious":
                raw_aes = ae_data["otherEvents"]
                other_aes = []
                for ae in raw_aes:
                    if adverse_event_type not in {"other", "all"}:
                        ae_name = ae.get("term", "").lower()
                        if adverse_event_type not in ae_name:
                            continue
                    if len(organs) > 0:
                        organ_system = ae.get("organSystem", "").lower()
                        if organ_system not in organs:
                            continue

                    if "sourceVocabulary" in ae:
                        del ae["sourceVocabulary"]
                    if "assessmentType" in ae:
                        del ae["assessmentType"]

                    if "stats" in ae and len(ae["stats"]) > 0:
                        for group_stats in ae["stats"]:
                            if (
                                group_stats.get("numAffected") is not None
                                and group_stats.get("numAtRisk") is not None
                                and group_stats.get("numAtRisk", 0) > 0
                            ):
                                group_stats["percentage"] = (
                                    str(
                                        round(
                                            group_stats.get("numAffected", 0)
                                            / group_stats.get("numAtRisk", 1)
                                            * 100,
                                            2,
                                        )
                                    )
                                    + "%"
                                )
                            elif (
                                group_stats.get("numEvents") is not None
                                and group_stats.get("numAtRisk") is not None
                                and group_stats.get("numAtRisk", 0) > 0
                            ):
                                group_stats["percentage"] = (
                                    str(
                                        round(
                                            group_stats.get("numeEvents", 0)
                                            / group_stats.get("numAtRisk", 1)
                                            * 100,
                                            2,
                                        )
                                    )
                                    + "%"
                                )
                            else:
                                group_stats["percentage"] = None

                            if "numEvents" in group_stats:
                                del group_stats["numEvents"]

                    other_aes.append(ae)

                new_study["other_adverse_events"] = other_aes

            new_study = self._remove_empty_values(new_study)

        return new_study

    def _remove_empty_values(self, obj):
        if isinstance(obj, dict):
            return {
                k: self._remove_empty_values(v)
                for k, v in obj.items()
                if v not in [[], None]
            }
        elif isinstance(obj, list):
            return [self._remove_empty_values(v) for v in obj if v not in [[], None]]
        else:
            return obj
