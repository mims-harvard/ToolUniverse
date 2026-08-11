import copy
import hashlib
import json
import re
from typing import Any, Dict

import requests

from .base_rest_tool import BaseRESTTool
from .base_tool import BaseTool
from .openfda_adv_tool import faers_drug_name_clause
from .tool_registry import register_tool
import os
import urllib.parse

# Cache for GraphQL query to avoid repeated string operations
_OPENTARGETS_DRUG_NAMES_QUERY = None
_OPENTARGETS_ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"

# ===== PLR vs legacy label-section siblings =====
#
# An FDA label carries its safety content under DIFFERENT section names depending
# on the format it was written in:
#
#   * "PLR" (Physician Labeling Rule, 2006-) labels use `warnings_and_cautions`
#     (rendered as "5 WARNINGS AND PRECAUTIONS") and usually have NO `warnings`
#     section at all.
#   * Legacy / OTC-monograph labels use `warnings` (and `precautions`) and
#     usually have NO `warnings_and_cautions` section.
#
# Measured against openFDA drug/label on 2026-08-11 (`search=_exists_:<field>&limit=0`):
#
#   total labels (_exists_:effective_time)            261,639
#   _exists_:warnings                                 208,073
#   _exists_:warnings_and_cautions                     46,925
#   _exists_:boxed_warning                             33,054
#   _exists_:precautions                               47,085
#   warnings AND warnings_and_cautions                  3,439
#   warnings_and_cautions AND NOT warnings             43,486  <-- PLR-only
#   warnings AND NOT warnings_and_cautions            204,634  <-- legacy-only
#   warnings_and_cautions AND NOT warnings
#                          AND NOT boxed_warning       25,874
#
# Cross-checked against `dosage_forms_and_strengths`, a section that only exists
# in the PLR format (43,402 labels): 42,055 of those (96.9%) carry
# `warnings_and_cautions` and only 1,447 (3.3%) carry `warnings`; conversely, of
# the 218,237 non-PLR labels, 206,626 carry `warnings` and only 4,870 carry
# `warnings_and_cautions`. The split is the label format, not the drug.
#
# Consequence for a tool that queries exactly one of these names: for every label
# of the other vintage it returns `<section>: None` and reports `status: success`.
# Read literally that says "this drug has no warnings". Live example --
# GIAPREZA (angiotensin II), a vasopressor whose defining safety issue is
# thrombosis, has `warnings: None` and `boxed_warning: None` but a populated
# `warnings_and_cautions` reading "5. WARNINGS AND PRECAUTIONS There is a
# potential for venous and arterial thrombotic and thromboembolic events in
# patients who receive GIAPREZA. Use concurrent venous thromboembolism (VTE)
# prophylaxis. ... (13% vs. 5%) ...".
#
# The maps below let `search_openfda` notice that situation and say so, instead
# of returning a structurally-null answer that reads as an all-clear. They are
# used for annotation only -- the requested section keys are always left exactly
# as openFDA reported them (usually `None`), and sibling content is added under
# the sibling's OWN name so provenance is never misrepresented.
#
# NOTE: `warnings_and_precautions` is deliberately absent -- it is the human
# heading text, not an openFDA field. It does not appear in openFDA's searchable
# field list for drug/label and `search=_exists_:warnings_and_precautions`
# returns NOT_FOUND.
LABEL_SECTION_SIBLINGS = {
    "warnings": [
        "warnings_and_cautions",
        "boxed_warning",
        "precautions",
        "general_precautions",
    ],
    "warnings_and_cautions": [
        "warnings",
        "boxed_warning",
        "precautions",
        "general_precautions",
    ],
    "boxed_warning": ["warnings_and_cautions", "warnings"],
    "precautions": ["warnings_and_cautions", "warnings", "general_precautions"],
    "general_precautions": ["precautions", "warnings_and_cautions", "warnings"],
    "adverse_reactions": ["warnings_and_cautions", "warnings", "boxed_warning"],
    "contraindications": ["warnings_and_cautions", "warnings"],
    "drug_interactions": ["warnings_and_cautions", "warnings", "precautions"],
    "other_safety_information": ["warnings_and_cautions", "warnings"],
    "user_safety_warnings": ["warnings", "warnings_and_cautions"],
}

# Which ToolUniverse tool returns each label section, so the note can name a
# concrete next call instead of an openFDA field name the caller cannot use.
LABEL_SECTION_TOOLS = {
    "warnings": "FDA_get_warnings_by_drug_name",
    "warnings_and_cautions": "FDA_get_warnings_and_cautions_by_drug_name",
    "boxed_warning": "FDA_get_boxed_warning_info_by_drug_name",
    "precautions": "FDA_get_precautions_by_drug_name",
    "general_precautions": "FDA_get_general_precautions_by_drug_name",
    "adverse_reactions": "FDA_get_adverse_reactions_by_drug_name",
    "contraindications": "FDA_get_contraindications_by_drug_name",
    "drug_interactions": "FDA_get_drug_interactions_by_drug_name",
    "other_safety_information": "FDA_get_other_safety_info_by_drug_name",
    "user_safety_warnings": "FDA_get_user_safety_warning_by_drug_names",
}


def _get_drug_names_query():
    """Get the GraphQL query for drug names (cached)"""
    global _OPENTARGETS_DRUG_NAMES_QUERY
    if _OPENTARGETS_DRUG_NAMES_QUERY is None:
        _OPENTARGETS_DRUG_NAMES_QUERY = (
            "\n      query drugNames($chemblId: String!) {\n        "
            "drug(chemblId: $chemblId) {\n          id\n          name\n          "  # noqa: E501
            "tradeNames\n          synonyms\n        }\n      }\n    "
        )
    return _OPENTARGETS_DRUG_NAMES_QUERY


def _execute_opentargets_query(chembl_id):
    """Directly execute OpenTargets GraphQL query (most efficient)"""
    try:
        from tooluniverse.graphql_tool import execute_query

        query = _get_drug_names_query()
        variables = {"chemblId": chembl_id}
        return execute_query(
            endpoint_url=_OPENTARGETS_ENDPOINT, query=query, variables=variables
        )
    except ImportError:
        # Fallback if graphql_tool not available
        import requests

        query = _get_drug_names_query()
        variables = {"chemblId": chembl_id}
        response = requests.post(
            _OPENTARGETS_ENDPOINT, json={"query": query, "variables": variables}
        )
        try:
            result = response.json()
            if "errors" in result:
                return None
            return result
        except Exception:
            return None


def check_keys_present(api_capabilities_dict, keys):
    for key in keys:
        levels = key.split(".")
        current_dict = api_capabilities_dict
        key_present = True
        for level in levels:
            if level not in current_dict:
                print(f"Key '{level}' not found in dictionary.")
                key_present = False
                break
            if "properties" in current_dict[level]:
                current_dict = current_dict[level]["properties"]
            else:
                current_dict = current_dict[level]
    return key_present


def extract_nested_fields(
    records, fields, keywords=None, identity_fields=None, sibling_sections=None
):
    """
    Recursively extracts nested fields from a list of dictionaries.

    :param records: List of dictionaries from which to extract fields
    :param fields: List of nested fields to extract, each specified with dot notation (e.g., 'openfda.brand_name')
    :param keywords: Optional keyword list used to trim long sections down to
        matching sentences.
    :param identity_fields: Optional extra fields copied verbatim (never keyword
        trimmed) onto every kept record. They exist so a caller can identify the
        product when the ``openfda`` block is empty. They deliberately do NOT
        take part in the "did we extract anything at all?" test below, so adding
        one can never resurrect a record that would otherwise have been dropped.
    :param sibling_sections: Optional ``{requested_section: [sibling, ...]}`` map
        (see ``LABEL_SECTION_SIBLINGS``). When every requested section listed in
        the map came back empty for a record but the raw label carries one of the
        siblings, the sibling is copied onto the record under its OWN key and its
        name is listed in ``related_sections_present``. This is what stops a
        PLR-format label from being reported as ``warnings: None`` with nothing
        else said. Like ``identity_fields`` it runs AFTER the keep test, so it
        can never resurrect a record that would otherwise have been dropped, and
        it never overwrites a key that extraction already populated.

    :return: List of dictionaries containing only the specified fields
    """
    extracted_records = []
    for record in records:
        extracted_record = {}
        for field in fields:
            keys = field.split(".")
            # print("keys", keys)
            value = record
            try:
                for key in keys:
                    value = value[key]
                if key != "openfda" and key != "generic_name" and key != "brand_name":
                    if len(keywords) > 0:
                        # print("key words:", keywords)
                        # print(value)
                        # print(type(value))
                        value = extract_sentences_with_keywords(value, keywords)
                extracted_record[field] = value
            except KeyError:
                extracted_record[field] = None
        keep = any(extracted_record.values())
        for field in identity_fields or []:
            if field in extracted_record:
                continue
            value = record
            try:
                for key in field.split("."):
                    value = value[key]
                extracted_record[field] = value
            except (KeyError, TypeError):
                extracted_record[field] = None
        if sibling_sections and isinstance(record, dict):
            requested = [f for f in fields if f in sibling_sections]
            if requested and not any(extracted_record.get(f) for f in requested):
                present = []
                for f in requested:
                    for sib in sibling_sections[f]:
                        if sib in requested or sib in present:
                            continue
                        if sib in extracted_record:
                            continue
                        value = record.get(sib)
                        # Trim the sibling the same way the requested section
                        # would have been trimmed, so a keyword-filtered tool
                        # does not get an untrimmed wall of text back.
                        if value and keywords:
                            value = extract_sentences_with_keywords(value, keywords)
                        if value:
                            present.append(sib)
                            extracted_record[sib] = value
                if present:
                    extracted_record["related_sections_present"] = present
        if keep:
            extracted_records.append(extracted_record)
    return extracted_records


