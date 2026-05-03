# import xml.etree.ElementTree as ET
from lxml import etree as ET
from typing import List, Dict, Any, Optional, Set
from .base_tool import BaseTool
from .utils import download_from_hf
from .tool_registry import register_tool


@register_tool("XMLTool")
class XMLDatasetTool(BaseTool):
    """
    Tool to search and filter XML datasets that are organized as a collection of searchable records (e.g., dataset of medical subjects or drug descriptions).
    Supports user-friendly queries without requiring XPath knowledge.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.xml_root: Optional[ET.Element] = None
        self.records: List[ET.Element] = []
        self.record_xpath: str = tool_config.get("settings").get("record_xpath", ".//*")
        self.namespaces: Dict[str, str] = tool_config.get("settings").get(
            "namespaces", {}
        )
        self.field_mappings: Dict[str, str] = tool_config.get("settings").get(
            "field_mappings", {}
        )  # Dict of fields we're interested in extracting from each record
        self.filter_field: Optional[str] = tool_config.get("settings").get(
            "filter_field"
        )  # Field to filter on, if specified
        self.search_fields: List[str] = tool_config.get("settings").get(
            "search_fields", ["_text"] + list(self.field_mappings.keys())
        )
        self._record_cache: List[Dict[str, Any]] = []  # Cache extracted data
        self.temporary_record_fields: Set[str] = set()
        self._load_dataset()

    def _load_dataset(self) -> None:
        """Load and parse the XML dataset."""
        try:
            xml_path = self._get_dataset_path()
            if not xml_path:
                return

            tree = ET.parse(xml_path)
            self.xml_root = tree.getroot()
            self.records = self.xml_root.findall(
                self.record_xpath, namespaces=self.namespaces
            )

            print(
                f"Loaded XML dataset: {len(self.records)} records from root '{self.xml_root.tag}'"
            )

        except Exception as e:
            print(f"Error loading XML dataset: {e}")
            self.records = []

    def _get_dataset_path(self) -> Optional[str]:
        """Get the path to the XML dataset."""
        if "hf_dataset_path" in self.tool_config["settings"]:
            result = download_from_hf(self.tool_config["settings"])
            if result.get("success"):
                return result["local_path"]
            print(f"Failed to download dataset: {result.get('error')}")
            return None

        if "local_dataset_path" in self.tool_config["settings"]:
            return self.tool_config["settings"]["local_dataset_path"]

        print("No dataset path provided in tool configuration")
        return None

    def _extract_record_data(self, record_element: ET.Element) -> Dict[str, Any]:
        """Extract data from a record element with caching."""
        data = {
            "_tag": record_element.tag,
            "_text": (record_element.text or "").strip(),
            "_attributes": dict(record_element.attrib),
        }

        for field_name, xpath_expr in self.field_mappings.items():
            # Extract mapped fields
            if isinstance(xpath_expr, dict) and "parent_path" in xpath_expr:
                # Handle nested structure
                parent_xpath = xpath_expr["parent_path"]
                subfields = xpath_expr.get("subfields", {})
                elements = record_element.findall(
                    parent_xpath, namespaces=self.namespaces
                )
                structured_list = []
                for el in elements:
                    entry = {}
                    for sf_name, sf_path in subfields.items():
                        entry[sf_name] = self._extract_field_value(el, sf_path)
                    if any(entry.values()):  # Only add entries with non-empty values
                        structured_list.append(entry)

                data[field_name] = structured_list

                # Flatten for search
                for sf_name, _ in subfields.items():
                    flat_key = f"{field_name}_{sf_name}"

                    # For efficient search, flatten structured data into a single string
                    data[flat_key] = " | ".join(
                        entry.get(sf_name, "") for entry in structured_list
                    )

                    self.temporary_record_fields.add(flat_key)
            else:
                # Regular flat field extraction
                data[field_name] = self._extract_field_value(record_element, xpath_expr)

        return data

    def _extract_field_value(self, element: ET.Element, xpath_expr: str) -> str:
        """Extract field value using XPath expression."""
        try:
            # Handle attribute extraction with /@
            if "/@" in xpath_expr:
                elem_path, attr_name = xpath_expr.rsplit("/@", 1)
                found_elements = element.findall(elem_path, namespaces=self.namespaces)
                if not found_elements:
                    return ""

                # Use generator expression for memory efficiency
                values = (
                    el.get(attr_name, "").strip()
                    for el in found_elements
                    if el.get(attr_name)
                )
                return " | ".join(values)

            # Handle direct attribute on current element
            if xpath_expr.startswith("@"):
                return element.get(xpath_expr[1:], "").strip()

            # Handle text content extraction
            found_elements = element.findall(xpath_expr, namespaces=self.namespaces)
            if not found_elements:
                return ""

            # Use generator expression and filter out empty text
            values = ((elem.text or "").strip() for elem in found_elements)
            non_empty_values = (v for v in values if v)
            return " | ".join(non_empty_values)

        except Exception:
            return ""

    def _get_all_records_data(self) -> List[Dict[str, Any]]:
        """Get all records data with caching."""
        if not self._record_cache:
            self._record_cache = [
                self._extract_record_data(record) for record in self.records
            ]
        return self._record_cache

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for the tool."""
        if not self.records:
            return {
                "status": "error",
                "error": "XML dataset not loaded or contains no records",
            }

        # Route to appropriate function based on arguments
        if "query" in arguments:
            return self._search(arguments)
        elif "condition" in arguments:
            return self._filter(arguments)
        else:
            return {
                "status": "error",
                "error": "Provide either 'query' for search or 'condition' for filtering",
            }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search records by text content across multiple fields."""
        query = arguments.get("query", "").strip()
        if not query:
            return {"status": "error", "error": "Query parameter is required"}

        # Parse search parameters with sensible defaults
        case_sensitive = arguments.get("case_sensitive", False)
        exact_match = arguments.get("exact_match", False)
        limit = min(arguments.get("limit", 50), 1000)  # Cap at 1000

        search_query = query if case_sensitive else query.lower()
        results = []

        all_records = self._get_all_records_data()
        total_matches = 0
        for record_data in all_records:
            matched_fields = self._find_matches(
                record_data,
                search_query,
                self.search_fields,
                case_sensitive,
                exact_match,
            )

            if matched_fields:
                total_matches += 1
                if len(results) < limit:
                    result_record = record_data.copy()
                    for temp in self.temporary_record_fields:
                        result_record.pop(temp, None)
                    result_record["matched_fields"] = matched_fields
                    results.append(result_record)

        return {
            "status": "success",
            "data": {
                "query": query,
                "total_matches": total_matches,
                "total_returned_results": len(results),
                "results": results,
                "search_parameters": {
                    "case_sensitive": case_sensitive,
                    "exact_match": exact_match,
                    "limit": limit,
                },
            },
        }

    def _find_matches(
        self,
        record_data: Dict[str, Any],
        search_query: str,
        search_fields: List[str],
        case_sensitive: bool,
        exact_match: bool,
    ) -> List[str]:
        """Find matching fields in a record."""
        matched_fields = []

        for field in search_fields:
            if field not in record_data:
                continue

            field_value = self._get_searchable_value(record_data, field, case_sensitive)

            if self._is_match(field_value, search_query, exact_match):
                matched_fields.append(field)

        return matched_fields

    def _get_searchable_value(
        self, record_data: Dict[str, Any], field: str, case_sensitive: bool
    ) -> str:
        """Get searchable string value for a field."""
        if field == "_attributes":
            value = " ".join(record_data["_attributes"].values())
        else:
            value = str(record_data.get(field, ""))

        return value if case_sensitive else value.lower()

    def _is_match(self, field_value: str, search_query: str, exact_match: bool) -> bool:
        """Check if field value matches search query."""
        if exact_match:
            if "|" in field_value:  # Handle multiple values
                return search_query in [v.strip() for v in field_value.split("|")]
            return search_query == field_value.strip()

        return search_query in field_value

    def _filter(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Filter records based on field criteria."""
        field = self.filter_field
        condition = arguments.get("condition")
        value = arguments.get("value", "")
        limit = min(arguments.get("limit", 100), 1000)  # Cap at 1000

        if not field or not condition:
            return {
                "status": "error",
                "error": "Both 'field' and 'condition' are required",
            }

        # Validate condition requirements
        if condition not in ["not_empty", "has_attribute"] and not value:
            return {
                "status": "error",
                "error": f"'value' parameter required for condition '{condition}'",
            }

        all_records = self._get_all_records_data()

        # Check if field exists
        if all_records and field not in all_records[0]:
            available_fields = sorted(all_records[0].keys())
            return {
                "status": "error",
                "error": f"Field '{field}' not found. Available: {available_fields}",
            }

        filtered_records = []
        filter_func = self._get_filter_function(condition, value)

        if not filter_func:
            return {
                "status": "error",
                "error": f"Unknown condition '{condition}'. Supported: contains, starts_with, ends_with, exact, not_empty, has_attribute",
            }

        total_matches = 0
        for record_data in all_records:
            if field in record_data and filter_func(record_data, field):
                total_matches += 1
                if len(filtered_records) < limit:
                    result_record = record_data.copy()
                    for temp in self.temporary_record_fields:
                        result_record.pop(temp, None)
                    filtered_records.append(result_record)

        return {
            "status": "success",
            "data": {
                "total_matches": total_matches,
                "total_returned_results": len(filtered_records),
                "results": filtered_records,
                "applied_filter": self._get_filter_description(field, condition, value),
                "filter_parameters": {
                    "field": field,
                    "condition": condition,
                    "value": (
                        value
                        if condition not in ["not_empty", "has_attribute"]
                        else None
                    ),
                    "limit": limit,
                },
            },
        }

    def _get_filter_function(self, condition: str, value: str):
        """Get the appropriate filter function for the condition."""
        filter_functions = {
            "contains": lambda data, field: value.lower() in str(data[field]).lower(),
            "starts_with": lambda data, field: str(data[field])
            .lower()
            .startswith(value.lower()),
            "ends_with": lambda data, field: str(data[field])
            .lower()
            .endswith(value.lower()),
            "exact": lambda data, field: str(data[field]).lower() == value.lower(),
            "not_empty": lambda data, field: str(data[field]).strip() != "",
            "has_attribute": lambda data, field: field == "_attributes"
            and value in data["_attributes"],
        }
        return filter_functions.get(condition)

    def _get_filter_description(self, field: str, condition: str, value: str) -> str:
        """Get human-readable filter description."""
        descriptions = {
            "contains": f"{field} contains '{value}'",
            "starts_with": f"{field} starts with '{value}'",
            "ends_with": f"{field} ends with '{value}'",
            "exact": f"{field} equals '{value}'",
            "not_empty": f"{field} is not empty",
            "has_attribute": f"has attribute '{value}'",
        }
        return descriptions.get(condition, f"{field} {condition} {value}")

    def get_dataset_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the loaded XML dataset."""
        if not self.records:
            return {
                "status": "error",
                "error": "XML dataset not loaded or contains no records",
            }

        # Get field information from sample records
        sample_data = self._get_all_records_data()[:5]
        all_fields = set()
        for record_data in sample_data:
            all_fields.update(record_data.keys())

        info = {
            "total_records": len(self.records),
            "root_element": self.xml_root.tag if self.xml_root else None,
            "record_xpath": self.record_xpath,
            "field_mappings": self.field_mappings,
            "available_fields": sorted(all_fields),
        }

        if sample_data:
            info["sample_record"] = sample_data[0]

        return info
