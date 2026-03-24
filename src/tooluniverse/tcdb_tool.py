"""
TCDB (Transporter Classification Database) tool for ToolUniverse.

Provides search and lookup for membrane transporter proteins classified
by the IUBMB-approved TC system. 20,000+ proteins in 1,536 families.

TC# format: class.subclass.family.subfamily.protein (e.g., 2.A.1.7.1)

API: https://www.tcdb.org/ (CGI flat-file endpoints, no authentication)
Data is fetched as bulk TSV/CSV and cached in memory for the session.
"""

import csv
import io
import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool

TCDB_BASE = "https://www.tcdb.org"
ACC2TCID_URL = f"{TCDB_BASE}/cgi-bin/projectv/public/acc2tcid.py"
FAMILIES_URL = f"{TCDB_BASE}/cgi-bin/projectv/public/families.py"
SUBSTRATES_URL = f"{TCDB_BASE}/cgi-bin/substrates/getSubstrates.py"
PDB_URL = f"{TCDB_BASE}/cgi-bin/projectv/public/pdb.py"
HUMAN_CSV_URL = f"{TCDB_BASE}/public/human.csv"


@register_tool("TCDBTool")
class TCDBTool(BaseTool):
    """
    Tool for querying TCDB (Transporter Classification Database).

    Supports lookup by UniProt accession, family search by TC# or name,
    and substrate-based search. Data is fetched from bulk flat files and
    cached in memory.
    """

    _cache: dict = {}

    def __init__(self, tool_config: dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "get_transporter")

    def _fetch_and_cache(self, key: str, url: str) -> str:
        """Fetch a bulk data file and cache it. Returns raw text."""
        if key not in TCDBTool._cache:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            TCDBTool._cache[key] = resp.text
        return TCDBTool._cache[key]

    def _get_acc2tcid(self) -> dict[str, list[str]]:
        """Parse acc2tcid into {uniprot_acc: [tc_numbers]}."""
        cache_key = "acc2tcid_parsed"
        if cache_key in TCDBTool._cache:
            return TCDBTool._cache[cache_key]
        raw = self._fetch_and_cache("acc2tcid", ACC2TCID_URL)
        mapping: dict[str, list[str]] = {}
        for line in raw.strip().split("\n"):
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                acc, tc = parts[0].strip(), parts[1].strip()
                mapping.setdefault(acc, []).append(tc)
        TCDBTool._cache[cache_key] = mapping
        return mapping

    def _get_families(self) -> dict[str, str]:
        """Parse families into {family_id: description}."""
        cache_key = "families_parsed"
        if cache_key in TCDBTool._cache:
            return TCDBTool._cache[cache_key]
        raw = self._fetch_and_cache("families", FAMILIES_URL)
        families: dict[str, str] = {}
        for line in raw.strip().split("\n"):
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                families[parts[0].strip()] = parts[1].strip()
        TCDBTool._cache[cache_key] = families
        return families

    def _get_substrates(self) -> list[dict]:
        """Parse substrates into list of {tc_number, substrates: [{chebi_id, name}]}."""
        cache_key = "substrates_parsed"
        if cache_key in TCDBTool._cache:
            return TCDBTool._cache[cache_key]
        raw = self._fetch_and_cache("substrates", SUBSTRATES_URL)
        entries = []
        for line in raw.strip().split("\n"):
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            tc_num = parts[0].strip()
            substrate_parts = parts[1].strip().split("|")
            substrates = []
            for sp in substrate_parts:
                sp = sp.strip()
                if ";" in sp:
                    chebi_id, name = sp.split(";", 1)
                    substrates.append(
                        {"chebi_id": chebi_id.strip(), "name": name.strip()}
                    )
                elif sp:
                    substrates.append({"chebi_id": None, "name": sp})
            entries.append({"tc_number": tc_num, "substrates": substrates})
        TCDBTool._cache[cache_key] = entries
        return entries

    def _get_pdb_mapping(self) -> dict[str, list[str]]:
        """Parse PDB data into {tc_number: [pdb_ids]}."""
        cache_key = "pdb_parsed"
        if cache_key in TCDBTool._cache:
            return TCDBTool._cache[cache_key]
        raw = self._fetch_and_cache("pdb", PDB_URL)
        mapping: dict[str, list[str]] = {}
        for line in raw.strip().split("\n"):
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                pdb_id, tc_num = parts[0].strip(), parts[1].strip()
                mapping.setdefault(tc_num, []).append(pdb_id)
        TCDBTool._cache[cache_key] = mapping
        return mapping

    def _get_human_transporters(self) -> dict[str, dict]:
        """Parse human.csv into {uniprot_acc: {name, symbol, aliases, tc_number}}."""
        cache_key = "human_parsed"
        if cache_key in TCDBTool._cache:
            return TCDBTool._cache[cache_key]
        raw = self._fetch_and_cache("human", HUMAN_CSV_URL)
        humans: dict[str, dict] = {}
        reader = csv.reader(io.StringIO(raw))
        next(reader, None)
        for row in reader:
            if len(row) < 5:
                continue
            acc = row[3].strip() if row[3] else ""
            if acc:
                humans[acc] = {
                    "name": row[0].strip() if row[0] else None,
                    "symbol": row[1].strip() if row[1] else None,
                    "aliases": row[2].strip() if row[2] else None,
                    "tc_number": row[4].strip() if row[4] else None,
                }
        TCDBTool._cache[cache_key] = humans
        return humans

    def _family_for_tc(self, tc_number: str, families: dict[str, str]) -> str | None:
        """Find the family description for a TC number by matching prefixes."""
        parts = tc_number.split(".")
        for length in range(len(parts), 0, -1):
            prefix = ".".join(parts[:length])
            if prefix in families:
                return families[prefix]
        return None

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.operation == "get_transporter":
                return self._get_transporter(arguments)
            elif self.operation == "search_family":
                return self._search_family(arguments)
            elif self.operation == "search_by_substrate":
                return self._search_by_substrate(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"TCDB API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to TCDB"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_transporter(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Look up transporter info by UniProt accession."""
        accession = (
            (
                arguments.get("uniprot_accession")
                or arguments.get("uniprot_id")
                or arguments.get("accession")
                or ""
            )
            .strip()
            .upper()
        )
        if not accession:
            return {
                "status": "error",
                "error": "uniprot_accession is required",
            }

        acc2tcid = self._get_acc2tcid()
        tc_numbers = acc2tcid.get(accession)
        if not tc_numbers:
            return {
                "status": "error",
                "error": f"UniProt accession {accession} not found in TCDB",
            }

        families = self._get_families()
        pdb_mapping = self._get_pdb_mapping()
        human_data = self._get_human_transporters()

        results = []
        for tc in tc_numbers:
            entry = {
                "tc_number": tc,
                "family_description": self._family_for_tc(tc, families),
            }
            pdb_ids = pdb_mapping.get(tc, [])
            if pdb_ids:
                entry["pdb_structures"] = pdb_ids[:20]
            results.append(entry)

        data = {
            "uniprot_accession": accession,
            "tc_entries": results,
        }

        human_info = human_data.get(accession)
        if human_info:
            data["human_info"] = human_info

        return {"status": "success", "data": data}

    def _search_family(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search families by TC family ID prefix or name text."""
        family_id = (arguments.get("family_id") or "").strip()
        family_name = (arguments.get("family_name") or "").strip()
        limit = min(int(arguments.get("limit", 20)), 100)

        if not family_id and not family_name:
            return {
                "status": "error",
                "error": "Either family_id or family_name is required",
            }

        families = self._get_families()
        acc2tcid = self._get_acc2tcid()

        matches = []
        for fid, desc in families.items():
            if family_id and not fid.startswith(family_id):
                continue
            if family_name and family_name.lower() not in desc.lower():
                continue
            member_count = sum(
                1 for tcs in acc2tcid.values() for tc in tcs if tc.startswith(fid)
            )
            matches.append(
                {
                    "family_id": fid,
                    "description": desc,
                    "member_count": member_count,
                }
            )

        matches.sort(key=lambda x: x["family_id"])
        matches = matches[:limit]

        return {
            "status": "success",
            "data": {
                "total_matches": len(matches),
                "families": matches,
                "query": {
                    "family_id": family_id or None,
                    "family_name": family_name or None,
                },
            },
        }

    def _search_by_substrate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search transporters by substrate name."""
        substrate_name = (
            arguments.get("substrate_name") or arguments.get("substrate") or ""
        ).strip()
        limit = min(int(arguments.get("limit", 20)), 100)

        if not substrate_name:
            return {
                "status": "error",
                "error": "substrate_name is required",
            }

        substrates = self._get_substrates()
        families = self._get_families()
        query_lower = substrate_name.lower()

        matches = []
        for entry in substrates:
            matching_substrates = [
                s for s in entry["substrates"] if query_lower in s["name"].lower()
            ]
            if matching_substrates:
                family_desc = self._family_for_tc(entry["tc_number"], families)
                matches.append(
                    {
                        "tc_number": entry["tc_number"],
                        "family_description": family_desc,
                        "matching_substrates": matching_substrates,
                    }
                )

        matches = matches[:limit]
        return {
            "status": "success",
            "data": {
                "total_matches": len(matches),
                "transporters": matches,
                "query": substrate_name,
            },
        }
