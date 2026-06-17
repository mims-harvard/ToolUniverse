# interpro_member_db_tool.py
"""
InterPro member-database browse tool for ToolUniverse.

The existing InterPro tools (InterProRESTTool / InterProEntryTool /
InterProDomainArchTool) only browse INTEGRATED InterPro source entries
(IPRxxxxxx accessions) and protein->domain mappings. They cannot look up a
member-database SIGNATURE directly, browse a member database's catalog, or
enumerate the experimentally-solved PDB structures that contain a domain.

This tool fills those gaps using the InterPro REST API:

  * get_member_entry  -> GET /entry/{db}/{accession}
      Detail for a single member-database signature
      (Pfam PF00069, SMART SM00002, PANTHER PTHR10000, CDD cd00001,
       NCBIfam NF000004, SUPERFAMILY/ssf SSF52540, CATH-Gene3D, PRINTS,
       HAMAP, PIRSF, PROSITE profiles, SFLD, AntiFam), including which
       integrated InterPro entry it maps to.

  * list_member_entries -> GET /entry/{db}/
      Browse / paginate the signatures within one member database.

  * get_structures_for_entry -> GET /structure/pdb/entry/interpro/{id}
      List PDB structures whose chains contain a given InterPro domain,
      with experiment type and resolution.

  * list_member_databases -> GET /entry/
      The member-database catalog with entry counts (integrated /
      unintegrated totals per database).

API: https://www.ebi.ac.uk/interpro/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


INTERPRO_BASE_URL = "https://www.ebi.ac.uk/interpro/api"

# Member databases recognised by the InterPro REST API (the slug used in URLs).
VALID_MEMBER_DBS = {
    "pfam",
    "smart",
    "panther",
    "cdd",
    "ncbifam",
    "ssf",  # SUPERFAMILY
    "cathgene3d",
    "prints",
    "hamap",
    "pirsf",
    "profile",  # PROSITE profiles
    "prosite",  # PROSITE patterns
    "sfld",
    "antifam",
}


@register_tool("InterProMemberDBTool")
class InterProMemberDBTool(BaseTool):
    """
    Browse InterPro member-database signatures, the member-database catalog,
    and the PDB structures that contain an InterPro domain.

    Complements existing InterPro tools (which only handle integrated
    IPRxxxxxx entries) by exposing the member-database (signature) layer
    and structure cross-references. No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_member_entry")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to the configured endpoint handler."""
        try:
            if self.endpoint == "get_member_entry":
                return self._get_member_entry(arguments)
            if self.endpoint == "list_member_entries":
                return self._list_member_entries(arguments)
            if self.endpoint == "get_structures_for_entry":
                return self._get_structures_for_entry(arguments)
            if self.endpoint == "list_member_databases":
                return self._list_member_databases(arguments)
            return {
                "status": "error",
                "error": f"Unknown endpoint: {self.endpoint}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "InterPro API request timed out",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to InterPro API",
            }
        except requests.exceptions.RequestException as exc:
            return {
                "status": "error",
                "error": f"InterPro API request failed: {exc}",
            }
        except (ValueError, KeyError, TypeError) as exc:
            return {
                "status": "error",
                "error": f"Failed to parse InterPro API response: {exc}",
            }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_db(db: Any) -> str:
        """Map common aliases to the InterPro REST member-database slug."""
        if not isinstance(db, str):
            return ""
        d = db.strip().lower()
        aliases = {
            "superfamily": "ssf",
            "supfam": "ssf",
            "scop": "ssf",
            "gene3d": "cathgene3d",
            "cath": "cathgene3d",
            "cath-gene3d": "cathgene3d",
            "tigrfam": "ncbifam",
            "tigrfams": "ncbifam",
            "ncbifams": "ncbifam",
            "prosite_patterns": "prosite",
            "prosite_profiles": "profile",
            "prosite-profiles": "profile",
        }
        return aliases.get(d, d)

    @staticmethod
    def _entry_name(name_field: Any) -> Any:
        """InterPro entry 'name' may be a string or a {name, short} dict."""
        if isinstance(name_field, dict):
            return name_field.get("name")
        return name_field

    @staticmethod
    def _clamp_page_size(value: Any, default: int = 20) -> int:
        """Clamp a requested page_size into the InterPro-allowed 1..100 range."""
        try:
            return max(1, min(int(value), 100))
        except (ValueError, TypeError):
            return default

    def _resolve_member_db(self, arguments: Dict[str, Any]):
        """Normalize + validate member_database. Returns (db, error_dict)."""
        db = self._normalize_db(arguments.get("member_database", ""))
        if not db:
            return None, {"status": "error", "error": "member_database is required"}
        if db not in VALID_MEMBER_DBS:
            return None, {
                "status": "error",
                "error": f"Unsupported member_database '{db}'. "
                f"Valid: {', '.join(sorted(VALID_MEMBER_DBS))}",
            }
        return db, None

    def _get(self, url: str, params: Dict[str, Any] = None):
        """GET with shared timeout; returns (json, error_dict). One of them is None."""
        resp = requests.get(url, params=params or {}, timeout=self.timeout)
        if resp.status_code == 404:
            return None, {
                "status": "error",
                "error": "Not found in InterPro (HTTP 404). "
                "Check the accession / database slug.",
            }
        if resp.status_code != 200:
            return None, {
                "status": "error",
                "error": f"InterPro API HTTP error: {resp.status_code}",
            }
        return resp.json(), None

    # ------------------------------------------------------------------ #
    # Endpoint: get_member_entry
    # ------------------------------------------------------------------ #
    def _get_member_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        db, err = self._resolve_member_db(arguments)
        if err:
            return err
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {"status": "error", "error": "accession is required"}

        url = f"{INTERPRO_BASE_URL}/entry/{db}/{accession}"
        payload, err = self._get(url)
        if err:
            return err

        meta = payload.get("metadata", {})
        counters = meta.get("counters", {}) or {}
        result = {
            "accession": meta.get("accession"),
            "name": self._entry_name(meta.get("name")),
            "source_database": meta.get("source_database"),
            "type": meta.get("type"),
            "integrated_interpro": meta.get("integrated"),
            "description": self._first_description(meta.get("description")),
            "go_terms": [
                {
                    "identifier": g.get("identifier"),
                    "name": g.get("name"),
                    "category": (g.get("category") or {}).get("name"),
                }
                for g in (meta.get("go_terms") or [])
            ],
            "counters": {
                "proteins": counters.get("proteins"),
                "structures": counters.get("structures"),
                "taxa": counters.get("taxa"),
            },
        }
        return {"status": "success", "data": result}

    @staticmethod
    def _first_description(desc: Any) -> Any:
        """Normalize the 'description' field to a single string.

        InterPro returns this in several shapes depending on the member
        database: a plain string, a list of HTML strings, or a dict with a
        'text' key (e.g. {"text": "<p>...</p>", "llm": false, ...}).
        """
        if isinstance(desc, list):
            desc = desc[0] if desc else None
        if isinstance(desc, dict):
            return desc.get("text")
        return desc

    # ------------------------------------------------------------------ #
    # Endpoint: list_member_entries
    # ------------------------------------------------------------------ #
    def _list_member_entries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        db, err = self._resolve_member_db(arguments)
        if err:
            return err

        page_size = self._clamp_page_size(arguments.get("page_size", 20))

        params = {"page_size": page_size}
        entry_type = arguments.get("entry_type")
        if entry_type:
            params["type"] = str(entry_type).strip().lower()

        url = f"{INTERPRO_BASE_URL}/entry/{db}/"
        payload, err = self._get(url, params)
        if err:
            return err

        entries = []
        for item in payload.get("results", []):
            meta = item.get("metadata", {})
            entries.append(
                {
                    "accession": meta.get("accession"),
                    "name": self._entry_name(meta.get("name")),
                    "type": meta.get("type"),
                    "integrated_interpro": meta.get("integrated"),
                }
            )
        result = {
            "member_database": db,
            "total_count": payload.get("count"),
            "returned": len(entries),
            "entries": entries,
        }
        return {"status": "success", "data": result}

    # ------------------------------------------------------------------ #
    # Endpoint: get_structures_for_entry
    # ------------------------------------------------------------------ #
    def _get_structures_for_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        interpro_id = (arguments.get("interpro_id") or "").strip().upper()
        if not interpro_id:
            return {"status": "error", "error": "interpro_id is required"}
        if not interpro_id.startswith("IPR"):
            return {
                "status": "error",
                "error": "interpro_id must be an InterPro accession like IPR000719",
            }

        page_size = self._clamp_page_size(arguments.get("page_size", 20))

        url = f"{INTERPRO_BASE_URL}/structure/pdb/entry/interpro/{interpro_id}/"
        payload, err = self._get(url, {"page_size": page_size})
        if err:
            return err

        structures = []
        for item in payload.get("results", []):
            meta = item.get("metadata", {})
            structures.append(
                {
                    "pdb_id": meta.get("accession"),
                    "title": meta.get("name"),
                    "experiment_type": meta.get("experiment_type"),
                    "resolution": meta.get("resolution"),
                }
            )
        result = {
            "interpro_id": interpro_id,
            "total_structures": payload.get("count"),
            "returned": len(structures),
            "structures": structures,
        }
        return {"status": "success", "data": result}

    # ------------------------------------------------------------------ #
    # Endpoint: list_member_databases
    # ------------------------------------------------------------------ #
    def _list_member_databases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{INTERPRO_BASE_URL}/entry/"
        payload, err = self._get(url)
        if err:
            return err

        entries = payload.get("entries", {})
        member_dbs = entries.get("member_databases", {}) or {}
        databases = [
            {"member_database": db, "entry_count": count}
            for db, count in member_dbs.items()
        ]
        result = {
            "databases": databases,
            "integrated_total": entries.get("integrated"),
            "unintegrated_total": entries.get("unintegrated"),
            "interpro_total": entries.get("interpro"),
            "all_total": entries.get("all"),
        }
        return {"status": "success", "data": result}