def map_properties_to_openfda_fields(arguments, search_fields):
    """
    Maps the provided arguments to the corresponding openFDA fields based on the search_fields mapping.

    :param arguments: The input arguments containing property names and values.
    :param search_fields: The mapping of property names to openFDA fields.

    :return: A dictionary with openFDA fields and corresponding values.
    """
    mapped_arguments = {}

    for key, value in list(arguments.items()):
        if key in search_fields:
            # print("key in search_fields:", key)
            openfda_fields = search_fields[key]
            if isinstance(openfda_fields, list):
                # Use tuple key to indicate these fields should be OR'd
                mapped_arguments[tuple(openfda_fields)] = value
            else:
                mapped_arguments[openfda_fields] = value
            del arguments[key]
    arguments["search_fields"] = mapped_arguments
    return arguments


def extract_sentences_with_keywords(text_list, keywords):
    """
    Extracts sentences containing any of the specified keywords from the text.

    Parameters
    - text (str): The input text from which to extract sentences.
    - keywords (list): A list of keywords to search for in the text.

    Returns
    - list: A list of sentences containing any of the keywords.
    """
    sentences_with_keywords = []
    for text in text_list:
        # Compile a regular expression pattern for sentence splitting
        sentence_pattern = re.compile(r"(?<=[.!?]) +")
        # Split the text into sentences
        sentences = sentence_pattern.split(text)
        # Initialize a list to hold sentences with keywords

        # Iterate through each sentence
        for sentence in sentences:
            # Check if any of the keywords are present in the sentence
            if any(keyword.lower() in sentence.lower() for keyword in keywords):
                # If a keyword is found, add the sentence to the list
                sentences_with_keywords.append(sentence)

    return "......".join(sentences_with_keywords)


