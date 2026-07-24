"""
GEO Database REST API Tool

This tool provides access to gene expression data from the GEO database.
GEO is a public repository that archives and freely distributes microarray,
next-generation sequencing, and other forms of high-throughput functional
genomics data.
"""

import re
import requests
from typing import Dict, Any, List
from .ncbi_eutils_tool import NCBIEUtilsTool
from .tool_registry import register_tool

# Base of the NCBI GEO FTP-over-HTTPS supplementary file tree.
GEO_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/geo"


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
        # Optional discriminator: when "supplementary_files", run() lists the
        # downloadable supplementary/raw files from the GEO FTP tree instead of
        # calling E-utilities.
        self.mode: str = fields.get("mode", "")

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

        if self.mode == "supplementary_files":
            return self._list_supplementary_files(arguments)

        # Set endpoint for the base class
        self.endpoint = self.endpoint_template
        params = self._build_params(arguments)

        # Use the parent class's _make_request with rate limiting
        return self._make_request(self.endpoint, params)

    @staticmethod
    def _geo_bucket(accession: str) -> str:
        """Derive the GEO FTP bucket directory for a GSE/GSM accession.

        The bucket replaces the last three digits of the numeric part with
        'nnn'; accessions with three or fewer digits live in the bare bucket.
        e.g. GSE42657 -> GSE42nnn, GSE1000 -> GSE1nnn, GSE100 -> GSEnnn,
        GSM1045442 -> GSM1045nnn.
        """
        prefix = accession[:3]
        num = accession[3:]
        head = num[:-3] if len(num) > 3 else ""
        return f"{prefix}{head}nnn"

    def _list_supplementary_files(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List downloadable supplementary/raw files for a GEO Series/Sample.

        Series (GSE*) expose a structured filelist.txt TSV (Archive/File, Name,
        Time, Size, Type). Samples (GSM*) have no filelist.txt, so the suppl/
        directory HTML listing is parsed instead.
        """
        try:
            accession = str(arguments.get("accession", "")).strip().upper()
            if not accession:
                return {
                    "status": "error",
                    "error": "Missing required parameter: accession",
                }

            if accession.startswith("GSE"):
                kind, subdir = "series", "series"
            elif accession.startswith("GSM"):
                kind, subdir = "sample", "samples"
            else:
                return {
                    "status": "error",
                    "error": "accession must be a GEO Series (GSE...) or Sample (GSM...)",
                }

            bucket = self._geo_bucket(accession)
            base = f"{GEO_FTP_BASE}/{subdir}/{bucket}/{accession}/suppl"

            if kind == "series":
                return self._parse_filelist(accession, base)
            return self._parse_suppl_dir(accession, base)

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GEO FTP request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to GEO FTP server",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to list supplementary files: {str(e)}",
            }

    def _parse_filelist(self, accession: str, base: str) -> Dict[str, Any]:
        """Parse a Series filelist.txt TSV into structured file records."""
        url = f"{base}/filelist.txt"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"No supplementary filelist found for {accession} (HTTP 404)",
                "url": url,
            }
        resp.raise_for_status()

        files = []
        for line in resp.text.splitlines():
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            kind, name, time_str, size, ftype = parts[:5]
            try:
                size_val: Any = int(size)
            except (ValueError, TypeError):
                size_val = size
            files.append(
                {
                    "kind": kind,
                    "name": name,
                    "modified": time_str,
                    "size": size_val,
                    "type": ftype,
                    "download_url": f"{base}/{name}",
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": accession,
                "suppl_url": base + "/",
                "files": files,
                "file_count": len(files),
            },
            "metadata": {
                "source": "NCBI GEO FTP",
                "query": accession,
                "endpoint": "supplementary_files",
            },
        }

    def _parse_suppl_dir(self, accession: str, base: str) -> Dict[str, Any]:
        """Parse a Sample suppl/ directory HTML listing into file records."""
        url = base + "/"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"No supplementary directory found for {accession} (HTTP 404)",
                "url": url,
            }
        resp.raise_for_status()

        files = []
        seen = set()
        for href in re.findall(r'href="([^"]+)"', resp.text):
            # Skip parent links, absolute paths, and external policy links.
            if href.startswith("/") or href.startswith("http") or href.startswith("?"):
                continue
            if href in ("../",) or href.endswith("/"):
                continue
            if href in seen:
                continue
            seen.add(href)
            files.append(
                {
                    "kind": "File",
                    "name": href,
                    "download_url": f"{base}/{href}",
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": accession,
                "suppl_url": url,
                "files": files,
                "file_count": len(files),
            },
            "metadata": {
                "source": "NCBI GEO FTP",
                "query": accession,
                "endpoint": "supplementary_files",
            },
        }


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
