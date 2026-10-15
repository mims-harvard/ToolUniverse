"""MouseMine search, falling back to MGI's own reports while MouseMine is down.

MouseMine is the InterMine front end over Mouse Genome Informatics data. Since
2026-10-03 every MouseMine endpoint has answered 504 Gateway Time-out, while the
InterMine registry still lists it as Running and in production -- an outage,
not a retirement. MGI itself is up, and it serves the same gene and allele
records as tab-separated reports:

    /marker/report.txt?nomen=Brca1   200   13 genes   (Trp53 22, insulin 164)
    /allele/report.txt?nomen=Brca1   200   272 alleles

So MouseMine stays the primary source and these reports answer only when it
fails with a server error, a timeout or a refused connection. A client error
from MouseMine is passed through unchanged, since that is about the request.
Every fallback response says it came from MGI.

Not used as a fallback: Alliance's search_autocomplete, which also carries MGI
data. It caps at ten results across all species and returned no mouse hit at
all for Tp53, insulin or CRISPR, and no alleles for anything -- a fallback that
quietly answers with almost nothing is worse than the outage it covers.

The result keeps MouseMine's shape, {totalHits, results: [{type, fields}]}.
MouseMine's internal object id and its relevance score have no MGI
equivalent, so they are left out rather than invented; neither is required.
"""

import csv
import io
from typing import Any, Dict, List, Optional

import requests

from .base_rest_tool import BaseRESTTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

MGI_BASE_URL = "https://www.informatics.jax.org"
MGI_MARKER_REPORT = f"{MGI_BASE_URL}/marker/report.txt"
MGI_ALLELE_REPORT = f"{MGI_BASE_URL}/allele/report.txt"

# MGI's Feature Type, as MouseMine names the same class.
_FEATURE_TO_MOUSEMINE_TYPE = {
    "protein coding gene": "ProteinCodingGene",
}


def _rows(tsv_text: str) -> List[Dict[str, str]]:
    """Parse an MGI report, whose lines end in a stray tab-and-CR."""
    cleaned = "\n".join(line.rstrip("\r\t") for line in tsv_text.splitlines())
    return [
        {key.strip(): (value or "").strip() for key, value in row.items() if key}
        for row in csv.DictReader(io.StringIO(cleaned), delimiter="\t")
    ]


@register_tool("MouseMineTool")
class MouseMineTool(BaseRESTTool):
    """A MouseMine search with an MGI fallback for gene and allele queries."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = super().run(arguments)
        if not self._mousemine_is_down(result):
            return result

        try:
            fallback = self._from_mgi(arguments)
        except requests.exceptions.RequestException:
            # Both down: report MouseMine's own error, which is the real one.
            return result
        if fallback is None:
            return result
        return fallback

    @staticmethod
    def _mousemine_is_down(result: Dict[str, Any]) -> bool:
        """A server error, a timeout or a refused connection -- not a 4xx."""
        if not isinstance(result, dict) or result.get("status") != "error":
            return False
        code = result.get("status_code")
        if isinstance(code, int):
            return 500 <= code < 600
        error = str(result.get("error", "")).lower()
        return any(
            marker in error
            for marker in ("timed out", "timeout", "connection", "unreachable")
        )

    def _mode(self) -> str:
        name = (self.tool_config.get("name") or "").lower()
        if "allele" in name:
            return "alleles"
        if "gene" in name:
            return "genes"
        return "both"

    def _report(self, url: str, query: str) -> List[Dict[str, str]]:
        session = requests.Session()
        try:
            response = request_with_retry(
                session, "GET", url, params={"nomen": query}, timeout=30
            )
        finally:
            session.close()
        response.raise_for_status()
        return _rows(response.text)

    def _from_mgi(self, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        query = str(arguments.get("q") or "").strip()
        if not query:
            return None
        try:
            size = max(1, int(arguments.get("size") or 10))
        except (TypeError, ValueError):
            size = 10

        mode = self._mode()
        results: List[Dict[str, Any]] = []
        total = 0

        if mode in ("genes", "both"):
            genes = self._report(MGI_MARKER_REPORT, query)
            total += len(genes)
            for row in genes:
                feature = row.get("Feature Type", "")
                results.append(
                    {
                        "type": _FEATURE_TO_MOUSEMINE_TYPE.get(feature, "Gene"),
                        "fields": {
                            "primaryIdentifier": row.get("MGI ID", ""),
                            "symbol": row.get("Symbol", ""),
                            "name": row.get("Name", ""),
                            "sequenceOntologyTerm.name": feature,
                            "organism.commonName": "mouse",
                        },
                    }
                )

        if mode in ("alleles", "both"):
            alleles = self._report(MGI_ALLELE_REPORT, query)
            total += len(alleles)
            for row in alleles:
                results.append(
                    {
                        "type": "Allele",
                        "fields": {
                            "primaryIdentifier": row.get("MGI Allele ID", ""),
                            "symbol": row.get("Allele Symbol", ""),
                            "name": row.get("Allele Name", ""),
                            "alleleType": row.get("Allele Type", ""),
                            "attributeString": row.get("Allele Attributes", ""),
                        },
                    }
                )

        # MGI's nomen search is fuzzy and returns alphabetically, so asking for
        # Brca1 alleles led with Abraxas1<em1(IMPC)Ccpcz> -- a related gene's
        # allele -- ahead of Brca1's own. An exact symbol, then an allele of
        # the queried gene (symbol "Brca1<...>"), then a prefix, then the rest.
        wanted = query.lower()

        def relevance(item):
            symbol = str(item["fields"].get("symbol", "")).lower()
            gene_part = symbol.split("<", 1)[0]
            if symbol == wanted:
                return 0
            if gene_part == wanted:
                return 1
            if symbol.startswith(wanted):
                return 2
            return 3

        results.sort(key=relevance)

        note = (
            "MouseMine is not responding (server error or timeout), so this "
            "came from Mouse Genome Informatics' own reports, which hold the "
            "same records. MouseMine's internal id and relevance score have no "
            "MGI equivalent and are omitted."
        )
        if mode == "both":
            note += (
                " Facet counts are not available from MGI's reports, so "
                "facets is empty."
            )
        return {
            "status": "success",
            "data": {
                "totalHits": total,
                "results": results[:size],
                **({"facets": {}} if mode == "both" else {}),
            },
            "metadata": {
                "source": "Mouse Genome Informatics (MouseMine fallback)",
                "fallback_reason": "MouseMine unavailable",
                "note": note,
            },
        }
