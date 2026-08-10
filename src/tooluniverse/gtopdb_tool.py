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


# ---------------------------------------------------------------------------
# Fix-R30-GtoPdb-type: make the `type` filter on the /ligands and /targets
# search endpoints real.
#
# Verified live against https://www.guidetopharmacology.org/services on
# 2026-08-10:
#
#   /ligands?name=semaglutide                       -> 1 record, type "Peptide"
#   /ligands?name=semaglutide&type=Synthetic%20organic -> the SAME record
#   /ligands?name=semaglutide&type=NotARealType     -> the SAME record
#   /targets?name=serotonin                         -> 19 records (gpcr/lgic/transporter)
#   /targets?name=serotonin&type=GPCR               -> the SAME 19 records
#   /targets?name=serotonin&type=NotARealType       -> the SAME 19 records
#
# i.e. GtoPdb silently DROPS ?type= whenever ?name= is present, on both search
# endpoints. Used alone, ?type= does filter, but only for a specific vocabulary
# that is neither the record `type` vocabulary nor the enum ToolUniverse used to
# document:
#
#   /ligands?type=Peptide            -> HTTP 404 {"error":"No ligands found"}
#   /ligands?type=Endogenous peptide -> HTTP 404   (GtoPdb's own docs list it)
#   /ligands?type=INN                -> HTTP 404   (GtoPdb's own docs list it)
#   /targets?type=Ion channel        -> HTTP 404   (ToolUniverse documented it)
#   /targets?type=Nuclear receptor   -> HTTP 404   (ToolUniverse documented it)
#   /targets?type=Catalytic receptor -> HTTP 404   (ToolUniverse documented it)
#
# So the only trustworthy filter is a client-side one against the record's own
# `type` field, plus input validation against the values GtoPdb actually uses.
#
# Census of the full record vocabulary (GET /ligands, 13856 records; GET
# /targets, 3317 records), 2026-08-10:
#   ligands: Synthetic organic 9753, Peptide 2452, Natural product 558,
#            Metabolite 514, Antibody 495, Nucleic acid 45, Inorganic 39
#   targets: enzyme 1337, transporter 557, gpcr 411, other_protein 348,
#            catalytic_receptor 313, vgic 145, lgic 86, other_ic 61, nhr 49,
#            "" 10 (the records ?type=AccessoryProtein returns)
# ---------------------------------------------------------------------------


def _norm_type(value: Any) -> str:
    """Normalize a type token for comparison.

    Case-, space- and underscore-insensitive so that the API query vocabulary
    ("CatalyticReceptor"), the record vocabulary ("catalytic_receptor") and
    human spellings ("Catalytic receptor") all collapse to one key.
    """
    if value is None:
        return ""
    return re.sub(r"[\s_\-]+", " ", str(value).strip().lower())


class _TypeSpec:
    """One accepted `type` value for a GtoPdb search endpoint.

    canonical      display spelling used in messages
    record_types   normalized record `type` values that satisfy the filter
                   (None when the filter is a boolean record flag instead)
    flag           record boolean field that satisfies the filter, e.g.
                   'approved' -- GtoPdb exposes these through ?type= too
    server_value   value that ?type= actually honours upstream when no name
                   search is in play, or None if GtoPdb 404s on it
    """

    __slots__ = ("canonical", "flag", "record_types", "server_value")

    def __init__(self, canonical, record_types=None, flag=None, server_value=None):
        self.canonical = canonical
        self.record_types = (
            frozenset(_norm_type(t) for t in record_types)
            if record_types is not None
            else None
        )
        self.flag = flag
        self.server_value = server_value

    def matches(self, record: Any) -> bool:
        if not isinstance(record, dict):
            return False
        if self.flag is not None:
            return record.get(self.flag) is True
        return _norm_type(record.get("type")) in self.record_types


def _build_specs(entries) -> dict:
    """Expand (aliases, spec) pairs into a normalized alias -> spec lookup."""
    table = {}
    for aliases, spec in entries:
        for alias in aliases:
            table[_norm_type(alias)] = spec
    return table


