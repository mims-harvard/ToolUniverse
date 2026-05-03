import os
import copy
import requests
import urllib.parse
from .base_tool import BaseTool
from .tool_registry import register_tool

# ---- Helper: human readable -> openFDA code mapping ----
HUMAN_TO_FDA_MAP = {
    "fulfillexpeditecriteria": {"Yes": "1", "No": "2"},
    "patient.patientsex": {"Unknown": "0", "Male": "1", "Female": "2"},
    "patient.patientagegroup": {
        "Neonate": "1",
        "Infant": "2",
        "Child": "3",
        "Adolescent": "4",
        "Adult": "5",
        "Elderly": "6",
    },
    "patientonsetageunit": {
        "Decade": "800",
        "Year": "801",
        "Month": "802",
        "Week": "803",
        "Day": "804",
        "Hour": "805",
    },
    "patient.reaction.reactionoutcome": {
        "Recovered/resolved": "1",
        "Recovering/resolving": "2",
        "Not recovered/not resolved": "3",
        "Recovered/resolved with sequelae": "4",
        "Fatal": "5",
        "Unknown": "6",
    },
    "serious": {"Yes": "1", "No": "2"},
    "seriousnessdeath": {"Yes": "1"},
    "seriousnesshospitalization": {"Yes": "1"},
    "seriousnessdisabling": {"Yes": "1"},
    "seriousnesslifethreatening": {"Yes": "1"},
    "seriousnessother": {"Yes": "1"},
    "primarysource.qualification": {
        "Physician": "1",
        "Pharmacist": "2",
        "Other health professional": "3",
        "Lawyer": "4",
        "Consumer or non-health professional": "5",
    },
    "patient.drug.drugcharacterization": {
        "Suspect": "1",
        "Concomitant": "2",
        "Interacting": "3",
    },
    "patient.drug.drugadministrationroute": {
        "Oral": "048",
        "Intravenous": "042",
        "Intramuscular": "030",
        "Subcutaneous": "058",
        "Rectal": "054",
        "Topical": "061",
        "Respiratory (inhalation)": "055",
        "Ophthalmic": "047",
        "Unknown": "065",
    },
}


