"""
GEO Database REST API Tool

This tool provides access to gene expression data from the GEO database.
GEO is a public repository that archives and freely distributes microarray,
next-generation sequencing, and other forms of high-throughput functional
genomics data.
"""

from typing import Dict, Any, List
from .ncbi_eutils_tool import NCBIEUtilsTool
from .tool_registry import register_tool


@register_tool("GEORESTTool")
class GEORESTTool(NCBIEUtilsTool):
    """
    GEO Database REST API tool with rate limiting.
    Generic wrapper for GEO API endpoints defined in expression_tools.json.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        parameter = tool_config.get("parameter", {})

        self.endpoint_template: str = fields.get("endpoint", "/esearch.fcgi")
        self.required: List[str] = parameter.get("required", [])
        self.output_format: str = fields.get("return_format", "JSON")

    def _build_url(self, arguments: Dict[str, Any]) -> str | Dict[str, Any]:
        """Build URL for GEO API request."""
        url_path = self.endpoint_template
        return self.base_url + url_path

    def _build_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for GEO API request."""
        params = {"db": "gds", "retmode": "json", "retmax": 50}

        # Build search query
        query_parts = []
        if "query" in arguments:
            query_parts.append(arguments["query"])

        if "organism" in arguments:
            organism = arguments["organism"]
            if organism.lower() == "homo sapiens":
                query_parts.append("Homo sapiens[organism]")
            elif organism.lower() == "mus musculus":
                query_parts.append("Mus musculus[organism]")
            else:
                query_parts.append(f'"{organism}"[organism]')

        if "study_type" in arguments:
            study_type = arguments["study_type"]
            query_parts.append(f'"{study_type}"[study_type]')

        if "platform" in arguments:
            platform = arguments["platform"]
            query_parts.append(f'"{platform}"[platform]')

        if "date_range" in arguments:
            date_range = arguments["date_range"]
            if ":" in date_range:
                start_year, end_year = date_range.split(":")
                query_parts.append(f'"{start_year}"[PDAT] : "{end_year}"[PDAT]')

        if query_parts:
            params["term"] = " AND ".join(query_parts)

        if "limit" in arguments:
            params["retmax"] = min(arguments["limit"], 500)

        if "sort" in arguments:
            sort = arguments["sort"]
            if sort == "date":
                params["sort"] = "relevance"
            elif sort == "title":
                params["sort"] = "title"
            else:
                params["sort"] = "relevance"

        return params

    def _detect_database(self, dataset_id: str) -> str:
        """
        Return the appropriate NCBI GEO database name.

        For NCBI E-utilities, GEO records (GDS, GSE, GSM, GPL) are all accessed
        through the single `gds` database. The accession prefix (GDS/GSE/GSM)
        is used in the search term, not as the database name.
        """
        return "gds"

    def _accession_to_uid(self, dataset_id: str, db: str) -> Dict[str, Any]:
        """Convert accession number (e.g. GSE/GDS/GSM) to numeric UID using esearch."""
        search_params = {
            "db": db,
            # Use ACCN field which is the documented field for accessions in GDS
            # See: https://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ESearch
            "term": f"{dataset_id}[ACCN]",
            "retmode": "json",
            "retmax": 1,
        }
        return self._make_request("/esearch.fcgi", search_params)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        # Validate required parameters
        for param in self.required:
            if param not in arguments:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {param}",
                }

        # Set endpoint for the base class
        self.endpoint = self.endpoint_template
        params = self._build_params(arguments)

        # Use the parent class's _make_request with rate limiting
        return self._make_request(self.endpoint, params)


@register_tool("GEOSearchDatasets")
class GEOSearchDatasets(GEORESTTool):
    """Search GEO datasets by various criteria."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint_template = "/esearch.fcgi"

    def _build_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for GEO dataset search."""
        params = {"db": "gds", "retmode": "json", "retmax": 50}

        # Build search query
        query_parts = []
        if "query" in arguments:
            query_parts.append(arguments["query"])

        if "organism" in arguments:
            organism = arguments["organism"]
            query_parts.append(f'"{organism}"[organism]')

        if "study_type" in arguments:
            study_type = arguments["study_type"]
            query_parts.append(f'"{study_type}"[study_type]')

        if "platform" in arguments:
            platform = arguments["platform"]
            query_parts.append(f'"{platform}"[platform]')

        if query_parts:
            params["term"] = " AND ".join(query_parts)

        if "limit" in arguments:
            params["retmax"] = min(arguments["limit"], 500)

        return params


