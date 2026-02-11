"""NCBI SRA (Sequence Read Archive) Tool for NGS/RNA-seq data access."""

import xml.etree.ElementTree as ET
from typing import Any, Dict
from .ncbi_eutils_tool import NCBIEUtilsTool
from .tool_registry import register_tool


@register_tool("NCBISRATool")
class NCBISRATool(NCBIEUtilsTool):
    """NCBI SRA Tool using E-utilities for sequencing run metadata and downloads."""

    _OPERATIONS = {
        "search": "_search_sra_runs",
        "get_run_info": "_get_run_info",
        "get_download_urls": "_get_download_urls",
        "link_to_biosample": "_link_to_biosample",
    }

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.db = "sra"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SRA tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        method_name = self._OPERATIONS.get(operation)
        if not method_name:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return getattr(self, method_name)(arguments)

    _SEARCH_FIELDS = {
        "study": "Study",
        "organism": "Organism",
        "strategy": "Strategy",
        "platform": "Platform",
        "source": "Source",
    }

    def _build_search_term(self, arguments: Dict[str, Any]) -> str:
        """Build NCBI SRA search term from arguments."""
        terms = [
            f"{arguments[key]}[{field}]"
            for key, field in self._SEARCH_FIELDS.items()
            if arguments.get(key)
        ]

        if arguments.get("query") and not terms:
            return arguments["query"]

        if terms:
            return " AND ".join(f"({term})" for term in terms)

        return arguments.get("query", "")

    def _search_sra_runs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search SRA database for runs using esearch."""
        try:
            # Build search term
            search_term = self._build_search_term(arguments)

            if not search_term:
                return {
                    "status": "error",
                    "error": "No search criteria provided. Use study, organism, strategy, platform, source, or query.",
                }

            # Build esearch parameters
            params = {
                "db": self.db,
                "term": search_term,
                "retmode": "json",
                "retmax": arguments.get("limit", 20),
                "sort": arguments.get("sort", "relevance"),
                "usehistory": "y",  # Store results on server for large queries
            }

            # Make request
            result = self._make_request("/esearch.fcgi", params)

            if result["status"] == "error":
                return result

            # Extract UIDs from esearch response
            data = result.get("data", {})
            if isinstance(data, dict):
                esearch_result = data.get("esearchresult", {})
                uids = esearch_result.get("idlist", [])
                count = int(esearch_result.get("count", 0))

                return {
                    "status": "success",
                    "data": {
                        "uids": uids,
                        "count": count,
                        "returned": len(uids),
                        "search_term": search_term,
                    },
                    "total_count": count,
                    "url": result.get("url"),
                }
            else:
                return {
                    "status": "error",
                    "error": "Unexpected response format from NCBI",
                }

        except Exception as e:
            return {"status": "error", "error": f"Search failed: {str(e)}"}

    def _get_run_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata for SRA run accessions via efetch XML."""
        try:
            accessions = arguments.get("accessions", [])

            if isinstance(accessions, str):
                accessions = [accessions]

            if not accessions:
                return {
                    "status": "error",
                    "error": "Missing required parameter: accessions",
                }

            # Build efetch parameters
            params = {
                "db": self.db,
                "id": ",".join(str(acc) for acc in accessions),
                "rettype": "full",
                "retmode": "xml",
            }

            # Make request
            result = self._make_request("/efetch.fcgi", params)

            if result["status"] == "error":
                return result

            # Parse XML response
            data = result.get("data", "")
            if isinstance(data, str):
                try:
                    run_info = self._parse_sra_xml(data)

                    return {
                        "status": "success",
                        "data": run_info,
                        "count": len(run_info),
                        "url": result.get("url"),
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to parse XML response: {str(e)}",
                        "raw_data": data[:1000] if len(data) > 1000 else data,
                    }
            else:
                return {
                    "status": "error",
                    "error": "Unexpected response format from NCBI",
                }

        except Exception as e:
            return {"status": "error", "error": f"Get run info failed: {str(e)}"}

    def _parse_sra_xml(self, xml_data: str) -> list:
        """Parse SRA XML metadata to extract run information."""
        try:
            root = ET.fromstring(xml_data)
            runs = []

            # Find all EXPERIMENT_PACKAGE elements
            for exp_pkg in root.findall(".//EXPERIMENT_PACKAGE"):
                run_info = {}

                # Get RUN information
                run = exp_pkg.find(".//RUN")
                if run is not None:
                    run_info["run_accession"] = run.get("accession", "")
                    run_info["total_spots"] = run.get("total_spots", "")
                    run_info["total_bases"] = run.get("total_bases", "")
                    run_info["published"] = run.get("published", "")

                # Get EXPERIMENT information
                experiment = exp_pkg.find(".//EXPERIMENT")
                if experiment is not None:
                    run_info["experiment_accession"] = experiment.get("accession", "")

                    # Platform
                    platform = experiment.find(".//PLATFORM")
                    if platform is not None:
                        for child in platform:
                            run_info["platform"] = child.tag
                            instrument = child.find(".//INSTRUMENT_MODEL")
                            if instrument is not None:
                                run_info["instrument"] = instrument.text

                    # Library
                    library = experiment.find(".//LIBRARY_DESCRIPTOR")
                    if library is not None:
                        lib_strategy = library.find("LIBRARY_STRATEGY")
                        lib_source = library.find("LIBRARY_SOURCE")
                        lib_selection = library.find("LIBRARY_SELECTION")
                        lib_layout = library.find("LIBRARY_LAYOUT")

                        if lib_strategy is not None:
                            run_info["library_strategy"] = lib_strategy.text
                        if lib_source is not None:
                            run_info["library_source"] = lib_source.text
                        if lib_selection is not None:
                            run_info["library_selection"] = lib_selection.text
                        if lib_layout is not None:
                            run_info["library_layout"] = (
                                "PAIRED" if lib_layout.find("PAIRED") is not None else "SINGLE"
                            )

                # Get STUDY information
                study = exp_pkg.find(".//STUDY")
                if study is not None:
                    run_info["study_accession"] = study.get("accession", "")
                    study_title = study.find(".//STUDY_TITLE")
                    if study_title is not None:
                        run_info["study_title"] = study_title.text

                # Get SAMPLE information
                sample = exp_pkg.find(".//SAMPLE")
                if sample is not None:
                    run_info["sample_accession"] = sample.get("accession", "")
                    organism = sample.find(".//SCIENTIFIC_NAME")
                    if organism is not None:
                        run_info["organism"] = organism.text

                runs.append(run_info)

            return runs

        except ET.ParseError as e:
            raise Exception(f"XML parsing error: {str(e)}")

    def _get_download_urls(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get FTP, S3, and NCBI download URLs for SRA run accessions."""
        try:
            accessions = arguments.get("accessions", [])

            if isinstance(accessions, str):
                accessions = [accessions]

            if not accessions:
                return {
                    "status": "error",
                    "error": "Missing required parameter: accessions",
                }

            download_urls = []

            _VALID_PREFIXES = ("SRR", "ERR", "DRR")
            _FTP_BASE = "ftp://ftp-trace.ncbi.nlm.nih.gov/sra/sra-instant/reads/ByRun/sra"

            for accession in accessions:
                if not any(accession.startswith(p) for p in _VALID_PREFIXES):
                    download_urls.append({
                        "accession": accession,
                        "error": "Invalid accession format. Must start with SRR, ERR, or DRR",
                    })
                    continue

                prefix = accession[:3]
                acc_num = accession[3:]
                subdir = acc_num[:6] if len(acc_num) >= 6 else acc_num.zfill(6)

                download_urls.append({
                    "accession": accession,
                    "ftp_url": f"{_FTP_BASE}/{prefix}/{prefix}{subdir}/{accession}/{accession}.sra",
                    "s3_url": f"s3://sra-pub-run-odp/sra/{accession}/{accession}",
                    "ncbi_url": f"https://trace.ncbi.nlm.nih.gov/Traces/sra/?run={accession}",
                    "note": "Use SRA Toolkit (fastq-dump or fasterq-dump) to convert SRA to FASTQ format",
                })

            return {
                "status": "success",
                "data": download_urls,
                "count": len(download_urls),
            }

        except Exception as e:
            return {"status": "error", "error": f"Get download URLs failed: {str(e)}"}

    def _link_to_biosample(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Link SRA runs to BioSample records via elink."""
        try:
            accessions = arguments.get("accessions", [])

            if isinstance(accessions, str):
                accessions = [accessions]

            if not accessions:
                return {
                    "status": "error",
                    "error": "Missing required parameter: accessions",
                }

            # Build elink parameters
            params = {
                "dbfrom": self.db,
                "db": "biosample",
                "id": ",".join(str(acc) for acc in accessions),
                "retmode": "json",
            }

            # Make request
            result = self._make_request("/elink.fcgi", params)

            if result["status"] == "error":
                return result

            # Parse elink response
            data = result.get("data", {})
            if isinstance(data, dict):
                linksets = data.get("linksets", [])
                links = []

                for linkset in linksets:
                    sra_id = linkset.get("ids", [""])[0]
                    linksetdbs = linkset.get("linksetdbs", [])

                    biosample_ids = []
                    for linksetdb in linksetdbs:
                        if linksetdb.get("dbto") == "biosample":
                            biosample_ids.extend(linksetdb.get("links", []))

                    links.append({
                        "sra_uid": sra_id,
                        "biosample_uids": biosample_ids,
                        "biosample_count": len(biosample_ids),
                    })

                return {
                    "status": "success",
                    "data": links,
                    "count": len(links),
                    "url": result.get("url"),
                }
            else:
                return {
                    "status": "error",
                    "error": "Unexpected response format from NCBI",
                }

        except Exception as e:
            return {"status": "error", "error": f"Link to BioSample failed: {str(e)}"}
