# mygene_tool.py
"""
MyGene.info API tool for ToolUniverse.

MyGene.info is a high-performance gene annotation service providing
access to gene information from 30+ sources for 22M+ genes across 22K+ species.

API Documentation: https://mygene.info/doc
"""

import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for MyGene.info API v3
MYGENE_BASE_URL = "https://mygene.info/v3"


@register_tool("MyGeneTool")
class MyGeneTool(BaseTool):
    """
    Tool for querying MyGene.info API.

    MyGene.info provides gene annotation data from 30+ sources including
    Entrez Gene, Ensembl, UniProt, HGNC, and more.

    No authentication required. Free for academic/research use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        # Get the operation type from config
        self.operation = tool_config.get("fields", {}).get("operation", "query")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MyGene.info API call."""
        operation = self.operation

        if operation == "query":
            return self._query_genes(arguments)
        elif operation == "get_gene":
            return self._get_gene(arguments)
        elif operation == "query_batch":
            return self._query_batch(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _query_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query genes by keyword, symbol, or other identifiers.

        Endpoint: GET /query
        """
        query = arguments.get("query", "")
        species = arguments.get("species", "human")
        fields = arguments.get("fields", "symbol,name,entrezgene,ensembl.gene")
        size = arguments.get("size", 10)

        if not query:
            return {"status": "error", "error": "Query parameter is required"}

        params = {
            "q": query,
            "species": species,
            "fields": fields,
            "size": min(size, 100),  # Cap at 100 to avoid overwhelming responses
        }

        try:
            response = requests.get(
                f"{MYGENE_BASE_URL}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyGene.info API request failed: {str(e)}",
            }

    def _get_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed gene annotation by gene ID.

        Endpoint: GET /gene/<geneid>
        """
        gene_id = arguments.get("gene_id", "")
        fields = arguments.get(
            "fields", "symbol,name,entrezgene,ensembl,summary,generif,pathway"
        )

        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        params = {"fields": fields}

        try:
            response = requests.get(
                f"{MYGENE_BASE_URL}/gene/{gene_id}", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyGene.info API request failed: {str(e)}",
            }

    def _query_batch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query multiple genes at once using POST.

        Endpoint: POST /query
        """
        gene_ids = arguments.get("gene_ids", [])
        fields = arguments.get("fields", "symbol,name,entrezgene")
        species = arguments.get("species", "human")

        if not gene_ids:
            return {
                "status": "error",
                "error": "gene_ids parameter is required (list of gene IDs)",
            }

        # Convert list to comma-separated string if needed
        if isinstance(gene_ids, list):
            gene_ids_str = ",".join(str(g) for g in gene_ids)
        else:
            gene_ids_str = str(gene_ids)

        data = {
            "q": gene_ids_str,
            "scopes": "entrezgene,ensembl.gene,symbol",
            "species": species,
            "fields": fields,
        }

        try:
            response = requests.post(
                f"{MYGENE_BASE_URL}/query", data=data, timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "success", "data": {"results": response.json()}}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyGene.info API request failed: {str(e)}",
            }


@register_tool("MyVariantTool")
class MyVariantTool(BaseTool):
    """
    Tool for querying MyVariant.info API.

    MyVariant.info provides variant annotation data from 19+ sources
    for 400M+ human variants.

    No authentication required. Free for academic/research use.
    """

    MYVARIANT_BASE_URL = "https://myvariant.info/v1"

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "query")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MyVariant.info API call."""
        operation = self.operation

        if operation == "query":
            return self._query_variants(arguments)
        elif operation == "get_variant":
            return self._get_variant(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _query_variants(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query variants by various criteria.

        Endpoint: GET /query
        """
        query = arguments.get("query", "")
        fields = arguments.get("fields", "dbsnp,clinvar,cadd,gnomad_genome")
        size = arguments.get("size", 10)

        if not query:
            return {"status": "error", "error": "Query parameter is required"}

        params = {"q": query, "fields": fields, "size": min(size, 100)}

        try:
            response = requests.get(
                f"{self.MYVARIANT_BASE_URL}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyVariant.info API request failed: {str(e)}",
            }

    def _get_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed variant annotation by HGVS ID.

        Endpoint: GET /variant/<hgvsid>
        """
        variant_id = arguments.get("variant_id", "")
        fields = arguments.get("fields", "dbsnp,clinvar,cadd,gnomad_genome,dbnsfp")

        if not variant_id:
            return {
                "status": "error",
                "error": "variant_id parameter is required (HGVS format)",
            }

        params = {"fields": fields}

        try:
            response = requests.get(
                f"{self.MYVARIANT_BASE_URL}/variant/{variant_id}",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyVariant.info API request failed: {str(e)}",
            }


@register_tool("MyChemTool")
class MyChemTool(BaseTool):
    """
    Tool for querying MyChem.info API.

    MyChem.info provides chemical/drug annotation data from 30+ sources
    for 90M+ chemicals and drugs.

    No authentication required. Free for academic/research use.
    """

    MYCHEM_BASE_URL = "https://mychem.info/v1"

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "query")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MyChem.info API call."""
        operation = self.operation

        if operation == "query":
            return self._query_chemicals(arguments)
        elif operation == "get_chemical":
            return self._get_chemical(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _query_chemicals(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query chemicals/drugs by name, InChIKey, or other identifiers.

        Endpoint: GET /query
        """
        query = arguments.get("query", "")
        fields = arguments.get("fields", "drugbank,chebi,pubchem,chembl")
        size = arguments.get("size", 10)

        if not query:
            return {"status": "error", "error": "Query parameter is required"}

        params = {"q": query, "fields": fields, "size": min(size, 100)}

        try:
            response = requests.get(
                f"{self.MYCHEM_BASE_URL}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyChem.info API request failed: {str(e)}",
            }

    def _get_chemical(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed chemical annotation by InChIKey or other ID.

        Endpoint: GET /chem/<chemid>
        """
        chem_id = arguments.get("chem_id", "")
        fields = arguments.get("fields", "drugbank,chebi,pubchem,chembl,drugcentral")

        if not chem_id:
            return {
                "status": "error",
                "error": "chem_id parameter is required (InChIKey recommended)",
            }

        params = {"fields": fields}

        try:
            response = requests.get(
                f"{self.MYCHEM_BASE_URL}/chem/{chem_id}",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"MyChem.info API request failed: {str(e)}",
            }
