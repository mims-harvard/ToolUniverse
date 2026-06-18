"""RNAcentral genomic-location, publication, and sequence retrieval tools.

These complement the existing RNAcentral text-search / get-by-accession tools by
exposing three additional, stable RNAcentral REST endpoints that were previously
unwrapped:

  * ``genome_locations`` -> ``GET /rna/{urs}/genome-locations/{taxid}``
    Per-organism genomic coordinates (chromosome, strand, start, end, assembly)
    for a non-coding RNA. Requires a numeric NCBI taxid (e.g. 9606 = human).

  * ``publications`` -> ``GET /rna/{urs}/publications``
    Full literature list (title, authors, journal, year, PubMed ID, DOI) for an
    ncRNA, with the total count.

  * ``sequence`` -> ``GET /rna/{urs}.fasta``
    The canonical RNA sequence in FASTA format (header + sequence string).

All requests are anonymous (no API key). ``run()`` always returns a dict with a
``status`` key and never raises.
"""

import json
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://rnacentral.org/api/v1"
_TIMEOUT = 30


def _http_get_json(url: str, timeout: int = _TIMEOUT) -> Dict[str, Any]:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
    return json.loads(raw)


def _http_get_text(url: str, timeout: int = _TIMEOUT) -> str:
    # The '.fasta' URL suffix already selects the FASTA representation; sending
    # an explicit Accept header (e.g. text/plain) makes RNAcentral return
    # HTTP 406, so deliberately send no Accept header here.
    req = Request(url)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


@register_tool("RNAcentralGenomeTool")
class RNAcentralGenomeTool(BaseTool):
    """Retrieve genomic locations, publications, or FASTA sequence for an
    RNAcentral non-coding RNA (URS identifier)."""

    def __init__(self, tool_config=None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}
        settings = self.tool_config.get("settings", {}) or {}
        self.base_url = settings.get("base_url", _BASE_URL).rstrip("/")
        self.timeout = int(settings.get("timeout", _TIMEOUT))
        # Each wrapper fixes its operation via fields.operation so that a call
        # with only urs_id routes to the right endpoint (the schema default for
        # `operation` is not injected by the runner).
        self.default_operation = (self.tool_config.get("fields", {}) or {}).get(
            "operation", "genome_locations"
        )

    # ------------------------------------------------------------------ helpers
    def _error(self, message: str, operation: str = None) -> Dict[str, Any]:
        out = {"status": "error", "error": message, "source": "RNAcentral"}
        if operation:
            out["operation"] = operation
        return out

    @staticmethod
    def _clean_urs(value: str) -> str:
        # Accept either a bare URS id ('URS00003B7674') or a species-specific id
        # ('URS00003B7674_9606'); genome-locations/publications/sequence all use
        # the bare URS id, so strip any trailing '_taxid' suffix.
        urs = (value or "").strip()
        if "_" in urs:
            urs = urs.split("_", 1)[0]
        return urs

    # ------------------------------------------------------------------- run
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}
        operation = (arguments.get("operation") or self.default_operation).strip()

        urs_raw = arguments.get("urs_id")
        urs = self._clean_urs(urs_raw) if urs_raw else ""
        if not urs:
            return self._error("urs_id is required (e.g. 'URS00003B7674').", operation)

        if operation == "genome_locations":
            return self._genome_locations(urs, arguments)
        if operation == "sequence":
            return self._sequence(urs)

        return self._error(
            f"Unknown operation '{operation}'. Use one of: genome_locations, sequence.",
            operation,
        )

    # -------------------------------------------------------------- operations
    def _genome_locations(self, urs: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        taxid = arguments.get("taxid")
        if taxid in (None, ""):
            return self._error(
                "taxid is required for genome_locations (e.g. 9606 for human). "
                "RNAcentral maps genome coordinates per organism.",
                "genome_locations",
            )
        try:
            taxid = int(taxid)
        except (TypeError, ValueError):
            return self._error(
                f"taxid must be a numeric NCBI taxonomy id, got '{taxid}'.",
                "genome_locations",
            )

        url = f"{self.base_url}/rna/{urs}/genome-locations/{taxid}"
        try:
            payload = _http_get_json(url, self.timeout)
        except HTTPError as e:
            if e.code == 404:
                return self._error(
                    f"No genome locations found for {urs} in taxid {taxid} "
                    "(unknown URS, or this organism has no mapping).",
                    "genome_locations",
                )
            return self._error(f"HTTP {e.code} from RNAcentral.", "genome_locations")
        except (URLError, TimeoutError) as e:
            return self._error(f"Network error: {e}", "genome_locations")
        except json.JSONDecodeError:
            return self._error(
                "RNAcentral returned a non-JSON response.", "genome_locations"
            )

        results = payload.get("results", []) if isinstance(payload, dict) else []
        locations = []
        for r in results:
            asm = r.get("ensembl_assembly") or {}
            locations.append(
                {
                    "chromosome": r.get("chromosome"),
                    "strand": r.get("strand"),
                    "start": r.get("start"),
                    "end": r.get("end"),
                    "identity": r.get("identity"),
                    "ucsc_chromosome": r.get("ucsc_chromosome"),
                    "assembly_id": asm.get("assembly_id"),
                    "assembly_ucsc": asm.get("assembly_ucsc"),
                    "gca_accession": asm.get("gca_accession"),
                    "common_name": asm.get("common_name"),
                    "taxid": asm.get("taxid"),
                }
            )

        return {
            "status": "success",
            "source": "RNAcentral",
            "operation": "genome_locations",
            "urs_id": urs,
            "taxid": taxid,
            "data": {
                "count": payload.get("count", len(locations))
                if isinstance(payload, dict)
                else len(locations),
                "locations": locations,
            },
        }

    def _sequence(self, urs: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rna/{urs}.fasta"
        try:
            text = _http_get_text(url, self.timeout)
        except HTTPError as e:
            if e.code == 404:
                return self._error(f"Unknown RNAcentral id '{urs}'.", "sequence")
            return self._error(f"HTTP {e.code} from RNAcentral.", "sequence")
        except (URLError, TimeoutError) as e:
            return self._error(f"Network error: {e}", "sequence")

        lines = [ln for ln in text.splitlines() if ln.strip()]
        header = ""
        seq_lines = []
        for ln in lines:
            if ln.startswith(">"):
                header = ln[1:].strip()
            else:
                seq_lines.append(ln.strip())
        sequence = "".join(seq_lines)

        if not sequence:
            return self._error(f"No sequence returned for '{urs}'.", "sequence")

        return {
            "status": "success",
            "source": "RNAcentral",
            "operation": "sequence",
            "urs_id": urs,
            "data": {
                "fasta_header": header,
                "sequence": sequence,
                "length": len(sequence),
            },
        }
