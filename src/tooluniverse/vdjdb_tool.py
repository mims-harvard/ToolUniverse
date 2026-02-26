"""
VDJdb - TCR/BCR Clonotype Database Tool

Provides access to the VDJdb API for querying T-cell receptor (TCR) and
B-cell receptor (BCR) sequences with known antigen specificities.

VDJdb is a curated database of TCR sequences with experimentally
verified antigen specificity data, integrating 226,000+ records
from 300+ studies across human, mouse, and macaque species.

API base: https://vdjdb.com/api/
No authentication required.

Reference: Bagaev et al., NAR 2020 (PMID: 31782517)
"""

import json
import requests
from typing import Any, Dict, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


VDJDB_BASE_URL = "https://vdjdb.com/api"

# Column name -> index mapping based on /api/database/meta
COLUMN_NAMES = [
    "gene",
    "cdr3",
    "v.segm",
    "j.segm",
    "species",
    "mhc.a",
    "mhc.b",
    "mhc.class",
    "antigen.epitope",
    "antigen.gene",
    "antigen.species",
    "reference.id",
    "method",
    "meta",
    "cdr3fix",
    "vdjdb.score",
]


def _parse_row(entries: List[str], metadata: Dict) -> Dict[str, Any]:
    """Parse a raw VDJdb search row into a structured dictionary."""
    record = {}
    for i, col_name in enumerate(COLUMN_NAMES):
        if i < len(entries):
            val = entries[i]
            # Parse JSON fields
            if col_name in ("method", "meta", "cdr3fix"):
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
            # Convert score to integer
            elif col_name == "vdjdb.score":
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    pass
            record[col_name] = val

    # Add metadata
    if metadata:
        record["paired_id"] = metadata.get("pairedID", "0")
        record["cdr3_v_end"] = metadata.get("cdr3vEnd")
        record["cdr3_j_start"] = metadata.get("cdr3jStart")

    return record


