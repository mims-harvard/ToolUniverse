# impc_tool.py
"""
IMPC (International Mouse Phenotyping Consortium) Solr API tool for ToolUniverse.

IMPC provides standardized phenotyping data for knockout mouse lines,
covering all protein-coding genes in the mouse genome.

Data includes:
- Gene summaries with production/phenotyping status
- Mammalian Phenotype (MP) ontology annotations from knockout mice
- Statistical results from phenotyping pipelines
- Viability and fertility assessments

API Documentation: https://www.mousephenotype.org/help/programmatic-data-access/
Base URL: https://www.ebi.ac.uk/mi/impc/solr/
No authentication required.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for IMPC Solr API
IMPC_SOLR_BASE = "https://www.ebi.ac.uk/mi/impc/solr"


@register_tool("IMPCTool")
class IMPCTool(BaseTool):
    """
    Tool for querying IMPC mouse phenotyping data via Solr API.

    Provides access to:
    - Gene information and phenotyping status
    - Mouse knockout phenotype associations (MP terms)
    - Statistical results from standardized phenotyping
    - Viability and fertility data

    No authentication required. Data freely available (CC-BY 4.0).
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_gene_summary"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the IMPC API call."""
        operation = self.operation

        if operation == "get_gene_summary":
            return self._get_gene_summary(arguments)
        elif operation == "get_phenotypes_by_gene":
            return self._get_phenotypes_by_gene(arguments)
        elif operation == "search_genes":
            return self._search_genes(arguments)
        elif operation == "get_gene_phenotype_hits":
            return self._get_gene_phenotype_hits(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _solr_query(
        self,
        core: str,
        query: str,
        rows: int = 50,
        fields: Optional[str] = None,
        filter_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a Solr query against an IMPC core."""
        url = f"{IMPC_SOLR_BASE}/{core}/select"
        params = {
            "q": query,
            "rows": min(rows, 500),
            "wt": "json",
        }
        if fields:
            params["fl"] = fields
        if filter_query:
            params["fq"] = filter_query

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return {
                "status": "success",
                "response": data.get("response", {}),
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"IMPC Solr API timeout after {self.timeout}s",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"IMPC API HTTP error: {e.response.status_code}",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"IMPC API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_gene_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get gene summary from IMPC including phenotyping status, viability, and basic info.

        Queries the 'gene' core for a given gene symbol.
        """
        gene_symbol = arguments.get("gene_symbol", "")
        mgi_id = arguments.get("mgi_id", "")

        if not gene_symbol and not mgi_id:
            return {
                "status": "error",
                "error": "Either gene_symbol or mgi_id is required",
            }

        if mgi_id:
            query = f'mgi_accession_id:"{mgi_id}"'
        else:
            query = f'marker_symbol:"{gene_symbol}"'

        fields = (
            "mgi_accession_id,marker_symbol,marker_name,marker_synonym,"
            "marker_type,human_gene_symbol,status,imits_phenotype_started,"
            "imits_phenotype_complete,imits_phenotype_status,"
            "latest_phenotype_status,latest_production_status,"
            "latest_phenotyping_centre,latest_production_centre,"
            "allele_name,es_cell_status,mouse_status,phenotype_status,"
            "production_centre,phenotyping_centre,p_value,mp_id,mp_term,"
            "mp_term_synonym,top_level_mp_id,top_level_mp_term,"
            "hp_id,hp_term,disease_id,disease_term,disease_source,"
            "human_curated,mouse_curated,mgi_predicted,impc_predicted,"
            "has_qc,legacy_phenotype_status"
        )

        result = self._solr_query(core="gene", query=query, rows=5, fields=fields)

        if result["status"] != "success":
            return result

        docs = result["response"].get("docs", [])
        num_found = result["response"].get("numFound", 0)

        if num_found == 0:
            return {
                "status": "success",
                "data": None,
                "message": f"Gene not found in IMPC: {gene_symbol or mgi_id}. "
                "The gene may not yet be phenotyped by IMPC.",
            }

        gene_data = docs[0]
        return {
            "status": "success",
            "data": {
                "mgi_id": gene_data.get("mgi_accession_id"),
                "symbol": gene_data.get("marker_symbol"),
                "name": gene_data.get("marker_name"),
                "synonyms": gene_data.get("marker_synonym", []),
                "human_ortholog": gene_data.get("human_gene_symbol", []),
                "marker_type": gene_data.get("marker_type"),
                "phenotype_status": gene_data.get("latest_phenotype_status"),
                "production_status": gene_data.get("latest_production_status"),
                "phenotyping_centre": gene_data.get("latest_phenotyping_centre"),
                "production_centre": gene_data.get("latest_production_centre"),
                "has_phenotype_data": gene_data.get("imits_phenotype_complete") == "1"
                or bool(gene_data.get("mp_id")),
                "mp_terms": gene_data.get("mp_term", []),
                "mp_ids": gene_data.get("mp_id", []),
                "top_level_mp_terms": gene_data.get("top_level_mp_term", []),
                "hp_terms": gene_data.get("hp_term", []),
                "disease_associations": [
                    {"disease_id": did, "disease_term": dt}
                    for did, dt in zip(
                        gene_data.get("disease_id", []),
                        gene_data.get("disease_term", []),
                    )
                ]
                if gene_data.get("disease_id")
                else [],
            },
            "source": "IMPC (International Mouse Phenotyping Consortium)",
        }

    def _get_phenotypes_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all phenotype annotations for a gene from IMPC knockout mice.

        Queries the 'genotype-phenotype' core for significant phenotype calls.
        """
        gene_symbol = arguments.get("gene_symbol", "")
        mgi_id = arguments.get("mgi_id", "")
        rows = arguments.get("limit", 100)

        if not gene_symbol and not mgi_id:
            return {
                "status": "error",
                "error": "Either gene_symbol or mgi_id is required",
            }

        if mgi_id:
            query = f'marker_accession_id:"{mgi_id}"'
        else:
            query = f'marker_symbol:"{gene_symbol}"'

        fields = (
            "marker_symbol,marker_accession_id,allele_symbol,allele_accession_id,"
            "mp_term_id,mp_term_name,top_level_mp_term_id,top_level_mp_term_name,"
            "zygosity,sex,life_stage_name,parameter_name,procedure_name,"
            "pipeline_name,phenotyping_center,p_value,effect_size,"
            "statistical_method,resource_name"
        )

        result = self._solr_query(
            core="genotype-phenotype",
            query=query,
            rows=rows,
            fields=fields,
        )

        if result["status"] != "success":
            return result

        docs = result["response"].get("docs", [])
        num_found = result["response"].get("numFound", 0)

        # Organize phenotypes by MP term to deduplicate
        phenotype_map = {}
        for doc in docs:
            mp_id = doc.get("mp_term_id")
            if mp_id and mp_id not in phenotype_map:
                phenotype_map[mp_id] = {
                    "mp_term_id": mp_id,
                    "mp_term_name": doc.get("mp_term_name"),
                    "top_level_mp_term_id": doc.get("top_level_mp_term_id"),
                    "top_level_mp_term_name": doc.get("top_level_mp_term_name"),
                    "zygosity": doc.get("zygosity"),
                    "sex": doc.get("sex"),
                    "life_stage": doc.get("life_stage_name"),
                    "procedure": doc.get("procedure_name"),
                    "parameter": doc.get("parameter_name"),
                    "p_value": doc.get("p_value"),
                    "effect_size": doc.get("effect_size"),
                    "phenotyping_center": doc.get("phenotyping_center"),
                    "allele_symbol": doc.get("allele_symbol"),
                }

        phenotypes = list(phenotype_map.values())

        # Group by top-level MP term for summary
        top_level_groups = {}
        for p in phenotypes:
            top_names = p.get("top_level_mp_term_name") or ["Uncategorized"]
            if isinstance(top_names, str):
                top_names = [top_names]
            for tname in top_names:
                if tname not in top_level_groups:
                    top_level_groups[tname] = []
                top_level_groups[tname].append(p["mp_term_name"])

        return {
            "status": "success",
            "data": {
                "gene_symbol": gene_symbol or docs[0].get("marker_symbol", ""),
                "mgi_id": mgi_id
                or (docs[0].get("marker_accession_id", "") if docs else ""),
                "total_phenotype_calls": num_found,
                "unique_phenotypes": len(phenotypes),
                "phenotypes": phenotypes,
                "phenotype_summary_by_system": {
                    system: terms for system, terms in sorted(top_level_groups.items())
                },
            },
            "source": "IMPC genotype-phenotype associations",
        }

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search IMPC for genes matching a query string.

        Useful for finding MGI IDs from gene symbols or partial names.
        """
        query_str = arguments.get("query", "")
        rows = arguments.get("limit", 20)

        if not query_str:
            return {"status": "error", "error": "query parameter is required"}

        # Search across multiple fields
        query = (
            f"marker_symbol:{query_str}* OR "
            f"marker_name:*{query_str}* OR "
            f"marker_synonym:*{query_str}* OR "
            f'mgi_accession_id:"{query_str}"'
        )

        fields = (
            "mgi_accession_id,marker_symbol,marker_name,marker_synonym,"
            "marker_type,human_gene_symbol,latest_phenotype_status,"
            "latest_production_status"
        )

        result = self._solr_query(core="gene", query=query, rows=rows, fields=fields)

        if result["status"] != "success":
            return result

        docs = result["response"].get("docs", [])
        num_found = result["response"].get("numFound", 0)

        genes = []
        for doc in docs:
            genes.append(
                {
                    "mgi_id": doc.get("mgi_accession_id"),
                    "symbol": doc.get("marker_symbol"),
                    "name": doc.get("marker_name"),
                    "synonyms": doc.get("marker_synonym", []),
                    "human_ortholog": doc.get("human_gene_symbol", []),
                    "phenotype_status": doc.get("latest_phenotype_status"),
                    "production_status": doc.get("latest_production_status"),
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query_str,
                "genes": genes,
                "count": len(genes),
                "total_found": num_found,
            },
            "source": "IMPC gene search",
        }

    def _get_gene_phenotype_hits(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistical results for a gene including p-values and effect sizes.

        Queries the 'statistical-result' core for detailed phenotyping statistics.
        """
        gene_symbol = arguments.get("gene_symbol", "")
        mgi_id = arguments.get("mgi_id", "")
        rows = arguments.get("limit", 100)
        significant_only = arguments.get("significant_only", True)

        if not gene_symbol and not mgi_id:
            return {
                "status": "error",
                "error": "Either gene_symbol or mgi_id is required",
            }

        if mgi_id:
            query = f'marker_accession_id:"{mgi_id}"'
        else:
            query = f'marker_symbol:"{gene_symbol}"'

        filter_query = None
        if significant_only:
            filter_query = "significant:true"

        fields = (
            "marker_symbol,marker_accession_id,allele_symbol,"
            "mp_term_id,mp_term_name,top_level_mp_term_id,top_level_mp_term_name,"
            "parameter_name,procedure_name,pipeline_name,"
            "zygosity,sex,phenotyping_center,"
            "p_value,effect_size,statistical_method,significant,"
            "female_ko_parameter_estimate,male_ko_parameter_estimate,"
            "female_percentage_change,male_percentage_change,"
            "classification_tag,life_stage_name"
        )

        result = self._solr_query(
            core="statistical-result",
            query=query,
            rows=rows,
            fields=fields,
            filter_query=filter_query,
        )

        if result["status"] != "success":
            return result

        docs = result["response"].get("docs", [])
        num_found = result["response"].get("numFound", 0)

        hits = []
        for doc in docs:
            hits.append(
                {
                    "parameter": doc.get("parameter_name"),
                    "procedure": doc.get("procedure_name"),
                    "mp_term_id": doc.get("mp_term_id"),
                    "mp_term_name": doc.get("mp_term_name"),
                    "top_level_mp_term": doc.get("top_level_mp_term_name"),
                    "p_value": doc.get("p_value"),
                    "effect_size": doc.get("effect_size"),
                    "significant": doc.get("significant"),
                    "zygosity": doc.get("zygosity"),
                    "sex": doc.get("sex"),
                    "life_stage": doc.get("life_stage_name"),
                    "statistical_method": doc.get("statistical_method"),
                    "classification_tag": doc.get("classification_tag"),
                    "female_ko_estimate": doc.get("female_ko_parameter_estimate"),
                    "male_ko_estimate": doc.get("male_ko_parameter_estimate"),
                    "phenotyping_center": doc.get("phenotyping_center"),
                    "allele_symbol": doc.get("allele_symbol"),
                }
            )

        return {
            "status": "success",
            "data": {
                "gene_symbol": gene_symbol
                or (docs[0].get("marker_symbol", "") if docs else ""),
                "total_results": num_found,
                "results_returned": len(hits),
                "significant_only": significant_only,
                "hits": hits,
            },
            "source": "IMPC statistical results",
        }
