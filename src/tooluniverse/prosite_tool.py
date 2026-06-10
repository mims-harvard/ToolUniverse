# prosite_tool.py
"""
PROSITE protein motif/domain database tool for ToolUniverse.

PROSITE is a database of protein domains, families and functional sites,
maintained by SIB Swiss Institute of Bioinformatics (ExPASy).

This tool provides:
1. Entry lookup: Retrieve PROSITE pattern/profile entries by accession (PS00xxx)
   using the ExPASy text format endpoint with parsing
2. Search: Search PROSITE entries by keyword via the EBI InterPro API
3. Scan sequence: Scan a raw amino acid sequence against all PROSITE patterns
   using the ScanProsite CGI with JSON output

APIs used:
- https://prosite.expasy.org/{accession}.txt (entry text format)
- https://www.ebi.ac.uk/interpro/api/entry/prosite (search via InterPro)
- https://prosite.expasy.org/cgi-bin/prosite/PSScan.cgi (sequence scanning)

No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("PROSITETool")
class PROSITETool(BaseTool):
    """
    Tool for querying the PROSITE protein motif/domain database.

    Supports four operations:
    - get_entry: Retrieve a PROSITE entry by accession (parses text format)
    - search: Search PROSITE entries by keyword (via InterPro API)
    - scan_sequence: Scan a protein sequence for PROSITE pattern matches
    - find_proteins_with_motif: Reverse scan - given a PROSITE signature
      accession, return all UniProtKB/Swiss-Prot proteins containing that motif
    """

    PROSITE_BASE_URL = "https://prosite.expasy.org"
    INTERPRO_BASE_URL = "https://www.ebi.ac.uk/interpro/api"
    SCANPROSITE_URL = "https://prosite.expasy.org/cgi-bin/prosite/PSScan.cgi"

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_entry")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PROSITE API call."""
        try:
            if self.endpoint == "get_entry":
                return self._get_entry(arguments)
            elif self.endpoint == "search":
                return self._search(arguments)
            elif self.endpoint == "scan_sequence":
                return self._scan_sequence(arguments)
            elif self.endpoint == "find_proteins_with_motif":
                return self._find_proteins_with_motif(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint: {self.endpoint}",
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PROSITE API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to PROSITE/InterPro API",
            }
        except requests.exceptions.ChunkedEncodingError:
            return {
                "status": "error",
                "error": (
                    "PROSITE scan response was truncated. This usually happens for "
                    "very frequent low-information signatures (SKIP-FLAG=TRUE, e.g. "
                    "PS00005, PS00008) scanned across the whole proteome. Try a more "
                    "specific signature accession."
                ),
            }
        except Exception as e:
            return {"status": "error", "error": f"PROSITE API error: {str(e)}"}

    def _parse_prosite_text(self, text: str) -> Dict[str, Any]:
        """
        Parse PROSITE text format into a structured dictionary.

        PROSITE text format uses two-letter tags:
        ID - Entry name and type
        AC - Accession number
        DT - Date stamps
        DE - Description
        PA - Pattern (for PATTERN type entries)
        MA - Matrix (for MATRIX/PROFILE type entries)
        CC - Comments (functional annotations, sites)
        PR - ProRule reference
        DO - Documentation reference
        DR - Database cross-references
        """
        entry = {}
        current_tag = None

        for line in text.strip().split("\n"):
            if line.startswith("//"):
                break

            tag = line[:2].strip()
            value = line[5:].strip() if len(line) > 5 else ""

            if tag:
                current_tag = tag

            if current_tag == "ID":
                parts = value.split(";")
                entry["entry_name"] = parts[0].strip()
                if len(parts) > 1:
                    entry["entry_type"] = parts[1].strip().rstrip(".")
            elif current_tag == "AC":
                entry["accession"] = value.rstrip(";").strip()
            elif current_tag == "DT":
                entry["dates"] = value.rstrip(";").strip()
            elif current_tag == "DE":
                entry["description"] = entry.get("description", "") + value
            elif current_tag == "PA":
                entry["pattern"] = entry.get("pattern", "") + value
            elif current_tag == "MA":
                # Skip matrix data (too large and technical)
                if "entry_type" not in entry or entry.get("entry_type") != "MATRIX":
                    pass
                entry["entry_type"] = "MATRIX"
            elif current_tag == "CC":
                cc = entry.get("comments", "")
                entry["comments"] = (cc + " " + value).strip() if cc else value
            elif current_tag == "PR":
                entry["prorule"] = value.rstrip(";").strip()
            elif current_tag == "DO":
                entry["documentation"] = value.rstrip(";").strip()
            elif current_tag == "DR":
                # Database cross-references - collect UniProt links
                if "cross_references" not in entry:
                    entry["cross_references"] = []
                # DR lines have comma-separated UniProt entries
                refs = [r.strip().rstrip(";") for r in value.split(",") if r.strip()]
                entry["cross_references"].extend(refs)

        # Parse comments for functional sites
        if "comments" in entry:
            sites = []
            cc = entry["comments"]
            for part in cc.split("/"):
                part = part.strip()
                if part.startswith("SITE="):
                    sites.append(part.replace("SITE=", ""))
            if sites:
                entry["functional_sites"] = sites
            # Check skip flag
            if "SKIP-FLAG=TRUE" in cc:
                entry["skip_flag"] = True

        # Limit cross_references to first 20
        if "cross_references" in entry and len(entry["cross_references"]) > 20:
            total = len(entry["cross_references"])
            entry["cross_references"] = entry["cross_references"][:20]
            entry["cross_references_note"] = (
                f"Showing 20 of {total} total cross-references"
            )

        return entry

    def _get_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve a PROSITE entry by accession."""
        accession = arguments.get("accession", "").strip()
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (e.g., PS00001, PS00028, PS51420)",
            }

        # Ensure accession has correct format
        acc_upper = accession.upper()
        if not acc_upper.startswith("PS"):
            return {
                "status": "error",
                "error": f"Invalid PROSITE accession: {accession}. Must start with 'PS' (e.g., PS00001)",
            }

        # Fetch text format from ExPASy
        url = f"{self.PROSITE_BASE_URL}/{acc_upper}.txt"
        response = requests.get(url, timeout=self.timeout)

        if response.status_code == 404:
            return {"status": "error", "error": f"PROSITE entry {acc_upper} not found"}
        response.raise_for_status()

        # Check if response is HTML (error page) instead of text
        content = response.text
        if content.strip().startswith("<!DOCTYPE") or content.strip().startswith(
            "<html"
        ):
            return {
                "status": "error",
                "error": f"PROSITE entry {acc_upper} not found (received HTML error page)",
            }

        # Parse text format
        entry = self._parse_prosite_text(content)
        if not entry:
            return {
                "status": "error",
                "error": f"Failed to parse PROSITE entry {acc_upper}",
            }

        return {
            "status": "success",
            "data": entry,
            "metadata": {
                "source": "PROSITE (ExPASy/SIB)",
                "accession": acc_upper,
                "url": f"https://prosite.expasy.org/{acc_upper}",
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PROSITE entries by keyword via InterPro API."""
        query = arguments.get("query", "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'zinc finger', 'kinase', 'glycosylation')",
            }

        limit = arguments.get("limit", 10)
        limit = min(max(1, limit), 50)

        # Use InterPro API to search PROSITE entries
        url = f"{self.INTERPRO_BASE_URL}/entry/prosite"
        params = {
            "search": query,
            "page_size": limit,
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        for result in data.get("results", []):
            if isinstance(result, dict):
                meta = result.get("metadata", {})
                name_obj = meta.get("name", {})
                if isinstance(name_obj, dict):
                    name = name_obj.get("name", "")
                    short_name = name_obj.get("short", "")
                else:
                    name = str(name_obj)
                    short_name = ""

                results.append(
                    {
                        "accession": meta.get("accession"),
                        "name": name,
                        "short_name": short_name,
                        "type": meta.get("type"),
                        "source_database": meta.get("source_database"),
                        "integrated_into": meta.get("integrated"),
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "PROSITE via InterPro API (EBI)",
                "query": query,
                "total_results": data.get("count", len(results)),
            },
        }

    def _scan_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Scan a protein sequence against all PROSITE patterns."""
        sequence = arguments.get("sequence", "").strip()
        if not sequence:
            return {
                "status": "error",
                "error": "sequence parameter is required (amino acid sequence)",
            }

        # Validate it looks like a protein sequence
        valid_aa = set("ACDEFGHIKLMNPQRSTVWYXBZJU")
        seq_clean = sequence.upper().replace(" ", "").replace("\n", "")
        if not all(c in valid_aa for c in seq_clean):
            return {
                "status": "error",
                "error": "Invalid protein sequence. Must contain only standard amino acid letters.",
            }

        skip = arguments.get("skip_frequent", True)

        # POST to ScanProsite CGI
        post_data = {
            "seq": seq_clean,
            "output": "json",
            "skip": "yes" if skip else "no",
        }

        response = requests.post(
            self.SCANPROSITE_URL, data=post_data, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        matches = []
        for m in data.get("matchset", []):
            matches.append(
                {
                    "signature_accession": m.get("signature_ac"),
                    "start": m.get("start"),
                    "end": m.get("stop"),
                    "score": m.get("score"),
                    "level": m.get("level"),
                }
            )

        return {
            "status": "success",
            "data": matches,
            "metadata": {
                "source": "ScanProsite (ExPASy/SIB)",
                "sequence_length": len(seq_clean),
                "total_matches": data.get("n_match", len(matches)),
                "skip_frequent_patterns": skip,
            },
        }

    def _find_proteins_with_motif(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse motif scan: given a PROSITE signature accession, return all
        UniProtKB/Swiss-Prot proteins that contain that motif, with positions.

        This is the inverse of the forward scan (protein -> its motifs): it
        enumerates the proteome occurrences of a single signature.
        """
        signature = (
            arguments.get("signature_ac")
            or arguments.get("accession")
            or arguments.get("sig")
            or ""
        ).strip()
        if not signature:
            return {
                "status": "error",
                "error": (
                    "signature_ac parameter is required "
                    "(PROSITE signature accession, e.g., PS00029)"
                ),
            }

        sig_upper = signature.upper()
        if not sig_upper.startswith("PS"):
            return {
                "status": "error",
                "error": (
                    f"Invalid PROSITE signature accession: {signature}. "
                    "Must start with 'PS' (e.g., PS00029)"
                ),
            }

        # Default Swiss-Prot; allow callers to widen to TrEMBL if desired.
        db = arguments.get("db", "sprot")
        if db not in ("sprot", "trembl", "uniprot"):
            db = "sprot"

        max_results = arguments.get("max_results", 50)
        try:
            max_results = int(max_results)
        except (TypeError, ValueError):
            max_results = 50
        max_results = min(max(1, max_results), 1000)

        # SKIP-FLAG=TRUE signatures (PS00005, PS00008, ...) are skipped by default
        # by ScanProsite and return no hits unless overridden. skip_frequent=False
        # sends skip=no so those very frequent patterns are included.
        skip_frequent = arguments.get("skip_frequent", True)

        post_data = {
            "sig": sig_upper,
            "db": db,
            "output": "json",
            "skip": "yes" if skip_frequent else "no",
        }

        response = requests.post(
            self.SCANPROSITE_URL, data=post_data, timeout=self.timeout
        )
        response.raise_for_status()

        content = response.text
        if content.strip().startswith("<!DOCTYPE") or content.strip().startswith(
            "<html"
        ):
            return {
                "status": "error",
                "error": (
                    f"ScanProsite returned an HTML page for signature {sig_upper}. "
                    "The signature accession may be invalid."
                ),
            }

        data = response.json()
        matchset = data.get("matchset", []) or []

        proteins = []
        for m in matchset[:max_results]:
            proteins.append(
                {
                    "sequence_ac": m.get("sequence_ac"),
                    "sequence_id": m.get("sequence_id"),
                    "sequence_db": m.get("sequence_db"),
                    "start": m.get("start"),
                    "stop": m.get("stop"),
                    "signature_ac": m.get("signature_ac"),
                    "signature_id": m.get("signature_id"),
                }
            )

        return {
            "status": "success",
            "data": proteins,
            "metadata": {
                "source": "ScanProsite (ExPASy/SIB)",
                "signature_ac": sig_upper,
                "database": db,
                "total_matches": data.get("n_match", len(matchset)),
                "total_sequences": data.get("n_seq"),
                "capped": bool(data.get("capped", 0)),
                "returned": len(proteins),
                "skip_frequent_patterns": skip_frequent,
            },
        }
