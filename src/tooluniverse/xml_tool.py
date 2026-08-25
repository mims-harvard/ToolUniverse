# import xml.etree.ElementTree as ET
from lxml import etree as ET
from typing import List, Dict, Any, Optional, Set
from .base_tool import BaseTool
from .utils import download_from_hf
from .tool_registry import register_tool
from .logging_config import get_logger

# Fix-R13B-4: dataset-load status was reported via print(), which writes
# straight to stdout. Any caller piping a tool's raw stdout as JSON (e.g.
# `tu run ... --raw` or a script parsing captured output) got this line
# prepended ahead of the JSON payload and failed to parse it. Routing
# through the logging module keeps it on stderr instead.
logger = get_logger(__name__)


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
        # Values may be a single XPath string, a LIST of XPath strings (tried
        # in order, first non-empty wins -- see _extract_field_value), or a
        # dict describing a nested structure (see _extract_record_data).
        self.field_mappings: Dict[str, Any] = tool_config.get("settings").get(
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

            logger.info(
                "Loaded XML dataset: %d records from root '%s'",
                len(self.records),
                self.xml_root.tag,
            )

        except Exception as e:
            logger.error("Error loading XML dataset: %s", e)
            self.records = []

    def _get_dataset_path(self) -> Optional[str]:
        """Get the path to the XML dataset."""
        if "hf_dataset_path" in self.tool_config["settings"]:
            result = download_from_hf(self.tool_config["settings"])
            if result.get("success"):
                return result["local_path"]
            logger.error("Failed to download dataset: %s", result.get("error"))
            return None

        if "local_dataset_path" in self.tool_config["settings"]:
            return self.tool_config["settings"]["local_dataset_path"]

        logger.warning("No dataset path provided in tool configuration")
        return None

    # Fix-R13B-4: a record's nested list field (e.g. DrugBank's
    # interacting_drugs) has no size bound of its own -- the tool's `limit`
    # parameter only caps how many *top-level matched records* come back,
    # not the length of a list field inside one record. A well-connected
    # drug like azathioprine has ~1286 documented interactions, so a
    # single matched record (limit=5 had no effect, since only 1 record
    # matched "azathioprine") produced an 80k+ token payload with the
    # clinically critical interaction undifferentiated among hundreds of
    # others. Capping nested list fields for display (while still using
    # the untruncated list to build searchable text, so search matching
    # is unaffected) keeps responses usable; the true count is preserved
    # in a sibling `<field>_total_count` key so callers know more exist.
    # Fix-R28B: the cap above bounds payload size, but on its own it produced a
    # silently truncated list -- `interacting_drugs` came back with 25 of
    # labetalol's 1855 interactions, in raw document order, with no flag saying
    # the list was cut and no way to reach entry #71 (nifedipine). An empty or
    # short list then reads as "no such interaction". The cap value is shared by
    # every nested list field of every XMLTool and is deliberately left alone;
    # what is added is (a) unconditional disclosure keys next to the list and
    # (b) the optional `nested_contains` / `nested_offset` arguments below, whose
    # defaults reproduce the previous output byte for byte.
    _NESTED_LIST_DISPLAY_CAP = 25

    def _is_nested_mapping(self, xpath_expr: Any) -> bool:
        """True when a field mapping describes a nested (structured list) field."""
        return isinstance(xpath_expr, dict) and "parent_path" in xpath_expr

    def _extract_nested_list(
        self, record_element: ET.Element, xpath_expr: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Extract the FULL, untruncated structured list for a nested field."""
        parent_xpath = xpath_expr["parent_path"]
        subfields = xpath_expr.get("subfields", {})
        structured_list = []
        for el in record_element.findall(parent_xpath, namespaces=self.namespaces):
            entry = {}
            for sf_name, sf_path in subfields.items():
                entry[sf_name] = self._extract_field_value(el, sf_path)
            if any(entry.values()):  # Only add entries with non-empty values
                structured_list.append(entry)
        return structured_list

    def _extract_record_data(self, record_element: ET.Element) -> Dict[str, Any]:
        """Extract data from a record element with caching."""
        data = {
            "_tag": record_element.tag,
            "_text": (record_element.text or "").strip(),
            "_attributes": dict(record_element.attrib),
        }

        for field_name, xpath_expr in self.field_mappings.items():
            # Extract mapped fields
            if self._is_nested_mapping(xpath_expr):
                # Handle nested structure
                subfields = xpath_expr.get("subfields", {})
                structured_list = self._extract_nested_list(record_element, xpath_expr)

                # Flatten for search using the full, untruncated list so
                # matching behavior doesn't change based on the display cap.
                for sf_name, _ in subfields.items():
                    flat_key = f"{field_name}_{sf_name}"

                    # For efficient search, flatten structured data into a single string
                    data[flat_key] = " | ".join(
                        entry.get(sf_name, "") for entry in structured_list
                    )

                    self.temporary_record_fields.add(flat_key)

                total_count = len(structured_list)
                max_items = xpath_expr.get("max_items", self._NESTED_LIST_DISPLAY_CAP)
                truncated = bool(max_items) and total_count > max_items
                if truncated:
                    structured_list = structured_list[:max_items]
                data[field_name] = structured_list
                # Disclosure keys sit next to every nested list so a caller can
                # always tell a complete list from a truncated window.
                data[f"{field_name}_total_count"] = total_count
                data[f"{field_name}_shown_count"] = len(structured_list)
                data[f"{field_name}_offset"] = 0
                data[f"{field_name}_truncated"] = truncated
            else:
                # Regular flat field extraction
                data[field_name] = self._extract_field_value(record_element, xpath_expr)

        return data

    def _nested_view_args(self, arguments: Dict[str, Any]) -> tuple:
        """Parse the optional nested-list view arguments.

        Returns ``(contains, offset)``. ``(None, 0)`` -- the default -- means
        "behave exactly as before": first page of every nested list, unfiltered.
        """
        contains = arguments.get("nested_contains")
        if isinstance(contains, str):
            contains = contains.strip() or None
        else:
            contains = None

        offset = arguments.get("nested_offset", 0)
        try:
            offset = max(0, int(offset))
        except (TypeError, ValueError):
            offset = 0

        return contains, offset

    def _apply_nested_view(
        self,
        result_record: Dict[str, Any],
        record_element: ET.Element,
        contains: Optional[str],
        offset: int,
    ) -> None:
        """Re-window every nested list field of one result record, in place.

        Only called when the caller actually supplied `nested_contains` or
        `nested_offset`; otherwise the cached first-page view is returned
        untouched, so the default response is unchanged.
        """
        needle = contains.lower() if contains else None

        for field_name, xpath_expr in self.field_mappings.items():
            if not self._is_nested_mapping(xpath_expr):
                continue

            full_list = self._extract_nested_list(record_element, xpath_expr)
            total_count = len(full_list)

            if needle:
                selected = [
                    entry
                    for entry in full_list
                    if any(needle in str(v).lower() for v in entry.values())
                ]
            else:
                selected = full_list

            window = selected[offset:]
            max_items = xpath_expr.get("max_items", self._NESTED_LIST_DISPLAY_CAP)
            shown = window[:max_items] if max_items else window

            result_record[field_name] = shown
            result_record[f"{field_name}_total_count"] = total_count
            if needle:
                # Only meaningful under a filter; without one it would just
                # duplicate `_total_count`. A 0 here is a searched-and-found-
                # nothing answer, not a truncation artifact.
                result_record[f"{field_name}_matching_count"] = len(selected)
            result_record[f"{field_name}_shown_count"] = len(shown)
            result_record[f"{field_name}_offset"] = offset
            # More entries remain after this window -- raise `nested_offset` to
            # reach them.
            result_record[f"{field_name}_truncated"] = offset + len(shown) < len(
                selected
            )

    def _extract_field_value(self, element: ET.Element, xpath_expr: Any) -> str:
        """Extract field value using XPath expression.

        Fix Round 25: `xpath_expr` may also be a LIST of XPath strings, which
        are tried in order and the first non-empty result returned. Some
        source datasets file the same logical field under different parents
        depending on the record -- DrugBank puts Molecular Formula/Weight
        under <calculated-properties> for small molecules but under
        <experimental-properties> for biotech/peptide entries, so a single
        XPath silently yields "" for one whole class of records. Note that
        ElementTree/lxml's findall() does not accept `|` XPath unions, so a
        list of expressions (rather than one union expression) is the right
        shape here.
        """
        if isinstance(xpath_expr, (list, tuple)):
            for candidate in xpath_expr:
                value = self._extract_field_value(element, candidate)
                if value:
                    return value
            return ""

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
                return " | ".join(dict.fromkeys(values))

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
            # Dedupe while preserving order: fields with many repeated child
            # elements (e.g. DrugBank <products><product><name> repeats the
            # same brand name once per country/dosage-form combination) would
            # otherwise return the same string hundreds of times.
            return " | ".join(dict.fromkeys(non_empty_values))

        except Exception:
            return ""

    def _get_all_records_data(self) -> List[Dict[str, Any]]:
        """Get all records data with caching."""
        if not self._record_cache:
            self._record_cache = [
                self._extract_record_data(record) for record in self.records
            ]
        return self._record_cache

    def _declared_limit_default(self, fallback):
        # _search and _filter each back multiple registered tool names with
        # different declared `limit` defaults (e.g. mesh_* tools default 50,
        # drugbank_*_search-style tools default 10, sharing _search; only
        # drugbank_filter_drugs_by_name uses _filter, default 10 vs the
        # hardcoded 100). Read the per-instance declared default instead of
        # hardcoding one limit for every tool routed through the same
        # handler, or tools with a smaller declared default silently return
        # more rows than documented whenever `limit` is omitted.
        return (
            self.tool_config.get("parameter", {})
            .get("properties", {})
            .get("limit", {})
            .get("default", fallback)
        )

    # Fix Round 17: every _search-mode tool built on this shared class takes
    # a single param named 'query', regardless of what its own tool NAME
    # promises (e.g. drugbank_get_pharmacology_by_drug_name_or_drugbank_id,
    # mesh_get_subjects_by_subject_name). Confirmed live: calling that tool
    # with 'drug_name' (the exact term in its own name) errored with
    # "'query' is a required property" -- a natural first guess from reading
    # the tool name fails. Accept the terms these tool names actually use as
    # synonyms for 'query' instead of renaming the parameter across every
    # config entry (a much larger, more disruptive change).
    _QUERY_ALIASES = ("drug_name", "drugbank_id", "subject_name", "subject_id")

    def _resolve_query_alias(self, arguments: Dict[str, Any]) -> None:
        """Mutate arguments in place, filling in 'query' from a known alias.

        Must run before schema validation (not just inside run()): jsonschema
        rejects a missing required 'query' before run() is ever reached, so an
        alias resolved only in run() would be dead code for every normal
        (validated) call path.
        """
        if "query" in arguments or "condition" in arguments:
            return
        for alias in self._QUERY_ALIASES:
            if arguments.get(alias):
                arguments["query"] = arguments[alias]
                break

    def validate_parameters(self, arguments: Dict[str, Any]) -> Optional[Any]:
        self._resolve_query_alias(arguments)
        return super().validate_parameters(arguments)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for the tool."""
        if not self.records:
            return {
                "status": "error",
                "error": "XML dataset not loaded or contains no records",
            }

        # Also resolve here so direct run() calls that skip validate_parameters
        # (e.g. validate=False, or calling the tool class directly) still work.
        self._resolve_query_alias(arguments)

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
        limit = min(
            arguments.get("limit", self._declared_limit_default(50)), 1000
        )  # Cap at 1000

        search_query = query if case_sensitive else query.lower()

        all_records = self._get_all_records_data()
        # Feature-27B-01: this loop used to truncate to `limit` *while*
        # scanning, so the page handed back was simply "the first N records in
        # the file that matched anything" and match quality never entered into
        # it. Asking DrugBank for "Aspirin" was therefore answered with
        # caffeine's chemistry: DB00201 Caffeine and nine other combination
        # products merely carry the string "Aspirin" inside a brand name, and
        # being earlier in the document they filled the entire page, while the
        # record the caller actually asked for -- DB00945 Acetylsalicylic
        # acid, an exact synonym hit -- was pushed off it. Collect every match
        # first, rank, and only then truncate.
        matched_records = []
        for position, record_data in enumerate(all_records):
            matched_fields = self._find_matches(
                record_data,
                search_query,
                self.search_fields,
                case_sensitive,
                exact_match,
            )

            if matched_fields:
                rank = self._match_rank(
                    record_data, matched_fields, search_query, case_sensitive
                )
                matched_records.append((rank, position, record_data, matched_fields))

        total_matches = len(matched_records)
        # Stable sort on (rank, position) keeps document order as the final
        # tiebreaker among equally-ranked records.
        matched_records.sort(key=lambda item: (item[0], item[1]))

        nested_contains, nested_offset = self._nested_view_args(arguments)
        nested_view_requested = bool(nested_contains) or nested_offset > 0

        results = []
        for _rank, position, record_data, matched_fields in matched_records[:limit]:
            result_record = record_data.copy()
            for temp in self.temporary_record_fields:
                result_record.pop(temp, None)
            if nested_view_requested:
                self._apply_nested_view(
                    result_record,
                    self.records[position],
                    nested_contains,
                    nested_offset,
                )
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
                    "nested_contains": nested_contains,
                    "nested_offset": nested_offset,
                },
            },
        }

    def _match_rank(
        self,
        record_data: Dict[str, Any],
        matched_fields: List[str],
        search_query: str,
        case_sensitive: bool,
    ) -> tuple:
        """Rank key for a matched record -- lower sorts first.

        Feature-27B-01: scored on the *best* field the record matched, as
        ``(exactness_tier, field_index)``:

        * ``exactness_tier`` is 0 when the query equals a whole field value, or
          a whole ``|``-separated item within a multi-valued field (how
          synonyms and brand names are stored), and 1 for a mere substring hit.
        * ``field_index`` is the field's position in the tool's declared
          ``search_fields``, which the configs order by identity strength
          (drug_name, drugbank_id, then synonyms, then brand_names).

        Exactness deliberately outranks field priority: an exact synonym hit is
        a stronger signal that this is the entity the caller named than a
        substring buried in a nominally higher-priority field. Under
        ``exact_match=True`` every hit is already whole-value, so the tier is a
        constant 0 and ranking degenerates to field priority plus document
        order.
        """
        lowest_priority = len(self.search_fields)
        best = (1, lowest_priority)

        for field in matched_fields:
            field_value = self._get_searchable_value(record_data, field, case_sensitive)
            # Reuse the exact-match predicate so "whole value" means exactly
            # what exact_match=True already means for this class.
            exactness_tier = 0 if self._is_match(field_value, search_query, True) else 1
            field_index = (
                self.search_fields.index(field)
                if field in self.search_fields
                else lowest_priority
            )
            candidate = (exactness_tier, field_index)
            if candidate < best:
                best = candidate

        return best

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
        limit = min(
            arguments.get("limit", self._declared_limit_default(100)), 1000
        )  # Cap at 1000

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

        nested_contains, nested_offset = self._nested_view_args(arguments)
        nested_view_requested = bool(nested_contains) or nested_offset > 0

        total_matches = 0
        for position, record_data in enumerate(all_records):
            if field in record_data and filter_func(record_data, field):
                total_matches += 1
                if len(filtered_records) < limit:
                    result_record = record_data.copy()
                    for temp in self.temporary_record_fields:
                        result_record.pop(temp, None)
                    if nested_view_requested:
                        self._apply_nested_view(
                            result_record,
                            self.records[position],
                            nested_contains,
                            nested_offset,
                        )
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
                    "nested_contains": nested_contains,
                    "nested_offset": nested_offset,
                },
            },
        }

    def _get_filter_function(self, condition: str, value: str):
        """Get the appropriate filter function for the condition."""
        filter_functions = {
            "contains": lambda data, field: value.lower() in str(data[field]).lower(),
            "starts_with": lambda data, field: (
                str(data[field]).lower().startswith(value.lower())
            ),
            "ends_with": lambda data, field: (
                str(data[field]).lower().endswith(value.lower())
            ),
            "exact": lambda data, field: str(data[field]).lower() == value.lower(),
            "not_empty": lambda data, field: str(data[field]).strip() != "",
            "has_attribute": lambda data, field: (
                field == "_attributes" and value in data["_attributes"]
            ),
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
