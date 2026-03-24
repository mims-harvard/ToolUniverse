# alliance_genome_tool.py
"""
Alliance of Genome Resources REST API tool for ToolUniverse.

The Alliance of Genome Resources (AGR) integrates data from 7 model organism
databases (SGD, FlyBase, WormBase, ZFIN, RGD, MGI, Xenbase) plus human data.
It provides unified access to gene information, disease associations,
phenotypes, and cross-species search across all model organisms.

API: https://www.alliancegenome.org/api
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ALLIANCE_BASE = "https://www.alliancegenome.org/api"


@register_tool("AllianceGenomeTool")
class AllianceGenomeTool(BaseTool):
    """
    Tool for querying the Alliance of Genome Resources API.

    Provides cross-species gene information across 7 model organisms
    (yeast, fly, worm, zebrafish, rat, mouse, frog) plus human.
    Supports gene detail, disease associations, phenotypes, and search.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "gene_detail"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Alliance of Genome Resources API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Alliance API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Alliance API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Alliance API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Alliance API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate Alliance endpoint."""
        endpoint_type = self.endpoint_type

        if endpoint_type == "gene_detail":
            return self._get_gene_detail(arguments)
        elif endpoint_type == "search_genes":
            return self._search_genes(arguments)
        elif endpoint_type == "gene_phenotypes":
            return self._get_gene_phenotypes(arguments)
        elif endpoint_type == "disease_genes":
            return self._get_disease_genes(arguments)
        elif endpoint_type == "disease_detail":
            return self._get_disease_detail(arguments)
        elif endpoint_type == "gene_orthologs":
            return self._get_gene_orthologs(arguments)
        elif endpoint_type == "gene_alleles":
            return self._get_gene_alleles(arguments)
        elif endpoint_type == "gene_expression_summary":
            return self._get_gene_expression_summary(arguments)
        elif endpoint_type == "gene_interactions":
            return self._get_gene_interactions(arguments)
        elif endpoint_type == "gene_disease_models":
            return self._get_gene_disease_models(arguments)
        elif endpoint_type == "allele_detail":
            return self._get_allele_detail(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint type: {endpoint_type}",
            }

    def _get_gene_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed gene information from Alliance."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'HGNC:6081', 'MGI:98834', 'FB:FBgn0003996')",
            }

        url = f"{ALLIANCE_BASE}/gene/{gene_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        species = data.get("species", {})
        locations = data.get("genomeLocations", [])
        loc_info = locations[0] if locations else {}
        xrefs = data.get("crossReferenceMap", {})

        # Extract cross-references
        other_xrefs = xrefs.get("other", [])
        xref_list = [
            {"name": x.get("name"), "url": x.get("crossRefCompleteUrl")}
            for x in other_xrefs[:10]
        ]

        return {
            "status": "success",
            "data": {
                "id": data.get("id"),
                "symbol": data.get("symbol"),
                "name": data.get("name"),
                "species": {
                    "name": species.get("name"),
                    "short_name": species.get("shortName"),
                    "taxon_id": species.get("taxonId"),
                    "data_provider": species.get("dataProviderShortName"),
                },
                "gene_synopsis": data.get("geneSynopsis"),
                "automated_gene_synopsis": data.get("automatedGeneSynopsis"),
                "synonyms": data.get("synonyms", []),
                "so_term": data.get("soTerm", {}).get("name"),
                "genomic_location": {
                    "chromosome": loc_info.get("chromosome"),
                    "start": loc_info.get("start"),
                    "end": loc_info.get("end"),
                    "assembly": loc_info.get("assembly"),
                    "strand": loc_info.get("strand"),
                },
                "cross_references": xref_list,
            },
            "metadata": {
                "query_gene_id": gene_id,
                "data_provider": data.get("dataProvider"),
                "source": "Alliance of Genome Resources",
            },
        }

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for genes across all model organisms."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        limit = arguments.get("limit", 10)
        url = f"{ALLIANCE_BASE}/search_autocomplete"
        params = {"q": query, "category": "gene", "limit": min(int(limit), 50)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        genes = []
        for r in results:
            genes.append(
                {
                    "symbol": r.get("symbol"),
                    "name": r.get("name"),
                    "primary_key": r.get("primaryKey"),
                    "name_key": r.get("name_key"),
                    "category": r.get("category"),
                }
            )

        return {
            "status": "success",
            "data": genes,
            "metadata": {
                "total_results": len(genes),
                "query": query,
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype annotations for a gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        url = f"{ALLIANCE_BASE}/gene/{gene_id}/phenotypes"
        params = {"limit": min(int(limit), 100), "page": int(page)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        phenotypes = []
        for r in results:
            subject = r.get("subject", {})
            phenotypes.append(
                {
                    "gene_symbol": subject.get("symbol"),
                    "gene_id": subject.get("primaryExternalId"),
                    "phenotype_statement": r.get("phenotypeStatement"),
                }
            )

        return {
            "status": "success",
            "data": phenotypes,
            "metadata": {
                "total_results": total,
                "returned": len(phenotypes),
                "query_gene_id": gene_id,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_disease_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genes associated with a disease by Disease Ontology ID."""
        disease_id = arguments.get("disease_id", "")
        if not disease_id:
            return {
                "status": "error",
                "error": "disease_id parameter is required (e.g., 'DOID:162' for cancer)",
            }

        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        url = f"{ALLIANCE_BASE}/disease/{disease_id}/genes"
        params = {"limit": min(int(limit), 100), "page": int(page)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        genes = []
        for r in results:
            subject = r.get("subject", {})
            species = subject.get("taxon", {})
            disease_obj = r.get("object", {})
            genes.append(
                {
                    "gene_symbol": subject.get("symbol")
                    or subject.get("geneSymbol", {}).get("displayText"),
                    "gene_id": subject.get("primaryExternalId") or subject.get("curie"),
                    "species": species.get("curie"),
                    "disease_name": disease_obj.get("name"),
                    "disease_id": disease_obj.get("curie"),
                    "association_type": r.get("associationType"),
                }
            )

        return {
            "status": "success",
            "data": genes,
            "metadata": {
                "total_results": total,
                "returned": len(genes),
                "query_disease_id": disease_id,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_disease_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get disease summary information by Disease Ontology ID."""
        disease_id = arguments.get("disease_id", "")
        if not disease_id:
            return {
                "status": "error",
                "error": "disease_id parameter is required (e.g., 'DOID:162' for cancer)",
            }

        url = f"{ALLIANCE_BASE}/disease/{disease_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        do_term = data.get("doTerm", {})
        synonyms = do_term.get("synonyms", [])
        synonym_names = [s.get("name") for s in synonyms if s.get("name")]

        return {
            "status": "success",
            "data": {
                "disease_id": do_term.get("curie"),
                "name": do_term.get("name"),
                "definition": do_term.get("definition"),
                "synonyms": synonym_names,
                "category": data.get("category"),
            },
            "metadata": {
                "query_disease_id": disease_id,
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ortholog genes across species for a given gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        stringency = arguments.get("stringency", "stringent")
        url = f"{ALLIANCE_BASE}/gene/{gene_id}/orthologs"
        params = {
            "limit": min(int(limit), 100),
            "page": int(page),
            "filter.stringency": stringency,
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        orthologs = []
        for r in results:
            orth = r.get("geneToGeneOrthologyGenerated", {})
            subject = orth.get("subjectGene", {})
            obj_gene = orth.get("objectGene", {})
            methods = orth.get("predictionMethodsMatched", [])
            orthologs.append(
                {
                    "subject_gene_id": subject.get("primaryExternalId"),
                    "subject_symbol": subject.get("geneSymbol", {}).get("displayText"),
                    "subject_species": subject.get("taxon", {}).get("name"),
                    "ortholog_gene_id": obj_gene.get("primaryExternalId"),
                    "ortholog_symbol": obj_gene.get("geneSymbol", {}).get(
                        "displayText"
                    ),
                    "ortholog_species": obj_gene.get("taxon", {}).get("name"),
                    "is_best_score": orth.get("isBestScore", {}).get("name"),
                    "is_best_score_reverse": orth.get("isBestScoreReverse", {}).get(
                        "name"
                    ),
                    "methods": [m.get("name") for m in methods],
                    "method_count": len(methods),
                }
            )

        return {
            "status": "success",
            "data": orthologs,
            "metadata": {
                "total_results": total,
                "returned": len(orthologs),
                "query_gene_id": gene_id,
                "stringency": stringency,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_alleles(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get alleles and variants for a gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        url = f"{ALLIANCE_BASE}/gene/{gene_id}/alleles"
        params = {"limit": min(int(limit), 100), "page": int(page)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        alleles = []
        for r in results:
            variants = r.get("variants", [])
            variant_info = []
            for v in variants[:3]:
                variant_info.append(
                    {
                        "id": v.get("id"),
                        "name": v.get("name"),
                        "type": v.get("variantType", {}).get("name"),
                        "location": v.get("location"),
                    }
                )
            alleles.append(
                {
                    "id": r.get("id"),
                    "symbol": r.get("symbol"),
                    "symbol_text": r.get("symbolText"),
                    "category": r.get("category"),
                    "has_disease": r.get("hasDisease"),
                    "has_phenotype": r.get("hasPhenotype"),
                    "variants": variant_info,
                }
            )

        return {
            "status": "success",
            "data": alleles,
            "metadata": {
                "total_results": total,
                "returned": len(alleles),
                "query_gene_id": gene_id,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_expression_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get expression summary (ribbon) for a gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        url = f"{ALLIANCE_BASE}/gene/{gene_id}/expression-summary"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        total_annotations = data.get("totalAnnotations", 0)
        groups = data.get("groups", [])
        expression_groups = []
        for g in groups:
            terms = []
            for t in g.get("terms", []):
                if t.get("numberOfAnnotations", 0) > 0:
                    terms.append(
                        {
                            "id": t.get("id"),
                            "name": t.get("name"),
                            "annotation_count": t.get("numberOfAnnotations"),
                        }
                    )
            expression_groups.append(
                {
                    "group_name": g.get("name"),
                    "total_annotations": g.get("totalAnnotations", 0),
                    "terms": terms,
                }
            )

        return {
            "status": "success",
            "data": {
                "total_annotations": total_annotations,
                "expression_groups": expression_groups,
            },
            "metadata": {
                "query_gene_id": gene_id,
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get molecular or genetic interactions for a gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        interaction_type = arguments.get("interaction_type", "molecular")
        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)

        if interaction_type == "genetic":
            url = f"{ALLIANCE_BASE}/gene/{gene_id}/genetic-interactions"
        else:
            url = f"{ALLIANCE_BASE}/gene/{gene_id}/molecular-interactions"

        params = {"limit": min(int(limit), 100), "page": int(page)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        interactions = []
        for r in results:
            if interaction_type == "genetic":
                gi = r.get("geneGeneticInteraction", {})
                subject = gi.get("geneAssociationSubject", {})
                obj = gi.get("geneGeneAssociationObject", {})
                int_type = gi.get("interactionType", {}).get("name")
            else:
                gi = r.get("geneMolecularInteraction", {})
                subject = gi.get("geneAssociationSubject", {})
                obj = gi.get("geneGeneAssociationObject", {})
                int_type = (
                    gi.get("interactionType", {}).get("name")
                    if gi.get("interactionType")
                    else None
                )

            interactions.append(
                {
                    "subject_gene_id": subject.get("primaryExternalId"),
                    "subject_symbol": subject.get("geneSymbol", {}).get("displayText"),
                    "interactor_gene_id": obj.get("primaryExternalId") if obj else None,
                    "interactor_symbol": obj.get("geneSymbol", {}).get("displayText")
                    if obj
                    else None,
                    "interactor_species": obj.get("taxon", {}).get("name")
                    if obj
                    else None,
                    "interaction_type": int_type,
                }
            )

        return {
            "status": "success",
            "data": interactions,
            "metadata": {
                "total_results": total,
                "returned": len(interactions),
                "query_gene_id": gene_id,
                "interaction_type": interaction_type,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_disease_models(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get disease models involving a gene."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        url = f"{ALLIANCE_BASE}/gene/{gene_id}/models"
        params = {"limit": min(int(limit), 100), "page": int(page)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        models = []
        for r in results:
            model = r.get("model", {})
            gene = r.get("gene", {})
            disease_models = r.get("diseaseModels", [])
            diseases = []
            for dm in disease_models:
                diseases.append(
                    {
                        "disease_name": dm.get("disease", {}).get("name"),
                        "disease_id": dm.get("disease", {}).get("curie"),
                        "association_type": dm.get("associationType"),
                    }
                )
            models.append(
                {
                    "model_id": model.get("primaryExternalId"),
                    "model_name": model.get("agmFullName", {}).get("displayText")
                    if isinstance(model.get("agmFullName"), dict)
                    else model.get("name"),
                    "gene_symbol": gene.get("geneSymbol", {}).get("displayText"),
                    "gene_id": gene.get("primaryExternalId"),
                    "data_provider": r.get("dataProvider"),
                    "diseases": diseases,
                }
            )

        return {
            "status": "success",
            "data": models,
            "metadata": {
                "total_results": total,
                "returned": len(models),
                "query_gene_id": gene_id,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_allele_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific allele."""
        allele_id = arguments.get("allele_id", "")
        if not allele_id:
            return {"status": "error", "error": "allele_id parameter is required"}

        url = f"{ALLIANCE_BASE}/allele/{allele_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        allele = data.get("allele", {})
        allele_of_gene = data.get("alleleOfGene", {})
        synonyms = allele.get("alleleSynonyms", [])
        synonym_list = [s.get("displayText") for s in synonyms if s.get("displayText")]

        return {
            "status": "success",
            "data": {
                "id": allele.get("primaryExternalId"),
                "symbol": allele.get("alleleSymbol", {}).get("displayText"),
                "species": allele.get("taxon", {}).get("name"),
                "alteration_type": data.get("alterationType"),
                "gene_id": allele_of_gene.get("primaryExternalId"),
                "gene_symbol": allele_of_gene.get("geneSymbol", {}).get("displayText"),
                "synonyms": synonym_list,
            },
            "metadata": {
                "query_allele_id": allele_id,
                "source": "Alliance of Genome Resources",
            },
        }
