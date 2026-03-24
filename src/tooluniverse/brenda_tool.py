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
