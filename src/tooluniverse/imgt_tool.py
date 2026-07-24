"""
IMGT (International ImMunoGeneTics Information System) tool for ToolUniverse.

IMGT is the international reference for immunoglobulin (IG), T cell receptor (TR),
and MHC/HLA gene sequences.

Website: https://www.imgt.org/
Uses DBFetch for sequence retrieval where available.
"""

import html
import re
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
from .base_tool import BaseTool
from .tool_registry import register_tool

# IMGT related URLs
IMGT_BASE_URL = "https://www.imgt.org"
EBI_DBFETCH_URL = "https://www.ebi.ac.uk/Tools/dbfetch/dbfetch"


@register_tool("IMGTTool")
class IMGTTool(BaseTool):
    """
    Tool for accessing IMGT immunoglobulin/TCR data.

    IMGT provides:
    - Immunoglobulin gene sequences
    - T cell receptor sequences
    - MHC/HLA sequences
    - Germline gene assignments

    Uses EBI DBFetch for sequence retrieval. No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute IMGT query based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "get_sequence":
            return self._get_sequence(arguments)
        elif operation == "get_germline_fasta":
            return self._get_germline_fasta(arguments)
        elif operation == "search_genes":
            return self._search_genes(arguments)
        elif operation == "get_gene_info":
            return self._get_gene_info(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: get_sequence, get_germline_fasta, search_genes, get_gene_info",
            }

    @staticmethod
    def _follow_imgt_redirects(
        session: requests.Session, url: str, params: Dict[str, str], timeout: int
    ) -> requests.Response:
        """Follow the IMGT GENE-DB redirect chain, forcing HTTPS.

        GENElect issues a 302 to ``http://...`` (port 80, which hangs from many
        networks) and then a relative redirect to ``/genedb/fastaC.action``. We
        resolve each Location against the current URL and rewrite http->https so
        the request stays on the working TLS endpoint.
        """
        resp = session.get(url, params=params, timeout=timeout, allow_redirects=False)
        current = resp.url
        hops = 0
        while resp.status_code in (301, 302, 303, 307, 308) and hops < 6:
            location = urljoin(current, resp.headers.get("Location", ""))
            if location.startswith("http://"):
                location = "https://" + location[len("http://") :]
            resp = session.get(location, timeout=timeout, allow_redirects=False)
            current = location
            hops += 1
        return resp

    def _get_germline_fasta(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve IMGT germline IG/TR gene reference sequences in FASTA.

        Queries IMGT/GENE-DB (GENElect) for V/D/J-REGION reference sequences of
        a gene type (e.g. IGHV, TRBV) in a species, returning labeled FASTA
        records such as '>AB019441|IGHV(II)-1-1*01|Homo sapiens|...'.

        Args:
            arguments: Dict containing:
                - gene_type: IG/TR gene type, e.g. IGHV, IGHD, IGHJ, IGKV,
                  IGLV, TRAV, TRBV, TRBD, TRBJ (alias: query when it is a gene type)
                - species: species name (default: Homo sapiens)
                - label: IMGT GENElect label number controlling the region set
                  (default '7.2' = all V-REGION/D-REGION/J-REGION reference alleles)
        """
        gene_type = (
            arguments.get("gene_type")
            or arguments.get("gene")
            or arguments.get("query")
            or ""
        ).strip()
        if not gene_type:
            return {
                "status": "error",
                "error": "Missing required parameter: gene_type (e.g. 'IGHV', 'TRBV')",
            }

        species = (arguments.get("species") or "Homo sapiens").strip()
        label = str(arguments.get("label") or "7.2").strip()

        # GENElect's query field is "<label> <GENETYPE>" (e.g. "7.2 IGHV").
        query_value = f"{label} {gene_type.upper()}"

        try:
            session = requests.Session()
            session.headers.update({"User-Agent": "Mozilla/5.0 (ToolUniverse/IMGT)"})

            response = self._follow_imgt_redirects(
                session,
                f"{IMGT_BASE_URL}/IMGT_GENE-DB/GENElect",
                {"query": query_value, "species": species},
                self.timeout,
            )
            response.raise_for_status()

            page = response.text

            # The result page embeds the labeled FASTA inside <pre> blocks. The
            # first <pre> documents the header fields; the FASTA records are in
            # the block whose content begins with a '>' header line.
            fasta_text = None
            for block in re.findall(r"<pre[^>]*>(.*?)</pre>", page, re.DOTALL):
                unescaped = html.unescape(block).strip()
                if unescaped.startswith(">"):
                    fasta_text = unescaped
                    break

            if not fasta_text:
                return {
                    "status": "error",
                    "error": (
                        f"No FASTA records returned by IMGT/GENE-DB for "
                        f"gene_type='{gene_type}' species='{species}'. "
                        "Verify the gene type is a valid IG/TR locus "
                        "(e.g. IGHV, IGKV, IGLV, TRAV, TRBV)."
                    ),
                }

            headers = re.findall(r"^>.*$", fasta_text, re.MULTILINE)

            return {
                "status": "success",
                "data": {
                    "gene_type": gene_type.upper(),
                    "species": species,
                    "query": query_value,
                    "fasta": fasta_text,
                    "record_count": len(headers),
                    "first_records": headers[:5],
                },
                "metadata": {
                    "source": "IMGT/GENE-DB (GENElect)",
                    "format": "FASTA",
                    "note": (
                        "FASTA headers carry 15 '|'-separated IMGT fields "
                        "(accession, gene/allele, species, functionality, region, ...)."
                    ),
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get immunoglobulin/TCR sequence by accession.

        Args:
            arguments: Dict containing:
                - accession: IMGT/LIGM-DB accession or EMBL/GenBank accession
                - format: Output format (fasta, embl). Default: fasta
        """
        accession = arguments.get("accession", "")
        if not accession:
            return {"status": "error", "error": "Missing required parameter: accession"}

        fmt = arguments.get("format", "fasta")

        try:
            # Use EBI DBFetch to retrieve IMGT sequences
            response = requests.get(
                EBI_DBFETCH_URL,
                params={
                    "db": "imgt",
                    "id": accession,
                    "format": fmt,
                    "style": "raw",
                },
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/IMGT"},
            )

            if response.status_code == 404 or "not found" in response.text.lower():
                # Try EMBL database as fallback
                response = requests.get(
                    EBI_DBFETCH_URL,
                    params={
                        "db": "embl",
                        "id": accession,
                        "format": fmt,
                        "style": "raw",
                    },
                    timeout=self.timeout,
                    headers={"User-Agent": "ToolUniverse/IMGT"},
                )

            if response.status_code == 404:
                return {"status": "error", "error": f"Sequence not found: {accession}"}

            response.raise_for_status()

            return {
                "status": "success",
                "data": {
                    "accession": accession,
                    "format": fmt,
                    "sequence": response.text,
                },
                "metadata": {
                    "source": "IMGT via EBI DBFetch",
                    "accession": accession,
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search IMGT for immunoglobulin/TCR genes.

        Args:
            arguments: Dict containing:
                - query: Search query (gene name, species)
                - gene_type: Gene type filter (IGHV, IGKV, IGLV, TRAV, TRBV, etc.)
                - species: Species filter (e.g., Homo sapiens)
        """
        query = arguments.get("query", "")
        gene_type = arguments.get("gene_type", "")
        species = arguments.get("species", "Homo sapiens")

        # Feature-84A-003: include query in search URL; warn when query is
        # not an IG/TR gene family (e.g. HLA) — IMGT GENE-DB only covers IG/TR genes.
        ig_tr_prefixes = ("IG", "TR")
        query_upper = query.upper()
        is_ig_tr = not query_upper or any(
            query_upper.startswith(p) for p in ig_tr_prefixes
        )

        # Build gene-type URL (query=2 prefix is the IMGT GENE-DB gene-type search)
        gt_suffix = gene_type if gene_type else ""
        search_url = (
            f"{IMGT_BASE_URL}/IMGT_GENE-DB/GENElect"
            f"?query=2+{gt_suffix}&species={species.replace(' ', '+')}"
        )
        # If a keyword query is given, also provide a keyword search URL (query=8)
        keyword_url = None
        if query:
            keyword_url = (
                f"{IMGT_BASE_URL}/IMGT_GENE-DB/GENElect"
                f"?query=8+{query.replace(' ', '+')}&species={species.replace(' ', '+')}"
            )

        search_info = {
            "query": query,
            "gene_type": gene_type if gene_type else "all",
            "species": species,
            "search_url": keyword_url or search_url,
            "reference_url": f"{IMGT_BASE_URL}/IMGTrepertoire/",
            "gene_types": {
                "IGHV": "Immunoglobulin heavy chain variable",
                "IGHD": "Immunoglobulin heavy chain diversity",
                "IGHJ": "Immunoglobulin heavy chain joining",
                "IGKV": "Immunoglobulin kappa chain variable",
                "IGLV": "Immunoglobulin lambda chain variable",
                "TRAV": "T cell receptor alpha chain variable",
                "TRBV": "T cell receptor beta chain variable",
            },
        }

        note = "Use the provided search_url in a browser; IMGT GENE-DB does not expose a public REST API."
        if not is_ig_tr:
            note += (
                f" Note: IMGT GENE-DB covers immunoglobulin and T-cell receptor genes only."
                f" '{query}' may be an HLA/MHC gene — use IMGT/HLA ({IMGT_BASE_URL}/IMGThla/)"
                f" or EBI IPD-IMGT/HLA (https://www.ebi.ac.uk/ipd/imgt/hla/) for HLA genes."
            )

        return {
            "status": "success",
            "data": search_info,
            "metadata": {
                "source": "IMGT",
                "note": note,
            },
        }

    def _get_gene_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get information about IMGT gene nomenclature and databases.

        Args:
            arguments: Dict (no required parameters)
        """
        gene_info = {
            "databases": {
                "IMGT/LIGM-DB": "Annotated IG/TR sequences from EMBL/GenBank/DDBJ",
                "IMGT/GENE-DB": "Human and mouse IG/TR gene reference",
                "IMGT/3Dstructure-DB": "3D structures of IG, TR, MHC",
            },
            "gene_nomenclature": {
                "description": "IMGT unique gene nomenclature",
                "format": "[LOCUS][GROUP][SUBGROUP]*[ALLELE]",
                "example": "IGHV1-2*01",
                "components": {
                    "LOCUS": "IG (immunoglobulin) or TR (T cell receptor)",
                    "CHAIN": "H (heavy), K (kappa), L (lambda), A (alpha), B (beta)",
                    "REGION": "V (variable), D (diversity), J (joining), C (constant)",
                },
            },
            "tools": {
                "IMGT/V-QUEST": "Sequence alignment to germline V genes",
                "IMGT/HighV-QUEST": "High-throughput sequence analysis",
                "IMGT/DomainGapAlign": "Domain annotation",
            },
            "urls": {
                "main": IMGT_BASE_URL,
                "gene_db": f"{IMGT_BASE_URL}/IMGT_GENE-DB/",
                "ligm_db": f"{IMGT_BASE_URL}/ligmdb/",
                "vquest": f"{IMGT_BASE_URL}/IMGT_vquest/",
            },
        }

        return {
            "status": "success",
            "data": gene_info,
            "metadata": {
                "source": "IMGT",
            },
        }
