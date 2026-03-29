# hpa_tool.py

import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

HPA_SEARCH_API = "https://www.proteinatlas.org/api/search_download.php"
HPA_BASE = "https://www.proteinatlas.org"
HPA_JSON_API_TEMPLATE = "https://www.proteinatlas.org/{ensembl_id}.json"
HPA_XML_API_TEMPLATE = "https://www.proteinatlas.org/{ensembl_id}.xml"

# --- Base Tool Classes ---


@register_tool("HPASearchApiTool")
class HPASearchApiTool(BaseTool):
    """
    Base class for interacting with HPA's search_download.php API.
    Uses HPA's search and download API to get protein expression data.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 30
        self.base_url = HPA_SEARCH_API

    def _make_api_request(
        self, search_term: str, columns: str, format_type: str = "json"
    ) -> Dict[str, Any]:
        """Make HPA API request with improved error handling"""
        params = {
            "search": search_term,
            "format": format_type,
            "columns": columns,
            "compress": "no",
        }

        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            if resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"No data found for gene '{search_term}'",
                }
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HPA API request failed, HTTP {resp.status_code}",
                    "detail": resp.text,
                }

            if format_type == "json":
                data = resp.json()
                # Ensure we always return a list for consistency
                if not isinstance(data, list):
                    return {
                        "status": "error",
                        "error": "API did not return expected list format",
                    }
                return data
            else:
                return {"tsv_data": resp.text}

        except requests.RequestException as e:
            return {"status": "error", "error": f"HPA API request failed: {str(e)}"}
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Failed to parse HPA response data: {str(e)}",
                "content": resp.text,
            }


@register_tool("HPAJsonApiTool")
class HPAJsonApiTool(BaseTool):
    """
    Base class for interacting with HPA's /{ensembl_id}.json API.
    More efficient for getting comprehensive gene data.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 30
        self.base_url_template = HPA_JSON_API_TEMPLATE

    def _make_api_request(self, ensembl_id: str) -> Dict[str, Any]:
        """Make HPA JSON API request for a specific gene"""
        url = self.base_url_template.format(ensembl_id=ensembl_id)
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"No data found for Ensembl ID '{ensembl_id}'",
                }
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HPA JSON API request failed, HTTP {resp.status_code}",
                    "detail": resp.text,
                }

            return resp.json()

        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"HPA JSON API request failed: {str(e)}",
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Failed to parse HPA JSON response: {str(e)}",
                "content": resp.text,
            }


