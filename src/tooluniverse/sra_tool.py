# sra_tool.py
"""
NCBI Sequence Read Archive (SRA) search tool for ToolUniverse.

Provides search and summary retrieval for SRA experiments, runs, and studies
using NCBI Entrez E-utilities.

API: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
No authentication required (optional API key for higher rate limits).
"""

import time
import requests
import xml.etree.ElementTree as ET
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@register_tool("SRATool")
class SRATool(BaseTool):
    """
    Tool for searching NCBI SRA (Sequence Read Archive) for sequencing
    experiments, runs, and studies.

    Supports keyword search, organism filtering, and retrieval of experiment
    metadata including platform, library strategy, and run statistics.

    No authentication required.
    """

    def __init__(self, tool_config: dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "search")

    def _get_with_retry(self, url, params, max_retries=3):
        """GET request with retry on 429 rate limit."""
        for attempt in range(max_retries):
            resp = requests.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 429:
                wait = 1.0 * (attempt + 1)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        resp.raise_for_status()
        return resp

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.operation == "search":
                return self._search(arguments)
            elif self.operation == "get_experiment":
                return self._get_experiment(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {self.operation}",
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NCBI SRA API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NCBI SRA API",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search SRA for experiments by keyword, organism, strategy."""
        query = arguments.get("query", "")
        organism = arguments.get("organism")
        library_strategy = arguments.get("library_strategy")
        platform = arguments.get("platform")
        limit = min(int(arguments.get("limit", 10)), 50)

        terms = []
        if query:
            terms.append(query)
        if organism:
            terms.append(f"{organism}[Organism]")
        if library_strategy:
            terms.append(f"{library_strategy}[Strategy]")
        if platform:
            terms.append(f"{platform}[Platform]")

        if not terms:
            return {
                "status": "error",
                "error": "At least one search parameter is required (query, organism, library_strategy, or platform)",
            }

        search_term = " AND ".join(terms)

        # Step 1: Search for IDs
        search_url = f"{EUTILS_BASE}/esearch.fcgi"
        search_params = {
            "db": "sra",
            "term": search_term,
            "retmax": limit,
            "retmode": "json",
            "sort": "relevance",
        }
        resp = self._get_with_retry(search_url, search_params)
        search_data = resp.json()

        result = search_data.get("esearchresult", {})
        total_count = int(result.get("count", 0))
        id_list = result.get("idlist", [])

        if not id_list:
            return {
                "status": "success",
                "data": {
                    "total": total_count,
                    "returned": 0,
                    "experiments": [],
                    "query_used": search_term,
                },
            }

        # Brief pause to avoid NCBI rate limits (3 req/sec without key)
        time.sleep(0.4)

        # Step 2: Get summaries for found IDs
        summary_url = f"{EUTILS_BASE}/esummary.fcgi"
        summary_params = {
            "db": "sra",
            "id": ",".join(id_list),
            "retmode": "json",
        }
        resp = self._get_with_retry(summary_url, summary_params)
        summary_data = resp.json()

        result_entries = summary_data.get("result", {})
        uids = result_entries.get("uids", [])

        experiments = []
        for uid in uids:
            entry = result_entries.get(uid, {})
            parsed = self._parse_sra_summary(entry, uid)
            experiments.append(parsed)

        return {
            "status": "success",
            "data": {
                "total": total_count,
                "returned": len(experiments),
                "experiments": experiments,
                "query_used": search_term,
            },
        }

    def _get_experiment(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get detailed metadata for a specific SRA experiment by accession."""
        accession = arguments.get("accession", "")
        if not accession:
            return {"status": "error", "error": "accession is required"}

        # Search by accession
        search_url = f"{EUTILS_BASE}/esearch.fcgi"
        search_params = {
            "db": "sra",
            "term": f"{accession}[Accession]",
            "retmax": 1,
            "retmode": "json",
        }
        resp = self._get_with_retry(search_url, search_params)
        search_data = resp.json()

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return {
                "status": "error",
                "error": f"SRA accession not found: {accession}",
            }

        time.sleep(0.4)

        # Get summary
        summary_url = f"{EUTILS_BASE}/esummary.fcgi"
        summary_params = {
            "db": "sra",
            "id": id_list[0],
            "retmode": "json",
        }
        resp = self._get_with_retry(summary_url, summary_params)
        summary_data = resp.json()

        result_entries = summary_data.get("result", {})
        uid = id_list[0]
        entry = result_entries.get(uid, {})

        parsed = self._parse_sra_summary(entry, uid)
        return {"status": "success", "data": parsed}

    def _parse_sra_summary(self, entry: dict, uid: str) -> dict:
        """Parse SRA eSummary XML fields into structured data."""
        exp_xml = entry.get("expxml", "")
        runs_xml = entry.get("runs", "")

        result = {"uid": uid}

        # Parse experiment XML
        if exp_xml:
            try:
                wrapped = f"<root>{exp_xml}</root>"
                root = ET.fromstring(wrapped)

                # Feature-SRA-001: detect HUP (held-under-private) experiments
                experiment_el = root.find("Experiment")
                if (
                    experiment_el is not None
                    and experiment_el.attrib.get("status") == "hup"
                ):
                    acc = experiment_el.attrib.get("acc", uid)
                    return {
                        "uid": uid,
                        "experiment_accession": acc,
                        "status": "hup",
                        "note": f"Experiment {acc} is held under private embargo (HUP). "
                        "Data will become available after the embargo period ends.",
                    }

                summary = root.find("Summary")
                if summary is not None:
                    title_el = summary.find("Title")
                    result["title"] = title_el.text if title_el is not None else None

                    platform_el = summary.find("Platform")
                    if platform_el is not None:
                        result["platform"] = platform_el.attrib.get("instrument_model")

                    stats = summary.find("Statistics")
                    if stats is not None:
                        result["total_runs"] = stats.attrib.get("total_runs")
                        result["total_spots"] = stats.attrib.get("total_spots")
                        result["total_bases"] = stats.attrib.get("total_bases")
                        result["total_size"] = stats.attrib.get("total_size")

                organism = root.find("Organism")
                if organism is not None:
                    result["organism"] = organism.attrib.get("ScientificName")
                    result["taxid"] = organism.attrib.get("taxid")

                library = root.find("Library_descriptor")
                if library is not None:
                    strategy = library.find("LIBRARY_STRATEGY")
                    source = library.find("LIBRARY_SOURCE")
                    selection = library.find("LIBRARY_SELECTION")
                    layout = library.find("LIBRARY_LAYOUT")
                    result["library_strategy"] = (
                        strategy.text if strategy is not None else None
                    )
                    result["library_source"] = (
                        source.text if source is not None else None
                    )
                    result["library_selection"] = (
                        selection.text if selection is not None else None
                    )
                    if layout is not None:
                        children = list(layout)
                        result["library_layout"] = children[0].tag if children else None

                study = root.find("Study")
                if study is not None:
                    result["study_accession"] = study.attrib.get("acc")
                    result["study_name"] = study.attrib.get("name")

                bioproject = root.find("Bioproject")
                if bioproject is not None:
                    result["bioproject"] = bioproject.text

                experiment = root.find("Experiment")
                if experiment is not None:
                    result["experiment_accession"] = experiment.attrib.get("acc")

                submitter = root.find("Submitter")
                if submitter is not None:
                    result["submitter"] = submitter.attrib.get("center_name")

            except ET.ParseError:
                result["raw_expxml"] = exp_xml[:200]

        # Parse runs XML
        if runs_xml:
            try:
                wrapped = f"<root>{runs_xml}</root>"
                root = ET.fromstring(wrapped)
                runs = []
                for run in root.findall("Run"):
                    runs.append(
                        {
                            "accession": run.attrib.get("acc"),
                            "total_spots": run.attrib.get("total_spots"),
                            "total_bases": run.attrib.get("total_bases"),
                            "is_public": run.attrib.get("is_public"),
                        }
                    )
                result["runs"] = runs[:10]
            except ET.ParseError:
                pass

        return result
