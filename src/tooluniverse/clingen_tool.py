"""
ClinGen Database REST API Tool

This tool provides access to ClinGen (Clinical Genome Resource) data including:
- Gene-Disease Validity curations
- Dosage Sensitivity curations
- Clinical Actionability curations
- Variant Pathogenicity data

ClinGen is a NIH-funded resource providing authoritative information on
gene-disease relationships for use in clinical genomics.
"""

import requests
import csv
import io
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URLs for ClinGen APIs
CLINGEN_BASE_URL = "https://search.clinicalgenome.org"
ACTIONABILITY_ADULT_URL = "https://actionability.clinicalgenome.org/ac/Adult/api"
ACTIONABILITY_PEDIATRIC_URL = (
    "https://actionability.clinicalgenome.org/ac/Pediatric/api"
)
EREPO_BASE_URL = "https://erepo.clinicalgenome.org/evrepo/api"

# Confirmed live against the Evidence Repository's `classifications` endpoint:
#   * `gene`, `caid`, `hgvs` and `variationId` are real server-side filters
#   * `variant` is not a parameter at all -- it is accepted and ignored, so the
#     request degrades to an unfiltered listing of the whole repository. A
#     deliberately bogus `variant=ZZZNOTAVARIANT` returned the same first rows
#     as sending no filter whatsoever.
#   * the response carries no total, and an unspecified `matchLimit` pages at 25
# Those two facts together understated PAH by 32x -- `total: 25` reported for a
# gene with 817 curated classifications -- and reported curated variants as
# absent, because the old client-side narrowing ran over an arbitrary 25-row
# page: CAID CA16020993 (PAH c.1315+1G>T) is row 401 of PAH's 817, so it was
# answered "No variant classifications found ... Not all genes have active
# VCEPs" when in fact the Phenylketonuria VCEP had classified it.
#
# The largest single gene is RUNX1 at 1,648 rows and the entire repository is
# 13,084 rows, so this cap covers any gene-scoped query outright.
_EREPO_MATCH_LIMIT = 5000

# `data` stays capped so a listing cannot return tens of MB; `total` reports the
# real count beside it and the gap is now disclosed rather than left to be
# inferred from counting rows.
_MAX_PUBLISHED = 100


def _published(rows: List[Dict[str, Any]], narrow_hint: str) -> Dict[str, Any]:
    """Publish a capped slice of `rows` and state the cap beside the total.

    Every listing in this module caps `data` for payload size while reporting
    the full `total` next to it. Undisclosed, that reads as a total which
    disagrees with the rows printed beside it: ClinGen_get_gene_validity
    published `total: 3659` directly above exactly 100 rows, on a tool whose
    own description promises a "comprehensive list".
    """
    published = rows[:_MAX_PUBLISHED]
    result: Dict[str, Any] = {
        "data": published,
        "total": len(rows),
        "returned": len(published),
    }
    if len(published) < len(rows):
        result["data_truncated"] = True
        result["data_truncation_note"] = (
            f"`total` is the full count for this query; `data` carries only the "
            f"first {len(published)} of them. {narrow_hint}"
        )
    return result


def _variant_query_param(variant: Any) -> tuple:
    """Map a variant identifier onto the erepo parameter that filters on it.

    Returns an (endpoint parameter name, value) pair. `hgvs` is the fallback
    because it matches protein-change strings as well as full HGVS -- confirmed
    live that `hgvs=p.Arg408Trp` resolves to a single classification.
    """
    value = str(variant).strip()
    caid = value.upper().removeprefix("CAR:")
    if re.fullmatch(r"CA\d+", caid):
        return "caid", caid
    if value.isdigit():
        return "variationId", value
    return "hgvs", value


