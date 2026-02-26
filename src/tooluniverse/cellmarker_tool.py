"""
CellMarker 2.0 Tool

Provides access to the CellMarker 2.0 database for querying curated
cell type marker genes from single-cell RNA-seq and experimental studies.

CellMarker 2.0 is a comprehensive database of cell type markers curated
from >26,000 publications, covering >500 cell types across >400 tissue types
for human and mouse. Data sources include single-cell sequencing, experiments,
reviews, and commercial antibody panels.

Website: http://bio-bigdata.hrbmu.edu.cn/CellMarker/
No authentication required.

Reference: Hu et al., Nucleic Acids Research, 2023 (PMID: 36300619)
"""

import re
import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


CELLMARKER_BASE_URL = "http://bio-bigdata.hrbmu.edu.cn/CellMarker"


def _parse_html_table_rows(html: str) -> List[Dict[str, str]]:
    """Parse HTML table rows from CellMarker JSP response.

    CellMarker returns data as HTML table rows with columns:
    Species | Tissue Class | Tissue Type | Cancer/Normal | Cell Name | Cell Marker | Source | Supports
    """
    results = []
    # Match all table rows with data
    row_pattern = re.compile(r"<tr><td>(.*?)</tr>", re.DOTALL)
    for match in row_pattern.finditer(html):
        row_html = match.group(1)
        # Extract cell contents - handle cells with nested HTML
        cells = re.findall(r"<td>(.*?)</td>", "<td>" + row_html, re.DOTALL)
        if len(cells) >= 6:
            # Extract source from nested HTML (e.g., <p class='noplay'>Experiment</p><img...>)
            source_raw = cells[6] if len(cells) > 6 else ""
            source_match = re.search(r"class='noplay'>(.*?)</p>", source_raw)
            source = source_match.group(1) if source_match else source_raw.strip()

            # Extract support count
            supports = cells[7].strip() if len(cells) > 7 else "0"

            record = {
                "species": cells[0].strip(),
                "tissue_class": cells[1].strip(),
                "tissue_type": cells[2].strip(),
                "cell_type": cells[3].strip(),  # "Normal cell" or "Cancer cell"
                "cell_name": cells[4].strip(),
                "cell_marker": cells[5].strip(),
                "source": source,
                "supports": int(supports) if supports.isdigit() else 0,
            }
            results.append(record)
    return results


def _parse_cell_type_list(js_text: str) -> List[Dict[str, str]]:
    """Parse the JavaScript cell type list from CONTROL endpoint.

    CONTROL returns pseudo-JSON like:
    [{id:0,tissuet:"none",tissuec:"X",pId:0,name:"Y",namein:"Z",...},...]
    """
    results = []
    # Extract name values from the JS object array
    name_pattern = re.compile(r'namein:"(.*?)"')
    tissuec_pattern = re.compile(r'tissuec:"(.*?)"')

    names = name_pattern.findall(js_text)
    tissues = tissuec_pattern.findall(js_text)

    for i, name in enumerate(names):
        if name == "ALL":
            continue
        tissue = tissues[i] if i < len(tissues) else ""
        results.append(
            {
                "cell_name": name,
                "tissue_class": tissue,
            }
        )
    return results