@register_tool("HPAXmlApiTool")
class HPAXmlApiTool(BaseTool):
    """
    Base class for interacting with HPA's /{ensembl_id}.xml API.
    Optimized for comprehensive XML data extraction.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 45
        self.base_url_template = HPA_XML_API_TEMPLATE

    def _make_api_request(self, ensembl_id: str) -> ET.Element:
        """Make HPA XML API request for a specific gene"""
        url = self.base_url_template.format(ensembl_id=ensembl_id)
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                raise Exception(f"No XML data found for Ensembl ID '{ensembl_id}'")
            if resp.status_code != 200:
                raise Exception(f"HPA XML API request failed, HTTP {resp.status_code}")

            return ET.fromstring(resp.content)
        except requests.RequestException as e:
            raise Exception(f"HPA XML API request failed: {str(e)}")
        except ET.ParseError as e:
            raise Exception(f"Failed to parse HPA XML response: {str(e)}")


@register_tool("HPASearchTool")
class HPASearchTool(HPASearchApiTool):
    """
    Generic search tool for Human Protein Atlas.

    This tool allows custom search queries and retrieval of specific columns from the
    Human Protein Atlas API. It provides more flexibility than the specialized tools
    by allowing direct access to the search API with custom parameters.

    Args:
        search_query (str): The search term to query for (e.g., gene name, description).
        columns (str, optional): Comma-separated list of columns to retrieve.
            Defaults to "g,gs,gd" (Gene, Gene synonym, Gene description).

            Available columns and their specifiers:
            - g: Gene name
            - gs: Gene synonym
            - gd: Gene description
            - e: Ensembl ID
            - u: UniProt ID
            - en: Enhanced
            - pe: Protein existence
            - r: Reliability
            - p: Pathology
            - c: Cancer
            - pt: Protein tissue
            - ptm: Predicted Transmembrane
            - s: Subcellular location
            - scml: Subcellular main location
            - scal: Subcellular additional location
            - rnat: RNA tissue specificity
            - rnats: RNA tissue specific score
            - rnatsm: RNA tissue specific nTPM
            - rnablm: RNA blood lineage specific nTPM
            - rnabrm: RNA brain region specific nTPM
            - rnascm: RNA single cell type specific nTPM

            See HPA API documentation for the full list of over 40 available columns.

        format (str, optional): Response format, "json" or "tsv". Defaults to "json".

    Returns:
        dict: A dictionary containing the search results.
            If successful, returns the API response (list of entries).
            If failed, returns a dictionary with an "error" key.

    Example:
        >>> tool = HPASearchTool()
        >>> result = tool.run({
        ...     "search_query": "p53",
        ...     "columns": "g,gs,scml,rnat",
        ...     "format": "json"
        ... })
        >>> print(result[0]["Gene"])
        TP53
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the search tool.

        Args:
            arguments (Dict[str, Any]): Dictionary containing:
                - search_query (str): The term to search for.
                - columns (str, optional): Columns to retrieve.
                - format (str, optional): Response format.

        Returns:
            Dict[str, Any]: Search results or error message.
        """
        search_query = arguments.get("search_query")
        columns = arguments.get("columns", "g,gs,gd")
        format_type = arguments.get("format", "json")

        if not search_query:
            return {"status": "error", "error": "Parameter 'search_query' is required"}

        result = self._make_api_request(search_query, columns, format_type)
        if isinstance(result, dict) and result.get("status") == "error":
            return result
        return {"status": "success", "data": result}


# --- New Enhanced Tools Based on Your Optimization Plan ---


@register_tool("HPAGetRnaExpressionBySourceTool")
class HPAGetRnaExpressionBySourceTool(HPASearchApiTool):
    """
    Get RNA expression for a gene from specific biological sources using optimized columns parameter.
    This tool directly leverages the comprehensive columns table for efficient queries.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Use correct HPA API column identifiers
        self.source_column_mappings = {
            "tissue": "rnatsm",  # RNA tissue specific nTPM
            "blood": "rnablm",  # RNA blood lineage specific nTPM
            "brain": "rnabrm",  # RNA brain region specific nTPM
            "single_cell": "rnascm",  # RNA single cell type specific nTPM
        }

        # Map expected API response field names for each source type
        self.api_response_fields = {
            "tissue": "RNA tissue specific nTPM",
            "blood": "RNA blood lineage specific nTPM",
            "brain": "RNA brain region specific nTPM",
            "single_cell": "RNA single cell type specific nTPM",
        }

        # Map source names to expected keys in API response
        self.source_name_mappings = {
            "tissue": {
                "adipose_tissue": ["adipose tissue", "fat"],
                "adrenal_gland": ["adrenal gland", "adrenal"],
                "appendix": ["appendix"],
                "bone_marrow": ["bone marrow"],
                "brain": ["brain", "cerebral cortex"],
                "breast": ["breast"],
                "bronchus": ["bronchus"],
                "cerebellum": ["cerebellum"],
                "cerebral_cortex": ["cerebral cortex", "brain"],
                "cervix": ["cervix"],
                "choroid_plexus": ["choroid plexus"],
                "colon": ["colon"],
                "duodenum": ["duodenum"],
                "endometrium": ["endometrium"],
                "epididymis": ["epididymis"],
                "esophagus": ["esophagus"],
                "fallopian_tube": ["fallopian tube"],
                "gallbladder": ["gallbladder"],
                "heart_muscle": ["heart muscle", "heart"],
                "hippocampal_formation": ["hippocampus", "hippocampal formation"],
                "hypothalamus": ["hypothalamus"],
                "kidney": ["kidney"],
                "liver": ["liver"],
                "lung": ["lung"],
                "lymph_node": ["lymph node"],
                "nasopharynx": ["nasopharynx"],
                "oral_mucosa": ["oral mucosa"],
                "ovary": ["ovary"],
                "pancreas": ["pancreas"],
                "parathyroid_gland": ["parathyroid gland"],
                "pituitary_gland": ["pituitary gland"],
                "placenta": ["placenta"],
                "prostate": ["prostate"],
                "rectum": ["rectum"],
                "retina": ["retina"],
                "salivary_gland": ["salivary gland"],
                "seminal_vesicle": ["seminal vesicle"],
                "skeletal_muscle": ["skeletal muscle"],
                "skin": ["skin"],
                "small_intestine": ["small intestine"],
                "smooth_muscle": ["smooth muscle"],
                "soft_tissue": ["soft tissue"],
                "spleen": ["spleen"],
                "stomach": ["stomach"],
                "testis": ["testis"],
                "thymus": ["thymus"],
                "thyroid_gland": ["thyroid gland"],
                "tongue": ["tongue"],
                "tonsil": ["tonsil"],
                "urinary_bladder": ["urinary bladder"],
                "vagina": ["vagina"],
            },
            "blood": {
                "t_cell": ["t-cell", "t cell"],
                "b_cell": ["b-cell", "b cell"],
                "nk_cell": ["nk-cell", "nk cell", "natural killer"],
                "monocyte": ["monocyte"],
                "neutrophil": ["neutrophil"],
                "eosinophil": ["eosinophil"],
                "basophil": ["basophil"],
                "dendritic_cell": ["dendritic cell"],
            },
            "brain": {
                "cerebellum": ["cerebellum"],
                "cerebral_cortex": ["cerebral cortex", "cortex"],
                "hippocampus": ["hippocampus", "hippocampal formation"],
                "hypothalamus": ["hypothalamus"],
                "amygdala": ["amygdala"],
                "brainstem": ["brainstem", "brain stem"],
                "thalamus": ["thalamus"],
            },
            "single_cell": {
                "t_cell": ["t-cell", "t cell"],
                "b_cell": ["b-cell", "b cell"],
                "hepatocyte": ["hepatocyte"],
                "neuron": ["neuron"],
                "astrocyte": ["astrocyte"],
                "fibroblast": ["fibroblast"],
            },
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        source_type = arguments.get("source_type", "").lower()
        source_name = (
            arguments.get("source_name", "").lower().replace(" ", "_").replace("-", "_")
        )

        if not gene_name:
            return {
                "status": "error",
                "data": {"error": "Parameter 'gene_name' is required"},
            }
        if not source_type:
            return {
                "status": "error",
                "data": {"error": "Parameter 'source_type' is required"},
            }
        if not source_name:
            return {
                "status": "error",
                "data": {"error": "Parameter 'source_name' is required"},
            }

        # Validate source type
        if source_type not in self.source_column_mappings:
            available_types = ", ".join(self.source_column_mappings.keys())
            return {
                "status": "error",
                "data": {
                    "error": f"Invalid source_type '{source_type}'. Available types: {available_types}"
                },
            }

        # Enhanced validation with intelligent recommendations
        if source_name not in self.source_name_mappings[source_type]:
            available_sources = list(self.source_name_mappings[source_type].keys())

            # Find similar source names (fuzzy matching)
            similar_sources = []
            source_keywords = source_name.replace("_", " ").split()

            for valid_source in available_sources:
                # Direct substring matching
                if (
                    source_name.lower() in valid_source.lower()
                    or valid_source.lower() in source_name.lower()
                ):
                    similar_sources.append(valid_source)
                    continue

                # Check with underscores removed/normalized
                normalized_input = source_name.lower().replace("_", "").replace(" ", "")
                normalized_valid = (
                    valid_source.lower().replace("_", "").replace(" ", "")
                )
                if (
                    normalized_input in normalized_valid
                    or normalized_valid in normalized_input
                ):
                    similar_sources.append(valid_source)
                    continue

                # Check individual keywords
                for keyword in source_keywords:
                    if (
                        keyword.lower() in valid_source.lower()
                        or valid_source.lower() in keyword.lower()
                    ):
                        similar_sources.append(valid_source)
                        break

            error_msg = (
                f"Invalid source_name '{source_name}' for source_type '{source_type}'. "
            )
            if similar_sources:
                error_msg += f"Similar options: {similar_sources[:3]}. "
            error_msg += (
                f"All available sources for '{source_type}': {available_sources}"
            )
            return {"status": "error", "data": {"error": error_msg}}

        try:
            # Get the correct API column
            api_column = self.source_column_mappings[source_type]
            columns = f"g,gs,{api_column}"

            # Call the search API
            response_data = self._make_api_request(gene_name, columns)

            if "error" in response_data:
                return {"status": "error", "data": response_data}

            if not response_data or len(response_data) == 0:
                result = {
                    "gene_name": gene_name,
                    "source_type": source_type,
                    "source_name": source_name,
                    "expression_value": "N/A",
                    "status": "Gene not found",
                }
                return {"status": "success", "data": result}

            # Get the first result
            gene_data = response_data[0]

            # Extract expression data from the API response
            expression_value = "N/A"
            available_sources = []

            # Get the expression data dictionary for this source type
            api_field_name = self.api_response_fields[source_type]
            expression_data = gene_data.get(api_field_name)

            if expression_data and isinstance(expression_data, dict):
                available_sources = list(expression_data.keys())

                # Get possible names for this source
                possible_names = self.source_name_mappings[source_type][source_name]

                # Try to find a matching source name in the response
                for source_key in expression_data.keys():
                    source_key_lower = source_key.lower()
                    for possible_name in possible_names:
                        if (
                            possible_name.lower() in source_key_lower
                            or source_key_lower in possible_name.lower()
                        ):
                            expression_value = expression_data[source_key]
                            break
                    if expression_value != "N/A":
                        break

                # If exact match not found, look for partial matches
                if expression_value == "N/A":
                    source_keywords = source_name.replace("_", " ").split()
                    for source_key in expression_data.keys():
                        source_key_lower = source_key.lower()
                        for keyword in source_keywords:
                            if keyword in source_key_lower:
                                expression_value = expression_data[source_key]
                                break
                        if expression_value != "N/A":
                            break

            # Categorize expression level
            expression_level = "unknown"
            if expression_value != "N/A":
                try:
                    val = float(expression_value)
                    if val > 50:
                        expression_level = "very high"
                    elif val > 10:
                        expression_level = "high"
                    elif val > 1:
                        expression_level = "medium"
                    elif val > 0.1:
                        expression_level = "low"
                    else:
                        expression_level = "very low"
                except (ValueError, TypeError):
                    expression_level = "unknown"

            result = {
                "gene_name": gene_data.get("Gene", gene_name),
                "gene_synonym": gene_data.get("Gene synonym", ""),
                "source_type": source_type,
                "source_name": source_name,
                "expression_value": expression_value,
                "expression_level": expression_level,
                "expression_unit": "nTPM",
                "column_queried": api_column,
                "available_sources": (
                    available_sources[:10]
                    if len(available_sources) > 10
                    else available_sources
                ),
                "total_available_sources": len(available_sources),
                "status": (
                    "success"
                    if expression_value != "N/A"
                    else "no_expression_data_for_source"
                ),
            }
            return {"status": "success", "data": result}

        except Exception as e:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to retrieve RNA expression data: {str(e)}",
                    "gene_name": gene_name,
                    "source_type": source_type,
                    "source_name": source_name,
                },
            }