_LIGAND_TYPE_SPECS = _build_specs(
    [
        # Structural types -- these are the values a ligand record's `type`
        # field actually carries.
        (
            ("Synthetic organic",),
            _TypeSpec(
                "Synthetic organic", ["Synthetic organic"], None, "Synthetic organic"
            ),
        ),
        # ?type=Peptide 404s upstream even though 2452 records carry it, so it
        # must never be pushed server-side; client-side only.
        (("Peptide",), _TypeSpec("Peptide", ["Peptide"], None, None)),
        (
            ("Natural product",),
            _TypeSpec("Natural product", ["Natural product"], None, "Natural product"),
        ),
        (("Metabolite",), _TypeSpec("Metabolite", ["Metabolite"], None, "Metabolite")),
        (("Antibody",), _TypeSpec("Antibody", ["Antibody"], None, "Antibody")),
        (
            ("Nucleic acid",),
            _TypeSpec("Nucleic acid", ["Nucleic acid"], None, "Nucleic acid"),
        ),
        (("Inorganic",), _TypeSpec("Inorganic", ["Inorganic"], None, "Inorganic")),
        # Boolean "flag" pseudo-types: not record `type` values, but boolean
        # fields present on every ligand record, and accepted by ?type=.
        (("Approved",), _TypeSpec("Approved", None, "approved", "Approved")),
        (("Withdrawn",), _TypeSpec("Withdrawn", None, "withdrawn", "Withdrawn")),
        (
            ("Labelled", "Labeled"),
            _TypeSpec("Labelled", None, "labelled", "Labelled"),
        ),
    ]
)

_TARGET_TYPE_SPECS = _build_specs(
    [
        (("GPCR",), _TypeSpec("GPCR", ["gpcr"], None, "GPCR")),
        (
            ("NHR", "Nuclear receptor"),
            _TypeSpec("NHR", ["nhr"], None, "NHR"),
        ),
        (("LGIC",), _TypeSpec("LGIC", ["lgic"], None, "LGIC")),
        (("VGIC",), _TypeSpec("VGIC", ["vgic"], None, "VGIC")),
        (("OtherIC",), _TypeSpec("OtherIC", ["other_ic"], None, "OtherIC")),
        (("Enzyme",), _TypeSpec("Enzyme", ["enzyme"], None, "Enzyme")),
        (
            ("CatalyticReceptor", "Catalytic receptor"),
            _TypeSpec(
                "CatalyticReceptor",
                ["catalytic_receptor"],
                None,
                "CatalyticReceptor",
            ),
        ),
        (
            ("Transporter",),
            _TypeSpec("Transporter", ["transporter"], None, "Transporter"),
        ),
        (
            ("OtherProtein", "Other protein"),
            _TypeSpec("OtherProtein", ["other_protein"], None, "OtherProtein"),
        ),
        (
            ("AccessoryProtein", "Accessory protein"),
            # ?type=AccessoryProtein returns 10 records whose `type` is "".
            _TypeSpec("AccessoryProtein", [""], None, "AccessoryProtein"),
        ),
        # Convenience umbrella: GtoPdb splits ion channels into three record
        # types and has no single query value covering them, so this one is
        # client-side only.
        (
            ("Ion channel", "Ion channels"),
            _TypeSpec("Ion channel", ["lgic", "vgic", "other_ic"], None, None),
        ),
    ]
)

# Values GtoPdb's own web-service documentation lists but that match nothing
# (verified: all three return HTTP 404 "No ligands found"). Rejecting them with
# a pointer beats silently returning every record.
_LIGAND_TYPE_DEAD_VALUES = {
    "endogenous peptide": "Peptide",
    "inn": "Approved",
}