@register_tool("ClinGenTool")
class ClinGenTool(BaseTool):
    """
    ClinGen Database REST API tool.

    Provides access to ClinGen curated data including gene-disease validity,
    dosage sensitivity, and clinical actionability.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "")
        self.timeout = fields.get("timeout", 60)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to operation handler based on config."""
        operation = self.operation or arguments.get("operation")

        if not operation:
            return {"status": "error", "error": "Missing: operation"}

        operation_map = {
            "get_gene_validity": self._get_gene_validity,
            "search_gene_validity": self._search_gene_validity,
            "get_dosage_sensitivity": self._get_dosage_sensitivity,
            "search_dosage_sensitivity": self._search_dosage_sensitivity,
            "get_actionability_adult": self._get_actionability_adult,
            "get_actionability_pediatric": self._get_actionability_pediatric,
            "search_actionability": self._search_actionability,
            "get_variant_classifications": self._get_variant_classifications,
        }

        handler = operation_map.get(operation)
        if not handler:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return handler(arguments)

    def _get_gene_validity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all gene-disease validity curations from ClinGen."""
        try:
            url = f"{CLINGEN_BASE_URL}/kb/gene-validity/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Optional filtering by gene
            gene = arguments.get("gene")
            if gene:
                gene_upper = gene.upper()
                # Handle both "GENE SYMBOL" (from CSV) and "Gene Symbol" key formats
                curations = [
                    c
                    for c in curations
                    if c.get("GENE SYMBOL", c.get("Gene Symbol", "")).upper()
                    == gene_upper
                ]

            return {
                "status": "success",
                **_published(
                    curations,
                    "Pass `gene` to narrow to one gene's curations, or use "
                    "ClinGen_search_gene_validity, which returns every match.",
                ),
                "source": "ClinGen Gene-Disease Validity",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_gene_validity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search gene-disease validity curations by gene symbol."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            url = f"{CLINGEN_BASE_URL}/kb/gene-validity/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Filter by gene symbol (case-insensitive, EXACT match -- this
            # column holds a single precise HGNC symbol, not free text, and
            # substring matching silently pulled in unrelated genes whose
            # symbol happens to contain the query, e.g. "OTC" -> "NOTCH1"/
            # "NOTCH2" (confirmed live). Mirrors _get_gene_validity's already-
            # correct exact-match filter above.
            gene_upper = gene.upper()
            matches = [
                c
                for c in curations
                if c.get("GENE SYMBOL", c.get("Gene Symbol", "")).upper() == gene_upper
            ]

            return {
                "status": "success",
                "data": matches,
                "total": len(matches),
                "gene_searched": gene,
                "source": "ClinGen Gene-Disease Validity",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_dosage_sensitivity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all dosage sensitivity curations from ClinGen."""
        include_regions = arguments.get("include_regions", False)

        try:
            if include_regions:
                url = f"{CLINGEN_BASE_URL}/kb/gene-dosage/downloadall"
            else:
                url = f"{CLINGEN_BASE_URL}/kb/gene-dosage/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Optional filtering by gene -- EXACT match (case-insensitive):
            # this column holds a single precise HGNC symbol, not free text,
            # and substring matching silently pulled in unrelated genes
            # whose symbol happens to contain the query, e.g. "OTC" ->
            # "NOTCH1"/"NOTCH2" (confirmed live).
            gene = arguments.get("gene")
            if gene:
                gene_upper = gene.upper()
                # Handle both "GENE SYMBOL" and "Gene Symbol" key formats
                curations = [
                    c
                    for c in curations
                    if c.get("GENE SYMBOL", c.get("Gene Symbol", "")).upper()
                    == gene_upper
                ]

            return {
                "status": "success",
                **_published(
                    curations,
                    "Pass `gene` to narrow to one gene's dosage curations.",
                ),
                "include_regions": include_regions,
                "source": "ClinGen Dosage Sensitivity",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_dosage_sensitivity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search dosage sensitivity curations by gene symbol."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            # Use the simpler download endpoint (genes only) for searching
            url = f"{CLINGEN_BASE_URL}/kb/gene-dosage/download"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse CSV response
            curations = self._parse_csv(response.text)

            # Filter by gene symbol (case-insensitive, EXACT match -- this
            # column holds a single precise HGNC symbol, not free text, and
            # substring matching silently pulled in unrelated genes whose
            # symbol happens to contain the query, e.g. "OTC" -> "NOTCH1"/
            # "NOTCH2" (confirmed live).
            # Handle different column name formats from different endpoints
            gene_upper = gene.upper()
            matches = [
                c
                for c in curations
                if c.get(
                    "GENE SYMBOL", c.get("GENE/REGION", c.get("Gene Symbol", ""))
                ).upper()
                == gene_upper
            ]

            return {
                "status": "success",
                "data": matches,
                "total": len(matches),
                "gene_searched": gene,
                "source": "ClinGen Dosage Sensitivity",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_actionability_adult(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical actionability curations for adult context."""
        return self._get_actionability(arguments, "Adult")

    def _get_actionability_pediatric(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical actionability curations for pediatric context."""
        return self._get_actionability(arguments, "Pediatric")

    @staticmethod
    def _actionability_rows_to_dicts(data: Any) -> list:
        """The ?flavor=flat actionability API returns a columnar table --
        {"columns": [...], "rows": [[...], ...]} -- not a list of record
        dicts (confirmed live). Neither older code path recognized this
        shape (isinstance(data, list) is False and there's no "data" key),
        so the gene filter silently matched nothing and the raw un-parsed
        table was returned as-is. Zip columns with each row into dicts.
        """
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("columns"), list):
            columns = data["columns"]
            return [
                dict(zip(columns, row))
                for row in data.get("rows", [])
                if isinstance(row, list)
            ]
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        return []

    def _get_actionability(
        self, arguments: Dict[str, Any], context: str
    ) -> Dict[str, Any]:
        """Get clinical actionability curations for a specific context."""
        try:
            base_url = (
                ACTIONABILITY_ADULT_URL
                if context == "Adult"
                else ACTIONABILITY_PEDIATRIC_URL
            )

            # Use flat format for easier parsing
            url = f"{base_url}/summ?flavor=flat"

            headers = {"Accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            curations = self._actionability_rows_to_dicts(response.json())

            # Optional filtering by gene. geneOrVariant is a comma-joined
            # multi-gene field for panel curations (e.g. "BRCA1,BRCA2"), so
            # substring match rather than exact-match the whole field.
            gene = arguments.get("gene")
            if gene:
                gene_upper = gene.upper()
                curations = [
                    c
                    for c in curations
                    if gene_upper in str(c.get("geneOrVariant", "")).upper()
                    or gene_upper in str(c.get("gene", "")).upper()
                    or gene_upper in str(c.get("Gene", "")).upper()
                    or gene_upper in str(c.get("hgncId", "")).upper()
                ]

            return {
                "status": "success",
                **_published(
                    curations,
                    "Pass `gene` to narrow to one gene's actionability curations.",
                ),
                "context": context,
                "source": f"ClinGen Clinical Actionability ({context})",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _fetch_actionability_context(
        self, base_url: str, gene: str
    ) -> List[Dict[str, Any]]:
        """Fetch and gene-filter one actionability context (Adult/Pediatric).
        Raises on failure -- the caller decides how to handle a failed context."""
        url = f"{base_url}/summ?flavor=flat"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        curations = self._actionability_rows_to_dicts(response.json())

        # Filter by gene. geneOrVariant is a comma-joined multi-gene field
        # for panel curations, so substring match rather than exact-match
        # the whole field.
        gene_upper = gene.upper()
        return [
            c
            for c in curations
            if gene_upper in str(c.get("geneOrVariant", "")).upper()
            or gene_upper in str(c.get("gene", "")).upper()
            or gene_upper in str(c.get("Gene", "")).upper()
            or gene_upper in str(c.get("hgncId", "")).upper()
        ]

    def _search_actionability(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search clinical actionability across both adult and pediatric contexts."""
        gene = arguments.get("gene")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            # Fix-R53A-1: the Adult and Pediatric actionability endpoints are
            # each independently slow (confirmed live: the Adult endpoint
            # alone took ~124s for a 138KB response -- expensive server-side
            # computation, not a network issue) but are fetched one after
            # the other despite being fully independent requests, so a
            # caller paid the sum of both (up to ~4 minutes, and close to
            # this tool's own 120s per-request timeout budget even for a
            # single context). Fetching them concurrently bounds the wait
            # to the slower of the two instead of the sum of both.
            contexts = [
                ("Adult", ACTIONABILITY_ADULT_URL),
                ("Pediatric", ACTIONABILITY_PEDIATRIC_URL),
            ]
            results = {"Adult": [], "Pediatric": []}
            # Fix-R43-1: a failed context must not read as a genuine zero, so
            # record which ones failed rather than swallowing the exception.
            failures: Dict[str, str] = {}
            with ThreadPoolExecutor(max_workers=len(contexts)) as executor:
                futures = {
                    executor.submit(
                        self._fetch_actionability_context, base_url, gene
                    ): context
                    for context, base_url in contexts
                }
                for future in futures:
                    context = futures[future]
                    try:
                        results[context] = future.result()
                    except Exception as exc:
                        failures[context] = f"{type(exc).__name__}: {exc}"

            response: Dict[str, Any] = {
                "gene_searched": gene,
                "source": "ClinGen Clinical Actionability",
            }
            if failures:
                response["failed_contexts"] = failures
            if len(failures) == len(contexts):
                # Both counts would be a fabricated zero. proteins_api_tool
                # likewise reports error when nothing at all was retrieved.
                response["status"] = "error"
                response["error"] = (
                    f"All ClinGen actionability contexts failed to fetch for "
                    f"{gene}; see failed_contexts. No count can be reported."
                )
                return response

            response.update(
                status="success",
                data=results,
                adult_count=len(results["Adult"]),
                pediatric_count=len(results["Pediatric"]),
            )
            if failures:
                response["note"] = (
                    f"Partial result: {', '.join(sorted(failures))} could not be "
                    "fetched, so its count of 0 means 'not retrieved', not "
                    "'no curation exists'. Retry for a complete answer."
                )
            return response
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _flatten_classification(item: Dict[str, Any]) -> Dict[str, Any]:
        """Map one classifications?gene=/variant= JSON record to the tool's
        declared 7-field return_schema (Variation, ClinVar Variation Id,
        HGNC Gene Symbol, Disease, Mondo Id, Assertion, Expert Panel)."""
        hgvs = item.get("hgvs") or []
        gene = item.get("gene") or {}
        condition = item.get("condition") or {}
        guidelines = item.get("guidelines") or []
        first_guideline = guidelines[0] if guidelines else {}
        agents = first_guideline.get("agents") or []
        first_agent = agents[0] if agents else {}
        return {
            # The last hgvs entry is the gene-and-protein-notation form,
            # e.g. "NM_000277.2(PAH):c.1A>G (p.Met1Val)" -- matches the old
            # TSV "Variation" column's format.
            "Variation": hgvs[-1] if hgvs else None,
            "ClinVar Variation Id": item.get("variationId"),
            "HGNC Gene Symbol": gene.get("label"),
            "Disease": condition.get("label"),
            "Mondo Id": condition.get("@id"),
            "Assertion": (first_guideline.get("outcome") or {}).get("label"),
            "Expert Panel": first_agent.get("affiliation"),
        }

    def _get_variant_classifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get variant pathogenicity classifications from ClinGen Evidence Repository.

        classifications/all fetches the *entire* ~22MB, ~10k-row repository
        with no server-side filter and filters client-side -- confirmed live
        this routinely took 2-5+ minutes (and sometimes hung past a 300s
        client timeout) even for a gene with zero curated variants. The
        classifications endpoint (no /all) supports real server-side filtering
        and returns in ~1s -- confirmed live for both a curated gene (PAH) and
        an uncurated one (empty result, still ~1s). Calling it with neither
        gene nor variant set is just as unbounded as classifications/all
        (confirmed live: also hangs past 30s with no params), so require at
        least one.

        Every filter is applied by the server: `gene` directly, and `variant`
        via whichever of `caid`/`variationId`/`hgvs` matches the identifier
        supplied. See `_variant_query_param` and `_EREPO_MATCH_LIMIT` for why
        the tool must name the parameter the endpoint actually implements and
        must state its own page size.
        """
        gene = arguments.get("gene")
        variant = arguments.get("variant")
        if not gene and not variant:
            return {
                "status": "error",
                "error": (
                    "gene or variant parameter is required. The ClinGen "
                    "Evidence Repository's classifications endpoint has no "
                    "working unfiltered listing (an unfiltered request is "
                    "just as unbounded as the bulk classifications/all "
                    "download) -- query by gene and/or variant instead."
                ),
            }
        try:
            params: Dict[str, Any] = {"matchLimit": _EREPO_MATCH_LIMIT}
            if gene:
                params["gene"] = gene
            if variant:
                variant_key, variant_value = _variant_query_param(variant)
                params[variant_key] = variant_value

            response = requests.get(
                f"{EREPO_BASE_URL}/classifications", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("variantInterpretations", [])

            data = [self._flatten_classification(item) for item in items]

            result = {
                "status": "success",
                **_published(
                    data,
                    "Pass `variant` (a ClinGen CAID, a ClinVar VariationID or an "
                    "HGVS/protein-change string) to retrieve a specific row.",
                ),
                "source": "ClinGen Evidence Repository",
            }
            if len(data) >= _EREPO_MATCH_LIMIT:
                result["total_is_a_lower_bound"] = True
                result["total_note"] = (
                    f"The query filled the {_EREPO_MATCH_LIMIT}-row request cap, "
                    "so `total` is a lower bound rather than the true count."
                )
            if not data:
                if gene:
                    result["note"] = (
                        f"No variant classifications found for gene '{gene}'. "
                        "The ClinGen Evidence Repository only contains variants "
                        "curated by Variant Curation Expert Panels (VCEPs), and "
                        "not all genes have an active VCEP. Try "
                        "ClinGen_get_gene_validity for gene-disease validity or "
                        "clinvar_search_variants for ClinVar classifications."
                    )
                else:
                    result["note"] = (
                        f"No variant classification found for variant '{variant}', "
                        f"queried as `{variant_key}`. This was an exact "
                        "server-side lookup over the whole Evidence Repository, so "
                        "the variant is genuinely uncurated rather than merely "
                        "missing from a page of results. Supply `gene` to list "
                        "every curated variant for its gene, or use "
                        "clinvar_search_variants for ClinVar classifications."
                    )
            return result
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _parse_csv(self, csv_text: str) -> List[Dict[str, Any]]:
        """Parse CSV text into list of dictionaries.

        Handles ClinGen's special CSV format which has metadata headers
        before the actual data rows.
        """
        result = []
        try:
            lines = csv_text.strip().split("\n")

            # Find the header row (contains "GENE SYMBOL" or similar)
            header_idx = None
            for i, line in enumerate(lines):
                if "GENE SYMBOL" in line.upper():
                    header_idx = i
                    break

            if header_idx is None:
                # Fallback - try standard CSV parsing
                reader = csv.DictReader(io.StringIO(csv_text))
                for row in reader:
                    cleaned = {k: v for k, v in row.items() if v and k}
                    if cleaned:
                        result.append(cleaned)
                return result

            # Find where actual data starts (skip separator row after header)
            data_start = header_idx + 1
            if data_start < len(lines) and "+++++" in lines[data_start]:
                data_start += 1

            # Build new CSV content: header + data rows
            header_line = lines[header_idx]
            data_lines = [line for line in lines[data_start:] if "+++++" not in line]
            csv_content = header_line + "\n" + "\n".join(data_lines)

            # Use StringIO to read CSV from string
            reader = csv.DictReader(io.StringIO(csv_content))
            for row in reader:
                # Clean up the row - remove empty values
                cleaned = {}
                for k, v in row.items():
                    if v and k:
                        # Strip whitespace
                        k = k.strip()
                        v = v.strip()
                        if v:
                            cleaned[k] = v
                if cleaned and len(cleaned) > 2:  # Must have meaningful data
                    result.append(cleaned)
        except Exception:
            # Log but don't fail
            pass
        return result