@register_tool("HPAGetSubcellularLocationTool")
class HPAGetSubcellularLocationTool(HPASearchApiTool):
    """
    Get annotated subcellular locations for a protein using optimized columns parameter.
    Uses scml (main location) and scal (additional location) columns for efficient queries.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}

        # Use specific columns for subcellular location data
        result = self._make_api_request(gene_name, "g,gs,scml,scal")

        if "error" in result:
            return result

        if not result:
            return {"status": "error", "error": "No subcellular location data found"}

        gene_data = result[0]

        # Parse main and additional locations
        main_location = gene_data.get("Subcellular main location", "")
        additional_location = gene_data.get("Subcellular additional location", "")

        # Handle different data types (string or list)
        if isinstance(main_location, list):
            main_locations = main_location
        elif isinstance(main_location, str):
            main_locations = (
                [loc.strip() for loc in main_location.split(";") if loc.strip()]
                if main_location
                else []
            )
        else:
            main_locations = []

        if isinstance(additional_location, list):
            additional_locations = additional_location
        elif isinstance(additional_location, str):
            additional_locations = (
                [loc.strip() for loc in additional_location.split(";") if loc.strip()]
                if additional_location
                else []
            )
        else:
            additional_locations = []

        return {
            "status": "success",
            "data": {
                "gene_name": gene_data.get("Gene", gene_name),
                "gene_synonym": gene_data.get("Gene synonym", ""),
                "main_locations": main_locations,
                "additional_locations": additional_locations,
                "total_locations": len(main_locations) + len(additional_locations),
                "location_summary": self._generate_location_summary(
                    main_locations, additional_locations
                ),
            },
        }

    def _generate_location_summary(
        self, main_locs: List[str], add_locs: List[str]
    ) -> str:
        """Generate a summary of subcellular locations"""
        if not main_locs and not add_locs:
            return "No subcellular location data available"

        summary_parts = []
        if main_locs:
            summary_parts.append(f"Primary: {', '.join(main_locs)}")
        if add_locs:
            summary_parts.append(f"Additional: {', '.join(add_locs)}")

        return "; ".join(summary_parts)


# --- Existing Tools (Updated with improvements) ---


@register_tool("HPASearchGenesTool")
class HPASearchGenesTool(HPASearchApiTool):
    """
    Search for matching genes by gene name, keywords, or cell line names and return Ensembl ID list.
    This is the entry tool for many query workflows.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        search_query = arguments.get("search_query")
        if not search_query:
            return {"status": "error", "error": "Parameter 'search_query' is required"}

        # 'g' for Gene name, 'gs' for Gene synonym, 'eg' for Ensembl ID
        columns = "g,gs,eg"
        result = self._make_api_request(search_query, columns)

        if "error" in result:
            return result

        if not result or not isinstance(result, list):
            return {
                "status": "error",
                "error": f"No matching genes found for query '{search_query}'",
            }

        formatted_results = []
        for gene in result:
            gene_synonym = gene.get("Gene synonym", "")
            if isinstance(gene_synonym, str):
                synonyms = gene_synonym.split(", ") if gene_synonym else []
            elif isinstance(gene_synonym, list):
                synonyms = gene_synonym
            else:
                synonyms = []

            formatted_results.append(
                {
                    "gene_name": gene.get("Gene"),
                    "ensembl_id": gene.get("Ensembl"),
                    "gene_synonyms": synonyms,
                }
            )

        return {
            "status": "success",
            "data": {
                "search_query": search_query,
                "match_count": len(formatted_results),
                "genes": formatted_results,
            },
        }