@register_tool("CellMarkerTool")
class CellMarkerTool(BaseTool):
    """
    Tool for querying the CellMarker 2.0 cell type marker database.

    CellMarker 2.0 provides curated marker genes for hundreds of cell types
    across tissues in human and mouse, sourced from single-cell RNA-seq
    studies, experiments, reviews, and commercial antibody panels.

    Supported operations:
    - search_by_gene: Find cell types that express a given marker gene
    - search_by_cell_type: Find marker genes for a specific cell type
    - list_cell_types: List available cell types in a tissue
    - search_cancer_markers: Search cancer-specific cell markers
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CellMarker tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "search_by_gene": self._search_by_gene,
            "search_by_cell_type": self._search_by_cell_type,
            "list_cell_types": self._list_cell_types,
            "search_cancer_markers": self._search_cancer_markers,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}".format(operation),
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "CellMarker request timed out"}
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Could not connect to CellMarker server",
            }
        except Exception as e:
            return {"status": "error", "error": "CellMarker error: {}".format(str(e))}

    def _search_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find cell types that express a given marker gene.

        Uses Marker_table.jsp with POST: markerSpecies + markerMarker params.
        Returns HTML table rows parsed into structured data.
        """
        gene_symbol = arguments.get("gene_symbol")
        if not gene_symbol:
            return {
                "status": "error",
                "error": "Missing required parameter: gene_symbol",
            }

        species = arguments.get("species", "")
        tissue_type = arguments.get("tissue_type")

        # Map species to API format
        species_map = {
            "Human": "human",
            "Mouse": "mouse",
            "human": "human",
            "mouse": "mouse",
        }
        api_species = species_map.get(species, species.lower() if species else "")

        url = "{}/Marker_table.jsp".format(CELLMARKER_BASE_URL)
        data = {
            "markerSpecies": api_species,
            "markerMarker": gene_symbol,
        }

        resp = self.session.post(url, data=data, timeout=self.timeout)
        resp.raise_for_status()

        records = _parse_html_table_rows(resp.text)

        # Filter by tissue_type if specified
        if tissue_type:
            tissue_lower = tissue_type.lower()
            records = [
                r
                for r in records
                if tissue_lower in r["tissue_type"].lower()
                or tissue_lower in r["tissue_class"].lower()
            ]

        # Deduplicate and summarize by cell type
        return {
            "status": "success",
            "data": {
                "gene_symbol": gene_symbol,
                "species": species if species else "all",
                "total_records": len(records),
                "records": records[:200],  # Limit to 200 records
            },
        }

    def _search_by_cell_type(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find marker genes for a specific cell type.

        Uses Marker_table.jsp with quickkeyword + quick_v=yes for general search,
        then filters results to match the target cell type.
        """
        cell_name = arguments.get("cell_name")
        if not cell_name:
            return {"status": "error", "error": "Missing required parameter: cell_name"}

        species = arguments.get("species")
        tissue_type = arguments.get("tissue_type")

        # Use quick search which searches across cell names, markers, and tissues
        url = "{}/Marker_table.jsp".format(CELLMARKER_BASE_URL)
        params = {
            "quickkeyword": cell_name,
            "quick_v": "yes",
        }

        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()

        records = _parse_html_table_rows(resp.text)

        # Filter to records matching the cell name
        cell_lower = cell_name.lower()
        filtered = [r for r in records if cell_lower in r["cell_name"].lower()]

        # Apply species filter
        if species:
            species_lower = species.lower()
            filtered = [r for r in filtered if r["species"].lower() == species_lower]

        # Apply tissue filter
        if tissue_type:
            tissue_lower = tissue_type.lower()
            filtered = [
                r
                for r in filtered
                if tissue_lower in r["tissue_type"].lower()
                or tissue_lower in r["tissue_class"].lower()
            ]

        # Extract unique marker genes
        marker_genes = sorted(set(r["cell_marker"] for r in filtered))

        return {
            "status": "success",
            "data": {
                "cell_name": cell_name,
                "species": species if species else "all",
                "total_records": len(filtered),
                "unique_markers": len(marker_genes),
                "marker_genes": marker_genes[:500],  # Limit list
                "records": filtered[:200],
            },
        }

    def _list_cell_types(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available cell types in a tissue.

        Uses the CONTROL endpoint which returns a JavaScript array of cell types
        for a given tissue and species combination.
        """
        tissue_type = arguments.get("tissue_type", "")
        species = arguments.get("species", "Human")
        cell_class = arguments.get("cell_class")

        # Map species to API format
        species_map = {
            "Human": "human",
            "Mouse": "mouse",
            "human": "human",
            "mouse": "mouse",
        }
        api_species = species_map.get(species, species.lower() if species else "human")

        # Determine cancer type filter
        cancer_type = "all"  # "all" for normal+cancer, "cancer" for cancer only
        if cell_class and cell_class.lower() == "cancer":
            cancer_type = "cancer"

        url = "{}/CONTROL".format(CELLMARKER_BASE_URL)
        params = {
            "spcies": api_species,
            "cancertype": cancer_type,
            "tissuet": tissue_type,
            "tissuec": tissue_type,
        }

        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()

        cell_types = _parse_cell_type_list(resp.text)

        return {
            "status": "success",
            "data": {
                "species": species,
                "tissue_type": tissue_type if tissue_type else "all",
                "total_cell_types": len(cell_types),
                "cell_types": cell_types,
            },
        }

    def _search_cancer_markers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search cancer-specific cell markers.

        Searches for markers in cancer cell contexts. Can filter by:
        - cancer_type (tissue where cancer occurs, e.g., "Breast", "Lung")
        - gene_symbol (specific marker gene)
        - cell_type (specific cancer cell type)

        Uses Marker_table.jsp with markerSpecies/markerMarker for gene-based search,
        or quickkeyword search for cell type / cancer type searches.
        """
        cancer_type = arguments.get("cancer_type")
        gene_symbol = arguments.get("gene_symbol")
        cell_type = arguments.get("cell_type")

        if not any([cancer_type, gene_symbol, cell_type]):
            return {
                "status": "error",
                "error": "At least one parameter required: cancer_type, gene_symbol, or cell_type",
            }

        records = []

        if gene_symbol:
            # Search by gene, then filter to cancer records
            url = "{}/Marker_table.jsp".format(CELLMARKER_BASE_URL)
            data = {
                "markerSpecies": "human",
                "markerMarker": gene_symbol,
            }
            resp = self.session.post(url, data=data, timeout=self.timeout)
            resp.raise_for_status()
            records = _parse_html_table_rows(resp.text)
        elif cell_type:
            # Search by cell type name
            url = "{}/Marker_table.jsp".format(CELLMARKER_BASE_URL)
            params = {"quickkeyword": cell_type, "quick_v": "yes"}
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            records = _parse_html_table_rows(resp.text)
        elif cancer_type:
            # Search by cancer tissue type
            url = "{}/Marker_table.jsp".format(CELLMARKER_BASE_URL)
            params = {"quickkeyword": cancer_type, "quick_v": "yes"}
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            records = _parse_html_table_rows(resp.text)

        # Filter to cancer records only
        cancer_records = [r for r in records if r["cell_type"] == "Cancer cell"]

        # Apply additional filters
        if cancer_type:
            cancer_lower = cancer_type.lower()
            cancer_records = [
                r
                for r in cancer_records
                if cancer_lower in r["tissue_type"].lower()
                or cancer_lower in r["tissue_class"].lower()
            ]

        if cell_type and gene_symbol:
            # If both provided, also filter by cell type name
            cell_lower = cell_type.lower()
            cancer_records = [
                r for r in cancer_records if cell_lower in r["cell_name"].lower()
            ]

        if gene_symbol and cancer_type:
            # Already filtered by gene, also filter by cancer tissue
            pass  # cancer_type filter already applied above

        # Build query summary, omitting None values
        query = {}
        if cancer_type:
            query["cancer_type"] = cancer_type
        if gene_symbol:
            query["gene_symbol"] = gene_symbol
        if cell_type:
            query["cell_type"] = cell_type

        return {
            "status": "success",
            "data": {
                "query": query,
                "total_records": len(cancer_records),
                "records": cancer_records[:200],
            },
        }
