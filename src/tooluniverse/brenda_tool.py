"""
BRENDA Enzyme Database API tool for ToolUniverse.

BRENDA is the largest enzyme database containing functional data like
Km, Vmax, turnover numbers, and inhibitor information.

API: BRENDA SOAP web service (zeep client) + ExPASy ENZYME (REST, no auth)
Auth: BRENDA_EMAIL + BRENDA_PASSWORD environment variables required for
      SOAP-only operations (get_km, get_kcat, get_inhibitors, get_enzyme_info).
      The get_enzyme_kinetics operation works WITHOUT credentials by using
      ExPASy ENZYME + SABIO-RK as primary data sources.
Register for free at: https://www.brenda-enzymes.org/register.php
WSDL: https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl
"""

import hashlib
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

BRENDA_WSDL = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"


def _get_client():
    """Return a zeep SOAP client for BRENDA."""
    try:
        from zeep import Client, Settings

        return Client(BRENDA_WSDL, settings=Settings(strict=False))
    except ImportError:
        raise RuntimeError(
            "zeep is required for BRENDA SOAP access. Install with: pip install zeep"
        )


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _parse_rows(raw) -> List[Dict[str, Any]]:
    """Parse a zeep response object into a list of plain dicts."""
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    result = []
    for item in items:
        if hasattr(item, "__dict__"):
            result.append(
                {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
            )
        elif isinstance(item, dict):
            result.append(item)
    return result


@register_tool("BRENDATool")
class BRENDATool(BaseTool):
    """
    Tool for querying BRENDA enzyme database via SOAP API.

    Supports Km, kcat, inhibitor, and general enzyme info queries.
    Requires BRENDA_EMAIL and BRENDA_PASSWORD environment variables.
    Register for free at https://www.brenda-enzymes.org/register.php
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)

    def _credentials(self) -> Optional[tuple]:
        email = os.environ.get("BRENDA_EMAIL", "")
        password = os.environ.get("BRENDA_PASSWORD", "")
        if not email or not password:
            return None
        return email, _hash_password(password)

    def _auth_error(self) -> Dict[str, Any]:
        return {
            "status": "error",
            "error": (
                "BRENDA requires authentication. "
                "Set BRENDA_EMAIL and BRENDA_PASSWORD environment variables. "
                "Register for free at https://www.brenda-enzymes.org/register.php"
            ),
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Feature-111B-006: enzyme_id as alias for ec_number
        if not arguments.get("ec_number") and arguments.get("enzyme_id"):
            arguments = dict(arguments, ec_number=arguments["enzyme_id"])

        operation = arguments.get("operation", "") or self.get_schema_const_operation()

        dispatch = {
            "get_km": self._get_km,
            "get_kcat": self._get_kcat,
            "get_inhibitors": self._get_inhibitors,
            "get_enzyme_info": self._get_enzyme_info,
            "get_enzyme_kinetics": self._get_enzyme_kinetics,
        }
        handler = dispatch.get(operation)
        if handler is None:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: {', '.join(dispatch)}",
            }
        return handler(arguments)

    def _get_km(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {"status": "error", "error": "Missing required parameter: ec_number"}
        creds = self._credentials()
        if not creds:
            return self._auth_error()
        email, pw_hash = creds
        organism = arguments.get("organism", "")

        try:
            from zeep.exceptions import Fault

            client = _get_client()
            raw = client.service.getKmValue(
                email=email,
                password=pw_hash,
                ecNumber=ec_number,
                organism=organism,
                kmValue="",
                kmValueMaximum="",
                substrate="",
                commentary="",
                ligandStructureId="",
                literature="",
            )
            rows = _parse_rows(raw)
            km_values = [
                {
                    "km_value": str(r.get("kmValue", "")),
                    "substrate": str(r.get("substrate", "")),
                    "organism": str(r.get("organism", "")),
                    "comment": str(r.get("commentary", "")),
                }
                for r in rows
                if r.get("kmValue")
            ]
            return {
                "status": "success",
                "data": {
                    "ec_number": ec_number,
                    "organism": organism or "all",
                    "km_values": km_values,
                    "count": len(km_values),
                },
                "metadata": {"source": "BRENDA SOAP", "parameter": "Km", "unit": "mM"},
            }
        except Fault as f:
            msg = str(f)
            if "wrong" in msg.lower() or "password" in msg.lower():
                return {
                    "status": "error",
                    "error": "Invalid BRENDA credentials. Check BRENDA_EMAIL and BRENDA_PASSWORD.",
                }
            return {"status": "error", "error": f"BRENDA SOAP fault: {msg}"}
        except Exception as e:
            return {"status": "error", "error": f"BRENDA query failed: {str(e)}"}

    def _get_kcat(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {"status": "error", "error": "Missing required parameter: ec_number"}
        creds = self._credentials()
        if not creds:
            return self._auth_error()
        email, pw_hash = creds
        organism = arguments.get("organism", "")

        try:
            from zeep.exceptions import Fault

            client = _get_client()
            raw = client.service.getTurnoverNumber(
                email=email,
                password=pw_hash,
                ecNumber=ec_number,
                organism=organism,
                turnoverNumber="",
                turnoverNumberMaximum="",
                substrate="",
                commentary="",
                ligandStructureId="",
                literature="",
            )
            rows = _parse_rows(raw)
            kcat_values = [
                {
                    "kcat_value": str(r.get("turnoverNumber", "")),
                    "substrate": str(r.get("substrate", "")),
                    "organism": str(r.get("organism", "")),
                    "comment": str(r.get("commentary", "")),
                }
                for r in rows
                if r.get("turnoverNumber")
            ]
            return {
                "status": "success",
                "data": {
                    "ec_number": ec_number,
                    "organism": organism or "all",
                    "kcat_values": kcat_values,
                    "count": len(kcat_values),
                },
                "metadata": {
                    "source": "BRENDA SOAP",
                    "parameter": "kcat",
                    "unit": "1/s",
                },
            }
        except Fault as f:
            msg = str(f)
            if "wrong" in msg.lower() or "password" in msg.lower():
                return {
                    "status": "error",
                    "error": "Invalid BRENDA credentials. Check BRENDA_EMAIL and BRENDA_PASSWORD.",
                }
            return {"status": "error", "error": f"BRENDA SOAP fault: {msg}"}
        except Exception as e:
            return {"status": "error", "error": f"BRENDA query failed: {str(e)}"}

    def _get_inhibitors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {"status": "error", "error": "Missing required parameter: ec_number"}
        creds = self._credentials()
        if not creds:
            return self._auth_error()
        email, pw_hash = creds
        organism = arguments.get("organism", "")

        try:
            from zeep.exceptions import Fault

            client = _get_client()
            raw = client.service.getInhibitors(
                email=email,
                password=pw_hash,
                ecNumber=ec_number,
                organism=organism,
                inhibitor="",
                commentary="",
                ligandStructureId="",
                literature="",
            )
            rows = _parse_rows(raw)
            inhibitors = [
                {
                    "inhibitor": str(r.get("inhibitor", "")),
                    "organism": str(r.get("organism", "")),
                    "comment": str(r.get("commentary", "")),
                }
                for r in rows
                if r.get("inhibitor")
            ]
            return {
                "status": "success",
                "data": {
                    "ec_number": ec_number,
                    "organism": organism or "all",
                    "inhibitors": inhibitors,
                    "count": len(inhibitors),
                },
                "metadata": {"source": "BRENDA SOAP"},
            }
        except Fault as f:
            msg = str(f)
            if "wrong" in msg.lower() or "password" in msg.lower():
                return {
                    "status": "error",
                    "error": "Invalid BRENDA credentials. Check BRENDA_EMAIL and BRENDA_PASSWORD.",
                }
            return {"status": "error", "error": f"BRENDA SOAP fault: {msg}"}
        except Exception as e:
            return {"status": "error", "error": f"BRENDA query failed: {str(e)}"}

    def _get_enzyme_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {"status": "error", "error": "Missing required parameter: ec_number"}
        creds = self._credentials()
        if not creds:
            return self._auth_error()
        email, pw_hash = creds

        try:
            from zeep.exceptions import Fault

            client = _get_client()
            raw = client.service.getSystematicName(
                email=email,
                password=pw_hash,
                ecNumber=ec_number,
                organism="",
                systematicName="",
            )
            rows = _parse_rows(raw)
            info = [
                {
                    "systematic_name": str(r.get("systematicName", "")),
                    "organism": str(r.get("organism", "")),
                }
                for r in rows
                if r.get("systematicName")
            ]
            return {
                "status": "success",
                "data": {
                    "ec_number": ec_number,
                    "info": info or [{"note": "No systematic name data found"}],
                    "count": len(info),
                },
                "metadata": {"source": "BRENDA SOAP"},
            }
        except Fault as f:
            msg = str(f)
            if "wrong" in msg.lower() or "password" in msg.lower():
                return {
                    "status": "error",
                    "error": "Invalid BRENDA credentials. Check BRENDA_EMAIL and BRENDA_PASSWORD.",
                }
            return {"status": "error", "error": f"BRENDA SOAP fault: {msg}"}
        except Exception as e:
            return {"status": "error", "error": f"BRENDA query failed: {str(e)}"}

    # ---- get_enzyme_kinetics: NO AUTH REQUIRED ----
    # Uses ExPASy ENZYME (enzyme info) + SABIO-RK (kinetic parameters)
    # Optionally enriched with BRENDA SOAP if credentials are available.

    def _resolve_ec_from_name(self, enzyme_name: str) -> Optional[str]:
        """Resolve enzyme name to EC number via UniProt search."""
        try:
            url = (
                "https://rest.uniprot.org/uniprotkb/search"
                f"?query=protein_name:{enzyme_name}+AND+ec:*"
                "&fields=ec&format=json&size=5"
            )
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            for result in data.get("results", []):
                desc = result.get("proteinDescription", {})
                rec_name = desc.get("recommendedName", {})
                for ec_entry in rec_name.get("ecNumbers", []):
                    val = ec_entry.get("value", "")
                    if val and not val.endswith("-"):
                        return val
            return None
        except Exception:
            return None

    def _fetch_expasy_enzyme(self, ec_number: str) -> Dict[str, Any]:
        """Fetch enzyme info from ExPASy ENZYME database (no auth)."""
        url = f"https://enzyme.expasy.org/EC/{ec_number}.txt"
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return {}

        data: Dict[str, Any] = {}
        for line in resp.text.strip().split("\n"):
            if line.startswith("ID   "):
                data["ec_number"] = line[5:].strip()
            elif line.startswith("DE   "):
                data["name"] = line[5:].strip().rstrip(".")
            elif line.startswith("AN   "):
                data.setdefault("alternative_names", []).append(
                    line[5:].strip().rstrip(".")
                )
            elif line.startswith("CA   "):
                data.setdefault("catalytic_activity", []).append(line[5:].strip())
            elif line.startswith("CC   "):
                data.setdefault("comments", []).append(line[5:].strip())
        return data

    def _fetch_sabiork_kinetics(
        self, ec_number: str, organism: str = "", limit: int = 20
    ) -> Dict[str, Any]:
        """Fetch kinetic parameters from SABIO-RK (no auth).

        Reuses shared parsing from sabiork_tool module.
        """
        from .sabiork_tool import (
            SABIORK_BASE,
            _is_no_data_response,
            _parse_entry_ids,
            _parse_sbml_kinetics,
        )

        query_parts = [f"ecnumber:{ec_number}"]
        if organism:
            query_parts.append(f'Organism:"{organism}"')
        query = " AND ".join(query_parts)

        resp = requests.get(
            f"{SABIORK_BASE}/searchKineticLaws/entryIDs?q={query}", timeout=20
        )
        if resp.status_code != 200:
            return {"kinetic_laws": [], "total_count": 0}

        if _is_no_data_response(resp.text):
            return {"kinetic_laws": [], "total_count": 0}

        try:
            entry_ids = _parse_entry_ids(resp.text)
        except ET.ParseError:
            return {"kinetic_laws": [], "total_count": 0}

        total = len(entry_ids)
        if total == 0:
            return {"kinetic_laws": [], "total_count": 0}

        fetch_ids = entry_ids[:limit]
        resp2 = requests.get(
            f"{SABIORK_BASE}/kineticLaws?kinlawids={','.join(fetch_ids)}", timeout=30
        )
        if resp2.status_code != 200:
            return {"kinetic_laws": [], "total_count": total}

        records = _parse_sbml_kinetics(resp2.text)
        for i, rec in enumerate(records):
            if i < len(fetch_ids):
                rec["sabiork_entry_id"] = fetch_ids[i]
        return {"kinetic_laws": records, "total_count": total}

    def _get_enzyme_kinetics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve comprehensive enzyme kinetics WITHOUT requiring BRENDA credentials.

        Uses ExPASy ENZYME for enzyme info + SABIO-RK for kinetic parameters.
        If BRENDA credentials are set, adds BRENDA data as enhancement.
        """
        ec_number = arguments.get("ec_number", "")
        enzyme_name = arguments.get("enzyme_name", "")
        organism = arguments.get("organism", "")
        limit = int(arguments.get("limit", 20))

        # Resolve enzyme name to EC number if needed
        if not ec_number and enzyme_name:
            ec_number = self._resolve_ec_from_name(enzyme_name) or ""
            if not ec_number:
                return {
                    "status": "error",
                    "error": (
                        f"Could not resolve enzyme name '{enzyme_name}' to an EC number. "
                        "Try providing the EC number directly (e.g., ec_number='1.1.1.1')."
                    ),
                }

        if not ec_number:
            return {
                "status": "error",
                "error": "Provide ec_number (e.g., '1.1.1.1') or enzyme_name (e.g., 'alcohol dehydrogenase')",
            }

        sources_used = []
        result: Dict[str, Any] = {"ec_number": ec_number}

        # 1. ExPASy ENZYME: enzyme identity and catalytic activity
        try:
            expasy = self._fetch_expasy_enzyme(ec_number)
            if expasy:
                result["enzyme_name"] = expasy.get("name", "")
                result["alternative_names"] = expasy.get("alternative_names", [])
                result["catalytic_activity"] = expasy.get("catalytic_activity", [])
                result["comments"] = expasy.get("comments", [])
                sources_used.append("ExPASy ENZYME")
        except Exception:
            pass  # Non-fatal, continue with kinetics

        # 2. SABIO-RK: kinetic parameters (Km, kcat, Ki, Vmax)
        try:
            sabio = self._fetch_sabiork_kinetics(ec_number, organism, limit)
            result["kinetic_parameters"] = sabio.get("kinetic_laws", [])
            result["sabiork_total_entries"] = sabio.get("total_count", 0)
            if sabio.get("kinetic_laws"):
                sources_used.append("SABIO-RK")

                # Aggregate summary statistics
                param_units = {"Km": "M", "kcat": "s^{-1}", "Ki": "M"}
                buckets: Dict[str, list] = {}
                for law in sabio.get("kinetic_laws", []):
                    for p in law.get("parameters", []):
                        ptype = p.get("type", "")
                        pval = p.get("value")
                        if isinstance(pval, (int, float)) and ptype in (
                            "Km",
                            "kcat",
                            "Ki",
                            "Vmax",
                        ):
                            buckets.setdefault(ptype, []).append(pval)

                summary: Dict[str, Any] = {}
                for ptype, vals in buckets.items():
                    s = sorted(vals)
                    entry: Dict[str, Any] = {
                        "count": len(s),
                        "min": s[0],
                        "max": s[-1],
                        "median": s[len(s) // 2],
                    }
                    if ptype in param_units:
                        entry["unit"] = param_units[ptype]
                    summary[ptype] = entry
                if summary:
                    result["parameter_summary"] = summary
        except Exception:
            pass  # Non-fatal

        # 3. Optional BRENDA SOAP enrichment (if credentials available)
        creds = self._credentials()
        if creds:
            try:
                from zeep.exceptions import Fault

                email, pw_hash = creds
                client = _get_client()

                # Fetch optimal pH
                try:
                    raw = client.service.getPhOptimum(
                        email=email,
                        password=pw_hash,
                        ecNumber=ec_number,
                        organism=organism or "",
                        phOptimum="",
                        phOptimumMaximum="",
                        commentary="",
                        literature="",
                    )
                    rows = _parse_rows(raw)
                    ph_data = [
                        {
                            "ph_optimum": str(r.get("phOptimum", "")),
                            "organism": str(r.get("organism", "")),
                        }
                        for r in rows
                        if r.get("phOptimum")
                    ]
                    if ph_data:
                        result["ph_optima"] = ph_data
                except Exception:
                    pass

                # Fetch optimal temperature
                try:
                    raw = client.service.getTemperatureOptimum(
                        email=email,
                        password=pw_hash,
                        ecNumber=ec_number,
                        organism=organism or "",
                        temperatureOptimum="",
                        temperatureOptimumMaximum="",
                        commentary="",
                        literature="",
                    )
                    rows = _parse_rows(raw)
                    temp_data = [
                        {
                            "temperature_optimum_C": str(
                                r.get("temperatureOptimum", "")
                            ),
                            "organism": str(r.get("organism", "")),
                        }
                        for r in rows
                        if r.get("temperatureOptimum")
                    ]
                    if temp_data:
                        result["temperature_optima"] = temp_data
                except Exception:
                    pass

                # Fetch specific activity
                try:
                    raw = client.service.getSpecificActivity(
                        email=email,
                        password=pw_hash,
                        ecNumber=ec_number,
                        organism=organism or "",
                        specificActivity="",
                        specificActivityMaximum="",
                        substrate="",
                        commentary="",
                        ligandStructureId="",
                        literature="",
                    )
                    rows = _parse_rows(raw)
                    sa_data = [
                        {
                            "specific_activity": str(r.get("specificActivity", "")),
                            "substrate": str(r.get("substrate", "")),
                            "organism": str(r.get("organism", "")),
                        }
                        for r in rows
                        if r.get("specificActivity")
                    ]
                    if sa_data:
                        result["specific_activity"] = sa_data
                except Exception:
                    pass

                sources_used.append("BRENDA SOAP")
            except Exception:
                pass  # BRENDA enrichment is optional

        if not sources_used:
            return {
                "status": "error",
                "error": f"No data found for EC {ec_number}. Verify the EC number is correct.",
            }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "sources": sources_used,
                "note": (
                    "ExPASy ENZYME and SABIO-RK data require no authentication. "
                    "Set BRENDA_EMAIL/BRENDA_PASSWORD for additional pH, temperature, "
                    "and specific activity data from BRENDA."
                ),
            },
        }