def search_openfda(
    params=None,
    endpoint_url=None,
    api_key=None,
    sort=None,
    limit=5,
    skip=None,
    count=None,
    exists=None,
    return_fields=None,
    exist_option="OR",
    search_keyword_option="AND",
    keywords_filter=True,
):
    # Return-field fallback mapping:
    # Some label sections are absent in many Rx labels (e.g., `do_not_use`), but
    # the closest equivalent section exists (e.g., `contraindications`). When a
    # tool requests a sparse section and the query yields NOT_FOUND due to
    # `_exists_` filtering, we can retry using the fallback section and map the
    # content back into the originally requested key in the final output.
    #
    # Extend this mapping as needed. Keys are the primary requested field; values
    # are ordered fallback fields to try.
    RETURN_FIELD_FALLBACKS = {
        "do_not_use": ["contraindications"],
        # OTC-style sections that are frequently absent; for Rx labels, the
        # closest equivalents are typically warnings/precautions or contraindications.
        "ask_doctor": ["warnings_and_precautions", "warnings"],
        "ask_doctor_or_pharmacist": [
            "warnings_and_precautions",
            "drug_interactions",
            "warnings",
        ],
        "stop_use": ["warnings_and_precautions", "warnings"],
        "when_using": ["warnings_and_precautions", "warnings"],
        "warnings_and_cautions": ["warnings_and_precautions", "warnings"],
        # Ingredient fields are frequently missing for Rx injectables; fall back
        # to product elements/description so we return best-effort info.
        "inactive_ingredient": ["spl_product_data_elements", "description"],
        "active_ingredient": ["spl_product_data_elements", "description"],
    }
    # Initialize params if not provided
    if params is None:
        params = {}

    if return_fields == "ALL":
        exists = None

    # Initialize search fields and construct search query
    search_fields = params.get("search_fields", {})
    # Keep an immutable copy for extraction/fallback logic later.
    orig_search_fields = copy.deepcopy(search_fields) if search_fields else {}
    search_query = []
    keywords_list = []
    if search_fields:
        for field, value in search_fields.items():
            if isinstance(field, tuple):
                value = value.replace(" and ", " ")
                value = value.replace(" AND ", " ")
                value = " ".join(value.split())
                group_queries = []
                for sub_field in field:
                    val_for_field = value
                    if sub_field == "openfda.generic_name":
                        val_for_field = val_for_field.upper()
                    group_queries.append(f'{sub_field}:"{val_for_field}"')
                search_query.append(f"({'+OR+'.join(group_queries)})")
                continue

            # Merge multiple continuous black spaces into one and use one '+'
            if (
                keywords_filter
                and field != "openfda.brand_name"
                and field != "openfda.generic_name"
            ):
                keywords_list.extend(value.split())
            if field == "openfda.generic_name":
                value = value.upper()  # all generic names are in uppercase
            value = value.replace(" and ", " ")  # remove 'and' in the search query
            value = value.replace(" AND ", " ")  # remove 'AND' in the search query
            # Quote stripping removed to allow manual quotes and support Special chars
            # value = value.replace('"', "")
            # value = value.replace("'", "")
            value = " ".join(value.split())
            if search_keyword_option == "AND":
                # Use quotes to ensure special characters like '-' are treated as part of the string, not operators
                search_query.append(f'{field}:"{value}"')
            elif search_keyword_option == "OR":
                # Fallback for OR (though rare for name fields) - keep original logic or quote?
                # OR usually implies we want any of the terms.
                # If we use quotes, we treat the whole string as one term.
                # Let's keep original OR logic for now or just force quotes?
                # If user asks for OR, they probably lists distinct items.
                search_query.append(f"{field}:({value.replace(' ', '+OR+')})")
            else:
                print("Invalid search_keyword_option. Please use 'AND' or 'OR'.")
        del params["search_fields"]
    if search_query:
        # Join the per-field clauses with an explicit AND. A bare "+" decodes to a
        # space, and openFDA's Lucene parser defaults to OR between clauses, so
        # every multi-field search returned the UNION of its filters: adding a
        # second filter increased the result count and admitted records matching
        # neither the first field nor, necessarily, having that field at all.
        params["search"] = "+AND+".join(search_query)
        params["search"] = "(" + params["search"] + ")"

    def _normalize_indication_terms(text: str) -> list[str]:
        """Normalize indication text into tokens for term-based search fallback."""
        if not isinstance(text, str):
            return []
        t = text.strip().lower()
        if not t:
            return []
        # Basic normalization
        for ch in ["-", "/", ",", ";", "(", ")", "[", "]", "{", "}", "®", "™"]:
            t = t.replace(ch, " ")
        t = " ".join(t.split())

        # Tokenize
        tokens = [x for x in t.split(" ") if x]

        # Drop common stopwords (keep medical abbreviations)
        stop = {
            "in",
            "with",
            "for",
            "of",
            "and",
            "or",
            "to",
            "the",
            "a",
            "an",
            "on",
            "at",
            "by",
            "from",
            "patients",
            "patient",
            "adult",
            "adults",
        }
        tokens = [x for x in tokens if x not in stop]

        # Expand common abbreviations
        expanded: list[str] = []
        for tok in tokens:
            expanded.append(tok)
            if tok == "mds":
                expanded.extend(["myelodysplastic", "myelodysplastic", "syndrome"])
        # De-dupe while preserving order
        seen = set()
        out = []
        for x in expanded:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    # Validate the presence of at least one of search, count, or sort
    if not (
        params.get("search")
        or params.get("count")
        or params.get("sort")
        or search_fields
    ):
        return {
            "status": "error",
            "error": "You must provide at least one of 'search', 'count', or 'sort' parameters.",
        }

    # Set additional query parameters
    params["limit"] = params.get("limit", limit)
    params["sort"] = params.get("sort", sort)
    params["skip"] = params.get("skip", skip)
    params["count"] = params.get("count", count)
    # The `_exists_:<section>` clause appended below, remembered verbatim so the
    # NOT_FOUND path can re-run the very same query with it removed. That probe
    # is what tells "no such drug" apart from "drug is right, section absent" --
    # two situations that are indistinguishable from the NOT_FOUND alone, and
    # which need opposite advice.
    section_exists_clause = ""
    if exists is not None:
        if isinstance(exists, str):
            exists = [exists]
        if "search" in params:
            if exist_option in ("AND", "OR"):
                joiner = f"+{exist_option}+"
                section_exists_clause = (
                    "+AND+("
                    + joiner.join([f"_exists_:{keyword}" for keyword in exists])
                    + ")"
                )
                params["search"] += section_exists_clause
        else:
            if exist_option == "AND":
                params["search"] = "+AND+".join(
                    [f"_exists_:{keyword}" for keyword in exists]
                )
            elif exist_option == "OR":
                params["search"] = "+OR+".join(
                    [f"_exists_:{keyword}" for keyword in exists]
                )
        # Ensure that at least one of the search fields exists (only if we have any).
        flat_fields = []
        for k in search_fields.keys():
            if isinstance(k, tuple):
                flat_fields.extend(k)
            else:
                flat_fields.append(k)
        if flat_fields:
            params["search"] += (
                "+AND+("
                + "+OR+".join([f"_exists_:{field}" for field in flat_fields])
                + ")"
            )
        # params['search']+="+AND+_exists_:openfda"

    # Construct full query with additional parameters
    query = "&".join(
        [
            f"{key}={urllib.parse.quote(str(value), safe='+')}"
            for key, value in params.items()
            if value is not None
        ]
    )

    def _is_valid_api_key(v):
        if v is None:
            return False
        if not isinstance(v, str):
            return True
        vv = v.strip()
        if not vv:
            return False
        # Avoid common placeholder values that users put into env vars.
        placeholders = {
            "none",
            "null",
            "your_fda_key_here",
            "your_key_here",
        }
        if vv.lower() in placeholders:
            return False
        return True

    full_url = f"{endpoint_url}?{query}"
    used_api_key = False
    if _is_valid_api_key(api_key):
        full_url += f"&api_key={api_key}"
        used_api_key = True

    response = requests.get(full_url)

    # Get the JSON response
    response_data = response.json()

    # If an invalid API key was supplied, retry once without it.
    if (
        used_api_key
        and isinstance(response_data, dict)
        and isinstance(response_data.get("error"), dict)
        and response_data["error"].get("code") == "API_KEY_INVALID"
    ):
        response = requests.get(f"{endpoint_url}?{query}")
        response_data = response.json()

    # ===== Generic NOT_FOUND fallback engine (applies to all FDADrugLabel tools) =====
    requested_return_fields = return_fields
    applied_return_field_mapping = {}  # primary_field -> fallback_field
    fallback_terms: list[str] = []
    used_generic_fallback = False
    # Fix-20A-1: `used_generic_fallback` was tracked but never surfaced to the
    # caller. Each fallback stage weakens the match in a different way, and
    # the returned payload looked identical to an exact hit, so a caller had
    # no way to tell "this is the drug you asked for" from "this is the
    # closest thing we could find". Record which stage fired so we can attach
    # an honest note.
    fallback_note: str | None = None

    def _all_search_fields_from_orig() -> list[str]:
        out = []
        for k in (orig_search_fields or {}).keys():
            if isinstance(k, tuple):
                out.extend(list(k))
            else:
                out.append(k)
        return out

    def _first_query_text() -> str:
        for v in (orig_search_fields or {}).values():
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    def _normalize_terms(text: str) -> list[str]:
        if not isinstance(text, str):
            return []
        t = text.strip().lower()
        if not t:
            return []
        for ch in ["-", "/", ",", ";", "(", ")", "[", "]", "{", "}", "®", "™"]:
            t = t.replace(ch, " ")
        t = " ".join(t.split())
        toks = [x for x in t.split(" ") if x]
        # Drop very low-signal tokens (numbers / single letters)
        toks = [x for x in toks if not x.isdigit() and len(x) > 1]
        stop = {
            "in",
            "with",
            "for",
            "of",
            "and",
            "or",
            "to",
            "the",
            "a",
            "an",
            "on",
            "at",
            "by",
            "from",
            "patients",
            "patient",
            "adult",
            "adults",
        }
        toks = [x for x in toks if x not in stop]
        expanded = []
        for tok in toks:
            expanded.append(tok)
        seen = set()
        out = []
        for x in expanded:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    def _filter_exists(ex: object, allowed_fields: set[str]) -> list[str] | None:
        if ex is None:
            return None
        ex_list = ex if isinstance(ex, list) else [ex]
        cleaned = []
        for e in ex_list:
            if not isinstance(e, str):
                continue
            if e.startswith("openfda.") and e not in allowed_fields:
                # don't force openfda existence when we are not querying openfda
                continue
            cleaned.append(e)
        return cleaned

    def _guarded(search_str: str, allowed_fields: set[str]) -> str:
        """Re-apply the caller's `_exists_` guard to a broadened search string.

        Every broadening stage builds its query from a different field set, so
        the guard has to be re-appended per stage rather than centrally. Stage C
        used to skip this step, which made it answer a different question --
        "labels mentioning X" rather than "labels mentioning X that have the
        requested section" -- and report that broader query's hit count as the
        answer. Routing all stages through one function is what stops the next
        stage from forgetting it too.
        """
        ex = _filter_exists(exists, allowed_fields)
        if not ex:
            return search_str
        return search_str + "+AND+(" + "+OR+".join(f"_exists_:{e}" for e in ex) + ")"

    def _run_search(search: str, limit_override: int | None = None) -> dict | None:
        p = {k: v for k, v in params.items() if k != "search"}
        p["search"] = search
        if limit_override is not None:
            p["limit"] = limit_override
        q = "&".join(
            [
                f"{key}={urllib.parse.quote(str(value), safe='+')}"
                for key, value in p.items()
                if value is not None
            ]
        )
        url = f"{endpoint_url}?{q}"
        if _is_valid_api_key(api_key):
            url += f"&api_key={api_key}"
        resp = requests.get(url)
        try:
            return resp.json()
        except Exception:
            return {
                "status": "error",
                "error": {"code": "BAD_JSON", "message": "Non-JSON response"},
            }

    # Only run fallbacks on NOT_FOUND
    if (
        isinstance(response_data, dict)
        and isinstance(response_data.get("error"), dict)
        and response_data["error"].get("code") == "NOT_FOUND"
        and orig_search_fields
    ):
        orig_fields_flat = set(_all_search_fields_from_orig())
        qtext = _first_query_text()
        fallback_terms = _normalize_terms(qtext)
        is_name_based = bool(
            {"openfda.brand_name", "openfda.generic_name"} & orig_fields_flat
        )
        # The broadening stages below exist to tolerate typos and synonyms in a
        # single lookup term: they OR the terms across several fields and use only
        # the FIRST filter's text. Applied to a query that supplied more than one
        # filter, they silently drop the other filters and re-introduce the union
        # semantics this function is meant to avoid -- so a deliberately narrow
        # two-filter query would come back with thousands of non-matching records
        # instead of the correct empty result. With multiple filters, NOT_FOUND is
        # the right answer.
        is_multi_filter = len(orig_search_fields) > 1

        # Return-field fallback mapping (generic):
        # If NOT_FOUND is likely caused by `_exists_:{primary}` for a requested
        # field, retry using `_exists_:{fallback}` and later map extracted content
        # back into `{primary}`.
        if isinstance(requested_return_fields, list) and isinstance(
            params.get("search"), str
        ):
            search_str = params["search"]
            for primary, fallbacks in RETURN_FIELD_FALLBACKS.items():
                if primary not in requested_return_fields:
                    continue
                if f"_exists_:{primary}" not in search_str:
                    continue
                for fb in fallbacks:
                    swapped = search_str.replace(
                        f"_exists_:{primary}", f"_exists_:{fb}"
                    )
                    tmp = _run_search(swapped)
                    if isinstance(tmp, dict) and "error" not in tmp:
                        response_data = tmp
                        requested_return_fields = [fb]
                        applied_return_field_mapping[primary] = fb
                        used_generic_fallback = True
                        fallback_note = (
                            f"Label section '{primary}' was not present for this "
                            f"product; showing content from the related section "
                            f"'{fb}' instead."
                        )
                        break
                if used_generic_fallback:
                    break

        # Sibling-section stage (PLR vs legacy):
        #
        # Runs only if the mapping above did not already rescue the query, so
        # every tool that has a RETURN_FIELD_FALLBACKS entry keeps its exact
        # previous behaviour. It fires when the ONLY thing standing between the
        # caller and their drug is the `_exists_:<section>` guard: the drug is
        # named exactly right, the label exists, but it is written in the other
        # format. Live example -- KEYTRUDA has neither `warnings` nor
        # `boxed_warning`, so `FDA_get_warnings_by_drug_name` returned
        # "No matches found!" for a drug with pages of warnings under
        # `warnings_and_cautions`.
        #
        # Unlike RETURN_FIELD_FALLBACKS this does NOT rewrite the sibling's
        # content into the requested key. `requested_return_fields` is left
        # alone, so the requested sections still come back exactly as openFDA
        # reports them (null) and the sibling arrives under its own name via
        # `extract_nested_fields(sibling_sections=...)`, with `section_note`
        # explaining the split.
        if (
            not used_generic_fallback
            and isinstance(requested_return_fields, list)
            and isinstance(params.get("search"), str)
        ):
            primaries = [
                f for f in requested_return_fields if f in LABEL_SECTION_SIBLINGS
            ]
            if primaries:
                exists_group = (
                    "(" + "+OR+".join(f"_exists_:{p}" for p in primaries) + ")"
                )
                siblings = []
                for p in primaries:
                    for sib in LABEL_SECTION_SIBLINGS[p]:
                        if sib not in primaries and sib not in siblings:
                            siblings.append(sib)
                if siblings and exists_group in params["search"]:
                    sibling_group = (
                        "(" + "+OR+".join(f"_exists_:{s}" for s in siblings) + ")"
                    )
                    tmp = _run_search(
                        params["search"].replace(exists_group, sibling_group)
                    )
                    if isinstance(tmp, dict) and "error" not in tmp:
                        response_data = tmp
                        used_generic_fallback = True

        # Stage A: phrase -> terms within the same search field(s)
        if (
            not used_generic_fallback
            and not is_multi_filter
            and fallback_terms
            and isinstance(response_data, dict)
            and response_data.get("error", {}).get("code") == "NOT_FOUND"
        ):
            # Use explicit boolean AND between terms to avoid very broad matches.
            term_expr = "+AND+".join(fallback_terms)
            per_field = []
            for f in orig_fields_flat:
                per_field.append(f"{f}:({term_expr})")
            # Respect exists only for fields we are actually using in this stage.
            search_a = _guarded(
                "(" + "+OR+".join(per_field) + ")", set(orig_fields_flat)
            )
            tmp = _run_search(
                search_a, limit_override=max(int(params.get("limit") or 0), 25)
            )
            if isinstance(tmp, dict) and "error" not in tmp:
                response_data = tmp
                used_generic_fallback = True
                fallback_note = (
                    f"No exact phrase match for '{qtext}'; results use a "
                    f"broadened, term-based match in the same field(s) "
                    f"({', '.join(sorted(orig_fields_flat))}) -- verify the "
                    f"returned drug name is the one you intended."
                )

        # Stage B: expand to label-text fields (robust when openfda is empty or name mismatched)
        if (
            not is_multi_filter
            and fallback_terms
            and isinstance(response_data, dict)
            and response_data.get("error", {}).get("code") == "NOT_FOUND"
        ):
            term_expr = "+AND+".join(fallback_terms)
            if is_name_based:
                fields_b = [
                    "spl_product_data_elements",
                    "indications_and_usage",
                    "description",
                ]
            else:
                # Generic expansion for non-name tools
                fields_b = list(orig_fields_flat) + ["clinical_studies"]
            per_field = [f"{f}:({term_expr})" for f in fields_b]
            search_b = _guarded("(" + "+OR+".join(per_field) + ")", set(fields_b))
            tmp = _run_search(
                search_b, limit_override=max(int(params.get("limit") or 0), 25)
            )
            if isinstance(tmp, dict) and "error" not in tmp:
                response_data = tmp
                used_generic_fallback = True
                # Fix-20A-1: this stage matches '{qtext}' anywhere in full
                # label-text fields, including ingredient lists -- so a query
                # that is not a product name at all still returns rows. Live
                # example: "magnesium stearate tablet" (an excipient plus a
                # dosage form) returns unrelated products that merely list it,
                # indistinguishable from a real hit. Flag that explicitly,
                # since the field-based fallback above (Stage A) already
                # covers ordinary name/spelling mismatches.
                fallback_note = (
                    f"No product/drug named '{qtext}' matched exactly; "
                    f"results were broadened to full label text (e.g. "
                    f"ingredients, indications, description) and may include "
                    f"unrelated products that merely mention '{qtext}' -- "
                    f"check the returned openfda.brand_name/generic_name "
                    f"before treating this as data about '{qtext}' itself."
                )

        # Stage C: data-driven closest-name candidates (name-based only, single token)
        if (
            is_name_based
            and isinstance(response_data, dict)
            and response_data.get("error", {}).get("code") == "NOT_FOUND"
        ):
            term = qtext.strip().replace('"', " ")
            term = " ".join(term.split())
            if term and (" " not in term):
                try:
                    import difflib
                    from tooluniverse.data.fda_drugs_with_brand_generic_names_for_tool import (
                        drug_list,
                    )

                    def _edit_distance_leq2(a: str, b: str) -> bool:
                        """Fast check for edit distance <= 2 (length-sensitive)."""
                        if a == b:
                            return True
                        la, lb = len(a), len(b)
                        if abs(la - lb) > 2:
                            return False
                        # Simple DP with early exit; strings are short.
                        prev = list(range(lb + 1))
                        for i, ca in enumerate(a, start=1):
                            cur = [i] + [0] * lb
                            row_min = cur[0]
                            for j, cb in enumerate(b, start=1):
                                cost = 0 if ca == cb else 1
                                cur[j] = min(
                                    prev[j] + 1,  # deletion
                                    cur[j - 1] + 1,  # insertion
                                    prev[j - 1] + cost,  # substitution
                                )
                                if cur[j] < row_min:
                                    row_min = cur[j]
                            if row_min > 2:
                                return False
                            prev = cur
                        return prev[lb] <= 2

                    t_upper = term.upper()
                    t0 = t_upper[:1]
                    filtered = []
                    candidate_set = set()
                    for item in drug_list:
                        b = item.get("brand_name")
                        g = item.get("generic_name")
                        for cand in [b, g]:
                            if not isinstance(cand, str) or not cand:
                                continue
                            cu = cand.upper()
                            if cu[:1] != t0:
                                continue
                            if abs(len(cu) - len(t_upper)) > 2:
                                continue
                            candidate_set.add(cu)
                    filtered = list(candidate_set)
                    # Keep cutoff moderate; we use edit-distance <=2 as the
                    # strong guard against wrong-drug matches.
                    matches = difflib.get_close_matches(
                        t_upper, filtered, n=5, cutoff=0.8
                    )
                    if matches:
                        # Guard against wrong-drug matches: only accept very close
                        # candidates by edit distance (<=2).
                        near = [
                            m for m in set(matches) if _edit_distance_leq2(t_upper, m)
                        ]
                        if not near:
                            raise RuntimeError(
                                "No close-enough match after edit-distance filter"
                            )
                        near_sorted = sorted(set(near))
                        per_field = [
                            f'spl_product_data_elements:"{m}"' for m in near_sorted
                        ]
                        # This stage used to skip `_guarded`, which is what made
                        # it answer a broader question than the caller asked and
                        # report that query's hit count as the answer: codeine
                        # came back with meta.total=533 when only 524 labels in
                        # all of openFDA have a `pharmacogenomics` section.
                        search_c = _guarded(
                            "(" + "+OR+".join(per_field) + ")",
                            {"spl_product_data_elements"},
                        )
                        tmp = _run_search(
                            search_c,
                            limit_override=max(int(params.get("limit") or 0), 25),
                        )
                        if isinstance(tmp, dict) and "error" not in tmp:
                            response_data = tmp
                            used_generic_fallback = True
                            # A candidate equal to the input except for case is
                            # not a spelling suggestion -- it is proof the name
                            # was already correct, so saying "no drug named X was
                            # found" sends the reader to fix a spelling that was
                            # never wrong.
                            if t_upper in near_sorted:
                                fallback_note = (
                                    f"'{term}' matched on the product data "
                                    f"elements (ingredient) field rather than on "
                                    f"brand/generic name, so results may include "
                                    f"combination products that merely contain "
                                    f"it -- check openfda.brand_name/"
                                    f"openfda.generic_name on each row."
                                )
                            else:
                                misspelled = [m for m in near_sorted if m != t_upper]
                                fallback_note = (
                                    f"No drug named '{term}' was found; showing "
                                    f"the closest-spelling candidate(s) "
                                    f"({', '.join(misspelled)}) instead -- "
                                    f"verify the returned drug name matches what "
                                    f"you intended."
                                )
                except Exception:
                    pass

    if isinstance(response_data, dict) and "error" in response_data:
        # When no results are found, return a helpful suggestion instead of None.
        err = response_data.get("error") if isinstance(response_data, dict) else None
        code = err.get("code") if isinstance(err, dict) else None
        if code == "NOT_FOUND":
            orig_fields_flat = set(_all_search_fields_from_orig())
            query_text = _first_query_text()
            is_abbrev_like = (
                isinstance(query_text, str)
                and len(query_text.strip()) <= 6
                and any(ch.isdigit() for ch in query_text)
            )
            name_based = bool(
                {"openfda.brand_name", "openfda.generic_name"} & orig_fields_flat
            )
            section = None
            if isinstance(requested_return_fields, list) and requested_return_fields:
                section = requested_return_fields[0]

            # Re-run the caller's own query with the `_exists_:<section>` guard
            # removed. A hit means the drug name was never the problem -- the
            # section simply does not exist on any of its labels -- and spelling
            # advice would send the reader to fix something that is not broken.
            section_hits = 0
            sections_present = []
            if section and section_exists_clause:
                probe = _run_search(
                    params["search"].replace(section_exists_clause, ""),
                    limit_override=5,
                )
                if isinstance(probe, dict) and "error" not in probe:
                    section_hits = (
                        probe.get("meta", {}).get("results", {}).get("total") or 0
                    )
                    for row in probe.get("results") or []:
                        if not isinstance(row, dict):
                            continue
                        for key in LABEL_SECTION_TOOLS:
                            # Truthiness, not key membership: openFDA can report a
                            # section as explicitly null, and pointing the caller
                            # at an empty section would repeat the very mistake
                            # this message exists to correct.
                            if row.get(key) and key not in sections_present:
                                sections_present.append(key)

            suggestion = _build_not_found_suggestion(
                query_text=query_text,
                section=section,
                section_hits=section_hits,
                sections_present=sections_present,
                is_abbrev_like=is_abbrev_like,
                name_based=name_based,
            )
            return {
                "status": "error",
                "error": err,
                "suggestion": suggestion,
                "meta": {
                    "skip": params.get("skip", 0) or 0,
                    "limit": params.get("limit", 0) or 0,
                    "total": 0,
                },
                "results": [],
                "result_count": 0,
                "duplicates_removed": 0,
            }
        return None

    # Extract meta information
    meta_info = response_data.get("meta", {})
    meta_info = meta_info.get("results", {})
    # The NOT_FOUND fallback engine above re-queries with an internal
    # `limit_override` (floored at 25) to get enough candidates to rank/dedupe,
    # then truncates `extracted_results` back down to the caller's requested
    # limit. Without this, `meta.limit` would leak that internal retry value
    # (e.g. 25) even though only the caller's requested number of results
    # (e.g. 1) is actually returned in `results`.
    if meta_info:
        meta_info = dict(meta_info)
        if params.get("limit") is not None:
            meta_info["limit"] = params.get("limit")
        if params.get("skip") is not None:
            meta_info["skip"] = params.get("skip")

    # Extract results and return only the specified return fields
    results = response_data.get("results", [])
    if return_fields == "ALL":
        out = {
            "meta": meta_info,
            "results": results,
            "result_count": len(results),
            "duplicates_removed": 0,
        }
        if fallback_note:
            out["note"] = fallback_note
        return out
    # If count parameter is used, return results directly (count API format)
    if params.get("count") or count:
        out = {
            "meta": meta_info,
            "results": results,
            "result_count": len(results),
            "duplicates_removed": 0,
        }
        if fallback_note:
            out["note"] = fallback_note
        return out
    flat_keys = []
    # Use original search_fields for consistent output schema even when we fell
    # back to broad text search.
    for k in orig_search_fields.keys():
        if isinstance(k, tuple):
            flat_keys.extend(k)
        else:
            flat_keys.append(k)
    required_fields = flat_keys + requested_return_fields
    # If the tool expects openfda names, include stable IDs in case openfda is empty.
    if isinstance(requested_return_fields, list) and any(
        x in {"openfda.brand_name", "openfda.generic_name"}
        for x in requested_return_fields
    ):
        required_fields.extend(["set_id", "id"])
    # Identity fallback: many SPL records carry an empty `openfda` block, so
    # `openfda.brand_name` / `openfda.generic_name` come back null -- yet the
    # fallback notes tell the caller to check exactly those fields to confirm
    # which product a row describes. `spl_product_data_elements` is populated on
    # those records (e.g. "Ethyol amifostine AMIFOSTINE AMIFOSTINE") and makes
    # that check possible. It is added as an identity field so it can never
    # change which records are kept.
    identity_fields = []
    if (
        any(
            x in {"openfda.brand_name", "openfda.generic_name"} for x in required_fields
        )
        and "spl_product_data_elements" not in required_fields
    ):
        identity_fields.append("spl_product_data_elements")
    # PLR-vs-legacy sibling annotation. Only armed when the tool actually asks
    # for one of the interchangeable safety sections, so no other FDADrugLabel
    # tool changes shape.
    sibling_map = (
        {
            f: LABEL_SECTION_SIBLINGS[f]
            for f in requested_return_fields
            if f in LABEL_SECTION_SIBLINGS
        }
        if isinstance(requested_return_fields, list)
        else {}
    )
    extracted_results = extract_nested_fields(
        results,
        required_fields,
        keywords_list,
        identity_fields=identity_fields,
        sibling_sections=sibling_map or None,
    )

    # Apply return-field mapping after extraction (generic)
    if applied_return_field_mapping:
        for r in extracted_results:
            for primary, fb in applied_return_field_mapping.items():
                r[primary] = r.pop(fb, None)

    # `meta` mirrors openFDA's own numbers and is left untouched, so `meta.total`
    # is the UPSTREAM pre-deduplication hit count and does not describe the list
    # below it. `result_count` / `duplicates_removed` are added so the two can be
    # reconciled.
    duplicates_removed = 0
    deduplicated = False

    # General dedupe + rank (helps any fallback avoid garbage top-N).
    if extracted_results and fallback_terms:

        def _first_str(v):
            if isinstance(v, list) and v:
                return v[0]
            return v if isinstance(v, str) else None

        def _score(r):
            score = 0
            # Prefer having openfda names when present
            if _first_str(r.get("openfda.brand_name")):
                score += 6
            if _first_str(r.get("openfda.generic_name")):
                score += 4
            # Prefer term coverage in high-signal fields
            txt = (
                _first_str(r.get("spl_product_data_elements"))
                or _first_str(r.get("indications_and_usage"))
                or ""
            )
            txt_l = txt.lower()
            hit = 0
            for t in fallback_terms[:12]:
                if t and t in txt_l:
                    hit += 1
            score += hit
            if hit == min(len(fallback_terms), 6):
                score += 3
            return score

        def _content_fingerprint(r):
            """Stable hash of everything a record actually carries.

            The previous fallback key was `brand_name + "|" + generic_name`.
            These tools request neither `set_id` nor `id`, and many SPL records
            have an empty `openfda` block, so every such record hashed to the
            single key "|" and genuinely distinct labels were destroyed (e.g.
            'amifostine' collapsed four distinct labels -- including the branded
            Ethyol one -- into one row while meta.total still said 4).
            Hashing the returned content instead means byte-identical records
            still collapse but different ones survive. `set_id` / `id` are
            excluded because they are used as the primary key above; including
            them here would make every record unique.
            """
            payload = {k: v for k, v in r.items() if k not in ("set_id", "id")}
            blob = json.dumps(payload, sort_keys=True, default=str)
            return hashlib.md5(blob.encode("utf-8")).hexdigest()

        dedup = {}
        for r in extracted_results:
            key = (
                _first_str(r.get("set_id"))
                or _first_str(r.get("id"))
                or (
                    (_first_str(r.get("openfda.brand_name")) or "")
                    + "|"
                    + (_first_str(r.get("openfda.generic_name")) or "")
                    + "|"
                    + _content_fingerprint(r)
                )
            )
            s = _score(r)
            prev = dedup.get(key)
            if prev is None or s > prev[0]:
                dedup[key] = (s, r)
        ranked = sorted(dedup.values(), key=lambda x: x[0], reverse=True)
        duplicates_removed = len(extracted_results) - len(ranked)
        deduplicated = True
        extracted_results = [r for _, r in ranked]
        try:
            user_limit_final = int(params.get("limit") or 0)
        except Exception:
            user_limit_final = 0
        if user_limit_final:
            extracted_results = extracted_results[:user_limit_final]

    out = {
        "meta": meta_info,
        "results": extracted_results,
        "result_count": len(extracted_results),
        "duplicates_removed": duplicates_removed,
    }
    if fallback_note:
        out["note"] = fallback_note
    if deduplicated:
        out["dedup_note"] = (
            f"meta.total ({meta_info.get('total')}) is openFDA's upstream hit "
            f"count before local processing; 'results' holds {len(extracted_results)} "
            f"row(s) after {duplicates_removed} byte-identical duplicate label(s) "
            f"were dropped and the caller's limit was applied. Deduplication runs "
            f"per request on the records fetched for that request, so paging with "
            f"'skip' deduplicates each page independently and consecutive pages "
            f"may overlap or omit records; do not sum result_count across pages."
        )
    section_note = _build_section_note(sibling_map, extracted_results)
    if section_note:
        out["section_note"] = section_note
    return out