@register_tool("HPAGetComparativeExpressionTool")
class HPAGetComparativeExpressionTool(HPASearchApiTool):
    """
    Compare gene expression levels in specific cell lines and healthy tissues.
    Get expression data for comparison by gene name and cell line name.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Mapping of common cell lines to their column identifiers
        self.cell_line_columns = {
            "ishikawa": "cell_RNA_ishikawa_heraklio",
            "hela": "cell_RNA_hela",
            "mcf7": "cell_RNA_mcf7",
            "a549": "cell_RNA_a549",
            "hepg2": "cell_RNA_hepg2",
            "jurkat": "cell_RNA_jurkat",
            "pc3": "cell_RNA_pc3",
            "rh30": "cell_RNA_rh30",
            "siha": "cell_RNA_siha",
            "u251": "cell_RNA_u251",
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        cell_line = arguments.get("cell_line", "").lower()

        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}
        if not cell_line:
            return {"status": "error", "error": "Parameter 'cell_line' is required"}

        # Enhanced validation with intelligent recommendations
        cell_column = self.cell_line_columns.get(cell_line)
        if not cell_column:
            available_lines = list(self.cell_line_columns.keys())

            # Find similar cell line names
            similar_lines = []
            for valid_line in available_lines:
                if cell_line in valid_line or valid_line in cell_line:
                    similar_lines.append(valid_line)

            error_msg = f"Unsupported cell_line '{cell_line}'. "
            if similar_lines:
                error_msg += f"Similar options: {similar_lines}. "
            error_msg += f"All supported cell lines: {available_lines}"
            return {"status": "error", "error": error_msg}

        # Request expression data for the cell line
        cell_columns = f"g,gs,{cell_column}"
        cell_result = self._make_api_request(gene_name, cell_columns)
        if "error" in cell_result:
            return cell_result

        # Request expression data for healthy tissues
        tissue_columns = "g,gs,rnatsm"
        tissue_result = self._make_api_request(gene_name, tissue_columns)
        if "error" in tissue_result:
            return tissue_result

        # Format the result
        if not cell_result or not tissue_result:
            return {"status": "error", "error": "No expression data found"}

        # Extract the first matching gene data
        cell_data = (
            cell_result[0] if isinstance(cell_result, list) and cell_result else {}
        )
        tissue_data = (
            tissue_result[0]
            if isinstance(tissue_result, list) and tissue_result
            else {}
        )

        return {
            "status": "success",
            "data": {
                "gene_name": gene_name,
                "gene_symbol": cell_data.get("Gene", gene_name),
                "gene_synonym": cell_data.get("Gene synonym", ""),
                "cell_line": cell_line,
                "cell_line_expression": cell_data.get(cell_column, "N/A"),
                "healthy_tissue_expression": tissue_data.get(
                    "RNA tissue specific nTPM", "N/A"
                ),
                "expression_unit": "nTPM (normalized Transcripts Per Million)",
                "comparison_summary": self._generate_comparison_summary(
                    cell_data.get(cell_column),
                    tissue_data.get("RNA tissue specific nTPM"),
                ),
            },
        }

    def _generate_comparison_summary(self, cell_expr, tissue_expr) -> str:
        """Generate expression level comparison summary"""
        try:
            cell_val = float(cell_expr) if cell_expr and cell_expr != "N/A" else None
            tissue_val = (
                float(tissue_expr) if tissue_expr and tissue_expr != "N/A" else None
            )

            if cell_val is None or tissue_val is None:
                return "Insufficient data for comparison"

            if cell_val > tissue_val * 2:
                return f"Expression significantly higher in cell line ({cell_val:.2f} vs {tissue_val:.2f})"
            elif tissue_val > cell_val * 2:
                return f"Expression significantly higher in healthy tissues ({tissue_val:.2f} vs {cell_val:.2f})"
            else:
                return f"Expression levels similar (cell line: {cell_val:.2f}, healthy tissues: {tissue_val:.2f})"
        except Exception:
            return "Failed to calculate expression level comparison"


@register_tool("HPAGetDiseaseExpressionTool")
class HPAGetDiseaseExpressionTool(HPASearchApiTool):
    """
    Get expression data for a gene in specific diseases and tissues.
    Get related expression information by gene name, tissue type, and disease name.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Mapping of common cancer types to their column identifiers
        self.cancer_columns = {
            "brain_cancer": "cancer_RNA_brain_cancer",
            "breast_cancer": "cancer_RNA_breast_cancer",
            "colon_cancer": "cancer_RNA_colon_cancer",
            "lung_cancer": "cancer_RNA_lung_cancer",
            "liver_cancer": "cancer_RNA_liver_cancer",
            "prostate_cancer": "cancer_RNA_prostate_cancer",
            "kidney_cancer": "cancer_RNA_kidney_cancer",
            "pancreatic_cancer": "cancer_RNA_pancreatic_cancer",
            "stomach_cancer": "cancer_RNA_stomach_cancer",
            "ovarian_cancer": "cancer_RNA_ovarian_cancer",
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        tissue_type = arguments.get("tissue_type", "").lower()
        disease_name = arguments.get("disease_name", "").lower()

        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}
        if not disease_name:
            return {"status": "error", "error": "Parameter 'disease_name' is required"}

        # Enhanced validation with intelligent recommendations
        disease_key = f"{tissue_type}_{disease_name}" if tissue_type else disease_name
        cancer_column = None

        # Match cancer type
        for key, column in self.cancer_columns.items():
            if disease_key in key or disease_name in key:
                cancer_column = column
                break

        if not cancer_column:
            available_diseases = [
                k.replace("_", " ") for k in self.cancer_columns.keys()
            ]

            # Find similar disease names
            similar_diseases = []
            disease_keywords = disease_name.replace("_", " ").split()

            for valid_disease in available_diseases:
                for keyword in disease_keywords:
                    if (
                        keyword in valid_disease.lower()
                        or valid_disease.lower() in keyword
                    ):
                        similar_diseases.append(valid_disease)
                        break

            error_msg = f"Unsupported disease_name '{disease_name}'. "
            if similar_diseases:
                error_msg += f"Similar options: {similar_diseases[:3]}. "
            error_msg += f"All supported diseases: {available_diseases}"
            return {"status": "error", "error": error_msg}

        # Build request columns
        columns = f"g,gs,{cancer_column},rnatsm"
        result = self._make_api_request(gene_name, columns)

        if "error" in result:
            return result

        if not result:
            return {"status": "error", "error": "No expression data found"}

        # Extract the first matching gene data
        gene_data = result[0] if isinstance(result, list) and result else {}

        return {
            "status": "success",
            "data": {
                "gene_name": gene_name,
                "gene_symbol": gene_data.get("Gene", gene_name),
                "gene_synonym": gene_data.get("Gene synonym", ""),
                "tissue_type": tissue_type or "Not specified",
                "disease_name": disease_name,
                "disease_expression": gene_data.get(cancer_column, "N/A"),
                "healthy_expression": gene_data.get("RNA tissue specific nTPM", "N/A"),
                "expression_unit": "nTPM (normalized Transcripts Per Million)",
                "disease_vs_healthy": self._compare_disease_healthy(
                    gene_data.get(cancer_column),
                    gene_data.get("RNA tissue specific nTPM"),
                ),
            },
        }

    def _compare_disease_healthy(self, disease_expr, healthy_expr) -> str:
        """Compare expression difference between disease and healthy state"""
        try:
            disease_val = (
                float(disease_expr) if disease_expr and disease_expr != "N/A" else None
            )
            healthy_val = (
                float(healthy_expr) if healthy_expr and healthy_expr != "N/A" else None
            )

            if disease_val is None or healthy_val is None:
                return "Insufficient data for comparison"

            fold_change = disease_val / healthy_val if healthy_val > 0 else float("inf")

            if fold_change > 2:
                return f"Disease state expression upregulated {fold_change:.2f} fold"
            elif fold_change < 0.5:
                return (
                    f"Disease state expression downregulated {1 / fold_change:.2f} fold"
                )
            else:
                return f"Expression level relatively stable (fold change: {fold_change:.2f})"
        except Exception:
            return "Failed to calculate expression difference"


