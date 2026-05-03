"""
CIViC (Clinical Interpretation of Variants in Cancer) API tool for ToolUniverse.

CIViC is a community knowledgebase for expert-curated interpretations of variants
in cancer. It provides clinical evidence levels and interpretations.

API Documentation: https://civicdb.org/api
GraphQL Endpoint: https://civicdb.org/api/graphql
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for CIViC
CIVIC_BASE_URL = "https://civicdb.org/api"
CIVIC_GRAPHQL_URL = f"{CIVIC_BASE_URL}/graphql"


@register_tool("CIViCTool")
class CIViCTool(BaseTool):
    """
    Tool for querying CIViC (Clinical Interpretation of Variants in Cancer).

    CIViC provides:
    - Expert-curated cancer variant interpretations
    - Clinical evidence levels
    - Drug-variant associations
    - Disease-variant associations

    Uses GraphQL API. No authentication required. Free for academic/research use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.query_template: str = fields.get("query", "")
        self.operation_name: Optional[str] = fields.get("operation_name")
        self.timeout: int = tool_config.get("timeout", 30)
        # array_wrap: maps argument name -> GraphQL variable name, wrapping string in a list
        # e.g. {"gene_symbol": "entrezSymbols"} means arguments["gene_symbol"] -> variables["entrezSymbols"] = [value]
        self.array_wrap: Dict[str, str] = fields.get("array_wrap", {})
        # param_map: maps argument name -> GraphQL variable name (without list wrapping)
        # e.g. {"therapy": "therapyName"} means arguments["therapy"] -> variables["therapyName"] = value
        self.param_map: Dict[str, str] = fields.get("param_map", {})
        # variable_defaults: applies default values for GraphQL variables not supplied by user
        # e.g. {"status": "ACCEPTED"} sets status=ACCEPTED when not explicitly provided
        self.variable_defaults: Dict[str, Any] = fields.get("variable_defaults", {})

    def _build_graphql_query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build GraphQL query from template and arguments."""
        query = self.query_template

        # GraphQL queries use variables, not string replacement
        # Extract variable names from query (e.g., $limit, $gene_id)
        import re

        var_matches = re.findall(r"\$(\w+)", query)

        # Map arguments to GraphQL variables
        # GraphQL variable names match argument names in our config
        variables = {}
        for var_name in var_matches:
            # Check if argument exists (variable name matches argument name)
            if var_name in arguments:
                variables[var_name] = arguments[var_name]

        # Handle array_wrap: convert string arguments to lists for array-typed GraphQL variables
        for arg_name, var_name in self.array_wrap.items():
            if arg_name in arguments and arguments[arg_name] is not None:
                val = arguments[arg_name]
                variables[var_name] = [val] if not isinstance(val, list) else val

        # Handle param_map: rename argument names to GraphQL variable names
        # Only sets the variable if not already set by direct name match
        for arg_name, var_name in self.param_map.items():
            if arg_name in arguments and arguments[arg_name] is not None:
                if var_name not in variables:
                    variables[var_name] = arguments[arg_name]

        # Apply variable_defaults: set defaults for variables not already set by arguments
        for var_name, default_val in self.variable_defaults.items():
            if var_name not in variables and var_name in var_matches:
                variables[var_name] = default_val

        payload = {"query": query}

        if self.operation_name:
            payload["operationName"] = self.operation_name

        if variables:
            payload["variables"] = variables

        return payload

    def _lookup_gene_id(self, gene_name: str) -> Optional[int]:
        """Look up CIViC gene ID by gene symbol via GraphQL."""
        payload = {
            "query": "query GetGenes($entrezSymbols: [String!]) { genes(entrezSymbols: $entrezSymbols) { nodes { id name } } }",
            "variables": {"entrezSymbols": [gene_name.upper()]},
        }
        try:
            resp = requests.post(
                CIVIC_GRAPHQL_URL,
                json=payload,
                timeout=10,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            data = resp.json().get("data", {})
            nodes = data.get("genes", {}).get("nodes", [])
            if nodes:
                return nodes[0]["id"]
        except Exception:
            pass
        return None

    def _get_variants_for_gene_id(
        self, gene_id: int, limit: int = 500
    ) -> Dict[str, Any]:
        """Fetch variants for a given CIViC gene_id via GraphQL.

        Feature-45A-01: CIViC API caps variants(first:) at 100 server-side.
        Use cursor-based pagination to fetch all variants up to `limit`.
        """
        # Feature-41A-02: include feature { id name } so callers can distinguish
        # e.g. KRAS G12C (ID 78) from NRAS G12C (ID 897).
        PAGINATED_QUERY = (
            "query GetVariantsByGene($gene_id: Int!, $page_size: Int, $after: String) { "
            "gene(id: $gene_id) { id name variants(first: $page_size, after: $after) { "
            "nodes { id name ... on GeneVariant { feature { id name } } } "
            "pageInfo { hasNextPage endCursor } } } }"
        )
        PAGE_SIZE = 100  # CIViC server max per page
        all_nodes: list = []
        cursor = None
        gene_meta: Dict[str, Any] = {}
        try:
            while len(all_nodes) < limit:
                fetch = min(PAGE_SIZE, limit - len(all_nodes))
                variables: Dict[str, Any] = {
                    "gene_id": gene_id,
                    "page_size": fetch,
                }
                if cursor:
                    variables["after"] = cursor
                resp = requests.post(
                    CIVIC_GRAPHQL_URL,
                    json={
                        "query": PAGINATED_QUERY,
                        "operationName": "GetVariantsByGene",
                        "variables": variables,
                    },
                    timeout=30,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                resp_data = resp.json().get("data", {})
                gene_data = resp_data.get("gene", {})
                if not gene_meta:
                    gene_meta = {
                        "id": gene_data.get("id"),
                        "name": gene_data.get("name"),
                    }
                variants_block = gene_data.get("variants", {})
                nodes = variants_block.get("nodes", [])
                all_nodes.extend(nodes)
                page_info = variants_block.get("pageInfo", {})
                if not page_info.get("hasNextPage"):
                    break
                cursor = page_info.get("endCursor")
                if not cursor:
                    break
            # Feature-46B-01: deduplicate by variant ID (prevents pagination overlap artifacts)
            seen_ids: set = set()
            deduped: list = []
            name_count: Dict[str, int] = {}
            for node in all_nodes:
                node_id = node.get("id")
                if node_id not in seen_ids:
                    seen_ids.add(node_id)
                    # Strip leading/trailing whitespace from variant names (API artifact)
                    if "name" in node and isinstance(node["name"], str):
                        node["name"] = node["name"].strip()
                    deduped.append(node)
                    name = node.get("name", "")
                    name_count[name] = name_count.get(name, 0) + 1
            all_nodes = deduped
            # Flag variant names that appear multiple times (distinct CIViC records)
            duplicate_names = [n for n, c in name_count.items() if c > 1]
            # Reassemble in the original single-request structure
            data = {
                "gene": {
                    **gene_meta,
                    "variants": {"nodes": all_nodes[:limit]},
                }
            }
            metadata: Dict[str, Any] = {"source": "CIViC", "format": "GraphQL"}
            if duplicate_names:
                metadata["note"] = (
                    f"Multiple distinct CIViC variant records share the same name(s): "
                    f"{', '.join(duplicate_names[:5])}. These are separate entries with different "
                    f"IDs (e.g., from different molecular profiles or evidence contexts) — "
                    f"use the variant ID to distinguish them."
                )
            return {
                "status": "success",
                "data": data,
                "metadata": metadata,
            }
        except Exception as e:
            return {"status": "error", "error": f"CIViC API request failed: {str(e)}"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CIViC GraphQL API call."""
        tool_name = self.tool_config.get("name", "")

        # civic_get_variants_by_gene: resolve gene_name → gene_id if needed
        if tool_name == "civic_get_variants_by_gene":
            if not arguments.get("gene_id"):
                gene_name = (
                    arguments.get("gene_name")
                    or arguments.get("gene")
                    or arguments.get("gene_symbol")  # Feature-47A-01
                    or arguments.get("query")
                )
                if not gene_name:
                    return {
                        "status": "error",
                        "error": "gene_id or gene_name is required for civic_get_variants_by_gene",
                    }
                gene_id = self._lookup_gene_id(gene_name)
                if gene_id is None:
                    return {
                        "status": "error",
                        "error": f"Gene '{gene_name}' not found in CIViC database",
                    }
                arguments = dict(arguments)
                arguments["gene_id"] = gene_id
            return self._get_variants_for_gene_id(
                arguments["gene_id"], arguments.get("limit", 500)
            )

        # Feature-40B-01: civic_search_evidence_items — warn on unsupported gene/variant params.
        # Feature-41A-03: also catch molecular_profile_id (integer) — no GraphQL binding.
        # Feature-61A-001: extend to catch ANY unrecognized parameter that would be silently
        # ignored, causing unfiltered evidence dumps (e.g. description="ESR1", gene_id=38).
        if tool_name == "civic_search_evidence_items":
            _known_params = {
                "molecular_profile",
                "disease",
                "disease_name",
                "therapy",
                "status",
                "limit",
                "evidence_type",
                "significance",
                "evidence_direction",
                "after",
                "operation",
            }
            # Also include names reachable via param_map and array_wrap
            _known_params.update(self.param_map.keys())
            _known_params.update(self.array_wrap.keys())
            # Legacy unsupported params with specific hints
            legacy_unsupported = [
                p
                for p in ("gene", "variant", "gene_name", "molecular_profile_id")
                if arguments.get(p)
            ]
            # Any other unrecognized params
            other_unknown = [
                p
                for p in arguments
                if p not in _known_params
                and p not in ("gene", "variant", "gene_name", "molecular_profile_id")
            ]
            if legacy_unsupported:
                gene = arguments.get("gene") or arguments.get("gene_name")
                variant = arguments.get("variant")
                mol_id = arguments.get("molecular_profile_id")
                profile_hint = ""
                if gene and variant:
                    profile_hint = f' Try: molecular_profile="{gene} {variant}"'
                elif gene:
                    profile_hint = f' Try: molecular_profile="{gene}"'
                elif mol_id:
                    profile_hint = (
                        f" For integer ID filtering, use civic_get_evidence_item with the "
                        f"evidence ID, or civic_get_variant with the variant ID."
                    )
                return {
                    "status": "error",
                    "error": f"Unsupported parameter(s) for civic_search_evidence_items: {', '.join(legacy_unsupported)}. "
                    "Supported filters: molecular_profile (string, e.g. 'BRAF V600E'), "
                    "therapy, disease, status, evidence_type (PREDICTIVE, DIAGNOSTIC, "
                    "PROGNOSTIC, PREDISPOSING, ONCOGENIC, FUNCTIONAL)." + profile_hint,
                }
            if other_unknown:
                return {
                    "status": "error",
                    "error": (
                        f"Unrecognized parameter(s) for civic_search_evidence_items:"
                        f" {', '.join(sorted(other_unknown))}. These are silently ignored by"
                        f" the CIViC GraphQL API, returning unfiltered results."
                        f" Supported filters: molecular_profile, disease, therapy, status,"
                        f" evidence_type, significance, limit."
                    ),
                }

        # civic_search_variants: if gene/gene_name provided, look up gene_id then get variants.
        # Feature-41A-01: also handle combined gene+query — get gene variants, filter client-side.
        if tool_name == "civic_search_variants":
            gene_name = (
                arguments.get("gene")
                or arguments.get("gene_name")
                or arguments.get("gene_symbol")  # Feature-47A-01
            )
            # Feature-53B-004: variant_name parameter was silently ignored — only "query" was
            # checked. Users naturally pass variant_name='S249C' expecting it to filter
            # variants client-side, just like query='S249C' does.
            # Feature-54A-005: when BOTH query and variant_name are provided and differ,
            # silently dropping one is confusing. Apply AND logic and add a note.
            raw_query = arguments.get("query")
            raw_variant_name = arguments.get("variant_name") or arguments.get("variant")
            # Feature-66A-002: strip leading/trailing whitespace from query/variant inputs
            if raw_query and isinstance(raw_query, str):
                raw_query = raw_query.strip()
            if raw_variant_name and isinstance(raw_variant_name, str):
                raw_variant_name = raw_variant_name.strip()
            _both_provided = (
                raw_query and raw_variant_name and raw_query != raw_variant_name
            )
            if _both_provided:
                # AND logic: we'll filter on both below
                query_term = raw_query
                _secondary_term = raw_variant_name
            else:
                query_term = raw_query or raw_variant_name
                _secondary_term = None
            # Feature-66A-001: variant_name was silently ignored on the no-gene GraphQL path
            # because _build_graphql_query only reads arguments["query"]. Forward query_term
            # into arguments["query"] so the no-gene path correctly filters by variant name.
            if query_term and not arguments.get("query"):
                arguments = dict(arguments)
                arguments["query"] = query_term
            if gene_name:
                gene_id = self._lookup_gene_id(gene_name)
                if gene_id is None:
                    return {
                        "status": "error",
                        "error": f"Gene '{gene_name}' not found in CIViC database",
                    }
                # Feature-43B-01: when gene+query combined, always fetch up to 200 variants
                # before client-side filtering; the user's limit applies to the OUTPUT,
                # not the pre-filter fetch — otherwise alphabetically early variants may
                # block clinically important ones (e.g. FLT3 ITD at position >10).
                user_limit = arguments.get("limit")
                fetch_limit = 500 if query_term else (user_limit or 500)
                result = self._get_variants_for_gene_id(gene_id, fetch_limit)
                # If query also provided, filter returned variants by name client-side
                if query_term and isinstance(result.get("data"), dict):
                    gene_data = result["data"].get("gene", {})
                    nodes = gene_data.get("variants", {}).get("nodes", [])
                    q_lower = query_term.lower()
                    filtered = [
                        v for v in nodes if q_lower in v.get("name", "").lower()
                    ]
                    # Feature-54A-005: AND logic when both query and variant_name provided
                    if _secondary_term:
                        sec_lower = _secondary_term.lower()
                        filtered = [
                            v
                            for v in filtered
                            if sec_lower in v.get("name", "").lower()
                        ]
                        result["filter_note"] = (
                            f"Both query='{raw_query}' and variant_name='{raw_variant_name}' "
                            f"were provided; applied AND logic (variants matching both terms)."
                        )
                    # Truncate to user-requested limit AFTER filtering
                    if user_limit:
                        filtered = filtered[:user_limit]
                    gene_data.get("variants", {})["nodes"] = filtered
                    # Feature-48B-02: recompute duplicate names among filtered results only.
                    # The metadata.note from _get_variants_for_gene_id cites duplicates from ALL
                    # gene variants; after filtering, only filtered duplicates are relevant.
                    if "metadata" in result:
                        filtered_name_count: Dict[str, int] = {}
                        for v in filtered:
                            n = v.get("name", "")
                            filtered_name_count[n] = filtered_name_count.get(n, 0) + 1
                        filtered_dups = [
                            n for n, c in filtered_name_count.items() if c > 1
                        ]
                        if filtered_dups:
                            result["metadata"]["note"] = (
                                f"Multiple distinct CIViC variant records share the same name(s): "
                                f"{', '.join(filtered_dups[:5])}. These are separate entries — "
                                f"use the variant ID to distinguish them."
                            )
                        else:
                            result["metadata"].pop("note", None)
                    # Feature-43A-04: when gene+query filter returns empty, add a helpful note.
                    # Feature-44A-01: also provide gene-specific alternative query terms for
                    # common oncology terms that CIViC names differently (e.g., "truncating"
                    # → use "LOSS" or "Loss-of-function" for BRCA1/BRCA2 in CIViC).
                    if not filtered:
                        fusion_hint = ""
                        alt_hint = ""
                        if "fusion" in q_lower:
                            # Feature-56A-006: BICC1 was hardcoded as an example but it's only a
                            # real partner for FGFR2, not other genes. Use a validated lookup table.
                            _FUSION_EXAMPLES = {
                                "ALK": "EML4",
                                "ROS1": "CD74",
                                "RET": "KIF5B",
                                "NTRK1": "TPM3",
                                "FGFR2": "BICC1",
                                "FGFR3": "TACC3",
                                "PDGFRA": "FIP1L1",
                                "BCR": "ABL1",
                                "ABL1": "BCR",
                            }
                            _partner = _FUSION_EXAMPLES.get(gene_name, "PARTNER")
                            _example = (
                                f"'{_partner}::{gene_name} Fusion'"
                                if _partner != "PARTNER"
                                else f"'{gene_name}::GENE2 Fusion'"
                            )
                            fusion_hint = (
                                f" CIViC stores fusion events as molecular profiles "
                                f"rather than gene variants. Try civic_search_evidence_items "
                                f"with molecular_profile='{gene_name}::PARTNER Fusion' "
                                f"(e.g., {_example})."
                            )
                        # Provide alternative query suggestions for common terms CIViC names differently
                        _alt_suggestions: Dict[str, str] = {
                            "truncat": "Try query='LOSS' or query='Loss-of-function' — CIViC uses these terms for truncating/LOF variants.",
                            "loss of function": "Try query='LOSS' or query='Loss-of-function'.",
                            "lof": "Try query='LOSS' or query='Loss-of-function'.",
                            "amplif": "Try query='AMPLIFICATION'.",
                            "delet": "Try query='DELETION' or query='LOSS'.",
                            "overexpress": "Try query='OVEREXPRESSION'.",
                            "missense": "Try query='V600E' or another specific amino acid change — CIViC indexes by specific variant names.",
                        }
                        for term, suggestion in _alt_suggestions.items():
                            if term in q_lower:
                                alt_hint = f" {suggestion}"
                                break
                        # Show available variant names to guide the user
                        available_names = [v.get("name", "") for v in nodes[:10]]
                        available_str = (
                            f" Available {gene_name} variant names include: {', '.join(available_names[:8])}."
                            if available_names
                            else ""
                        )
                        result["note"] = (
                            f"No variants found matching '{query_term}' in {gene_name}."
                            + fusion_hint
                            + alt_hint
                            + available_str
                        )
                return result

        # Track input normalizations to disclose them in the result (Feature-55A-008).
        _therapy_normalized_from = None
        _mp_normalized_from = None

        # Feature-53B-002: CIViC therapy names are case-sensitive (stored as Title Case, e.g.,
        # "Erdafitinib" not "erdafitinib"). Auto-normalize to Title Case when the input is
        # entirely lowercase or uppercase, to avoid silent empty results from case mismatches.
        # Feature-63B-002: CIViC status uses a strict GraphQL enum (ACCEPTED, SUBMITTED, etc.)
        # that requires uppercase. Normalize status to uppercase to prevent enum validation
        # errors when users pass lowercase/mixed-case values like "accepted".
        if tool_name == "civic_search_evidence_items":
            therapy = arguments.get("therapy")
            if therapy and isinstance(therapy, str):
                if therapy == therapy.lower() or therapy == therapy.upper():
                    _therapy_normalized_from = therapy
                    arguments = dict(arguments)
                    arguments["therapy"] = therapy.title()
            status_val = arguments.get("status")
            if (
                status_val
                and isinstance(status_val, str)
                and status_val != status_val.upper()
            ):
                arguments = dict(arguments)
                arguments["status"] = status_val.upper()

        # Feature-55B-005: CIViC uses double-colon notation for fusion molecular profiles
        # (e.g., "BCR::ABL1 Fusion", "EML4::ALK Fusion"). Users often write hyphenated
        # fusions (e.g., "BCR-ABL1 Fusion") which silently returns 0 results.
        # Feature-56A-001: the original regex matched mutation notation too (e.g., EGFR-T790M,
        # BRAF-V600E, KRAS-G12C) because T790M/V600E/G12C start with an uppercase letter.
        # Fix: skip normalization when the second part matches HGVS protein-change format
        # (single uppercase letter + digits + uppercase letter/asterisk, e.g. T790M, G12C).
        if tool_name in ("civic_search_evidence_items", "civic_search_variants"):
            import re as _re

            mol_profile = arguments.get("molecular_profile")
            if mol_profile and isinstance(mol_profile, str):

                def _maybe_fuse(m: "_re.Match") -> str:
                    """Replace GENE1-GENE2 with GENE1::GENE2, but not GENE-MutationNotation."""
                    second = m.group(2)
                    # Protein-change notation: single letter + digits + letter/asterisk (e.g. T790M)
                    if _re.match(r"^[A-Z]\d+[A-Z*]?$", second):
                        return m.group(0)  # leave unchanged
                    return m.group(1) + "::" + second

                normalized_mp = _re.sub(
                    r"\b([A-Z][A-Z0-9]*)-([A-Z][A-Z0-9]+)\b",
                    _maybe_fuse,
                    mol_profile,
                )
                if normalized_mp != mol_profile:
                    _mp_normalized_from = mol_profile
                    arguments = dict(arguments)
                    arguments["molecular_profile"] = normalized_mp

        try:
            # Build GraphQL query
            payload = self._build_graphql_query(arguments)

            # Make GraphQL request
            response = requests.post(
                CIVIC_GRAPHQL_URL,
                json=payload,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/CIViC",
                },
            )

            response.raise_for_status()
            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                return {
                    "status": "error",
                    "error": "GraphQL query errors",
                    "errors": data["errors"],
                    "query": arguments,
                }

            result = {
                "status": "success",
                "data": data.get("data", {}),
                "metadata": {
                    "source": "CIViC (Clinical Interpretation of Variants in Cancer)",
                    "format": "GraphQL",
                    "endpoint": CIVIC_GRAPHQL_URL,
                },
            }

            # Feature-55A-008 / Feature-55B-005: disclose any input normalizations applied.
            _norm_parts = []
            if _therapy_normalized_from:
                _norm_parts.append(
                    f"therapy '{_therapy_normalized_from}' → '{arguments.get('therapy')}' (CIViC uses Title Case)"
                )
            if _mp_normalized_from:
                _norm_parts.append(
                    f"molecular_profile '{_mp_normalized_from}' → '{arguments.get('molecular_profile')}'"
                    " (CIViC uses double-colon '::' for fusion gene pairs)"
                )
            if _norm_parts:
                result["normalization_note"] = (
                    "Input auto-normalized: " + "; ".join(_norm_parts) + "."
                )

            # Feature-50A-001: warn when civic_search_evidence_items combined
            # molecular_profile+disease filter returns 0 results.
            # Feature-52A-004: auto-probe with molecular_profile only to surface the actual
            # CIViC disease names that have evidence, so users can correct the disease name.
            if tool_name == "civic_search_evidence_items":
                mol_profile = arguments.get("molecular_profile")
                disease = arguments.get("disease") or arguments.get("disease_name")

                # Feature-63B-002: CIViC GraphQL uses substring/contains matching for
                # molecularProfileName — compound profiles like "BRAF V600E OR KIAA1549::BRAF
                # Fusion" are returned when filtering for "BRAF V600E" because the substring
                # matches. Disclose non-exact matches so users can confirm relevance.
                if mol_profile:
                    _ev_nodes_exact_check = (
                        result.get("data", {}).get("evidenceItems", {}).get("nodes", [])
                    )
                    if _ev_nodes_exact_check:
                        _mp_lower = mol_profile.lower()
                        _non_exact_profiles = [
                            node.get("molecularProfile", {}).get("name", "")
                            for node in _ev_nodes_exact_check
                            if node.get("molecularProfile", {}).get("name", "").lower()
                            != _mp_lower
                            and node.get("molecularProfile", {}).get("name", "")
                        ]
                        if _non_exact_profiles:
                            _unique_non_exact = sorted(set(_non_exact_profiles))[:3]
                            result["molecular_profile_match_note"] = (
                                f"CIViC uses substring/contains matching for molecular_profile "
                                f"— results include any profile whose name contains "
                                f"'{mol_profile}' as a substring, not only exact matches. "
                                f"Non-exact profiles in these results: "
                                + ", ".join(f"'{p}'" for p in _unique_non_exact)
                                + ". Review the molecularProfile.name field in each result to "
                                "confirm clinical relevance."
                            )

                # Feature-57A-005: fire when ANY disease filter is set (not just mol_profile+disease)
                if disease:
                    evidence_nodes = (
                        result.get("data", {}).get("evidenceItems", {}).get("nodes", [])
                    )
                    if len(evidence_nodes) == 0:
                        # Auto-probe: re-run without disease filter to find actual disease names
                        actual_diseases: list = []
                        probe_nodes: list = []
                        try:
                            probe_args = {
                                k: v
                                for k, v in arguments.items()
                                if k not in ("disease", "disease_name")
                            }
                            probe_args["limit"] = 50
                            probe_payload = self._build_graphql_query(probe_args)
                            probe_resp = requests.post(
                                CIVIC_GRAPHQL_URL,
                                json=probe_payload,
                                timeout=self.timeout,
                                headers={
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                },
                            )
                            probe_nodes = (
                                probe_resp.json()
                                .get("data", {})
                                .get("evidenceItems", {})
                                .get("nodes", [])
                            )
                            actual_diseases = sorted(
                                {
                                    node.get("disease", {}).get("name", "")
                                    for node in probe_nodes
                                    if node.get("disease", {}).get("name")
                                }
                            )
                        except Exception:
                            pass

                        # Build context string for hint message
                        therapy = arguments.get("therapy")
                        if mol_profile:
                            _ctx = f"molecular_profile='{mol_profile}'"
                        elif therapy:
                            _ctx = f"therapy='{therapy}'"
                        else:
                            _ctx = "the specified filter"

                        if actual_diseases:
                            disease_hint = (
                                f" CIViC has {len(probe_nodes)} evidence items for "
                                f"{_ctx} across these diseases: "
                                + ", ".join(f"'{d}'" for d in actual_diseases[:10])
                                + ". Use one of these exact disease names."
                            )
                        else:
                            disease_hint = (
                                f" Try retrying with {_ctx} "
                                "(remove the disease filter) to see all evidence."
                            )
                        # Feature-59A-001: disclose ACCEPTED filter that may be hiding evidence
                        _status_used = arguments.get(
                            "status", self.variable_defaults.get("status", "ACCEPTED")
                        )
                        _status_note = ""
                        if str(_status_used).upper() == "ACCEPTED":
                            _status_note = (
                                " CIViC defaults to ACCEPTED evidence only — "
                                "add status='SUBMITTED' to include pre-review evidence."
                            )
                        result["warning"] = (
                            f"No evidence items found for {_ctx} "
                            f"AND disease='{disease}'. CIViC applies AND logic across all "
                            "filters, and disease names must match CIViC's exact taxonomy "
                            "(e.g., 'Lung Non-small Cell Carcinoma' not 'NSCLC' or "
                            "'Non-small Cell Lung Carcinoma', "
                            "'Chronic Myelogenous Leukemia, BCR-ABL1+' not 'CML', "
                            "'Pancreatic Ductal Carcinoma' not 'Pancreatic Adenocarcinoma')."
                            + disease_hint
                            + _status_note
                        )

                # Feature-56A-002: when molecular_profile alone returns 0 results (no disease,
                # no therapy filter), warn — especially if input was auto-normalized (fusion fix
                # may have converted a mutation like EGFR-T790M to EGFR::T790M incorrectly).
                therapy = arguments.get("therapy")
                if mol_profile and not disease and not therapy:
                    evidence_nodes = (
                        result.get("data", {}).get("evidenceItems", {}).get("nodes", [])
                    )
                    if len(evidence_nodes) == 0:
                        mp_warn = f"No evidence items found for molecular_profile='{mol_profile}'."
                        # Feature-59A-001: ACCEPTED filter may be hiding evidence. Disclose the active
                        # status filter so users know to try status='SUBMITTED' if evidence exists
                        # only in pre-review form (common for rare cancers and newer variants).
                        _status_used = arguments.get(
                            "status", self.variable_defaults.get("status", "ACCEPTED")
                        )
                        if str(_status_used).upper() == "ACCEPTED":
                            mp_warn += (
                                " CIViC defaults to ACCEPTED (peer-reviewed) evidence only. "
                                "If this variant has recent or emerging evidence it may be "
                                "SUBMITTED (pre-review) — add status='SUBMITTED' to include it."
                            )
                        if _mp_normalized_from:
                            mp_warn += (
                                f" Note: your input '{_mp_normalized_from}' was auto-normalized"
                                f" to '{mol_profile}' as a gene fusion. If this is a point"
                                " mutation (e.g., EGFR T790M), use space-separated notation"
                                " instead (CIViC does not use hyphens for mutations)."
                            )
                        elif _re.search(
                            r"\b[A-Z][A-Z0-9]*-[A-Z]\d+[A-Z*]?\b", mol_profile
                        ):
                            # Input looks like GENE-Mutation (e.g., EGFR-T790M) — not normalized
                            # because we correctly identified it as a mutation, not a fusion.
                            # Suggest space-separated notation which CIViC actually uses.
                            space_form = mol_profile.replace("-", " ", 1)
                            mp_warn += (
                                f" If '{mol_profile}' is a point mutation, try"
                                f" molecular_profile='{space_form}' (CIViC uses"
                                " 'GENE Mutation' with a space, not a hyphen)."
                            )
                        result["warning"] = mp_warn

                # Feature-53B-002: warn when molecular_profile+therapy returns 0 results.
                # Feature-54A-001: auto-probe available therapies for the molecular profile
                # so users can identify the correct exact therapy name from CIViC.
                if mol_profile and therapy and not disease:
                    evidence_nodes = (
                        result.get("data", {}).get("evidenceItems", {}).get("nodes", [])
                    )
                    if len(evidence_nodes) == 0:
                        # Auto-probe: re-run without therapy filter to find actual therapy names
                        available_therapies: list = []
                        try:
                            probe_args = {
                                k: v
                                for k, v in arguments.items()
                                if k not in ("therapy",)
                            }
                            probe_args["limit"] = 50
                            probe_payload = self._build_graphql_query(probe_args)
                            probe_resp = requests.post(
                                CIVIC_GRAPHQL_URL,
                                json=probe_payload,
                                timeout=self.timeout,
                                headers={
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                },
                            )
                            probe_nodes = (
                                probe_resp.json()
                                .get("data", {})
                                .get("evidenceItems", {})
                                .get("nodes", [])
                            )
                            available_therapies = sorted(
                                {
                                    t.get("name", "")
                                    for node in probe_nodes
                                    for t in node.get("therapies", [])
                                    if t.get("name")
                                }
                            )
                        except Exception:
                            pass

                        if available_therapies:
                            therapy_hint = (
                                f" CIViC has evidence for '{mol_profile}' with these "
                                f"therapies: "
                                + ", ".join(f"'{t}'" for t in available_therapies[:10])
                                + ". Use one of these exact therapy names."
                            )
                        else:
                            therapy_hint = (
                                f" Try removing the therapy filter and searching only by "
                                f"molecular_profile='{mol_profile}' to see all available evidence."
                            )
                        result["therapy_warning"] = (
                            f"No evidence items found for molecular_profile='{mol_profile}' "
                            f"AND therapy='{therapy}'. CIViC therapy names are exact-match "
                            "and case-sensitive (stored as Title Case, e.g., 'Erdafitinib', "
                            "'Trastuzumab', 'Lapatinib'). The therapy name was auto-normalized "
                            "to Title Case, but may still not match CIViC's exact entry."
                            + therapy_hint
                        )

            # Feature-67B-002: detect "GENE VARIANT" combined input in variant_name returning
            # empty — CIViC stores variants without gene prefix (e.g., "L858R" not "EGFR L858R").
            if tool_name == "civic_search_variants":
                _variant_nodes = (
                    result.get("data", {}).get("variants", {}).get("nodes", [])
                )
                if len(_variant_nodes) == 0:
                    import re as _re_vn

                    _raw_vn = (
                        arguments.get("variant_name")
                        or arguments.get("variant")
                        or arguments.get("query")
                        or ""
                    )
                    if _raw_vn and _re_vn.match(r"^[A-Z][A-Z0-9]+\s+\S", str(_raw_vn)):
                        _vn_parts = str(_raw_vn).split(None, 1)
                        result["hint"] = (
                            f"No variants found for '{_raw_vn}'. CIViC stores variants "
                            f"without the gene prefix — try gene_name='{_vn_parts[0]}' "
                            f"with variant_name='{_vn_parts[1]}'."
                        )

            # Feature-60A-001: when evidence items ARE returned under ACCEPTED-only filter,
            # disclose the filter so users know SUBMITTED items may also exist.
            if tool_name == "civic_search_evidence_items":
                evidence_nodes = (
                    result.get("data", {}).get("evidenceItems", {}).get("nodes", [])
                )
                if len(evidence_nodes) > 0:
                    _status_used = arguments.get(
                        "status", self.variable_defaults.get("status", "ACCEPTED")
                    )
                    if str(_status_used).upper() == "ACCEPTED":
                        result["status_note"] = (
                            f"Showing {len(evidence_nodes)} ACCEPTED (peer-reviewed) evidence"
                            " items. Additional SUBMITTED (pre-review) items may exist —"
                            " add status='SUBMITTED' to include them."
                        )

            return result

        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"CIViC API request failed: {str(e)}",
                "query": arguments,
            }
        except ValueError as e:
            return {"status": "error", "error": str(e), "query": arguments}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "query": arguments,
            }
