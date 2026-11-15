# go_api_tool.py
"""
Gene Ontology (GO) REST API tool for ToolUniverse.

The Gene Ontology provides a standardized framework for describing gene
and gene product attributes across species. The GO API provides programmatic
access to ontology terms, gene annotations, and functional associations.

API: https://api.geneontology.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

GO_BASE_URL = "https://api.geneontology.org/api"


def _evidence(association: Dict[str, Any]) -> Dict[str, Any]:
    """The evidence code of a GO annotation.

    The API sends it as ``evidence`` with the labelled codes under
    ``evidence_types``. There is no ``evidence_type`` or ``evidence_label``
    key, so reading those returned None for every annotation ever served.
    """
    types = [t for t in (association.get("evidence_types") or []) if isinstance(t, dict)]
    codes = [t.get("id") for t in types if t.get("id")]
    code = association.get("evidence") or (codes[0] if codes else None)
    labels = [t.get("label") for t in types if t.get("label")]
    return {
        "evidence_type": code,
        "evidence_label": labels[0] if labels else None,
        "evidence_codes": codes,
        "evidence_labels": labels,
    }


def _references(association: Dict[str, Any]) -> list:
    """``publications`` holds the references; there is no ``reference`` key."""
    out = []
    for publication in association.get("publications") or []:
        if isinstance(publication, dict):
            identifier = publication.get("id")
            if identifier:
                out.append(identifier)
        elif publication:
            out.append(str(publication))
    return out


def _categories(entity: Dict[str, Any]) -> list:
    """GO sends ``category: [null]`` on most entities; drop the nulls."""
    return [c for c in (entity.get("category") or []) if c]


def _is_negated(association: Dict[str, Any]) -> bool:
    """A NOT annotation: the gene is curated as *not* having the function."""
    if association.get("negated"):
        return True
    qualifiers = association.get("qualifier") or association.get("qualifiers") or []
    if isinstance(qualifiers, str):
        qualifiers = [qualifiers]
    return any(str(q).lower() == "not" for q in qualifiers)


def _association_page_arguments(
    arguments: Dict[str, Any],
) -> tuple[int | None, int | None, str | None]:
    """Validate GO association paging without silently clamping values."""
    raw_rows = arguments.get("rows")
    raw_start = arguments.get("start")
    raw_rows = 20 if raw_rows is None else raw_rows
    raw_start = 0 if raw_start is None else raw_start
    try:
        if isinstance(raw_rows, bool) or isinstance(raw_start, bool):
            raise ValueError
        rows = int(raw_rows)
        start = int(raw_start)
        if isinstance(raw_rows, float) and not raw_rows.is_integer():
            raise ValueError
        if isinstance(raw_start, float) and not raw_start.is_integer():
            raise ValueError
        if not 1 <= rows <= 1000 or start < 0:
            raise ValueError
    except (TypeError, ValueError):
        return None, None, "rows must be 1-1000 and start must be non-negative"
    return rows, start, None


def _association_metadata(
    *, start: int, rows: int, upstream_count: int, returned: int
) -> Dict[str, Any]:
    """Build exact next-page metadata despite GO API omitting a total count."""
    has_more = upstream_count > rows
    end_reached = not has_more
    return {
        "total_results": start + returned if end_reached else None,
        "total_results_exact": end_reached,
        "matching_associations_lower_bound": start + returned + (1 if has_more else 0),
        "returned": returned,
        "rows": rows,
        "start": start,
        "has_more": has_more,
        "truncated": has_more,
        "next_start": start + returned if has_more else None,
    }


def _unique_gene_page_arguments(
    arguments: Dict[str, Any],
) -> tuple[int | None, int | None, int | None, str | None]:
    raw_rows = arguments.get("rows")
    raw_offset = arguments.get("offset")
    rows = 20 if raw_rows is None else raw_rows
    offset = 0 if raw_offset is None else raw_offset
    try:
        if isinstance(rows, bool) or isinstance(offset, bool):
            raise ValueError
        rows = int(rows)
        offset = int(offset)
        if isinstance(raw_rows, float) and not raw_rows.is_integer():
            raise ValueError
        if isinstance(raw_offset, float) and not raw_offset.is_integer():
            raise ValueError
        if not 1 <= rows <= 1000 or offset < 0:
            raise ValueError
    except (TypeError, ValueError):
        return None, None, None, "rows must be 1-1000 and offset must be non-negative"

    raw_budget = arguments.get("max_associations_scanned")
    default_budget = min(max((offset + rows + 1) * 20, 1000), 200_000)
    budget = default_budget if raw_budget is None else raw_budget
    try:
        if isinstance(budget, bool):
            raise ValueError
        budget = int(budget)
        if isinstance(raw_budget, float) and not raw_budget.is_integer():
            raise ValueError
        if not 1 <= budget <= 200_000:
            raise ValueError
    except (TypeError, ValueError):
        return (
            None,
            None,
            None,
            "max_associations_scanned must be an integer from 1 to 200000",
        )
    return rows, offset, budget, None


@register_tool("GOAPITool")
class GOAPITool(BaseTool):
    """
    Tool for querying the Gene Ontology (GO) REST API.

    The GO API provides access to three major ontology domains:
    - Biological Process (BP): cellular/organismal processes
    - Molecular Function (MF): molecular-level activities
    - Cellular Component (CC): locations of gene products

    Supports: GO term lookup, gene GO annotations, gene function associations.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "term")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GO API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GO API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to GO API"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"GO API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying GO API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate GO endpoint."""
        if self.endpoint == "term":
            return self._get_term(arguments)
        elif self.endpoint == "gene_functions":
            return self._get_gene_functions(arguments)
        elif self.endpoint == "search_annotations":
            return self._search_annotations(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_term(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get GO term details by GO ID."""
        go_id = arguments.get("go_id", "")
        if not go_id:
            return {
                "status": "error",
                "error": "go_id parameter is required (e.g., GO:0006915)",
            }

        # Normalize GO ID
        if not go_id.startswith("GO:"):
            go_id = f"GO:{go_id}"

        url = f"{GO_BASE_URL}/ontology/term/{go_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Clean up synonyms (they have @ artifacts)
        synonyms = [s.strip("@").strip() for s in data.get("synonyms", [])]
        related_synonyms = [
            s.strip("@").strip() for s in data.get("relatedSynonyms", [])
        ]

        return {
            "status": "success",
            "data": {
                "go_id": data.get("goid"),
                "label": data.get("label"),
                "definition": data.get("definition"),
                "synonyms": synonyms,
                "related_synonyms": related_synonyms,
                "xrefs": [x.strip("@").strip() for x in data.get("xrefs", [])],
                "alternative_ids": [
                    a.strip("@").strip() for a in data.get("alternativeIds", [])
                ],
            },
            "metadata": {
                "source": "Gene Ontology (GO)",
            },
        }

    def _get_gene_functions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get GO annotations (functions/processes/components) for a gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., HGNC:11998 or UniProtKB:P04637)",
            }

        rows, start, pagination_error = _association_page_arguments(arguments)
        if pagination_error:
            return {"status": "error", "error": pagination_error}
        assert rows is not None and start is not None
        aspect = arguments.get("aspect")  # P=process, F=function, C=component

        url = f"{GO_BASE_URL}/bioentity/gene/{gene_id}/function"
        # Request one look-ahead association because this API omits numFound.
        params = {"rows": rows + 1, "start": start}
        if aspect:
            params["fq"] = f'aspect:"{aspect}"'

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        raw_associations = data.get("associations", []) or []
        associations = []
        negated_count = 0
        for a in raw_associations[:rows]:
            obj = a.get("object", {})
            categories = _categories(obj)
            negated = _is_negated(a)
            negated_count += bool(negated)

            associations.append(
                {
                    "go_id": obj.get("id"),
                    "go_label": obj.get("label"),
                    "category": categories[0] if categories else None,
                    "categories": categories,
                    # True when the gene is annotated as NOT having this term.
                    "negated": negated,
                    **_evidence(a),
                    "provided_by": a.get("provided_by", []),
                    "references": _references(a),
                }
            )

        pagination = _association_metadata(
            start=start,
            rows=rows,
            upstream_count=len(raw_associations),
            returned=len(associations),
        )
        pagination.update(
            {
                "source": "Gene Ontology (GO)",
                "gene_id": gene_id,
                "negated_annotations": negated_count,
            }
        )
        if negated_count:
            pagination["negated_note"] = (
                f"{negated_count} of the returned annotations are NOT "
                "annotations (negated true): the gene is curated as not "
                "having that term."
            )
        return {
            "status": "success",
            "data": associations,
            "metadata": pagination,
        }

    def _search_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search unique genes annotated with a specific GO term.

        The upstream ``/genes`` route actually returns association rows, so a
        gene can occur repeatedly for descendant GO terms or data providers.
        Scan and aggregate those rows locally before applying the public offset.
        """
        go_id = arguments.get("go_id", "")
        if not go_id:
            return {
                "status": "error",
                "error": "go_id parameter is required (e.g., GO:0006915)",
            }

        if not go_id.startswith("GO:"):
            go_id = f"GO:{go_id}"

        rows, offset, scan_budget, pagination_error = _unique_gene_page_arguments(
            arguments
        )
        if pagination_error:
            return {"status": "error", "error": pagination_error}
        assert rows is not None and offset is not None and scan_budget is not None
        taxon = arguments.get("taxon")  # e.g., NCBITaxon:9606

        url = f"{GO_BASE_URL}/bioentity/function/{go_id}/genes"
        target_unique_count = offset + rows + 1
        genes_by_id: Dict[str, Dict[str, Any]] = {}
        gene_order = []
        # NOT annotations, held aside: they must not make a gene count as
        # having the function, but a gene that is also annotated positively
        # should carry them so the conflict is visible.
        negated_by_gene: Dict[str, list] = {}
        negated_scanned = 0
        association_start = 0
        associations_scanned = 0
        upstream_exhausted = False

        while (
            len(gene_order) < target_unique_count and associations_scanned < scan_budget
        ):
            request_rows = min(1000, scan_budget - associations_scanned)
            params = {"rows": request_rows, "start": association_start}
            if taxon:
                params["taxon"] = taxon

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            raw_associations = data.get("associations", []) or []

            for association in raw_associations:
                subject = association.get("subject", {}) or {}
                gene_id = subject.get("id")
                if not gene_id:
                    continue
                obj = association.get("object", {}) or {}
                row = {
                    "go_id": obj.get("id"),
                    "go_label": obj.get("label"),
                    "category": _categories(obj),
                    **_evidence(association),
                    "provided_by": association.get("provided_by", []),
                    "references": _references(association),
                }
                if _is_negated(association):
                    negated_scanned += 1
                    row["negated"] = True
                    negated_by_gene.setdefault(gene_id, []).append(row)
                    continue

                if gene_id not in genes_by_id:
                    taxon_info = subject.get("taxon", {}) or {}
                    genes_by_id[gene_id] = {
                        "gene_id": gene_id,
                        "gene_label": subject.get("label"),
                        "taxon_id": taxon_info.get("id"),
                        "taxon_label": taxon_info.get("label"),
                        "associations_returned": 0,
                        "associations": [],
                    }
                    gene_order.append(gene_id)

                genes_by_id[gene_id]["associations_returned"] += 1
                genes_by_id[gene_id]["associations"].append(row)

            association_start += len(raw_associations)
            associations_scanned += len(raw_associations)
            if len(raw_associations) < request_rows:
                upstream_exhausted = True
                break

        page_ids = gene_order[offset : offset + rows]
        genes = [genes_by_id[gene_id] for gene_id in page_ids]
        for gene in genes:
            negated = negated_by_gene.get(gene["gene_id"])
            if negated:
                gene["negated_associations"] = negated
        genes_excluded_as_negated_only = sum(
            1 for gene_id in negated_by_gene if gene_id not in genes_by_id
        )
        extra_unique_seen = len(gene_order) > offset + rows
        has_more = extra_unique_seen or not upstream_exhausted
        has_more_known = extra_unique_seen or upstream_exhausted
        scan_limit_reached = bool(
            not has_more_known and associations_scanned >= scan_budget
        )
        page_complete = len(genes) == rows or upstream_exhausted
        warning = None
        if scan_limit_reached:
            warning = (
                "The association scan budget ended before unique-gene pagination "
                "could be completed. Increase max_associations_scanned and rerun "
                "the same offset."
            )
        for gene in genes:
            # A later association page can mention the same gene again. Only an
            # exhausted upstream scan proves that the nested association list is
            # complete; otherwise label it conservatively.
            gene["associations_complete"] = upstream_exhausted

        pagination = {
            "source": "Gene Ontology (GO)",
            "go_id": go_id,
            "row_semantics": "unique_genes_with_aggregated_associations",
            "total_unique_genes": len(gene_order) if upstream_exhausted else None,
            "total_unique_genes_exact": upstream_exhausted,
            "unique_genes_lower_bound": len(gene_order),
            "returned": len(genes),
            "rows": rows,
            "offset": offset,
            "has_more": has_more,
            "has_more_known": has_more_known,
            "truncated": has_more,
            "next_offset": offset + len(genes) if has_more and genes else None,
            "page_complete": page_complete,
            "associations_scanned": associations_scanned,
            "max_associations_scanned": scan_budget,
            "scan_limit_reached": scan_limit_reached,
            "warning": warning,
            # NOT annotations are excluded from the gene list: a gene curated
            # as not having the function is not a gene with the function.
            "negated_associations_scanned": negated_scanned,
            "genes_excluded_as_negated_only": genes_excluded_as_negated_only,
        }
        if negated_scanned:
            pagination["negated_note"] = (
                f"{negated_scanned} scanned annotations are NOT annotations. "
                "They never put a gene in this list; where a listed gene also "
                "has one it is under negated_associations."
            )
        return {
            "status": "success",
            "data": genes,
            "metadata": pagination,
        }
