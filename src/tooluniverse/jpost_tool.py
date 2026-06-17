# jpost_tool.py
"""
jPOST (Japan ProteOme STandard Repository, jPOSTrepo) tool for ToolUniverse.

jPOST is a ProteomeXchange-member mass-spectrometry proteomics data
repository hosted in Japan. It exposes a standards-compliant PROXI
(PROteomics eXpression Interface) JSON API for browsing, searching, and
retrieving dataset metadata described with PSI-MS controlled-vocabulary
(CV) terms.

API:  https://repository.jpostdb.org/proxi/
No authentication / API key required. Free for all use.

Notable behaviors confirmed live (2026-06):
- /proxi/datasets supports keyword (`keywords=`), species scientific-name
  (`species=Homo sapiens`), and pagination (`pageSize`, `pageNumber`)
  filters. The keyword filter is best-effort: a non-matching keyword
  falls back to returning the full dataset list rather than an empty set,
  so results are filtered client-side as well.
- Pagination is 1-based; `pageNumber=0` returns an empty list upstream, so
  this tool clamps page numbers to a minimum of 1.
- /proxi/datasets/{accession} accepts the jPOST accession (e.g.
  JPST000004). The ProteomeXchange (PXD) accession is NOT accepted by this
  endpoint and returns 404.
"""

import re
import requests
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

JPOST_PROXI_BASE = "https://repository.jpostdb.org/proxi"

# Cap how many datasets a single search returns to keep payloads manageable.
MAX_PAGE_SIZE = 100