@register_tool("GEOGetDatasetInfo")
class GEOGetDatasetInfo(GEORESTTool):
    """Get detailed information about a specific GEO dataset."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint_template = "/esummary.fcgi"

    def _build_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for GEO dataset info retrieval."""
        dataset_id = arguments.get("dataset_id", "")
        if not dataset_id:
            return {"status": "error", "error": "dataset_id is required"}

        # Detect database type
        db = self._detect_database(dataset_id)

        # Check if dataset_id is already a numeric UID
        if dataset_id.isdigit():
            return {"db": db, "id": dataset_id, "retmode": "json"}

        # For accession numbers, we need to convert to UID first
        # This will be handled in the run method
        return {"db": db, "id": dataset_id, "retmode": "json"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        # Validate required parameters
        for param in self.required:
            if param not in arguments:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {param}",
                }

        dataset_id = arguments.get("dataset_id", "")
        if not dataset_id:
            return {"status": "error", "error": "dataset_id is required"}

        # Detect database type
        db = self._detect_database(dataset_id)

        # Check if dataset_id is already a numeric UID
        if dataset_id.isdigit():
            # Direct UID, use esummary directly
            self.endpoint = self.endpoint_template
            params = {"db": db, "id": dataset_id, "retmode": "json"}
            return self._make_request(self.endpoint, params)

        # For accession numbers, first convert to UID using esearch
        search_result = self._accession_to_uid(dataset_id, db)

        if search_result.get("status") != "success":
            return search_result

        search_data = search_result.get("data", {})
        esearch_result = search_data.get("esearchresult", {})
        idlist = esearch_result.get("idlist", [])

        if not idlist:
            return {
                "status": "error",
                "error": f"No UID found for accession {dataset_id} in database {db}",
                "data": search_data,
            }

        # Use the first UID from the search results
        uid = idlist[0]

        # Now use esummary with the UID
        self.endpoint = self.endpoint_template
        params = {"db": db, "id": uid, "retmode": "json"}
        return self._make_request(self.endpoint, params)


@register_tool("GEOGetSampleInfo")
class GEOGetSampleInfo(GEORESTTool):
    """Get sample information for a GEO dataset."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint_template = "/esummary.fcgi"

    def _build_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for GEO sample info retrieval."""
        dataset_id = arguments.get("dataset_id", "")
        if not dataset_id:
            return {"status": "error", "error": "dataset_id is required"}

        # Detect database type
        db = self._detect_database(dataset_id)

        # Check if dataset_id is already a numeric UID
        if dataset_id.isdigit():
            return {"db": db, "id": dataset_id, "retmode": "json"}

        # For accession numbers, we need to convert to UID first
        # This will be handled in the run method
        return {"db": db, "id": dataset_id, "retmode": "json"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        # Validate required parameters
        for param in self.required:
            if param not in arguments:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {param}",
                }

        dataset_id = arguments.get("dataset_id", "")
        if not dataset_id:
            return {"status": "error", "error": "dataset_id is required"}

        # Detect database type
        db = self._detect_database(dataset_id)

        # Check if dataset_id is already a numeric UID
        if dataset_id.isdigit():
            # Direct UID, use esummary directly
            self.endpoint = self.endpoint_template
            params = {"db": db, "id": dataset_id, "retmode": "json"}
            return self._make_request(self.endpoint, params)

        # For accession numbers, first convert to UID using esearch
        search_result = self._accession_to_uid(dataset_id, db)

        if search_result.get("status") != "success":
            return search_result

        search_data = search_result.get("data", {})
        esearch_result = search_data.get("esearchresult", {})
        idlist = esearch_result.get("idlist", [])

        if not idlist:
            return {
                "status": "error",
                "error": f"No UID found for accession {dataset_id} in database {db}",
                "data": search_data,
            }

        # Use the first UID from the search results
        uid = idlist[0]

        # Now use esummary with the UID
        self.endpoint = self.endpoint_template
        params = {"db": db, "id": uid, "retmode": "json"}
        return self._make_request(self.endpoint, params)
