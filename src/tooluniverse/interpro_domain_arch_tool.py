# interpro_domain_arch_tool.py
"""
InterPro Domain Architecture tool for ToolUniverse.

Provides access to InterPro API endpoints for domain architecture analysis:
- Protein domain architecture with exact residue positions
- PDB structures containing a specific Pfam domain
- Pfam clan (superfamily) member families

API: https://www.ebi.ac.uk/interpro/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool


INTERPRO_BASE_URL = "https://www.ebi.ac.uk/interpro/api"


class InterProDomainArchTool(BaseTool):
    """
    Tool for InterPro domain architecture analysis via the InterPro API.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "protein_domain_architecture")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the InterPro API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"InterPro API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to InterPro API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                param = arguments.get(
                    "accession",
                    arguments.get(
                        "pfam_accession", arguments.get("clan_accession", "")
                    ),
                )
                return {"error": f"Not found in InterPro: {param}"}
            if code == 204:
                return {"error": "No results found"}
            return {"error": f"InterPro API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying InterPro API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "protein_domain_architecture":
            return self._get_protein_domain_architecture(arguments)
        elif self.endpoint == "structures_for_domain":
            return self._get_structures_for_domain(arguments)
        elif self.endpoint == "clan_members":
            return self._get_clan_members(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_protein_domain_architecture(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get Pfam domain architecture for a protein with exact positions."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession parameter is required (UniProt accession, e.g., 'P04637')"
            }

        url = f"{INTERPRO_BASE_URL}/entry/pfam/protein/uniprot/{accession}"
        params = {"page_size": 50, "format": "json"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        domains = []
        protein_length = None

        for r in results:
            metadata = r.get("metadata", {})
            name_info = metadata.get("name", {})
            name = (
                name_info.get("name", "")
                if isinstance(name_info, dict)
                else str(name_info)
            )

            proteins = r.get("proteins", [])
            for p in proteins:
                if protein_length is None:
                    protein_length = p.get("protein_length")
                for loc in p.get("entry_protein_locations", []):
                    for frag in loc.get("fragments", []):
                        domains.append(
                            {
                                "pfam_accession": metadata.get("accession", ""),
                                "name": name,
                                "type": metadata.get("type", ""),
                                "integrated_interpro": metadata.get("integrated"),
                                "start": frag.get("start"),
                                "end": frag.get("end"),
                                "score": loc.get("score"),
                            }
                        )

        # Sort domains by start position
        domains.sort(key=lambda d: d.get("start", 0))

        return {
            "data": {
                "accession": accession,
                "protein_length": protein_length,
                "domain_count": len(domains),
                "domains": domains,
            },
            "metadata": {
                "source": "InterPro API (Pfam domain architecture)",
                "accession": accession,
            },
        }

    def _get_structures_for_domain(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find PDB structures containing a specific Pfam domain."""
        pfam_acc = arguments.get("pfam_accession", "")
        if not pfam_acc:
            return {"error": "pfam_accession parameter is required (e.g., 'PF00870')"}

        max_results = min(arguments.get("max_results", 20), 200)

        url = f"{INTERPRO_BASE_URL}/structure/pdb/entry/pfam/{pfam_acc}"
        params = {"page_size": max_results, "format": "json"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        total = data.get("count", 0)
        results = data.get("results", [])

        structures = []
        for r in results:
            m = r.get("metadata", {})
            structures.append(
                {
                    "pdb_id": m.get("accession", ""),
                    "name": m.get("name"),
                    "experiment_type": m.get("experiment_type"),
                    "resolution": m.get("resolution"),
                }
            )

        return {
            "data": {
                "pfam_accession": pfam_acc,
                "total_structures": total,
                "returned": len(structures),
                "structures": structures,
            },
            "metadata": {
                "source": "InterPro API (structures for domain)",
                "pfam_accession": pfam_acc,
            },
        }

    def _get_clan_members(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get member families in a Pfam clan (superfamily)."""
        clan_acc = arguments.get("clan_accession", "")
        if not clan_acc:
            return {"error": "clan_accession parameter is required (e.g., 'CL0016')"}

        max_results = min(arguments.get("max_results", 50), 200)

        # First get clan metadata
        url = f"{INTERPRO_BASE_URL}/set/pfam/{clan_acc}"
        params = {"format": "json"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        clan_data = response.json()

        metadata = clan_data.get("metadata", {})
        name_info = metadata.get("name", {})
        clan_name = (
            name_info.get("name", "") if isinstance(name_info, dict) else str(name_info)
        )

        # Get member families from relationships
        relationships = metadata.get("relationships", {})
        nodes = relationships.get("nodes", [])

        members = []
        for node in nodes[:max_results]:
            members.append(
                {
                    "accession": node.get("accession", ""),
                    "short_name": node.get("short_name"),
                    "name": node.get("name"),
                    "type": node.get("type"),
                    "score": node.get("score"),
                }
            )

        # Sort by accession
        members.sort(key=lambda m: m.get("accession", ""))

        return {
            "data": {
                "clan_accession": clan_acc,
                "clan_name": clan_name,
                "description": metadata.get("description"),
                "member_count": len(members),
                "members": members,
            },
            "metadata": {
                "source": "InterPro API (Pfam clan members)",
                "clan_accession": clan_acc,
            },
        }
