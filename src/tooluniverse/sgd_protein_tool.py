# sgd_protein_tool.py
"""
SGD (Saccharomyces Genome Database) protein-feature & literature tool.

Complements the existing SGDTool (gene overview, phenotype, GO, interaction,
regulation, sequence, disease) by exposing three SGD locus sub-resources that
were previously unwrapped:

  * protein_domain_details      -> mapped protein domains (Pfam, InterPro,
                                   SMART, PROSITE, CDD, Gene3D, SUPERFAMILY,
                                   PANTHER, PRINTS) with residue coordinates.
  * posttranslational_details   -> curated post-translational modification
                                   sites (phosphorylation, ubiquitination,
                                   acetylation, ...) with residue + reference.
  * literature_details          -> categorized literature references
                                   (primary, review, interaction, phenotype,
                                   GO, disease, PTM, regulation, ...).

SGD webservice base: https://www.yeastgenome.org/backend
No authentication required. The {locus} path segment accepts an SGD ID
(e.g. S000001855), a systematic name (e.g. YFL039C), or a standard gene
name (e.g. ACT1) -- the backend resolves all three.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

SGD_BASE_URL = "https://www.yeastgenome.org/backend"

# SGD's backend rejects the default python-requests User-Agent on some paths;
# a browser-style UA is accepted consistently.
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
}

# Per-literature-category cap so a single ACT1 query (1000+ refs, ~1 MB)
# returns a bounded, useful payload instead of a megabyte dump.
_MAX_REFS_PER_CATEGORY = 25


@register_tool("SGDProteinTool")
class SGDProteinTool(BaseTool):
    """
    Query SGD protein-domain, post-translational-modification, and literature
    sub-resources for a budding-yeast (S. cerevisiae) gene/locus.

    Dispatch is driven by ``fields.endpoint`` in the tool config; the runtime
    argument is always a single ``locus`` string. No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint = tool_config.get("fields", {}).get("endpoint", "")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SGD sub-resource call. Never raises."""
        try:
            locus = (arguments or {}).get("locus", "")
            if isinstance(locus, str):
                locus = locus.strip()
            if not locus:
                return {
                    "status": "error",
                    "error": (
                        "locus parameter is required (gene name e.g. 'ACT1', "
                        "systematic name e.g. 'YFL039C', or SGD ID e.g. "
                        "'S000001855')"
                    ),
                }

            if self.endpoint == "protein_domain_details":
                return self._protein_domains(locus)
            if self.endpoint == "posttranslational_details":
                return self._ptm(locus)
            if self.endpoint == "literature_details":
                return self._literature(locus)
            return {
                "status": "error",
                "error": f"Unknown SGD endpoint configured: {self.endpoint!r}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SGD API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to SGD API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            code = getattr(getattr(e, "response", None), "status_code", "unknown")
            hint = " (locus not found)" if code == 404 else ""
            return {"status": "error", "error": f"SGD API HTTP error: {code}{hint}"}
        except ValueError:
            return {
                "status": "error",
                "error": "SGD API returned a non-JSON response",
            }
        except Exception as e:  # noqa: BLE001 - never propagate to caller
            return {"status": "error", "error": f"Unexpected error querying SGD: {e}"}

    # ----------------------------- helpers ------------------------------- #

    def _get(self, locus: str, sub: str):
        """Issue the GET and return parsed JSON (raises on HTTP/JSON error)."""
        url = f"{SGD_BASE_URL}/locus/{locus}/{sub}"
        resp = requests.get(url, headers=_HEADERS, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _locus_label(raw_list: List[dict]) -> Dict[str, Any]:
        """Pull the gene/systematic label from the first row that carries it."""
        for row in raw_list:
            loc = row.get("locus") or {}
            if loc:
                return {
                    "gene_name": loc.get("display_name"),
                    "systematic_name": loc.get("format_name"),
                    "sgd_link": loc.get("link"),
                }
        return {"gene_name": None, "systematic_name": None, "sgd_link": None}

    # ---------------------------- endpoints ------------------------------ #

    def _protein_domains(self, locus: str) -> Dict[str, Any]:
        raw = self._get(locus, "protein_domain_details")
        if not isinstance(raw, list):
            raw = []

        domains = []
        for row in raw:
            dom = row.get("domain") or {}
            src = row.get("source") or {}
            domains.append(
                {
                    "accession": dom.get("display_name"),
                    "description": (
                        None
                        if dom.get("description") in (None, "-")
                        else dom.get("description")
                    ),
                    "source": src.get("display_name"),
                    "start": row.get("start"),
                    "end": row.get("end"),
                    "domain_link": dom.get("link"),
                }
            )

        label = self._locus_label(raw)
        return {
            "status": "success",
            "data": {
                **label,
                "domain_count": len(domains),
                "domains": domains,
            },
            "metadata": {
                "source": "SGD",
                "query": locus,
                "endpoint": "locus/protein_domain_details",
            },
        }

    def _ptm(self, locus: str) -> Dict[str, Any]:
        raw = self._get(locus, "posttranslational_details")
        if not isinstance(raw, list):
            raw = []

        sites = []
        for row in raw:
            ref = row.get("reference") or {}
            sites.append(
                {
                    "modification": row.get("type"),
                    "residue": row.get("site_residue"),
                    "position": row.get("site_index"),
                    "reference": ref.get("display_name"),
                    "pubmed_id": ref.get("pubmed_id"),
                }
            )

        label = self._locus_label(raw)
        return {
            "status": "success",
            "data": {
                **label,
                "site_count": len(sites),
                "sites": sites,
            },
            "metadata": {
                "source": "SGD",
                "query": locus,
                "endpoint": "locus/posttranslational_details",
            },
        }

    def _literature(self, locus: str) -> Dict[str, Any]:
        raw = self._get(locus, "literature_details")
        if not isinstance(raw, dict):
            raw = {}

        counts: Dict[str, int] = {}
        references: Dict[str, List[dict]] = {}
        for category, refs in raw.items():
            if not isinstance(refs, list):
                continue
            counts[category] = len(refs)
            trimmed = []
            for ref in refs[:_MAX_REFS_PER_CATEGORY]:
                trimmed.append(
                    {
                        "citation": ref.get("citation") or ref.get("display_name"),
                        "pubmed_id": ref.get("pubmed_id"),
                        "year": ref.get("year"),
                        "reference_link": ref.get("link"),
                    }
                )
            references[category] = trimmed

        return {
            "status": "success",
            "data": {
                "query": locus,
                "total_references": sum(counts.values()),
                "counts_by_category": counts,
                "references": references,
                "truncated_per_category": _MAX_REFS_PER_CATEGORY,
            },
            "metadata": {
                "source": "SGD",
                "query": locus,
                "endpoint": "locus/literature_details",
            },
        }
