"""
BridgeDb Tool - Biological Identifier Mapping Service

BridgeDb is a framework for mapping identifiers between biological databases.
It supports genes, proteins, metabolites, and other biological entities,
providing cross-references between HMDB, ChEBI, KEGG, PubChem, Ensembl,
UniProt, HGNC, and many more databases.

API base: https://webservice.bridgedb.org
No authentication required.

Reference: van Iersel et al., BMC Bioinformatics 2010, 11:5
"""

import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool


BRIDGEDB_BASE_URL = "https://webservice.bridgedb.org"

# System code mapping for common databases
SYSTEM_CODES = {
    "HMDB": "Ch",
    "ChEBI": "Ce",
    "KEGG Compound": "Ck",
    "KEGG Drug": "Kd",
    "PubChem-compound": "Cpc",
    "Wikidata": "Wd",
    "CAS": "Ca",
    "Chemspider": "Cs",
    "Ensembl": "En",
    "HGNC": "H",
    "UniProt": "S",
    "NCBI Gene": "L",
    "RefSeq": "Q",
    "KEGG Genes": "Kg",
    "PDB": "Pd",
    "GeneOntology": "T",
    "InChIKey": "Ik",
    "SwissLipids": "Sl",
    "KNApSAcK": "Kn",
    "Rhea": "Rh",
    "MetaCyc": "Mc",
}

# Reverse: code -> name
CODE_TO_NAME = {v: k for k, v in SYSTEM_CODES.items()}


@register_tool("BridgeDbTool")
class BridgeDbTool(BaseTool):
    """
    Tool for mapping biological identifiers across databases using BridgeDb.

    BridgeDb provides cross-reference lookups for genes, proteins, metabolites,
    and other biological entities across 45+ databases including HMDB, ChEBI,
    KEGG, PubChem, Ensembl, UniProt, and HGNC.

    Supported operations:
    - xrefs: Get all cross-references for an identifier
    - search: Search for identifiers by name
    - attributes: Get properties/attributes of an identifier
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.timeout = 30

    def _infer_operation(self, arguments: Dict[str, Any]) -> str:
        """Infer operation from tool name when not explicitly provided."""
        tool_name = self.tool_config.get("name", "")
        if "search" in tool_name.lower():
            return "search"
        if "xref" in tool_name.lower():
            return "xrefs"
        if "attribute" in tool_name.lower():
            return "attributes"
        return ""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BridgeDb API tool with given arguments."""
        # Feature-81-aliases: support source_database/target_database aliases
        if "source_database" in arguments and "source" not in arguments:
            arguments["source"] = arguments.pop("source_database")
        if "target_database" in arguments and "target_source" not in arguments:
            arguments["target_source"] = arguments.pop("target_database")
        operation = arguments.get("operation") or self._infer_operation(arguments)
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "xrefs": self._get_xrefs,
            "search": self._search,
            "attributes": self._get_attributes,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(operation_handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "BridgeDb API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to BridgeDb API"}
        except Exception as e:
            return {
                "status": "error",
                "error": "BridgeDb operation failed: {}".format(str(e)),
            }

    def _resolve_system_code(self, source: str) -> str:
        """Resolve a database name or system code to a BridgeDb system code."""
        # If it's already a valid 1-3 char system code, use it directly
        if source in CODE_TO_NAME:
            return source
        # Try to match by name (case-insensitive)
        source_lower = source.lower()
        for name, code in SYSTEM_CODES.items():
            if name.lower() == source_lower:
                return code
        # Return as-is if not recognized (let API handle the error)
        return source

    def _parse_tsv_xrefs(self, text: str) -> List[Dict[str, str]]:
        """Parse tab-separated cross-reference data into structured list."""
        results = []
        for line in text.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                identifier = parts[0]
                source_name = parts[1]
                # Look up the system code from the source name
                code = SYSTEM_CODES.get(source_name, "")
                results.append(
                    {
                        "identifier": identifier,
                        "database": source_name,
                        "system_code": code,
                    }
                )
        return results

    def _parse_tsv_attributes(self, text: str) -> Dict[str, Any]:
        """Parse tab-separated attribute data into structured dict."""
        attributes = {}
        synonyms = []
        for line in text.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                value = parts[0]
                key = parts[1]
                if key == "Synonym":
                    synonyms.append(value)
                else:
                    attributes[key] = value
        if synonyms:
            attributes["Synonyms"] = synonyms
        return attributes

    def _get_xrefs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cross-references for an identifier."""
        identifier = arguments.get("identifier")
        source = arguments.get("source")
        organism = arguments.get("organism", "Human")
        target_source = arguments.get("target_source")

        if not identifier or not source:
            return {
                "status": "error",
                "error": "Both 'identifier' and 'source' parameters are required",
            }

        system_code = self._resolve_system_code(source)
        url = "{}/{}/xrefs/{}/{}".format(
            BRIDGEDB_BASE_URL, organism, system_code, identifier
        )

        params = {}
        if target_source:
            params["dataSource"] = self._resolve_system_code(target_source)

        response = self.session.get(url, params=params, timeout=self.timeout)
        if response.status_code not in (200, 204):
            return {
                "status": "error",
                "error": "BridgeDb returned status {}".format(response.status_code),
            }

        if response.status_code == 204 or not response.text.strip():
            return {
                "status": "success",
                "data": {
                    "query_identifier": identifier,
                    "query_source": source,
                    "organism": organism,
                    "cross_references": [],
                    "count": 0,
                },
            }

        xrefs = self._parse_tsv_xrefs(response.text)
        return {
            "status": "success",
            "data": {
                "query_identifier": identifier,
                "query_source": source,
                "organism": organism,
                "cross_references": xrefs,
                "count": len(xrefs),
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for identifiers by name."""
        query = arguments.get("query")
        organism = arguments.get("organism", "Human")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        url = "{}/{}/search/{}".format(BRIDGEDB_BASE_URL, organism, query)

        response = self.session.get(url, timeout=self.timeout)
        if response.status_code not in (200, 204):
            return {
                "status": "error",
                "error": "BridgeDb returned status {}".format(response.status_code),
            }

        if response.status_code == 204 or not response.text.strip():
            return {
                "status": "success",
                "data": {
                    "query": query,
                    "organism": organism,
                    "results": [],
                    "count": 0,
                },
            }

        results = self._parse_tsv_xrefs(response.text)
        return {
            "status": "success",
            "data": {
                "query": query,
                "organism": organism,
                "results": results,
                "count": len(results),
            },
        }

    def _get_attributes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get attributes/properties for an identifier."""
        identifier = arguments.get("identifier")
        source = arguments.get("source")
        organism = arguments.get("organism", "Human")

        if not identifier or not source:
            return {
                "status": "error",
                "error": "Both 'identifier' and 'source' parameters are required",
            }

        system_code = self._resolve_system_code(source)
        url = "{}/{}/attributes/{}/{}".format(
            BRIDGEDB_BASE_URL, organism, system_code, identifier
        )

        response = self.session.get(url, timeout=self.timeout)
        if response.status_code not in (200, 204):
            return {
                "status": "error",
                "error": "BridgeDb returned status {}".format(response.status_code),
            }

        if response.status_code == 204 or not response.text.strip():
            return {
                "status": "success",
                "data": {
                    "query_identifier": identifier,
                    "query_source": source,
                    "organism": organism,
                    "attributes": {},
                },
            }

        attributes = self._parse_tsv_attributes(response.text)
        return {
            "status": "success",
            "data": {
                "query_identifier": identifier,
                "query_source": source,
                "organism": organism,
                "attributes": attributes,
            },
        }