# ---- Base Tool Class ----
@register_tool("FDADrugAdverseEventTool")
class FDADrugAdverseEventTool(BaseTool):
    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)
        self.endpoint_url = endpoint_url
        self.api_key = api_key or os.getenv("FDA_API_KEY")
        self.search_fields = tool_config.get("fields", {}).get("search_fields", {})
        self.return_fields = tool_config.get("fields", {}).get("return_fields", [])
        self.count_field = tool_config.get("count_field") or (
            self.return_fields[0] if self.return_fields else None
        )
        self.return_fields_mapping = tool_config.get("fields", {}).get(
            "return_fields_mapping", {}
        )

        if not self.count_field:
            raise ValueError(
                "Either 'count_field' or 'return_fields' must be defined in tool_config."
            )

        # Store allowed enum values
        self.parameter_enums = {}
        if "parameter" in tool_config and "properties" in tool_config["parameter"]:
            for param_name, param_def in tool_config["parameter"]["properties"].items():
                if "enum" in param_def:
                    self.parameter_enums[param_name] = param_def["enum"]

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        # Validate enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return {"status": "error", "error": validation_error}

        # Store reactionmeddraverse for filtering results
        reaction_filter = arguments.get("reactionmeddraverse")

        response = self._search(arguments)
        return self._post_process(response, reaction_filter=reaction_filter)

    def validate_enum_arguments(self, arguments):
        """Validate that enum-based arguments match the allowed values"""
        for param_name, value in arguments.items():
            if param_name in self.parameter_enums and value is not None:
                allowed_values = self.parameter_enums[param_name]
                if value not in allowed_values:
                    return f"Invalid value '{value}' for parameter '{param_name}'. Allowed values are: {', '.join(allowed_values)}"
        return None

    def _post_process(self, response, reaction_filter=None):
        if not response or not isinstance(response, list):
            return []

        mapped_results = []
        for item in response:
            try:
                term = item.get("term")
                count = item.get("count", 0)

                # If reaction_filter is specified, only include matching reactions
                if reaction_filter is not None:
                    # Case-insensitive comparison
                    if term and term.upper() != reaction_filter.upper():
                        continue

                # Apply mapping if available
                if self.return_fields_mapping:
                    mapped_term = self.return_fields_mapping.get(
                        self.count_field, {}
                    ).get(str(term), term)
                    mapped_results.append({"term": mapped_term, "count": count})
                else:
                    mapped_results.append({"term": term, "count": count})
            except Exception:
                # Keep the original term in case of an exception
                if reaction_filter is None or (
                    isinstance(item, dict)
                    and item.get("term", "").upper() == reaction_filter.upper()
                ):
                    mapped_results.append(item)

        return mapped_results

    def _search(self, arguments):
        search_parts = []
        for param_name, value in arguments.items():
            fda_fields = self.search_fields.get(
                param_name, [param_name]
            )  # Map param -> FDA field
            # Use the first field name for value mapping
            fda_field = fda_fields[0] if fda_fields else param_name

            # Apply value mapping using FDA field name
            # (for proper enum mapping)
            mapping_error, mapped_value = self._map_value(fda_field, value)
            if mapping_error:
                return [{"error": mapping_error}]
            if mapped_value is None:
                continue  # Skip this field if instructed

            # Build search parts using FDA field name(s)
            # If multiple fields for same param, use OR logic within the param
            if len(fda_fields) > 1:
                # Multiple fields for same parameter - use OR
                field_parts = []
                for fda_field_name in fda_fields:
                    if isinstance(mapped_value, str) and " " in mapped_value:
                        field_parts.append(f'{fda_field_name}:"{mapped_value}"')
                    else:
                        field_parts.append(f"{fda_field_name}:{mapped_value}")
                # Join multiple fields with OR
                search_parts.append("+OR+".join(field_parts))
            else:
                # Single field - normal behavior
                fda_field_name = fda_fields[0]
                if isinstance(mapped_value, str) and " " in mapped_value:
                    search_parts.append(f'{fda_field_name}:"{mapped_value}"')
                else:
                    search_parts.append(f"{fda_field_name}:{mapped_value}")

        # Final search query - join different parameters with AND
        search_query = "+AND+".join(search_parts)
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Build URL
        if self.api_key:
            url = f"{self.endpoint_url}?api_key={self.api_key}&search={search_encoded}&count={self.count_field}"
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&count={self.count_field}"
            )

        # API request
        try:
            response = requests.get(url)
            # Handle 404 as "no matches found" - return empty list instead of error
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return []  # Return empty list for no matches
                except (ValueError, KeyError):
                    pass
            response.raise_for_status()
            response = response.json()
            if "results" in response:
                response = response["results"]
            return response
        except requests.exceptions.RequestException as e:
            return [{"error": f"API request failed: {str(e)}"}]

    def _map_value(self, param_name, value):
        # Special handling for seriousness fields: if value is "No", skip this field
        seriousness_fields = {
            "seriousnessdeath",
            "seriousnesshospitalization",
            "seriousnessdisabling",
            "seriousnesslifethreatening",
            "seriousnessother",
        }
        if param_name in seriousness_fields:
            if value == "No":
                return None, None  # Signal to skip this field
            # Feature-66B-005: also accept native openFDA integer 1 or string "1" as "Yes"
            if value in ("Yes", 1, "1"):
                return None, "1"
            # If not Yes/No/1, error
            return (
                f"Invalid value '{value}' for '{param_name}'. Allowed values: ['Yes'] (omit to include all).",
                None,
            )

        if param_name in HUMAN_TO_FDA_MAP:
            value_map = HUMAN_TO_FDA_MAP[param_name]
            if value not in value_map:
                print("No mapping found for value:", value, "skipping")
                allowed_values = list(value_map.keys())
                return (
                    f"Invalid value '{value}' for '{param_name}'. Allowed values: {allowed_values}",
                    None,
                )
            return None, value_map[value]
        return None, value


