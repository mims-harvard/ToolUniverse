"""NCI CACTUS Chemical Identifier Resolver tool for ToolUniverse.

The NCI Computer-Aided Chemistry (CACTUS) Chemical Identifier Resolver
is a free public service from the National Cancer Institute that converts
between chemical identifiers: names, SMILES, InChI, InChIKey, CAS numbers,
molecular formula, molecular weight, and more.

API: https://cactus.nci.nih.gov/chemical/structure/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

CACTUS_BASE_URL = "https://cactus.nci.nih.gov/chemical/structure"

VALID_REPRESENTATIONS = (
    "smiles",
    "iupac_name",
    "formula",
    "cas",
    "stdinchi",
    "stdinchikey",
    "mw",
    "names",
    "sdf",
    "inchi",
    "inchikey",
)


@register_tool("NCICACTUSTool")
class NCICACTUSTool(BaseTool):
    """
    Convert chemical identifiers using the NCI CACTUS resolver.

    Accepts chemical names, SMILES, InChI, InChIKey, or CAS numbers as input
    and returns the requested representation (SMILES, IUPAC name, InChI,
    InChIKey, molecular formula, molecular weight, CAS number, or synonyms).
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        identifier = (arguments.get("identifier") or "").strip()
        representation = (arguments.get("representation") or "smiles").strip().lower()
        resolve_all = bool(arguments.get("resolve_all", False))

        if not identifier:
            return {
                "status": "error",
                "error": "identifier is required",
                "retryable": False,
            }

        if representation not in VALID_REPRESENTATIONS:
            return {
                "status": "error",
                "error": f"representation must be one of: {', '.join(VALID_REPRESENTATIONS)}",
                "retryable": False,
            }

        if resolve_all:
            return self._resolve_multiple(identifier)

        return self._resolve_single(identifier, representation)

    def _resolve_single(self, identifier: str, representation: str) -> Dict[str, Any]:
        url = f"{CACTUS_BASE_URL}/{requests.utils.quote(identifier)}/{representation}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Could not resolve '{identifier}' — identifier not recognized",
                    "retryable": False,
                }
            resp.raise_for_status()
            text = resp.text.strip()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            value = lines if len(lines) > 1 else (lines[0] if lines else "")
            return {
                "status": "success",
                "data": {
                    "identifier": identifier,
                    "representation": representation,
                    "result": value,
                },
                "metadata": {"source": "NCI CACTUS Chemical Identifier Resolver"},
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "NCI CACTUS request timed out",
                "retryable": True,
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NCI CACTUS",
                "retryable": True,
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"NCI CACTUS HTTP {code}",
                "retryable": code in (429, 502, 503),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"NCI CACTUS error: {e}",
                "retryable": False,
            }

    def _resolve_multiple(self, identifier: str) -> Dict[str, Any]:
        targets: List[str] = [
            "smiles",
            "iupac_name",
            "formula",
            "mw",
            "stdinchikey",
            "cas",
        ]
        results: Dict[str, Any] = {}
        for rep in targets:
            url = f"{CACTUS_BASE_URL}/{requests.utils.quote(identifier)}/{rep}"
            try:
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    lines = [
                        ln.strip()
                        for ln in resp.text.strip().splitlines()
                        if ln.strip()
                    ]
                    results[rep] = (
                        lines if len(lines) > 1 else (lines[0] if lines else None)
                    )
                else:
                    results[rep] = None
            except Exception:
                results[rep] = None

        if all(v is None for v in results.values()):
            return {
                "status": "error",
                "error": f"Could not resolve '{identifier}' — identifier not recognized",
                "retryable": False,
            }

        return {
            "status": "success",
            "data": {"identifier": identifier, **results},
            "metadata": {
                "source": "NCI CACTUS Chemical Identifier Resolver",
                "resolve_all": True,
            },
        }
