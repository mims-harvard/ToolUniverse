"""
SAbDab (Structural Antibody Database) tool for ToolUniverse.

SAbDab is a database containing all antibody structures from the PDB,
annotated with CDR sequences, chain pairings, and other structural features.

Website: https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab
"""

import csv
import io
import re
import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# SAbDab base URL
SABDAB_BASE_URL = "https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab"
SABDAB2_BASE_URL = "https://sabdab.opig.stats.ox.ac.uk"


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
                "limit",
                "offset",
                "pdb_id",
                "species",
                "resolution_max",
                "method",
                "antigen_type",
                "antibody_type",
                "construct_type",
            },
            "get_structure": {"operation", "pdb_id", "pdb_code"},
            "get_structure_summary": {"operation", "pdb_id", "pdb_code", "pdb"},
            # Keep the historical redirect hint for callers that confuse the
            # database summary with per-structure retrieval.
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

    def _search_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search the current SAbDab2 antibody-instance JSON API."""
        query = arguments.get("query") or arguments.get("antigen", "")
        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)

        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            return {"status": "error", "error": "limit must be an integer from 1 to 100"}
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {"status": "error", "error": "offset must be a non-negative integer"}

        params = {"limit": limit, "offset": offset}
        filters = {
            "binds_to_antigen": query,
            "organism_scientific": arguments.get("species"),
            "experimental_method": arguments.get("method"),
            "resolution": arguments.get("resolution_max"),
            "antigen_type": arguments.get("antigen_type"),
            "antibody_type": arguments.get("antibody_type"),
            "construct_type": arguments.get("construct_type"),
        }
        pdb_id = arguments.get("pdb_id")
        if pdb_id:
            try:
                filters["pdb_entry"] = self._normalize_pdb_id(pdb_id)
            except ValueError as exc:
                return {"status": "error", "error": str(exc)}
        for name, value in filters.items():
            if value not in (None, ""):
                params[name] = value

        resolution = params.get("resolution")
        if resolution is not None and (
            isinstance(resolution, bool)
            or not isinstance(resolution, (int, float))
            or resolution <= 0
        ):
            return {"status": "error", "error": "resolution_max must be a positive number"}

        try:
            # The legacy /search/?q=... route is only the React SPA shell and
            # silently ignores both q and limit.  This is the endpoint used by
            # the current SAbDab2 web application.
            response = requests.get(
                f"{SABDAB2_BASE_URL}/api/antibody-instances",
                params=params,
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/SAbDab",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()

            if "json" in response.headers.get("Content-Type", ""):
                data = response.json()
                if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                    return {"status": "error", "error": "SAbDab returned malformed search JSON"}
                structures = data["results"]
                total = data.get("total")
                if (
                    not isinstance(total, int)
                    or data.get("limit") != limit
                    or data.get("offset") != offset
                ):
                    return {
                        "status": "error",
                        "error": "SAbDab search metadata conflicts with the requested pagination",
                    }
                if any(not isinstance(item, dict) or not item.get("id") for item in structures):
                    return {"status": "error", "error": "SAbDab returned a malformed structure record"}
                next_offset = offset + len(structures)
                has_more = next_offset < total
                return {
                    "status": "success",
                    "data": {
                        "structures": structures,
                        "count": len(structures),
                        "returned_count": len(structures),
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                        "has_more": has_more,
                        "next_offset": next_offset if has_more else None,
                        "result_set_complete": not has_more and offset == 0,
                        "query": query,
                        "filters_applied": {
                            key: value
                            for key, value in params.items()
                            if key not in ("limit", "offset")
                        },
                    },
                    "metadata": {
                        "source": "SAbDab2",
                        "api_url": response.url,
                        "pagination_warning": (
                            "Additional records exist; call again with next_offset."
                            if has_more
                            else None
                        ),
                    },
                }

            return {
                "status": "error",
                "error": (
                    "SAbDab search returned non-JSON content; refusing to report "
                    "the SPA page as search results"
                ),
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_structure(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get antibody structure details by PDB ID.

        Args:
            arguments: Dict containing:
                - pdb_id: 4-character PDB ID
        """
        pdb_id = arguments.get("pdb_id") or arguments.get("pdb_code") or ""
        if not pdb_id:
            return {"status": "error", "error": "Missing required parameter: pdb_id"}

        try:
            internal_pdb_id = self._normalize_pdb_id(pdb_id)
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        display_pdb_id = self._display_pdb_id(internal_pdb_id)

        try:
            pdb_url = f"{SABDAB2_BASE_URL}/api/pdb/{internal_pdb_id}"
            response = requests.get(
                pdb_url,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/SAbDab"},
            )

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Structure not found: {pdb_id}. Note: SAbDab may not have all PDB structures.",
                }

            response.raise_for_status()

            if "json" in response.headers.get("Content-Type", ""):
                source_record = response.json()
                if (
                    not isinstance(source_record, dict)
                    or source_record.get("id") != internal_pdb_id
                ):
                    return {
                        "status": "error",
                        "error": "SAbDab structure identity conflicts with the requested PDB ID",
                    }
                related = self._get_structure_relationships(internal_pdb_id)
                if related.get("status") == "error":
                    return related
                return {
                    "status": "success",
                    "data": {
                        "pdb_id": display_pdb_id,
                        "sabdab2_pdb_id": internal_pdb_id,
                        "name": source_record.get("name"),
                        "resolution": source_record.get("resolution"),
                        "method": source_record.get("structure_method"),
                        "r_work": source_record.get("r_work"),
                        "r_free": source_record.get("r_free"),
                        "status": source_record.get("status"),
                        "polymer_instances": source_record.get("polymer_instances", []),
                        "non_polymer_instances": source_record.get(
                            "non_polymer_instances", []
                        ),
                        "antibody_instances": related["antibody_instances"],
                        "antigen_instances": related["antigen_instances"],
                        "source_record": source_record,
                        "source_record_complete": True,
                    },
                    "metadata": {
                        "source": "SAbDab2",
                        "api_url": response.url,
                        "note": (
                            "Full current SAbDab2 JSON record with antibody "
                            "and antigen relationships"
                        ),
                    },
                }

            # Backward-compatible parsing for deployments that still return
            # a legacy Chothia-numbered PDB file.
            # Fix-R17D-2: SAbDab migrated to a new frontend ("SAbDab2", a
            # React SPA) and its old download URL now redirects to an
            # internal-only backend hostname (confirmed live: the new
            # domain's /api/pdb/{id}/ route 307-redirects to
            # "http://sabdab-backend:8000/...", not publicly resolvable) --
            # so this request lands on the SPA shell instead of real PDB
            # coordinate data, and used to be reported as a successful
            # download of that HTML. Detect and report it honestly instead.
            pdb_content = response.text
            # SAbDab migrated to a React SPA that serves the same generic
            # HTML app shell for every route including this download
            # endpoint (confirmed live: /pdb/<id>/ 200s with
            # "<!doctype html>..." instead of PDB coordinate records) --
            # detect that before claiming success, rather than reporting
            # the HTML page's byte count/preview as if it were structure
            # data. A positive check against known PDB record prefixes
            # (rather than an HTML-only negative check) also catches any
            # other non-PDB content the endpoint might return.
            first_line = pdb_content.lstrip().splitlines()[0] if pdb_content else ""
            looks_like_pdb = first_line[:6].strip() in (
                "HEADER",
                "ATOM",
                "HETATM",
                "TITLE",
                "REMARK",
                "COMPND",
            )
            if not looks_like_pdb:
                return {
                    "status": "error",
                    "error": (
                        f"SAbDab did not return PDB structure data for {pdb_id} "
                        "(got non-PDB content, likely an HTML page from "
                        "SAbDab's current site). The structure/site layout "
                        "may have changed; try downloading directly from "
                        f"{pdb_url}."
                    ),
                }

            metadata = {"pdb_id": display_pdb_id}

            # Parse REMARK 5 lines which contain SAbDab annotations
            remarks = []
            for line in pdb_content.split("\n"):
                if line.startswith("REMARK   5 PAIRED_"):
                    for part in line.split():
                        if "=" in part:
                            key, val = part.split("=")
                            metadata[key.lower()] = val
                elif line.startswith("REMARK   5 "):
                    remark = line[15:].strip()
                    if remark and remark not in str(remarks):
                        remarks.append(remark)
            if remarks:
                metadata["remarks"] = remarks

            return {
                "status": "success",
                "data": {
                    "pdb_id": display_pdb_id,
                    "download_url": pdb_url,
                    "structure_url": f"{SABDAB_BASE_URL}/structureviewer/?pdb={pdb_id}",
                    "search_url": f"{SABDAB_BASE_URL}/search/?pdb={pdb_id}",
                    "metadata": metadata,
                    "pdb_size_bytes": len(pdb_content),
                    "pdb_preview": pdb_content[:500]
                    if len(pdb_content) > 500
                    else pdb_content,
                },
                "metadata": {
                    "source": "SAbDab",
                    "note": "PDB file with Chothia numbering available at download_url",
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    @staticmethod
    def _looks_like_html(text: str) -> bool:
        """True when the response body is an HTML page (the SAbDab2 SPA shell)
        rather than the expected PDB/TSV data."""
        return text.lstrip()[:20].lower().startswith(("<!doctype html", "<html"))

    @staticmethod
    def _normalize_pdb_id(pdb_id: Any) -> str:
        """Convert a public four-character PDB code to SAbDab2's identifier."""
        if not isinstance(pdb_id, str) or not re.fullmatch(
            r"[A-Za-z0-9]{4}", pdb_id.strip()
        ):
            raise ValueError("pdb_id must be exactly four letters or digits")
        return f"pdb_{pdb_id.strip().lower().rjust(8, '0')}"

    @staticmethod
    def _display_pdb_id(internal_pdb_id: str) -> str:
        return internal_pdb_id.removeprefix("pdb_").lstrip("0") or "0"

    def _get_structure_relationships(self, internal_pdb_id: str) -> Dict[str, Any]:
        """Fetch the antibody and antigen records displayed by SAbDab2's UI."""
        antibody_instances = []
        expected_total = None
        offset = 0
        seen_ids = set()
        while expected_total is None or offset < expected_total:
            response = requests.get(
                f"{SABDAB2_BASE_URL}/api/antibody-instances",
                params={"pdb_entry": internal_pdb_id, "limit": 100, "offset": offset},
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/SAbDab",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            if "json" not in response.headers.get("Content-Type", ""):
                return {
                    "status": "error",
                    "error": "SAbDab returned non-JSON relationship data",
                }
            payload = response.json()
            page = payload.get("results") if isinstance(payload, dict) else None
            total = payload.get("total") if isinstance(payload, dict) else None
            if (
                not isinstance(page, list)
                or not isinstance(total, int)
                or payload.get("limit") != 100
                or payload.get("offset") != offset
                or (expected_total is not None and total != expected_total)
            ):
                return {
                    "status": "error",
                    "error": "SAbDab antibody relationship pagination is malformed or inconsistent",
                }
            expected_total = total
            if not page and offset < total:
                return {
                    "status": "error",
                    "error": "SAbDab antibody relationship pagination stopped before total",
                }
            for antibody in page:
                antibody_id = antibody.get("id") if isinstance(antibody, dict) else None
                if not antibody_id or antibody_id in seen_ids:
                    return {
                        "status": "error",
                        "error": "SAbDab returned malformed or duplicate antibody relationships",
                    }
                seen_ids.add(antibody_id)
                antibody_instances.append(antibody)
            offset += len(page)

        if len(antibody_instances) != expected_total:
            return {
                "status": "error",
                "error": "SAbDab antibody relationship results are unexpectedly truncated",
            }

        antigen_ids = sorted(
            {
                binding.get("antigen_instance_id")
                for antibody in antibody_instances
                for binding in antibody.get("antigen_bindings", [])
                if binding.get("antigen_instance_id")
            }
        )
        antigen_instances = []
        for antigen_id in antigen_ids:
            antigen_response = requests.get(
                f"{SABDAB2_BASE_URL}/api/antigen-instance/{antigen_id}",
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/SAbDab",
                    "Accept": "application/json",
                },
            )
            antigen_response.raise_for_status()
            if "json" not in antigen_response.headers.get("Content-Type", ""):
                return {
                    "status": "error",
                    "error": "SAbDab returned non-JSON antigen data",
                }
            antigen = antigen_response.json()
            if not isinstance(antigen, dict) or antigen.get("id") != antigen_id:
                return {"status": "error", "error": "SAbDab antigen identity mismatch"}
            antigen_instances.append(antigen)

        return {
            "status": "success",
            "antibody_instances": antibody_instances,
            "antigen_instances": antigen_instances,
        }

    @staticmethod
    def _coerce(value: str):
        """Convert SAbDab TSV string cells to typed values.

        SAbDab writes the literal strings 'None'/'NA'/'' for missing fields and
        'True'/'False' for boolean flags. Numeric fields (resolution, r_free)
        come back as decimal strings.
        """
        if value is None:
            return None
        stripped = value.strip()
        if stripped in ("", "None", "NA", "na", "N/A"):
            return None
        if stripped == "True":
            return True
        if stripped == "False":
            return False
        # Try numeric conversion (resolution, r_free, r_factor, delta_g, ...)
        try:
            if "." in stripped or "e" in stripped.lower():
                return float(stripped)
            return int(stripped)
        except ValueError:
            return stripped

    def _get_structure_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get per-structure curated antibody annotations for a PDB ID.

        Returns the SAbDab summary TSV row(s) for the structure: antigen
        name/type/species, heavy/light chain species and subclass, resolution,
        experimental method, R-free / R-factor, scFv and engineered flags, and
        (when curated) binding affinity Kd, delta_G, affinity method,
        temperature and PMID.

        Args:
            arguments: Dict containing:
                - pdb_id: 4-character PDB ID (alias: pdb_code, pdb)
        """
        pdb_id = (
            arguments.get("pdb_id")
            or arguments.get("pdb_code")
            or arguments.get("pdb")
            or ""
        )
        if not pdb_id:
            return {
                "status": "error",
                "error": "Missing required parameter: pdb_id",
            }

        pdb_id_lower = pdb_id.strip().lower()

        try:
            response = requests.get(
                f"{SABDAB2_BASE_URL}/api/pdb/{self._normalize_pdb_id(pdb_id_lower)}",
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/SAbDab",
                    "Accept": "text/tab-separated-values",
                },
            )

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": (
                        f"Structure not found in SAbDab: {pdb_id}. "
                        "SAbDab only annotates PDB entries containing antibody structures."
                    ),
                }

            response.raise_for_status()

            if "json" in response.headers.get("Content-Type", ""):
                source_record = response.json()
                internal_pdb_id = self._normalize_pdb_id(pdb_id_lower)
                if (
                    not isinstance(source_record, dict)
                    or source_record.get("id") != internal_pdb_id
                ):
                    return {
                        "status": "error",
                        "error": "SAbDab structure identity conflicts with the requested PDB ID",
                    }
                related = self._get_structure_relationships(internal_pdb_id)
                if related.get("status") == "error":
                    return related
                antibodies = related["antibody_instances"]
                antigens = related["antigen_instances"]
                first_antibody = antibodies[0] if antibodies else {}
                first_antigen = antigens[0] if antigens else {}
                antigen_entity = first_antigen.get("polymer_instance") or first_antigen.get(
                    "non_polymer_instance"
                ) or {}
                polymers = {
                    item.get("sabdab_auth_asym_id"): item
                    for item in source_record.get("polymer_instances", [])
                }
                heavy = first_antibody.get("heavy_like_segment") or {}
                light = first_antibody.get("light_like_segment") or {}
                heavy_polymer = polymers.get(heavy.get("sabdab_auth_asym_id"), {})
                light_polymer = polymers.get(light.get("sabdab_auth_asym_id"), {})
                return {
                    "status": "success",
                    "data": {
                        "pdb_id": pdb_id_lower,
                        "sabdab2_pdb_id": internal_pdb_id,
                        "name": source_record.get("name"),
                        "antigen_name": antigen_entity.get("name"),
                        "antigen_type": antigen_entity.get("entity_type"),
                        "antigen_species": antigen_entity.get("organism_scientific"),
                        "heavy_species": heavy_polymer.get("organism_scientific"),
                        "light_species": light_polymer.get("organism_scientific"),
                        "resolution": source_record.get("resolution"),
                        "method": source_record.get("structure_method"),
                        "r_free": source_record.get("r_free"),
                        "r_factor": source_record.get("r_work"),
                        "heavy_subclass": heavy.get("v_gene"),
                        "light_subclass": light.get("v_gene"),
                        "light_ctype": light.get("type"),
                        "scfv": first_antibody.get("type") == "SCFV",
                        "engineered": None,
                        "affinity": None,
                        "delta_g": None,
                        "affinity_method": None,
                        "temperature": None,
                        "pmid": None,
                        "chains": antibodies,
                        "count": len(antibodies),
                        "antigen_instances": antigens,
                        "source_record": source_record,
                        "source_record_complete": True,
                    },
                    "metadata": {
                        "source": "SAbDab2",
                        "summary_url": response.url,
                        "note": (
                            "Current SAbDab2 JSON data; unavailable legacy affinity "
                            "fields are explicitly null rather than silently omitted."
                        ),
                    },
                }

            text = response.text
            content_type = response.headers.get("Content-Type", "")

            # Expect a TSV with a header row + one row per antibody chain pairing.
            if "tab-separated" not in content_type and "\t" not in text:
                # Fix-R17D-3: see the matching detection in _get_structure
                # -- SAbDab's new site returns its SPA shell HTML instead
                # of TSV data at this URL now, which the old message here
                # ("may not be an antibody complex") misleadingly blamed on
                # the structure itself rather than the actual cause
                # (upstream site migration), confirmed live even for
                # verified real antibody-antigen complexes.
                if self._looks_like_html(text):
                    return {
                        "status": "error",
                        "error": (
                            "SAbDab appears to have migrated to a new site "
                            "(SAbDab2) with no public summary-data API "
                            "currently reachable at this URL -- got an "
                            "HTML page instead of TSV data. This is an "
                            "upstream issue, not a query problem."
                        ),
                    }
                return {
                    "status": "error",
                    "error": (
                        f"SAbDab did not return tabular data for {pdb_id} "
                        "(got non-tabular content, likely an HTML page from "
                        "SAbDab's current site, rather than 'structure may "
                        "not be an antibody complex' -- confirmed live this "
                        "now happens even for known antibody structures)."
                    ),
                }

            reader = csv.DictReader(io.StringIO(text.strip()), delimiter="\t")
            rows = []
            for raw in reader:
                rows.append({k: self._coerce(v) for k, v in raw.items()})

            if not rows:
                return {
                    "status": "error",
                    "error": f"No SAbDab annotation rows found for {pdb_id}.",
                }

            first = rows[0]
            return {
                "status": "success",
                "data": {
                    "pdb_id": pdb_id_lower,
                    "antigen_name": first.get("antigen_name"),
                    "antigen_type": first.get("antigen_type"),
                    "antigen_species": first.get("antigen_species"),
                    "heavy_species": first.get("heavy_species"),
                    "light_species": first.get("light_species"),
                    "resolution": first.get("resolution"),
                    "method": first.get("method"),
                    "r_free": first.get("r_free"),
                    "r_factor": first.get("r_factor"),
                    "heavy_subclass": first.get("heavy_subclass"),
                    "light_subclass": first.get("light_subclass"),
                    "light_ctype": first.get("light_ctype"),
                    "scfv": first.get("scfv"),
                    "engineered": first.get("engineered"),
                    "affinity": first.get("affinity"),
                    "delta_g": first.get("delta_g"),
                    "affinity_method": first.get("affinity_method"),
                    "temperature": first.get("temperature"),
                    "pmid": first.get("pmid"),
                    "chains": rows,
                    "count": len(rows),
                },
                "metadata": {
                    "source": "SAbDab",
                    "summary_url": f"{SABDAB_BASE_URL}/summary/{pdb_id_lower}/",
                    "note": (
                        "'chains' lists one row per antibody chain pairing in the "
                        "structure; top-level fields are taken from the first pairing."
                    ),
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get SAbDab database summary statistics.

        Args:
            arguments: Dict (no required parameters)
        """
        # Redirect hint if user passed a PDB ID (Feature-125B-003)
        pdb = arguments.get("pdb") or arguments.get("pdb_id")
        if pdb:
            return {
                "status": "error",
                "error": (
                    f"SAbDab_get_summary returns database-wide statistics, not per-structure data. "
                    f"To retrieve structure '{pdb}', use SAbDab_get_structure instead."
                ),
            }
        try:
            response = requests.get(
                f"{SABDAB2_BASE_URL}/api/stats/summary",
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/SAbDab",
                    "Accept": "application/json",
                },
            )

            if "json" in response.headers.get("Content-Type", ""):
                data = response.json()
            else:
                return {
                    "status": "error",
                    "error": (
                        "SAbDab statistics returned non-JSON content; refusing "
                        "to substitute static text for current database statistics"
                    ),
                }

            required = {
                "antibody_instances",
                "PDB_entries",
                "SAbDab2_entries",
                "with_antigen",
                "last_update",
            }
            if not isinstance(data, dict) or not required.issubset(data):
                return {"status": "error", "error": "SAbDab returned malformed statistics"}

            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "source": "SAbDab2",
                    "api_url": response.url,
                },
            }

        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