@register_tool("FDACountAdditiveReactionsTool")
class FDACountAdditiveReactionsTool(FDADrugAdverseEventTool):
    """
    Leverage openFDA API to count adverse reaction events across multiple drugs in one request.
    """

    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)

    def run(self, arguments):
        # Make a copy to avoid modifying the original
        arguments = copy.deepcopy(arguments)

        # Validate medicinalproducts list first
        drugs = arguments.pop("medicinalproducts", [])
        if not drugs:
            return {"status": "error", "error": "`medicinalproducts` list is required."}
        if not isinstance(drugs, list):
            return {
                "status": "error",
                "error": "`medicinalproducts` must be a list of drug names.",
            }

        # Validate the remaining enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return {"status": "error", "error": validation_error}

        # Build OR clause for multiple drugs
        escaped = []
        for d in drugs:
            val = urllib.parse.quote(d, safe="")
            escaped.append(f"patient.drug.medicinalproduct:{val}")
        or_clause = "+OR+".join(escaped)

        # Combine additional filters
        filters = []
        for k, v in arguments.items():
            # Get FDA field name(s) from search_fields mapping
            fda_fields = self.search_fields.get(k, [k])
            # Use the first field name for value mapping
            fda_field = fda_fields[0] if fda_fields else k

            # Map value using FDA field name (for proper enum mapping)
            mapping_error, mapped = self._map_value(fda_field, v)
            if mapping_error:
                return {"status": "error", "error": mapping_error}
            if mapped is None:
                continue  # Skip this field if instructed

            # Use FDA field name(s) in the query
            for fda_field_name in fda_fields:
                if isinstance(mapped, str) and " " in mapped:
                    filters.append(f'{fda_field_name}:"{mapped}"')
                else:
                    filters.append(f"{fda_field_name}:{mapped}")

        filter_str = "+AND+".join(filters) if filters else ""
        search_query = f"({or_clause})" + (f"+AND+{filter_str}" if filter_str else "")
        # URL encode the search query, preserving +, :, and " as safe chars
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Call API
        if self.api_key:
            url = (
                f"{self.endpoint_url}?api_key={self.api_key}"
                f"&search={search_encoded}&count={self.count_field}"
            )
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&count={self.count_field}"
            )

        try:
            resp = requests.get(url)
            # Handle 404 as "no matches found" - return empty list instead of error
            if resp.status_code == 404:
                try:
                    error_data = resp.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return []  # Return empty list for no matches
                except (ValueError, KeyError):
                    pass
            resp.raise_for_status()
            results = resp.json().get("results", [])
            results = self._post_process(results)
            return results
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}


