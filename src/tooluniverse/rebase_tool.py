# rebase_tool.py
"""
REBASE restriction enzyme database tool for ToolUniverse.

REBASE (New England Biolabs) is the reference catalogue of restriction
enzymes and their recognition sequences: ~6,000 enzymes with cleavage
positions, source organisms, isoschizomers, and commercial availability.

ToolUniverse already computes with restriction enzymes -- DNA_find_restriction_sites,
DNA_virtual_digest and DNA_golden_gate_design -- but those work from a curated
set of 25 common enzymes. This tool supplies the full reference catalogue, so
an enzyme can be looked up by name or by the site it recognizes before being
used in those calculators.

Data: http://rebase.neb.com/rebase/link_allenz (flat file, refreshed monthly)
No authentication required.
"""

import re
import threading
from typing import Dict, Any, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

REBASE_ALLENZ_URL = "http://rebase.neb.com/rebase/link_allenz"

# IUPAC ambiguity codes, used to expand a recognition site into a regex.
_IUPAC = {
    "A": "A", "C": "C", "G": "G", "T": "T",
    "R": "[AG]", "Y": "[CT]", "M": "[AC]", "K": "[GT]",
    "S": "[CG]", "W": "[AT]", "B": "[CGT]", "D": "[AGT]",
    "H": "[ACT]", "V": "[ACG]", "N": ".",
}


def _clean_site(site: str) -> str:
    """Strip cleavage annotation from a recognition sequence.

    REBASE writes cleavage inside the site with '^' (G^AATTC) or outside it
    with offsets in parentheses (GACGC(5/10)).
    """
    return re.sub(r"\(.*?\)", "", site or "").replace("^", "").strip().upper()


def _site_to_regex(site: str) -> Optional[str]:
    """Translate an IUPAC recognition site into a regex, or None if unusable."""
    cleaned = _clean_site(site)
    if not cleaned or any(c not in _IUPAC for c in cleaned):
        return None
    return "".join(_IUPAC[c] for c in cleaned)


def _parse_allenz(text: str) -> List[Dict[str, Any]]:
    """Parse the REBASE allenz flat file into enzyme records.

    Records are blocks of <n>-tagged lines: 1 name, 2 prototype,
    3 microorganism, 4 source, 5 recognition sequence, 6 methylation,
    7 commercial suppliers, 8 references.
    """
    enzymes: List[Dict[str, Any]] = []
    current: Dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^<(\d)>(.*)$", line)
        if not match:
            continue
        field, value = match.group(1), match.group(2).strip()
        if field == "1":
            if current.get("name"):
                enzymes.append(_finalize(current))
            current = {"name": value}
        elif field == "2":
            current["prototype"] = value
        elif field == "3":
            current["organism"] = value
        elif field == "4":
            current["source"] = value
        elif field == "5":
            current["site"] = value
        elif field == "6":
            current["methylation"] = value
        elif field == "7":
            current["suppliers"] = value
    if current.get("name"):
        enzymes.append(_finalize(current))
    return enzymes


def _finalize(record: Dict[str, str]) -> Dict[str, Any]:
    """Normalize one parsed block into the shape the tool returns."""
    site = record.get("site", "")
    return {
        "name": record.get("name", ""),
        "prototype": record.get("prototype") or record.get("name", ""),
        "recognition_site": site,
        "blunt_or_sticky": _cut_style(site),
        "organism": record.get("organism") or None,
        "source": record.get("source") or None,
        "methylation": record.get("methylation") or None,
        "commercially_available": bool(record.get("suppliers")),
        "supplier_codes": record.get("suppliers") or None,
    }


def _cut_style(site: str) -> Optional[str]:
    """Classify the cut as blunt, sticky, or unknown from the '^' position."""
    if "^" not in site or "(" in site:
        return None
    cleaned = site.replace("^", "")
    cut = site.index("^")
    # A cut exactly at the midpoint of a palindromic site leaves blunt ends.
    return "blunt" if cut * 2 == len(cleaned) else "sticky"