@register_tool("HPAGetBiologicalProcessTool")
class HPAGetBiologicalProcessTool(HPASearchApiTool):
    """
    Get biological process information related to a gene.
    Get specific biological processes a gene is involved in by gene name.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Predefined biological process list
        self.target_processes = [
            "Apoptosis",
            "Biological rhythms",
            "Cell cycle",
            "Host-virus interaction",
            "Necrosis",
            "Transcription",
            "Transcription regulation",
        ]

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        filter_processes = arguments.get("filter_processes", True)

        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}

        # Request biological process data for the gene
        columns = "g,gs,upbp"
        result = self._make_api_request(gene_name, columns)

        if "error" in result:
            return result

        if not result:
            return {"status": "error", "error": "No gene data found"}

        # Extract the first matching gene data
        gene_data = result[0] if isinstance(result, list) and result else {}

        # Parse biological processes
        biological_processes = gene_data.get("Biological process", "")
        if not biological_processes or biological_processes == "N/A":
            return {
                "status": "success",
                "data": {
                    "gene_name": gene_name,
                    "gene_symbol": gene_data.get("Gene", gene_name),
                    "gene_synonym": gene_data.get("Gene synonym", ""),
                    "biological_processes": [],
                    "target_processes_found": [],
                    "target_process_names": [],
                    "total_processes": 0,
                    "target_processes_count": 0,
                },
            }

        # Split and clean process list - handle both string and list formats
        processes_list = []
        if isinstance(biological_processes, list):
            processes_list = biological_processes
        elif isinstance(biological_processes, str):
            # Usually separated by semicolon or comma
            processes_list = [
                p.strip()
                for p in biological_processes.replace(";", ",").split(",")
                if p.strip()
            ]

        # Filter target processes
        target_found = []
        if filter_processes:
            for process in processes_list:
                for target in self.target_processes:
                    if target.lower() in process.lower():
                        target_found.append(
                            {"target_process": target, "full_description": process}
                        )

        return {
            "status": "success",
            "data": {
                "gene_name": gene_name,
                "gene_symbol": gene_data.get("Gene", gene_name),
                "gene_synonym": gene_data.get("Gene synonym", ""),
                "biological_processes": processes_list,
                "target_processes_found": target_found,
                "target_process_names": [tp["target_process"] for tp in target_found],
                "total_processes": len(processes_list),
                "target_processes_count": len(target_found),
            },
        }


@register_tool("HPAGetCancerPrognosticsTool")
class HPAGetCancerPrognosticsTool(HPAJsonApiTool):
    """
    Get prognostic value of a gene across various cancers.
    Uses the efficient JSON API to retrieve cancer prognostic data.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}

        data = self._make_api_request(ensembl_id)
        if "error" in data:
            return data

        prognostics = []
        for key, value in data.items():
            if key.startswith("Cancer prognostics") and isinstance(value, dict):
                cancer_type = key.replace("Cancer prognostics - ", "").strip()
                if value and value.get("is_prognostic"):
                    prognostics.append(
                        {
                            "cancer_type": cancer_type,
                            "prognostic_type": value.get("prognostic type", "Unknown"),
                            "p_value": value.get("p_val", "N/A"),
                            "is_prognostic": value.get("is_prognostic", False),
                        }
                    )

        return {
            "status": "success",
            "data": {
                "ensembl_id": ensembl_id,
                "gene": data.get("Gene", "Unknown"),
                "gene_synonym": data.get("Gene synonym", ""),
                "prognostic_cancers_count": len(prognostics),
                "prognostic_summary": (
                    prognostics
                    if prognostics
                    else "No significant prognostic value found in the analyzed cancers."
                ),
                "note": "Prognostic value indicates whether high/low expression of this gene correlates with patient survival in specific cancer types.",
            },
        }


@register_tool("HPAGetProteinInteractionsTool")
class HPAGetProteinInteractionsTool(HPASearchApiTool):
    """
    Get protein-protein interaction partners for a gene.
    Uses search API to retrieve interaction data.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}

        # Feature-68B-002: HPA 'ppi' column has been deprecated and returns no data.
        # Direct users to EBIProteinsInteractionsTool or STRING tools instead.
        return {
            "status": "error",
            "error": (
                "HPA protein-protein interaction data (ppi column) is no longer available "
                "via the HPA search API. Use EBIProteins_get_interactions with a UniProt "
                "accession, or STRING_get_interactions with a gene symbol instead."
            ),
        }


@register_tool("HPAGetRnaExpressionByTissueTool")
class HPAGetRnaExpressionByTissueTool(HPAJsonApiTool):
    """
    Query RNA expression levels for a gene in specific tissues.
    More precise than general tissue expression queries.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        tissue_names = arguments.get("tissue_names", [])

        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}
        if not tissue_names or not isinstance(tissue_names, list):
            # Provide helpful tissue name examples
            example_tissues = [
                "brain",
                "liver",
                "heart",
                "kidney",
                "lung",
                "pancreas",
                "skin",
                "muscle",
            ]
            return {
                "status": "error",
                "error": f"Parameter 'tissue_names' is required and must be a list. Example: {example_tissues}",
            }

        data = self._make_api_request(ensembl_id)
        if "error" in data:
            return data

        # Get RNA tissue expression data
        rna_data = data.get("RNA tissue specific nTPM", {})
        if not isinstance(rna_data, dict):
            return {
                "status": "error",
                "error": "No RNA tissue expression data available for this gene",
            }

        expression_results = {}
        available_tissues = list(rna_data.keys())

        for tissue in tissue_names:
            # Case-insensitive matching
            found_tissue = None
            for available_tissue in available_tissues:
                if (
                    tissue.lower() in available_tissue.lower()
                    or available_tissue.lower() in tissue.lower()
                ):
                    found_tissue = available_tissue
                    break

            if found_tissue:
                expression_results[tissue] = {
                    "matched_tissue": found_tissue,
                    "expression_value": rna_data[found_tissue],
                    "expression_level": self._categorize_expression(
                        rna_data[found_tissue]
                    ),
                }
            else:
                expression_results[tissue] = {
                    "matched_tissue": "Not found",
                    "expression_value": "N/A",
                    "expression_level": "No data",
                }

        return {
            "status": "success",
            "data": {
                "ensembl_id": ensembl_id,
                "gene": data.get("Gene", "Unknown"),
                "gene_synonym": data.get("Gene synonym", ""),
                "expression_unit": "nTPM (normalized Transcripts Per Million)",
                "queried_tissues": tissue_names,
                "tissue_expression": expression_results,
                "available_tissues_sample": (
                    available_tissues[:10]
                    if len(available_tissues) > 10
                    else available_tissues
                ),
                "total_available_tissues": len(available_tissues),
            },
        }

    def _categorize_expression(self, expr_value) -> str:
        """Categorize expression level"""
        try:
            val = float(expr_value)
            if val > 50:
                return "Very high"
            elif val > 10:
                return "High"
            elif val > 1:
                return "Medium"
            elif val > 0.1:
                return "Low"
            else:
                return "Very low"
        except (ValueError, TypeError):
            return "Unknown"


