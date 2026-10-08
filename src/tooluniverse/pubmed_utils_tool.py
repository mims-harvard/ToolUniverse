"""PubMed helper tools: article ID conversion and citation lookup (NCBI).

* ``PubMed_convert_article_ids`` wraps the PMC ID Converter (PMID <-> PMCID <-> DOI).
  It only knows articles that are in PubMed Central; anything else comes back with
  ``found: false`` rather than an invented mapping.
* ``PubMed_lookup_article_by_citation`` wraps NCBI ECitMatch: journal, year, volume,
  first page and first-author surname go in, a PMID comes out.
"""

import re
from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

IDCONV_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
ECITMATCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/ecitmatch.cgi"
MAX_IDS = 200
MAX_CITATIONS = 100
USER_AGENT = "ToolUniverse/1.0 (+https://github.com/mims-harvard/ToolUniverse)"


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = re.split(r"[,\s]+", value.strip())
    return [str(v).strip() for v in value if str(v).strip()]


def _detect_id_type(identifier: str) -> str:
    if re.fullmatch(r"PMC\d+(\.\d+)?", identifier, re.I):
        return "pmcid"
    if re.fullmatch(r"10\.\d{4,9}/\S+", identifier):
        return "doi"
    if re.fullmatch(r"NIHMS\d+", identifier, re.I):
        return "mid"
    if identifier.isdigit():
        return "pmid"
    return ""


class _NCBIHelperTool(BaseTool):
    def __init__(self, tool_config: Dict[str, Any], timeout: int = 30):
        super().__init__(tool_config)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/json"}
        )

    def _get(self, url: str, params: Dict[str, Any]) -> requests.Response:
        return request_with_retry(
            self.session, "GET", url, params=params, timeout=self.timeout
        )


@register_tool("PubMedConvertIDsTool")
class PubMedConvertIDsTool(_NCBIHelperTool):
    """PMID / PMCID / DOI / NIH manuscript ID conversion via the PMC ID Converter."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ids = _as_list(arguments.get("ids"))
        if not ids:
            return {
                "status": "error",
                "error": "ids is required (PMIDs, PMCIDs or DOIs)",
            }
        if len(ids) > MAX_IDS:
            return {
                "status": "error",
                "error": f"At most {MAX_IDS} ids per call ({len(ids)} given)",
            }
        forced = (arguments.get("id_type") or "").strip().lower()
        if forced and forced not in ("pmid", "pmcid", "doi", "mid"):
            return {
                "status": "error",
                "error": "id_type must be one of pmid, pmcid, doi, mid",
            }

        groups: Dict[str, List[str]] = {}
        undetected = []
        for identifier in ids:
            kind = forced or _detect_id_type(identifier)
            if kind:
                groups.setdefault(kind, []).append(identifier)
            else:
                undetected.append(identifier)

        found: Dict[str, Dict[str, Any]] = {}
        for kind, members in groups.items():
            params = {
                "ids": ",".join(members),
                "idtype": kind,
                "format": "json",
                "tool": "ToolUniverse",
                "versions": "no",
            }
            try:
                response = self._get(IDCONV_URL, params)
                payload = response.json()
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"PMC ID Converter request failed: {e}",
                }
            if response.status_code != 200 or payload.get("status") == "error":
                detail = (
                    "; ".join(
                        err.get("message", "") for err in payload.get("errors", [])
                    )
                    or response.text[:200]
                )
                return {
                    "status": "error",
                    "error": f"PMC ID Converter rejected the request: {detail}",
                }
            for record in payload.get("records", []):
                found[str(record.get("requested-id"))] = record

        rows = []
        for identifier in ids:
            record = found.get(identifier)
            if record is None:
                rows.append(
                    {
                        "requested_id": identifier,
                        "found": False,
                        "pmid": None,
                        "pmcid": None,
                        "doi": None,
                        "error": "Could not tell whether this is a PMID, PMCID or DOI; "
                        "pass id_type"
                        if identifier in undetected
                        else "No response for this identifier",
                    }
                )
                continue
            ok = record.get("status") != "error"
            pmid = record.get("pmid")
            rows.append(
                {
                    "requested_id": identifier,
                    "found": ok,
                    "pmid": str(pmid) if pmid is not None else None,
                    "pmcid": record.get("pmcid"),
                    "doi": record.get("doi"),
                    "error": None if ok else record.get("errmsg"),
                }
            )
        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "source": "PMC ID Converter (NCBI)",
                "requested": len(ids),
                "found": sum(1 for r in rows if r["found"]),
                "note": "Only articles indexed in PubMed Central can be converted.",
            },
        }


_CITATION_FIELDS = ("journal", "year", "volume", "first_page", "author")


@register_tool("PubMedCitationLookupTool")
class PubMedCitationLookupTool(_NCBIHelperTool):
    """Find PMIDs from citation details with NCBI ECitMatch."""

    def _citations(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        citations = arguments.get("citations")
        if citations:
            return [dict(c) for c in citations if isinstance(c, dict)]
        if any(arguments.get(f) for f in _CITATION_FIELDS):
            return [{f: arguments.get(f) for f in _CITATION_FIELDS + ("key",)}]
        return []

    @staticmethod
    def _clean(value: Any) -> str:
        return re.sub(r"[|\r\n]+", " ", str(value if value is not None else "")).strip()

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        citations = self._citations(arguments)
        if not citations:
            return {
                "status": "error",
                "error": "Give journal, year, volume, first_page and author, "
                "or a list of such objects as citations",
            }
        if len(citations) > MAX_CITATIONS:
            return {
                "status": "error",
                "error": f"At most {MAX_CITATIONS} citations per call",
            }
        lines = []
        for index, citation in enumerate(citations):
            key = self._clean(citation.get("key")) or f"c{index + 1}"
            citation["key"] = key
            lines.append(
                "|".join(
                    [self._clean(citation.get(f)) for f in _CITATION_FIELDS] + [key, ""]
                )
            )
        try:
            response = self._get(
                ECITMATCH_URL,
                {"db": "pubmed", "retmode": "xml", "bdata": "\r".join(lines)},
            )
        except Exception as e:
            return {"status": "error", "error": f"ECitMatch request failed: {e}"}
        if response.status_code != 200:
            return {
                "status": "error",
                "error": f"ECitMatch returned HTTP {response.status_code}",
            }

        results = {}
        for line in response.text.splitlines():
            parts = line.rstrip().split("|")
            if len(parts) >= 7:
                results[parts[5]] = parts[6].strip()
        rows = []
        for citation in citations:
            outcome = results.get(citation["key"], "")
            row = {
                "key": citation["key"],
                "journal": citation.get("journal"),
                "year": citation.get("year"),
                "volume": citation.get("volume"),
                "first_page": citation.get("first_page"),
                "author": citation.get("author"),
                "pmid": None,
                "status": "not_found",
            }
            if outcome.isdigit():
                row.update(pmid=outcome, status="found")
            elif outcome.upper().startswith("AMBIGUOUS"):
                candidates = re.findall(r"\d+", outcome)
                row.update(status="ambiguous", candidates=candidates)
            elif outcome and outcome.upper() != "NOT_FOUND":
                row.update(status="error", error=outcome)
            rows.append(row)
        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "source": "NCBI ECitMatch",
                "requested": len(rows),
                "found": sum(1 for r in rows if r["status"] == "found"),
            },
        }
