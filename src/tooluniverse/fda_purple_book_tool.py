# fda_purple_book_tool.py
"""
FDA Purple Book tool for ToolUniverse -- licensed biological products,
biosimilars, and interchangeables.

The Purple Book (purplebooksearch.fda.gov) lists every FDA-licensed
biological product regulated by CDER and CBER: reference biologics,
their licensed biosimilars and interchangeables, and each product's
exclusivity expiration dates. There is no JSON API, but FDA publishes a
monthly CSV snapshot at a discoverable, stable URL
(accessdata.fda.gov/drugsatfda_docs/PurpleBook/{year}/...-data-download.csv).
Per the FDA's own download-page documentation, each monthly file's *second*
section (after the blank line following that month's changes) "contains
all products in the Purple Book database for that month" -- i.e. the most
recent monthly file's bottom section is a complete, current snapshot of
the whole database, not just a delta. This tool discovers the latest
file from the downloads page (avoiding any hardcoded/guessed month-name
casing, which FDA's own naming is inconsistent about), parses that full
snapshot, and filters it.

No authentication required.
"""

import csv
import io
import re
import threading
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

DOWNLOADS_PAGE_URL = "https://purplebooksearch.fda.gov/downloads"
_CSV_URL_PATTERN = re.compile(
    r'href=["\'](https://www\.accessdata\.fda\.gov/drugsatfda_docs/PurpleBook/'
    r'(\d{4})/purplebook-search-[^"\']+?-data-download\.csv)["\']'
)

_FIELD_MAP = {
    "applicant": "Applicant",
    "bla_number": "BLA Number",
    "proprietary_name": "Proprietary Name",
    "proper_name": "Proper Name",
    "license_type": "License Type",
    "strength": "Strength",
    "dosage_form": "Dosage Form",
    "route_of_administration": "Route of Administration",
    "marketing_status": "Marketing Status",
    "approval_date": "Approval Date",
    "reference_product_proper_name": "Ref. Product Proper Name",
    "reference_product_proprietary_name": "Ref. Product Proprietary Name",
    "license_number": "License Number",
    "product_number": "Product Number",
    "center": "Center",
    "exclusivity_expiration_date": "Exclusivity Expiration Date",
    "orphan_exclusivity_expiration_date": "Orphan Exclusivity Exp. Date",
}

_FILTERABLE = (
    "applicant",
    "bla_number",
    "proprietary_name",
    "proper_name",
    "license_type",
    "reference_product_proper_name",
    "reference_product_proprietary_name",
)

_cache_lock = threading.Lock()
_cache: Dict[str, List[Dict[str, Any]]] = {}


def _find_latest_csv_url(timeout: int):
    """Discover the most recently published monthly CSV's URL.

    Returns (url, error). FDA's downloads page lists years newest-first and
    months in chronological order within a year, so the last URL under the
    highest year is the latest available month.
    """
    try:
        resp = requests.get(DOWNLOADS_PAGE_URL, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return None, f"Purple Book downloads page timed out after {timeout}s"
    except requests.exceptions.RequestException as e:
        return None, f"Failed to reach the Purple Book downloads page: {e}"

    by_year: Dict[str, List[str]] = {}
    for url, year in _CSV_URL_PATTERN.findall(resp.text):
        by_year.setdefault(year, []).append(url)
    if not by_year:
        return None, "No monthly data-download CSV links found on the Purple Book downloads page."

    latest_year = max(by_year)
    return by_year[latest_year][-1], None


def _parse_full_snapshot(csv_text: str):
    """Parse a monthly CSV's full-database section (its *second* table).

    Returns (records, error). Records are dicts keyed by the CSV's own
    column names.
    """
    rows = list(csv.reader(io.StringIO(csv_text)))
    header_rows = [
        i
        for i, row in enumerate(rows)
        if row and row[0] == "N/R/U" and len(row) > 1 and row[1] == "Applicant"
    ]
    if len(header_rows) < 2:
        return None, "Could not locate the full-database section in the monthly CSV."

    header = rows[header_rows[-1]]
    data_rows = [row for row in rows[header_rows[-1] + 1 :] if any(c.strip() for c in row)]
    records = [dict(zip(header, row)) for row in data_rows]
    return records, None


def _load_records(timeout: int):
    """Fetch and parse the latest snapshot, cached per resolved CSV URL."""
    url, err = _find_latest_csv_url(timeout)
    if err is not None:
        return None, None, {"status": "error", "error": err}

    with _cache_lock:
        cached = _cache.get(url)
    if cached is not None:
        return url, cached, None

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return None, None, {
            "status": "error",
            "error": f"Purple Book data file timed out after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return None, None, {
            "status": "error",
            "error": f"Failed to download the Purple Book data file: {e}",
        }

    records, err = _parse_full_snapshot(resp.text)
    if err is not None:
        return None, None, {"status": "error", "error": err}

    with _cache_lock:
        _cache[url] = records
    return url, records, None


def _summarize(rec: Dict[str, str]) -> Dict[str, Optional[str]]:
    return {key: (rec.get(csv_col) or "").strip() or None for key, csv_col in _FIELD_MAP.items()}


@register_tool("FDAPurpleBookTool")
class FDAPurpleBookTool(BaseTool):
    """Search FDA's Purple Book of licensed biological products.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def _limit(self, arguments: Dict[str, Any], default: int = 30) -> int:
        try:
            return max(1, min(int(arguments.get("limit") or default), 500))
        except (TypeError, ValueError):
            return default

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        filters = {
            key: str(arguments[key]).strip().lower()
            for key in _FILTERABLE
            if arguments.get(key) not in (None, "")
        }
        if not filters:
            return {
                "status": "error",
                "error": "Provide at least one filter: "
                + ", ".join(_FILTERABLE),
            }

        source_url, records, err = _load_records(self.timeout)
        if err is not None:
            return err

        matches = []
        for rec in records:
            summary = _summarize(rec)
            if all(
                (summary.get(key) or "").lower().find(value) != -1
                for key, value in filters.items()
            ):
                matches.append(summary)

        limit = self._limit(arguments)
        return {
            "status": "success",
            "data": matches[:limit],
            "metadata": {
                "filters": filters,
                "total_matching": len(matches),
                "returned": min(len(matches), limit),
                "snapshot_source": source_url,
                "source": "FDA Purple Book (purplebooksearch.fda.gov)",
            },
        }
