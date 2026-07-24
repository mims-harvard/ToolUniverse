# reactome_analysis_tool.py
"""
Reactome Analysis Service tool for ToolUniverse.

The Reactome Analysis Service provides pathway overrepresentation analysis,
expression data analysis, and species comparison for gene/protein lists.
This is separate from the Reactome Content Service (already in ToolUniverse).

API: https://reactome.org/AnalysisService
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ANALYSIS_BASE_URL = "https://reactome.org/AnalysisService"


@register_tool("ReactomeAnalysisTool")
class ReactomeAnalysisTool(BaseTool):
    """
    Tool for Reactome pathway analysis (enrichment/overrepresentation).

    Accepts gene/protein identifiers and performs overrepresentation
    analysis or species comparison against Reactome pathways. Returns
    enriched pathways with p-values, FDR, and entity counts.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "pathway_enrichment")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Reactome Analysis API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Reactome Analysis request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Reactome Analysis Service.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Reactome Analysis HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate analysis endpoint."""
        if self.endpoint == "pathway_enrichment":
            return self._pathway_enrichment(arguments)
        elif self.endpoint == "species_comparison":
            return self._species_comparison(arguments)
        elif self.endpoint == "token_result":
            return self._token_result(arguments)
        elif self.endpoint == "expression_analysis":
            return self._expression_analysis(arguments)
        elif self.endpoint == "species_comparison_v2":
            return self._species_comparison_v2(arguments)
        elif self.endpoint == "found_entities":
            return self._found_entities(arguments)
        elif self.endpoint == "not_found_identifiers":
            return self._not_found_identifiers(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _pathway_enrichment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform pathway overrepresentation analysis."""
        identifiers = arguments.get("identifiers", "")
        if not identifiers:
            return {
                "status": "error",
                "error": "identifiers parameter required (newline-separated gene/protein IDs)",
            }

        # Ensure identifiers is newline-separated
        if isinstance(identifiers, list):
            identifiers = "\n".join(identifiers)

        page_size = arguments.get("page_size", 20)
        include_disease = arguments.get("include_disease", True)
        projection = arguments.get("projection", True)

        url = (
            f"{ANALYSIS_BASE_URL}/identifiers/projection"
            if projection
            else f"{ANALYSIS_BASE_URL}/identifiers/"
        )
        params = {
            "pageSize": min(page_size, 50),
            "page": 1,
            "includeDisease": str(include_disease).lower(),
        }

        response = requests.post(
            url,
            data=identifiers,
            headers={"Content-Type": "text/plain"},
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        return self._format_analysis_result(data, identifiers)

    def _species_comparison(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform species comparison analysis."""
        identifiers = arguments.get("identifiers", "")
        if not identifiers:
            return {
                "status": "error",
                "error": "identifiers parameter required (newline-separated gene/protein IDs)",
            }

        if isinstance(identifiers, list):
            identifiers = "\n".join(identifiers)

        arguments.get("species", 9606)
        page_size = arguments.get("page_size", 20)

        url = f"{ANALYSIS_BASE_URL}/identifiers/projection"
        params = {
            "pageSize": min(page_size, 50),
            "page": 1,
        }

        response = requests.post(
            url,
            data=identifiers,
            headers={"Content-Type": "text/plain"},
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        return self._format_analysis_result(data, identifiers)

    def _token_result(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve analysis results by token."""
        token = arguments.get("token", "")
        if not token:
            return {"status": "error", "error": "token parameter is required"}

        page_size = arguments.get("page_size", 20)

        url = f"{ANALYSIS_BASE_URL}/token/{token}"
        params = {
            "pageSize": min(page_size, 50),
            "page": 1,
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return self._format_analysis_result(data, "")

    def _expression_analysis(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Quantitative expression analysis (type=EXPRESSION).

        Maps numeric expression / fold-change values onto Reactome pathways.
        Submit tab-delimited 'GENE\\tVALUE' lines so Reactome treats the input
        as an expression matrix and overlays the values per pathway.
        """
        identifiers = arguments.get("identifiers", "")
        if not identifiers:
            return {
                "status": "error",
                "error": (
                    "identifiers parameter required: tab-delimited 'GENE\\tVALUE' "
                    "lines, one per row (e.g. 'PTEN\\t2.5\\nTP53\\t-1.8')."
                ),
            }
        if isinstance(identifiers, list):
            identifiers = "\n".join(identifiers)

        page_size = arguments.get("page_size", 20)
        include_disease = arguments.get("include_disease", True)
        projection = arguments.get("projection", False)

        url = (
            f"{ANALYSIS_BASE_URL}/identifiers/projection"
            if projection
            else f"{ANALYSIS_BASE_URL}/identifiers/"
        )
        params = {
            "pageSize": min(page_size, 50),
            "page": 1,
            "includeDisease": str(include_disease).lower(),
        }

        response = requests.post(
            url,
            data=identifiers,
            headers={"Content-Type": "text/plain"},
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        return self._format_analysis_result(data, identifiers, include_expression=True)

    def _species_comparison_v2(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """True cross-species comparison (type=SPECIES_COMPARISON).

        Calls the genuine /species/{source}/{target} endpoint, which compares
        a source species' pathways against a target species by orthology.
        """
        species = arguments.get("species")
        if species in (None, ""):
            return {
                "status": "error",
                "error": (
                    "species parameter required: Reactome dbId of the species to "
                    "compare against the source (e.g. 48892 for Mus musculus)."
                ),
            }

        source = arguments.get("source_species", "homoSapiens")
        page_size = arguments.get("page_size", 20)

        url = f"{ANALYSIS_BASE_URL}/species/{source}/{species}"
        params = {
            "pageSize": min(page_size, 50),
            "page": 1,
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return self._format_analysis_result(data, "")

    def _found_entities(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Per-pathway found-entities drill-down.

        For an analysis token + a hit pathway, returns exactly which submitted
        identifiers matched and their Reactome cross-references (mapsTo).
        """
        token = arguments.get("token", "")
        pathway = arguments.get("pathway", "")
        if not token:
            return {"status": "error", "error": "token parameter is required"}
        if not pathway:
            return {
                "status": "error",
                "error": "pathway parameter is required (e.g. 'R-HSA-3700989')",
            }

        resource = arguments.get("resource", "TOTAL")
        url = f"{ANALYSIS_BASE_URL}/token/{token}/found/entities/{pathway}"
        params = {"resource": resource}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        identifiers = []
        for ent in data.get("identifiers", []):
            maps_to = []
            for m in ent.get("mapsTo", []):
                maps_to.append(
                    {
                        "resource": m.get("resource"),
                        "ids": m.get("ids", []),
                    }
                )
            identifiers.append(
                {
                    "id": ent.get("id"),
                    "exp": ent.get("exp", []),
                    "mapsTo": maps_to,
                }
            )

        return {
            "status": "success",
            "data": {
                "pathway": pathway,
                "found": data.get("found", len(identifiers)),
                "total_entities_count": data.get("totalEntitiesCount"),
                "resources": data.get("resources", []),
                "identifiers": identifiers,
            },
            "metadata": {
                "source": "Reactome Analysis Service",
                "token": token,
                "returned": len(identifiers),
            },
        }

    def _not_found_identifiers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List submitted identifiers that did NOT map to any Reactome entity."""
        token = arguments.get("token", "")
        if not token:
            return {"status": "error", "error": "token parameter is required"}

        url = f"{ANALYSIS_BASE_URL}/token/{token}/notFound"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        not_found = []
        if isinstance(data, list):
            for ent in data:
                if isinstance(ent, dict):
                    not_found.append(ent.get("id"))
                else:
                    not_found.append(ent)

        return {
            "status": "success",
            "data": {
                "token": token,
                "not_found_count": len(not_found),
                "not_found": not_found,
            },
            "metadata": {
                "source": "Reactome Analysis Service",
                "token": token,
                "returned": len(not_found),
            },
        }

    def _format_analysis_result(
        self, data: Dict, identifiers: str, include_expression: bool = False
    ) -> Dict[str, Any]:
        """Format analysis result into standard output."""
        summary = data.get("summary", {})
        pathways_raw = data.get("pathways", [])

        pathways = []
        for pw in pathways_raw:
            entities = pw.get("entities", {})
            reactions = pw.get("reactions", {})
            species = pw.get("species", {})

            pathway_entry = {
                "pathway_id": pw.get("stId"),
                "name": pw.get("name"),
                "species": species.get("name"),
                "is_disease": pw.get("inDisease", False),
                "is_lowest_level": pw.get("llp", False),
                "entities_found": entities.get("found"),
                "entities_total": entities.get("total"),
                "entities_ratio": entities.get("ratio"),
                "p_value": entities.get("pValue"),
                "fdr": entities.get("fdr"),
                "reactions_found": reactions.get("found"),
                "reactions_total": reactions.get("total"),
            }
            if include_expression:
                pathway_entry["entities_exp"] = entities.get("exp")
            pathways.append(pathway_entry)

        result_data = {
            "token": summary.get("token"),
            "analysis_type": summary.get("type"),
            "projection": summary.get("projection"),
            "identifiers_not_found": data.get("identifiersNotFound", 0),
            "pathways_found": data.get("pathwaysFound", 0),
            "pathways": pathways,
        }
        if include_expression:
            expression = data.get("expression") or {}
            result_data["expression_column_names"] = expression.get("columnNames", [])
            result_data["expression_min"] = expression.get("min")
            result_data["expression_max"] = expression.get("max")

        return {
            "status": "success",
            "data": result_data,
            "metadata": {
                "source": "Reactome Analysis Service",
                "total_pathways": data.get("pathwaysFound", 0),
                "returned": len(pathways),
            },
        }