@register_tool("JPOSTTool")
class JPOSTTool(BaseTool):
    """
    Tool for querying the jPOST proteomics data repository via its PROXI
    JSON API.

    Provides dataset search and per-dataset metadata retrieval, including
    title, description, species, instruments, post-translational
    modifications, keywords, publications, submitters/contacts, and
    cross-references to the corresponding ProteomeXchange (PXD) accession.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_datasets"
        )

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the jPOST PROXI API call. Never raises."""
        arguments = arguments or {}
        try:
            if self.endpoint_type == "search_datasets":
                return self._search_datasets(arguments)
            elif self.endpoint_type == "get_dataset":
                return self._get_dataset(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint_type: {self.endpoint_type}",
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"jPOST API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to jPOST API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"jPOST API HTTP error: {code}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "jPOST API returned a non-JSON response.",
            }
        except Exception as e:  # noqa: BLE001 - run() must never raise
            return {
                "status": "error",
                "error": f"Unexpected error querying jPOST: {str(e)}",
            }

    # ------------------------------------------------------------------ #
    # CV-term helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _strip_html(val: Any) -> Any:
        if isinstance(val, str):
            return re.sub(r"<[^>]+>", "", val).strip()
        return val

    @staticmethod
    def _cv_value(
        terms: Any,
        accession: Optional[str] = None,
        name_match: Optional[str] = None,
    ) -> Optional[str]:
        """Return the value of a CV term by accession or partial name match."""
        if not isinstance(terms, list):
            return None
        for term in terms:
            if not isinstance(term, dict):
                continue
            if accession and term.get("accession") == accession:
                return term.get("value")
            if name_match and name_match.lower() in str(term.get("name", "")).lower():
                val = term.get("value")
                if val:
                    return val
        return None

    def _accession_pair(self, raw: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Extract jPOST + ProteomeXchange accessions from a dataset object."""
        acc_terms = raw.get("accession", [])
        jpost_id = self._cv_value(acc_terms, accession="MS:1002632")
        if not jpost_id:
            jpost_id = self._cv_value(acc_terms, name_match="jPOST")
        px_id = self._cv_value(acc_terms, accession="MS:1001919")
        if not px_id:
            px_id = self._cv_value(acc_terms, name_match="ProteomeXchange")
        return {"jpost_id": jpost_id, "px_id": px_id}

    def _species_names(self, raw: Dict[str, Any]) -> List[str]:
        names: List[str] = []
        for group in raw.get("species", []) or []:
            if not isinstance(group, dict):
                continue
            terms = group.get("terms", [])
            name = self._cv_value(terms, name_match="scientific name")
            if not name:
                name = self._cv_value(terms, name_match="taxonomy")
            if name and name not in names:
                names.append(name)
        return names

    def _instrument_names(self, raw: Dict[str, Any]) -> List[str]:
        names: List[str] = []
        for inst in raw.get("instruments", []) or []:
            if not isinstance(inst, dict):
                continue
            # Instruments may appear as flat dicts or as CV-term groups.
            name = inst.get("name")
            if name and name not in ("null", ""):
                if name not in names:
                    names.append(name)
                continue
            terms = inst.get("terms", [])
            cv_name = self._cv_value(terms, name_match="instrument")
            if cv_name and cv_name not in names:
                names.append(cv_name)
        return names

    def _modification_names(self, raw: Dict[str, Any]) -> List[str]:
        mods: List[str] = []
        for mod in raw.get("modifications", []) or []:
            if isinstance(mod, dict):
                name = mod.get("name") or self._cv_value(
                    mod.get("terms", []), name_match="modification"
                )
                if name and name not in mods:
                    mods.append(name)
        return mods

    def _keyword_list(self, raw: Dict[str, Any]) -> List[str]:
        kws: List[str] = []
        for kw in raw.get("keywords", []) or []:
            if isinstance(kw, dict):
                val = kw.get("value")
                if val and val not in kws:
                    kws.append(val)
            elif isinstance(kw, str) and kw:
                kws.append(kw)
        return kws

    def _publication_list(self, raw: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
        pubs: List[Dict[str, Optional[str]]] = []
        for pub in raw.get("publications", []) or []:
            if not isinstance(pub, dict):
                continue
            terms = pub.get("terms", [])
            pmid = self._cv_value(terms, name_match="PubMed")
            doi = self._cv_value(terms, name_match="Digital Object Identifier")
            if pmid or doi:
                pubs.append({"pubmed_id": pmid, "doi": doi})
        return pubs

    def _contact_list(self, raw: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
        contacts: List[Dict[str, Optional[str]]] = []
        for c in raw.get("contacts", []) or []:
            if not isinstance(c, dict):
                continue
            terms = c.get("terms", [])
            name = self._cv_value(terms, name_match="contact name")
            affiliation = self._cv_value(terms, name_match="contact affiliation")
            role = self._cv_value(terms, name_match="lab head") or self._cv_value(
                terms, name_match="submitter"
            )
            if name or affiliation:
                contacts.append(
                    {"name": name, "affiliation": affiliation, "role": role}
                )
        return contacts

    def _ftp_link(self, raw: Dict[str, Any]) -> Optional[str]:
        for link in raw.get("fullDatasetLinks", []) or []:
            if not isinstance(link, dict):
                continue
            if link.get("accession") == "MS:1002852" or "FTP" in str(
                link.get("name", "")
            ):
                val = link.get("value")
                if val:
                    return val
        return None

    def _summarize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten one PROXI dataset object into a compact summary."""
        ids = self._accession_pair(raw)
        return {
            "jpost_id": ids["jpost_id"],
            "px_id": ids["px_id"],
            "title": self._strip_html(raw.get("title", "")) or "",
            "description": self._strip_html(raw.get("description", "")) or "",
            "species": self._species_names(raw),
            "instruments": self._instrument_names(raw),
            "modifications": self._modification_names(raw),
            "keywords": self._keyword_list(raw),
            "publications": self._publication_list(raw),
            "contacts": self._contact_list(raw),
            "ftp_link": self._ftp_link(raw),
        }

    # ------------------------------------------------------------------ #
    # Endpoints
    # ------------------------------------------------------------------ #
    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search jPOST datasets by keyword and/or species."""
        keyword = arguments.get("keyword")
        species = arguments.get("species")

        try:
            page_size = int(arguments.get("page_size") or 10)
        except (TypeError, ValueError):
            page_size = 10
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))

        try:
            page_number = int(arguments.get("page_number") or 1)
        except (TypeError, ValueError):
            page_number = 1
        # jPOST PROXI pagination is 1-based; page 0 returns an empty list.
        page_number = max(1, page_number)

        params: Dict[str, Any] = {
            "pageSize": page_size,
            "pageNumber": page_number,
        }
        if keyword:
            params["keywords"] = keyword
        if species:
            params["species"] = species

        url = f"{JPOST_PROXI_BASE}/datasets"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        if isinstance(raw, dict):
            # Error payloads come back as a dict (e.g. {"status":400,...}).
            detail = raw.get("title") or raw.get("message") or raw.get("error")
            return {
                "status": "error",
                "error": f"jPOST search failed: {detail or 'unexpected response'}",
            }
        if not isinstance(raw, list):
            return {
                "status": "error",
                "error": "jPOST search returned an unexpected response shape.",
            }

        # The keyword filter is best-effort upstream; apply a client-side
        # filter so an unmatched keyword does not silently return everything.
        kw_lower = keyword.lower().strip() if isinstance(keyword, str) else ""

        datasets: List[Dict[str, Any]] = []
        for ds in raw:
            if not isinstance(ds, dict):
                continue
            summary = self._summarize(ds)
            if kw_lower:
                haystack = " ".join(
                    [
                        summary["title"],
                        summary["description"],
                        " ".join(summary["keywords"]),
                    ]
                ).lower()
                if kw_lower not in haystack:
                    continue
            datasets.append(summary)

        return {
            "status": "success",
            "data": datasets,
            "metadata": {
                "source": "jPOST/PROXI",
                "total_returned": len(datasets),
                "keyword": keyword or "(all)",
                "species": species or "(all)",
                "page_size": page_size,
                "page_number": page_number,
                "endpoint": "search_datasets",
            },
        }

    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a single jPOST dataset by its jPOST accession (e.g. JPST000004)."""
        accession = arguments.get("accession")
        if not accession or not str(accession).strip():
            return {
                "status": "error",
                "error": "accession parameter is required (e.g., 'JPST000004')",
            }
        accession = str(accession).strip()

        if accession.upper().startswith("PXD"):
            return {
                "status": "error",
                "error": (
                    "This endpoint only accepts jPOST accessions (JPSTxxxxxx). "
                    "ProteomeXchange (PXD) accessions are not accepted here; "
                    "search by keyword to find the matching jPOST accession."
                ),
            }

        url = f"{JPOST_PROXI_BASE}/datasets/{accession}"
        response = requests.get(url, timeout=self.timeout)

        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No jPOST dataset found for accession '{accession}'",
            }
        response.raise_for_status()
        raw = response.json()

        if not isinstance(raw, dict):
            return {
                "status": "error",
                "error": f"Unexpected response for accession '{accession}'",
            }
        if raw.get("status") == 404 or raw.get("title") == "Not Found":
            return {
                "status": "error",
                "error": f"No jPOST dataset found for accession '{accession}'",
            }

        summary = self._summarize(raw)

        return {
            "status": "success",
            "data": summary,
            "metadata": {
                "source": "jPOST/PROXI",
                "query": accession,
                "endpoint": "get_dataset",
            },
        }
