"""
BRENDA Enzyme Database API tool for ToolUniverse.

BRENDA is the largest enzyme database containing functional data like
Km, Vmax, turnover numbers, and inhibitor information.

API: BRENDA SOAP web service (zeep client)
Auth: BRENDA_EMAIL + BRENDA_PASSWORD environment variables required.
Register for free at: https://www.brenda-enzymes.org/register.php
WSDL: https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl
"""

import hashlib
import os
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

BRENDA_WSDL = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"


def _get_client():
    """Return a cached zeep SOAP client for BRENDA."""
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
    """Parse SOAP response into a list of dicts."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [dict(r) if hasattr(r, "__iter__") else {"value": r} for r in raw]
    if hasattr(raw, "__dict__"):
        return [dict(raw.__dict__)]
    return []


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
        self.parameter = tool_config.get("parameter", {})

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
        operation = arguments.get("operation", "") or self.get_schema_const_operation()

        dispatch = {
            "get_km": self._get_km,
            "get_kcat": self._get_kcat,
            "get_inhibitors": self._get_inhibitors,
            "get_enzyme_info": self._get_enzyme_info,
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
            client = _get_client()
            params = f"ecNumber*{ec_number}#kmValue*#kmValueMaximum*#substrate*#commentary*#organism*{organism}#ligandStructureId*#literature*"
            raw = client.service.getKmValue(email, pw_hash, params)
            rows = _parse_rows(raw)
            km_values = [
                {
                    "km_value": str(r.get("kmValue", "")),
                    "substrate": str(r.get("substrate", "")),
                    "organism": str(r.get("organism", "")),
                    "comment": str(r.get("commentary", "")),
                }
                for r in rows
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
            client = _get_client()
            params = f"ecNumber*{ec_number}#turnoverNumber*#turnoverNumberMaximum*#substrate*#commentary*#organism*{organism}#ligandStructureId*#literature*"
            raw = client.service.getTurnoverNumber(email, pw_hash, params)
            rows = _parse_rows(raw)
            kcat_values = [
                {
                    "kcat_value": str(r.get("turnoverNumber", "")),
                    "substrate": str(r.get("substrate", "")),
                    "organism": str(r.get("organism", "")),
                    "comment": str(r.get("commentary", "")),
                }
                for r in rows
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
            client = _get_client()
            params = f"ecNumber*{ec_number}#inhibitor*#commentary*#organism*{organism}#ligandStructureId*#literature*"
            raw = client.service.getInhibitors(email, pw_hash, params)
            rows = _parse_rows(raw)
            inhibitors = [
                {
                    "inhibitor": str(r.get("inhibitor", "")),
                    "ki_value": str(r.get("kiValue", "")),
                    "organism": str(r.get("organism", "")),
                    "comment": str(r.get("commentary", "")),
                }
                for r in rows
            ]
            return {
                "status": "success",
                "data": {
                    "ec_number": ec_number,
                    "organism": organism or "all",
                    "inhibitors": inhibitors,
                    "count": len(inhibitors),
                },
                "metadata": {
                    "source": "BRENDA SOAP",
                    "parameter": "Inhibitors",
                    "unit": "mM",
                },
            }
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
            client = _get_client()
            params = f"ecNumber*{ec_number}#organism*#recommendedName*#systematicName*"
            raw = client.service.getSystematicName(email, pw_hash, params)
            rows = _parse_rows(raw)
            info = [
                {
                    "systematic_name": str(r.get("systematicName", "")),
                    "organism": str(r.get("organism", "")),
                }
                for r in rows
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
        except Exception as e:
            return {"status": "error", "error": f"BRENDA query failed: {str(e)}"}
