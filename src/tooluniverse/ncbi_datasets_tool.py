# ncbi_datasets_tool.py
"""
NCBI Datasets API v2 tool for ToolUniverse.

NCBI Datasets provides programmatic access to gene, genome, and taxonomy
data from NCBI. The API covers gene metadata, gene orthologs, genome
assembly reports, and taxonomic classification across all organisms.

API: https://api.ncbi.nlm.nih.gov/datasets/v2
No authentication required (optional API key for higher rate limits).
"""

import os
import time
from typing import Any, Dict
from urllib.parse import quote

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

NCBI_DATASETS_BASE = "https://api.ncbi.nlm.nih.gov/datasets/v2"
_TRANSIENT_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_GET_ATTEMPTS = 3


class _NCBIResponseError(RuntimeError):
    """NCBI returned a structured API error, sometimes with HTTP 200."""


@register_tool("NCBIDatasetsTool")
class NCBIDatasetsTool(BaseTool):
    """
    Tool for querying the NCBI Datasets API v2.

    Provides access to gene information by ID/symbol, gene orthologs,
    genome assembly reports by taxon, taxonomy details by taxon ID,
    and taxonomy name suggestions.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.api_key = os.environ.get("NCBI_API_KEY", "").strip()
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "gene_by_id"
        )

    def _headers(self) -> Dict[str, str]:
        """Build request headers without exposing the optional API key as input."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key
        return headers

    @staticmethod
    def _path_segment(value: Any) -> str:
        """Encode one user-controlled path component without changing its meaning."""
        return quote(str(value).strip(), safe="")

    @staticmethod
    def _extract_api_error(payload: Any) -> str:
        """Extract errors from NCBI's HTTP and HTTP-200 error envelopes."""
        if not isinstance(payload, dict):
            return ""

        def error_text(value: Any) -> str:
            if isinstance(value, str):
                return value.strip()
            if isinstance(value, dict):
                for key in ("message", "reason", "error", "detail"):
                    message = error_text(value.get(key))
                    if message:
                        return message
            if isinstance(value, list):
                for item in value:
                    message = error_text(item)
                    if message:
                        return message
            return ""

        for key in ("message", "error", "errors"):
            message = error_text(payload.get(key))
            if message:
                return message

        messages = payload.get("messages") or []
        for entry in messages:
            if not isinstance(entry, dict):
                continue
            detail = entry.get("error", entry)
            message = error_text(detail)
            if message:
                return message

        for report in payload.get("reports") or []:
            if not isinstance(report, dict):
                continue
            for detail in report.get("errors") or []:
                message = error_text(detail)
                if message:
                    return message

        return ""

    def _response_json(self, response: requests.Response) -> Dict[str, Any]:
        """Decode a response and reject both HTTP and embedded NCBI errors."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            try:
                detail = self._extract_api_error(response.json())
            except (TypeError, ValueError):
                detail = ""
            if detail:
                status_code = getattr(response, "status_code", "unknown")
                raise _NCBIResponseError(
                    f"NCBI Datasets API HTTP {status_code}: {detail}"
                ) from exc
            raise

        try:
            payload = response.json()
        except (TypeError, ValueError) as exc:
            raise _NCBIResponseError("NCBI Datasets API returned invalid JSON") from exc
        detail = self._extract_api_error(payload)
        if detail:
            raise _NCBIResponseError(f"NCBI Datasets API error: {detail}")
        if not isinstance(payload, dict):
            raise _NCBIResponseError("NCBI Datasets API returned non-object JSON")
        return payload

    def _get(self, url: str, **kwargs) -> requests.Response:
        """GET with bounded retries for NCBI throttling and transient failures."""
        for attempt in range(_MAX_GET_ATTEMPTS):
            try:
                response = requests.get(url, **kwargs)
            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ):
                if attempt == _MAX_GET_ATTEMPTS - 1:
                    raise
                time.sleep(min(0.5 * (2**attempt), 5.0))
                continue
            if (
                response.status_code not in _TRANSIENT_HTTP_STATUS
                or attempt == _MAX_GET_ATTEMPTS - 1
            ):
                return response

            retry_after = (getattr(response, "headers", {}) or {}).get("Retry-After")
            try:
                delay = float(retry_after) if retry_after is not None else None
            except (TypeError, ValueError):
                delay = None
            if delay is None:
                delay = 0.5 * (2**attempt)
            delay = min(max(delay, 0.0), 5.0)

            close = getattr(response, "close", None)
            if callable(close):
                close()
            time.sleep(delay)

        raise RuntimeError("NCBI GET retry loop exited unexpectedly")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NCBI Datasets API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NCBI Datasets API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NCBI Datasets API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"NCBI Datasets API HTTP error: {e.response.status_code}",
            }
        except _NCBIResponseError as e:
            return {"status": "error", "error": str(e)}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying NCBI Datasets: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate NCBI Datasets endpoint."""
        endpoint_type = self.endpoint_type

        if endpoint_type == "gene_by_id":
            return self._get_gene_by_id(arguments)
        elif endpoint_type == "gene_by_symbol":
            return self._get_gene_by_symbol(arguments)
        elif endpoint_type == "gene_orthologs":
            return self._get_gene_orthologs(arguments)
        elif endpoint_type == "taxonomy":
            return self._get_taxonomy(arguments)
        elif endpoint_type == "taxonomy_suggest":
            return self._get_taxonomy_suggest(arguments)
        elif endpoint_type == "genome_assembly":
            return self._get_genome_assembly(arguments)
        elif endpoint_type == "genomes_by_taxon":
            return self._list_genomes_by_taxon(arguments)
        elif endpoint_type == "sequence_reports":
            return self._get_sequence_reports(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint type: {endpoint_type}",
            }

    def _get_gene_by_id(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene information by NCBI Gene ID."""
        gene_id = str(arguments.get("gene_id") or "").strip()
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        url = (
            f"{NCBI_DATASETS_BASE}/gene/id/{self._path_segment(gene_id)}/dataset_report"
        )
        response = self._get(url, headers=self._headers(), timeout=self.timeout)
        result = self._response_json(response)

        reports = result.get("reports", [])
        if not reports:
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "total_results": 0,
                    "query_gene_id": str(gene_id),
                    "source": "NCBI Datasets API v2",
                },
            }

        gene_data = reports[0].get("gene", {})
        return {
            "status": "success",
            "data": {
                "gene_id": gene_data.get("gene_id"),
                "symbol": gene_data.get("symbol"),
                "description": gene_data.get("description"),
                "tax_id": gene_data.get("tax_id"),
                "taxname": gene_data.get("taxname"),
                "common_name": gene_data.get("common_name"),
                "type": gene_data.get("type"),
                "chromosomes": gene_data.get("chromosomes", []),
                "orientation": gene_data.get("orientation"),
                "swiss_prot_accessions": gene_data.get("swiss_prot_accessions", []),
                "ensembl_gene_ids": gene_data.get("ensembl_gene_ids", []),
                "omim_ids": gene_data.get("omim_ids", []),
                "synonyms": gene_data.get("synonyms", []),
                "nomenclature_authority": gene_data.get("nomenclature_authority"),
                "genomic_locations": self._extract_locations(gene_data),
            },
            "metadata": {
                "total_results": len(reports),
                "query_gene_id": str(gene_id),
                "source": "NCBI Datasets API v2",
            },
        }

    def _get_gene_by_symbol(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene information by gene symbol and taxon."""
        symbol = str(arguments.get("symbol") or "").strip()
        taxon = str(arguments.get("taxon") or "human").strip()
        if not symbol:
            return {"status": "error", "error": "symbol parameter is required"}

        url = (
            f"{NCBI_DATASETS_BASE}/gene/symbol/{self._path_segment(symbol)}/taxon/"
            f"{self._path_segment(taxon)}/dataset_report"
        )
        response = self._get(url, headers=self._headers(), timeout=self.timeout)
        result = self._response_json(response)

        reports = result.get("reports", [])
        if not reports:
            metadata = {
                "total_results": 0,
                "query_symbol": symbol,
                "query_taxon": taxon,
                "source": "NCBI Datasets API v2",
            }
            # Fix-R15C-1: NCBI returns HTTP 200 (not an error) for some
            # unresolvable taxon tokens, but includes a "messages" warning
            # explaining why -- e.g. taxon="cattle" gets
            # gene_warning_code=ABOVE_SPECIES_TAXON ("belongs to a taxonomy
            # level above species") instead of the "reports" the caller
            # expects. Previously this warning was discarded, so a plain
            # empty-success response was indistinguishable from "this gene
            # genuinely has no match for this taxon" (confirmed: taxon="cow"
            # succeeds with data, taxon="bovine" errors outright, and
            # taxon="cattle" -- silently -- returns neither). Surface the
            # warning so the caller can tell "bad taxon token" from "real
            # zero-match".
            api_messages = result.get("messages") or []
            warnings = [
                m["warning"]["message"]
                for m in api_messages
                if isinstance(m, dict) and m.get("warning", {}).get("message")
            ]
            if warnings:
                metadata["warning"] = (
                    " ".join(warnings)
                    + " Try a more specific taxon (e.g. a species common name "
                    "like 'cow' or 'pig' rather than a broader group name, "
                    "or an NCBI Taxonomy ID)."
                )
            return {
                "status": "success",
                "data": [],
                "metadata": metadata,
            }

        genes = []
        for report in reports:
            gene_data = report.get("gene", {})
            genes.append(
                {
                    "gene_id": gene_data.get("gene_id"),
                    "symbol": gene_data.get("symbol"),
                    "description": gene_data.get("description"),
                    "tax_id": gene_data.get("tax_id"),
                    "taxname": gene_data.get("taxname"),
                    "type": gene_data.get("type"),
                    "chromosomes": gene_data.get("chromosomes", []),
                    "swiss_prot_accessions": gene_data.get("swiss_prot_accessions", []),
                    "ensembl_gene_ids": gene_data.get("ensembl_gene_ids", []),
                    "synonyms": gene_data.get("synonyms", []),
                }
            )

        return {
            "status": "success",
            "data": genes,
            "metadata": {
                "total_results": len(genes),
                "query_symbol": symbol,
                "query_taxon": taxon,
                "source": "NCBI Datasets API v2",
            },
        }

    def _get_gene_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get orthologs for a gene by NCBI Gene ID."""
        gene_id = str(arguments.get("gene_id") or "").strip()
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        page_size = arguments.get("page_size", 20)
        url = f"{NCBI_DATASETS_BASE}/gene/id/{self._path_segment(gene_id)}/orthologs"
        params = {"page_size": max(1, min(int(page_size), 100))}

        response = self._get(
            url,
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        result = self._response_json(response)

        reports = result.get("reports", []) or []
        total_available = result.get("total_count")
        if total_available is None:
            total_available = len(reports)
        # The live ortholog endpoint currently ignores page_size and returns the
        # complete set. Enforce the public ToolUniverse contract locally so a
        # small request cannot unexpectedly produce hundreds of records.
        reports = reports[: params["page_size"]]
        orthologs = []
        for report in reports:
            gene_data = report.get("gene", {})
            orthologs.append(
                {
                    "gene_id": gene_data.get("gene_id"),
                    "symbol": gene_data.get("symbol"),
                    "description": gene_data.get("description"),
                    "tax_id": gene_data.get("tax_id"),
                    "taxname": gene_data.get("taxname"),
                    "common_name": gene_data.get("common_name"),
                    "type": gene_data.get("type"),
                    "chromosomes": gene_data.get("chromosomes", []),
                }
            )

        return {
            "status": "success",
            "data": orthologs,
            "metadata": {
                "total_results": len(orthologs),
                "total_available": total_available,
                "returned": len(orthologs),
                "query_gene_id": str(gene_id),
                "source": "NCBI Datasets API v2",
            },
        }

    def _get_taxonomy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy information by NCBI Taxonomy ID."""
        tax_id = str(arguments.get("tax_id") or "").strip()
        if not tax_id:
            return {"status": "error", "error": "tax_id parameter is required"}

        url = (
            f"{NCBI_DATASETS_BASE}/taxonomy/taxon/"
            f"{self._path_segment(tax_id)}/dataset_report"
        )
        response = self._get(url, headers=self._headers(), timeout=self.timeout)
        result = self._response_json(response)

        reports = result.get("reports", [])
        if not reports:
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "total_results": 0,
                    "query_tax_id": str(tax_id),
                    "source": "NCBI Datasets API v2",
                },
            }

        tax_data = reports[0].get("taxonomy", {})
        scientific_name = tax_data.get("current_scientific_name") or {}
        lineage_ids = tax_data.get("lineage") or tax_data.get("parents", [])
        return {
            "status": "success",
            "data": {
                "tax_id": tax_data.get("tax_id"),
                "organism_name": tax_data.get("organism_name")
                or scientific_name.get("name"),
                "genbank_common_name": tax_data.get("genbank_common_name")
                or tax_data.get("curator_common_name"),
                "rank": tax_data.get("rank"),
                "blast_name": tax_data.get("blast_name") or tax_data.get("group_name"),
                "lineage": lineage_ids,
                "lineage_names": self._resolve_lineage_names(lineage_ids),
                "children": tax_data.get("children", []),
                "counts": tax_data.get("counts", []),
            },
            "metadata": {
                "total_results": len(reports),
                "query_tax_id": str(tax_id),
                "source": "NCBI Datasets API v2",
            },
        }

    def _resolve_lineage_names(self, tax_ids):
        """Fix-R12B-1: `lineage` is a bare list of ancestor tax_ids with no
        names or ranks attached, despite the tool's own description promising
        "full lineage" -- confirmed this is exactly what NCBI's own API
        returns, not something dropped by this tool. NCBI's endpoint accepts
        a comma-joined batch of tax_ids in one request (confirmed live), so
        resolve the whole lineage's names/ranks in a single extra call rather
        than one call per ancestor. Best-effort: any failure here just leaves
        `lineage_names` empty, since the bare-id `lineage` field above already
        succeeded and shouldn't be failed by this enrichment step.
        """
        if not tax_ids:
            return []
        try:
            response = self._get(
                f"{NCBI_DATASETS_BASE}/taxonomy/taxon/"
                f"{','.join(str(t) for t in tax_ids)}/dataset_report",
                headers=self._headers(),
                timeout=self.timeout,
            )
            nodes = self._response_json(response).get("reports", [])
        except (requests.exceptions.RequestException, _NCBIResponseError):
            return []

        by_id = {}
        for node in nodes:
            node_tax = node.get("taxonomy", {})
            node_tax_id = node_tax.get("tax_id")
            if node_tax_id is not None:
                scientific_name = node_tax.get("current_scientific_name") or {}
                by_id[node_tax_id] = {
                    "tax_id": node_tax_id,
                    "organism_name": node_tax.get("organism_name")
                    or scientific_name.get("name"),
                    "rank": node_tax.get("rank"),
                }
        return [
            by_id.get(tid, {"tax_id": tid, "organism_name": None, "rank": None})
            for tid in tax_ids
        ]

    def _get_taxonomy_suggest(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest taxonomy names matching a query string."""
        query = str(arguments.get("query") or "").strip()
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        url = f"{NCBI_DATASETS_BASE}/taxonomy/taxon_suggest/{self._path_segment(query)}"
        response = self._get(url, headers=self._headers(), timeout=self.timeout)
        result = self._response_json(response)

        suggestions = result.get("sci_name_and_ids", [])
        items = []
        for s in suggestions:
            items.append(
                {
                    "scientific_name": s.get("sci_name"),
                    "tax_id": s.get("tax_id"),
                    "common_name": s.get("common_name"),
                    "rank": s.get("rank"),
                    "group_name": s.get("group_name"),
                    "matched_term": s.get("matched_term"),
                }
            )

        return {
            "status": "success",
            "data": items,
            "metadata": {
                "total_results": len(items),
                "query": query,
                "source": "NCBI Datasets API v2",
            },
        }

    @staticmethod
    def _summarize_assembly(report: Dict[str, Any]) -> Dict[str, Any]:
        """Curate a genome dataset_report record into key assembly fields."""
        info = report.get("assembly_info", {})
        stats = report.get("assembly_stats", {})
        org = report.get("organism", {})
        ann = report.get("annotation_info", {})
        return {
            "accession": report.get("accession"),
            "paired_accession": report.get("paired_accession"),
            "source_database": report.get("source_database"),
            "organism_name": org.get("organism_name"),
            "tax_id": org.get("tax_id"),
            "strain": (org.get("infraspecific_names") or {}).get("strain"),
            "assembly_name": info.get("assembly_name"),
            "assembly_level": info.get("assembly_level"),
            "assembly_status": info.get("assembly_status"),
            "refseq_category": info.get("refseq_category"),
            "release_date": info.get("release_date"),
            "submitter": info.get("submitter"),
            "bioproject_accession": info.get("bioproject_accession"),
            "total_sequence_length": stats.get("total_sequence_length"),
            "number_of_chromosomes": stats.get("total_number_of_chromosomes"),
            "number_of_contigs": stats.get("number_of_contigs"),
            "contig_n50": stats.get("contig_n50"),
            "scaffold_n50": stats.get("scaffold_n50"),
            "gc_percent": stats.get("gc_percent"),
            "annotation_provider": ann.get("provider"),
            "annotation_name": ann.get("name"),
        }

    def _get_genome_assembly(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genome assembly metadata by assembly accession (GCF_/GCA_)."""
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {"status": "error", "error": "accession parameter is required"}

        url = (
            f"{NCBI_DATASETS_BASE}/genome/accession/"
            f"{self._path_segment(accession)}/dataset_report"
        )
        response = self._get(url, headers=self._headers(), timeout=self.timeout)
        reports = self._response_json(response).get("reports", []) or []
        if not reports:
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "total_results": 0,
                    "query_accession": accession,
                    "source": "NCBI Datasets API v2",
                },
            }
        return {
            "status": "success",
            "data": self._summarize_assembly(reports[0]),
            "metadata": {
                "total_results": len(reports),
                "query_accession": accession,
                "source": "NCBI Datasets API v2",
            },
        }

    def _list_genomes_by_taxon(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List genome assemblies for a taxon (tax id or scientific name)."""
        taxon = str(arguments.get("taxon") or "").strip()
        if not taxon:
            return {"status": "error", "error": "taxon parameter is required"}
        try:
            page_size = int(arguments.get("limit") or 20)
        except (TypeError, ValueError):
            page_size = 20
        page_size = max(1, min(page_size, 100))

        url = (
            f"{NCBI_DATASETS_BASE}/genome/taxon/"
            f"{self._path_segment(taxon)}/dataset_report"
        )
        params = {"page_size": page_size}
        ref_only = arguments.get("reference_only")
        if ref_only:
            params["filters.reference_only"] = "true"
        response = self._get(
            url,
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        result = self._response_json(response)
        reports = result.get("reports", []) or []
        return {
            "status": "success",
            "data": [self._summarize_assembly(r) for r in reports],
            "metadata": {
                "total_available": result.get("total_count"),
                "returned": len(reports),
                "query_taxon": taxon,
                "page_size": page_size,
                "source": "NCBI Datasets API v2",
            },
        }

    def _get_sequence_reports(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get per-sequence (chromosome/scaffold) reports for an assembly."""
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {"status": "error", "error": "accession parameter is required"}
        try:
            page_size = int(arguments.get("page_size") or 100)
        except (TypeError, ValueError):
            page_size = 100
        page_size = max(1, min(page_size, 1000))
        page_token = str(arguments.get("page_token") or "").strip()
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        url = (
            f"{NCBI_DATASETS_BASE}/genome/accession/"
            f"{self._path_segment(accession)}/sequence_reports"
        )
        response = self._get(
            url,
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        result = self._response_json(response)
        reports = result.get("reports", []) or []
        sequences = [
            {
                "chr_name": s.get("chr_name"),
                "sequence_name": s.get("sequence_name"),
                "role": s.get("role"),
                "location_type": s.get("assigned_molecule_location_type"),
                "refseq_accession": s.get("refseq_accession"),
                "genbank_accession": s.get("genbank_accession"),
                "length": s.get("length"),
                "gc_percent": s.get("gc_percent"),
            }
            for s in reports
        ]
        return {
            "status": "success",
            "data": sequences,
            "metadata": {
                "total_results": len(sequences),
                "total_available": result.get("total_count"),
                "returned": len(sequences),
                "next_page_token": result.get("next_page_token"),
                "query_accession": accession,
                "page_size": page_size,
                "source": "NCBI Datasets API v2",
            },
        }

    def _extract_locations(self, gene_data: Dict[str, Any]) -> list:
        """Extract genomic location information from annotations."""
        locations = []
        for ann in gene_data.get("annotations", []):
            for loc in ann.get("genomic_locations", []):
                genomic_range = loc.get("genomic_range", {})
                locations.append(
                    {
                        "assembly": ann.get("assembly_name"),
                        "accession": loc.get("genomic_accession_version"),
                        "chromosome": loc.get("sequence_name"),
                        "begin": genomic_range.get("begin"),
                        "end": genomic_range.get("end"),
                        "orientation": genomic_range.get("orientation"),
                    }
                )
        return locations
