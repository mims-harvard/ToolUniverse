# quickgo_tool.py
"""
QuickGO (EBI Gene Ontology browser) REST API tool for ToolUniverse.

QuickGO provides fast access to Gene Ontology (GO) annotations and term
information. It offers annotation search by gene product or GO term,
ontology term details, and hierarchical relationships.

API: https://www.ebi.ac.uk/QuickGO/services/
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

QUICKGO_BASE_URL = "https://www.ebi.ac.uk/QuickGO/services"


@register_tool("QuickGOTool")
class QuickGOTool(BaseTool):
    """
    Tool for querying the EBI QuickGO Gene Ontology browser.

    QuickGO provides comprehensive GO annotation data with filtering
    by gene product, GO term, taxon, evidence code, and more. Also
    provides ontology term details and hierarchical relationships.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "annotation_gene")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the QuickGO API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"QuickGO API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to QuickGO API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"QuickGO API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying QuickGO: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate QuickGO endpoint."""
        if self.endpoint == "annotation_gene":
            return self._annotation_by_gene(arguments)
        elif self.endpoint == "annotation_goterm":
            return self._annotation_by_goterm(arguments)
        elif self.endpoint == "term_detail":
            return self._term_detail(arguments)
        elif self.endpoint == "term_children":
            return self._term_children(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    @staticmethod
    def _pagination_metadata(
        data: Dict[str, Any], requested_page: int, returned: int
    ) -> Dict[str, Any]:
        """Expose QuickGO's pageInfo instead of silently hiding later pages."""
        page_info = data.get("pageInfo") or {}
        current_page = int(page_info.get("current") or requested_page)
        total_pages = int(page_info.get("total") or 0)
        results_per_page = int(page_info.get("resultsPerPage") or returned)
        has_more = current_page < total_pages
        return {
            "page": current_page,
            "results_per_page": results_per_page,
            "total_pages": total_pages,
            "has_more": has_more,
            "next_page": current_page + 1 if has_more else None,
        }

    def _annotation_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search GO annotations for a specific gene product."""
        gene_product_id = arguments.get("gene_product_id", "")
        if not gene_product_id:
            return {"status": "error", "error": "gene_product_id parameter is required"}

        # Feature-25B-05: detect bare gene symbols (e.g. "TP53") and explain the correct format.
        # QuickGO requires "DB:Accession" format such as "UniProtKB:P04637".
        if ":" not in gene_product_id:
            return {
                "status": "error",
                "error": (
                    f"Invalid gene_product_id format: '{gene_product_id}'. "
                    "QuickGO requires accession format 'DB:Accession', "
                    "e.g. 'UniProtKB:P04637' for human TP53. "
                    "Use `tu run UniProt_search query=TP53` to find the UniProt accession "
                    "for your gene."
                ),
            }

        url = f"{QUICKGO_BASE_URL}/annotation/search"
        page = max(1, int(arguments.get("page") or 1))
        limit = min(max(1, int(arguments.get("limit") or 25)), 100)
        params = {
            "geneProductId": gene_product_id,
            "limit": limit,
            "page": page,
        }

        # Optional filters
        aspect = arguments.get("aspect")
        if aspect:
            params["aspect"] = aspect

        taxon_id = arguments.get("taxon_id")
        if taxon_id:
            params["taxonId"] = taxon_id

        evidence_code = arguments.get("evidence_code")
        if evidence_code:
            params["evidenceCode"] = evidence_code

        headers = {"Accept": "application/json"}
        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        annotations = []
        for r in data.get("results", []):
            annotations.append(
                {
                    "go_id": r.get("goId"),
                    "go_name": r.get("goName"),
                    "go_aspect": r.get("goAspect"),
                    "gene_product_id": r.get("geneProductId"),
                    "symbol": r.get("symbol"),
                    "qualifier": r.get("qualifier"),
                    "go_evidence": r.get("goEvidence"),
                    "evidence_code": r.get("evidenceCode"),
                    "assigned_by": r.get("assignedBy"),
                    "reference": r.get("reference"),
                    "annotation_id": r.get("id"),
                    "date": r.get("date"),
                    "with_from": r.get("withFrom") or [],
                    "taxon_id": r.get("taxonId"),
                    "gene_product_type": r.get("geneProductType"),
                    "target_sets": r.get("targetSets") or [],
                }
            )

        # Feature-25B-04: the annotation endpoint returns goName=null for many records.
        # Batch-resolve the missing names from the GO terms endpoint.
        null_ids = list(
            {a["go_id"] for a in annotations if a["go_id"] and a["go_name"] is None}
        )
        if null_ids:
            try:
                ids_str = ",".join(null_ids)
                term_resp = requests.get(
                    f"{QUICKGO_BASE_URL}/ontology/go/terms/{ids_str}",
                    headers={"Accept": "application/json"},
                    timeout=self.timeout,
                )
                if term_resp.ok:
                    # The backfill fetches the whole term record to recover a
                    # name. What it also holds -- the definition, the aspect,
                    # whether the term is obsolete -- was discarded, so an
                    # annotation to GO:0005515 came back as "protein binding"
                    # with no statement of what that means. The record is
                    # already paid for.
                    id_to_term = {
                        t["id"]: t
                        for t in term_resp.json().get("results", [])
                        if isinstance(t, dict) and "id" in t
                    }
                    for a in annotations:
                        term = id_to_term.get(a["go_id"]) or {}
                        if a["go_name"] is None and term.get("name"):
                            a["go_name"] = term["name"]
                        if term:
                            definition = term.get("definition")
                            a["go_definition"] = (
                                definition.get("text")
                                if isinstance(definition, dict)
                                else definition
                            )
                            a["go_is_obsolete"] = term.get("isObsolete", False)
                            a["go_aspect"] = a.get("go_aspect") or term.get("aspect")
                            a["go_child_count"] = len(term.get("children") or [])
                            a["go_synonym_count"] = len(term.get("synonyms") or [])
            except Exception:
                pass  # Best-effort; don't fail if name resolution fails

        return {
            "status": "success",
            "data": annotations,
            "metadata": {
                "source": "QuickGO",
                "query": gene_product_id,
                "total_annotations": data.get("numberOfHits", len(annotations)),
                "page_size": len(annotations),
                **self._pagination_metadata(data, page, len(annotations)),
            },
        }

    def _annotation_by_goterm(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search GO annotations for a specific GO term."""
        go_id = arguments.get("go_id", "")
        if not go_id:
            return {"status": "error", "error": "go_id parameter is required"}

        url = f"{QUICKGO_BASE_URL}/annotation/search"
        page = max(1, int(arguments.get("page") or 1))
        limit = min(max(1, int(arguments.get("limit") or 25)), 100)
        params = {
            "goId": go_id,
            "limit": limit,
            "page": page,
        }

        # Optional filters
        taxon_id = arguments.get("taxon_id")
        if taxon_id:
            params["taxonId"] = taxon_id

        evidence_code = arguments.get("evidence_code")
        if evidence_code:
            params["evidenceCode"] = evidence_code

        headers = {"Accept": "application/json"}
        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        annotations = []
        for r in data.get("results", []):
            annotations.append(
                {
                    "gene_product_id": r.get("geneProductId"),
                    "symbol": r.get("symbol"),
                    "go_id": r.get("goId"),
                    "go_name": r.get("goName"),
                    "go_aspect": r.get("goAspect"),
                    "qualifier": r.get("qualifier"),
                    "go_evidence": r.get("goEvidence"),
                    "evidence_code": r.get("evidenceCode"),
                    "taxon_id": r.get("taxonId"),
                    "assigned_by": r.get("assignedBy"),
                    # The paper. `assigned_by` is the database that made the
                    # annotation; `reference` is what it cites, and the
                    # by-gene direction of this same tool already reports it.
                    "reference": r.get("reference"),
                    "annotation_id": r.get("id"),
                    "date": r.get("date"),
                    # What an IEA or an IC was inferred FROM, which is the
                    # difference between a computed annotation a reader can
                    # check and one they cannot.
                    "with_from": r.get("withFrom") or [],
                    "interacting_taxon_id": r.get("interactingTaxonId"),
                    "gene_product_type": r.get("geneProductType"),
                }
            )

        return {
            "status": "success",
            "data": annotations,
            "metadata": {
                "source": "QuickGO",
                "query_go_id": go_id,
                "total_annotations": data.get("numberOfHits", len(annotations)),
                "page_size": len(annotations),
                **self._pagination_metadata(data, page, len(annotations)),
            },
        }

    def _term_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a GO term."""
        go_id = arguments.get("go_id", "")
        if not go_id:
            return {"status": "error", "error": "go_id parameter is required"}

        url = f"{QUICKGO_BASE_URL}/ontology/go/terms/{go_id}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "source": "QuickGO",
                    "query": go_id,
                    "found": False,
                },
            }

        term = results[0]
        definition = term.get("definition", {})

        # Extract synonyms
        synonyms = []
        for syn in term.get("synonyms", []):
            if isinstance(syn, dict):
                synonyms.append(
                    {
                        "name": syn.get("name"),
                        "type": syn.get("type"),
                    }
                )
            elif isinstance(syn, str):
                synonyms.append({"name": syn, "type": "unknown"})

        # Extract cross-references
        xrefs = []
        for xref in term.get("xRefs", []) or []:
            if isinstance(xref, dict):
                xrefs.append(
                    {
                        "db_code": xref.get("dbCode"),
                        "db_id": xref.get("dbId"),
                    }
                )

        result = {
            "id": term.get("id"),
            "name": term.get("name"),
            "definition": definition.get("text")
            if isinstance(definition, dict)
            else definition,
            "aspect": term.get("aspect"),
            "is_obsolete": term.get("isObsolete", False),
            "synonyms": synonyms,
            "xrefs": xrefs,
            "usage": term.get("usage"),
            "num_children": len(term.get("children", [])),
            # The children themselves, with the relation to each. A term
            # detail that reports only how many children there are cannot be
            # walked, and `is_a` against `part_of` is the whole meaning of
            # the edge.
            "children": [
                {
                    "id": child.get("id"),
                    "name": child.get("name"),
                    "relation": child.get("relation"),
                }
                for child in (term.get("children") or [])
                if isinstance(child, dict)
            ],
            "comment": term.get("comment"),
            "subsets": term.get("subsets") or [],
            "replaced_by": term.get("replacedBy"),
            "considers": term.get("considers") or [],
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "QuickGO",
                "query": go_id,
                "found": True,
            },
        }

    def _term_children(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get child terms of a GO term."""
        go_id = arguments.get("go_id", "")
        if not go_id:
            return {"status": "error", "error": "go_id parameter is required"}

        url = f"{QUICKGO_BASE_URL}/ontology/go/terms/{go_id}/children"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        children = []
        if results:
            for child in results[0].get("children", []):
                children.append(
                    {
                        "id": child.get("id"),
                        "name": child.get("name"),
                        "relation": child.get("relation"),
                        "has_children": child.get("hasChildren", False),
                    }
                )

        return {
            "status": "success",
            "data": children,
            "metadata": {
                "source": "QuickGO",
                "parent_go_id": go_id,
                "num_children": len(children),
            },
        }
