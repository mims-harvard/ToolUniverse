"""
OPSIN tool for ToolUniverse — deterministic IUPAC chemical name -> structure.

OPSIN (Open Parser for Systematic IUPAC Nomenclature) is a grammar-based parser
that converts systematic chemical names into structures (SMILES / InChI / InChIKey).
Unlike a name-lookup service (e.g. NCI/CADD Cactus, which matches names against a
database), OPSIN parses the name itself, so it resolves novel systematic names that
are not present in any database.

API: https://www.ebi.ac.uk/opsin/ws/{name}.json  (EBI-hosted, public, no auth, MIT-licensed)
On a parseable name it returns {"status": "SUCCESS", "smiles", "inchi",
"stdinchi", "stdinchikey", "cml"}; on an unparseable name {"status": "FAILURE", "message"}.
"""

from typing import Any, Dict
from urllib.parse import quote

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

OPSIN_BASE = "https://www.ebi.ac.uk/opsin/ws"


@register_tool("OPSINNameToStructureTool")
class OPSINNameToStructureTool(BaseTool):
    """Convert a systematic (IUPAC) chemical name to a chemical structure."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        name = (arguments.get("name") or "").strip()
        if not name:
            return {"status": "error", "error": "'name' parameter is required"}

        url = f"{OPSIN_BASE}/{quote(name, safe='')}.json"
        try:
            resp = requests.get(
                url, headers={"Accept": "application/json"}, timeout=self.timeout
            )
            # OPSIN returns HTTP 404 (with a JSON body) for names it cannot parse;
            # treat that as a structured "not parseable" result, not a hard error.
            if resp.status_code not in (200, 404):
                resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"OPSIN request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"OPSIN request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "OPSIN returned a non-JSON response"}

        if (payload.get("status") or "").upper() != "SUCCESS":
            return {
                "status": "success",
                "data": {
                    "name": name,
                    "parsed": False,
                    "smiles": None,
                    "inchi": None,
                    "inchikey": None,
                },
                "metadata": {
                    "parsed": False,
                    "note": payload.get("message")
                    or f"OPSIN could not parse the name '{name}'. "
                    "It must be a systematic/IUPAC name, not a trade or trivial name.",
                    "source": "OPSIN (EBI)",
                },
            }

        return {
            "status": "success",
            "data": {
                "name": name,
                "parsed": True,
                "smiles": payload.get("smiles"),
                "inchi": payload.get("stdinchi") or payload.get("inchi"),
                "inchikey": payload.get("stdinchikey"),
            },
            "metadata": {"parsed": True, "source": "OPSIN (EBI)"},
        }
