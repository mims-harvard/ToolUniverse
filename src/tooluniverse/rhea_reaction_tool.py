# rhea_reaction_tool.py
"""
Rhea reaction-detail tool for ToolUniverse.

Rhea (https://www.rhea-db.org) is an expert-curated knowledgebase of chemical
and transport reactions of biological interest from the SIB Swiss Institute of
Bioinformatics. Every reaction is linked to ChEBI compounds and EC numbers.

This tool complements the existing Rhea *search* tools (RheaTool /
Rhea_search_reactions / Rhea_search_by_ec / Rhea_search_by_chebi) by fetching
the full structured detail of a *single* reaction given its Rhea identifier:
the parsed ChEBI participants (reactants and products, each with name + ChEBI
id), the chemical equation, EC numbers, enzyme count, PubMed references, the
KEGG / MetaCyc cross-references, and the balanced / transport flags.

Two endpoints are dispatched by the ``fields.endpoint`` JSON config value:

* ``get_reaction``     -> full reaction record (default)
* ``get_participants`` -> just the structured reactant/product participant lists

API: https://www.rhea-db.org/help/rest-api
The same ``/rhea`` query endpoint serves both JSON (rich equation HTML, balanced
/ transport flags) and TSV (EC numbers, PubMed, KEGG / MetaCyc xrefs); this tool
merges both into one structured record. No authentication required; free public
access.
"""

import re
import requests
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool

RHEA_BASE_URL = "https://www.rhea-db.org/rhea"