def _tools_for_sections(sections):
    """Name the ToolUniverse tool that returns each section, order-preserving."""
    tools = []
    for section in sections:
        tool = LABEL_SECTION_TOOLS.get(section)
        if tool and tool not in tools:
            tools.append(tool)
    return tools


def _build_not_found_suggestion(
    query_text,
    section,
    section_hits,
    sections_present,
    is_abbrev_like,
    name_based,
):
    """Advise the caller after a NOT_FOUND, based on WHY it was empty.

    ``section_hits`` is the number of labels the drug name matched once the
    ``_exists_:<section>`` guard was lifted. When it is non-zero the name was
    never the problem and the requested section simply does not exist for that
    drug -- advising a spelling check there sends the reader to fix something
    that is not broken, and an empty answer on a section like
    ``pharmacogenomics`` reads as "no concern" when the concern is merely filed
    elsewhere on the label.
    """
    if section_hits:
        hint = (
            f"The name '{query_text}' is spelled correctly -- it matches "
            f"{section_hits} openFDA label(s). What is missing is the "
            f"'{section}' SECTION: none of those labels carries one, so "
            f"there is nothing for this tool to return. Absence of the "
            f"section is NOT evidence that the drug has no '{section}' "
            f"concern -- FDA frequently files that content under a "
            f"different section of the same label."
        )
        if sections_present:
            hint += (
                f" Labels sampled for this drug DO carry: "
                f"{', '.join(sections_present)} -- retrieve that content with "
                f"{', '.join(_tools_for_sections(sections_present))}."
            )
        return hint

    parts = []
    if is_abbrev_like:
        parts.append(
            "Try using the full generic/brand name instead of an abbreviation."
        )
    if name_based:
        parts.append(
            "Try removing punctuation/hyphens, checking spelling, or using a longer drug name."
        )
    if section:
        # `warnings_and_precautions` used to be suggested here. It is the printed
        # heading, not an openFDA field -- it is not in openFDA's searchable-field
        # list for drug/label and `search=_exists_:warnings_and_precautions`
        # returns NOT_FOUND, so the suggestion could never work. Name the real
        # sibling sections and the tools that return them instead. Only sections
        # with a known sibling get the PLR/legacy explanation: it is a fact about
        # the warnings family, and asserting it of an unrelated section
        # (pharmacogenomics, say) points the reader at sections that are not
        # related to theirs at all.
        siblings = LABEL_SECTION_SIBLINGS.get(section)
        if siblings:
            hint = (
                f"This label section ('{section}') may be missing for that "
                f"product -- FDA labels split this content by format, with "
                f"modern PLR labels using 'warnings_and_cautions' and legacy/OTC "
                f"labels using 'warnings'/'precautions'. Try a related section: "
                f"{', '.join(siblings)}."
            )
            sibling_tools = _tools_for_sections(siblings)
            if sibling_tools:
                hint += f" Corresponding tools: {', '.join(sibling_tools)}."
        else:
            hint = (
                f"This label section ('{section}') is absent from most FDA "
                f"labels; a drug can have the underlying concern documented "
                f"elsewhere on its label. Try "
                f"FDA_get_boxed_warning_info_by_drug_name or "
                f"FDA_get_warnings_by_drug_name."
            )
        parts.append(hint)
    parts.append(
        "As a fallback, try searching label text fields (e.g., spl_product_data_elements) and then pivot to the desired section."
    )
    return " ".join(parts)