@register_tool("FDADrugAdverseEventDetailTool")
class FDADrugAdverseEventDetailTool(BaseTool):
    """
    Tool for retrieving detailed adverse event reports from FAERS.
    Uses limit/skip parameters instead of count aggregation.
    """

    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)
        self.tool_config = tool_config
        self.endpoint_url = endpoint_url
        self.api_key = api_key or os.getenv("FDA_API_KEY")
        self.search_fields = tool_config.get("fields", {}).get("search_fields", {})
        self.return_fields = tool_config.get("fields", {}).get("return_fields", [])

        # Store allowed enum values
        self.parameter_enums = {}
        if "parameter" in tool_config and "properties" in tool_config["parameter"]:
            for param_name, param_def in tool_config["parameter"]["properties"].items():
                if "enum" in param_def:
                    self.parameter_enums[param_name] = param_def["enum"]

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        # Validate enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return [{"error": validation_error}]

        response = self._search(arguments)
        return response

    def validate_enum_arguments(self, arguments):
        """Validate that enum-based arguments match the allowed values"""
        for param_name, value in arguments.items():
            if param_name in self.parameter_enums and value is not None:
                allowed_values = self.parameter_enums[param_name]
                if value not in allowed_values:
                    return f"Invalid value '{value}' for parameter '{param_name}'. Allowed values are: {', '.join(allowed_values)}"
        return None

    def _search(self, arguments):
        # Extract limit and skip from arguments
        limit = arguments.pop("limit", 10)
        skip = arguments.pop("skip", 0)

        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return [{"error": "limit must be an integer between 1 and 100"}]
        if not isinstance(skip, int) or skip < 0:
            return [{"error": "skip must be a non-negative integer"}]

        # Build search query
        search_parts = []
        for param_name, value in arguments.items():
            fda_fields = self.search_fields.get(
                param_name, [param_name]
            )  # Map param -> FDA field
            # Use the first field name for value mapping
            fda_field = fda_fields[0] if fda_fields else param_name

            # Apply value mapping using FDA field name
            # (for proper enum mapping)
            mapping_error, mapped_value = self._map_value(fda_field, value)
            if mapping_error:
                return [{"error": mapping_error}]
            if mapped_value is None:
                continue  # Skip this field if instructed

            # Build search parts using FDA field name(s)
            # If multiple fields for same param, use OR logic within the param
            if len(fda_fields) > 1:
                # Multiple fields for same parameter - use OR
                field_parts = []
                for fda_field_name in fda_fields:
                    if isinstance(mapped_value, str) and " " in mapped_value:
                        field_parts.append(f'{fda_field_name}:"{mapped_value}"')
                    else:
                        field_parts.append(f"{fda_field_name}:{mapped_value}")
                # Join multiple fields with OR
                search_parts.append("+OR+".join(field_parts))
            else:
                # Single field - normal behavior
                fda_field_name = fda_fields[0]
                if isinstance(mapped_value, str) and " " in mapped_value:
                    search_parts.append(f'{fda_field_name}:"{mapped_value}"')
                else:
                    search_parts.append(f"{fda_field_name}:{mapped_value}")

        # Final search query - join different parameters with AND
        search_query = "+AND+".join(search_parts)
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Build URL with limit and skip (not count)
        if self.api_key:
            url = (
                f"{self.endpoint_url}?api_key={self.api_key}"
                f"&search={search_encoded}&limit={limit}&skip={skip}"
            )
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&limit={limit}&skip={skip}"
            )

        # API request
        try:
            response = requests.get(url)
            # Handle 404 as "no matches found" - return empty list instead of error
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return []  # Return empty list for no matches
                except (ValueError, KeyError):
                    pass
            response.raise_for_status()
            response_data = response.json()
            results = response_data.get("results", [])

            # If return_fields is specified, filter the results
            if self.return_fields:
                filtered_results = []
                for result in results:
                    filtered_result = {}
                    for field in self.return_fields:
                        # Handle nested fields (e.g., "patient.reaction.reactionmeddrapt")
                        field_parts = field.split(".")
                        value = result
                        for part in field_parts:
                            if isinstance(value, dict):
                                value = value.get(part)
                            elif isinstance(value, list) and part.isdigit():
                                value = (
                                    value[int(part)] if int(part) < len(value) else None
                                )
                            else:
                                value = None
                                break
                        if value is not None:
                            filtered_result[field] = value
                    if filtered_result:
                        filtered_results.append(filtered_result)
                return filtered_results

            # Extract essential fields if configured
            extract_essential = self.tool_config.get("fields", {}).get(
                "extract_essential", False
            )
            if extract_essential:
                results = [self._extract_essential_fields(r) for r in results]

            return results
        except requests.exceptions.RequestException as e:
            return [{"error": f"API request failed: {str(e)}"}]

    def _extract_essential_fields(self, report):
        """
        Extract only essential fields from a FAERS report.
        Removes verbose metadata like openfda to keep output concise.
        Can be customized via tool_config['fields']['essential_fields'].
        """
        # Get custom essential fields from config, or use default
        essential_fields_config = self.tool_config.get("fields", {}).get(
            "essential_fields", None
        )

        if essential_fields_config:
            # Use custom field extraction logic from config
            return self._extract_custom_fields(report, essential_fields_config)

        # Default essential fields extraction
        essential = {
            # Report identification
            "safetyreportid": report.get("safetyreportid"),
            "safetyreportversion": report.get("safetyreportversion"),
            # Seriousness indicators
            "serious": report.get("serious"),
            "seriousnessdeath": report.get("seriousnessdeath"),
            "seriousnesshospitalization": report.get("seriousnesshospitalization"),
            "seriousnesslifethreatening": report.get("seriousnesslifethreatening"),
            "seriousnessdisabling": report.get("seriousnessdisabling"),
            # Location
            "occurcountry": report.get("occurcountry"),
            "primarysourcecountry": report.get("primarysourcecountry"),
            # Dates
            "transmissiondate": report.get("transmissiondate"),
            "receivedate": report.get("receivedate"),
        }

        # Patient information (essential fields only)
        patient = report.get("patient", {})
        if patient:
            essential_patient = {
                "patientsex": patient.get("patientsex"),
                "patientagegroup": patient.get("patientagegroup"),
                "patientonsetage": patient.get("patientonsetage"),
                "patientonsetageunit": patient.get("patientonsetageunit"),
                "patientweight": patient.get("patientweight"),
            }

            # Drugs (essential fields only, no openfda metadata)
            drugs = patient.get("drug", [])
            if drugs:
                essential_drugs = []
                for drug in drugs:
                    essential_drug = {
                        "medicinalproduct": drug.get("medicinalproduct"),
                        "drugindication": drug.get("drugindication"),
                        "drugadministrationroute": drug.get("drugadministrationroute"),
                        "drugdosagetext": drug.get("drugdosagetext"),
                        "drugdosageform": drug.get("drugdosageform"),
                        "drugstartdate": drug.get("drugstartdate"),
                        "actiondrug": drug.get("actiondrug"),
                    }
                    # Only include non-empty fields
                    essential_drug = {
                        k: v for k, v in essential_drug.items() if v is not None
                    }
                    if essential_drug:
                        essential_drugs.append(essential_drug)
                if essential_drugs:
                    essential_patient["drug"] = essential_drugs

            # Reactions (all fields are essential)
            reactions = patient.get("reaction", [])
            if reactions:
                essential_reactions = []
                for reaction in reactions:
                    essential_reaction = {
                        "reactionmeddrapt": reaction.get("reactionmeddrapt"),
                        "reactionmeddraversionpt": reaction.get(
                            "reactionmeddraversionpt"
                        ),
                        "reactionoutcome": reaction.get("reactionoutcome"),
                    }
                    # Only include non-empty fields
                    essential_reaction = {
                        k: v for k, v in essential_reaction.items() if v is not None
                    }
                    if essential_reaction:
                        essential_reactions.append(essential_reaction)
                if essential_reactions:
                    essential_patient["reaction"] = essential_reactions

            # Summary if available
            if "summary" in patient:
                essential_patient["summary"] = patient["summary"]

            essential["patient"] = essential_patient

        # Remove None values
        essential = {k: v for k, v in essential.items() if v is not None}
        return essential

    def _extract_custom_fields(self, report, field_config):
        """
        Extract fields based on custom configuration.
        field_config can be a list of field paths or a dict with inclusion rules.
        """
        if isinstance(field_config, list):
            # Simple list of field paths to include
            result = {}
            for field_path in field_config:
                value = self._get_nested_value(report, field_path)
                if value is not None:
                    self._set_nested_value(result, field_path, value)
            return result
        else:
            # Use default extraction
            return self._extract_essential_fields(report)

    def _get_nested_value(self, obj, path):
        """Get value from nested dict using dot notation path"""
        parts = path.split(".")
        value = obj
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)] if int(part) < len(value) else None
            else:
                return None
            if value is None:
                return None
        return value

    def _set_nested_value(self, obj, path, value):
        """Set value in nested dict using dot notation path"""
        parts = path.split(".")
        current = obj
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _map_value(self, param_name, value):
        # Special handling for seriousness fields: if value is "No", skip this field
        seriousness_fields = {
            "seriousnessdeath",
            "seriousnesshospitalization",
            "seriousnessdisabling",
            "seriousnesslifethreatening",
            "seriousnessother",
        }
        if param_name in seriousness_fields:
            if value == "No":
                return None, None  # Signal to skip this field
            # Feature-66B-005: also accept native openFDA integer 1 or string "1" as "Yes"
            if value in ("Yes", 1, "1"):
                return None, "1"
            # If not Yes/No/1, error
            return (
                f"Invalid value '{value}' for '{param_name}'. Allowed values: ['Yes'] (omit to include all).",
                None,
            )

        if param_name in HUMAN_TO_FDA_MAP:
            value_map = HUMAN_TO_FDA_MAP[param_name]
            if value not in value_map:
                print("No mapping found for value:", value, "skipping")
                allowed_values = list(value_map.keys())
                return (
                    f"Invalid value '{value}' for '{param_name}'. Allowed values: {allowed_values}",
                    None,
                )
            return None, value_map[value]
        return None, value


