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


def _reference_chain(chains: List[Any]) -> Dict[str, Any]:
    """The chain M-CSA marks as the reference, not whichever came first."""
    dicts = [c for c in chains if isinstance(c, dict)]
    for chain in dicts:
        if chain.get("is_reference"):
            return chain
    return dicts[0] if dicts else {}


def _residue_summary(residue: Dict[str, Any]) -> Dict[str, Any]:
    """Condense one catalytic residue record to its identity and roles.

    Two things here are easy to get wrong and were.

    `resid` is M-CSA's own sequential index and `auth_resid` is the PDB
    author numbering -- the one papers and mutation names use. Entry 2's
    catalytic serine is `resid: 45, auth_resid: 70`, and the enzyme's
    mechanism text in the same response calls it "Ser70". Reporting 45 as
    the residue number, for a tool whose purpose is interpreting active-site
    mutations, is the wrong number under the right name.

    A role is `{function, function_type, emo}`, and `function_type` is
    "reactant", "interaction" or "spectator": whether the residue does the
    chemistry, holds the substrate, or neither. Collapsing the role objects
    to a sorted set of `function` strings dropped that distinction along with
    the EMO ontology ids -- 3 of entry 2's 7 residues are spectators, and
    nothing said so.
    """
    chains = residue.get("residue_chains") or []
    first = _reference_chain(chains)
    sequences = residue.get("residue_sequences") or []
    seq = sequences[0] if sequences and isinstance(sequences[0], dict) else {}
    role_details = []
    for role in residue.get("roles") or []:
        if not isinstance(role, dict) or not role.get("function"):
            continue
        role_details.append(
            {
                "function": role.get("function"),
                "function_type": role.get("function_type") or None,
                "emo_id": role.get("emo") or None,
                "group_function": role.get("group_function") or None,
            }
        )
    role_types = sorted({r["function_type"] for r in role_details if r["function_type"]})
    return {
        "code": first.get("code") or seq.get("code"),
        "pdb_id": first.get("pdb_id"),
        "chain": first.get("chain_name"),
        "residue_number": first.get("resid"),
        # The PDB/literature numbering of the same residue.
        "auth_residue_number": first.get("auth_resid"),
        "uniprot_id": seq.get("uniprot_id"),
        "uniprot_position": seq.get("resid"),
        "domain_name": first.get("domain_name") or None,
        "domain_cath_id": first.get("domain_cath_id") or None,
        "assembly": first.get("assembly"),
        "is_reference_chain": bool(first.get("is_reference")),
        "chain_count": len([c for c in chains if isinstance(c, dict)]),
        "roles": sorted({r["function"] for r in role_details}),
        "role_details": role_details,
        "role_count": len(role_details),
        "role_types": role_types,
        "roles_summary": residue.get("roles_summary") or None,
        # "main-N" where catalysis is by the backbone nitrogen, not the side
        # chain -- which changes what a substitution at the position means.
        "function_location": residue.get("function_location_abv") or None,
        "annotation": (residue.get("main_annotation") or "").strip() or None,
        "is_ptm": bool(residue.get("ptm")),
    }


MECHANISM_TEXT_CHARACTERS = 1500


def _compounds(reaction: Dict[str, Any]) -> List[Dict[str, Any]]:
    """What the reaction consumes and produces, which the tool's own
    description promises as "the reaction catalysed" and never returned."""
    out = []
    for compound in reaction.get("compounds") or []:
        if not isinstance(compound, dict):
            continue
        out.append(
            {
                "name": compound.get("name"),
                "chebi_id": compound.get("chebi_id"),
                "role": compound.get("type"),
                "count": compound.get("count"),
            }
        )
    return out


def _mechanisms(reaction: Dict[str, Any]) -> List[Dict[str, Any]]:
    """M-CSA's curated mechanisms, capped per entry.

    `mechanism_text` is the prose a curator wrote about how the enzyme works
    -- entry 2's names Ser70 and the acylation/deacylation steps -- and it
    reached no caller. `steps` is the per-step arrow-pushing and is left to
    the M-CSA page, which `url` points at.
    """
    out = []
    for mechanism in reaction.get("mechanisms") or []:
        if not isinstance(mechanism, dict):
            continue
        text = (mechanism.get("mechanism_text") or "").strip()
        truncated = len(text) > MECHANISM_TEXT_CHARACTERS
        out.append(
            {
                "mechanism_id": mechanism.get("mechanism_id"),
                "is_detailed": mechanism.get("is_detailed"),
                "rating": mechanism.get("rating"),
                "text": (
                    text[:MECHANISM_TEXT_CHARACTERS].rstrip() + "..."
                    if truncated
                    else text or None
                ),
                "text_truncated": truncated,
                "step_count": len(mechanism.get("steps") or []),
                # Each reference is a record, with the evidence types that
                # tie it to this mechanism: "computational experiment" and
                # "traceable author statement" are different claims.
                "references": [
                    {
                        "pubmed_id": r.get("pubmed_id"),
                        "doi": r.get("doi"),
                        "title": r.get("title"),
                        "evidence_types": [
                            e for e in (r.get("evidence_types") or []) if e
                        ],
                    }
                    for r in (mechanism.get("references") or [])
                    if isinstance(r, dict)
                ],
            }
        )
    return out


def _entry_summary(
    entry: Dict[str, Any],
    with_residues: bool = True,
    with_mechanisms: bool = False,
) -> Dict[str, Any]:
    """Condense one M-CSA entry.

    The mechanism prose belongs to the single-entry lookup: a search of 25
    rows would otherwise carry 25 copies of a 1.5 kB curator narrative, so a
    search row gets the count and the compounds and points at `url`.
    """
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
        # `reaction_name` was read from a key M-CSA does not send -- the
        # reaction object holds ec, compounds, mechanisms and is_polymeric
        # and has never carried a name -- so it was null on every entry.
        summary["reaction_ec"] = reaction.get("ec")
        summary["reaction_is_polymeric"] = reaction.get("is_polymeric")
        summary["reaction_compounds"] = _compounds(reaction)
        mechanisms = _mechanisms(reaction)
        summary["mechanism_count"] = len(mechanisms)
        if with_mechanisms:
            summary["mechanisms"] = mechanisms
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
            "data": _entry_summary(entry, with_mechanisms=True),
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