def _build_section_note(sibling_map, extracted_results):
    """Explain a null safety section that a sibling section actually carries.

    Returns ``None`` unless at least one returned row was annotated by
    ``extract_nested_fields`` with ``related_sections_present`` -- i.e. unless
    the requested section(s) really did come back empty while the same label
    demonstrably documents the content elsewhere. This is emitted under its own
    key (``section_note``) rather than reusing ``note``, so the existing
    fallback note is never overwritten.
    """
    if not sibling_map or not extracted_results:
        return None
    found = []
    affected = 0
    for r in extracted_results:
        present = r.get("related_sections_present")
        if not present:
            continue
        affected += 1
        for sib in present:
            if sib not in found:
                found.append(sib)
    if not found:
        return None
    requested = list(sibling_map.keys())
    tools = _tools_for_sections(found)
    return (
        f"The requested label section(s) ({', '.join(requested)}) are absent "
        f"from {affected} of the {len(extracted_results)} returned label(s). "
        f"That is a label-FORMAT difference, NOT evidence that the drug lacks "
        f"this content: modern PLR-format labels (2006-) file it under "
        f"'warnings_and_cautions' and carry no 'warnings' section, while "
        f"legacy/OTC labels do the reverse. Those label(s) DO carry: "
        f"{', '.join(found)}. That content has been added to each affected row "
        f"under its own section key, and is also retrievable via "
        f"{', '.join(tools) if tools else 'the matching FDA section tool'}. "
        f"Do not read a null section as 'this drug has no warnings'."
    )


@register_tool("FDATool")
class FDATool(BaseTool):
    def __init__(self, tool_config, endpoint_url, api_key=None):
        super().__init__(tool_config)
        fields = tool_config["fields"]
        self.search_fields = fields.get("search_fields", {})
        self.return_fields = fields.get("return_fields", [])
        self.exists = fields.get("exists", None)
        if self.exists is None:
            self.exists = self.return_fields
        self.endpoint_url = endpoint_url
        self.api_key = api_key or os.getenv("FDA_API_KEY")

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        # Set default limit to 100 if not provided
        if "limit" not in arguments or arguments["limit"] is None:
            arguments["limit"] = 100
        mapped_arguments = map_properties_to_openfda_fields(
            arguments, self.search_fields
        )
        return search_openfda(
            mapped_arguments,
            endpoint_url=self.endpoint_url,
            api_key=self.api_key,
            exists=self.exists,
            return_fields=self.return_fields,
            exist_option="OR",
        )


