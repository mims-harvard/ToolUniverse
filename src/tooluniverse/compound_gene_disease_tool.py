"""Compound tool: gather gene-disease associations from multiple databases in one call.

Queries DisGeNET, OMIM, OpenTargets, GenCC, and ClinVar for a given gene or disease,
cross-references results, and returns a unified comparison table with concordance scores.
"""

from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("CompoundGeneDiseaseAssociationTool")
class CompoundGeneDiseaseAssociationTool(BaseTool):
    """Query multiple gene-disease databases in a single call."""

    SOURCES = ["DisGeNET", "OMIM", "OpenTargets", "GenCC", "ClinVar"]

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene = arguments.get("gene") or arguments.get("gene_symbol")
        disease = arguments.get("disease")
        if not gene and not disease:
            return {
                "status": "error",
                "error": "At least one of 'gene' or 'disease' is required.",
            }

        from .execute_function import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        results_by_source: Dict[str, Any] = {}
        sources_failed: List[str] = []

        def _try_tool(source_name, tool_name, args):
            """Call a tool and handle errors gracefully."""
            try:
                r = tu.run_one_function({"name": tool_name, "arguments": args})
                if isinstance(r, dict) and r.get("status") == "error":
                    sources_failed.append(
                        f"{source_name}: {r.get('error', 'unknown error')[:100]}"
                    )
                    return r
                return r
            except Exception as e:
                sources_failed.append(f"{source_name}: {str(e)[:100]}")
                return {"status": "error", "error": str(e)}

        # 1. DisGeNET
        if disease:
            r = _try_tool(
                "DisGeNET", "DisGeNET_search_disease", {"disease": disease, "limit": 20}
            )
        else:
            r = _try_tool(
                "DisGeNET", "DisGeNET_search_gene", {"gene": gene, "limit": 20}
            )
        results_by_source["DisGeNET"] = self._extract_genes_or_diseases(
            r, "DisGeNET", query_by_disease=bool(disease)
        )

        # 2. OMIM
        r = _try_tool("OMIM", "OMIM_search", {"query": disease or gene, "limit": 10})
        results_by_source["OMIM"] = self._extract_genes_or_diseases(
            r, "OMIM", query_by_disease=bool(disease)
        )

        # 3. OpenTargets
        # Fix-R30D-6: for a gene-only query, passing the gene symbol into
        # OpenTargets_get_disease_ids_by_name (a disease-name search) doesn't
        # look up the gene's associated diseases at all -- confirmed live it
        # returns 0-1 spurious hits that merely happen to contain the gene
        # symbol as a substring (e.g. "congenital muscular dystrophy due to
        # LMNA mutation"), not real gene->disease associations (OpenTargets
        # itself has 6084 for LMNA). Resolve the gene symbol to its Ensembl
        # ID first and query its associated-diseases list instead.
        if disease:
            r = self._opentargets_disease_genes(tu, disease, sources_failed)
        else:
            r = self._opentargets_gene_diseases(tu, gene, sources_failed)
        results_by_source["OpenTargets"] = self._extract_genes_or_diseases(
            r, "OpenTargets", query_by_disease=bool(disease)
        )

        # 4. GenCC
        if gene:
            r = _try_tool("GenCC", "GenCC_search_gene", {"gene_symbol": gene})
        else:
            r = _try_tool("GenCC", "GenCC_search_disease", {"disease": disease})
        results_by_source["GenCC"] = self._extract_genes_or_diseases(
            r, "GenCC", query_by_disease=bool(disease)
        )

        # 5. ClinVar -- Fix-R80A-1: "query" is documented as an alias for
        # "condition" (a disease/phenotype free-text search), not a gene
        # lookup -- the exact same mistake already caught and fixed in the
        # sibling compound_variant_tool.py (Fix-R31D-4/R31A-3), but never
        # ported here. Confirmed live that {"query": "LDLR"} silently
        # returned ClinVar rows for LDLR-related variants anyway (a
        # coincidental partial match, not a deliberate gene lookup) whose
        # `genes` field then got mislabeled as "disease" entries below (see
        # that fix for why genes can't be used as disease names at all).
        # Branch on gene/disease the same way DisGeNET/OpenTargets already do
        # above.
        if disease:
            r = _try_tool(
                "ClinVar",
                "ClinVar_search_variants",
                {"condition": disease, "limit": 10},
            )
        else:
            r = _try_tool(
                "ClinVar", "ClinVar_search_variants", {"gene": gene, "limit": 10}
            )
        results_by_source["ClinVar"] = self._extract_genes_or_diseases(
            r, "ClinVar", query_by_disease=bool(disease)
        )

        notes: List[str] = []
        clinvar_failed = any(f.startswith("ClinVar:") for f in sources_failed)
        # Only the gene->disease direction has the ClinVar data-shape limitation
        # (its rows carry no disease name). In the disease->gene direction ClinVar
        # DOES contribute (the variants' `genes` field), so no note is needed.
        if not clinvar_failed and not results_by_source["ClinVar"] and not disease:
            notes.append(
                "ClinVar was queried successfully but contributed no entries to "
                "the disease-name comparison: ClinVar_search_variants' response "
                "carries variant title/genes/clinical_significance, not a "
                "condition/disease name, so this tool cannot extract named "
                "disease associations from it. This is a data-shape limitation, "
                "not evidence ClinVar has no data for this gene/disease."
            )

        # Build cross-reference table
        associations = self._build_concordance(results_by_source)

        result: Dict[str, Any] = {
            "query": {"gene": gene, "disease": disease},
            "sources_queried": list(results_by_source.keys()),
            "sources_failed": sources_failed,
            "num_associations": len(associations),
            "associations": associations[:50],
            "per_source_results": {k: v[:10] for k, v in results_by_source.items()},
        }
        if notes:
            result["notes"] = notes
        return {"status": "success", "data": result}

    def _opentargets_gene_diseases(
        self, tu, gene: str, sources_failed: List[str]
    ) -> Dict[str, Any]:
        """Resolve a gene symbol to its OpenTargets/Ensembl target ID, then
        fetch its real associated-diseases list. OpenTargets has no
        symbol-keyed "diseases for this gene" endpoint, so this chains the
        target-name search (for the ID) with the ID-based diseases lookup.

        Both calls are wrapped the same way `_try_tool` wraps every other
        source in `run()` -- an unhandled exception here (e.g. a network
        error) would otherwise propagate out of `run()` and kill the whole
        multi-source lookup instead of just marking OpenTargets failed."""
        try:
            search = tu.run_one_function(
                {
                    "name": "OpenTargets_get_target_id_description_by_name",
                    "arguments": {"targetName": gene},
                }
            )
            hits = (search or {}).get("data", {}).get("search", {}).get("hits", [])
            if not hits:
                sources_failed.append(f"OpenTargets: no target match for gene '{gene}'")
                return {
                    "status": "error",
                    "error": f"No target match for gene '{gene}'",
                }

            gene_upper = gene.upper()
            match = next(
                (h for h in hits if h.get("name", "").upper() == gene_upper), hits[0]
            )
            ensembl_id = match.get("id")

            result = tu.run_one_function(
                {
                    "name": "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
                    "arguments": {"ensemblId": ensembl_id},
                }
            )
            if isinstance(result, dict) and result.get("status") == "error":
                sources_failed.append(
                    f"OpenTargets: {result.get('error', 'unknown error')[:100]}"
                )
            return result
        except Exception as e:
            sources_failed.append(f"OpenTargets: {str(e)[:100]}")
            return {"status": "error", "error": str(e)}

    def _opentargets_disease_genes(
        self, tu, disease: str, sources_failed: List[str]
    ) -> Dict[str, Any]:
        """Resolve a disease name to its OpenTargets EFO id, then fetch its real
        associated-targets (gene) list -- the disease-direction parallel of
        _opentargets_gene_diseases. The bare disease-name search
        (get_disease_ids_by_name / get_disease_id_description_by_name) only
        returns matching disease *names*, NOT the genes associated with the
        disease, so without this chaining a disease-query's OpenTargets
        contribution was just the queried disease echoed back instead of its
        associated genes (the disease-direction twin of the gene-direction bug
        already fixed by Fix-R30D-6)."""
        try:
            search = tu.run_one_function(
                {
                    "name": "OpenTargets_get_disease_id_description_by_name",
                    "arguments": {"diseaseName": disease},
                }
            )
            hits = (search or {}).get("data", {}).get("search", {}).get("hits", [])
            if not hits:
                sources_failed.append(f"OpenTargets: no disease match for '{disease}'")
                return {"status": "error", "error": f"No disease match for '{disease}'"}
            efo_id = hits[0].get("id")
            result = tu.run_one_function(
                {
                    "name": "OpenTargets_get_associated_targets_by_disease_efoId",
                    "arguments": {"efoId": efo_id},
                }
            )
            if isinstance(result, dict) and result.get("status") == "error":
                sources_failed.append(
                    f"OpenTargets: {result.get('error', 'unknown error')[:100]}"
                )
            return result
        except Exception as e:
            sources_failed.append(f"OpenTargets: {str(e)[:100]}")
            return {"status": "error", "error": str(e)}

    def _extract_genes_or_diseases(
        self, result: Any, source: str, query_by_disease: bool = False
    ) -> List[Dict[str, Any]]:
        """Extract the association *targets* from a tool result, direction-aware:
        the associated GENES when the caller queried by disease
        (disease->gene), the associated DISEASE names when they queried by gene
        (gene->disease). Without the direction split, a disease query just
        echoed back the queried disease name and dropped the genes that are the
        actual answer (e.g. GenCC returns cystic fibrosis + CFTR; the useful
        part for a disease query is CFTR)."""
        items = []
        if not isinstance(result, dict):
            return items
        if result.get("status") == "error":
            return items

        data = result.get("data", result)

        # GenCC "submissions" carry BOTH disease_title and gene_symbol; pick the
        # one the caller is asking for.
        if isinstance(data, dict) and "submissions" in data:
            for sub in data["submissions"][:30]:
                if isinstance(sub, dict):
                    if query_by_disease:
                        name = sub.get("gene_symbol") or sub.get("disease_title") or ""
                    else:
                        name = sub.get("disease_title") or sub.get("gene_symbol") or ""
                    items.append(
                        {
                            "name": str(name),
                            "score": None,
                            "source": source,
                            "evidence": sub.get("classification", ""),
                        }
                    )
            return items

        # OpenTargets gene->disease: "target.associatedDiseases.rows"
        if isinstance(data, dict) and "target" in data:
            rows = (
                (data.get("target") or {}).get("associatedDiseases", {}).get("rows", [])
            )
            for row in rows[:30]:
                disease = (row or {}).get("disease") or {}
                name = disease.get("name", "")
                if name:
                    items.append(
                        {"name": str(name), "score": row.get("score"), "source": source}
                    )
            return items

        # OpenTargets disease->gene: "disease.associatedTargets.rows"
        if isinstance(data, dict) and "disease" in data:
            rows = (
                (data.get("disease") or {}).get("associatedTargets", {}).get("rows", [])
            )
            for row in rows[:30]:
                target = (row or {}).get("target") or {}
                name = target.get("approvedSymbol", "")
                if name:
                    items.append(
                        {"name": str(name), "score": row.get("score"), "source": source}
                    )
            return items

        # OpenTargets bare disease-name search fallback: "search.hits" (names).
        if isinstance(data, dict) and "search" in data:
            hits = data["search"].get("hits", [])
            for hit in hits[:30]:
                if isinstance(hit, dict):
                    name = hit.get("name", "")
                    items.append({"name": str(name), "score": None, "source": source})
            return items

        # ClinVar_search_variants rows carry a variant title + a `genes` list +
        # clinical_significance -- NOT a condition/disease name. For a GENE
        # query, extracting those genes would mislabel them as diseases in the
        # concordance (Fix-R80A-1: "LDLR"/"LDLR-AS1" appeared as fake diseases)
        # -- so contribute nothing. For a DISEASE query, though, a
        # condition-search returns that disease's variants and their `genes`
        # field IS the disease-associated gene set (e.g. cystic fibrosis ->
        # CFTR), so extract it.
        if isinstance(data, dict) and "variants" in data:
            if query_by_disease:
                for v in (data.get("variants") or [])[:30]:
                    if isinstance(v, dict):
                        for g in v.get("genes", []) or []:
                            if g:
                                items.append(
                                    {"name": str(g), "score": None, "source": source}
                                )
            return items

        # Generic list: prefer the field the caller is asking for -- gene fields
        # for a disease query, disease fields for a gene query.
        if isinstance(data, dict):
            data = data.get(
                "results", data.get("data", data.get("genes", data.get("entries", [])))
            )
        if isinstance(data, list):
            gene_fields = ("gene_symbol", "geneName", "gene", "symbol")
            disease_fields = ("disease", "diseaseName", "disease_name", "title", "name")
            order = (
                gene_fields + disease_fields
                if query_by_disease
                else disease_fields + gene_fields
            )
            for item in data[:30]:
                if isinstance(item, dict):
                    name = next((item[f] for f in order if item.get(f)), "")
                    score = item.get(
                        "score", item.get("gda_score", item.get("associationScore"))
                    )
                    if name:
                        items.append(
                            {"name": str(name), "score": score, "source": source}
                        )
        return items

    def _build_concordance(
        self, results_by_source: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Build a concordance table showing which entities appear in which sources."""
        entity_sources: Dict[str, Dict[str, Any]] = {}

        for source, items in results_by_source.items():
            for item in items:
                name = item["name"].upper()
                if name not in entity_sources:
                    entity_sources[name] = {
                        "name": item["name"],
                        "sources": [],
                        "scores": {},
                    }
                entity_sources[name]["sources"].append(source)
                if item.get("score") is not None:
                    entity_sources[name]["scores"][source] = item["score"]

        associations = []
        for entity_data in entity_sources.values():
            sources = entity_data["sources"]
            associations.append(
                {
                    "name": entity_data["name"],
                    "sources": sorted(set(sources)),
                    "concordance": len(set(sources)),
                    "total_sources_queried": len(results_by_source),
                    "scores": entity_data["scores"],
                }
            )

        # Rank by cross-source concordance first (agreement = confidence), then
        # by the best association score within a tier, then name as a stable
        # tiebreak. Without the score term, entities in the same concordance tier
        # were ordered alphabetically, which could bury the most-relevant entity
        # below an alphabetically-earlier lower-scored one (e.g. for "sickle cell"
        # the causal gene HBB -- OpenTargets' top target at score 0.81 -- sorted
        # below BCL11A). Scores are computed here anyway; use them. Kept as an
        # internal sort key so the output shape is unchanged.
        for a in associations:
            vals = [v for v in a["scores"].values() if isinstance(v, (int, float))]
            a["_best_score"] = max(vals) if vals else None
        associations.sort(
            key=lambda a: (
                -a["concordance"],
                0 if a["_best_score"] is not None else 1,
                -(a["_best_score"] or 0),
                a["name"],
            )
        )
        for a in associations:
            a.pop("_best_score", None)
        return associations
