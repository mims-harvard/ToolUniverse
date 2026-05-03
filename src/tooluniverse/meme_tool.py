"""
MEME Suite Tool

Provides access to the MEME Suite motif analysis web services at
https://meme-suite.org/meme/

The MEME Suite is the gold-standard toolkit for sequence motif analysis.
This tool wraps three core programs:

- FIMO (Find Individual Motif Occurrences): Scan sequences for known TF
  binding motifs from databases like JASPAR and HOCOMOCO. Returns binding
  sites with p-values, scores, and genomic coordinates.

- MEME (Multiple Em for Motif Elicitation): De novo motif discovery from
  a set of input sequences. Finds overrepresented sequence patterns that
  may correspond to TF binding sites, splice sites, or other regulatory
  elements.

- TOMTOM: Compare a query motif against a database of known motifs
  (JASPAR, HOCOMOCO, CIS-BP, etc.) to identify the transcription factor
  most likely to bind the discovered motif.

Additionally provides a local database listing endpoint that catalogs
available motif databases by category (no remote API call needed).

API pattern:
1. POST multipart form to https://meme-suite.org/meme/tools/{program}
2. Parse job ID from the HTML verification response
3. Poll status via GET .../info/status?service={PROGRAM}&id={job_id}&xml=1
   Status values: pending, active, done, failed, expired, unknown
4. Retrieve TSV/text results from .../opal-jobs/{job_id}/{output_file}

No authentication required. Free academic service.
"""

import re
import time
import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

MEME_BASE_URL = "https://meme-suite.org/meme"

# Motif database categories available on MEME Suite
# category_id -> {name, description, db_count}
MOTIF_DB_CATEGORIES = [
    {
        "id": 1,
        "name": "Eukaryote DNA",
        "count": 14,
        "description": "Curated eukaryotic TF motif collections including HOCOMOCO, Swiss Regulon, UniPROBE",
    },
    {
        "id": 2,
        "name": "Prokaryote DNA",
        "count": 5,
        "description": "Prokaryotic TF motif databases including RegTransBase and DPInteract",
    },
    {
        "id": 3,
        "name": "Methylcytosine DNA",
        "count": 1,
        "description": "Methylcytosine-aware TF binding motifs",
    },
    {
        "id": 4,
        "name": "JASPAR NON-REDUNDANT DNA",
        "count": 51,
        "description": "JASPAR CORE non-redundant TF binding profiles (2014-2026). Recommended for TF motif scanning.",
    },
    {
        "id": 5,
        "name": "JASPAR REDUNDANT DNA",
        "count": 51,
        "description": "JASPAR CORE redundant TF binding profiles (2014-2026)",
    },
    {
        "id": 6,
        "name": "JASPAR COLLECTIONS DNA",
        "count": 10,
        "description": "JASPAR specialized collections (PBM, CNE, POLII, PHYLOFACTS, SPLICE, etc.)",
    },
    {
        "id": 7,
        "name": "HOCOMOCO DNA",
        "count": 4,
        "description": "HOCOMOCO v12 human and mouse ortholog TF binding models. High-quality curated collection.",
    },
    {
        "id": 8,
        "name": "TFBSshape DNA",
        "count": 3,
        "description": "TFBSshape TF binding site shape-based motifs",
    },
    {
        "id": 9,
        "name": "CIS-BP 2.00 DNA",
        "count": 729,
        "description": "CIS-BP 2.00 single-species TF binding motifs (729 species)",
    },
    {
        "id": 10,
        "name": "CIS-BP 1.02 DNA",
        "count": 321,
        "description": "CIS-BP 1.02 single-species TF binding motifs (321 species)",
    },
    {
        "id": 11,
        "name": "ARABIDOPSIS DNA",
        "count": 2,
        "description": "Arabidopsis thaliana TF binding motifs (AthaMap, AGRIS)",
    },
    {
        "id": 12,
        "name": "ECOLI DNA",
        "count": 2,
        "description": "Escherichia coli TF binding motifs (DPInteract, RegTransBase)",
    },
    {
        "id": 13,
        "name": "FLY DNA",
        "count": 6,
        "description": "Drosophila melanogaster TF binding motifs (DMMPMM, FlyFactorSurvey, etc.)",
    },
    {
        "id": 14,
        "name": "HUMAN DNA",
        "count": 4,
        "description": "Human TF binding motifs (TRANSFAC, Zhao2011, Wei2010, Jolma2013)",
    },
    {
        "id": 15,
        "name": "MALARIA DNA",
        "count": 1,
        "description": "Plasmodium falciparum TF binding motifs",
    },
    {
        "id": 16,
        "name": "MOUSE DNA",
        "count": 3,
        "description": "Mus musculus TF binding motifs (UniPROBE, Chen2008)",
    },
    {
        "id": 17,
        "name": "WORM DNA",
        "count": 1,
        "description": "Caenorhabditis elegans TF binding motifs",
    },
    {
        "id": 18,
        "name": "YEAST DNA",
        "count": 4,
        "description": "Saccharomyces cerevisiae TF binding motifs (SCPD, MacIsaac, etc.)",
    },
    {
        "id": 19,
        "name": "CISBP-RNA RNA",
        "count": 729,
        "description": "CIS-BP RNA binding protein motifs (single species)",
    },
    {
        "id": 21,
        "name": "RNA",
        "count": 3,
        "description": "RNA binding protein motifs (Ray2013, etc.)",
    },
]

