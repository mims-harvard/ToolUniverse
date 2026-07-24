# veupathdb_tool.py
"""
VEuPathDB WDK REST API tool for ToolUniverse.

VEuPathDB (https://veupathdb.org) is a family of eukaryotic-pathogen genome
databases sharing one EuPathDB WDK REST API shape. Member sites include
PlasmoDB (malaria), ToxoDB (toxoplasmosis), FungiDB, VectorBase, CryptoDB,
GiardiaDB, MicrosporidiaDB, PiroplasmaDB, TrichDB, TriTrypDB and AmoebaDB.

The real query API is POST-with-JSON-body (the shared GET-only BaseRESTTool
cannot reach it), so this tool wraps two operations:

  - search_genes_by_organism : POST .../record-types/gene/searches/
        GenesByTaxonGene/reports/standard   (find all genes for an organism)
  - get_gene_record          : POST .../record-types/gene/records
        (retrieve attributes for a single gene by primary key)

No authentication required. Free for academic/research use.
"""

import json
import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Each VEuPathDB member site shares the WDK API but lives under its own host
# and URL sub-directory, and stamps records with its own project_id value.
# Mapping: project key -> (host, service sub-directory, project_id).
VEUPATHDB_PROJECTS: Dict[str, Dict[str, str]] = {
    "plasmodb": {"host": "plasmodb.org", "subdir": "plasmo", "project_id": "PlasmoDB"},
    "toxodb": {"host": "toxodb.org", "subdir": "toxo", "project_id": "ToxoDB"},
    "fungidb": {"host": "fungidb.org", "subdir": "fungidb", "project_id": "FungiDB"},
    "vectorbase": {
        "host": "vectorbase.org",
        "subdir": "vectorbase",
        "project_id": "VectorBase",
    },
    "cryptodb": {
        "host": "cryptodb.org",
        "subdir": "cryptodb",
        "project_id": "CryptoDB",
    },
    "giardiadb": {
        "host": "giardiadb.org",
        "subdir": "giardiadb",
        "project_id": "GiardiaDB",
    },
    "microsporidiadb": {
        "host": "microsporidiadb.org",
        "subdir": "micro",
        "project_id": "MicrosporidiaDB",
    },
    "piroplasmadb": {
        "host": "piroplasmadb.org",
        "subdir": "piro",
        "project_id": "PiroplasmaDB",
    },
    "trichdb": {"host": "trichdb.org", "subdir": "trichdb", "project_id": "TrichDB"},
    "tritrypdb": {
        "host": "tritrypdb.org",
        "subdir": "tritrypdb",
        "project_id": "TriTrypDB",
    },
    "amoebadb": {"host": "amoebadb.org", "subdir": "amoeba", "project_id": "AmoebaDB"},
}

# Default attributes requested for gene records / search rows. All are valid
# columns on the WDK `gene` record type across member sites.
DEFAULT_GENE_ATTRIBUTES: List[str] = [
    "primary_key",
    "product",
    "organism",
    "gene_type",
    "location_text",
    "source_id",
]


