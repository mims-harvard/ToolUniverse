# ega_tool.py
"""
EGA (European Genome-phenome Archive) tool for ToolUniverse.

EGA archives controlled-access human genomic and phenotypic data; the
sequence/genotype data itself requires Data Access Committee approval, but
study and dataset *metadata* (title, description, technology, sample
count, access policy) is public. EGA accessions (EGAS.../EGAD...) appear
constantly in papers' data-availability statements with no way to resolve
them in ToolUniverse today.

The API silently accepts a query-like parameter under any name tried
(query, q, search, title, free_text_search) without filtering by it at
all: every variant returned the identical first record regardless of
content, confirmed by comparing results across nonsense and real queries.
Only exact-accession lookups are exposed here as a result.

API: https://metadata.ega-archive.org
No authentication required for metadata (the underlying data is separately
access-controlled).
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

EGA_BASE_URL = "https://metadata.ega-archive.org"


@register_tool("EGATool")
class EGATool(BaseTool):
    """
    Tool for resolving EGA study and dataset accessions to their public
    metadata.

    Supports fetching one study, one dataset, or the datasets belonging to
    a study, all by exact accession. No free-text search: the API's own
    query parameters are silently non-functional (see module docstring).

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_study"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EGA metadata lookup."""
        try:
            if self.operation == "get_study":
                return self._get_study(arguments)
            if self.operation == "get_dataset":
                return self._get_dataset(arguments)
            if self.operation == "get_study_datasets":
                return self._get_study_datasets(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EGA request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to EGA. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"EGA returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "EGA returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying EGA: {str(e)}"}

    def _get_study(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one study's public metadata by its EGAS accession."""
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {
                "status": "error",
                "error": "accession is required, e.g. 'EGAS00000000001'.",
            }

        response = requests.get(
            f"{EGA_BASE_URL}/studies/{accession}", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No EGA study with accession '{accession}'.",
            }
        response.raise_for_status()
        study = response.json()

        return {
            "status": "success",
            "data": {
                "accession_id": study.get("accession_id"),
                "title": study.get("title"),
                "description": study.get("description"),
                "study_type": study.get("study_type"),
                "pubmed_ids": study.get("pubmed_ids") or [],
                "is_released": study.get("is_released"),
                "released_date": study.get("released_date"),
                "is_deprecated": study.get("is_deprecated"),
            },
            "metadata": {
                "accession": accession,
                "note": "Metadata only; the underlying sequence/genotype "
                "data requires Data Access Committee approval. Use "
                "get_study_datasets for this study's dataset accessions.",
                "source": "European Genome-phenome Archive (EGA)",
            },
        }

    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one dataset's public metadata by its EGAD accession."""
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {
                "status": "error",
                "error": "accession is required, e.g. 'EGAD00000000001'.",
            }

        response = requests.get(
            f"{EGA_BASE_URL}/datasets/{accession}", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No EGA dataset with accession '{accession}'.",
            }
        response.raise_for_status()
        dataset = response.json()

        return {
            "status": "success",
            "data": {
                "accession_id": dataset.get("accession_id"),
                "title": dataset.get("title"),
                "description": dataset.get("description"),
                "dataset_types": dataset.get("dataset_types") or [],
                "technologies": dataset.get("technologies") or [],
                "num_samples": dataset.get("num_samples"),
                "access_type": dataset.get("access_type"),
                "policy_accession_id": dataset.get("policy_accession_id"),
                "is_released": dataset.get("is_released"),
                "released_date": dataset.get("released_date"),
            },
            "metadata": {
                "accession": accession,
                "note": "access_type 'controlled' means the actual data "
                "requires Data Access Committee approval via the "
                "policy_accession_id shown here.",
                "source": "European Genome-phenome Archive (EGA)",
            },
        }

    def _get_study_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the dataset accessions belonging to one study."""
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {
                "status": "error",
                "error": "accession is required, e.g. 'EGAS00000000001'.",
            }

        response = requests.get(
            f"{EGA_BASE_URL}/studies/{accession}/datasets", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No EGA study with accession '{accession}'.",
            }
        response.raise_for_status()
        datasets = response.json() or []

        if not datasets:
            return {
                "status": "error",
                "error": f"No datasets found for EGA study '{accession}'.",
            }

        rows = [
            {
                "accession_id": d.get("accession_id"),
                "title": d.get("title"),
                "technologies": d.get("technologies") or [],
                "num_samples": d.get("num_samples"),
                "access_type": d.get("access_type"),
            }
            for d in datasets
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "study_accession": accession,
                "returned": len(rows),
                "note": "accession_id is what get_dataset expects for full "
                "dataset metadata.",
                "source": "European Genome-phenome Archive (EGA)",
            },
        }