# Popular JASPAR database listings
JASPAR_DB_LISTINGS = {
    "JASPAR2026_vertebrates": {
        "category": 4,
        "listing": 22,
        "description": "JASPAR CORE 2026 vertebrates (non-redundant)",
    },
    "JASPAR2026_all": {
        "category": 4,
        "listing": 21,
        "description": "JASPAR CORE 2026 all species (non-redundant)",
    },
    "JASPAR2024_vertebrates": {
        "category": 4,
        "listing": 30,
        "description": "JASPAR CORE 2024 vertebrates (non-redundant)",
    },
    "HOCOMOCO_v12": {
        "category": 7,
        "listing": 1,
        "description": "HOCOMOCO v12 human and mouse CORE motifs",
    },
}


def _build_meme_motif_text(motif_name, matrix_rows, alphabet="ACGT"):
    """Build a minimal MEME-format motif string from a probability matrix."""
    w = len(matrix_rows)
    header = (
        "MEME version 5\n\n"
        "ALPHABET= {}\n\n"
        "strands: + -\n\n"
        "Background letter frequencies\n"
        "A 0.25 C 0.25 G 0.25 T 0.25\n\n"
        "MOTIF {}\n"
        "letter-probability matrix: alength= {} w= {} nsites= 100 E= 0\n"
    ).format(alphabet, motif_name, len(alphabet), w)
    rows = "\n".join(" ".join("{:.2f}".format(v) for v in row) for row in matrix_rows)
    return header + rows


