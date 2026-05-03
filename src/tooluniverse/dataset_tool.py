import pandas as pd
import os
from copy import deepcopy
from .base_tool import BaseTool
from .utils import download_from_hf
from .tool_registry import register_tool


@register_tool("DatasetTool")
class DatasetTool(BaseTool):
    """
    Tool to search and filter the DrugBank vocabulary dataset.
    Provides functionality to search drugs by name, ID, synonyms and filter by various criteria.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.dataset = None
        self.query_schema = tool_config[
            "query_schema"
        ]  # TODO: Move query_schema to BaseTool
        self.parameters = tool_config["parameter"][
            "properties"
        ]  # TODO: Move parameters to BaseTool
        self._load_dataset()

    def _load_dataset(self):
        """Load the drugbank vocabulary CSV dataset."""
        try:
            if "hf_dataset_path" in self.tool_config:
                # Download dataset from Hugging Face Hub
                result = download_from_hf(self.tool_config)

                if not result.get("success", False):
                    print(f"Failed to download dataset: {result.get('error')}")
                    self.dataset = pd.DataFrame()
                    return

                # Load the downloaded CSV
                dataset_path = result["local_path"]

            elif "local_dataset_path" in self.tool_config:
                dataset_path = self.tool_config["local_dataset_path"]

                # If relative path, make it relative to the project root
                if not os.path.isabs(dataset_path):
                    # Go up from src/tooluniverse to project root
                    project_root = os.path.dirname(
                        os.path.dirname(os.path.dirname(__file__))
                    )
                    dataset_path = os.path.join(project_root, dataset_path)

            else:
                print("No dataset path provided in tool configuration")
                self.dataset = pd.DataFrame()
                return

            # Load the CSV file
            if dataset_path.endswith(".csv"):
                self.dataset = pd.read_csv(dataset_path)
            elif dataset_path.endswith(".tsv"):
                self.dataset = pd.read_csv(dataset_path, sep="\t")
            elif dataset_path.endswith(".txt"):
                self.dataset = pd.read_table(dataset_path, sep="\t")
            elif dataset_path.endswith(".xlsx"):
                self.dataset = pd.read_excel(dataset_path)
            elif dataset_path.endswith(".pkl"):
                self.dataset = pd.read_pickle(dataset_path)
            elif dataset_path.endswith(".parquet"):
                self.dataset = pd.read_parquet(dataset_path)

            # Clean column names
            self.dataset.columns = self.dataset.columns.str.strip()

            # Fill NaN values with empty strings for better searching
            self.dataset = self.dataset.fillna("")

            print(f"Loaded dataset with {len(self.dataset)} records")

        except Exception as e:
            print(f"Error loading dataset: {e}")
            self.dataset = pd.DataFrame()

    def run(self, arguments):
        """Main entry point for the tool."""
        if self.dataset is None or self.dataset.empty:
            return {"status": "error", "error": "Dataset not loaded or is empty"}

        query_params = deepcopy(self.query_schema)
        expected_param_names = self.parameters.keys()

        # Prepare API parameters from arguments
        for k in expected_param_names:
            if k in arguments and arguments[k] is not None:
                query_params[k] = arguments[k]

        # Determine operation based on arguments - completely separate functions
        if "field" in query_params:
            # Use dedicated filter function
            return self._drugbank_filter(query_params)
        elif "query" in query_params:
            # Use dedicated search function
            return self._drugbank_search(query_params)
        else:
            return {
                "status": "error",
                "error": "Invalid arguments: must provide either 'query' for search or 'field' for filtering",
            }

    # ==================== SEARCH FUNCTIONALITY ====================

    def _drugbank_search(self, arguments):
        """
        Search drugs by name, ID, synonyms, or other fields using text-based queries.

        This function is dedicated to text-based searching across specified fields.
        It performs substring or exact matching based on user preferences.

        Args:
            arguments (dict): Search parameters including:
                - query (str): Text to search for
                - search_fields (list): Fields to search in
                - case_sensitive (bool): Whether search is case sensitive
                - exact_match (bool): Whether to perform exact matching
                - limit (int): Maximum number of results

        Returns
            dict: Search results with matched records and metadata
        """
        query = arguments.get("query", "")
        search_fields = arguments.get("search_fields")
        case_sensitive = arguments.get("case_sensitive", False)
        exact_match = arguments.get("exact_match", False)
        limit = arguments.get("limit", 50)

        if not query:
            return {
                "status": "error",
                "error": "Query parameter is required for search",
            }

        # Prepare search query
        if not case_sensitive:
            query = query.lower()

        results = []

        for _, row in self.dataset.iterrows():
            match_found = False
            matched_fields = []

            for field in search_fields:
                if field not in self.dataset.columns:
                    continue

                field_value = str(row[field])
                if not case_sensitive:
                    field_value = field_value.lower()

                if exact_match:
                    # For synonyms, check each synonym separately
                    if (
                        field.lower() == "synonyms" and "|" in field_value
                    ):  # TODO: rename correpsonding columns in each dataset to `synonyms` and use `|` to separate keywords
                        synonyms = [s.strip() for s in field_value.split("|")]
                        if query in synonyms:
                            match_found = True
                            matched_fields.append(field)
                    elif query == field_value:
                        match_found = True
                        matched_fields.append(field)
                else:
                    if query in field_value:
                        match_found = True
                        matched_fields.append(field)

            if match_found:
                result_row = row.to_dict()
                # Convert numpy arrays and pandas types to regular Python types for JSON serialization
                for key, value in result_row.items():
                    if hasattr(value, "tolist"):  # numpy array
                        result_row[key] = value.tolist()
                    elif hasattr(value, "item"):  # numpy/pandas scalar
                        # Get the Python native value
                        native_val = value.item()
                        # Keep score/numeric fields as numbers
                        if "score" in key.lower() or "count" in key.lower():
                            result_row[key] = native_val
                        # For ID fields, convert integer-like floats to strings
                        elif (
                            "id" in key.lower()
                            and isinstance(native_val, float)
                            and native_val == int(native_val)
                        ):
                            result_row[key] = str(int(native_val))
                        else:
                            result_row[key] = native_val
                    # Convert regular Python float
                    elif isinstance(value, float) and not isinstance(value, bool):
                        # NaN becomes None to match schema null expectation
                        if value != value:
                            result_row[key] = None
                        # Keep score/numeric fields as numbers
                        elif "score" in key.lower() or "count" in key.lower():
                            result_row[key] = value
                        # For ID fields, convert integer-like floats to strings
                        elif "id" in key.lower() and value == int(value):
                            result_row[key] = str(int(value))
                    # Convert numeric string to number if key contains 'score' or similar numeric fields
                    elif (
                        isinstance(value, str)
                        and "score" in key.lower()
                        and value.replace(".", "", 1).replace("-", "", 1).isdigit()
                    ):
                        # Try to convert numeric strings to numbers for schema validation
                        try:
                            if "." in value:
                                result_row[key] = float(value)
                            else:
                                result_row[key] = int(value) if value else None
                        except (ValueError, TypeError):
                            pass  # Keep as string if conversion fails
                result_row["matched_fields"] = matched_fields
                results.append(result_row)

                if len(results) >= limit:
                    break

        return {
            "query": arguments.get("query"),
            "total_results": len(results),
            "results": results,
            "search_parameters": {
                "search_fields": search_fields,
                "case_sensitive": case_sensitive,
                "exact_match": exact_match,
                "limit": limit,
            },
        }

    # ==================== FILTER FUNCTIONALITY ====================

    def _drugbank_filter(self, arguments):
        """
        Filter drugs based on specific criteria and field-based conditions.

        This function is dedicated to criteria-based filtering using simple field-condition-value parameters.
        It supports filter types like contains, starts_with, ends_with, exact, not_empty.

        Args:
            arguments (dict): Filter parameters including:
                - field (str): Field name to filter on
                - condition (str): Type of condition (contains, starts_with, ends_with, exact, not_empty)
                - value (str): Value to filter by (optional for not_empty condition)
                - limit (int): Maximum number of results

        Returns
            dict: Filtered results with matched records and applied filters
        """
        field = arguments.get("field")
        condition = arguments.get("condition")
        value = arguments.get("value", "")
        limit = arguments.get("limit", 100)

        if not field or not condition:
            return {
                "status": "error",
                "error": "Both 'field' and 'condition' parameters are required for filtering",
            }

        if field not in self.dataset.columns:
            return {
                "status": "error",
                "error": f"Field '{field}' not found in dataset. Available fields: {list(self.dataset.columns)}",
            }

        # Check if value is required for this condition
        if condition != "not_empty" and not value:
            return {
                "status": "error",
                "error": f"'value' parameter is required for condition '{condition}'",
            }

        filtered_data = self.dataset.copy()
        applied_filter = ""

        try:
            if condition == "contains":
                mask = filtered_data[field].str.contains(value, case=False, na=False)
                applied_filter = f"{field} contains '{value}'"

            elif condition == "starts_with":
                mask = filtered_data[field].str.startswith(value, na=False)
                applied_filter = f"{field} starts with '{value}'"

            elif condition == "ends_with":
                mask = filtered_data[field].str.endswith(value, na=False)
                applied_filter = f"{field} ends with '{value}'"

            elif condition == "exact":
                mask = filtered_data[field] == value
                applied_filter = f"{field} equals '{value}'"

            elif condition == "not_empty":
                mask = (filtered_data[field] != "") & (filtered_data[field].notna())
                applied_filter = f"{field} is not empty"

            else:
                return {
                    "status": "error",
                    "error": f"Unknown condition '{condition}'. Supported: contains, starts_with, ends_with, exact, not_empty",
                }

            filtered_data = filtered_data[mask]

        except Exception as e:
            return {"status": "error", "error": f"Error applying filter: {str(e)}"}

        # Apply limit and convert to dict
        results = filtered_data.head(limit).to_dict("records")

        # Convert numpy arrays and pandas types to regular Python types for JSON serialization
        for result_row in results:
            for key, value in result_row.items():
                if hasattr(value, "tolist"):  # numpy array
                    result_row[key] = value.tolist()
                elif hasattr(value, "item"):  # numpy/pandas scalar
                    # Get the Python native value
                    native_val = value.item()
                    # Keep score/numeric fields as numbers
                    if "score" in key.lower() or "count" in key.lower():
                        result_row[key] = native_val
                    # For ID fields, convert integer-like floats to strings
                    elif (
                        "id" in key.lower()
                        and isinstance(native_val, float)
                        and native_val == int(native_val)
                    ):
                        result_row[key] = str(int(native_val))
                    else:
                        result_row[key] = native_val
                # Convert regular Python float
                elif isinstance(value, float) and not isinstance(value, bool):
                    # NaN becomes None to match schema null expectation
                    if value != value:
                        result_row[key] = None
                    # Keep score/numeric fields as numbers
                    elif "score" in key.lower() or "count" in key.lower():
                        result_row[key] = value
                    # For ID fields, convert integer-like floats to strings
                    elif "id" in key.lower() and value == int(value):
                        result_row[key] = str(int(value))
                # Convert numeric string to number if key contains 'score' or similar numeric fields
                elif (
                    isinstance(value, str)
                    and "score" in key.lower()
                    and value.replace(".", "", 1).replace("-", "", 1).isdigit()
                ):
                    # Try to convert numeric strings to numbers for schema validation
                    try:
                        if "." in value:
                            result_row[key] = float(value)
                        else:
                            result_row[key] = int(value) if value else None
                    except (ValueError, TypeError):
                        pass  # Keep as string if conversion fails

        return {
            "total_matches": len(filtered_data),
            "returned_results": len(results),
            "results": results,
            "applied_filter": applied_filter,
            "filter_parameters": {
                "field": field,
                "condition": condition,
                "value": value if condition != "not_empty" else None,
                "limit": limit,
            },
        }

    # ==================== UTILITY FUNCTIONS ====================

    def get_dataset_info(self):
        """Get information about the loaded dataset."""
        if self.dataset is None or self.dataset.empty:
            return {"status": "error", "error": "Dataset not loaded or is empty"}

        return {
            "total_records": len(self.dataset),
            "columns": list(self.dataset.columns),
            "sample_record": (
                self.dataset.iloc[0].to_dict() if len(self.dataset) > 0 else None
            ),
        }