@register_tool("VDJDBTool")
class VDJDBTool(BaseTool):
    """
    Tool for querying the VDJdb T-cell receptor sequence database.

    VDJdb is a curated database of TCR sequences with experimentally
    verified antigen specificity. It links CDR3 sequences to specific
    epitopes, MHC alleles, and antigen sources.

    Supported operations:
    - search_cdr3: Search by CDR3 amino acid sequence
    - get_antigen_specificity: Search by epitope sequence
    - get_database_summary: Get database statistics
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the VDJdb API tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "search_cdr3": self._search_cdr3,
            "get_antigen_specificity": self._get_antigen_specificity,
            "get_database_summary": self._get_database_summary,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "VDJdb API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to VDJdb API"}
        except Exception as e:
            return {"status": "error", "error": f"VDJdb operation failed: {str(e)}"}

    def _post_search(
        self,
        filters: List[Dict],
        page: Optional[int] = None,
        page_size: int = 25,
        paired: bool = False,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make a POST search request to VDJdb API."""
        url = f"{VDJDB_BASE_URL}/database/search"
        body = {"filters": filters}
        if page is not None:
            body["page"] = page
            body["pageSize"] = page_size
        if paired:
            body["paired"] = True
        if sort:
            body["sort"] = sort

        response = self.session.post(
            url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "error": f"VDJdb API returned status {response.status_code}",
                "detail": response.text[:500],
            }

        try:
            data = response.json()
        except Exception:
            return {"ok": False, "error": "Invalid JSON response from VDJdb"}

        return {"ok": True, "data": data}

    def _search_cdr3(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search VDJdb by CDR3 amino acid sequence."""
        cdr3 = arguments.get("cdr3")
        if not cdr3:
            return {"status": "error", "error": "cdr3 parameter is required"}

        species = arguments.get("species")
        gene = arguments.get("gene")
        match_type = arguments.get("match_type", "exact")
        page = arguments.get("page", 0)
        page_size = arguments.get("page_size", 25)

        filters = []

        # CDR3 filter
        if match_type == "exact":
            filters.append(
                {
                    "column": "cdr3",
                    "value": cdr3,
                    "filterType": "exact",
                    "negative": False,
                }
            )
        elif match_type == "fuzzy":
            # Fuzzy match: value format is "sequence:substitutions:insertions:deletions"
            subs = arguments.get("substitutions", 1)
            ins = arguments.get("insertions", 1)
            dels = arguments.get("deletions", 1)
            filters.append(
                {
                    "column": "cdr3",
                    "value": f"{cdr3}:{subs}:{ins}:{dels}",
                    "filterType": "sequence",
                    "negative": False,
                }
            )
        elif match_type == "pattern":
            filters.append(
                {
                    "column": "cdr3",
                    "value": cdr3,
                    "filterType": "pattern",
                    "negative": False,
                }
            )

        # Optional species filter
        if species:
            filters.append(
                {
                    "column": "species",
                    "value": species,
                    "filterType": "exact",
                    "negative": False,
                }
            )

        # Optional gene filter (TRA or TRB)
        if gene:
            filters.append(
                {
                    "column": "gene",
                    "value": gene,
                    "filterType": "exact",
                    "negative": False,
                }
            )

        result = self._post_search(filters, page=page, page_size=page_size)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        raw = result["data"]
        records = [
            _parse_row(row["entries"], row.get("metadata", {}))
            for row in raw.get("rows", [])
        ]

        return {
            "status": "success",
            "data": {
                "records": records,
                "records_found": raw.get("recordsFound", 0),
                "page": raw.get("page", -1),
                "page_size": raw.get("pageSize", -1),
                "page_count": raw.get("pageCount", -1),
            },
        }

    def _get_antigen_specificity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search VDJdb by epitope sequence to find TCRs recognizing an antigen."""
        epitope = arguments.get("epitope")
        if not epitope:
            return {"status": "error", "error": "epitope parameter is required"}

        species = arguments.get("species")
        gene = arguments.get("gene")
        mhc_class = arguments.get("mhc_class")
        min_score = arguments.get("min_score")
        page = arguments.get("page", 0)
        page_size = arguments.get("page_size", 25)

        filters = [
            {
                "column": "antigen.epitope",
                "value": epitope,
                "filterType": "exact",
                "negative": False,
            }
        ]

        if species:
            filters.append(
                {
                    "column": "species",
                    "value": species,
                    "filterType": "exact",
                    "negative": False,
                }
            )

        if gene:
            filters.append(
                {
                    "column": "gene",
                    "value": gene,
                    "filterType": "exact",
                    "negative": False,
                }
            )

        if mhc_class:
            filters.append(
                {
                    "column": "mhc.class",
                    "value": mhc_class,
                    "filterType": "exact",
                    "negative": False,
                }
            )

        if min_score is not None:
            filters.append(
                {
                    "column": "vdjdb.score",
                    "value": str(min_score),
                    "filterType": "level",
                    "negative": False,
                }
            )

        result = self._post_search(filters, page=page, page_size=page_size)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        raw = result["data"]
        records = [
            _parse_row(row["entries"], row.get("metadata", {}))
            for row in raw.get("rows", [])
        ]

        return {
            "status": "success",
            "data": {
                "records": records,
                "records_found": raw.get("recordsFound", 0),
                "page": raw.get("page", -1),
                "page_size": raw.get("pageSize", -1),
                "page_count": raw.get("pageCount", -1),
            },
        }

    def _get_database_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get VDJdb database metadata and column information."""
        url = f"{VDJDB_BASE_URL}/database/meta"
        response = self.session.get(url, timeout=self.timeout)

        if response.status_code != 200:
            return {
                "status": "error",
                "error": f"VDJdb meta endpoint returned status {response.status_code}",
            }

        try:
            data = response.json()
        except Exception:
            return {"status": "error", "error": "Invalid JSON from VDJdb meta endpoint"}

        meta = data.get("metadata", {})
        columns = meta.get("columns", [])
        column_info = []
        for col in columns:
            column_info.append(
                {
                    "name": col.get("name"),
                    "title": col.get("title"),
                    "data_type": col.get("dataType"),
                    "column_type": col.get("columnType"),
                    "comment": col.get("comment"),
                }
            )

        return {
            "status": "success",
            "data": {
                "total_records": meta.get("numberOfRecords", 0),
                "number_of_columns": meta.get("numberOfColumns", 0),
                "columns": column_info,
            },
        }
