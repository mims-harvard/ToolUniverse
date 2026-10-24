"""
SAbDab (Structural Antibody Database) tool for ToolUniverse.

SAbDab is a database containing all antibody structures from the PDB,
annotated with CDR sequences, chain pairings, and other structural features.

Website: https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab
"""

import csv
import io
import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# SAbDab base URL
SABDAB_BASE_URL = "https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab"
# SAbDab 2 serves JSON here. The site itself answers 200 text/html for every
# path, including ones that look like data routes, which is why this tool used
# to report "SAbDab appears to have migrated ... with no public summary-data
# API currently reachable" -- the API is reachable, just not where it looked.
# `GET {SABDAB_API_URL}/` returns {"message": "Welcome to the SAbDab API!"} and
# {SABDAB_API_URL}/openapi.json identifies it as SAbDab 2.1.4.
#
# NEVER append a trailing slash to an API path. That is the whole reason this
# API was written off as unreachable, and it is reproducible:
#   /api/pdb/pdb_00003hfm   -> 200 JSON
#   /api/pdb/pdb_00003hfm/  -> 307 http://backend:8000/pdb/pdb_00003hfm
# The redirect target is an internal hostname that does not resolve off the
# cluster, so the slash form fails DNS rather than returning data -- which is
# exactly what tests/unit/test_sabdab_spa_migration_detection.py recorded as
# "307-redirects to an internal-only hostname, not publicly resolvable".
SABDAB_API_URL = f"{SABDAB_BASE_URL}/api"

# `sabdab_chain_type` vocabulary, tallied over 286 chains in 40 structures:
# H heavy (98), N non-antibody (92), K kappa light (50), L lambda light (42),
# M single-chain construct such as scFv16 (4). Light chains are K *or* L, so
# testing for "L" alone drops every kappa chain -- and classifying antigen as
# "not H or L" then files those kappa chains, and scFvs, as antigen. 3hfm is
# the case that showed it: its light chain is K on auth_asym_id "L".
SABDAB_HEAVY_TYPES = frozenset({"H"})
SABDAB_LIGHT_TYPES = frozenset({"K", "L"})
SABDAB_SINGLE_CHAIN_TYPES = frozenset({"M"})
SABDAB_ANTIGEN_TYPES = frozenset({"N"})

# /api/antibody-instances filters, as its openapi.json (SAbDab 2.1.5) declares
# them. `binds_to_antigen` is a case-insensitive substring of the antigen's
# name as deposited in the PDB, and the API rejects it above 25 characters
# (HTTP 422), so a full UniProt name such as "Receptor tyrosine-protein kinase
# erbB-2" cannot be sent; "erbB-2" matches 31 instances. A gene symbol or
# shorthand usually matches nothing: "HER2" and "PD-1" both return 0, while
# "cell death protein 1" returns 51.
SABDAB_ANTIGEN_QUERY_MAX = 25
SABDAB_SEARCH_LIMIT_MAX = 100
SABDAB_EXPERIMENTAL_METHODS = (
    "X-ray diffraction",
    "electron microscopy",
    "electron crystallography",
    "solution NMR",
    "solid-state NMR",
    "neutron diffraction",
    "fiber diffraction",
    "powder diffraction",
    "solution scattering",
    "fluorescence transfer",
    "infrared spectroscopy",
    "EPR",
    "theoretical model",
)
SABDAB_ANTIGEN_KINDS = (
    "PROTEIN",
    "PEPTIDE",
    "DNA",
    "RNA",
    "NUCLEOTIDE",
    "PEPTIDE_NUCLEIC_ACID",
    "SUGAR",
    "HAPTEN",
    "ION",
    "CHEMICAL_ELEMENT",
    "WATER",
    "UNKNOWN",
    "OTHER",
)
SABDAB_ANTIBODY_KINDS = ("FV", "FAB", "FAB+FC", "FV*", "SD-H", "SD-L", "VNAR")


