"""LOINC API Tool via NIH Clinical Table Search Service.

API: https://clinicaltables.nlm.nih.gov/api/loinc_items/v3/
"""

import requests
from typing import Any, Dict, List, Sequence
from urllib.parse import urljoin
from .base_tool import BaseTool
from .tool_registry import register_tool

LOINC_BASE_URL = "https://clinicaltables.nlm.nih.gov/api/"


@register_tool("LOINCTool")
class LOINCTool(BaseTool):
    """LOINC tool for lab tests, code details, answer lists, and clinical forms."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = LOINC_BASE_URL
        self.timeout = 30

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """Make a request to the LOINC Clinical Tables API."""
        url = urljoin(self.base_url, endpoint)
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to query LOINC API: {e}",
                "endpoint": endpoint,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error while querying LOINC: {e}",
                "endpoint": endpoint,
            }

    # Fields the loinc_items/v3 index does NOT carry.
    #
    # Fix-R48 established this by probing field-by-field against the live API
    # with `search?terms=2823-3&df=<FIELD>` -- one code, serum potassium. Those
    # fields were being requested anyway and emitted as empty strings, so a
    # rule author choosing a code was shown a blank exactly where the
    # discriminating value belongs, with nothing saying the index simply does
    # not publish it. An unavailable field was presented as a valid empty
    # answer.
    #
    # Fix-R49: one code was not enough, and METHOD_TYP was wrong. Three
    # independent personas hit the same contradiction -- a response that names
    # METHOD_TYP as "returned empty for every code" directly above rows reading
    # METHOD_TYP "PhenX", "ISE", "LC/MS/MS", "Confirm". Re-measured over 570
    # rows drawn from 19 unrelated search terms:
    #
    #   METHOD_TYP        260/570 populated (45.6%)  <- not absent at all
    #   SYSTEM              0/570
    #   SCALE_TYP           0/570
    #   CLASS               0/570
    #   STATUS              0/570
    #   TIME_ASPCT          0/570
    #   COMMON_TEST_RANK    0/570
    #
    # so the other six survive the wider sample and METHOD_TYP is removed. It
    # is a costly field to disclaim: it is what separates a presumptive
    # immunoassay screen from a confirmatory LC/MS/MS quantitation, and the
    # note was telling callers to disregard it.
    #
    # (CLASSTYPE, ORDER_OBS and CONSUMER_NAME are equally empty upstream --
    # 0/570 each -- but this module never requests them, so they are not listed
    # here: the tuple describes fields this tool actually asks for.)
    _FIELDS_ABSENT_FROM_V3_INDEX = (
        "SYSTEM",
        "SCALE_TYP",
        "CLASS",
        "STATUS",
        "TIME_ASPCT",
        "COMMON_TEST_RANK",
    )

    _UNAVAILABLE_FIELDS_NOTE = (
        "The clinicaltables loinc_items/v3 index does not publish these "
        "fields, so they are returned empty for every code and their "
        "emptiness carries no information about this code: {fields}. Use the "
        "full LOINC release or a FHIR terminology server if you need to "
        "select a code on them."
    )

    # Added only when SYSTEM is among the absent fields, since it is the one
    # whose absence changes which code a caller should pick.
    _SPECIMEN_CAVEAT = (
        " SYSTEM (specimen) in particular is unavailable, so this response "
        "cannot distinguish e.g. a serum from a urine measurement."
    )

    @classmethod
    def _unavailable_fields_disclosure(
        cls, fields: List[str], results: Sequence[Dict[str, Any]] = ()
    ) -> Dict[str, Any]:
        """Name the requested fields this index cannot answer, or {} if none.

        Fix-R49: `results` is checked so that the claim cannot contradict the
        rows it is attached to. The static list above is knowledge about the
        index and is what catches a field that is empty in *this* response but
        meaningful in general; the check is the cheap invariant that would have
        caught the METHOD_TYP error at runtime rather than three rounds later,
        and it keeps any future entry honest by construction.
        """
        absent = [
            field
            for field in fields
            if field in cls._FIELDS_ABSENT_FROM_V3_INDEX
            and not any(row.get(field) for row in results)
        ]
        if not absent:
            return {}
        note = cls._UNAVAILABLE_FIELDS_NOTE.format(fields=", ".join(absent))
        if "SYSTEM" in absent:
            note += cls._SPECIMEN_CAVEAT
        return {"fields_unavailable": absent, "fields_unavailable_note": note}

    @staticmethod
    def _is_api_error(api_response: Any) -> bool:
        """Check if an API response is an error dict."""
        return isinstance(api_response, dict) and "error" in api_response

    def _parse_search_results(
        self, api_response: Any, fields: List[str]
    ) -> Dict[str, Any]:
        """Parse the Clinical Tables response: [total_count, codes, extra_info, data]."""
        if not isinstance(api_response, list) or len(api_response) < 4:
            return {
                "status": "error",
                "error": "Invalid API response format",
                "raw_response": api_response,
            }

        total_count = api_response[0]
        # `or []` rather than a length check: the length is already guaranteed
        # above, and this API really does send null in these slots (slot 2 is
        # null on every response that requests no `ef` field). The sibling
        # client for the same service, ClinicalTablesTool._parse, hardens the
        # same way.
        codes = api_response[1] or []
        # `ef` fields arrive in slot 2 as {field: [value_per_row]}, parallel to
        # the row order of slot 1, rather than inline with the `df` row data.
        # Nothing but the requested `ef` fields lands there, so they are read
        # off the response rather than passed in again: naming the field list
        # twice at a call site is a way for `ef` values to vanish silently.
        extra_info = api_response[2] if isinstance(api_response[2], dict) else {}
        data_arrays = api_response[3] or []

        results = []
        for i, code in enumerate(codes):
            result_item = {"code": code}
            if i < len(data_arrays) and data_arrays[i]:
                for field_name, value in zip(fields, data_arrays[i]):
                    result_item[field_name] = value
            for field_name, values in extra_info.items():
                if isinstance(values, list) and i < len(values):
                    result_item[field_name] = values[i]
            results.append(result_item)

        parsed = {
            "total_count": total_count,
            "count": len(results),
            "results": results,
        }
        # Attached here rather than per operation: every operation funnels
        # through this method with the field list it requested, so all four are
        # covered and none can be added later without the disclosure.
        #
        # Fix-R49: only when there are rows. The note describes per-code field
        # emptiness, so on a zero-result response it explains the fields of no
        # codes at all -- noise attached to the one answer that most needs to
        # be read plainly.
        if results:
            parsed.update(self._unavailable_fields_disclosure(fields, results))
        return parsed

    def _search_loinc_items(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search LOINC lab tests and observations by name or keywords."""
        terms = arguments.get("terms", "").strip()
        if not terms:
            return {"status": "error", "error": "terms parameter is required"}

        max_results = min(arguments.get("max_results", 20), 500)
        exclude_copyrighted = arguments.get("exclude_copyrighted", True)

        # Define fields to retrieve
        fields = [
            "LOINC_NUM",
            "LONG_COMMON_NAME",
            "COMPONENT",
            "SYSTEM",
            "SCALE_TYP",
            "METHOD_TYP",
            "CLASS",
        ]

        params = {
            "terms": terms,
            "df": ",".join(fields),  # Display fields
            "maxList": max_results,
        }

        if exclude_copyrighted:
            params["excludeCopyrighted"] = "true"

        api_response = self._make_request("loinc_items/v3/search", params)

        if self._is_api_error(api_response):
            return api_response

        parsed = self._parse_search_results(api_response, fields)
        parsed["search_terms"] = terms

        return parsed

    def _get_code_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a specific LOINC code."""
        loinc_code = arguments.get("loinc_code", "").strip()
        if not loinc_code:
            return {"status": "error", "error": "loinc_code parameter is required"}

        # Get comprehensive fields for details
        fields = [
            "LOINC_NUM",
            "LONG_COMMON_NAME",
            # Fix-R48: this was "SHORT_NAME", which the v3 index does not
            # recognise, so it answered "" for every code in existence. The
            # index spells it SHORTNAME -- verified live, df=SHORT_NAME returns
            # [1,["2823-3"],null,[[""]]] while df=SHORTNAME returns
            # [1,["2823-3"],null,[["Potassium SerPl-sCnc"]]].
            "SHORTNAME",
            "COMPONENT",
            "PROPERTY",
            "TIME_ASPCT",
            "SYSTEM",
            "SCALE_TYP",
            "METHOD_TYP",
            "CLASS",
            "STATUS",
            "COMMON_TEST_RANK",
        ]

        params = {
            "terms": loinc_code,
            "df": ",".join(fields),
            "maxList": 1,
        }

        api_response = self._make_request("loinc_items/v3/search", params)

        if self._is_api_error(api_response):
            return api_response

        parsed = self._parse_search_results(api_response, fields)

        if parsed.get("count", 0) == 0:
            return {
                "status": "error",
                "error": f"No details found for LOINC code: {loinc_code}",
            }

        # Return the first (and should be only) result
        result = parsed["results"][0] if parsed["results"] else {}
        result["loinc_code"] = loinc_code
        result.update(self._unavailable_fields_disclosure(fields))

        return result

    # Fix-R49: this operation used to pass `type: "answer"`, which the API does
    # not implement -- the values it recognises are "question", "form" and
    # "form_and_section" (the documented "panel" is inert; see `_search_forms`).
    # Unrecognised values are silently dropped rather than rejected, so
    # the request degraded into a plain keyword search whose rows were then
    # presented as "answer-type codes". Proven by totals being identical for
    # `type=answer` and for an invented `type=zzzgarbage` on every term tried
    # (PHQ-9 58/58, potassium 145/145, hemoglobin 526/526), and by the index
    # holding no answer codes at all: `terms=LA6568-5` -> [0,[],null,[]].
    # Answer lists are published as an `ef` field instead, which really does
    # carry them: `terms=883-9&ef=AnswerLists` returns answer list LL2419-1
    # with Group A / B / O / AB.
    _ANSWER_LIST_EXTRA_FIELDS = ["AnswerLists", "datatype"]

    _NO_ANSWER_LIST_NOTE = (
        "These LOINC codes were found but none of them publishes an answer "
        "list, so there are no permissible coded values to return. `datatype` "
        "says why: only CNE and CWE codes answer from a list, whereas REAL, "
        "ST, DT, TM and Ratio codes take a free value."
    )

    def _get_answer_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get the permissible answer lists published for a LOINC code."""
        loinc_code = arguments.get("loinc_code", "").strip()
        if not loinc_code:
            return {"status": "error", "error": "loinc_code parameter is required"}

        fields = ["LOINC_NUM", "LONG_COMMON_NAME", "COMPONENT", "SCALE_TYP"]

        params = {
            "terms": loinc_code,
            "df": ",".join(fields),
            "maxList": 20,
            "ef": ",".join(self._ANSWER_LIST_EXTRA_FIELDS),
        }

        api_response = self._make_request("loinc_items/v3/search", params)

        if self._is_api_error(api_response):
            return api_response

        parsed = self._parse_search_results(api_response, fields)

        if parsed.get("count", 0) == 0:
            return {
                "status": "error",
                "error": f"No LOINC code found for: {loinc_code}",
                "loinc_code": loinc_code,
            }

        # Separated from `count` so that "20 codes matched, none of them has an
        # answer list" cannot read as twenty answer lists.
        found = sum(1 for item in parsed["results"] if item.get("AnswerLists"))
        parsed["answer_lists_found"] = found
        if not found:
            parsed["note"] = self._NO_ANSWER_LIST_NOTE

        parsed["query"] = loinc_code
        return parsed

    _NO_FORM_MATCH_NOTE = (
        "No LOINC form or panel matched these terms. This operation searches "
        "whole instruments only, so an individual question or lab test will "
        "not appear here even when its wording matches -- use "
        "LOINC_search_tests for those."
    )

    def _search_forms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search LOINC forms and survey instruments (e.g., PHQ-9, GAD-7)."""
        terms = arguments.get("terms", "").strip()
        if not terms:
            return {"status": "error", "error": "terms parameter is required"}

        max_results = min(arguments.get("max_results", 20), 200)

        fields = ["LOINC_NUM", "LONG_COMMON_NAME", "CLASS", "STATUS"]

        params = {
            "terms": terms,
            "df": ",".join(fields),
            "maxList": max_results,
            # Fix-R49: this used to be `sf: "CLASS"` plus a post-filter keeping
            # rows whose CLASS contained "survey"/"panel"/"form", which made the
            # operation incapable of returning anything. CLASS is not one of the
            # index's searchable fields -- the API documents sf as "text,
            # COMPONENT, CONSUMER_NAME, RELATEDNAMES2, METHOD_TYP, SHORTNAME,
            # LONG_COMMON_NAME, SURVEY_QUEST_TEXT, LOINC_NUM" -- so the query
            # matched nothing (`terms=PHQ-9&sf=CLASS` -> [0,[],null,[]] against
            # 58 hits unfiltered), and CLASS is also empty in this index, so the
            # post-filter would have discarded every row even had the search
            # returned some. Both halves had to hold for the tool to answer, and
            # neither did: every shipped test_example reported count 0 as
            # success. `type` is the documented way to restrict to instruments;
            # "form" is the value that works (`terms=PHQ-9&type=form` -> the 2
            # real PHQ-9 panels). The documented "panel" value is inert upstream
            # -- it returns totals identical to no `type` at all and to an
            # invented value, across every term tried -- so do not reach for it.
            "type": "form",
        }

        api_response = self._make_request("loinc_items/v3/search", params)

        if self._is_api_error(api_response):
            return api_response

        parsed = self._parse_search_results(api_response, fields)

        if parsed.get("count", 0) == 0:
            parsed["note"] = self._NO_FORM_MATCH_NOTE

        parsed["search_terms"] = terms

        return parsed

    _OPERATION_MAP = {
        "search_tests": "_search_loinc_items",
        "get_code_details": "_get_code_details",
        "get_answer_list": "_get_answer_list",
        "search_forms": "_search_forms",
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the LOINC tool based on the operation derived from tool config name."""
        tool_name = self.tool_config.get("name", "")

        for key, method_name in self._OPERATION_MAP.items():
            if key in tool_name:
                return getattr(self, method_name)(arguments)

        return {"status": "error", "error": f"Unknown operation for tool: {tool_name}"}