@register_tool("FDADrugInteractionDetailTool")
class FDADrugInteractionDetailTool(BaseTool):
    """
    Tool for retrieving detailed adverse event reports involving multiple drugs (drug interactions).
    Uses limit/skip parameters instead of count aggregation.
    """

    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)
        self.tool_config = tool_config
        self.endpoint_url = endpoint_url
        self.api_key = api_key or os.getenv("FDA_API_KEY")
        self.search_fields = tool_config.get("fields", {}).get("search_fields", {})
        self.return_fields = tool_config.get("fields", {}).get("return_fields", [])

        # Store allowed enum values
        self.parameter_enums = {}
        if "parameter" in tool_config and "properties" in tool_config["parameter"]:
            for param_name, param_def in tool_config["parameter"]["properties"].items():
                if "enum" in param_def:
                    self.parameter_enums[param_name] = param_def["enum"]

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        # Validate enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return [{"error": validation_error}]

        response = self._search(arguments)
        return response

    def validate_enum_arguments(self, arguments):
        """Validate that enum-based arguments match the allowed values"""
        for param_name, value in arguments.items():
            if param_name in self.parameter_enums and value is not None:
                allowed_values = self.parameter_enums[param_name]
                if value not in allowed_values:
                    return f"Invalid value '{value}' for parameter '{param_name}'. Allowed values are: {', '.join(allowed_values)}"
        return None

    def _search(self, arguments):
        # Extract limit and skip from arguments
        limit = arguments.pop("limit", 10)
        skip = arguments.pop("skip", 0)

        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return [{"error": "limit must be an integer between 1 and 100"}]
        if not isinstance(skip, int) or skip < 0:
            return [{"error": "skip must be a non-negative integer"}]

        # Extract medicinalproducts list
        drugs = arguments.pop("medicinalproducts", [])
        if not drugs:
            return [{"error": "medicinalproducts list is required"}]
        if not isinstance(drugs, list) or len(drugs) < 2:
            return [
                {"error": "medicinalproducts must be a list of at least 2 drug names"}
            ]

        # Build AND clause for multiple drugs (all must be present)
        drug_parts = []
        for drug in drugs:
            escaped_drug = urllib.parse.quote(drug, safe="")
            drug_parts.append(f"patient.drug.medicinalproduct:{escaped_drug}")

        # Build additional filters
        filter_parts = []
        for param_name, value in arguments.items():
            fda_fields = self.search_fields.get(
                param_name, [param_name]
            )  # Map param -> FDA field
            # Use the first field name for value mapping
            fda_field = fda_fields[0] if fda_fields else param_name

            # Apply value mapping using FDA field name
            mapping_error, mapped_value = self._map_value(fda_field, value)
            if mapping_error:
                return [{"error": mapping_error}]
            if mapped_value is None:
                continue  # Skip this field if instructed

            # Build filter parts using FDA field name(s)
            for fda_field_name in fda_fields:
                if isinstance(mapped_value, str) and " " in mapped_value:
                    filter_parts.append(f'{fda_field_name}:"{mapped_value}"')
                else:
                    filter_parts.append(f"{fda_field_name}:{mapped_value}")

        # Combine drug parts (AND) with additional filters (AND)
        all_parts = drug_parts + filter_parts
        search_query = "+AND+".join(all_parts)
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Build URL with limit and skip
        if self.api_key:
            url = (
                f"{self.endpoint_url}?api_key={self.api_key}"
                f"&search={search_encoded}&limit={limit}&skip={skip}"
            )
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&limit={limit}&skip={skip}"
            )

        # API request
        try:
            response = requests.get(url)
            # Handle 404 as "no matches found" - return empty list instead of error
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return []  # Return empty list for no matches
                except (ValueError, KeyError):
                    pass
            response.raise_for_status()
            response_data = response.json()
            results = response_data.get("results", [])

            # If return_fields is specified, filter the results
            if self.return_fields:
                filtered_results = []
                for result in results:
                    filtered_result = {}
                    for field in self.return_fields:
                        # Handle nested fields (e.g., "patient.reaction.reactionmeddrapt")
                        field_parts = field.split(".")
                        value = result
                        for part in field_parts:
                            if isinstance(value, dict):
                                value = value.get(part)
                            elif isinstance(value, list) and part.isdigit():
                                value = (
                                    value[int(part)] if int(part) < len(value) else None
                                )
                            else:
                                value = None
                                break
                        if value is not None:
                            filtered_result[field] = value
                    if filtered_result:
                        filtered_results.append(filtered_result)
                return filtered_results

            # Extract essential fields if configured
            extract_essential = self.tool_config.get("fields", {}).get(
                "extract_essential", False
            )
            if extract_essential:
                results = [self._extract_essential_fields(r) for r in results]

            return results
        except requests.exceptions.RequestException as e:
            return [{"error": f"API request failed: {str(e)}"}]

    def _extract_essential_fields(self, report):
        """
        Extract only essential fields from a FAERS report.
        Removes verbose metadata like openfda to keep output concise.
        Can be customized via tool_config['fields']['essential_fields'].
        """
        # Get custom essential fields from config, or use default
        essential_fields_config = self.tool_config.get("fields", {}).get(
            "essential_fields", None
        )

        if essential_fields_config:
            # Use custom field extraction logic from config
            return self._extract_custom_fields(report, essential_fields_config)

        # Default essential fields extraction
        essential = {
            # Report identification
            "safetyreportid": report.get("safetyreportid"),
            "safetyreportversion": report.get("safetyreportversion"),
            # Seriousness indicators
            "serious": report.get("serious"),
            "seriousnessdeath": report.get("seriousnessdeath"),
            "seriousnesshospitalization": report.get("seriousnesshospitalization"),
            "seriousnesslifethreatening": report.get("seriousnesslifethreatening"),
            "seriousnessdisabling": report.get("seriousnessdisabling"),
            # Location
            "occurcountry": report.get("occurcountry"),
            "primarysourcecountry": report.get("primarysourcecountry"),
            # Dates
            "transmissiondate": report.get("transmissiondate"),
            "receivedate": report.get("receivedate"),
        }

        # Patient information (essential fields only)
        patient = report.get("patient", {})
        if patient:
            essential_patient = {
                "patientsex": patient.get("patientsex"),
                "patientagegroup": patient.get("patientagegroup"),
                "patientonsetage": patient.get("patientonsetage"),
                "patientonsetageunit": patient.get("patientonsetageunit"),
                "patientweight": patient.get("patientweight"),
            }

            # Drugs (essential fields only, no openfda metadata)
            drugs = patient.get("drug", [])
            if drugs:
                essential_drugs = []
                for drug in drugs:
                    essential_drug = {
                        "medicinalproduct": drug.get("medicinalproduct"),
                        "drugindication": drug.get("drugindication"),
                        "drugadministrationroute": drug.get("drugadministrationroute"),
                        "drugdosagetext": drug.get("drugdosagetext"),
                        "drugdosageform": drug.get("drugdosageform"),
                        "drugstartdate": drug.get("drugstartdate"),
                        "actiondrug": drug.get("actiondrug"),
                    }
                    # Only include non-empty fields
                    essential_drug = {
                        k: v for k, v in essential_drug.items() if v is not None
                    }
                    if essential_drug:
                        essential_drugs.append(essential_drug)
                if essential_drugs:
                    essential_patient["drug"] = essential_drugs

            # Reactions (all fields are essential)
            reactions = patient.get("reaction", [])
            if reactions:
                essential_reactions = []
                for reaction in reactions:
                    essential_reaction = {
                        "reactionmeddrapt": reaction.get("reactionmeddrapt"),
                        "reactionmeddraversionpt": reaction.get(
                            "reactionmeddraversionpt"
                        ),
                        "reactionoutcome": reaction.get("reactionoutcome"),
                    }
                    # Only include non-empty fields
                    essential_reaction = {
                        k: v for k, v in essential_reaction.items() if v is not None
                    }
                    if essential_reaction:
                        essential_reactions.append(essential_reaction)
                if essential_reactions:
                    essential_patient["reaction"] = essential_reactions

            # Summary if available
            if "summary" in patient:
                essential_patient["summary"] = patient["summary"]

            essential["patient"] = essential_patient

        # Remove None values
        essential = {k: v for k, v in essential.items() if v is not None}
        return essential

    def _extract_custom_fields(self, report, field_config):
        """
        Extract fields based on custom configuration.
        field_config can be a list of field paths or a dict with inclusion rules.
        """
        if isinstance(field_config, list):
            # Simple list of field paths to include
            result = {}
            for field_path in field_config:
                value = self._get_nested_value(report, field_path)
                if value is not None:
                    self._set_nested_value(result, field_path, value)
            return result
        else:
            # Use default extraction
            return self._extract_essential_fields(report)

    def _get_nested_value(self, obj, path):
        """Get value from nested dict using dot notation path"""
        parts = path.split(".")
        value = obj
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)] if int(part) < len(value) else None
            else:
                return None
            if value is None:
                return None
        return value

    def _set_nested_value(self, obj, path, value):
        """Set value in nested dict using dot notation path"""
        parts = path.split(".")
        current = obj
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _map_value(self, param_name, value):
        # Special handling for seriousness fields: if value is "No", skip this field
        seriousness_fields = {
            "seriousnessdeath",
            "seriousnesshospitalization",
            "seriousnessdisabling",
            "seriousnesslifethreatening",
            "seriousnessother",
        }
        if param_name in seriousness_fields:
            if value == "No":
                return None, None  # Signal to skip this field
            # Feature-66B-005: also accept native openFDA integer 1 or string "1" as "Yes"
            if value in ("Yes", 1, "1"):
                return None, "1"
            # If not Yes/No/1, error
            return (
                f"Invalid value '{value}' for '{param_name}'. Allowed values: ['Yes'] (omit to include all).",
                None,
            )

        if param_name in HUMAN_TO_FDA_MAP:
            value_map = HUMAN_TO_FDA_MAP[param_name]
            if value not in value_map:
                print("No mapping found for value:", value, "skipping")
                allowed_values = list(value_map.keys())
                return (
                    f"Invalid value '{value}' for '{param_name}'. Allowed values: {allowed_values}",
                    None,
                )
            return None, value_map[value]
        return None, value
