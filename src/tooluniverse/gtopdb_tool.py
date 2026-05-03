import re
import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


def _strip_html(text: Any) -> Any:
    """Strip HTML tags and decode HTML entities from a string.

    Feature-49A-H3: GtoPdb returns raw HTML tags in some fields (e.g., <sup>, <i>).
    Feature-51B-002: GtoPdb also returns HTML entities (e.g., &ouml; → ö, &alpha; → α).
    """
    if not isinstance(text, str):
        return text
    # First strip tags, then decode entities
    stripped = re.sub(r"<[^>]+>", "", text).strip()
    # Decode common HTML entities
    import html

    return html.unescape(stripped)


# Feature-53A-005: HGNC gene symbols → GtoPdb pharmacological receptor/enzyme names.
# GtoPdb indexes nuclear receptors and GPCRs by pharmacological names (ERα, D2 receptor)
# not HGNC gene symbols (ESR1, DRD2). When gene_symbol lookup returns 404, fall back to
# searching by the pharmacological name from this mapping.
_HGNC_TO_GTOPDB_NAME: dict = {
    "ESR1": "ERα",
    "ESR2": "ERβ",
    "AR": "androgen receptor",
    "PPARG": "PPARγ",
    "PPARA": "PPARα",
    "PPARD": "PPARδ",
    "NR3C1": "glucocorticoid receptor",
    "NR3C2": "mineralocorticoid receptor",
    "NR1I2": "pregnane X receptor",
    "VDR": "vitamin D receptor",
    "RXRA": "RXRα",
    "DRD1": "D1 receptor",
    "DRD2": "D2 receptor",
    "DRD3": "D3 receptor",
    "DRD4": "D4 receptor",
    "DRD5": "D5 receptor",
    "HTR1A": "5-HT1A receptor",
    "HTR2A": "5-HT2A receptor",
    "ADRB1": "β1-adrenoceptor",
    "ADRB2": "β2-adrenoceptor",
    "ADRA1A": "α1A-adrenoceptor",
    "CHRM1": "M1 receptor",
    "CHRM2": "M2 receptor",
    "CHRM3": "M3 receptor",
    "OPRD1": "δ receptor",
    "OPRM1": "μ receptor",
    "OPRK1": "κ receptor",
    "PTGER2": "EP2 receptor",
    "PTGER4": "EP4 receptor",
    "HDAC1": "HDAC1",
    "PARP1": "PARP1",
}


