# mcsa_tool.py
"""
M-CSA (Mechanism and Catalytic Site Atlas) tool for ToolUniverse.

M-CSA is the EBI/Thornton curated atlas of enzyme catalytic machinery: for
~1,000 enzymes it records which residues perform catalysis, what role each
plays (nucleophile, proton donor, electrostatic stabiliser and so on), and
the reaction catalysed with its EC number.

ToolUniverse covers enzyme *function* through several routes (BRENDA, Rhea,
UniProt, InterPro) but nothing identifies the specific catalytic residues in
an active site. This tool fills that gap, which matters for interpreting
active-site mutations and for engineering work.

API: https://www.ebi.ac.uk/thornton-srv/m-csa/api
No authentication required.

Note on searching: the API's list endpoint ignores server-side filters and
returns ~14 KB per record, so search scans pages client-side under an
explicit page budget. Every response reports how much of the catalogue was
examined rather than silently truncating.
"""

from typing import Dict, Any, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MCSA_BASE_URL = "https://www.ebi.ac.uk/thornton-srv/m-csa/api"
_PAGE_SIZE = 100


def _residue_summary(residue: Dict[str, Any]) -> Dict[str, Any]:
    """Condense one catalytic residue record to its identity and roles."""
    chains = residue.get("residue_chains") or []
    first = chains[0] if chains and isinstance(chains[0], dict) else {}
    sequences = residue.get("residue_sequences") or []
    seq = sequences[0] if sequences and isinstance(sequences[0], dict) else {}
    roles = [
        r.get("function")
        for r in (residue.get("roles") or [])
        if isinstance(r, dict) and r.get("function")
    ]
    return {
        "code": first.get("code") or seq.get("code"),
        "pdb_id": first.get("pdb_id"),
        "chain": first.get("chain_name"),
        "residue_number": first.get("resid"),
        "uniprot_id": seq.get("uniprot_id"),
        "uniprot_position": seq.get("resid"),
        "roles": sorted(set(roles)),
        "roles_summary": residue.get("roles_summary") or None,
        "is_ptm": bool(residue.get("ptm")),
    }


def _entry_summary(entry: Dict[str, Any], with_residues: bool = True) -> Dict[str, Any]:
    """Condense one M-CSA entry."""
    reaction = entry.get("reaction") or {}
    summary = {
        "mcsa_id": entry.get("mcsa_id"),
        "enzyme_name": entry.get("enzyme_name"),
        "ec_numbers": entry.get("all_ecs") or [],
        "reference_uniprot_id": entry.get("reference_uniprot_id"),
        "description": (entry.get("description") or "").strip() or None,
        "url": entry.get("url"),
    }
    if isinstance(reaction, dict):
        summary["reaction_name"] = reaction.get("name")
    if with_residues:
        residues = [
            _residue_summary(r)
            for r in (entry.get("residues") or [])
            if isinstance(r, dict)
        ]
        summary["catalytic_residues"] = residues
        summary["catalytic_residue_count"] = len(residues)
    return summary


@register_tool("MCSATool")
class MCSATool(BaseTool):
    """
    Tool for retrieving enzyme catalytic site annotations from M-CSA.

    Supports fetching one entry by its M-CSA identifier, and searching the
    catalogue by enzyme name, EC number, or UniProt accession.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get("operation", "get_entry")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the M-CSA lookup."""
        try:
            if self.operation == "get_entry":
                return self._get_entry(arguments)
            if self.operation == "search_enzymes":
                return self._search_enzymes(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"M-CSA request timed out after {self.timeout}s. "
                "Reduce max_pages if you are searching.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to M-CSA. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"M-CSA returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "M-CSA returned a non-JSON response",
            }
        except Exception as e:
            return {"status": "error", "error": f"Error querying M-CSA: {str(e)}"}

    def _get_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one M-CSA entry by identifier."""
        mcsa_id = arguments.get("mcsa_id")
        if mcsa_id is None or str(mcsa_id).strip() == "":
            return {
                "status": "error",
                "error": "mcsa_id is required, e.g. 2 (class A beta-lactamase). "
                "Use MCSA_search_enzymes to find identifiers by name or EC.",
            }

        entry_id = str(mcsa_id).strip()
        response = requests.get(
            f"{MCSA_BASE_URL}/entries/{entry_id}/",
            params={"format": "json"},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No M-CSA entry with id '{entry_id}'. Identifiers run "
                "from 1 to roughly 1000.",
            }
        response.raise_for_status()
        entry = response.json()

        return {
            "status": "success",
            "data": _entry_summary(entry),
            "metadata": {
                "mcsa_id": entry.get("mcsa_id"),
                "source": "M-CSA (EBI/Thornton group)",
            },
        }

    def _matches(self, entry: Dict[str, Any], arguments: Dict[str, Any]) -> bool:
        """Test one entry against the supplied search criteria."""
        name = (arguments.get("enzyme_name") or "").lower()
        if name and name not in (entry.get("enzyme_name") or "").lower():
            return False

        ec_number = (arguments.get("ec_number") or "").strip()
        if ec_number:
            ecs = entry.get("all_ecs") or []
            if not any(str(e).startswith(ec_number) for e in ecs):
                return False

        uniprot = (arguments.get("uniprot_id") or "").strip().upper()
        if uniprot:
            if (entry.get("reference_uniprot_id") or "").upper() != uniprot:
                return False

        return True

    def _search_enzymes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Scan the catalogue for entries matching name, EC, or UniProt."""
        if not any(
            arguments.get(k) for k in ("enzyme_name", "ec_number", "uniprot_id")
        ):
            return {
                "status": "error",
                "error": "Provide at least one of enzyme_name, ec_number, or "
                "uniprot_id. Example: ec_number='3.5.2' for beta-lactamases.",
            }

        max_pages = arguments.get("max_pages")
        if not isinstance(max_pages, int) or max_pages <= 0:
            max_pages = 4
        max_pages = min(max_pages, 11)

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25

        matches: List[Dict[str, Any]] = []
        scanned = 0
        catalogue_size: Optional[int] = None
        pages_read = 0

        for page in range(1, max_pages + 1):
            response = requests.get(
                f"{MCSA_BASE_URL}/entries/",
                params={"format": "json", "page": page, "page_size": _PAGE_SIZE},
                timeout=self.timeout,
            )
            if response.status_code == 404:
                break
            response.raise_for_status()
            payload = response.json()
            catalogue_size = payload.get("count", catalogue_size)
            results = payload.get("results") or []
            if not results:
                break

            pages_read += 1
            scanned += len(results)
            for entry in results:
                if self._matches(entry, arguments):
                    matches.append(_entry_summary(entry))

            if len(matches) >= limit or not payload.get("next"):
                break

        scan_complete = catalogue_size is not None and scanned >= catalogue_size

        return {
            "status": "success",
            "data": matches[:limit],
            "metadata": {
                "criteria": {
                    "enzyme_name": arguments.get("enzyme_name"),
                    "ec_number": arguments.get("ec_number"),
                    "uniprot_id": arguments.get("uniprot_id"),
                },
                "matches_found": len(matches),
                "returned": len(matches[:limit]),
                "entries_scanned": scanned,
                "pages_read": pages_read,
                "catalogue_size": catalogue_size,
                "scan_complete": scan_complete,
                "note": (
                    "Scanned the whole catalogue."
                    if scan_complete
                    else "Partial scan: the API ignores server-side filters, so "
                    "entries are examined page by page. Raise max_pages to "
                    "cover more of the catalogue."
                ),
                "source": "M-CSA (EBI/Thornton group)",
            },
        }
