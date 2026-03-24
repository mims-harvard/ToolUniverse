import copy
import re
from typing import Any, Dict

import requests

from .base_rest_tool import BaseRESTTool
from .base_tool import BaseTool
from .tool_registry import register_tool
import os
import urllib.parse

# Cache for GraphQL query to avoid repeated string operations
_OPENTARGETS_DRUG_NAMES_QUERY = None
_OPENTARGETS_ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"


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


def extract_nested_fields(records, fields, keywords=None):
    """
    Recursively extracts nested fields from a list of dictionaries.

    :param records: List of dictionaries from which to extract fields
    :param fields: List of nested fields to extract, each specified with dot notation (e.g., 'openfda.brand_name')

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
        if any(extracted_record.values()):
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
        params["search"] = "+".join(search_query)
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
    if exists is not None:
        if isinstance(exists, str):
            exists = [exists]
        if "search" in params:
            if exist_option == "AND":
                params["search"] += (
                    "+AND+("
                    + "+AND+".join([f"_exists_:{keyword}" for keyword in exists])
                    + ")"
                )
            elif exist_option == "OR":
                params["search"] += (
                    "+AND+("
                    + "+OR+".join([f"_exists_:{keyword}" for keyword in exists])
                    + ")"
                )
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
                        break
                if used_generic_fallback:
                    break

        # Stage A: phrase -> terms within the same search field(s)
        if (
            not used_generic_fallback
            and fallback_terms
            and isinstance(response_data, dict)
            and response_data.get("error", {}).get("code") == "NOT_FOUND"
        ):
            # Use explicit boolean AND between terms to avoid very broad matches.
            term_expr = "+AND+".join(fallback_terms)
            per_field = []
            for f in orig_fields_flat:
                per_field.append(f"{f}:({term_expr})")
            search_a = "(" + "+OR+".join(per_field) + ")"
            # Respect exists only for fields we are actually using in this stage.
            ex_a = _filter_exists(exists, set(orig_fields_flat))
            if ex_a:
                search_a += (
                    "+AND+(" + "+OR+".join([f"_exists_:{e}" for e in ex_a]) + ")"
                )
            tmp = _run_search(
                search_a, limit_override=max(int(params.get("limit") or 0), 25)
            )
            if isinstance(tmp, dict) and "error" not in tmp:
                response_data = tmp
                used_generic_fallback = True

        # Stage B: expand to label-text fields (robust when openfda is empty or name mismatched)
        if (
            fallback_terms
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
            search_b = "(" + "+OR+".join(per_field) + ")"
            ex_b = _filter_exists(exists, set(fields_b))
            if ex_b:
                search_b += (
                    "+AND+(" + "+OR+".join([f"_exists_:{e}" for e in ex_b]) + ")"
                )
            tmp = _run_search(
                search_b, limit_override=max(int(params.get("limit") or 0), 25)
            )
            if isinstance(tmp, dict) and "error" not in tmp:
                response_data = tmp
                used_generic_fallback = True

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
                        per_field = [f'spl_product_data_elements:"{m}"' for m in near]
                        search_c = "(" + "+OR+".join(per_field) + ")"
                        tmp = _run_search(
                            search_c,
                            limit_override=max(int(params.get("limit") or 0), 25),
                        )
                        if isinstance(tmp, dict) and "error" not in tmp:
                            response_data = tmp
                            used_generic_fallback = True
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

            suggestion_parts = []
            if is_abbrev_like:
                suggestion_parts.append(
                    "Try using the full generic/brand name instead of an abbreviation."
                )
            if name_based:
                suggestion_parts.append(
                    "Try removing punctuation/hyphens, checking spelling, or using a longer drug name."
                )
            if section:
                suggestion_parts.append(
                    f"This label section ('{section}') may be missing for that product; try a related section like 'contraindications' or 'warnings_and_precautions'."
                )
            suggestion_parts.append(
                "As a fallback, try searching label text fields (e.g., spl_product_data_elements) and then pivot to the desired section."
            )
            suggestion = " ".join(suggestion_parts)
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
            }
        return None

    # Extract meta information
    meta_info = response_data.get("meta", {})
    meta_info = meta_info.get("results", {})

    # Extract results and return only the specified return fields
    results = response_data.get("results", [])
    if return_fields == "ALL":
        return {"meta": meta_info, "results": results}
    # If count parameter is used, return results directly (count API format)
    if params.get("count") or count:
        return {"meta": meta_info, "results": results}
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
    extracted_results = extract_nested_fields(results, required_fields, keywords_list)

    # Apply return-field mapping after extraction (generic)
    if applied_return_field_mapping:
        for r in extracted_results:
            for primary, fb in applied_return_field_mapping.items():
                r[primary] = r.pop(fb, None)

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

        dedup = {}
        for r in extracted_results:
            key = (
                _first_str(r.get("set_id"))
                or _first_str(r.get("id"))
                or (
                    (_first_str(r.get("openfda.brand_name")) or "")
                    + "|"
                    + (_first_str(r.get("openfda.generic_name")) or "")
                )
            )
            s = _score(r)
            prev = dedup.get(key)
            if prev is None or s > prev[0]:
                dedup[key] = (s, r)
        ranked = sorted(dedup.values(), key=lambda x: x[0], reverse=True)
        extracted_results = [r for _, r in ranked]
        try:
            user_limit_final = int(params.get("limit") or 0)
        except Exception:
            user_limit_final = 0
        if user_limit_final:
            extracted_results = extracted_results[:user_limit_final]

    return {"meta": meta_info, "results": extracted_results}


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

        return search_openfda(
            arguments,
            endpoint_url=self.endpoint_url,
            api_key=self.api_key,
            return_fields=return_fields,
            exists=return_fields if return_fields != "ALL" else None,
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
            parts = [f'patient.drug.medicinalproduct:"{drug_name}"']
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