@register_tool("GtoPdbRESTTool")
class GtoPdbRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.guidetopharmacology.org/services"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL with path parameters and query parameters."""
        url = self.tool_config["fields"]["endpoint"]

        # Feature-29A-07 fix: interactions endpoint requires path params, not query params
        # /services/interactions?targetId=X is ignored; must use /targets/{id}/interactions
        if (
            url.endswith("/interactions")
            and "{targetId}" not in url
            and "{ligandId}" not in url
        ):
            # Accept both camelCase and snake_case aliases
            target_id = args.get("targetId") or args.get("target_id")
            ligand_id = args.get("ligandId") or args.get("ligand_id")
            if target_id is not None:
                url = f"{self.base_url}/targets/{target_id}/interactions"
                # Feature-53A-002: when BOTH targetId AND ligandId are provided, the original code
                # only used targetId (correct for URL construction) but also silently removed
                # ligandId from args without setting _pending_ligand_id_filter. This meant the
                # client-side ligandId filter (set up in the elif branch) never ran, so the
                # ligandId parameter was completely ignored. Fix: preserve ligandId for
                # client-side filtering when both are provided.
                if ligand_id is not None:
                    self._pending_ligand_id_filter = ligand_id
                args = {
                    k: v
                    for k, v in args.items()
                    if k not in ("targetId", "target_id", "ligandId", "ligand_id")
                }
            elif ligand_id is not None:
                # Feature-38B-02: /ligands/{id}/interactions always returns [] per GtoPdb REST API.
                # GtoPdb interactions are indexed by TARGET. Store ligand_id on self for use in run().
                self._pending_ligand_id_filter = ligand_id
                # Fall back to main interactions endpoint; run() will filter client-side
                url = f"{self.base_url}/interactions"
                args = {
                    k: v
                    for k, v in args.items()
                    if k not in ("targetId", "target_id", "ligandId", "ligand_id")
                }

        query_params = {}

        # Separate path params from query params
        path_params = {}
        for k, v in args.items():
            if f"{{{k}}}" in url:
                # This is a path parameter
                path_params[k] = v
            else:
                # This is a query parameter
                query_params[k] = v

        # Replace path parameters in URL
        for k, v in path_params.items():
            url = url.replace(f"{{{k}}}", str(v))

        # Build query string for remaining parameters
        if query_params:
            # Map parameter names to GtoPdb API parameter names
            param_mapping = {
                "target_type": "type",
                "ligand_type": "type",
                "action_type": "type",
                "affinity_parameter": "affinityParameter",
                "min_affinity": "affinity",
                "approved_only": "approved",
                "query": "name",  # alias: query → name (GtoPdb API uses ?name=)
            }

            api_params = {}
            for k, v in query_params.items():
                # Skip limit as it's handled separately
                if k == "limit":
                    continue
                # Map parameter name
                api_key = param_mapping.get(k, k)
                # Convert boolean to lowercase string for API
                if isinstance(v, bool):
                    v = str(v).lower()
                api_params[api_key] = v

            # Build query string
            if api_params:
                from urllib.parse import urlencode

                url = f"{url}?{urlencode(api_params)}"

        return url

    def _search_targets_by_abbreviation_variants(self, query: str, limit: int) -> list:
        """Feature-44A-04: When name search returns results whose names don't contain the query
        (e.g., 'PARP' → tankyrase via PARP5 synonym), also search for numbered variants
        like PARP1, PARP2, PARP3 and merge results.

        GtoPdb stores PARPs under full names ('poly(ADP-ribose) polymerase 1') but
        the abbreviation field has 'PARP1'. The API name= parameter matches abbreviations,
        so name=PARP1 finds the right target.
        """
        results = []
        seen_ids: set = set()
        from urllib.parse import urlencode

        # Try numbered variants: PARP1, PARP2, ..., PARP9
        for suffix in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            if len(results) >= limit:
                break
            candidate = f"{query}{suffix}"
            try:
                url = f"{self.base_url}/targets?{urlencode({'name': candidate})}"
                response = request_with_retry(
                    self.session, "GET", url, timeout=self.timeout, max_attempts=1
                )
                if response.status_code == 200:
                    for t in response.json():
                        tid = t.get("targetId")
                        if tid and tid not in seen_ids:
                            seen_ids.add(tid)
                            results.append(t)
            except Exception:
                pass
        return results[:limit]

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = None
        self._pending_ligand_id_filter = None  # Feature-38B-02: reset per call

        # Feature-61B-001: GtoPdb species filter is case-sensitive ("Human" not "human").
        # Normalize species to Title Case so users can pass any case variant.
        if arguments.get("species"):
            arguments = dict(arguments)
            arguments["species"] = str(arguments["species"]).strip().title()

        # Feature-62B-003: GtoPdb API does not honor approved=true/false on /targets or /ligands
        # endpoints — it returns the same full set regardless. Remove approved_only from
        # the arguments so it is NOT forwarded to the API (where it is silently ignored).
        # We apply client-side filtering on interaction results by cross-referencing
        # the approved ligands endpoint (/services/ligands?approved=true).
        _approved_only_requested = arguments.get("approved_only")
        if _approved_only_requested is not None:
            arguments = dict(arguments)
            arguments.pop("approved_only", None)

        # Feature-63B-001: GtoPdb API silently ignores ligand_type= when combined with name=
        # (e.g., ligand_type='Approved' + name='vemurafenib' returns all name matches,
        # including non-approved compounds). Capture early for client-side post-filtering.
        _ligand_type_requested = arguments.get("ligand_type")

        # Feature-46A-04: gene_symbol convenience parameter for GtoPdb_get_interactions.
        # Auto-resolve gene symbol → targetId so users don't need a separate
        # GtoPdb_search_targets call before querying interactions.
        gene_symbol = arguments.get("gene_symbol")
        if (
            gene_symbol
            and not arguments.get("targetId")
            and not arguments.get("target_id")
        ):
            from urllib.parse import urlencode

            # Feature-54B-001: the previous approach used ?name=gene_symbol which does a
            # substring search on target names/abbreviations. For short symbols like "AR",
            # this returns all targets containing "AR" (adrenoceptors, etc.) and falls back
            # to targets[0] which is wrong. Fix: use ?geneSymbol= first — this is the
            # GtoPdb API parameter for unambiguous HGNC gene symbol lookup and returns
            # exactly the target associated with that gene. Fall back to ?name= only if
            # ?geneSymbol= returns nothing (for gene symbols not in GtoPdb's gene index).
            target_id = None
            try:
                gs_url = (
                    f"{self.base_url}/targets?{urlencode({'geneSymbol': gene_symbol})}"
                )
                gs_resp = request_with_retry(
                    self.session, "GET", gs_url, timeout=self.timeout, max_attempts=2
                )
                if gs_resp.status_code == 200:
                    gs_targets = gs_resp.json()
                    if isinstance(gs_targets, list) and gs_targets:
                        # geneSymbol lookup returns exact matches — prefer the one
                        # whose abbreviation matches the gene symbol, else use first
                        gene_upper = gene_symbol.upper()
                        for t in gs_targets:
                            if (t.get("abbreviation") or "").upper() == gene_upper:
                                target_id = t["targetId"]
                                break
                        if target_id is None:
                            target_id = gs_targets[0]["targetId"]
            except Exception:
                pass

            if target_id is not None:
                arguments = dict(arguments)
                arguments["targetId"] = target_id
                arguments.pop("gene_symbol", None)
            else:
                # ?geneSymbol= returned nothing — try ?name= as fallback
                lookup_url = (
                    f"{self.base_url}/targets?{urlencode({'name': gene_symbol})}"
                )
                try:
                    resp = request_with_retry(
                        self.session,
                        "GET",
                        lookup_url,
                        timeout=self.timeout,
                        max_attempts=2,
                    )
                    # Feature-52B-002: GtoPdb returns HTTP 404 (not 200) when a gene_symbol
                    # doesn't match any target name. Previously, resp.status_code != 200
                    # caused the entire lookup block to be skipped silently, leaving
                    # gene_symbol in arguments → _build_url adds it as an unknown query
                    # param → API ignores it → returns ALL interactions.
                    if resp.status_code == 404 or (
                        resp.status_code == 200 and not isinstance(resp.json(), list)
                    ):
                        # Feature-53A-005: try HGNC→GtoPdb pharmacological name mapping
                        # (e.g., ESR1 → "ERα", DRD2 → "D2 receptor") as a final fallback.
                        fallback_resolved = False
                        gtopdb_name = _HGNC_TO_GTOPDB_NAME.get(gene_symbol.upper())
                        if gtopdb_name:
                            try:
                                from urllib.parse import urlencode as _urlencode

                                fb_url = f"{self.base_url}/targets?{_urlencode({'name': gtopdb_name})}"
                                fb_resp = request_with_retry(
                                    self.session,
                                    "GET",
                                    fb_url,
                                    timeout=self.timeout,
                                    max_attempts=2,
                                )
                                if fb_resp.status_code == 200:
                                    fb_targets = fb_resp.json()
                                    if isinstance(fb_targets, list) and fb_targets:
                                        target_id = fb_targets[0]["targetId"]
                                        arguments = dict(arguments)
                                        arguments["targetId"] = target_id
                                        arguments.pop("gene_symbol", None)
                                        fallback_resolved = True
                            except Exception:
                                pass
                        if not fallback_resolved:
                            return {
                                "status": "success",
                                "data": [],
                                "count": 0,
                                "message": (
                                    f"No GtoPdb target found for gene_symbol='{gene_symbol}'. "
                                    "GtoPdb targets are indexed by pharmacological receptor/enzyme "
                                    "names and may not recognize all HGNC gene symbols. "
                                    f"Try GtoPdb_search_targets with a descriptive name "
                                    f"(e.g., query='MEK1' or 'MAP2K1' or 'MEK' for MAP2K1). "
                                    "Nuclear receptors use Greek-letter names (ESR1→'ERα', "
                                    "AR→'androgen receptor', PPARG→'PPARγ'). "
                                    "Note: many kinases and signaling enzymes (MAP2K1/MEK1, "
                                    "MAP2K2/MEK2, MAPK1/ERK2, MAPK3/ERK1, etc.) have limited "
                                    "or no interaction data in GtoPdb — use "
                                    "ChEMBL_get_drug_mechanisms or ChEMBL_search_compounds "
                                    "for approved inhibitors of MAP kinase pathway proteins."
                                ),
                            }
                    if resp.status_code == 200:
                        targets = resp.json()
                        if isinstance(targets, list) and targets:
                            # Prefer exact abbreviation match (e.g., "KRAS" → KRAS entry)
                            gene_upper = gene_symbol.upper()
                            target_id = None
                            for t in targets:
                                if (t.get("abbreviation") or "").upper() == gene_upper:
                                    target_id = t["targetId"]
                                    break
                            # Feature-48A-05: before falling back to targets[0], try prefix match.
                            # e.g., gene_symbol="ABL1", abbreviation="Abl" →
                            # "abl1".startswith("abl") with rest "1" being a digit → ABL1 selected.
                            # This prevents "ABL1" from silently returning ABL2 (abbr "Arg").
                            if target_id is None:
                                gene_lower = gene_symbol.lower()
                                best_match = None
                                best_len = 0
                                for t in targets:
                                    abbr = (t.get("abbreviation") or "").lower()
                                    if (
                                        abbr
                                        and gene_lower.startswith(abbr)
                                        and len(abbr) > best_len
                                    ):
                                        rest = gene_lower[len(abbr) :]
                                        if rest == "" or rest.isdigit():
                                            best_match = t["targetId"]
                                            best_len = len(abbr)
                                if best_match is not None:
                                    target_id = best_match
                            if target_id is None:
                                target_id = targets[0]["targetId"]
                            arguments = dict(arguments)
                            arguments["targetId"] = target_id
                            # Feature-47A-05: remove gene_symbol so it doesn't leak into the API URL
                            arguments.pop("gene_symbol", None)
                except Exception:
                    pass

        try:
            url = self._build_url(arguments)
            response = request_with_retry(
                self.session, "GET", url, timeout=self.timeout, max_attempts=3
            )
            if response.status_code == 404 and "?" in url:
                # Feature-37A-02: on search endpoints (URL has query params), 404 means no results
                # not a real error. Provide helpful guidance.
                hint = ""
                if "/targets" in url:
                    hint = " If searching for a drug/ligand name, use GtoPdb_search_ligands instead."
                elif "/ligands" in url:
                    hint = " If searching for a target name, use GtoPdb_search_targets instead."
                # Feature-54B-002: multi-word name searches often fail silently
                name_q = arguments.get("name") or arguments.get("query")
                if name_q and " " in str(name_q):
                    first_word = str(name_q).split()[0]
                    hint += (
                        f" GtoPdb text search may not match multi-word phrases. "
                        f"Try a single keyword instead, e.g., name='{first_word}'."
                    )
                return {
                    "status": "success",
                    "data": [],
                    "count": 0,
                    "url": url,
                    "message": f"No results found matching the search criteria.{hint}",
                }
            if response.status_code != 200:
                raw_detail = (response.text or "")[:500]
                # Feature-35A-01: extract human-readable API error from JSON detail
                try:
                    import json as _json

                    detail_obj = _json.loads(raw_detail)
                    api_msg = detail_obj.get("error", raw_detail)
                except Exception:
                    api_msg = raw_detail
                return {
                    "status": "error",
                    "error": f"GtoPdb API error: {api_msg} (HTTP {response.status_code})",
                    "url": url,
                    "status_code": response.status_code,
                    "detail": raw_detail,
                }
            data = response.json()

            # Feature-49A-H3: strip raw HTML tags from GtoPdb API fields.
            # GtoPdb returns HTML-formatted display values in some fields
            # (e.g., originalAffinity="6.3x10<sup>-6</sup>", ligandName="compound 5 [Smith <i>et al</i>., 2020]").
            # Strip tags so LLMs and downstream code receive plain text.
            _HTML_FIELDS = ("originalAffinity", "ligandName", "authors", "name")
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for field in _HTML_FIELDS:
                            if field in item:
                                item[field] = _strip_html(item[field])

            # Feature-38B-02: client-side filter by ligandId when requested
            # (/ligands/{id}/interactions always returns [], so we fetch all and filter)
            ligand_id_filter = getattr(self, "_pending_ligand_id_filter", None)
            if ligand_id_filter is not None and isinstance(data, list):
                data = [x for x in data if x.get("ligandId") == ligand_id_filter]

            # Feature-63A-001: approved_only for interactions must cross-reference the approved
            # ligands endpoint. Interaction records do NOT have an 'approvedDrug' field;
            # approval status lives on /services/ligands objects as the 'approved' boolean.
            # Feature-63B-001: ligand_type= is silently ignored by GtoPdb API when name= is also
            # present. Apply both filters client-side BEFORE computing total_available/limit.
            _pre_approved_filter_count = len(data) if isinstance(data, list) else 0
            if (
                _approved_only_requested
                and isinstance(data, list)
                and "/interactions" in url
            ):
                try:
                    approved_url = f"{self.base_url}/ligands?approved=true"
                    approved_resp = request_with_retry(
                        self.session,
                        "GET",
                        approved_url,
                        timeout=self.timeout,
                        max_attempts=2,
                    )
                    if approved_resp.status_code == 200:
                        approved_ids = {
                            lig.get("ligandId")
                            for lig in approved_resp.json()
                            if isinstance(lig, dict) and lig.get("approved")
                        }
                        data = [x for x in data if x.get("ligandId") in approved_ids]
                except Exception:
                    pass  # on API failure, keep all data unfiltered

            if _ligand_type_requested and isinstance(data, list) and "/ligands" in url:
                lt_lower = _ligand_type_requested.lower()
                if lt_lower == "approved":
                    # 'approved' is a boolean field on GtoPdb ligand records
                    data = [x for x in data if x.get("approved") is True]
                else:
                    # Match structural type field (case-insensitive)
                    data = [
                        x for x in data if (x.get("type") or "").lower() == lt_lower
                    ]

            # Apply limit if specified (max_results is an alias for limit)
            # Feature-47A-04: increased default from 20 to 50 — interaction-rich targets
            # like EGFR (90 interactions) would only show 22% of data at limit=20.
            limit = arguments.get("limit", arguments.get("max_results", 50))
            total_available = len(data) if isinstance(data, list) else None
            if isinstance(data, list) and len(data) > limit:
                data = data[:limit]

            result: Dict[str, Any] = {
                "status": "success",
                "data": data,
                "url": url,
                "count": len(data) if isinstance(data, list) else 1,
            }

            # Feature-62B-003 / Feature-63B-001: for non-interaction endpoints, approved_only is not
            # applicable. For ligand searches, use ligand_type='Approved' instead.
            if _approved_only_requested and "/interactions" not in url:
                result["approved_only_note"] = (
                    "Note: approved_only applies only to GtoPdb_get_interactions (filters by "
                    "cross-referencing the GtoPdb approved ligands registry). For ligand "
                    "searches, use ligand_type='Approved' instead to filter by approval status."
                )

            # Feature-60A-003: disclose truncation so users know data was cut off
            if total_available is not None and total_available > len(data):
                result["total_available"] = total_available
                result["returned"] = len(data)
                result["truncation_note"] = (
                    f"Returned {len(data)} of {total_available} total interactions."
                    f" Increase limit (e.g., limit={total_available}) to retrieve all."
                )

            # Feature-54B-002: multi-word name search hint when results empty
            name_q = arguments.get("name") or arguments.get("query")
            if (
                result["count"] == 0
                and ("/targets" in url or "/ligands" in url)
                and "?" in url
                and name_q
                and " " in str(name_q)
            ):
                first_word = str(name_q).split()[0]
                result["multi_word_hint"] = (
                    f"GtoPdb text search may not match multi-word phrases like '{name_q}'. "
                    f"Try a single keyword: name='{first_word}'."
                )

            # Feature-38B-02: if ligandId filter returned nothing, add informative hint
            ligand_id_filter = getattr(self, "_pending_ligand_id_filter", None)
            if ligand_id_filter is not None and result["count"] == 0:
                result["message"] = (
                    f"No interactions found for ligandId={ligand_id_filter} in the GtoPdb "
                    "interactions database. Possible reasons: (1) The drug may be stored under "
                    "a related compound entry — some approved drugs (e.g., vemurafenib ID=5893) "
                    "have pharmacological data under their research compound record (e.g., ID=8548). "
                    "Check the ligand details from GtoPdb_search_ligands for 'activeDrugIds' or "
                    "'prodrugIds' fields and try those IDs. (2) The drug may not be in the GtoPdb "
                    "interactions database. GtoPdb covers GPCR, ion channel, enzyme, and transporter "
                    "interactions; some targets may be absent. Search by target_id instead if you "
                    "know the GtoPdb target ID."
                )

            # Feature-44A-04: for target name searches, detect when returned target names
            # don't contain the query string (meaning the match was via abbreviation/synonym,
            # e.g. name=PARP matches tankyrase via its PARP5 synonym). In that case,
            # also search for numbered variants (PARP1, PARP2, ...) and merge results.
            query = arguments.get("query")
            if (
                query
                and "/targets" in url
                and "/targets/" not in url
                and isinstance(data, list)
            ):
                q_lower = query.lower()
                # Check if the query appears in any returned target name
                names_contain_query = any(
                    q_lower in t.get("name", "").lower() for t in data
                )
                if not names_contain_query and data:
                    # The match was via synonym/abbreviation; try numbered variants
                    extra = self._search_targets_by_abbreviation_variants(query, limit)
                    if extra:
                        existing_ids = {t.get("targetId") for t in data}
                        new_targets = [
                            t for t in extra if t.get("targetId") not in existing_ids
                        ]
                        if new_targets:
                            data = new_targets + data  # put canonical matches first
                            result["data"] = data
                            result["count"] = len(data)
                            result["note"] = (
                                f"Searched for '{query}'. Results include targets with abbreviation "
                                f"matching '{query}' (e.g., {data[0].get('name', '')}) as well as "
                                f"targets matched via synonym. For kinase/enzyme families, try "
                                f"searching with full gene symbols like '{query}1', '{query}2'."
                            )

            # Feature-59B-002: when an explicit target_id was provided and interactions is empty,
            # warn the user — the target ID may not exist in GtoPdb (the API returns HTTP 200
            # with [] for non-existent targets, indistinguishable from "target has no data").
            import re as _re_gtopdb

            _tid_match = _re_gtopdb.search(r"/targets/(\d+)/interactions", url)
            if _tid_match and isinstance(data, list) and len(data) == 0:
                # Feature-63A-001: if approved_only filter cleared all results, give a specific
                # explanation instead of the misleading "target may be invalid" warning.
                if _approved_only_requested and _pre_approved_filter_count > 0:
                    result["approved_only_info"] = (
                        f"approved_only=True filtered all {_pre_approved_filter_count} "
                        f"interaction(s) for this target. GtoPdb interaction data focuses on "
                        "pharmacological research compounds with measured affinity — approved "
                        "drugs are rarely listed here. For approved drug-target interactions, "
                        "use ChEMBL_get_drug_mechanisms or ChEMBL_search_compounds with the "
                        "target gene name."
                    )
                else:
                    result["warning"] = (
                        f"No interactions found for target_id={_tid_match.group(1)}. "
                        "This may mean (a) the target has no pharmacological data in GtoPdb, "
                        "OR (b) the target ID is invalid (GtoPdb returns an empty list for "
                        "non-existent target IDs without an error). "
                        "Verify the target exists using GtoPdb_search_targets(name='...') "
                        "and confirm the returned targetId before calling get_interactions."
                    )

            # Feature-35A-02: add top-level queried_target summary for interactions endpoint
            # so users can immediately verify they're getting the right target's data
            if isinstance(data, list) and data and "/interactions" in url:
                first = data[0]
                if "targetId" in first or "targetName" in first:
                    result["queried_target"] = {
                        "id": first.get("targetId"),
                        "name": first.get("targetName"),
                    }
                elif "ligandId" in first or "ligandName" in first:
                    result["queried_ligand"] = {
                        "id": first.get("ligandId"),
                        "name": first.get("ligandName"),
                    }
                # Feature-49B-002 / Feature-55A-002 / Feature-55A-003 / Feature-55B-001:
                # GtoPdb interactions list pharmacological research compounds — approved drugs
                # may be absent for any target class (kinases, GPCRs, ion channels, etc.).
                # The previous code checked item.get("approved") which is only present on
                # /ligands objects, not /interactions objects, so has_approved was always False.
                # Fix: always emit the note as factual guidance (not conditional on an
                # always-false check). Use neutral target-class-agnostic wording. Embed the
                # queried gene_symbol so the ChEMBL suggestion is immediately actionable.
                if isinstance(data, list) and len(data) > 0:
                    _chembl_target = gene_symbol or (
                        result.get("queried_target", {}).get("name", "the target")
                    )
                    result["coverage_note"] = (
                        "GtoPdb interactions list pharmacological research compounds — approved "
                        "drugs for this target are not represented in these results. For approved "
                        "drugs and clinical compounds, use ChEMBL_get_drug_mechanisms or "
                        f"ChEMBL_search_compounds with target_name='{_chembl_target}'."
                    )

            # Feature-49A-M5: for ligand search results, add a hint about getting interaction data.
            # Feature-51A-001: warn that ligandId-based lookups often fail for enzyme/kinase
            # inhibitors (PARP, HDAC, CDK, etc.) because GtoPdb indexes interactions by TARGET.
            # In those cases, querying by gene_symbol or targetId is more reliable.
            if isinstance(data, list) and data and "/ligands" in url and "?" in url:
                result["hint"] = (
                    "To find pharmacological interactions for a specific ligand, try "
                    "GtoPdb_get_interactions with ligandId=<id>. IMPORTANT: For enzyme "
                    "and kinase inhibitors (e.g., PARP inhibitors, CDK inhibitors, HDAC "
                    "inhibitors, kinase inhibitors), GtoPdb indexes interactions by TARGET, "
                    "and ligandId-based queries often return empty results even for approved "
                    "drugs. In that case, query by gene_symbol (e.g., gene_symbol='PARP1') "
                    "or targetId from GtoPdb_search_targets for more complete results."
                )

            return result
        except Exception as e:
            return {
                "status": "error",
                "error": f"GtoPdb API error: {str(e)}",
                "url": url,
            }
