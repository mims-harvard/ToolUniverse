# pfam_tool.py
"""
Pfam protein families tool for ToolUniverse.

Provides access to Pfam data via the InterPro API (Pfam is now hosted at InterPro):
- Search Pfam families by keyword
- Get detailed Pfam family information (description, counters, clan membership)
- Get proteins containing a Pfam domain (with optional species filter)
- Get Pfam annotations for a specific protein
- List Pfam clans (superfamilies) with search
- Get proteome distribution for a Pfam family

API: https://www.ebi.ac.uk/interpro/api/
No authentication required. Free public access.
"""

import re
import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool


INTERPRO_BASE_URL = "https://www.ebi.ac.uk/interpro/api"


class PfamTool(BaseTool):
    """
    Tool for Pfam protein family queries via the InterPro API.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search_families")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Pfam API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"InterPro/Pfam API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to InterPro/Pfam API",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                param = arguments.get(
                    "accession",
                    arguments.get("pfam_accession", arguments.get("query", "")),
                )
                return {
                    "status": "error",
                    "error": f"Not found in Pfam/InterPro: {param}",
                }
            if code == 204:
                return {"status": "error", "error": "No results found"}
            return {"status": "error", "error": f"InterPro/Pfam API HTTP error: {code}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Pfam API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "search_families":
            return self._search_families(arguments)
        elif self.endpoint == "get_family_detail":
            return self._get_family_detail(arguments)
        elif self.endpoint == "get_family_proteins":
            return self._get_family_proteins(arguments)
        elif self.endpoint == "get_protein_pfam":
            return self._get_protein_pfam(arguments)
        elif self.endpoint == "search_clans":
            return self._search_clans(arguments)
        elif self.endpoint == "get_family_proteomes":
            return self._get_family_proteomes(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        return re.sub(r"<[^>]+>", "", text).strip()

    def _search_families(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search Pfam families by keyword."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'kinase', 'zinc finger')",
            }

        max_results = min(arguments.get("max_results", 20), 100)

        url = f"{INTERPRO_BASE_URL}/entry/pfam/"
        params = {"search": query, "page_size": max_results}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        total = data.get("count", 0)
        results = data.get("results", [])

        families = []
        for r in results:
            meta = r.get("metadata", {})
            families.append(
                {
                    "accession": meta.get("accession", ""),
                    "name": meta.get("name", ""),
                    "type": meta.get("type", ""),
                    "integrated_interpro": meta.get("integrated"),
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query,
                "total_results": total,
                "returned": len(families),
                "families": families,
            },
            "metadata": {
                "source": "InterPro API (Pfam family search)",
                "query": query,
            },
        }

    def _get_family_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific Pfam family."""
        pfam_acc = arguments.get("pfam_accession", "")
        if not pfam_acc:
            return {
                "status": "error",
                "error": "pfam_accession parameter is required (e.g., 'PF00001')",
            }

        url = f"{INTERPRO_BASE_URL}/entry/pfam/{pfam_acc}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        meta = data.get("metadata", {})
        name_info = meta.get("name", {})
        if isinstance(name_info, dict):
            full_name = name_info.get("name", "")
            short_name = name_info.get("short", "")
        else:
            full_name = str(name_info)
            short_name = ""

        # Extract description text
        desc_list = meta.get("description", [])
        description = ""
        if desc_list and isinstance(desc_list, list):
            description = self._strip_html(desc_list[0].get("text", ""))

        # Extract counters
        counters = meta.get("counters", {})

        # Extract set/clan info
        set_info = meta.get("set_info", {})
        clan_accession = set_info.get("accession") if set_info else None
        clan_name = set_info.get("name") if set_info else None

        # Extract representative structure
        rep_struct = meta.get("representative_structure", {})

        # Extract Wikipedia
        wiki = meta.get("wikipedia", [])
        wikipedia_title = wiki[0].get("title", "") if wiki else None

        # Extract literature count
        lit = meta.get("literature", {})
        literature_count = len(lit) if lit else 0

        # Extract GO terms
        go_terms = meta.get("go_terms", []) or []

        return {
            "status": "success",
            "data": {
                "accession": meta.get("accession", ""),
                "name": full_name,
                "short_name": short_name,
                "type": meta.get("type", ""),
                "source_database": meta.get("source_database", ""),
                "integrated_interpro": meta.get("integrated"),
                "description": description[:2000] if description else None,
                "clan_accession": clan_accession,
                "clan_name": clan_name,
                "counters": {
                    "proteins": counters.get("proteins", 0),
                    "structures": counters.get("structures", 0),
                    "taxa": counters.get("taxa", 0),
                    "proteomes": counters.get("proteomes", 0),
                    "domain_architectures": counters.get("domain_architectures", 0),
                    "matches": counters.get("matches", 0),
                },
                "representative_structure": {
                    "pdb_id": rep_struct.get("accession"),
                    "name": rep_struct.get("name"),
                }
                if rep_struct
                else None,
                "wikipedia_title": wikipedia_title,
                "literature_count": literature_count,
                "go_terms": go_terms[:20] if go_terms else [],
            },
            "metadata": {
                "source": "InterPro API (Pfam family detail)",
                "pfam_accession": pfam_acc,
            },
        }

    def _get_family_proteins(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get proteins containing a specific Pfam domain, optionally filtered by species."""
        pfam_acc = arguments.get("pfam_accession", "")
        if not pfam_acc:
            return {
                "status": "error",
                "error": "pfam_accession parameter is required (e.g., 'PF00001')",
            }

        max_results = min(arguments.get("max_results", 20), 100)
        reviewed_only = arguments.get("reviewed_only", True)
        tax_id = arguments.get("tax_id", None)

        db = "reviewed" if reviewed_only else "uniprot"

        if tax_id:
            url = f"{INTERPRO_BASE_URL}/protein/{db}/entry/pfam/{pfam_acc}/taxonomy/uniprot/{tax_id}/"
        else:
            url = f"{INTERPRO_BASE_URL}/protein/{db}/entry/pfam/{pfam_acc}/"

        params = {"page_size": max_results}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        total = data.get("count", 0)
        results = data.get("results", [])

        proteins = []
        for r in results:
            meta = r.get("metadata", {})
            organism = meta.get("source_organism", {})
            entries = r.get("entries", [])

            # Get domain positions
            domain_positions = []
            for entry in entries:
                if entry.get("accession", "").upper() == pfam_acc.upper():
                    for loc in entry.get("entry_protein_locations", []):
                        for frag in loc.get("fragments", []):
                            domain_positions.append(
                                {
                                    "start": frag.get("start"),
                                    "end": frag.get("end"),
                                }
                            )

            proteins.append(
                {
                    "accession": meta.get("accession", ""),
                    "name": meta.get("name", ""),
                    "gene": meta.get("gene"),
                    "length": meta.get("length"),
                    "organism": organism.get("scientificName") if organism else None,
                    "tax_id": organism.get("taxId") if organism else None,
                    "domain_positions": domain_positions,
                    "in_alphafold": meta.get("in_alphafold", False),
                }
            )

        return {
            "status": "success",
            "data": {
                "pfam_accession": pfam_acc,
                "total_proteins": total,
                "returned": len(proteins),
                "reviewed_only": reviewed_only,
                "tax_id_filter": tax_id,
                "proteins": proteins,
            },
            "metadata": {
                "source": "InterPro API (Pfam family proteins)",
                "pfam_accession": pfam_acc,
            },
        }

    def _get_protein_pfam(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all Pfam domain annotations for a specific protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., 'P04637')",
            }

        url = f"{INTERPRO_BASE_URL}/entry/pfam/protein/uniprot/{accession}"
        params = {"page_size": 50}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])

        domains = []
        protein_length = None

        for r in results:
            meta = r.get("metadata", {})
            name_info = meta.get("name", {})
            if isinstance(name_info, dict):
                name = name_info.get("name", "")
                short_name = name_info.get("short", "")
            else:
                name = str(name_info) if name_info else ""
                short_name = ""

            proteins = r.get("proteins", [])
            for p in proteins:
                if protein_length is None:
                    protein_length = p.get("protein_length")
                for loc in p.get("entry_protein_locations", []):
                    for frag in loc.get("fragments", []):
                        domains.append(
                            {
                                "pfam_accession": meta.get("accession", ""),
                                "name": name,
                                "short_name": short_name,
                                "type": meta.get("type", ""),
                                "integrated_interpro": meta.get("integrated"),
                                "start": frag.get("start"),
                                "end": frag.get("end"),
                                "score": loc.get("score"),
                            }
                        )

        # Sort domains by start position
        domains.sort(key=lambda d: d.get("start", 0))

        return {
            "status": "success",
            "data": {
                "accession": accession,
                "protein_length": protein_length,
                "domain_count": len(domains),
                "domains": domains,
            },
            "metadata": {
                "source": "InterPro API (Pfam annotations for protein)",
                "accession": accession,
            },
        }

    def _search_clans(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search Pfam clans (superfamilies)."""
        query = arguments.get("query", "")
        max_results = min(arguments.get("max_results", 20), 100)

        url = f"{INTERPRO_BASE_URL}/set/pfam/"
        params = {"page_size": max_results}
        if query:
            params["search"] = query

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        total = data.get("count", 0)
        results = data.get("results", [])

        clans = []
        for r in results:
            meta = r.get("metadata", {})
            clans.append(
                {
                    "accession": meta.get("accession", ""),
                    "name": meta.get("name", ""),
                    "source_database": meta.get("source_database", ""),
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query if query else "(all clans)",
                "total_results": total,
                "returned": len(clans),
                "clans": clans,
            },
            "metadata": {
                "source": "InterPro API (Pfam clan search)",
                "query": query,
            },
        }

    def _get_family_proteomes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get proteome distribution for a Pfam family."""
        pfam_acc = arguments.get("pfam_accession", "")
        if not pfam_acc:
            return {
                "status": "error",
                "error": "pfam_accession parameter is required (e.g., 'PF00001')",
            }

        max_results = min(arguments.get("max_results", 20), 100)

        url = f"{INTERPRO_BASE_URL}/proteome/uniprot/entry/pfam/{pfam_acc}/"
        params = {"page_size": max_results}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        total = data.get("count", 0)
        results = data.get("results", [])

        proteomes = []
        for r in results:
            meta = r.get("metadata", {})
            proteomes.append(
                {
                    "proteome_accession": meta.get("accession", ""),
                    "organism_name": meta.get("name", ""),
                    "taxonomy_id": meta.get("taxonomy"),
                    "is_reference": meta.get("is_reference", False),
                }
            )

        return {
            "status": "success",
            "data": {
                "pfam_accession": pfam_acc,
                "total_proteomes": total,
                "returned": len(proteomes),
                "proteomes": proteomes,
            },
            "metadata": {
                "source": "InterPro API (Pfam family proteomes)",
                "pfam_accession": pfam_acc,
            },
        }