@register_tool("FDADrugLabel")
class FDADrugLabelTool(FDATool):
    def __init__(self, tool_config, api_key=None):
        endpoint_url = "https://api.fda.gov/drug/label.json"
        super().__init__(tool_config, endpoint_url, api_key)

    def _is_chembl_id(self, value):
        """Check if the value looks like a ChEMBL ID"""
        if not isinstance(value, str):
            return False
        # Normalize to uppercase for consistent handling
        return value.upper().startswith("CHEMBL")

    def _convert_id_to_drug_name(self, chembl_id):
        """Convert ChEMBL ID to drug name using OpenTargets API"""
        try:
            # Directly call GraphQL API (most efficient, no tool overhead)
            result = _execute_opentargets_query(chembl_id)

            if result and isinstance(result, dict):
                # Extract drug name from result
                drug = None
                if "drug" in result:
                    drug = result["drug"]
                elif "data" in result and "drug" in result["data"]:
                    drug = result["data"]["drug"]

                if drug:
                    # Prefer generic name, fallback to name, then trade names
                    name = drug.get("name")
                    if name:
                        msg = f"Converted ChEMBL ID {chembl_id} to drug name: {name}"
                        print(msg)
                        return name

                    # Try trade names as fallback
                    trade_names = drug.get("tradeNames", [])
                    if trade_names:
                        msg = (
                            f"Converted ChEMBL ID {chembl_id} "
                            f"to trade name: {trade_names[0]}"
                        )
                        print(msg)
                        return trade_names[0]

            # No drug name found - the compound may not be approved as a drug
            msg = (
                f"Warning: Could not convert ChEMBL ID {chembl_id} "
                f"to drug name. This compound may not be approved as a drug "
                f"or may not be available in the OpenTargets database."
            )
            print(msg)
            return None
        except Exception as e:
            msg = f"Error converting ChEMBL ID {chembl_id} to drug name: {e}"
            print(msg)
            return None

    def run(self, arguments):
        """Override run to support ChEMBL ID conversion"""
        arguments = copy.deepcopy(arguments)

        # Check if drug_name parameter is a ChEMBL ID
        drug_name = arguments.get("drug_name")
        # Only process if drug_name is a non-empty string
        if drug_name and isinstance(drug_name, str) and drug_name.strip():
            # Strip whitespace before checking
            drug_name = drug_name.strip()
            if self._is_chembl_id(drug_name):
                # Normalize ChEMBL ID to uppercase (OpenTargets API expects uppercase)
                chembl_id = drug_name.upper()
                # Convert ChEMBL ID to drug name
                converted_name = self._convert_id_to_drug_name(chembl_id)
                if converted_name:
                    arguments["drug_name"] = converted_name
                else:
                    # If conversion fails, provide helpful error message
                    error_msg = (
                        f"Could not convert ChEMBL ID {drug_name} to drug name. "
                        f"This compound (ChEMBL ID: {drug_name}) may not be "
                        f"approved as a drug yet, or it may not be available "
                        f"in the OpenTargets database. Please provide a drug "
                        f"name directly if you know it, or check if this "
                        f"compound is actually approved as a pharmaceutical "
                        f"drug."
                    )
                    return {"status": "error", "error": error_msg}
            else:
                # Not a ChEMBL ID, use original value (strip whitespace)
                arguments["drug_name"] = drug_name

        # Call parent run method
        return super().run(arguments)


@register_tool("FDADrugLabelSearchTool")
class FDADrugLabelSearchTool(FDATool):
    def __init__(self, tool_config=None, api_key=None):
        self.tool_config = {
            "name": "FDADrugLabelSearch",
            "description": "Retrieve information of a specific drug.",
            "label": ["search", "drug"],
            "type": "FDADrugLabelSearch",
            "parameter": {
                "type": "object",
                "properties": {
                    "drug_name": {
                        "type": "string",
                        "description": "The name of the drug.",
                        "required": True,
                    },
                    "return_fields": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "ALL",
                                "abuse",
                                "accessories",
                                "active_ingredient",
                                "adverse_reactions",
                                "alarms",
                                "animal_pharmacology_and_or_toxicology",
                                "ask_doctor",
                                "ask_doctor_or_pharmacist",
                                "assembly_or_installation_instructions",
                                "boxed_warning",
                                "calibration_instructions",
                                "carcinogenesis_and_mutagenesis_and_impairment_of_fertility",
                                "cleaning",
                                "clinical_pharmacology",
                                "clinical_studies",
                                "compatible_accessories",
                                "components",
                                "contraindications",
                                "controlled_substance",
                                "dependence",
                                "description",
                                "diagram_of_device",
                                "disposal_and_waste_handling",
                                "do_not_use",
                                "dosage_and_administration",
                                "dosage_forms_and_strengths",
                                "drug_abuse_and_dependence",
                                "drug_and_or_laboratory_test_interactions",
                                "drug_interactions",
                                "effective_time",
                                "environmental_warning",
                                "food_safety_warning",
                                "general_precautions",
                                "geriatric_use",
                                "guaranteed_analysis_of_feed",
                                "health_care_provider_letter",
                                "health_claim",
                                "how_supplied",
                                "id",
                                "inactive_ingredient",
                                "indications_and_usage",
                                "information_for_owners_or_caregivers",
                                "information_for_patients",
                                "instructions_for_use",
                                "intended_use_of_the_device",
                                "keep_out_of_reach_of_children",
                                "labor_and_delivery",
                                "laboratory_tests",
                                "mechanism_of_action",
                                "microbiology",
                                "nonclinical_toxicology",
                                "nonteratogenic_effects",
                                "nursing_mothers",
                                "openfda",
                                "other_safety_information",
                                "overdosage",
                                "package_label_principal_display_panel",
                                "patient_medication_information",
                                "pediatric_use",
                                "pharmacodynamics",
                                "pharmacogenomics",
                                "pharmacokinetics",
                                "precautions",
                                "pregnancy",
                                "pregnancy_or_breast_feeding",
                                "purpose",
                                "questions",
                                "recent_major_changes",
                                "references",
                                "residue_warning",
                                "risks",
                                "route",
                                "safe_handling_warning",
                                "set_id",
                                "spl_indexing_data_elements",
                                "spl_medguide",
                                "spl_patient_package_insert",
                                "spl_product_data_elements",
                                "spl_unclassified_section",
                                "statement_of_identity",
                                "stop_use",
                                "storage_and_handling",
                                "summary_of_safety_and_effectiveness",
                                "teratogenic_effects",
                                "troubleshooting",
                                "use_in_specific_populations",
                                "user_safety_warnings",
                                "version",
                                "warnings",
                                "warnings_and_cautions",
                                "when_using",
                                "meta",
                            ],
                            "description": "Searchable field.",
                        },
                        "description": "Fields to search within drug labels.",
                        "required": True,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "The number of records to return.",
                        "required": False,
                    },
                    "skip": {
                        "type": "integer",
                        "description": "The number of records to skip.",
                        "required": False,
                    },
                },
            },
            "fields": {
                "search_fields": {
                    "drug_name": ["openfda.brand_name", "openfda.generic_name"]
                },
            },
        }
        endpoint_url = "https://api.fda.gov/drug/label.json"
        super().__init__(self.tool_config, endpoint_url, api_key)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        mapped_arguments = map_properties_to_openfda_fields(
            arguments, self.search_fields
        )
        return_fields = arguments["return_fields"]
        del arguments["return_fields"]
        return search_openfda(
            mapped_arguments,
            endpoint_url=self.endpoint_url,
            api_key=self.api_key,
            return_fields=return_fields,
            exists=return_fields,
            exist_option="OR",
        )