@register_tool("REBASETool")
class REBASETool(BaseTool):
    """
    Tool for looking up restriction enzymes in REBASE.

    Supports lookup by enzyme name, search by recognition site (including
    IUPAC ambiguity and matching against a DNA sequence), and listing
    isoschizomers that share a prototype.

    No authentication required.
    """

    _cache: Optional[List[Dict[str, Any]]] = None
    _cache_lock = threading.Lock()

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get("operation", "get_enzyme")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the REBASE lookup."""
        try:
            if self.operation == "get_enzyme":
                return self._get_enzyme(arguments)
            if self.operation == "search_by_site":
                return self._search_by_site(arguments)
            if self.operation == "list_isoschizomers":
                return self._list_isoschizomers(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"REBASE request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to REBASE. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"REBASE returned HTTP {code}"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying REBASE: {str(e)}"}

    def _enzymes(self) -> List[Dict[str, Any]]:
        """Return the parsed catalogue, downloading it once per process."""
        if REBASETool._cache is not None:
            return REBASETool._cache
        with REBASETool._cache_lock:
            if REBASETool._cache is None:
                response = requests.get(REBASE_ALLENZ_URL, timeout=self.timeout)
                response.raise_for_status()
                REBASETool._cache = _parse_allenz(response.text)
        return REBASETool._cache

    def _get_enzyme(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up one enzyme by name."""
        name = (arguments.get("name") or "").strip()
        if not name:
            return {
                "status": "error",
                "error": "name is required, e.g. 'EcoRI'. Enzyme names are "
                "case-sensitive in REBASE but this tool matches case-insensitively.",
            }

        enzymes = self._enzymes()
        match = next(
            (e for e in enzymes if e["name"].lower() == name.lower()), None
        )
        if match is None:
            near = [e["name"] for e in enzymes if e["name"].lower().startswith(
                name.lower()[:4])][:5]
            hint = f" Similar names: {', '.join(near)}." if near else ""
            return {
                "status": "error",
                "error": f"No REBASE enzyme named '{name}'.{hint}",
            }

        isoschizomers = [
            e["name"]
            for e in enzymes
            if e["prototype"] == match["prototype"] and e["name"] != match["name"]
        ]

        return {
            "status": "success",
            "data": dict(match, isoschizomer_count=len(isoschizomers),
                         isoschizomers=isoschizomers[:25]),
            "metadata": {
                "name": match["name"],
                "catalogue_size": len(enzymes),
                "source": "REBASE (New England Biolabs)",
            },
        }

    def _search_by_site(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find enzymes by recognition site, or that cut a given sequence."""
        site = (arguments.get("site") or "").strip().upper()
        sequence = (arguments.get("sequence") or "").strip().upper()
        if not site and not sequence:
            return {
                "status": "error",
                "error": "Provide either site (a recognition sequence such as "
                "'GAATTC') or sequence (a DNA sequence to find cutters for).",
            }

        enzymes = self._enzymes()
        only_commercial = bool(arguments.get("only_commercial"))
        matches: List[Dict[str, Any]] = []

        for enzyme in enzymes:
            if only_commercial and not enzyme["commercially_available"]:
                continue
            cleaned = _clean_site(enzyme["recognition_site"])
            if not cleaned:
                continue
            if site:
                if cleaned == site:
                    matches.append(enzyme)
            else:
                pattern = _site_to_regex(enzyme["recognition_site"])
                if pattern and re.search(pattern, sequence):
                    hits = len(re.findall(f"(?={pattern})", sequence))
                    matches.append(dict(enzyme, cut_site_count=hits))

        matches.sort(key=lambda e: e["name"])
        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 200)

        return {
            "status": "success",
            "data": matches[:limit],
            "metadata": {
                "query_site": site or None,
                "query_sequence_length": len(sequence) or None,
                "total_matching": len(matches),
                "returned": len(matches[:limit]),
                "only_commercial": only_commercial,
                "catalogue_size": len(enzymes),
                "source": "REBASE (New England Biolabs)",
            },
        }

    def _list_isoschizomers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all enzymes sharing a prototype (same recognition specificity)."""
        name = (arguments.get("name") or "").strip()
        if not name:
            return {
                "status": "error",
                "error": "name is required, e.g. 'EcoRI'.",
            }

        enzymes = self._enzymes()
        seed = next((e for e in enzymes if e["name"].lower() == name.lower()), None)
        if seed is None:
            return {
                "status": "error",
                "error": f"No REBASE enzyme named '{name}'.",
            }

        family = [e for e in enzymes if e["prototype"] == seed["prototype"]]
        family.sort(key=lambda e: (not e["commercially_available"], e["name"]))

        return {
            "status": "success",
            "data": family,
            "metadata": {
                "query": seed["name"],
                "prototype": seed["prototype"],
                "recognition_site": seed["recognition_site"],
                "family_size": len(family),
                "commercially_available_count": sum(
                    1 for e in family if e["commercially_available"]
                ),
                "source": "REBASE (New England Biolabs)",
            },
        }
