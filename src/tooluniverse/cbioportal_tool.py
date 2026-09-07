import re
import requests
from typing import Any, Callable, Dict, Optional
from urllib.parse import quote, urlencode, urlsplit, urlunsplit, parse_qsl
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("CBioPortalRESTTool")
class CBioPortalRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.cbioportal.org/api"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ToolUniverse/1.0",
            }
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        url = self.tool_config["fields"]["endpoint"]
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    # cBioPortal paginates with `pageSize`/`pageNumber` query params.
    _PAGE_SIZE_RE = re.compile(r"[?&]pageSize=(\d+)", re.IGNORECASE)
    _PAGE_NUMBER_RE = re.compile(r"[?&]pageNumber=(\d+)", re.IGNORECASE)

    @staticmethod
    def _as_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _fetch_total_count(self, url: str) -> Optional[int]:
        """Ask cBioPortal how many records the query matches in total.

        cBioPortal only reports the true total through `projection=META`,
        which answers with an empty body plus a `Total-Count` header.
        Verified live: `GET /api/studies?projection=META` -> `Total-Count:
        539` while the tool's default `pageSize=20` body carries 20
        records. The paging params are stripped from the probe because the
        `/studies` endpoint clamps the META count to `pageSize`
        (`/api/studies?pageSize=20&projection=META` -> `Total-Count: 20`),
        which would defeat the whole point of asking.

        Returns None when the total cannot be established, so callers can
        say "unknown" rather than invent a number.
        """
        parts = urlsplit(url)
        query = [
            (key, value)
            for key, value in parse_qsl(parts.query)
            if key.lower() not in ("pagesize", "pagenumber", "projection")
        ]
        query.append(("projection", "META"))
        probe_url = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )
        try:
            response = self.session.get(probe_url, timeout=self.timeout)
        except requests.RequestException:
            return None
        if response.status_code != 200:
            return None
        raw = response.headers.get("Total-Count") or response.headers.get(
            "X-Total-Count"
        )
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _truncation_fields(
        *, returned: int, offset: int, total: Optional[int], how_to_get_more: str
    ) -> Dict[str, Any]:
        """Build the disclosure keys that tell a slice apart from a full set.

        `count` stays the number of records actually returned;
        `total_available` is always the upstream total for the same query,
        so neither field's meaning depends on whether the page limit
        happened to bind.
        """
        if total is None:
            return {
                "total_available": None,
                "truncated": True,
                "truncation_note": (
                    f"Returned {returned} record(s) starting at offset {offset}. "
                    "The page came back full, so more records may exist upstream, "
                    "but cBioPortal did not report the total for this query. "
                    f"{how_to_get_more}"
                ),
            }
        if offset + returned >= total:
            return {"total_available": total, "truncated": False}
        return {
            "total_available": total,
            "truncated": True,
            "truncation_note": (
                f"Returned {returned} of {total} matching record(s), starting at "
                f"offset {offset}. This is a page, not the complete set — records "
                f"absent here may still exist upstream. {how_to_get_more}"
            ),
        }

    def _disclose_generic_truncation(
        self, result: Dict[str, Any], url: str
    ) -> Dict[str, Any]:
        """Attach total/truncation disclosure to a plain paginated GET result.

        Endpoints whose URL carries no `pageSize` return their whole set and
        are left untouched. When the returned page is short, the set is known
        to be exhausted without spending a second request.
        """
        data = result.get("data")
        if not isinstance(data, list):
            return result
        size_match = self._PAGE_SIZE_RE.search(url)
        if not size_match:
            return result

        page_size = int(size_match.group(1))
        number_match = self._PAGE_NUMBER_RE.search(url)
        offset = page_size * int(number_match.group(1) if number_match else 0)
        returned = len(data)

        if returned < page_size:
            total: Optional[int] = offset + returned
        else:
            total = self._fetch_total_count(url)

        props = self.tool_config.get("parameter", {}).get("properties", {})
        size_param = "limit" if "limit" in props else "page_size"
        page_param = "page_number" if "page_number" in props else None
        hint = f"Re-run with a larger `{size_param}`"
        if total is not None:
            hint += f" (`{size_param}={total}` returns everything)"
        if page_param:
            hint += f", or page through the rest with `{page_param}`"
        result.update(
            self._truncation_fields(
                returned=returned,
                offset=offset,
                total=total,
                how_to_get_more=hint + ".",
            )
        )
        return result

    def _fetch_cancer_studies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return a page of the cBioPortal study catalogue plus its true size.

        The endpoint defaults to `pageSize=20` while the catalogue holds 539
        studies (verified live: `GET /api/studies` returns 539 records and
        `GET /api/studies?projection=META` reports `Total-Count: 539`), so a
        bare call used to look like the complete list of everything
        cBioPortal has — a study sitting at position 21 read as "not in
        cBioPortal at all".

        `offset` is applied client-side because the endpoint accepts
        `pageNumber` and then ignores it (verified live:
        `?pageSize=5&pageNumber=2` returns the same first five studies as
        `pageNumber=0`), so the tool over-fetches by `offset` and slices.
        """
        limit = max(self._as_int(arguments.get("limit"), 20), 1)
        offset = max(self._as_int(arguments.get("offset"), 0), 0)
        window = limit + offset

        url = self._build_url({**arguments, "limit": window})
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        fetched = response.json()
        if not isinstance(fetched, list):
            fetched = []
        page = fetched[offset : offset + limit]

        if len(fetched) < window:
            # A short window means the catalogue is exhausted; no probe needed.
            total: Optional[int] = len(fetched)
        else:
            probed = self._fetch_total_count(url)
            total = None if probed is None else max(probed, len(fetched))

        result = {
            "status": "success",
            "data": page,
            "url": url,
            "count": len(page),
            "limit": limit,
            "offset": offset,
        }
        result.update(
            self._truncation_fields(
                returned=len(page),
                offset=offset,
                total=total,
                how_to_get_more=(
                    "Raise `limit` to retrieve the whole catalogue in one call, or "
                    "page through it with `offset`"
                    + (f" (next page: offset={offset + len(page)})" if page else "")
                    + "."
                ),
            )
        )
        return result

    def _get_gene_entrez_ids(self, gene_symbols: str) -> list[int]:
        """Convert gene symbols to Entrez IDs"""
        genes = [g.strip() for g in gene_symbols.split(",")]
        entrez_ids = []

        for gene in genes:
            response = self.session.get(
                f"{self.base_url}/genes?keyword={gene}", timeout=self.timeout
            )
            if response.status_code == 200:
                gene_data = response.json()
                if gene_data:
                    entrez_ids.append(gene_data[0].get("entrezGeneId"))

        return entrez_ids

    def _resolve_molecular_profile_id(
        self,
        study_id: str,
        matches: Callable[[Dict[str, Any]], bool],
        guess_suffix: str,
    ) -> Optional[str]:
        """Look up a study's molecular-profile ID for a given alteration type.

        Fix-Round3-003: previously any non-200 response (including a 404
        for a study_id that simply doesn't exist, e.g. a plausible-looking
        guess like 'luad_tcga_pan_can_atlas' instead of the real
        'luad_tcga_pan_can_atlas_2018') fell through to a guessed profile
        id, deferring the real problem to a confusing raw 404 several
        steps later at the actual data-fetch call. A confirmed-nonexistent
        study now returns None so the caller can give an actionable error
        immediately. Any other outcome (study exists but lacks this
        profile type, or a transient non-404 error) keeps the previous
        best-effort naming-convention guess. Shared by
        _get_mutation_profile_id and _get_cna_profile_id, which only differ
        in which profile counts as a match and what suffix to guess.
        """
        response = self.session.get(
            f"{self.base_url}/studies/{study_id}/molecular-profiles",
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return None
        if response.status_code == 200:
            for profile in response.json():
                if matches(profile):
                    return profile.get("molecularProfileId")
        return f"{study_id}_{guess_suffix}"

    def _get_mutation_profile_id(self, study_id: str) -> Optional[str]:
        """Get the mutation molecular profile ID for a study."""
        return self._resolve_molecular_profile_id(
            study_id,
            lambda profile: profile.get("molecularAlterationType")
            == "MUTATION_EXTENDED",
            "mutations",
        )

    _ALTERATION_LABELS = {
        -2: "deep_deletion",
        -1: "shallow_loss",
        0: "neutral",
        1: "gain",
        2: "amplification",
    }

    def _get_cna_profile_id(self, study_id: str) -> Optional[str]:
        """Get the discrete (GISTIC) copy-number molecular profile ID for a study."""
        return self._resolve_molecular_profile_id(
            study_id,
            lambda profile: (
                profile.get("molecularAlterationType") == "COPY_NUMBER_ALTERATION"
                and profile.get("datatype") == "DISCRETE"
            ),
            "gistic",
        )

    def _fetch_discrete_cna(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch discrete copy-number alteration (CNA) calls for a gene in a study.

        Returns per-sample alteration values (-2,-1,0,1,2 = deep-deletion,
        shallow-loss, neutral, gain, amplification) from GISTIC profiles, plus a
        count breakdown by alteration type.
        """
        study_id = arguments.get("study_id")
        if not study_id:
            return {"status": "error", "error": "study_id parameter is required"}

        gene_list = arguments.get("gene_list") or arguments.get("gene")
        if not gene_list:
            return {"status": "error", "error": "gene_list parameter is required"}

        event_type = (arguments.get("alteration_type") or "ALL").upper()
        valid_events = {"AMP", "GAIN", "DIPLOID", "HETLOSS", "HOMDEL", "ALL"}
        if event_type not in valid_events:
            event_type = "ALL"

        # Resolve molecular profile (allow explicit override).
        profile_id = arguments.get("molecular_profile_id") or self._get_cna_profile_id(
            study_id
        )
        if profile_id is None:
            return {
                "status": "error",
                "error": (
                    f"Unknown cBioPortal study_id '{study_id}'. "
                    "Use cBioPortal_get_cancer_studies to look up valid "
                    "study IDs — study naming conventions vary."
                ),
            }

        # Resolve gene symbols -> Entrez IDs.
        entrez_ids = self._get_gene_entrez_ids(gene_list)
        entrez_ids = [e for e in entrez_ids if e is not None]
        if not entrez_ids:
            return {
                "status": "error",
                "error": f"Could not find Entrez IDs for genes: {gene_list}",
            }

        sample_list_id = arguments.get("sample_list_id") or f"{study_id}_all"

        url = (
            f"{self.base_url}/molecular-profiles/{profile_id}"
            f"/discrete-copy-number/fetch?projection=SUMMARY"
        )
        if event_type != "ALL":
            url += f"&discreteCopyNumberEventType={event_type}"

        payload = {"entrezGeneIds": entrez_ids, "sampleListId": sample_list_id}
        response = self.session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            data = []

        # Tally alteration values into human-readable categories.
        counts: Dict[str, int] = {}
        for rec in data:
            label = self._ALTERATION_LABELS.get(rec.get("alteration"), "unknown")
            counts[label] = counts.get(label, 0) + 1

        return {
            "status": "success",
            "data": data,
            "url": url,
            "count": len(data),
            "molecular_profile_id": profile_id,
            "entrez_gene_ids": entrez_ids,
            "alteration_type": event_type,
            "alteration_counts": counts,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Fix-R4A-001: _build_url only substitutes {placeholder} for keys
            # actually present in `arguments`, so an omitted optional param
            # (e.g. `limit`) left its literal "{limit}" placeholder unfilled
            # in the endpoint template, sending a broken query string to the
            # live API instead of falling back to the schema's declared
            # default value.
            schema_props = self.tool_config.get("parameter", {}).get("properties", {})
            defaults = {
                name: prop["default"]
                for name, prop in schema_props.items()
                if "default" in prop and name not in arguments
            }
            if defaults:
                arguments = {**arguments, **defaults}

            if "query" in arguments and "keyword" not in arguments:
                arguments = {**arguments, "keyword": arguments["query"]}
            if (
                "get_genes" in self.tool_config.get("name", "")
                and "keyword" not in arguments
            ):
                return {
                    "status": "error",
                    "error": "keyword or query parameter is required",
                }
            method = self.tool_config["fields"].get("method", "GET")
            url = self._build_url(arguments)

            # Special handling for discrete copy-number alteration (CNA) queries.
            if "cBioPortal_get_copy_number_alterations" in self.tool_config.get(
                "name", ""
            ):
                return self._fetch_discrete_cna(arguments)

            # The study catalogue needs client-side offset handling and an
            # explicit catalogue size; see _fetch_cancer_studies.
            if "cBioPortal_get_cancer_studies" in self.tool_config.get("name", ""):
                return self._fetch_cancer_studies(arguments)

            # Special handling for mutation queries with new API
            if "cBioPortal_get_mutations" in self.tool_config.get("name", ""):
                study_id = arguments.get("study_id")
                gene_list = arguments.get("gene_list")
                sample_list_id = arguments.get("sample_list_id")

                # Get molecular profile ID
                profile_id = self._get_mutation_profile_id(study_id)
                if profile_id is None:
                    return {
                        "status": "error",
                        "error": (
                            f"Unknown cBioPortal study_id '{study_id}'. "
                            "Use cBioPortal_get_cancer_studies to look up "
                            "valid study IDs — study naming conventions vary "
                            "(e.g. the LUAD Pan-Cancer Atlas study is "
                            "'luad_tcga_pan_can_atlas_2018', not "
                            "'luad_tcga_pan_can_atlas')."
                        ),
                    }

                # Get gene Entrez IDs
                entrez_ids = self._get_gene_entrez_ids(gene_list)

                if not entrez_ids:
                    error_msg = f"Could not find Entrez IDs for genes: {gene_list}"
                    return {"status": "error", "error": error_msg}

                # Use the new API endpoint
                url = f"{self.base_url}/molecular-profiles/{profile_id}/mutations/fetch"

                # Build payload
                payload = {"entrezGeneIds": entrez_ids}

                # Add sample filter if provided, otherwise use all samples
                if sample_list_id:
                    payload["sampleListId"] = sample_list_id
                else:
                    payload["sampleListId"] = f"{study_id}_all"

                response = self.session.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                return {
                    "status": "success",
                    "data": data,
                    "url": url,
                    "count": len(data) if isinstance(data, list) else 1,
                    "molecular_profile_id": profile_id,
                    "entrez_gene_ids": entrez_ids,
                }

            # cBioPortal_get_clinical_data declares an optional
            # `clinical_attribute_id` filter that maps to the API's
            # `attributeId` query param. _build_url only substitutes
            # {placeholders}, so without this the filter was silently dropped
            # and every call returned all clinical attributes regardless of the
            # requested one (confirmed live: brca_tcga returns 17 attributes
            # unfiltered vs 1 with attributeId=CANCER_TYPE).
            if "cBioPortal_get_clinical_data" in self.tool_config.get("name", ""):
                attribute_id = arguments.get("clinical_attribute_id")
                if attribute_id:
                    sep = "&" if "?" in url else "?"
                    url = f"{url}{sep}attributeId={quote(str(attribute_id))}"

            # Handle regular GET or POST requests
            if method == "POST":
                payload = self.tool_config["fields"].get("payload", {})
                # Replace placeholders in payload
                for k, v in arguments.items():
                    if isinstance(payload, dict):
                        for pk, pv in payload.items():
                            if isinstance(pv, str):
                                payload[pk] = pv.replace(f"{{{k}}}", str(v))

                response = self.session.post(url, json=payload, timeout=self.timeout)
            else:
                response = self.session.get(url, timeout=self.timeout)

            response.raise_for_status()
            data = response.json()

            result = {
                "status": "success",
                "data": data,
                "url": url,
                "count": len(data) if isinstance(data, list) else 1,
            }
            # Paginated endpoints (gene panels, clinical data, samples,
            # patients) previously returned only `count` -- the size of the
            # page -- which is indistinguishable from the size of the set.
            return self._disclose_generic_truncation(result, url)
        except Exception as e:
            return {
                "status": "error",
                "error": f"cBioPortal API error: {str(e)}",
                "url": url if "url" in locals() else "unknown",
            }