@register_tool("SAbDabTool")
class SAbDabTool(BaseTool):
    """
    Tool for querying SAbDab structural antibody database.

    SAbDab provides:
    - Antibody structures from PDB
    - CDR (complementarity-determining region) annotations
    - Heavy/light chain pairing information
    - Antigen binding information

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 60)
        self.parameter = tool_config.get("parameter", {})

    @staticmethod
    def _extended_pdb_id(pdb_id: str) -> str:
        """SAbDab 2 keys entries by the extended PDB ID, not the 4-char code.

        `/api/pdb/3hfm` answers 404 "No PDB entry found with pdb_id='3hfm'" --
        a real route rejecting a real structure, which is what made the old
        code look like the API was gone. `/api/pdb/pdb_00003hfm` returns it.
        An id that is already extended is passed through unchanged.
        """
        code = (pdb_id or "").strip().lower()
        if code.startswith("pdb_"):
            return code
        return f"pdb_0000{code}"

    def _api_get(self, path: str, params=None):
        """GET one API path. Returns (payload, error_dict); exactly one is None."""
        url = f"{SABDAB_API_URL}{path}"
        try:
            response = requests.get(
                url,
                params=params or {},
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/SAbDab",
                },
            )
        except requests.exceptions.RequestException as exc:
            return None, {
                "status": "error",
                "error": f"SAbDab request failed: {exc}",
                "url": url,
            }
        if response.status_code == 404:
            return None, {"status": "not_found", "url": url}
        if response.status_code != 200:
            return None, {
                "status": "error",
                "error": f"SAbDab API returned HTTP {response.status_code}",
                "url": url,
            }
        try:
            return response.json(), None
        except ValueError:
            # The surrounding site answers 200 text/html for unknown paths, so
            # a non-JSON 200 means the path is not an API route.
            return None, {
                "status": "error",
                "error": (
                    "SAbDab returned a 200 that is not JSON, so this path is "
                    "not an API route"
                ),
                "url": url,
            }

    def _chain_rows(self, entry: dict) -> list:
        """Chain inventory: type, organism and sequence, per polymer instance."""
        rows = []
        for chain in entry.get("polymer_instances") or []:
            rows.append(
                {
                    "chain": chain.get("sabdab_auth_asym_id")
                    or chain.get("pdb_auth_asym_id"),
                    "chain_type": chain.get("sabdab_chain_type"),
                    "name": chain.get("name"),
                    "entity_type": chain.get("entity_type"),
                    "organism_scientific": chain.get("organism_scientific"),
                    "organism_common": chain.get("organism_common"),
                    "sequence": chain.get("sequence"),
                    "resolved_sequence": chain.get("resolved_sequence"),
                }
            )
        return rows

    @staticmethod
    def _antibody_rows(entry: dict) -> list:
        """One row per paired antibody found in the structure."""
        rows = []
        for instance in entry.get("antibody_instances") or []:
            rows.append(
                {
                    "id": instance.get("id"),
                    "antibody_id": instance.get("antibody_id"),
                    "type": instance.get("type"),
                    "pairing_distance": instance.get("pairing_distance"),
                    "any_cdr_coords_resolved": instance.get("any_cdr_coords_resolved"),
                    "all_cdr_coords_resolved": instance.get("all_cdr_coords_resolved"),
                }
            )
        return rows

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SAbDab query based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        allowed_arguments = {
            "search_structures": {
                "operation",
                "query",
                "antigen",
                "species",
                "method",
                "resolution_max",
                "antigen_type",
                "antibody_type",
                "pdb_id",
                "limit",
                "offset",
            },
            "get_structure": {"operation", "pdb_id", "pdb_code"},
            "get_structure_summary": {"operation", "pdb_id", "pdb_code", "pdb"},
            # pdb/pdb_id were accepted here historically; keep them harmless.
            "get_summary": {"operation", "pdb", "pdb_id"},
        }
        if operation in allowed_arguments:
            unknown = sorted(set(arguments) - allowed_arguments[operation])
            if unknown:
                return {
                    "status": "error",
                    "error": f"Unknown parameter(s) for {operation}: {', '.join(unknown)}",
                }

        if operation == "search_structures":
            return self._search_structures(arguments)
        elif operation == "get_structure":
            return self._get_structure(arguments)
        elif operation == "get_structure_summary":
            return self._get_structure_summary(arguments)
        elif operation == "get_summary":
            return self._get_summary(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_structures, get_structure, get_structure_summary, get_summary",
            }

    @staticmethod
    def _choice(value, choices, name):
        """Match `value` to one of `choices` ignoring case; (choice, error)."""
        if value in (None, ""):
            return None, None
        by_key = {choice.lower(): choice for choice in choices}
        choice = by_key.get(str(value).strip().lower())
        if choice is None:
            return None, f"{name} must be one of: {', '.join(choices)}"
        return choice, None

    @staticmethod
    def _segment_row(segment: dict) -> dict:
        """The CDRs and germline of one chain, without the residue numbering."""
        return {
            "chain": segment.get("sabdab_auth_asym_id"),
            "chain_type": segment.get("type"),
            "cdr1": segment.get("cdr1"),
            "cdr2": segment.get("cdr2"),
            "cdr3": segment.get("cdr3"),
            "v_gene": segment.get("v_gene"),
            "j_gene": segment.get("j_gene"),
        }

    def _instance_row(self, instance: dict) -> dict:
        """One antibody instance, compact: a full record carries the residue
        numbering of both chains, so a 500-row page is 3.4 MB."""
        entry = instance.get("pdb_entry") or {}
        heavy = instance.get("heavy_like_segment")
        light = instance.get("light_like_segment")
        extended = entry.get("id") or ""
        return {
            "instance_id": instance.get("id"),
            "pdb_id": extended[len("pdb_0000") :]
            if extended.startswith("pdb_0000")
            else extended,
            "structure_name": entry.get("name"),
            "antibody_id": instance.get("antibody_id"),
            "antibody_type": instance.get("type"),
            "resolution": entry.get("resolution"),
            "structure_method": entry.get("structure_method"),
            "release_date": entry.get("release_date"),
            "heavy": self._segment_row(heavy) if isinstance(heavy, dict) else None,
            "light": self._segment_row(light) if isinstance(light, dict) else None,
            "antigen_instance_ids": [
                binding.get("antigen_instance_id")
                for binding in instance.get("antigen_bindings") or []
            ],
        }

    def _search_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search antibody instances through /api/antibody-instances.

        #701 found no search route because it looked on /api/pdb, where every
        filter is accepted and ignored. /api/antibody-instances does filter:
        on 2026-10-23 no filter gave `total` 22671, `binds_to_antigen=lysozyme`
        123, "spike glycoprotein" 2008 and a made-up name 0.
        """
        query = (arguments.get("query") or arguments.get("antigen") or "").strip()
        if len(query) > SABDAB_ANTIGEN_QUERY_MAX:
            return {
                "status": "error",
                "error": (
                    f"query is {len(query)} characters; SAbDab matches antigen "
                    f"names on at most {SABDAB_ANTIGEN_QUERY_MAX}. Send a "
                    "distinctive part of the name instead, e.g. 'erbB-2' for "
                    "Receptor tyrosine-protein kinase erbB-2, or 'cell death "
                    "protein 1' for PD-1."
                ),
                "parameter": "query",
            }

        limit = arguments.get("limit", 20)
        offset = arguments.get("offset", 0)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= SABDAB_SEARCH_LIMIT_MAX
        ):
            return {
                "status": "error",
                "error": f"limit must be an integer from 1 to {SABDAB_SEARCH_LIMIT_MAX}",
                "parameter": "limit",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }

        resolution = arguments.get("resolution_max")
        if resolution is not None and (
            isinstance(resolution, bool)
            or not isinstance(resolution, (int, float))
            or resolution <= 0
        ):
            return {
                "status": "error",
                "error": "resolution_max must be a positive number of angstroms",
                "parameter": "resolution_max",
            }

        filters = {}
        for name, key, choices in (
            ("method", "experimental_method", SABDAB_EXPERIMENTAL_METHODS),
            ("antigen_type", "antigen_type", SABDAB_ANTIGEN_KINDS),
            ("antibody_type", "antibody_type", SABDAB_ANTIBODY_KINDS),
        ):
            choice, error = self._choice(arguments.get(name), choices, name)
            if error:
                return {"status": "error", "error": error, "parameter": name}
            if choice:
                filters[key] = choice
        if query:
            filters["binds_to_antigen"] = query
        species = (arguments.get("species") or "").strip()
        if species:
            filters["organism_scientific"] = species
        if resolution is not None:
            filters["resolution"] = resolution
        pdb_id = (arguments.get("pdb_id") or "").strip()
        if pdb_id:
            filters["pdb_entry"] = self._extended_pdb_id(pdb_id)

        payload, failure = self._api_get(
            "/antibody-instances", params={**filters, "limit": limit, "offset": offset}
        )
        if failure is not None:
            return failure
        results = payload.get("results") if isinstance(payload, dict) else None
        total = payload.get("total") if isinstance(payload, dict) else None
        if (
            not isinstance(results, list)
            or isinstance(total, bool)
            or not isinstance(total, int)
        ):
            return {
                "status": "error",
                "error": "SAbDab returned a search response without results and total",
                "url": f"{SABDAB_API_URL}/antibody-instances",
            }

        rows = [self._instance_row(item) for item in results if isinstance(item, dict)]
        next_offset = offset + len(rows)
        has_more = next_offset < total
        data = {
            "query": query,
            "filters_applied": filters,
            "structures": rows,
            "count": len(rows),
            "total_matches": total,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "next_offset": next_offset if has_more else None,
            "result_set_complete": offset == 0 and not has_more,
        }
        if total == 0 and query:
            data["note"] = (
                f"No antibody binds an antigen whose name contains {query!r}. "
                "SAbDab matches the antigen's name as deposited in the PDB, so "
                "gene symbols and shorthand often miss: 'HER2' finds nothing "
                "where 'erbB-2' finds 31. Try a distinctive part of the full "
                "protein name."
            )
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "SAbDab 2 API",
                "url": f"{SABDAB_API_URL}/antibody-instances",
                "details": "SAbDab_get_structure_summary takes a pdb_id from these rows",
            },
        }

    def _get_structure(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Structure-level antibody record: chains, pairings, organisms.

        The description has always promised "CDR annotations, chain
        information, and antigen binding data", but the implementation fetched
        {SABDAB_BASE_URL}/pdb/{id}/ and expected a coordinate file, so it
        reported "got non-PDB content, likely an HTML page". SAbDab 2 has no
        coordinate route at all -- /structure, /file, /download and
        /{id}.pdb all 404 under /api -- and coordinates were never what this
        tool said it returned. RCSB serves those, and ToolUniverse covers it
        through the rcsb_pdb tools.
        """
        pdb_id = arguments.get("pdb_id") or arguments.get("pdb_code") or ""
        if not pdb_id:
            return {"status": "error", "error": "Missing required parameter: pdb_id"}

        extended = self._extended_pdb_id(pdb_id)
        entry, failure = self._api_get(f"/pdb/{extended}")
        if failure is not None:
            if failure.get("status") == "not_found":
                return {
                    "status": "error",
                    "error": (
                        f"SAbDab has no entry for '{pdb_id}'. It holds antibody "
                        "and nanobody structures only, so a PDB entry without "
                        "one is absent rather than missing."
                    ),
                    "url": failure["url"],
                }
            return failure

        return {
            "status": "success",
            "data": {
                "pdb_id": entry.get("id"),
                "query_pdb_id": pdb_id,
                "name": entry.get("name"),
                "head": entry.get("head"),
                "resolution": entry.get("resolution"),
                "structure_method": entry.get("structure_method"),
                "chains": self._chain_rows(entry),
                "antibodies": self._antibody_rows(entry),
                "coordinates": (
                    "SAbDab serves no coordinate files; use the rcsb_pdb tools "
                    f"or https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
                ),
            },
            "metadata": {
                "source": "SAbDab 2 API",
                "url": f"{SABDAB_API_URL}/pdb/{extended}",
            },
        }

    def _get_structure_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """The curated per-structure fields, the way the summary TSV read.

        Same API entry as _get_structure, projected differently: this is the
        one-row view (method, resolution, dates, antibody type, chain species),
        while _get_structure returns the full chain and pairing inventory.
        """
        pdb_id = (
            arguments.get("pdb_id")
            or arguments.get("pdb_code")
            or arguments.get("pdb")
            or ""
        )
        if not pdb_id:
            return {"status": "error", "error": "Missing required parameter: pdb_id"}

        extended = self._extended_pdb_id(pdb_id)
        entry, failure = self._api_get(f"/pdb/{extended}")
        if failure is not None:
            if failure.get("status") == "not_found":
                return {
                    "status": "error",
                    "error": (
                        f"SAbDab has no entry for '{pdb_id}'. It holds antibody "
                        "and nanobody structures only."
                    ),
                    "url": failure["url"],
                }
            return failure

        chains = self._chain_rows(entry)
        heavy = [c for c in chains if c.get("chain_type") in SABDAB_HEAVY_TYPES]
        light = [c for c in chains if c.get("chain_type") in SABDAB_LIGHT_TYPES]
        single = [c for c in chains if c.get("chain_type") in SABDAB_SINGLE_CHAIN_TYPES]
        # Only N is the antigen side. Treating "not heavy or light" as antigen
        # files kappa chains and scFv constructs as antigen, and a chain type
        # SAbDab adds later would silently join them.
        antigen = [c for c in chains if c.get("chain_type") in SABDAB_ANTIGEN_TYPES]
        unclassified = [
            c
            for c in chains
            if c.get("chain_type")
            not in SABDAB_HEAVY_TYPES
            | SABDAB_LIGHT_TYPES
            | SABDAB_SINGLE_CHAIN_TYPES
            | SABDAB_ANTIGEN_TYPES
        ]
        antibodies = self._antibody_rows(entry)

        return {
            "status": "success",
            "data": {
                "pdb_id": entry.get("id"),
                "query_pdb_id": pdb_id,
                "name": entry.get("name"),
                "resolution": entry.get("resolution"),
                "structure_method": entry.get("structure_method"),
                "r_work": entry.get("r_work"),
                "r_free": entry.get("r_free"),
                "deposition_date": entry.get("deposition_date"),
                "release_date": entry.get("release_date"),
                "journal_references": entry.get("journal_references"),
                "antibody_type": sorted(
                    {a["type"] for a in antibodies if a.get("type")}
                ),
                "antibody_count": len(antibodies),
                "heavy_chains": [c["chain"] for c in heavy],
                "light_chains": [c["chain"] for c in light],
                "single_chain_constructs": [c["chain"] for c in single],
                "heavy_chain_species": sorted(
                    {
                        c["organism_scientific"]
                        for c in heavy
                        if c.get("organism_scientific")
                    }
                ),
                "light_chain_species": sorted(
                    {
                        c["organism_scientific"]
                        for c in light
                        if c.get("organism_scientific")
                    }
                ),
                "antigen_chains": [
                    {
                        "chain": c["chain"],
                        "name": c["name"],
                        "organism_scientific": c["organism_scientific"],
                    }
                    for c in antigen
                ],
                # Reported rather than folded into antigen, so a chain type
                # added upstream is visible instead of mislabelled.
                "unclassified_chains": [
                    {"chain": c["chain"], "chain_type": c["chain_type"]}
                    for c in unclassified
                ],
                "all_cdr_coords_resolved": all(
                    a.get("all_cdr_coords_resolved") for a in antibodies
                )
                if antibodies
                else None,
            },
            "metadata": {
                "source": "SAbDab 2 API",
                "url": f"{SABDAB_API_URL}/pdb/{extended}",
                "note": (
                    "Derived from the SAbDab 2 JSON entry. The summary TSV this "
                    "used to parse is no longer served, and four of its columns "
                    "have no counterpart anywhere in the JSON entry: IMGT "
                    "heavy/light V-gene subclass, affinity, the engineered "
                    "flag, and the PMID. They are absent rather than guessed. "
                    "`journal_references` is the only citation the API carries, "
                    "as free text. Whether an antibody is a single-chain "
                    "construct is readable from `antibody_type` and "
                    "`single_chain_constructs` instead of the old scfv flag."
                ),
            },
        }

    def _get_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Database-level counts, read from the API rather than hardcoded.

        This used to return a fixed blurb -- a description string and a list of
        features -- with status "success" and no request made at all. It could
        not go out of date because it was never live, and it could not tell a
        caller anything they did not already know.
        """
        structures, failure = self._api_get("/pdb", params={"limit": 1})
        if failure is not None:
            return failure
        antibodies, failure = self._api_get("/antibodies", params={"limit": 1})
        if failure is not None:
            return failure

        return {
            "status": "success",
            "data": {
                "description": "SAbDab 2 - the Structural Antibody Database",
                "structures": structures.get("total"),
                "unique_antibodies": antibodies.get("total"),
                "web_url": SABDAB_BASE_URL,
                "api_url": SABDAB_API_URL,
                "note": (
                    "`structures` counts PDB entries SAbDab holds; "
                    "`unique_antibodies` counts distinct heavy/light pairings "
                    "across them, so it is the smaller number."
                ),
            },
            "metadata": {
                "source": "SAbDab 2 API",
                "url": f"{SABDAB_API_URL}/pdb",
            },
        }
