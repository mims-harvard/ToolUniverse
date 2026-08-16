# oma_tool.py
"""
OMA (Orthologous MAtrix) Browser API tool for ToolUniverse.

OMA is a comprehensive database of orthologs among complete genomes.
It provides orthology predictions using a rigorous algorithm applied to
2,600+ genomes. OMA offers protein lookup, pairwise orthologs,
Hierarchical Orthologous Groups (HOGs), and OMA Groups.

API: https://omabrowser.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

OMA_BASE_URL = "https://omabrowser.org/api"


def _page_size(value: Any, default: int, maximum: Any = 100) -> int:
    """Normalize a caller-supplied page size.

    Every paging parameter in oma_tools.json is declared ``["integer", "null"]``,
    and the call sites went on to compare the value against a bound, so ``null``
    raised ``TypeError: '<' not supported between instances of 'int' and
    'NoneType'``, reported as an opaque "Unexpected error querying OMA".

    That was never reachable through ``run_one_function``: execute_function.py
    strips ``None`` arguments before dispatch on the grounds that "None means not
    provided". This helper is therefore hardening for the paths that do not go
    through it -- importing the class directly, as this repo's own unit tests do
    -- and not a fix for something users were hitting. It is kept because a tool
    that accepts its own declared argument only via one entry point is a trap for
    the next caller, and because "absent" and "null" genuinely mean the same
    thing here. The user-visible defect in this module was `per_page` being
    declared and then ignored; see ``_get_orthologs``.
    """
    if value is None:
        return default
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    value = max(1, value)
    return value if maximum is None else min(value, maximum)


@register_tool("OMATool")
class OMATool(BaseTool):
    """
    Tool for querying the OMA Orthology Browser.

    OMA provides orthology relationships among 2,600+ complete genomes
    using a highly reliable algorithm. Supports protein lookup, pairwise
    orthologs, Hierarchical Orthologous Groups (HOGs), and OMA Groups.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "protein")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OMA API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"OMA API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to OMA API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"OMA API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying OMA: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate OMA endpoint."""
        if self.endpoint == "protein":
            return self._get_protein(arguments)
        elif self.endpoint == "orthologs":
            return self._get_orthologs(arguments)
        elif self.endpoint == "hog":
            return self._get_hog(arguments)
        elif self.endpoint == "group":
            return self._get_group(arguments)
        elif self.endpoint == "xref":
            return self._resolve_xref(arguments)
        elif self.endpoint == "genome_pairs":
            return self._get_genome_pair_orthologs(arguments)
        elif self.endpoint == "protein_ontology":
            return self._get_protein_go(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein information by UniProt accession or OMA ID."""
        protein_id = arguments.get("protein_id", "")
        if not protein_id:
            return {
                "status": "error",
                "error": "protein_id parameter is required (UniProt accession e.g. P04637, or OMA ID e.g. HUMAN31534)",
            }

        url = f"{OMA_BASE_URL}/protein/{protein_id}/"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        species = data.get("species", {})
        locus = data.get("locus", {})

        result = {
            "entry_nr": data.get("entry_nr"),
            "oma_id": data.get("omaid"),
            "canonical_id": data.get("canonicalid"),
            "sequence_length": data.get("sequence_length"),
            "species_code": species.get("code"),
            "species_name": species.get("species"),
            "taxon_id": species.get("taxon_id"),
            "oma_group": data.get("oma_group"),
            "oma_hog_id": data.get("oma_hog_id"),
            "chromosome": data.get("chromosome"),
            "locus_start": locus.get("start"),
            "locus_end": locus.get("end"),
            "locus_strand": locus.get("strand"),
            "is_main_isoform": data.get("is_main_isoform"),
            "roothog_id": data.get("roothog_id"),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "OMA Browser",
                "query": protein_id,
            },
        }

    def _get_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get pairwise orthologs for a protein."""
        protein_id = arguments.get("protein_id", "")
        if not protein_id:
            return {
                "status": "error",
                "error": "protein_id parameter is required (UniProt accession e.g. P04637)",
            }

        rel_type = arguments.get("rel_type")
        # No `maximum`: /protein/{id}/orthologs/ has no server-side paging, so the
        # full set is already in hand and any cap here would make the tail of it
        # unreachable rather than merely unrequested.
        per_page = _page_size(arguments.get("per_page"), 20, maximum=None)

        url = f"{OMA_BASE_URL}/protein/{protein_id}/orthologs/"
        # `per_page` is deliberately not forwarded. This endpoint accepts it,
        # returns HTTP 200, and ignores it: measured against P04637, per_page=3,
        # 20 and 100 each returned all 157 orthologs, and the response carries no
        # Link, X-Total-Count or content-range header to page with. Sending it
        # only implied a limit that was never applied, so the limit is applied here.
        params = {}
        if rel_type:
            params["rel_type"] = rel_type

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        for orth in data:
            species = orth.get("species", {})
            results.append(
                {
                    "oma_id": orth.get("omaid"),
                    "canonical_id": orth.get("canonicalid"),
                    "species_name": species.get("species"),
                    "species_code": species.get("code"),
                    "taxon_id": species.get("taxon_id"),
                    "rel_type": orth.get("rel_type"),
                    "distance": orth.get("distance"),
                    "score": orth.get("score"),
                    "sequence_length": orth.get("sequence_length"),
                    "chromosome": orth.get("chromosome"),
                }
            )

        total_count = len(results)
        results = results[:per_page]
        truncated = len(results) < total_count

        metadata = {
            "source": "OMA Browser",
            "query": protein_id,
            # `count` / `total_count` / `truncated` are the disclosure vocabulary
            # this repo settled on; `total_orthologs` is gone rather than kept as
            # a synonym for `total_count`, because it used to mean "rows returned"
            # (the two coincided only while nothing was ever sliced) and a key
            # that silently changes meaning is worse than a key that is absent.
            "count": len(results),
            "total_count": total_count,
            "truncated": truncated,
        }
        if truncated:
            metadata["truncation_note"] = (
                f"Showing {len(results)} of {total_count} orthologs. OMA returns "
                f"the complete set in one response and does not paginate this "
                f"endpoint, so raise 'per_page' (e.g. per_page={total_count}) to "
                f"see the rest; there is no next page to fetch."
            )

        return {
            "status": "success",
            "data": results,
            "metadata": metadata,
        }

    def _get_hog(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get Hierarchical Orthologous Group (HOG) information."""
        hog_id = arguments.get("hog_id", "")
        if not hog_id:
            return {
                "status": "error",
                "error": "hog_id parameter is required (e.g. HOG:F0782425)",
            }

        url = f"{OMA_BASE_URL}/hog/{hog_id}/"
        response = requests.get(url, timeout=self.timeout)
        # OMA reassigns HOG IDs between releases; a retired ID returns HTTP 410.
        # Surface an actionable message instead of a bare "HTTP error: 410".
        if response.status_code == 410:
            return {
                "status": "error",
                "error": (
                    f"HOG ID '{hog_id}' is no longer valid -- OMA reassigns HOG IDs "
                    "between releases (the current scheme uses an 'F' prefix, e.g. "
                    "HOG:F0782425). Look up the protein with OMA_get_protein and use "
                    "the 'oma_hog_id' field to get the current HOG ID."
                ),
            }
        response.raise_for_status()
        data = response.json()

        results = []
        for hog in data:
            children = []
            for child in hog.get("children_hogs", []):
                children.append(
                    {
                        "hog_id": child.get("hog_id"),
                        "alternative_levels": child.get("alternative_levels", [])[:5],
                    }
                )

            results.append(
                {
                    "hog_id": hog.get("hog_id"),
                    "level": hog.get("level"),
                    "roothog_id": hog.get("roothog_id"),
                    "completeness_score": hog.get("completeness_score"),
                    "description": hog.get("description"),
                    "parent_hogs": hog.get("parent_hogs", []),
                    "children_hogs": children[:10],
                    "alternative_levels": hog.get("alternative_levels", [])[:10],
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "OMA Browser",
                "query": hog_id,
                "total_entries": len(results),
            },
        }

    def _get_group(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get OMA Group details (strict 1:1 orthologs across all genomes)."""
        group_id = arguments.get("group_id", "")
        if not group_id:
            return {
                "status": "error",
                "error": "group_id parameter is required (numeric group ID, e.g. 1388790)",
            }

        url = f"{OMA_BASE_URL}/group/{group_id}/"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        members = []
        for m in data.get("members", [])[:30]:  # Limit members
            species = m.get("species", {})
            members.append(
                {
                    "oma_id": m.get("omaid"),
                    "canonical_id": m.get("canonicalid"),
                    "species_name": species.get("species"),
                    "species_code": species.get("code"),
                    "taxon_id": species.get("taxon_id"),
                    "sequence_length": m.get("sequence_length"),
                    "chromosome": m.get("chromosome"),
                }
            )

        result = {
            "group_nr": data.get("group_nr"),
            "fingerprint": data.get("fingerprint"),
            "description": data.get("description"),
            "members": members,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "OMA Browser",
                "query": str(group_id),
                "total_members": len(data.get("members", [])),
                "returned_members": len(members),
            },
        }

    def _resolve_xref(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a gene name / symbol / cross-reference to OMA entries."""
        search = arguments.get("search", "")
        if not search:
            return {
                "status": "error",
                "error": (
                    "search parameter is required (gene symbol e.g. 'BRCA2', "
                    "UniProt name e.g. 'MED4_HUMAN', or any cross-reference identifier)"
                ),
            }

        limit = _page_size(arguments.get("limit"), 25)

        url = f"{OMA_BASE_URL}/xref/"
        response = requests.get(url, params={"search": search}, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        # /xref/?search= returns a flat list of cross-reference matches.
        for x in data[:limit] if isinstance(data, list) else []:
            genome = x.get("genome") or {}
            results.append(
                {
                    "xref": x.get("xref"),
                    "source": x.get("source"),
                    "seq_match": x.get("seq_match"),
                    "entry_nr": x.get("entry_nr"),
                    "oma_id": x.get("omaid"),
                    "species_code": genome.get("code"),
                    "species_name": genome.get("species"),
                    "taxon_id": genome.get("taxon_id"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "OMA Browser",
                "query": search,
                "total_matches": len(data) if isinstance(data, list) else 0,
                "returned_matches": len(results),
            },
        }

    def _get_genome_pair_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all pairwise orthologs between two whole genomes."""
        genome1 = arguments.get("genome1", "")
        genome2 = arguments.get("genome2", "")
        if not genome1 or not genome2:
            return {
                "status": "error",
                "error": (
                    "genome1 and genome2 parameters are required (UniProt species "
                    "codes or NCBI taxon IDs, e.g. genome1='HUMAN', genome2='MOUSE')"
                ),
            }

        # Unlike /protein/{id}/orthologs/, this endpoint does honour per_page
        # (measured: per_page=3 returned 3 rows, per_page=20 returned 20, each
        # with a Link header), so the value is still forwarded upstream.
        per_page = _page_size(arguments.get("per_page"), 20)
        page = arguments.get("page")

        url = f"{OMA_BASE_URL}/pairs/{genome1}/{genome2}/"
        params = {"per_page": per_page}
        if page:
            params["page"] = page

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        def _entry_summary(entry):
            entry = entry or {}
            species = entry.get("species") or {}
            return {
                "entry_nr": entry.get("entry_nr"),
                "oma_id": entry.get("omaid"),
                "canonical_id": entry.get("canonicalid"),
                "species_code": species.get("code"),
                "species_name": species.get("species"),
                "taxon_id": species.get("taxon_id"),
                "oma_group": entry.get("oma_group"),
                "oma_hog_id": entry.get("oma_hog_id"),
                "chromosome": entry.get("chromosome"),
            }

        results = []
        for pair in data if isinstance(data, list) else []:
            results.append(
                {
                    "entry_1": _entry_summary(pair.get("entry_1")),
                    "entry_2": _entry_summary(pair.get("entry_2")),
                    "rel_type": pair.get("rel_type"),
                    "distance": pair.get("distance"),
                    "score": pair.get("score"),
                    "oma_group": pair.get("oma_group"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "OMA Browser",
                "genome1": genome1,
                "genome2": genome2,
                "returned_pairs": len(results),
            },
        }

    def _get_protein_go(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get GO functional annotations for a specific OMA protein."""
        protein_id = arguments.get("protein_id", "")
        if not protein_id:
            return {
                "status": "error",
                "error": (
                    "protein_id parameter is required (OMA ID e.g. 'HUMAN17018' "
                    "or UniProt accession e.g. 'P04637')"
                ),
            }

        aspect_filter = arguments.get("aspect")

        url = f"{OMA_BASE_URL}/protein/{protein_id}/ontology/"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = []
        for go in data if isinstance(data, list) else []:
            if aspect_filter and go.get("aspect") != aspect_filter:
                continue
            results.append(
                {
                    "go_term": go.get("GO_term"),
                    "name": go.get("name"),
                    "aspect": go.get("aspect"),
                    "information_content": go.get("ic"),
                    "evidence": go.get("evidence"),
                    "reference": go.get("reference"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "OMA Browser",
                "query": protein_id,
                "total_annotations": len(results),
            },
        }