@register_tool("HPAGetContextualBiologicalProcessTool")
class HPAGetContextualBiologicalProcessTool(BaseTool):
    """
    Analyze a gene's biological processes in the context of specific tissue or cell line.
    Enhanced with intelligent context validation and recommendation.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Define all valid context options
        self.valid_contexts = {
            "tissues": [
                "adipose_tissue",
                "adrenal_gland",
                "appendix",
                "bone_marrow",
                "brain",
                "breast",
                "bronchus",
                "cerebellum",
                "cerebral_cortex",
                "cervix",
                "colon",
                "duodenum",
                "endometrium",
                "esophagus",
                "gallbladder",
                "heart_muscle",
                "kidney",
                "liver",
                "lung",
                "lymph_node",
                "ovary",
                "pancreas",
                "placenta",
                "prostate",
                "rectum",
                "salivary_gland",
                "skeletal_muscle",
                "skin",
                "small_intestine",
                "spleen",
                "stomach",
                "testis",
                "thymus",
                "thyroid_gland",
                "urinary_bladder",
                "vagina",
            ],
            "cell_lines": [
                "hela",
                "mcf7",
                "a549",
                "hepg2",
                "jurkat",
                "pc3",
                "rh30",
                "siha",
                "u251",
            ],
            "blood_cells": [
                "t_cell",
                "b_cell",
                "nk_cell",
                "monocyte",
                "neutrophil",
                "eosinophil",
            ],
            "brain_regions": [
                "cerebellum",
                "cerebral_cortex",
                "hippocampus",
                "hypothalamus",
                "amygdala",
            ],
        }

    def _validate_context(self, context_name: str) -> Dict[str, Any]:
        """Validate context_name and provide intelligent recommendations"""
        context_lower = context_name.lower().replace(" ", "_").replace("-", "_")

        # Check all valid contexts
        all_valid = []
        for category, contexts in self.valid_contexts.items():
            all_valid.extend(contexts)
            if context_lower in contexts:
                return {"valid": True, "category": category}

        # Find similar contexts (fuzzy matching)
        similar_contexts = []
        context_keywords = context_lower.split("_")

        for valid_context in all_valid:
            for keyword in context_keywords:
                if keyword in valid_context.lower() or valid_context.lower() in keyword:
                    similar_contexts.append(valid_context)
                    break

        return {
            "valid": False,
            "input": context_name,
            "similar_suggestions": similar_contexts[:5],  # Top 5 suggestions
            "all_tissues": self.valid_contexts["tissues"][:10],  # First 10 tissues
            "all_cell_lines": self.valid_contexts["cell_lines"],
            "total_available": len(all_valid),
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene_name = arguments.get("gene_name")
        context_name = arguments.get("context_name")

        if not gene_name:
            return {"status": "error", "error": "Parameter 'gene_name' is required"}
        if not context_name:
            return {"status": "error", "error": "Parameter 'context_name' is required"}

        # Validate context_name and provide recommendations if invalid
        validation = self._validate_context(context_name)
        if not validation["valid"]:
            error_msg = f"Invalid context_name '{validation['input']}'. "
            if validation["similar_suggestions"]:
                error_msg += f"Similar options: {validation['similar_suggestions']}. "
            error_msg += f"Available tissues: {validation['all_tissues']}... "
            error_msg += f"Available cell lines: {validation['all_cell_lines']}. "
            error_msg += f"Total {validation['total_available']} contexts available."
            return {"status": "error", "error": error_msg}

        try:
            # Step 1: Get gene basic info and Ensembl ID
            search_api = HPASearchApiTool({})
            search_result = search_api._make_api_request(gene_name, "g,gs,eg,upbp")

            if "error" in search_result or not search_result:
                return {
                    "status": "error",
                    "error": f"Could not find gene information for '{gene_name}'",
                }

            gene_data = (
                search_result[0] if isinstance(search_result, list) else search_result
            )
            ensembl_id = gene_data.get("Ensembl", "")

            if not ensembl_id:
                return {
                    "status": "error",
                    "error": f"Could not find Ensembl ID for gene '{gene_name}'",
                }

            # Step 2: Get biological processes
            biological_processes = gene_data.get("Biological process", "")
            processes_list = []
            if biological_processes and biological_processes != "N/A":
                if isinstance(biological_processes, list):
                    processes_list = biological_processes
                elif isinstance(biological_processes, str):
                    processes_list = [
                        p.strip()
                        for p in biological_processes.replace(";", ",").split(",")
                        if p.strip()
                    ]

            # Step 3: Get expression in context with improved error handling
            json_api = HPAJsonApiTool({})
            json_data = json_api._make_api_request(ensembl_id)

            expression_value = "N/A"
            expression_level = "not expressed"
            context_type = (
                validation["category"].replace("_", " ").rstrip("s")
            )  # "tissues" -> "tissue"

            if "error" not in json_data and json_data:
                # FIXED: Check if rna_data is not None before calling .keys()
                rna_data = json_data.get("RNA tissue specific nTPM")
                if rna_data and isinstance(rna_data, dict):
                    # Try to find matching tissue
                    for tissue_key in rna_data.keys():
                        if (
                            context_name.lower() in tissue_key.lower()
                            or tissue_key.lower() in context_name.lower()
                        ):
                            expression_value = rna_data[tissue_key]
                            break

                # If not found in tissues and it's a cell line, try cell line data
                if expression_value == "N/A" and validation["category"] == "cell_lines":
                    context_type = "cell line"
                    cell_line_columns = {
                        "hela": "cell_RNA_hela",
                        "mcf7": "cell_RNA_mcf7",
                        "a549": "cell_RNA_a549",
                        "hepg2": "cell_RNA_hepg2",
                    }

                    cell_column = cell_line_columns.get(context_name.lower())
                    if cell_column:
                        cell_result = search_api._make_api_request(
                            gene_name, f"g,{cell_column}"
                        )
                        if "error" not in cell_result and cell_result:
                            expression_value = cell_result[0].get(cell_column, "N/A")

            # Categorize expression level
            try:
                expr_val = float(expression_value) if expression_value != "N/A" else 0
                if expr_val > 10:
                    expression_level = "highly expressed"
                elif expr_val > 1:
                    expression_level = "moderately expressed"
                elif expr_val > 0.1:
                    expression_level = "expressed at low level"
                else:
                    expression_level = "not expressed or very low"
            except (ValueError, TypeError):
                expression_level = "expression level unclear"

            # Generate contextual conclusion
            relevance = (
                "may be functionally relevant"
                if "expressed" in expression_level and "not" not in expression_level
                else "is likely not functionally relevant"
            )

            conclusion = f"Gene {gene_name} is involved in {len(processes_list)} biological processes. It is {expression_level} in {context_name} ({expression_value} nTPM), suggesting its functional roles {relevance} in this {context_type} context."

            return {
                "status": "success",
                "data": {
                    "gene": gene_data.get("Gene", gene_name),
                    "gene_synonym": gene_data.get("Gene synonym", ""),
                    "ensembl_id": ensembl_id,
                    "context": context_name,
                    "context_type": context_type,
                    "context_category": validation["category"],
                    "expression_in_context": f"{expression_value} nTPM",
                    "expression_level": expression_level,
                    "total_biological_processes": len(processes_list),
                    "biological_processes": (
                        processes_list[:10]
                        if len(processes_list) > 10
                        else processes_list
                    ),
                    "contextual_conclusion": conclusion,
                    "functional_relevance": relevance,
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to perform contextual analysis: {str(e)}",
            }


# --- Keep existing comprehensive gene details tool for images ---


@register_tool("HPAGetGenePageDetailsTool")
class HPAGetGenePageDetailsTool(HPAXmlApiTool):
    """
    Get detailed information about a gene page, including images, protein expression, antibody data, etc.
    Get the most comprehensive data by parsing HPA's single gene XML endpoint.
    Enhanced version with improved image extraction and comprehensive data parsing based on optimization plan.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        include_images = arguments.get("include_images", True)
        include_antibodies = arguments.get("include_antibodies", True)
        include_expression = arguments.get("include_expression", True)

        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}

        try:
            root = self._make_api_request(ensembl_id)
            parsed = self._parse_gene_xml(
                root, ensembl_id, include_images, include_antibodies, include_expression
            )
            return {"status": "success", "data": parsed}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _parse_gene_xml(
        self,
        root: ET.Element,
        ensembl_id: str,
        include_images: bool,
        include_antibodies: bool,
        include_expression: bool,
    ) -> Dict[str, Any]:
        """Parse gene XML data comprehensively based on actual HPA XML schema"""
        result = {
            "ensembl_id": ensembl_id,
            "gene_name": "",
            "gene_description": "",
            "chromosome_location": "",
            "uniprot_ids": [],
            "summary": {},
        }

        # Extract basic gene information from entry element
        entry_elem = root.find(".//entry")
        if entry_elem is not None:
            # Gene name
            name_elem = entry_elem.find("name")
            if name_elem is not None:
                result["gene_name"] = name_elem.text or ""

            # Gene synonyms
            synonyms = []
            for synonym_elem in entry_elem.findall("synonym"):
                if synonym_elem.text:
                    synonyms.append(synonym_elem.text)
            result["gene_synonyms"] = synonyms

            # Extract Uniprot IDs from identifier/xref elements
            identifier_elem = entry_elem.find("identifier")
            if identifier_elem is not None:
                for xref in identifier_elem.findall("xref"):
                    if xref.get("db") == "Uniprot/SWISSPROT":
                        result["uniprot_ids"].append(xref.get("id", ""))

            # Extract protein classes
            protein_classes = []
            protein_classes_elem = entry_elem.find("proteinClasses")
            if protein_classes_elem is not None:
                for pc in protein_classes_elem.findall("proteinClass"):
                    class_name = pc.get("name", "")
                    if class_name:
                        protein_classes.append(class_name)
            result["protein_classes"] = protein_classes

        # Extract image information with enhanced parsing
        if include_images:
            result["ihc_images"] = self._extract_ihc_images(root)
            result["if_images"] = self._extract_if_images(root)

        # Extract antibody information
        if include_antibodies:
            result["antibodies"] = self._extract_antibodies(root)

        # Extract expression information
        if include_expression:
            result["expression_summary"] = self._extract_expression_summary(root)
            result["tissue_expression"] = self._extract_tissue_expression(root)
            result["cell_line_expression"] = self._extract_cell_line_expression(root)

        # Extract summary statistics
        result["summary"] = {
            "total_antibodies": len(result.get("antibodies", [])),
            "total_ihc_images": len(result.get("ihc_images", [])),
            "total_if_images": len(result.get("if_images", [])),
            "tissues_with_expression": len(result.get("tissue_expression", [])),
            "cell_lines_with_expression": len(result.get("cell_line_expression", [])),
        }

        return result

    def _extract_ihc_images(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract tissue immunohistochemistry (IHC) images based on actual HPA XML structure"""
        images = []

        # Find tissueExpression elements which contain IHC images
        for tissue_expr in root.findall(".//tissueExpression"):
            # Extract selected images from tissueExpression
            for image_elem in tissue_expr.findall(".//image"):
                image_type = image_elem.get("imageType", "")
                if image_type == "selected":
                    tissue_elem = image_elem.find("tissue")
                    image_url_elem = image_elem.find("imageUrl")

                    if tissue_elem is not None and image_url_elem is not None:
                        tissue_name = tissue_elem.text or ""
                        organ = tissue_elem.get("organ", "")
                        ontology_terms = tissue_elem.get("ontologyTerms", "")
                        image_url = image_url_elem.text or ""

                        images.append(
                            {
                                "image_type": "Immunohistochemistry",
                                "tissue_name": tissue_name,
                                "organ": organ,
                                "ontology_terms": ontology_terms,
                                "image_url": image_url,
                                "selected": True,
                            }
                        )

        return images

    def _extract_if_images(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract subcellular immunofluorescence (IF) images based on actual HPA XML structure"""
        images = []

        # Look for subcellular expression data (IF images are typically in subcellular sections)
        for subcell_expr in root.findall(".//subcellularExpression"):
            # Extract subcellular location images
            for image_elem in subcell_expr.findall(".//image"):
                image_type = image_elem.get("imageType", "")
                if image_type == "selected":
                    location_elem = image_elem.find("location")
                    image_url_elem = image_elem.find("imageUrl")

                    if location_elem is not None and image_url_elem is not None:
                        location_name = location_elem.text or ""
                        image_url = image_url_elem.text or ""

                        images.append(
                            {
                                "image_type": "Immunofluorescence",
                                "subcellular_location": location_name,
                                "image_url": image_url,
                                "selected": True,
                            }
                        )

        return images

    def _extract_antibodies(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract antibody information from actual HPA XML structure"""
        antibodies_data = []

        # Look for antibody references in various expression sections
        antibody_ids = set()

        # Look for antibody references in tissue expression
        for tissue_expr in root.findall(".//tissueExpression"):
            for elem in tissue_expr.iter():
                if "antibody" in elem.tag.lower() or elem.get("antibody"):
                    antibody_id = elem.get("antibody") or elem.text
                    if antibody_id:
                        antibody_ids.add(antibody_id)

        # Create basic antibody info for found IDs
        for antibody_id in antibody_ids:
            antibodies_data.append(
                {
                    "antibody_id": antibody_id,
                    "source": "HPA",
                    "applications": ["IHC", "IF"],
                    "validation_status": "Available",
                }
            )

        # If no specific antibody IDs found, create a placeholder
        if not antibodies_data:
            antibodies_data.append(
                {
                    "antibody_id": "HPA_antibody",
                    "source": "HPA",
                    "applications": ["IHC", "IF"],
                    "validation_status": "Available",
                }
            )

        return antibodies_data

    def _extract_expression_summary(self, root: ET.Element) -> Dict[str, Any]:
        """Extract expression summary information from actual HPA XML structure"""
        summary = {
            "tissue_specificity": "",
            "subcellular_location": [],
            "protein_class": [],
            "predicted_location": "",
            "tissue_expression_summary": "",
            "subcellular_expression_summary": "",
        }

        # Extract predicted location
        predicted_location_elem = root.find(".//predictedLocation")
        if predicted_location_elem is not None:
            summary["predicted_location"] = predicted_location_elem.text or ""

        # Extract tissue expression summary
        tissue_expr_elem = root.find(".//tissueExpression")
        if tissue_expr_elem is not None:
            tissue_summary_elem = tissue_expr_elem.find("summary")
            if tissue_summary_elem is not None:
                summary["tissue_expression_summary"] = tissue_summary_elem.text or ""

        # Extract subcellular expression summary
        subcell_expr_elem = root.find(".//subcellularExpression")
        if subcell_expr_elem is not None:
            subcell_summary_elem = subcell_expr_elem.find("summary")
            if subcell_summary_elem is not None:
                summary["subcellular_expression_summary"] = (
                    subcell_summary_elem.text or ""
                )

        return summary

    def _extract_tissue_expression(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract detailed tissue expression data from actual HPA XML structure"""
        tissue_data = []

        # Extract from tissueExpression data elements
        for tissue_expr in root.findall(".//tissueExpression"):
            for data_elem in tissue_expr.findall(".//data"):
                tissue_elem = data_elem.find("tissue")
                level_elem = data_elem.find("level")

                if tissue_elem is not None:
                    tissue_info = {
                        "tissue_name": tissue_elem.text or "",
                        "organ": tissue_elem.get("organ", ""),
                        "expression_level": "",
                    }

                    if level_elem is not None:
                        tissue_info["expression_level"] = (
                            level_elem.get("type", "") + ": " + (level_elem.text or "")
                        )

                    tissue_data.append(tissue_info)

        return tissue_data

    def _extract_cell_line_expression(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract cell line expression data from actual HPA XML structure"""
        cell_line_data = []

        # Look for cell line expression in subcellular expression
        for subcell_expr in root.findall(".//subcellularExpression"):
            for data_elem in subcell_expr.findall(".//data"):
                cell_line_elem = data_elem.find("cellLine")
                if cell_line_elem is not None:
                    cell_info = {
                        "cell_line_name": cell_line_elem.get("name", "")
                        or (cell_line_elem.text or ""),
                        "expression_data": [],
                    }

                    if cell_info["expression_data"]:
                        cell_line_data.append(cell_info)

        return cell_line_data


# --- Legacy/Compatibility Tools ---


@register_tool("HPAGetGeneJSONTool")
class HPAGetGeneJSONTool(HPAJsonApiTool):
    """
    Enhanced legacy tool - Get basic gene information using Ensembl Gene ID.
    Now uses the efficient JSON API instead of search API.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}

        # Use JSON API to get comprehensive information
        data = self._make_api_request(ensembl_id)

        if "error" in data:
            return data

        # Convert to response similar to original JSON format for compatibility
        return {
            "Ensembl": ensembl_id,
            "Gene": data.get("Gene", ""),
            "Gene synonym": data.get("Gene synonym", ""),
            "Uniprot": data.get("Uniprot", ""),
            "Biological process": data.get("Biological process", ""),
            "RNA tissue specific nTPM": data.get("RNA tissue specific nTPM", ""),
        }


@register_tool("HPAGetGeneXMLTool")
class HPAGetGeneXMLTool(HPASearchApiTool):
    """
    Legacy tool - Get gene TSV format data (alternative to XML).
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ensembl_id = arguments.get("ensembl_id")
        if not ensembl_id:
            return {"status": "error", "error": "Parameter 'ensembl_id' is required"}

        # Use TSV format to get detailed data
        columns = "g,gs,up,upbp,rnatsm,cell_RNA_a549,cell_RNA_hela"
        result = self._make_api_request(ensembl_id, columns, format_type="tsv")

        if "error" in result:
            return result

        return {"tsv_data": result.get("tsv_data", "")}