@register_tool("FDADrugLabelSearchIDTool")
class FDADrugLabelSearchIDTool(FDATool):
    def __init__(self, tool_config=None, api_key=None):
        self.tool_config = {
            "name": "FDADrugLabelSearchALLTool",
            "description": "Retrieve any related information to the query.",
            "label": ["search", "drug"],
            "type": "FDADrugLabelSearch",
            "parameter": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "key words need to be searched.",
                        "required": True,
                    },
                    "return_fields": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "ALL",
                                "abuse",
                                "accessories",
                                "active_ingredient",
                                "adverse_reactions",
                                "alarms",
                                "animal_pharmacology_and_or_toxicology",
                                "ask_doctor",
                                "ask_doctor_or_pharmacist",
                                "assembly_or_installation_instructions",
                                "boxed_warning",
                                "calibration_instructions",
                                "carcinogenesis_and_mutagenesis_and_impairment_of_fertility",
                                "cleaning",
                                "clinical_pharmacology",
                                "clinical_studies",
                                "compatible_accessories",
                                "components",
                                "contraindications",
                                "controlled_substance",
                                "dependence",
                                "description",
                                "diagram_of_device",
                                "disposal_and_waste_handling",
                                "do_not_use",
                                "dosage_and_administration",
                                "dosage_forms_and_strengths",
                                "drug_abuse_and_dependence",
                                "drug_and_or_laboratory_test_interactions",
                                "drug_interactions",
                                "effective_time",
                                "environmental_warning",
                                "food_safety_warning",
                                "general_precautions",
                                "geriatric_use",
                                "guaranteed_analysis_of_feed",
                                "health_care_provider_letter",
                                "health_claim",
                                "how_supplied",
                                "id",
                                "inactive_ingredient",
                                "indications_and_usage",
                                "information_for_owners_or_caregivers",
                                "information_for_patients",
                                "instructions_for_use",
                                "intended_use_of_the_device",
                                "keep_out_of_reach_of_children",
                                "labor_and_delivery",
                                "laboratory_tests",
                                "mechanism_of_action",
                                "microbiology",
                                "nonclinical_toxicology",
                                "nonteratogenic_effects",
                                "nursing_mothers",
                                "openfda",
                                "other_safety_information",
                                "overdosage",
                                "package_label_principal_display_panel",
                                "patient_medication_information",
                                "pediatric_use",
                                "pharmacodynamics",
                                "pharmacogenomics",
                                "pharmacokinetics",
                                "precautions",
                                "pregnancy",
                                "pregnancy_or_breast_feeding",
                                "purpose",
                                "questions",
                                "recent_major_changes",
                                "references",
                                "residue_warning",
                                "risks",
                                "route",
                                "safe_handling_warning",
                                "set_id",
                                "spl_indexing_data_elements",
                                "spl_medguide",
                                "spl_patient_package_insert",
                                "spl_product_data_elements",
                                "spl_unclassified_section",
                                "statement_of_identity",
                                "stop_use",
                                "storage_and_handling",
                                "summary_of_safety_and_effectiveness",
                                "teratogenic_effects",
                                "troubleshooting",
                                "use_in_specific_populations",
                                "user_safety_warnings",
                                "version",
                                "warnings",
                                "warnings_and_cautions",
                                "when_using",
                                "meta",
                            ],
                            "description": "Searchable field.",
                        },
                        "description": "Fields to search within drug labels.",
                        "required": True,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "The number of records to return.",
                        "required": False,
                    },
                    "skip": {
                        "type": "integer",
                        "description": "The number of records to skip.",
                        "required": False,
                    },
                },
            },
            "fields": {
                "search_fields": {"query": ["id"]},
            },
        }
        endpoint_url = "https://api.fda.gov/drug/label.json"
        super().__init__(self.tool_config, endpoint_url, api_key)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        mapped_arguments = map_properties_to_openfda_fields(
            arguments, self.search_fields
        )
        return_fields = arguments["return_fields"]
        del arguments["return_fields"]
        return search_openfda(
            mapped_arguments,
            endpoint_url=self.endpoint_url,
            api_key=self.api_key,
            return_fields=return_fields,
            exists=return_fields,
            exist_option="OR",
        )


@register_tool("FDADrugLabelFieldValueTool")
class FDADrugLabelFieldValueTool(BaseTool):
    """
    Search the openFDA drug label dataset by specifying a single openFDA field
    (e.g., "openfda.generic_name") and a corresponding field_value.

    This tool is intentionally generic and does not modify any existing
    FDA tools.
    """

    def __init__(self, tool_config, api_key=None):
        super().__init__(tool_config)
        self.endpoint_url = "https://api.fda.gov/drug/label.json"
        self.api_key = api_key or os.getenv("FDA_API_KEY")

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        field = arguments.pop("field", None)
        field_value = arguments.pop("field_value", None)
        if not field or not field_value:
            return {
                "status": "error",
                "error": "`field` and `field_value` are required.",
            }

        # Runtime enforcement: keep the JSON config small by not inlining
        # huge enums, but still validate inputs against a known allow-list.
        allowed_fields = {
            "abuse",
            "accessories",
            "active_ingredient",
            "adverse_reactions",
            "alarms",
            "animal_pharmacology_and_or_toxicology",
            "ask_doctor",
            "ask_doctor_or_pharmacist",
            "assembly_or_installation_instructions",
            "boxed_warning",
            "calibration_instructions",
            "carcinogenesis_and_mutagenesis_and_impairment_of_fertility",
            "cleaning",
            "clinical_pharmacology",
            "clinical_studies",
            "compatible_accessories",
            "components",
            "contraindications",
            "controlled_substance",
            "dependence",
            "description",
            "diagram_of_device",
            "disposal_and_waste_handling",
            "do_not_use",
            "dosage_and_administration",
            "dosage_forms_and_strengths",
            "drug_abuse_and_dependence",
            "drug_and_or_laboratory_test_interactions",
            "drug_interactions",
            "effective_time",
            "environmental_warning",
            "food_safety_warning",
            "general_precautions",
            "geriatric_use",
            "guaranteed_analysis_of_feed",
            "health_care_provider_letter",
            "health_claim",
            "how_supplied",
            "id",
            "inactive_ingredient",
            "indications_and_usage",
            "information_for_owners_or_caregivers",
            "information_for_patients",
            "instructions_for_use",
            "intended_use_of_the_device",
            "keep_out_of_reach_of_children",
            "labor_and_delivery",
            "laboratory_tests",
            "mechanism_of_action",
            "microbiology",
            "nonclinical_toxicology",
            "nonteratogenic_effects",
            "nursing_mothers",
            "openfda",
            "openfda.brand_name",
            "openfda.generic_name",
            "other_safety_information",
            "overdosage",
            "package_label_principal_display_panel",
            "patient_medication_information",
            "pediatric_use",
            "pharmacodynamics",
            "pharmacogenomics",
            "pharmacokinetics",
            "precautions",
            "pregnancy",
            "pregnancy_or_breast_feeding",
            "purpose",
            "questions",
            "recent_major_changes",
            "references",
            "residue_warning",
            "risks",
            "route",
            "safe_handling_warning",
            "set_id",
            "spl_indexing_data_elements",
            "spl_medguide",
            "spl_patient_package_insert",
            "spl_product_data_elements",
            "spl_unclassified_section",
            "statement_of_identity",
            "stop_use",
            "storage_and_handling",
            "summary_of_safety_and_effectiveness",
            "teratogenic_effects",
            "troubleshooting",
            "use_in_specific_populations",
            "user_safety_warnings",
            "version",
            "warnings",
            "warnings_and_cautions",
            "when_using",
        }

        if field not in allowed_fields:
            return {
                "status": "error",
                "error": (
                    f"Invalid `field`: {field}. "
                    "Use one of the documented FDA drug label fields."
                ),
            }

        return_fields = arguments.pop("return_fields", None)
        if return_fields is None:
            # Keep output small by default.
            return_fields = [
                "openfda.brand_name",
                "openfda.generic_name",
                "id",
                "set_id",
            ]
        if return_fields != "ALL":
            if not isinstance(return_fields, list) or not return_fields:
                return {
                    "status": "error",
                    "error": ('`return_fields` must be "ALL" or a non-empty list.'),
                }
            invalid = [rf for rf in return_fields if rf not in allowed_fields]
            if invalid:
                return {
                    "status": "error",
                    "error": (
                        "Invalid `return_fields` value(s): "
                        + ", ".join(invalid)
                        + ". Use only documented FDA drug label fields."
                    ),
                }

        # Build openFDA search_fields mapping expected by search_openfda()
        arguments["search_fields"] = {field: str(field_value)}

        # `return_fields` is a PROJECTION (which fields to return), NOT a match
        # filter. The user already pinned the record via field:value; do not add
        # `_exists_:{return_field}` constraints — otherwise asking for a field the
        # matched record lacks (e.g. boxed_warning for a drug with none) yields
        # NOT_FOUND and the fallback returns a DIFFERENT drug. Missing projected
        # fields should come back null for the requested record.
        return search_openfda(
            arguments,
            endpoint_url=self.endpoint_url,
            api_key=self.api_key,
            return_fields=return_fields,
            exists=None,
            exist_option="OR",
        )


@register_tool("FDADrugLabelGetDrugGenericNameTool")
class FDADrugLabelGetDrugGenericNameTool(FDADrugLabelTool):
    def __init__(self, tool_config=None, api_key=None):
        if tool_config is None:
            tool_config = {
                "name": "get_drug_generic_name",
                "description": "Get the drug’s generic name based on the drug's generic or brand name.",
                "parameter": {
                    "type": "object",
                    "properties": {
                        "drug_name": {
                            "type": "string",
                            "description": "The generic or brand name of the drug.",
                            "required": True,
                        }
                    },
                },
                "fields": {
                    "search_fields": {
                        "drug_name": ["openfda.brand_name", "openfda.generic_name"]
                    },
                    "return_fields": ["openfda.generic_name"],
                },
                "type": "FDADrugLabelGetDrugGenericNameTool",
                "label": ["FDADrugLabel", "purpose", "FDA"],
            }

        from .data.fda_drugs_with_brand_generic_names_for_tool import drug_list

        self.brand_to_generic = {
            drug["brand_name"]: drug["generic_name"] for drug in drug_list
        }
        self.generic_to_brand = {
            drug["generic_name"]: drug["brand_name"] for drug in drug_list
        }

        super().__init__(tool_config, api_key)

    def run(self, arguments):
        drug_info = {}

        drug_name = arguments.get("drug_name")
        if "-" in drug_name:
            drug_name = drug_name.split("-")[
                0
            ]  # to handle some drug names such as tarlatamab-dlle
        if drug_name in self.brand_to_generic:
            drug_info["openfda.generic_name"] = self.brand_to_generic[drug_name]
            drug_info["openfda.brand_name"] = drug_name
        elif drug_name in self.generic_to_brand:
            drug_info["openfda.brand_name"] = self.generic_to_brand[drug_name]
            drug_info["openfda.generic_name"] = drug_name
        else:
            results = super().run(arguments)
            if results is not None:
                drug_info["openfda.generic_name"] = results["results"][0][
                    "openfda.generic_name"
                ][0]
                drug_info["openfda.brand_name"] = results["results"][0][
                    "openfda.brand_name"
                ][0]
                print("drug_info", drug_info)
            else:
                drug_info = None
        return drug_info


