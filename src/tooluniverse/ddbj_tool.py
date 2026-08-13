# ddbj_tool.py
"""
DNA Data Bank of Japan (DDBJ) Search REST API tool for ToolUniverse.

DDBJ is the third member of the International Nucleotide Sequence Database
Collaboration (INSDC), alongside NCBI/GenBank and EMBL-EBI/ENA. ToolUniverse
wraps the other two extensively; this tool covers the Japanese member, whose
DRA/BioProject/BioSample records include submissions that are mirrored late
or indexed differently elsewhere.

It also reaches JGA (Japanese Genotype-phenotype Archive) study metadata,
Japan's controlled-access human archive.

API: https://ddbj.nig.ac.jp/search/entry/{type}/{accession}.json
No authentication required for public metadata.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

DDBJ_BASE_URL = "https://ddbj.nig.ac.jp/search/entry"

# Accession prefix -> DDBJ entry type, used to auto-detect the route.
ACCESSION_PREFIXES = [
    ("PRJD", "bioproject"),
    ("PRJ", "bioproject"),
    ("SAMD", "biosample"),
    ("JGAS", "jga-study"),
    ("DRP", "sra-study"),
    ("DRX", "sra-experiment"),
    ("DRR", "sra-run"),
    ("DRS", "sra-sample"),
]

VALID_TYPES = [
    "bioproject",
    "biosample",
    "sra-study",
    "sra-experiment",
    "sra-run",
    "sra-sample",
    "jga-study",
]


def _detect_type(accession: str) -> str:
    """Infer the DDBJ entry type from an accession prefix."""
    upper = accession.upper()
    for prefix, entry_type in ACCESSION_PREFIXES:
        if upper.startswith(prefix):
            return entry_type
    return ""


def _as_list(value: Any) -> List[Any]:
    """DDBJ returns scalar-ish fields as null, a scalar, or a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _organizations(value: Any) -> List[str]:
    """DDBJ returns organization as a list of dicts; keep the names."""
    out = []
    for org in _as_list(value):
        if isinstance(org, dict) and org.get("name"):
            out.append(org["name"])
        elif isinstance(org, str):
            out.append(org)
    return out


def _organism(value: Any) -> Dict[str, Any]:
    """Normalize the organism field, which DDBJ returns as {identifier, name}."""
    if isinstance(value, dict):
        return {"name": value.get("name"), "taxonomy_id": value.get("identifier")}
    if isinstance(value, str):
        return {"name": value, "taxonomy_id": None}
    return {"name": None, "taxonomy_id": None}


def _summarize_xrefs(xrefs: Any, limit: int = 25) -> List[Dict[str, Any]]:
    """Trim cross-references, which can run to thousands of runs per study."""
    items = xrefs if isinstance(xrefs, list) else []
    return [
        {
            "identifier": x.get("identifier"),
            "type": x.get("type"),
            "url": x.get("url"),
        }
        for x in items[:limit]
        if isinstance(x, dict)
    ]