@register_tool("MEMETool")
class MEMETool(BaseTool):
    """
    Tool for motif analysis using the MEME Suite web services.

    Supports three core operations:
    - fimo_scan: Scan sequences for known TF binding motifs
    - discover_motifs: De novo motif discovery with MEME
    - tomtom_compare: Compare motifs against known databases
    - list_databases: List available motif databases (local, no API call)

    All operations except list_databases submit jobs to meme-suite.org
    and poll for results.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    def run(self, arguments):
        """Execute the MEME Suite tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "fimo_scan": self._fimo_scan,
            "discover_motifs": self._discover_motifs,
            "tomtom_compare": self._tomtom_compare,
            "list_databases": self._list_databases,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(operation_handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "MEME Suite request timed out. The server may be busy.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Could not connect to MEME Suite. Service may be temporarily unavailable.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "MEME Suite error: {}".format(str(e)),
            }

    # ─── FIMO ──────────────────────────────────────────────────────────

    def _fimo_scan(self, arguments):
        """
        Scan sequences for known TF binding motifs using FIMO.

        Submits a FIMO job with inline motifs (MEME format) or database
        motifs, polls for completion, and returns parsed TSV results.
        """
        sequences = arguments.get("sequences")
        if not sequences:
            return {
                "status": "error",
                "error": "Missing required parameter: sequences (FASTA format)",
            }

        # Build motif input
        motif_text = arguments.get("motif_text")
        if not motif_text:
            return {
                "status": "error",
                "error": "Missing required parameter: motif_text (MEME format motif)",
            }

        pvalue_threshold = arguments.get("pvalue_threshold", 0.0001)
        scan_rc = arguments.get("scan_rc", True)

        # Build form data
        form_data = {
            "motifs_source": (None, "text"),
            "motifs_alphabet": (None, "dna"),
            "motifs_text": (None, motif_text),
            "sequences_source": (None, "text"),
            "sequences_text": (None, sequences),
            "output_pv": (None, str(pvalue_threshold)),
            "email": (None, "tooluniverse@example.com"),
            "description": (None, "FIMO scan via ToolUniverse"),
            "background_source": (None, "uniform"),
            "search": (None, "Start Search"),
        }

        if not scan_rc:
            form_data["norc"] = (None, "1")

        # Submit
        try:
            resp = self.session.post(
                "{}/tools/fimo".format(MEME_BASE_URL),
                files=form_data,
                timeout=120,
            )
        except requests.exceptions.ReadTimeout:
            return {"status": "error", "error": "FIMO submission timed out"}

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": "FIMO submission returned HTTP {}".format(resp.status_code),
            }

        # Extract job ID
        job_id = self._extract_job_id(resp.text)
        if not job_id:
            # Check for error
            error_msg = self._extract_form_error(resp.text)
            if error_msg:
                return {"status": "error", "error": "FIMO error: {}".format(error_msg)}
            return {
                "status": "error",
                "error": "Failed to extract FIMO job ID from response",
            }

        service = "FIMO"

        # Poll for completion
        status = self._poll_job(service, job_id)
        if status == "failed":
            error_detail = self._get_job_error(job_id)
            return {
                "status": "error",
                "error": "FIMO job failed: {}".format(error_detail or "unknown error"),
            }
        if status != "done":
            return {
                "status": "error",
                "error": "FIMO job did not complete (status: {})".format(status),
            }

        # Fetch TSV results
        tsv_url = "{}/opal-jobs/{}/fimo.tsv".format(MEME_BASE_URL, job_id)
        try:
            tsv_resp = self.session.get(tsv_url, timeout=30, allow_redirects=True)
        except Exception as e:
            return {
                "status": "error",
                "error": "Failed to fetch FIMO results: {}".format(str(e)),
            }

        if tsv_resp.status_code != 200:
            return {
                "status": "error",
                "error": "FIMO results returned HTTP {}".format(tsv_resp.status_code),
            }

        # Parse TSV
        hits = self._parse_fimo_tsv(tsv_resp.text)

        return {
            "status": "success",
            "data": {
                "hits": hits,
                "total_hits": len(hits),
                "job_id": job_id,
                "pvalue_threshold": pvalue_threshold,
                "result_url": "{}/opal-jobs/{}/fimo.html".format(MEME_BASE_URL, job_id),
            },
        }

    # ─── MEME (de novo discovery) ──────────────────────────────────────

    def _discover_motifs(self, arguments):
        """
        Run de novo motif discovery using MEME.

        Requires multiple FASTA sequences (>= 2) as input. Discovers
        overrepresented sequence patterns.
        """
        sequences = arguments.get("sequences")
        if not sequences:
            return {
                "status": "error",
                "error": "Missing required parameter: sequences (FASTA format)",
            }

        nmotifs = arguments.get("nmotifs", 3)
        minw = arguments.get("minw", 6)
        maxw = arguments.get("maxw", 50)
        distribution = arguments.get("distribution", "zoops")
        scan_rc = arguments.get("scan_rc", True)

        # MEME background_source is numeric for Markov model order
        form_data = {
            "disc_mode": (None, "classic"),
            "alphabet_custom": (None, "0"),
            "sequences_source": (None, "text"),
            "sequences_text": (None, sequences),
            "dist": (None, distribution),
            "nmotifs": (None, str(nmotifs)),
            "email": (None, "tooluniverse@example.com"),
            "description": (None, "MEME discovery via ToolUniverse"),
            "background_source": (None, "0"),
            "minw": (None, str(minw)),
            "maxw": (None, str(maxw)),
            "search": (None, "Start Search"),
        }

        if not scan_rc:
            form_data["norc"] = (None, "1")

        try:
            resp = self.session.post(
                "{}/tools/meme".format(MEME_BASE_URL),
                files=form_data,
                timeout=120,
            )
        except requests.exceptions.ReadTimeout:
            return {"status": "error", "error": "MEME submission timed out"}

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": "MEME submission returned HTTP {}".format(resp.status_code),
            }

        job_id = self._extract_job_id(resp.text)
        if not job_id:
            error_msg = self._extract_form_error(resp.text)
            if error_msg:
                return {"status": "error", "error": "MEME error: {}".format(error_msg)}
            return {
                "status": "error",
                "error": "Failed to extract MEME job ID from response",
            }

        service = "MEME"

        # MEME can take longer - poll with longer max wait
        status = self._poll_job(service, job_id, max_wait=600, interval=10)
        if status == "failed":
            error_detail = self._get_job_error(job_id)
            return {
                "status": "error",
                "error": "MEME job failed: {}".format(error_detail or "unknown error"),
            }
        if status != "done":
            return {
                "status": "error",
                "error": "MEME job did not complete (status: {}). "
                "De novo discovery may need more time for large inputs.".format(status),
            }

        # Fetch text output
        txt_url = "{}/opal-jobs/{}/meme.txt".format(MEME_BASE_URL, job_id)
        try:
            txt_resp = self.session.get(txt_url, timeout=30, allow_redirects=True)
        except Exception as e:
            return {
                "status": "error",
                "error": "Failed to fetch MEME results: {}".format(str(e)),
            }

        if txt_resp.status_code != 200:
            return {
                "status": "error",
                "error": "MEME results returned HTTP {}".format(txt_resp.status_code),
            }

        # Parse MEME text output
        motifs = self._parse_meme_text(txt_resp.text)

        return {
            "status": "success",
            "data": {
                "motifs": motifs,
                "total_motifs": len(motifs),
                "job_id": job_id,
                "parameters": {
                    "nmotifs": nmotifs,
                    "minw": minw,
                    "maxw": maxw,
                    "distribution": distribution,
                },
                "result_url": "{}/opal-jobs/{}/meme.html".format(MEME_BASE_URL, job_id),
            },
        }

    # ─── TOMTOM ────────────────────────────────────────────────────────

    def _tomtom_compare(self, arguments):
        """
        Compare a query motif against a database of known motifs using TOMTOM.

        The query motif must be in MEME format. Compares against a selected
        target database (JASPAR, HOCOMOCO, etc.).
        """
        query_motif = arguments.get("query_motif")
        if not query_motif:
            return {
                "status": "error",
                "error": "Missing required parameter: query_motif (MEME format)",
            }

        # Target database
        target_db = arguments.get("target_db", "JASPAR2026_vertebrates")
        db_info = JASPAR_DB_LISTINGS.get(target_db)
        if not db_info:
            return {
                "status": "error",
                "error": "Unknown target_db '{}'. Available: {}".format(
                    target_db, list(JASPAR_DB_LISTINGS.keys())
                ),
            }

        evalue_threshold = arguments.get("evalue_threshold", 0.5)
        comparison_function = arguments.get("comparison_function", "pearson")

        form_data = {
            "query_motifs_source": (None, "text"),
            "query_motifs_alphabet": (None, "dna"),
            "query_motifs_text": (None, query_motif),
            "target_motifs_source": (None, str(db_info["category"])),
            "target_motifs_db_listing": (None, str(db_info["listing"])),
            "instant_run": (None, "1"),
            "comparison_function": (None, comparison_function),
            "thresh_type": (None, "evalue"),
            "thresh": (None, str(evalue_threshold)),
            "complete_scoring": (None, "1"),
            "email": (None, "tooluniverse@example.com"),
            "description": (None, "TOMTOM comparison via ToolUniverse"),
            "search": (None, "Start Search"),
        }

        try:
            resp = self.session.post(
                "{}/tools/tomtom".format(MEME_BASE_URL),
                files=form_data,
                timeout=120,
            )
        except requests.exceptions.ReadTimeout:
            return {"status": "error", "error": "TOMTOM submission timed out"}

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": "TOMTOM submission returned HTTP {}".format(resp.status_code),
            }

        # Check for immediate error
        error_msg = self._extract_form_error(resp.text)
        if error_msg:
            return {"status": "error", "error": "TOMTOM error: {}".format(error_msg)}

        job_id = self._extract_job_id(resp.text)
        if not job_id:
            return {
                "status": "error",
                "error": "Failed to extract TOMTOM job ID from response",
            }

        service = "TOMTOM"

        # TOMTOM runs on short queue, should be fast
        status = self._poll_job(service, job_id, max_wait=300, interval=5)
        if status == "failed":
            error_detail = self._get_job_error(job_id)
            return {
                "status": "error",
                "error": "TOMTOM job failed: {}".format(
                    error_detail or "unknown error"
                ),
            }
        if status != "done":
            return {
                "status": "error",
                "error": "TOMTOM job did not complete (status: {})".format(status),
            }

        # Fetch TSV results
        tsv_url = "{}/opal-jobs/{}/tomtom.tsv".format(MEME_BASE_URL, job_id)
        try:
            tsv_resp = self.session.get(tsv_url, timeout=30, allow_redirects=True)
        except Exception as e:
            return {
                "status": "error",
                "error": "Failed to fetch TOMTOM results: {}".format(str(e)),
            }

        if tsv_resp.status_code != 200:
            return {
                "status": "error",
                "error": "TOMTOM results returned HTTP {}".format(tsv_resp.status_code),
            }

        # Parse TSV
        matches = self._parse_tomtom_tsv(tsv_resp.text)

        return {
            "status": "success",
            "data": {
                "matches": matches,
                "total_matches": len(matches),
                "job_id": job_id,
                "target_database": target_db,
                "evalue_threshold": evalue_threshold,
                "result_url": "{}/opal-jobs/{}/tomtom.html".format(
                    MEME_BASE_URL, job_id
                ),
            },
        }

    # ─── List databases ────────────────────────────────────────────────

    def _list_databases(self, arguments):
        """List available motif databases on MEME Suite (local data, no API call)."""
        category_filter = arguments.get("category_filter")

        categories = MOTIF_DB_CATEGORIES
        if category_filter:
            categories = [
                c
                for c in categories
                if category_filter.lower() in c["name"].lower()
                or category_filter.lower() in c["description"].lower()
            ]

        # Also include the shortcut database names
        db_shortcuts = [
            {
                "name": k,
                "description": v["description"],
                "category_id": v["category"],
                "listing_id": v["listing"],
            }
            for k, v in JASPAR_DB_LISTINGS.items()
        ]

        return {
            "status": "success",
            "data": {
                "categories": categories,
                "total_categories": len(categories),
                "database_shortcuts": db_shortcuts,
                "note": "Use category IDs with FIMO/TOMTOM. Database shortcuts can be used directly with the target_db parameter in tomtom_compare.",
            },
        }

    # ─── Shared helpers ────────────────────────────────────────────────

    def _extract_job_id(self, html):
        """Extract job ID from the MEME Suite verification response."""
        # Pattern: "id": "appFIMO_5.5.91772090284184-1332521127"
        match = re.search(r'"id":\s*"(app[^"]+)"', html)
        if match:
            return match.group(1)
        return None

    def _extract_form_error(self, html):
        """Extract error message from a MEME Suite form error response."""
        if "Problems with request" in html:
            errors = re.findall(r"<li>(.*?)</li>", html, re.S)
            if errors:
                return "; ".join(re.sub(r"<[^>]+>", "", e).strip() for e in errors)
        # Also check for HTTP 500 servlet errors
        msg_match = re.search(r"<b>Message</b>\s*(.*?)</p>", html, re.S)
        if msg_match:
            return re.sub(r"<[^>]+>", "", msg_match.group(1)).strip()
        return None

    def _poll_job(self, service, job_id, max_wait=300, interval=5):
        """
        Poll MEME Suite job status until completion.

        Status values: pending, active, done, failed, expired, unknown
        """
        status_url = "{}/info/status?service={}&id={}&xml=1".format(
            MEME_BASE_URL, service, job_id
        )
        elapsed = 0
        while elapsed < max_wait:
            try:
                resp = self.session.get(status_url, timeout=30)
                if resp.status_code == 200:
                    # Parse XML status
                    status_match = re.search(r"<status>(.*?)</status>", resp.text)
                    if status_match:
                        status = status_match.group(1).strip()
                        if status in ("done", "failed", "expired", "unknown"):
                            return status
            except Exception:
                pass  # Network blip, retry

            time.sleep(interval)
            elapsed += interval

        return "timeout"

    def _get_job_error(self, job_id):
        """Fetch error details from a failed job's index.html."""
        url = "{}/opal-jobs/{}/index.html".format(MEME_BASE_URL, job_id)
        try:
            resp = self.session.get(url, timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                # Extract error messages from <li> tags
                errors = re.findall(r"<li>(.*?)</li>", resp.text, re.S)
                if errors:
                    clean = [
                        re.sub(r"<[^>]+>", "", e).strip()
                        for e in errors
                        if "Error" in e
                        or "invalid" in e.lower()
                        or "failed" in e.lower()
                    ]
                    if clean:
                        return "; ".join(clean)
                    return "; ".join(re.sub(r"<[^>]+>", "", e).strip() for e in errors)
        except Exception:
            pass
        return None

    def _parse_fimo_tsv(self, tsv_text):
        """Parse FIMO TSV output into structured hits."""
        hits = []
        for line in tsv_text.strip().split("\n"):
            if line.startswith("#") or line.startswith("motif_id"):
                continue
            parts = line.split("\t")
            if len(parts) < 10:
                continue
            try:
                hit = {
                    "motif_id": parts[0],
                    "motif_alt_id": parts[1] if parts[1] else None,
                    "sequence_name": parts[2],
                    "start": int(parts[3]),
                    "stop": int(parts[4]),
                    "strand": parts[5],
                    "score": float(parts[6]),
                    "pvalue": float(parts[7]),
                    "qvalue": float(parts[8]),
                    "matched_sequence": parts[9],
                }
                hits.append(hit)
            except (ValueError, IndexError):
                continue
        return hits

    def _parse_tomtom_tsv(self, tsv_text):
        """Parse TOMTOM TSV output into structured matches."""
        matches = []
        for line in tsv_text.strip().split("\n"):
            if line.startswith("#") or line.startswith("Query_ID"):
                continue
            parts = line.split("\t")
            if len(parts) < 10:
                continue
            try:
                match = {
                    "query_id": parts[0],
                    "target_id": parts[1],
                    "optimal_offset": int(parts[2]),
                    "pvalue": float(parts[3]),
                    "evalue": float(parts[4]),
                    "qvalue": float(parts[5]),
                    "overlap": int(parts[6]),
                    "query_consensus": parts[7],
                    "target_consensus": parts[8],
                    "orientation": parts[9],
                }
                matches.append(match)
            except (ValueError, IndexError):
                continue
        return matches

    def _parse_meme_text(self, text):
        """Parse MEME text output to extract discovered motifs."""
        motifs = []

        # Find all MOTIF blocks
        # Pattern: MOTIF <consensus> MEME-<N>   width = <w>  sites = <s>  llr = <llr>  E-value = <e>
        motif_pattern = re.compile(
            r"MOTIF\s+(\S+)\s+MEME-(\d+)\s+width\s*=\s*(\d+)\s+"
            r"sites\s*=\s*(\d+)\s+llr\s*=\s*(\d+)\s+E-value\s*=\s*(\S+)"
        )

        # Find the simplified probability matrix sections
        matrix_pattern = re.compile(
            r"letter-probability matrix:.*?alength=\s*(\d+)\s+w=\s*(\d+).*?\n"
            r"((?:\s*[\d.]+(?:\s+[\d.]+)*\s*\n)+)",
            re.MULTILINE,
        )

        # Sites pattern: each line is like "seq1   +   7  ... TATAAAAG ..."
        re.compile(
            r"Motif\s+\S+\s+MEME-(\d+)\s+sites\s+sorted.*?\n-+\n"
            r"(.*?)\n-+",
            re.S,
        )

        for match in motif_pattern.finditer(text):
            consensus = match.group(1)
            motif_num = int(match.group(2))
            width = int(match.group(3))
            sites = int(match.group(4))
            llr = int(match.group(5))
            evalue_str = match.group(6)
            try:
                evalue = float(evalue_str)
            except ValueError:
                evalue = None

            motif_entry = {
                "motif_number": motif_num,
                "consensus": consensus,
                "width": width,
                "sites": sites,
                "log_likelihood_ratio": llr,
                "evalue": evalue,
            }

            motifs.append(motif_entry)

        # Try to extract probability matrices
        for i, matrix_match in enumerate(matrix_pattern.finditer(text)):
            if i < len(motifs):
                rows_text = matrix_match.group(3).strip()
                matrix = []
                for row_line in rows_text.split("\n"):
                    row_line = row_line.strip()
                    if row_line:
                        try:
                            matrix.append([float(x) for x in row_line.split()])
                        except ValueError:
                            continue
                if matrix:
                    motifs[i]["probability_matrix"] = matrix

        return motifs