@register_tool("FDADrugLabelAggregated")
class FDADrugLabelGetDrugNamesByIndicationAggregated(FDADrugLabelTool):
    """
    Enhanced version of FDA_get_drug_names_by_indication that:
    - Iterates through all results in batches of 100 (no limit)
    - Aggregates results by generic name
    - Returns one entry per generic name with indication and all brand names
    """

    def __init__(self, tool_config, api_key=None):
        super().__init__(tool_config, api_key)

    def run(self, arguments):
        """
        Run the aggregated drug names search by indication.

        Iterates through all results in batches of 100, aggregates by
        generic name, and returns a list where each entry contains:
        - generic_name: The generic drug name
        - indication: The indication (from input)
        - brand_names: List of all brand names for this generic name
        """
        arguments = copy.deepcopy(arguments)
        indication = arguments.get("indication")

        if not indication:
            return {"status": "error", "error": "indication parameter is required"}

        # Dictionary to aggregate results by generic name
        # Key: generic_name (normalized), Value: set of brand names
        aggregated_results = {}

        # Iterate through results in batches of 1000
        step = 1000
        skip = 0
        total_fetched = 0
        max_iterations = 1000  # Safety limit to prevent infinite loops

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            # Prepare arguments for this batch
            batch_arguments = {"indication": indication, "limit": step, "skip": skip}

            # Call parent run method to get results
            batch_result = super().run(batch_arguments)

            # Check for errors
            if batch_result is None or "error" in batch_result:
                # If we've already fetched some results, return what we have
                if total_fetched > 0:
                    break
                # Otherwise return the error
                error_msg = "No results returned"
                return batch_result if batch_result else {"error": error_msg}

            # Extract results
            results = batch_result.get("results", [])
            meta = batch_result.get("meta", {})

            # Process each result
            for result in results:
                generic_names = result.get("openfda.generic_name", [])
                brand_names = result.get("openfda.brand_name", [])

                # Handle both list and single value cases
                if not isinstance(generic_names, list):
                    generic_names = [generic_names] if generic_names else []
                if not isinstance(brand_names, list):
                    brand_names = [brand_names] if brand_names else []

                # Normalize and process generic names
                for generic_name in generic_names:
                    if not generic_name:
                        continue

                    # Normalize generic name (uppercase, strip whitespace)
                    normalized_generic = str(generic_name).upper().strip()

                    if normalized_generic:
                        # Initialize if not exists
                        if normalized_generic not in aggregated_results:
                            aggregated_results[normalized_generic] = set()

                        # Add all brand names for this generic name
                        for brand_name in brand_names:
                            if brand_name:
                                normalized_brand = str(brand_name).strip()
                                if normalized_brand:
                                    aggregated_results[normalized_generic].add(
                                        normalized_brand
                                    )

            total_fetched += len(results)

            # Check if we've reached the end
            # If we got fewer results than requested, we've reached the end
            if len(results) < step:
                # No more results to fetch
                break

            # Also check meta for total if available
            total_available = meta.get("total", None)
            if total_available is not None:
                if skip + len(results) >= total_available:
                    # Reached the total available
                    break

            # Move to next batch
            skip += step

        # Convert aggregated results to list format
        result_list = []
        for generic_name, brand_names_set in sorted(aggregated_results.items()):
            result_list.append(
                {
                    "generic_name": generic_name,
                    "indication": indication,
                    "brand_names": sorted(list(brand_names_set)),
                }
            )

        return {
            "meta": {
                "total_generic_names": len(result_list),
                "total_records_processed": total_fetched,
                "indication": indication,
            },
            "results": result_list,
        }


@register_tool("FDADrugLabelStats")
class FDADrugLabelGetDrugNamesByIndicationStats(FDADrugLabelTool):
    """
    Enhanced version using FDA count API to efficiently aggregate drug names
    by indication. Uses count mechanism to get brand_name and generic_name
    distributions without fetching full records.
    """

    def __init__(self, tool_config, api_key=None):
        super().__init__(tool_config, api_key)

    def run(self, arguments):
        """
        Run the aggregated drug names search using count API.

        Uses count API to:
        1. Get all unique generic names for the indication
        2. For each generic name, get corresponding brand names
        3. Return aggregated results
        """
        arguments = copy.deepcopy(arguments)
        indication = arguments.get("indication")

        if not indication:
            return {"status": "error", "error": "indication parameter is required"}

        # Step 1: Get all unique generic names using count API
        # Build search query for indication
        # Use the same logic as parent class for building search query
        indication_processed = indication.replace(" and ", " ")
        indication_processed = indication_processed.replace(" AND ", " ")
        indication_processed = " ".join(indication_processed.split())
        # Remove or escape quotes to avoid query errors
        indication_processed = indication_processed.replace('"', "")
        indication_processed = indication_processed.replace("'", "")
        indication_query = indication_processed.replace(" ", "+")
        search_query = f'indications_and_usage:"{indication_query}"'

        # Get all unique generic names using count API (use large limit)
        generic_count_params = {
            "search": search_query,
            "count": "openfda.generic_name.exact",
            "limit": 1000,  # Large limit to get all results
        }

        generic_count_result = search_openfda(
            generic_count_params,
            endpoint_url=self.endpoint_url,
            api_key=self.api_key,
            return_fields=[],
            exist_option="OR",
        )

        # Handle no matches found as empty result, not error
        if generic_count_result is None:
            all_generic_names_data = []
        elif "error" in generic_count_result:
            # Check if it's a "No matches found" error
            error_msg = str(generic_count_result.get("error", {}))
            if "No matches found" in error_msg or "NOT_FOUND" in error_msg:
                all_generic_names_data = []
            else:
                return generic_count_result
        else:
            all_generic_names_data = generic_count_result.get("results", [])

        if not all_generic_names_data:
            return {
                "meta": {
                    "total_generic_names": 0,
                    "total_brand_names": 0,
                    "indication": indication,
                },
                "results": {"generic_names": [], "brand_names": []},
            }

        # Step 2: Get all brand names using count API (only 2 API calls total)
        brand_count_params = {
            "search": search_query,
            "count": "openfda.brand_name.exact",
            "limit": 1000,  # Large limit to get all results
        }

        brand_count_result = search_openfda(
            brand_count_params,
            endpoint_url=self.endpoint_url,
            api_key=self.api_key,
            return_fields=[],
            exist_option="OR",
        )

        # Handle no matches found as empty result, not error
        if brand_count_result is None:
            brand_names_data = []
        elif "error" in brand_count_result:
            # Check if it's a "No matches found" error
            error_msg = str(brand_count_result.get("error", {}))
            if "No matches found" in error_msg or "NOT_FOUND" in error_msg:
                brand_names_data = []
            else:
                # For other errors, still return generic names if available
                brand_names_data = []
        else:
            brand_names_data = brand_count_result.get("results", [])

        # Format generic names
        generic_names_list = [
            {"term": item.get("term", "").strip(), "count": item.get("count", 0)}
            for item in all_generic_names_data
            if item.get("term", "").strip()
        ]
        generic_names_list = sorted(generic_names_list, key=lambda x: x["term"])

        # Format brand names
        brand_names_list = [
            {"term": item.get("term", "").strip(), "count": item.get("count", 0)}
            for item in brand_names_data
            if item.get("term", "").strip()
        ]
        brand_names_list = sorted(brand_names_list, key=lambda x: x["term"])

        return {
            "meta": {
                "total_generic_names": len(generic_names_list),
                "total_brand_names": len(brand_names_list),
                "indication": indication,
            },
            "results": {
                "generic_names": generic_names_list,
                "brand_names": brand_names_list,
            },
        }


@register_tool("OpenFDADrugEventsTool")
class OpenFDADrugEventsTool(BaseRESTTool):
    """OpenFDA drug adverse event search with convenience parameters.

    Accepts either a raw Lucene 'search' string or the convenience parameters
    'drug_name' and 'reaction' (which are assembled into a Lucene query).

    Note: MedDRA terms in FAERS use British English spelling (e.g.
    'haemorrhage' not 'hemorrhage', 'haematoma' not 'hematoma').
    """

    # Valid OpenFDA drug/event.json query parameters
    _VALID_API_PARAMS = frozenset({"search", "limit", "count", "skip", "api_key"})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        args = dict(arguments)
        drug_name = args.pop("drug_name", None)
        reaction = args.pop("reaction", None) or args.pop("adverse_event", None)

        # Strip params unknown to openFDA to avoid HTTP 400 "Invalid parameter".
        args = {k: v for k, v in args.items() if k in self._VALID_API_PARAMS}

        # Build Lucene query from convenience params when
        # 'search' is not provided directly.
        if not args.get("search"):
            if not drug_name:
                return {
                    "status": "error",
                    "error": (
                        "Provide either 'search' (Lucene query) or 'drug_name'. "
                        "Example: drug_name='warfarin', reaction='haemorrhage'. "
                        "Note: MedDRA terms use British spelling (haemorrhage, haematoma, etc.)."
                    ),
                }
            # Shared with the FAERS_* count/detail/analytics tools so this tool
            # cannot disagree with them about how many reports name a drug --
            # see FAERS_DRUG_NAME_FIELDS for the measurements.
            #
            # joiner=" OR " rather than the default "+OR+": this path hands the
            # finished query to requests as a `params` value, and a literal "+"
            # there is percent-encoded to %2B and reaches openFDA as a plus sign
            # instead of a separator. That is also why the AND below is " AND ".
            parts = [faers_drug_name_clause(drug_name, joiner=" OR ")]
            if reaction:
                parts.append(f'patient.reaction.reactionmeddrapt:"{reaction}"')
            args["search"] = " AND ".join(parts)

        result = super().run(args)
        # OpenFDA returns 404 when no records match the query (not a server error).
        # Convert to an actionable no-results message.
        if result.get("status") == "error" and result.get("status_code") == 404:
            query_desc = drug_name or args.get("search", "")
            reaction_hint = (
                " MedDRA terms are case-sensitive and use British spelling "
                "(e.g., 'Anaphylactic reaction' not 'anaphylaxis', "
                "'Haemorrhage' not 'hemorrhage')."
                if reaction
                else ""
            )
            return {
                "status": "success",
                "data": {"results": [], "total": 0},
                "metadata": {
                    "query": args.get("search"),
                    "note": f"No FAERS reports found for '{query_desc}'.{reaction_hint}",
                },
            }
        return result