@register_tool("VEuPathDBTool")
class VEuPathDBTool(BaseTool):
    """
    Tool for querying the VEuPathDB family of pathogen genome databases via
    their shared WDK REST API (POST with JSON body).

    Dispatch is by the operation named in the tool config (``fields.operation``
    or, as a fallback, inferred from the tool name). No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {}) or {}
        self.operation = fields.get("operation") or self._infer_operation()

    def _infer_operation(self) -> str:
        """Fallback: infer the operation from the tool name."""
        name = (self.tool_config.get("name") or "").lower()
        if "record" in name:
            return "get_gene_record"
        return "search_genes_by_organism"

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the VEuPathDB API call. Never raises; returns an envelope."""
        arguments = arguments or {}
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"VEuPathDB API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to VEuPathDB API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", "unknown")
            body = self._response_text(getattr(e, "response", None))
            return {
                "status": "error",
                "error": f"VEuPathDB API HTTP error {status}: {body}",
            }
        except Exception as e:  # noqa: BLE001 - run() must never raise
            return {
                "status": "error",
                "error": f"Unexpected error querying VEuPathDB: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.operation == "search_genes_by_organism":
            return self._search_genes_by_organism(arguments)
        if self.operation == "get_gene_record":
            return self._get_gene_record(arguments)
        return {
            "status": "error",
            "error": f"Unknown operation: {self.operation}",
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _resolve_project(self, arguments: Dict[str, Any]):
        """Resolve the project key to its site config, or return an error dict."""
        project = (arguments.get("project") or "plasmodb").strip().lower()
        site = VEUPATHDB_PROJECTS.get(project)
        if site is None:
            return None, {
                "status": "error",
                "error": (
                    f"Unknown project '{project}'. Valid projects: "
                    f"{', '.join(sorted(VEUPATHDB_PROJECTS))}."
                ),
            }
        return (project, site), None

    @staticmethod
    def _service_base(site: Dict[str, str]) -> str:
        return f"https://{site['host']}/{site['subdir']}/service"

    @staticmethod
    def _response_text(response) -> str:
        if response is None:
            return ""
        try:
            return response.text[:300]
        except Exception:  # noqa: BLE001
            return ""

    def _post_json(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """POST a JSON body to the WDK service and return the parsed payload.

        Raises on transport / HTTP errors; run() converts those to an envelope.
        """
        response = requests.post(
            url,
            json=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _attributes(arguments: Dict[str, Any]) -> List[str]:
        """Return the requested attribute list, defaulting and de-duplicating."""
        attrs = arguments.get("attributes")
        if not attrs:
            return list(DEFAULT_GENE_ATTRIBUTES)
        if isinstance(attrs, str):
            attrs = [a.strip() for a in attrs.split(",") if a.strip()]
        # primary_key is always useful; keep order, drop duplicates.
        seen, ordered = set(), []
        for a in ["primary_key", *attrs]:
            if a and a not in seen:
                seen.add(a)
                ordered.append(a)
        return ordered

    # ------------------------------------------------------------------ #
    # Operation: search genes by organism
    # ------------------------------------------------------------------ #
    def _search_genes_by_organism(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        organism = (arguments.get("organism") or "").strip()
        if not organism:
            return {
                "status": "error",
                "error": (
                    "organism parameter is required (full organism name, e.g. "
                    "'Plasmodium falciparum 3D7')."
                ),
            }

        resolved, err = self._resolve_project(arguments)
        if err:
            return err
        project, site = resolved

        attributes = self._attributes(arguments)
        try:
            limit = int(arguments.get("limit", 25))
        except (TypeError, ValueError):
            limit = 25
        limit = max(1, min(limit, 500))

        # The WDK `organism` param is a multi-pick vocabulary whose value is a
        # JSON-encoded array of organism term strings.
        body = {
            "searchConfig": {"parameters": {"organism": json.dumps([organism])}},
            "reportConfig": {
                "attributes": attributes,
                "tables": [],
                "pagination": {"offset": 0, "numRecords": limit},
            },
        }

        url = (
            f"{self._service_base(site)}/record-types/gene/searches/"
            "GenesByTaxonGene/reports/standard"
        )
        payload = self._post_json(url, body)

        rows = self._parse_search_records(payload.get("records", []))
        meta = payload.get("meta", {}) or {}
        total = meta.get("totalCount", meta.get("displayTotalCount"))

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "source": "VEuPathDB",
                "project": site["project_id"],
                "organism": organism,
                "total_count": total,
                "returned": len(rows),
                "attributes": attributes,
                "operation": "search_genes_by_organism",
            },
        }

    @staticmethod
    def _parse_search_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten WDK report `records` into clean attribute rows."""
        rows: List[Dict[str, Any]] = []
        for rec in records:
            attrs = dict(rec.get("attributes") or {})
            # The record id carries the primary-key parts; surface a flat id.
            for part in rec.get("id") or []:
                if part.get("name") == "source_id" and "source_id" not in attrs:
                    attrs["source_id"] = part.get("value")
            rows.append(VEuPathDBTool._clean_attrs(attrs))
        return rows

    # ------------------------------------------------------------------ #
    # Operation: get a single gene record
    # ------------------------------------------------------------------ #
    def _get_gene_record(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_id = (
            arguments.get("gene_id")
            or arguments.get("primary_key")
            or arguments.get("source_id")
            or ""
        ).strip()
        if not gene_id:
            return {
                "status": "error",
                "error": (
                    "gene_id (primary_key) parameter is required, e.g. 'PF3D7_0417200'."
                ),
            }

        resolved, err = self._resolve_project(arguments)
        if err:
            return err
        project, site = resolved

        attributes = self._attributes(arguments)
        body = {
            "primaryKey": [
                {"name": "source_id", "value": gene_id},
                {"name": "project_id", "value": site["project_id"]},
            ],
            "attributes": attributes,
            "tables": [],
        }

        url = f"{self._service_base(site)}/record-types/gene/records"
        payload = self._post_json(url, body)

        attrs = self._clean_attrs(dict(payload.get("attributes") or {}))
        if not attrs:
            return {
                "status": "error",
                "error": (
                    f"No gene record found for '{gene_id}' in {site['project_id']}."
                ),
            }

        return {
            "status": "success",
            "data": attrs,
            "metadata": {
                "source": "VEuPathDB",
                "project": site["project_id"],
                "gene_id": gene_id,
                "attributes": attributes,
                "operation": "get_gene_record",
            },
        }

    # ------------------------------------------------------------------ #
    # Shared cleanup
    # ------------------------------------------------------------------ #
    @staticmethod
    def _clean_attrs(attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Strip simple HTML markup the WDK adds to some display attributes."""
        cleaned: Dict[str, Any] = {}
        for key, value in attrs.items():
            if isinstance(value, str):
                value = (
                    value.replace("<i>", "")
                    .replace("</i>", "")
                    .replace("<b>", "")
                    .replace("</b>", "")
                    .strip()
                )
            cleaned[key] = value
        return cleaned