@register_tool("DDBJTool")
class DDBJTool(BaseTool):
    """
    Tool for retrieving DDBJ records by accession.

    Supports BioProject, BioSample, DRA (study/experiment/run/sample), and
    JGA study entries. The entry type is inferred from the accession prefix
    unless given explicitly.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get("operation", "get_entry")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DDBJ API call."""
        try:
            if self.operation == "get_entry":
                return self._get_entry(arguments)
            elif self.operation == "get_cross_references":
                return self._get_cross_references(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DDBJ request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to DDBJ. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"DDBJ returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "DDBJ returned a non-JSON response",
            }
        except Exception as e:
            return {"status": "error", "error": f"Error querying DDBJ: {str(e)}"}

    def _fetch(self, accession: str, entry_type: str) -> Dict[str, Any]:
        """Fetch one entry, returning either the record or an error dict."""
        accession = accession.strip()
        if not entry_type:
            entry_type = _detect_type(accession)
        if not entry_type:
            return {
                "status": "error",
                "error": f"Could not infer a DDBJ entry type from '{accession}'. "
                f"Pass entry_type explicitly. Valid types: {', '.join(VALID_TYPES)}. "
                "Accession prefixes: PRJD*=bioproject, SAMD*=biosample, "
                "DRP*=sra-study, DRX*=sra-experiment, DRR*=sra-run, "
                "DRS*=sra-sample, JGAS*=jga-study.",
            }
        if entry_type not in VALID_TYPES:
            return {
                "status": "error",
                "error": f"Unknown entry_type '{entry_type}'. "
                f"Valid types: {', '.join(VALID_TYPES)}.",
            }

        url = f"{DDBJ_BASE_URL}/{entry_type}/{accession}.json"
        response = requests.get(url, timeout=self.timeout)
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No DDBJ {entry_type} record for accession '{accession}'. "
                "Check the accession and that the entry type matches its prefix.",
            }
        response.raise_for_status()
        return {"status": "success", "raw": response.json(), "entry_type": entry_type}

    def _get_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve a DDBJ record and return its curated summary fields."""
        accession = arguments.get("accession")
        if not accession:
            return {
                "status": "error",
                "error": "accession is required, e.g. 'DRP000001' (DRA study), "
                "'PRJDB3490' (BioProject), or 'JGAS000001' (JGA study).",
            }

        fetched = self._fetch(accession, arguments.get("entry_type") or "")
        if fetched.get("status") == "error":
            return fetched

        raw = fetched["raw"]
        entry_type = fetched["entry_type"]

        return {
            "status": "success",
            "data": {
                "identifier": raw.get("identifier"),
                "type": raw.get("type") or entry_type,
                "title": raw.get("title"),
                "description": raw.get("description"),
                "organism": _organism(raw.get("organism"))["name"],
                "taxonomy_id": _organism(raw.get("organism"))["taxonomy_id"],
                "organization": _organizations(raw.get("organization")),
                "status_field": raw.get("status"),
                "accessibility": raw.get("accessibility"),
                "date_created": raw.get("dateCreated"),
                "date_modified": raw.get("dateModified"),
                "date_published": raw.get("datePublished"),
                "library_strategy": _as_list(raw.get("libraryStrategy")),
                "library_source": _as_list(raw.get("librarySource")),
                "instrument_model": _as_list(raw.get("instrumentModel")),
                "platform": _as_list(raw.get("platform")),
                "url": raw.get("url"),
                "cross_reference_count": len(raw.get("dbXrefs") or []),
            },
            "metadata": {
                "accession": accession,
                "entry_type": entry_type,
                "source": "DNA Data Bank of Japan (DDBJ), INSDC member",
            },
        }

    def _get_cross_references(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the linked DDBJ records for an accession.

        Useful for walking a study to its experiments, runs, and samples, or
        back to its BioProject.
        """
        accession = arguments.get("accession")
        if not accession:
            return {
                "status": "error",
                "error": "accession is required, e.g. 'DRP000001'.",
            }

        fetched = self._fetch(accession, arguments.get("entry_type") or "")
        if fetched.get("status") == "error":
            return fetched

        raw = fetched["raw"]
        all_xrefs = raw.get("dbXrefs") or []

        type_filter = arguments.get("reference_type")
        if type_filter:
            wanted = type_filter.lower()
            all_xrefs = [
                x
                for x in all_xrefs
                if isinstance(x, dict) and (x.get("type") or "").lower() == wanted
            ]

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 200)

        counts: Dict[str, int] = {}
        for x in raw.get("dbXrefs") or []:
            if isinstance(x, dict):
                t = x.get("type") or "unknown"
                counts[t] = counts.get(t, 0) + 1

        return {
            "status": "success",
            "data": _summarize_xrefs(all_xrefs, limit),
            "metadata": {
                "accession": accession,
                "entry_type": fetched["entry_type"],
                "total_matching": len(all_xrefs),
                "counts_by_type": counts,
                "source": "DNA Data Bank of Japan (DDBJ), INSDC member",
            },
        }