def _type_validation_error(raw_value: Any, specs: dict, dead: dict, kind: str) -> dict:
    """Structured rejection for an unrecognised `type` value."""
    valid = sorted({spec.canonical for spec in specs.values()})
    message = (
        f"Invalid {kind} type={raw_value!r}. GtoPdb does not use this value, and its "
        f"?type= parameter is silently ignored whenever a name search is also supplied, "
        f"so an unrecognised value would otherwise return every record unfiltered. "
        f"Valid values: {', '.join(valid)}."
    )
    hint = dead.get(_norm_type(raw_value))
    if hint:
        message += (
            f" Note: {raw_value!r} appears in GtoPdb's web-service documentation but "
            f"matches no record in the database -- use {hint!r} instead."
        )
    return {
        "status": "error",
        "error": message,
        "valid_types": valid,
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
                # Fix-R4A-3: gene_symbol was not in this map, so it was passed
                # through verbatim as ?gene_symbol=, which GtoPdb ignores --
                # GtoPdb_search_targets returned the identical unfiltered
                # first-50 target list ("12R-LOX", "12S-LOX", ...) for
                # gene_symbol=CHRNA7, gene_symbol=GRIN2B and no arguments at
                # all. GtoPdb does index targets by gene symbol under
                # ?geneSymbol= (CHRNA7 -> target 468, GRIN2B -> 457,
                # HTR6 -> 11), which the sibling GtoPdb_get_interactions
                # already uses.
                "gene_symbol": "geneSymbol",
                "gene": "geneSymbol",
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

    def _fetch_json(self, url: str):
        """GET a single GtoPdb endpoint and return (data, error_dict).

        On success: (parsed_json, None).
        On HTTP error / network failure: (None, {status,error,...}) so callers
        can decide whether the error is fatal or recoverable (e.g. a 404 from an
        endpoint that legitimately has no records).
        """
        try:
            response = request_with_retry(
                self.session, "GET", url, timeout=self.timeout, max_attempts=3
            )
        except Exception as exc:
            return None, {
                "status": "error",
                "error": f"GtoPdb API error: {exc}",
                "url": url,
            }
        if response.status_code != 200:
            raw_detail = (response.text or "")[:500]
            try:
                import json as _json

                api_msg = _json.loads(raw_detail).get("error", raw_detail)
            except Exception:
                api_msg = raw_detail
            return None, {
                "status": "error",
                "error": f"GtoPdb API error: {api_msg} (HTTP {response.status_code})",
                "url": url,
                "status_code": response.status_code,
            }
        try:
            return response.json(), None
        except Exception as exc:
            return None, {
                "status": "error",
                "error": f"GtoPdb API error: invalid JSON response: {exc}",
                "url": url,
            }

    def _run_ligand_properties(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """GtoPdb_get_ligand_properties: merge a ligand's structure +
        molecularProperties into a single record.

        Endpoints (keyless):
          GET /services/ligands/{id}/molecularProperties
          GET /services/ligands/{id}/structure
        Invalid ligand IDs return HTTP 404 (molecularProperties) or HTTP 500
        (structure); we surface that as a structured error, never raise.
        """
        ligand_id = arguments.get("ligand_id", arguments.get("ligandId"))
        if ligand_id is None:
            return {
                "status": "error",
                "error": "Missing required parameter 'ligand_id'.",
            }

        props_url = f"{self.base_url}/ligands/{ligand_id}/molecularProperties"
        struct_url = f"{self.base_url}/ligands/{ligand_id}/structure"

        props, props_err = self._fetch_json(props_url)
        structure, struct_err = self._fetch_json(struct_url)

        # If BOTH calls failed, the ligand ID is almost certainly invalid.
        if props_err and struct_err:
            err = dict(struct_err)
            err["error"] = (
                f"No GtoPdb ligand found for ligand_id={ligand_id}. "
                f"{struct_err['error']}"
            )
            return err

        data: Dict[str, Any] = {"ligandId": ligand_id}
        if isinstance(structure, dict):
            for key, value in structure.items():
                data[key] = _strip_html(value) if key == "ligandName" else value
        if isinstance(props, dict):
            data["molecularProperties"] = props

        result: Dict[str, Any] = {
            "status": "success",
            "data": data,
            "ligand_id": ligand_id,
        }
        notes = []
        if props_err:
            notes.append("molecularProperties unavailable for this ligand.")
        if struct_err:
            notes.append("structure (SMILES/InChI) unavailable for this ligand.")
        if notes:
            result["note"] = " ".join(notes)
        return result

    def _run_disease_associations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """GtoPdb_get_disease_associations: return a disease's curated target and
        ligand associations together.

        Endpoints (keyless):
          GET /services/diseases/{id}/diseaseTargets
          GET /services/diseases/{id}/diseaseLigands
        An empty list ([]) is a valid response (e.g. disease 1161 has targets but
        no ligands). Invalid disease IDs return HTTP 500 with an error body.
        """
        disease_id = arguments.get("disease_id", arguments.get("diseaseId"))
        if disease_id is None:
            return {
                "status": "error",
                "error": "Missing required parameter 'disease_id'.",
            }

        targets_url = f"{self.base_url}/diseases/{disease_id}/diseaseTargets"
        ligands_url = f"{self.base_url}/diseases/{disease_id}/diseaseLigands"

        targets, targets_err = self._fetch_json(targets_url)
        ligands, ligands_err = self._fetch_json(ligands_url)

        # Invalid disease IDs: diseaseTargets returns HTTP 500 (server-side null
        # disease) while diseaseLigands quirkily returns HTTP 200 with []. Treat a
        # 500 on diseaseTargets together with no ligand records as "disease not
        # found" so callers don't mistake an invalid ID for an empty valid disease.
        targets_500 = bool(targets_err) and targets_err.get("status_code") == 500
        no_ligand_records = not (isinstance(ligands, list) and ligands)
        if targets_err and (ligands_err or (targets_500 and no_ligand_records)):
            err = dict(targets_err)
            err["error"] = (
                f"No GtoPdb disease found for disease_id={disease_id}. "
                f"{targets_err['error']}"
            )
            return err

        targets_list = targets if isinstance(targets, list) else []
        ligands_list = ligands if isinstance(ligands, list) else []

        data = {
            "diseaseId": disease_id,
            "diseaseTargets": targets_list,
            "diseaseLigands": ligands_list,
        }
        result: Dict[str, Any] = {
            "status": "success",
            "data": data,
            "disease_id": disease_id,
            "target_count": len(targets_list),
            "ligand_count": len(ligands_list),
        }
        notes = []
        if targets_err:
            notes.append("diseaseTargets unavailable for this disease.")
        if ligands_err:
            notes.append("diseaseLigands unavailable for this disease.")
        if notes:
            result["note"] = " ".join(notes)
        return result

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = None
        self._pending_ligand_id_filter = None  # Feature-38B-02: reset per call

        # Feature-65A: two composite tools fetch + merge a pair of per-ID endpoints
        # (structure+molecularProperties, diseaseTargets+diseaseLigands). They are
        # dispatched here by their endpoint marker rather than through _build_url,
        # which only handles single-endpoint tools.
        endpoint = self.tool_config.get("fields", {}).get("endpoint", "")
        if endpoint.endswith("/ligandProperties"):
            return self._run_ligand_properties(arguments)
        if endpoint.endswith("/diseaseAssociations"):
            return self._run_disease_associations(arguments)

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

        # Fix-R30-GtoPdb-type: resolve and validate the `type` filter, then take it
        # out of the upstream query. GtoPdb drops ?type= whenever ?name= is present
        # (see module header), so the only honest implementation is client-side
        # filtering against the record's own `type` field / boolean flags. The value
        # is pushed back into the query ONLY when GtoPdb honours it there, purely as
        # a bandwidth optimisation -- the client-side filter runs either way.
        _endpoint_path = endpoint.rstrip("/")
        _is_ligand_search = _endpoint_path.endswith("/ligands")
        _is_target_search = _endpoint_path.endswith("/targets")
        _type_filter = None
        _type_full_scan = False
        if _is_ligand_search or _is_target_search:
            _raw_type = None
            for _key in ("type", "ligand_type", "target_type"):
                if arguments.get(_key) not in (None, ""):
                    _raw_type = arguments[_key]
                    break
            if _raw_type is not None:
                _specs = _LIGAND_TYPE_SPECS if _is_ligand_search else _TARGET_TYPE_SPECS
                _spec = _specs.get(_norm_type(_raw_type))
                if _spec is None:
                    return _type_validation_error(
                        _raw_type,
                        _specs,
                        _LIGAND_TYPE_DEAD_VALUES if _is_ligand_search else {},
                        "ligand" if _is_ligand_search else "target",
                    )
                _type_filter = _spec
                arguments = dict(arguments)
                for _key in ("type", "ligand_type", "target_type"):
                    arguments.pop(_key, None)
                _name_present = any(
                    arguments.get(k)
                    for k in ("name", "query", "gene_symbol", "gene", "geneSymbol")
                )
                if not _name_present:
                    if _spec.server_value is not None:
                        arguments["type"] = _spec.server_value
                    else:
                        # No name and no server-side equivalent: we must pull the
                        # whole collection and filter it ourselves.
                        _type_full_scan = True

        # Fix-R30-GtoPdb-type: `approved` is a total no-op upstream -- verified,
        # /ligands?approved=true returns all 13856 ligands, identical to
        # ?approved=false and to no parameter at all. Strip it from the query and
        # apply it client-side against the record's `approved` boolean.
        _approved_requested = arguments.get("approved") if _is_ligand_search else None
        if _approved_requested is not None:
            arguments = dict(arguments)
            arguments.pop("approved", None)
            if _approved_requested is True and _type_filter is None:
                _name_present = any(
                    arguments.get(k) for k in ("name", "query", "gene_symbol", "gene")
                )
                if not _name_present:
                    # ?type=Approved is the one server-side filter GtoPdb honours
                    # for approval status; use it instead of pulling 13856 records.
                    arguments["type"] = "Approved"

        # Feature-46A-04: gene_symbol convenience parameter for GtoPdb_get_interactions.
        # Auto-resolve gene symbol → targetId so users don't need a separate
        # GtoPdb_search_targets call before querying interactions.
        # Fix-R4A-3: this resolution is only meaningful for the interactions
        # endpoints, which are addressed as /targets/{targetId}/interactions.
        # On the plain /targets endpoint the resolved targetId becomes a query
        # parameter that GtoPdb ignores, and `gene_symbol` was popped on the
        # way -- so GtoPdb_search_targets silently dropped the filter and
        # returned the unfiltered first 50 targets. There, `gene_symbol` maps
        # directly to GtoPdb's own ?geneSymbol= instead (see _build_url).
        gene_symbol = arguments.get("gene_symbol")
        if (
            gene_symbol
            and endpoint.endswith("/interactions")
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
            # Fix-R30-GtoPdb-type: a full-collection scan (type filter with no
            # server-side equivalent and no name search) pulls ~8 MB and takes
            # ~25 s, so it needs more headroom than the 30 s default.
            _req_timeout = 120 if _type_full_scan else self.timeout
            response = request_with_retry(
                self.session, "GET", url, timeout=_req_timeout, max_attempts=3
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

            # Fix-R30-GtoPdb-type: apply the `type` filter client-side. This runs
            # unconditionally when a type was requested -- including when the value
            # was also pushed server-side, where it is simply a no-op -- so the rows
            # returned always satisfy the filter the caller submitted.
            _type_scanned = _type_matched = None
            if _type_filter is not None and isinstance(data, list):
                _type_scanned = len(data)
                data = [x for x in data if _type_filter.matches(x)]
                _type_matched = len(data)

            # Fix-R30-GtoPdb-type: `approved=true` filtered client-side (no-op upstream).
            # `approved=false` remains "no filter", as this parameter has always been
            # documented ("approved drugs only (true) or all ligands (false/omit)").
            _approved_scanned = _approved_matched = None
            if _approved_requested is True and isinstance(data, list):
                _approved_scanned = len(data)
                data = [x for x in data if x.get("approved") is True]
                _approved_matched = len(data)

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

            # Fix-R30-GtoPdb-type: disclose that the filter was enforced here rather
            # than upstream, and how many records it removed, so a shrunken result
            # set is never mistaken for a thin database.
            if _type_filter is not None and _type_scanned is not None:
                result["type_filter"] = {
                    "requested": _type_filter.canonical,
                    "enforced": "client-side",
                    "records_scanned": _type_scanned,
                    "records_matched": _type_matched,
                    "note": (
                        "GtoPdb's own ?type= parameter is unreliable -- it is silently "
                        "ignored whenever a name search is also supplied, and it returns "
                        "HTTP 404 for several values its documentation lists -- so "
                        "ToolUniverse filters the returned records itself."
                    ),
                }
            if _approved_requested is True and _approved_scanned is not None:
                result["approved_filter"] = {
                    "enforced": "client-side",
                    "records_scanned": _approved_scanned,
                    "records_matched": _approved_matched,
                    "note": (
                        "GtoPdb's ?approved= parameter is a no-op (it returns the full "
                        "ligand set either way), so ToolUniverse filters on each "
                        "record's 'approved' boolean instead."
                    ),
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
                    # Fix-R30-GtoPdb-type: these merged-in extras bypass the main
                    # request, so they must pass the same client-side type filter --
                    # otherwise the filter leaks right back out here.
                    if extra and _type_filter is not None:
                        extra = [t for t in extra if _type_filter.matches(t)]
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
