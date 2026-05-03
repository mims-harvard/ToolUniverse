# bvbrc_tool.py
"""
BV-BRC (Bacterial and Viral Bioinformatics Resource Center) REST API tool for ToolUniverse.

BV-BRC (formerly PATRIC) is the primary NIAID-funded bioinformatics resource center
for bacterial and viral pathogen genomics. It provides access to genome assemblies,
antimicrobial resistance (AMR) data, genome features, and specialty genes across
hundreds of thousands of pathogen genomes.

API: https://www.bv-brc.org/api/
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

BVBRC_BASE_URL = "https://www.bv-brc.org/api"


@register_tool("BVBRCTool")
class BVBRCTool(BaseTool):
    """
    Tool for querying the BV-BRC pathogen genomics database.

    BV-BRC provides comprehensive pathogen genome data including genome metadata,
    antimicrobial resistance phenotypes, and annotated genome features. Covers
    bacteria and viruses with rich AMR surveillance data.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.data_type = fields.get("data_type", "genome")
        self.action = fields.get("action", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BV-BRC API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"BV-BRC API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to BV-BRC API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"BV-BRC API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying BV-BRC: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate query method."""
        if self.data_type == "genome" and self.action == "get":
            return self._get_genome(arguments)
        elif self.data_type == "genome" and self.action == "search":
            return self._search_genomes(arguments)
        elif self.data_type == "genome_amr":
            return self._search_amr(arguments)
        elif self.data_type == "genome_feature":
            return self._search_features(arguments)
        elif self.data_type == "epitope":
            return self._search_epitopes(arguments)
        elif self.data_type == "surveillance":
            return self._search_surveillance(arguments)
        elif self.data_type == "sp_gene":
            return self._search_specialty_genes(arguments)
        elif self.data_type == "protein_structure" and self.action == "get":
            return self._get_protein_structure(arguments)
        elif self.data_type == "protein_structure" and self.action == "search":
            return self._search_protein_structures(arguments)
        elif self.data_type == "taxonomy" and self.action == "get":
            return self._get_taxonomy(arguments)
        elif self.data_type == "taxonomy" and self.action == "search":
            return self._search_taxonomy(arguments)
        elif self.data_type == "pathway":
            return self._search_pathways(arguments)
        elif self.data_type == "subsystem":
            return self._search_subsystems(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown data_type/action: {self.data_type}/{self.action}",
            }

    def _build_query_string(
        self,
        conditions: List[str],
        limit: int = 25,
        select_fields: Optional[List[str]] = None,
    ) -> str:
        """Build BV-BRC SOLR-like query string."""
        parts = []
        if len(conditions) == 1:
            parts.append(conditions[0])
        elif len(conditions) > 1:
            parts.append(f"and({','.join(conditions)})")

        parts.append(f"limit({limit})")

        if select_fields:
            parts.append(f"select({','.join(select_fields)})")

        return "&".join(parts)

    def _make_request(self, endpoint: str, query: str) -> Any:
        """Make a request to BV-BRC API."""
        url = f"{BVBRC_BASE_URL}/{endpoint}/?{query}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _get_genome(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific genome by ID."""
        genome_id = arguments.get("genome_id", "")
        if not genome_id:
            return {"status": "error", "error": "genome_id parameter is required"}

        select_fields = [
            "genome_id",
            "genome_name",
            "organism_name",
            "taxon_id",
            "genome_length",
            "gc_content",
            "contigs",
            "genome_status",
            "isolation_country",
            "host_name",
            "disease",
            "collection_date",
            "completion_date",
            "chromosomes",
            "plasmids",
            "sequences",
        ]

        query = self._build_query_string(
            [f"eq(genome_id,{genome_id})"],
            limit=1,
            select_fields=select_fields,
        )

        data = self._make_request("genome", query)

        if not data:
            return {
                "status": "success",
                "data": {},
                "metadata": {"source": "BV-BRC", "query_genome_id": genome_id},
            }

        return {
            "status": "success",
            "data": data[0] if isinstance(data, list) else data,
            "metadata": {"source": "BV-BRC", "query_genome_id": genome_id},
        }

    def _search_genomes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for genomes by keyword."""
        keyword = arguments.get("keyword", "")
        if not keyword:
            return {"status": "error", "error": "keyword parameter is required"}

        limit = min(arguments.get("limit") or 10, 100)

        select_fields = [
            "genome_id",
            "genome_name",
            "organism_name",
            "taxon_id",
            "genome_length",
            "gc_content",
            "genome_status",
            "host_name",
            "disease",
            "isolation_country",
        ]

        query = self._build_query_string(
            [f"keyword({keyword})"],
            limit=limit,
            select_fields=select_fields,
        )

        data = self._make_request("genome", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query": keyword,
            },
        }

    def _search_amr(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for antimicrobial resistance data."""
        conditions = []

        antibiotic = arguments.get("antibiotic")
        genome_id = arguments.get("genome_id")
        phenotype = arguments.get("resistant_phenotype")

        if antibiotic:
            conditions.append(f"eq(antibiotic,{antibiotic})")
        if genome_id:
            conditions.append(f"eq(genome_id,{genome_id})")
        if phenotype:
            conditions.append(f"eq(resistant_phenotype,{phenotype})")

        if not conditions:
            return {
                "status": "error",
                "error": "At least one of antibiotic, genome_id, or resistant_phenotype is required",
            }

        limit = min(arguments.get("limit") or 25, 100)

        select_fields = [
            "genome_id",
            "genome_name",
            "antibiotic",
            "resistant_phenotype",
            "measurement",
            "measurement_value",
            "measurement_unit",
            "laboratory_typing_method",
            "computational_method",
            "evidence",
            "taxon_id",
        ]

        query = self._build_query_string(
            conditions, limit=limit, select_fields=select_fields
        )
        data = self._make_request("genome_amr", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query_antibiotic": antibiotic,
                "query_genome_id": genome_id,
            },
        }

    def _search_features(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for genome features (genes, CDS)."""
        conditions = [
            "eq(annotation,PATRIC)",
            "eq(feature_type,CDS)",
        ]

        gene = arguments.get("gene")
        product = arguments.get("product") or arguments.get("keyword")
        genome_id = arguments.get("genome_id")

        if gene:
            conditions.append(f"eq(gene,{gene})")
        if product:
            conditions.append(f"keyword({product})")
        if genome_id:
            conditions.append(f"eq(genome_id,{genome_id})")

        if not gene and not product and not genome_id:
            return {
                "status": "error",
                "error": "At least one of gene, product, keyword, or genome_id is required",
            }

        limit = min(arguments.get("limit") or 10, 100)

        select_fields = [
            "patric_id",
            "genome_name",
            "gene",
            "product",
            "feature_type",
            "aa_length",
            "accession",
            "start",
            "end",
            "strand",
            "genome_id",
        ]

        query = self._build_query_string(
            conditions, limit=limit, select_fields=select_fields
        )
        data = self._make_request("genome_feature", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query_gene": gene,
                "query_product": product,
            },
        }

    def _search_epitopes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for pathogen epitopes (B-cell and T-cell)."""
        conditions = []

        taxon_id = arguments.get("taxon_id")
        protein_name = arguments.get("protein_name")
        epitope_type = arguments.get("epitope_type")
        organism = arguments.get("organism")

        if taxon_id:
            conditions.append(f"eq(taxon_id,{taxon_id})")
        if protein_name:
            conditions.append(f'eq(protein_name,"{protein_name}")')
        if epitope_type:
            conditions.append(f"eq(epitope_type,{epitope_type})")
        if organism:
            conditions.append(f"keyword({organism})")

        if not conditions:
            return {
                "status": "error",
                "error": "At least one of taxon_id, protein_name, epitope_type, or organism is required",
            }

        limit = min(arguments.get("limit") or 25, 100)

        select_fields = [
            "epitope_id",
            "epitope_type",
            "epitope_sequence",
            "organism",
            "protein_name",
            "start",
            "end",
            "bcell_assays",
            "tcell_assays",
            "mhc_allele",
            "taxon_id",
        ]

        query = self._build_query_string(
            conditions, limit=limit, select_fields=select_fields
        )
        data = self._make_request("epitope", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query_taxon_id": taxon_id,
                "query_protein_name": protein_name,
            },
        }

    def _search_surveillance(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search influenza/pathogen surveillance data."""
        conditions = []

        subtype = arguments.get("subtype")
        geographic_group = arguments.get("geographic_group")
        host_group = arguments.get("host_group")
        collection_country = arguments.get("collection_country")

        if subtype:
            conditions.append(f"eq(subtype,{subtype})")
        if geographic_group:
            conditions.append(f"eq(geographic_group,{geographic_group})")
        if host_group:
            conditions.append(f"eq(host_group,{host_group})")
        if collection_country:
            conditions.append(f"eq(collection_country,{collection_country})")

        if not conditions:
            return {
                "status": "error",
                "error": "At least one of subtype, geographic_group, host_group, or collection_country is required",
            }

        limit = min(arguments.get("limit") or 25, 100)

        select_fields = [
            "sample_identifier",
            "collection_date",
            "geographic_group",
            "host_group",
            "host_species",
            "subtype",
            "collection_country",
            "pathogen_test_result",
        ]

        query = self._build_query_string(
            conditions, limit=limit, select_fields=select_fields
        )
        data = self._make_request("surveillance", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query_subtype": subtype,
                "query_geographic_group": geographic_group,
            },
        }

    def _search_specialty_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for specialty genes (virulence factors, AMR genes, drug targets)."""
        conditions = []

        gene = arguments.get("gene")
        prop = arguments.get("property")
        source = arguments.get("source")
        taxon_id = arguments.get("taxon_id")

        if gene:
            conditions.append(f"eq(gene,{gene})")
        if prop:
            # BV-BRC RQL requires wildcard for multi-word values in and() queries
            prop_val = prop.replace(" ", "*") if " " in prop else prop
            conditions.append(f"eq(property,{prop_val})")
        if source:
            conditions.append(f"eq(source,{source})")
        if taxon_id:
            conditions.append(f"eq(taxon_id,{taxon_id})")

        if not conditions:
            return {
                "status": "error",
                "error": "At least one of gene, property, source, or taxon_id is required",
            }

        limit = min(arguments.get("limit") or 25, 100)

        select_fields = [
            "feature_id",
            "gene",
            "product",
            "property",
            "source",
            "evidence",
            "organism",
            "source_id",
            "taxon_id",
            "genome_id",
        ]

        query = self._build_query_string(
            conditions, limit=limit, select_fields=select_fields
        )
        data = self._make_request("sp_gene", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query_gene": gene,
                "query_property": prop,
            },
        }

    def _get_protein_structure(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific protein structure by PDB ID."""
        pdb_id = arguments.get("pdb_id", "")
        if not pdb_id:
            return {"status": "error", "error": "pdb_id parameter is required"}

        url = f"{BVBRC_BASE_URL}/protein_structure/{pdb_id}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not data:
            return {
                "status": "success",
                "data": {},
                "metadata": {"source": "BV-BRC", "query_pdb_id": pdb_id},
            }

        return {
            "status": "success",
            "data": data,
            "metadata": {"source": "BV-BRC", "query_pdb_id": pdb_id},
        }

    def _search_protein_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for pathogen protein structures."""
        conditions = []

        taxon_id = arguments.get("taxon_id")
        gene = arguments.get("gene")
        method = arguments.get("method")

        if taxon_id:
            conditions.append(f"eq(taxon_id,{taxon_id})")
        if gene:
            conditions.append(f"eq(gene,{gene})")
        if method:
            conditions.append(f"eq(method,{method})")

        if not conditions:
            return {
                "status": "error",
                "error": "At least one of taxon_id, gene, or method is required",
            }

        limit = min(arguments.get("limit") or 10, 100)

        select_fields = [
            "pdb_id",
            "title",
            "organism_name",
            "gene",
            "method",
            "resolution",
            "release_date",
            "taxon_id",
            "pmid",
        ]

        query = self._build_query_string(
            conditions, limit=limit, select_fields=select_fields
        )
        data = self._make_request("protein_structure", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query_taxon_id": taxon_id,
                "query_gene": gene,
            },
        }

    def _get_taxonomy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy details by taxon ID."""
        taxon_id = arguments.get("taxon_id", "")
        if not taxon_id:
            return {"status": "error", "error": "taxon_id parameter is required"}

        url = f"{BVBRC_BASE_URL}/taxonomy/{taxon_id}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not data:
            return {
                "status": "success",
                "data": {},
                "metadata": {"source": "BV-BRC", "query_taxon_id": str(taxon_id)},
            }

        return {
            "status": "success",
            "data": data,
            "metadata": {"source": "BV-BRC", "query_taxon_id": str(taxon_id)},
        }

    def _search_taxonomy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search pathogen taxonomy."""
        keyword = arguments.get("keyword", "")
        if not keyword:
            return {"status": "error", "error": "keyword parameter is required"}

        limit = min(arguments.get("limit") or 10, 100)

        select_fields = [
            "taxon_id",
            "taxon_name",
            "taxon_rank",
            "genomes",
            "lineage_names",
            "other_names",
        ]

        query = self._build_query_string(
            [f"keyword({keyword})"],
            limit=limit,
            select_fields=select_fields,
        )
        data = self._make_request("taxonomy", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query": keyword,
            },
        }

    def _search_pathways(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for metabolic pathways in pathogen genomes."""
        conditions = []

        taxon_id = arguments.get("taxon_id")
        pathway_name = arguments.get("pathway_name")
        ec_number = arguments.get("ec_number")
        genome_id = arguments.get("genome_id")

        if taxon_id:
            conditions.append(f"eq(taxon_id,{taxon_id})")
        if pathway_name:
            conditions.append(f"keyword({pathway_name})")
        if ec_number:
            conditions.append(f"eq(ec_number,{ec_number})")
        if genome_id:
            conditions.append(f"eq(genome_id,{genome_id})")

        if not conditions:
            return {
                "status": "error",
                "error": "At least one of taxon_id, pathway_name, ec_number, or genome_id is required",
            }

        limit = min(arguments.get("limit") or 25, 100)

        select_fields = [
            "pathway_id",
            "pathway_name",
            "pathway_class",
            "genome_id",
            "genome_name",
            "ec_number",
            "ec_description",
            "taxon_id",
        ]

        query = self._build_query_string(
            conditions, limit=limit, select_fields=select_fields
        )
        data = self._make_request("pathway", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query_taxon_id": taxon_id,
                "query_pathway_name": pathway_name,
            },
        }

    def _search_subsystems(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for functional subsystems in pathogen genomes."""
        conditions = []

        taxon_id = arguments.get("taxon_id")
        superclass = arguments.get("superclass")
        subsystem_name = arguments.get("subsystem_name")
        role_name = arguments.get("role_name")
        genome_id = arguments.get("genome_id")

        if taxon_id:
            conditions.append(f"eq(taxon_id,{taxon_id})")
        if superclass:
            # BV-BRC RQL requires wildcard for multi-word values in and() queries
            sc_val = superclass.replace(" ", "*") if " " in superclass else superclass
            conditions.append(f"eq(superclass,{sc_val})")
        if subsystem_name:
            conditions.append(f"keyword({subsystem_name})")
        if role_name:
            conditions.append(f"keyword({role_name})")
        if genome_id:
            conditions.append(f"eq(genome_id,{genome_id})")

        if not conditions:
            return {
                "status": "error",
                "error": "At least one of taxon_id, superclass, subsystem_name, role_name, or genome_id is required",
            }

        limit = min(arguments.get("limit") or 25, 100)

        select_fields = [
            "subsystem_id",
            "subsystem_name",
            "superclass",
            "class",
            "subclass",
            "genome_name",
            "role_name",
            "taxon_id",
            "genome_id",
        ]

        query = self._build_query_string(
            conditions, limit=limit, select_fields=select_fields
        )
        data = self._make_request("subsystem", query)

        results = data if isinstance(data, list) else [data] if data else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BV-BRC",
                "total_results": len(results),
                "query_taxon_id": taxon_id,
                "query_subsystem_name": subsystem_name,
            },
        }