# Pull "<a data-molid="chebi:25858">1,7-dimethylxanthine</a>" out of htmlequation.
_PARTICIPANT_RE = re.compile(
    r'data-molid="chebi:(?P<chebi>\d+)"[^>]*>(?P<name>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
# Strip residual inline HTML tags (<i>, <small>, <sup>, <sub>) from names.
_TAG_RE = re.compile(r"<[^>]+>")


@register_tool("RheaReactionTool")
class RheaReactionTool(BaseTool):
    """Fetch full structured detail for a single Rhea biochemical reaction.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_reaction")

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Rhea API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Rhea API."}
        except requests.exceptions.HTTPError as e:
            code = getattr(getattr(e, "response", None), "status_code", "unknown")
            return {"status": "error", "error": f"Rhea API HTTP error: {code}"}
        except Exception as e:  # never raise out of run()
            return {
                "status": "error",
                "error": f"Unexpected error querying Rhea: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.endpoint == "get_reaction":
            return self._get_reaction(arguments, participants_only=False)
        if self.endpoint == "get_participants":
            return self._get_reaction(arguments, participants_only=True)
        return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_rhea_id(raw: Any) -> str:
        """Accept 10280, '10280', 'RHEA:10280', 'rhea:10280' -> '10280'."""
        text = str(raw).strip()
        if text.upper().startswith("RHEA:"):
            text = text[5:]
        return text.strip()

    @staticmethod
    def _clean_name(name: str) -> str:
        return _TAG_RE.sub("", name).strip()

    def _parse_participants(
        self, html_equation: str
    ) -> Dict[str, List[Dict[str, str]]]:
        """Split htmlequation on ' = ' and extract ChEBI participants per side."""
        reactants: List[Dict[str, str]] = []
        products: List[Dict[str, str]] = []
        if not html_equation:
            return {"reactants": reactants, "products": products}

        # The two reaction sides are separated by a bare ' = ' between spans.
        parts = re.split(r"</span>\s*=\s*<span", html_equation, maxsplit=1)
        if len(parts) == 2:
            left, right = parts[0], parts[1]
        else:
            # Fall back: no clean split -> treat everything as one side.
            left, right = html_equation, ""

        for side_html, bucket in ((left, reactants), (right, products)):
            for m in _PARTICIPANT_RE.finditer(side_html):
                bucket.append(
                    {
                        "chebi_id": f"CHEBI:{m.group('chebi')}",
                        "name": self._clean_name(m.group("name")),
                    }
                )
        return {"reactants": reactants, "products": products}

    @staticmethod
    def _split_multi(value: str) -> List[str]:
        """Split a semicolon-separated TSV cell into a clean list."""
        if not value:
            return []
        return [v.strip() for v in value.split(";") if v.strip()]

    def _fetch_json(self, rhea_id: str) -> Dict[str, Any]:
        params = {
            "query": f"RHEA:{rhea_id}",
            "columns": "rhea-id,equation",
            "format": "json",
            "limit": 1,
        }
        resp = requests.get(RHEA_BASE_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        results = payload.get("results", [])
        return results[0] if results else {}

    def _fetch_tsv_row(self, rhea_id: str) -> Dict[str, str]:
        params = {
            "query": f"RHEA:{rhea_id}",
            "columns": (
                "rhea-id,equation,ec,uniprot,pubmed,"
                "reaction-xref(KEGG),reaction-xref(MetaCyc)"
            ),
            "format": "tsv",
            "limit": 1,
        }
        resp = requests.get(RHEA_BASE_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        lines = [ln for ln in resp.text.split("\n") if ln.strip()]
        if len(lines) < 2:
            return {}
        headers = lines[0].split("\t")
        values = lines[1].split("\t")
        row = {}
        for i, header in enumerate(headers):
            row[header.strip()] = values[i].strip() if i < len(values) else ""
        return row

    # ------------------------------------------------------------------ #
    # Endpoints
    # ------------------------------------------------------------------ #
    def _get_reaction(
        self, arguments: Dict[str, Any], participants_only: bool
    ) -> Dict[str, Any]:
        raw_id = arguments.get("rhea_id", "")
        if raw_id in (None, ""):
            return {
                "status": "error",
                "error": "rhea_id parameter is required (e.g., '10280' or 'RHEA:10280').",
            }

        rhea_id = self._normalize_rhea_id(raw_id)
        if not rhea_id.isdigit():
            return {
                "status": "error",
                "error": (
                    f"Invalid Rhea id '{raw_id}'. Expected a numeric Rhea identifier "
                    "like 10280 or RHEA:10280."
                ),
            }

        json_row = self._fetch_json(rhea_id)
        if not json_row:
            return {
                "status": "error",
                "error": f"No Rhea reaction found for RHEA:{rhea_id}.",
            }

        participants = self._parse_participants(json_row.get("htmlequation", ""))

        if participants_only:
            data = {
                "rhea_id": f"RHEA:{rhea_id}",
                "equation": json_row.get("equation", ""),
                "reactants": participants["reactants"],
                "products": participants["products"],
                "n_reactants": len(participants["reactants"]),
                "n_products": len(participants["products"]),
            }
            return {
                "status": "success",
                "data": data,
                "metadata": {"source": "Rhea (SIB)", "rhea_id": f"RHEA:{rhea_id}"},
            }

        # Full record: merge JSON flags with TSV EC / PubMed / xref data.
        tsv = self._fetch_tsv_row(rhea_id)

        ec_numbers = self._split_multi(tsv.get("EC number", ""))
        pubmed_ids = self._split_multi(tsv.get("PubMed", ""))
        kegg = self._split_multi(tsv.get("Cross-reference (KEGG)", ""))
        metacyc = self._split_multi(tsv.get("Cross-reference (MetaCyc)", ""))

        enzyme_count_raw = tsv.get("Enzymes", "")
        try:
            enzyme_count = int(enzyme_count_raw) if enzyme_count_raw else 0
        except ValueError:
            enzyme_count = 0

        data = {
            "rhea_id": f"RHEA:{rhea_id}",
            "equation": json_row.get("equation", ""),
            "status_curation": json_row.get("status", ""),
            "balanced": bool(json_row.get("balanced", False)),
            "transport": bool(json_row.get("transport", False)),
            "comment": json_row.get("comment", "") or None,
            "reactants": participants["reactants"],
            "products": participants["products"],
            "ec_numbers": ec_numbers,
            "enzyme_count": enzyme_count,
            "pubmed_ids": pubmed_ids,
            "kegg_xrefs": kegg,
            "metacyc_xrefs": metacyc,
        }

        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "Rhea (SIB)",
                "rhea_id": f"RHEA:{rhea_id}",
                "url": f"https://www.rhea-db.org/rhea/{rhea_id}",
            },
        }
