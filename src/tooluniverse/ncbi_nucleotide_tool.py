"""
NCBI Nucleotide Search Tool

This tool provides search capabilities for NCBI's Nucleotide database (GenBank/EMBL/RefSeq)
using E-utilities (esearch + efetch). Allows searching by organism name, gene name, keywords,
and retrieving accession numbers.
"""

from typing import Dict, Any
from .ncbi_eutils_tool import NCBIEUtilsTool
from .tool_registry import register_tool


@register_tool("NCBINucleotideSearchTool")
class NCBINucleotideSearchTool(NCBIEUtilsTool):
    """
    NCBI Nucleotide Database Search Tool using E-utilities.
    Searches GenBank/EMBL/RefSeq for DNA/RNA sequences by organism, gene, keywords.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.db = "nucleotide"  # Database name for E-utilities

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the nucleotide search with given arguments."""
        operation = arguments.get("operation")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        if operation == "search":
            return self._search_nucleotide(arguments)
        elif operation == "fetch_accession":
            return self._fetch_accession(arguments)
        elif operation == "fetch_sequence":
            return self._fetch_sequence(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
            }

    def _build_search_term(self, arguments: Dict[str, Any]) -> str:
        """Build NCBI search term from arguments."""
        terms = []

        # Organism filter
        if arguments.get("organism"):
            terms.append(f"{arguments['organism']}[Organism]")

        # Gene name filter
        if arguments.get("gene"):
            terms.append(f"{arguments['gene']}[Gene]")

        # Strain filter
        if arguments.get("strain"):
            terms.append(f"{arguments['strain']}[Strain]")

        # Keywords/title search
        if arguments.get("keywords"):
            terms.append(f"{arguments['keywords']}[Title]")

        # Sequence type filter
        if arguments.get("seq_type"):
            seq_type = arguments["seq_type"]
            if seq_type == "complete_genome":
                terms.append("complete genome[Title]")
            elif seq_type == "mrna":
                terms.append("mRNA[Filter]")
            elif seq_type == "refseq":
                terms.append("RefSeq[Filter]")

        # Free text query (if no specific filters provided)
        if arguments.get("query") and not terms:
            return arguments["query"]

        # Combine terms with AND
        if terms:
            return " AND ".join(f"({term})" for term in terms)

        return arguments.get("query", "")

    def _search_nucleotide(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search NCBI nucleotide database and return UIDs.
        Uses esearch to find matching records.
        """
        try:
            # Build search term
            search_term = self._build_search_term(arguments)

            if not search_term:
                return {
                    "status": "error",
                    "error": "No search criteria provided. Use organism, gene, keywords, or query.",
                }

            # Build esearch parameters
            params = {
                "db": self.db,
                "term": search_term,
                "retmode": "json",
                "retmax": arguments.get("limit") or arguments.get("max_results") or 20,
                "sort": arguments.get("sort", "relevance"),
            }

            result = self._make_request("/esearch.fcgi", params)

            if result["status"] == "error":
                return result

            data = result.get("data", {})
            if isinstance(data, dict):
                esearch_result = data.get("esearchresult", {})
                uids = esearch_result.get("idlist", [])
                count = int(esearch_result.get("count", 0))

                # Auto-fetch accession numbers so results are immediately usable
                accessions = []
                if uids:
                    try:
                        acc_result = self._make_request(
                            "/efetch.fcgi",
                            {
                                "db": self.db,
                                "id": ",".join(uids),
                                "rettype": "acc",
                                "retmode": "text",
                            },
                        )
                        if acc_result["status"] == "success":
                            raw = acc_result.get("data", "")
                            if isinstance(raw, str):
                                accessions = [
                                    a.strip()
                                    for a in raw.strip().split("\n")
                                    if a.strip()
                                ]
                    except Exception:
                        pass

                return {
                    "status": "success",
                    "data": {
                        "uids": uids,
                        "accessions": accessions,
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

    def _fetch_accession(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch accession numbers for given UIDs.
        Uses efetch with rettype=acc to get just accession numbers.
        """
        try:
            uids = arguments.get("uids", [])

            if isinstance(uids, str):
                uids = [uids]

            if not uids:
                return {"status": "error", "error": "Missing required parameter: uids"}

            # Build efetch parameters
            params = {
                "db": self.db,
                "id": ",".join(str(uid) for uid in uids),
                "rettype": "acc",
                "retmode": "text",
            }

            # Make request
            result = self._make_request("/efetch.fcgi", params)

            if result["status"] == "error":
                return result

            # Parse accession numbers from response
            data = result.get("data", "")
            if isinstance(data, str):
                accessions = [
                    acc.strip() for acc in data.strip().split("\n") if acc.strip()
                ]

                return {
                    "status": "success",
                    "data": accessions,
                    "count": len(accessions),
                    "url": result.get("url"),
                }
            else:
                return {
                    "status": "error",
                    "error": "Unexpected response format from NCBI",
                }

        except Exception as e:
            return {"status": "error", "error": f"Fetch accessions failed: {str(e)}"}

    def _fetch_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch sequence data for given accession(s).
        Uses efetch to retrieve sequences in specified format.
        """
        try:
            accession = arguments.get("accession")

            if not accession:
                return {
                    "status": "error",
                    "error": "Missing required parameter: accession",
                }

            # Get format (default to fasta)
            seq_format = arguments.get("format", "fasta")

            # Build efetch parameters
            params = {
                "db": self.db,
                "id": accession,
                "rettype": seq_format,
                "retmode": "text",
            }

            # Make request
            result = self._make_request("/efetch.fcgi", params)

            if result["status"] == "error":
                return result

            # Return sequence data
            data = result.get("data", "")

            return {
                "status": "success",
                "data": data,
                "accession": accession,
                "format": seq_format,
                "length": len(data),
                "url": result.get("url"),
            }

        except Exception as e:
            return {"status": "error", "error": f"Fetch sequence failed: {str(e)}"}
