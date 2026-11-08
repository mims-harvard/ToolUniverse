# pubchem_bioassay_tool.py
"""
PubChem BioAssay API tool for ToolUniverse.

PubChem BioAssay stores biological screening data submitted by depositors
through the BioAssay Submission system. Contains over 1.3 million assays
covering drug screening, toxicology, and biological pathway probing.

API: https://pubchem.ncbi.nlm.nih.gov/rest/pug/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Free text PubChem sends as a list of paragraphs, capped per row in a search
# page so one verbose assay cannot crowd out the other nineteen.
DESCRIPTION_CHARACTERS = 1200
_COUNT_SUFFIXES = (
    "All",
    "Active",
    "Inactive",
    "Inconclusive",
    "Unspecified",
    "Probe",
)


def _paragraphs(value: Any, cap: Optional[int] = None) -> tuple:
    """(text, truncated) from PubChem's list-of-paragraphs free text."""
    if isinstance(value, str):
        value = [value]
    text = "\n".join(str(v).strip() for v in (value or []) if str(v).strip())
    if not text:
        return None, False
    if cap is not None and len(text) > cap:
        return text[:cap].rstrip() + "...", True
    return text, False


def _counts(summary: Dict[str, Any], prefix: str) -> Optional[Dict[str, Any]]:
    """SIDCount*/CIDCount*: how much data the assay holds and how much of it
    was active - what tells a screen worth opening from an empty one."""
    out = {
        suffix.lower(): summary.get(f"{prefix}Count{suffix}")
        for suffix in _COUNT_SUFFIXES
    }
    return out if any(v is not None for v in out.values()) else None


def _last_data_change(summary: Dict[str, Any]) -> Optional[str]:
    change = summary.get("LastDataChange")
    if not isinstance(change, dict) or not change.get("Year"):
        return None
    return "%04d-%02d-%02d" % (
        int(change.get("Year")),
        int(change.get("Month") or 1),
        int(change.get("Day") or 1),
    )


@register_tool("PubChemBioAssayTool")
class PubChemBioAssayTool(BaseTool):
    """
    Tool for querying PubChem BioAssay data.

    Access biological assay descriptions, targets, and screening results
    from PubChem. Supports searching by assay ID, target gene, or keyword.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_assay")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PubChem BioAssay API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PubChem BioAssay request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to PubChem API."}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"PubChem API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying PubChem BioAssay: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_assay":
            return self._get_assay(arguments)
        elif self.endpoint == "search_by_gene":
            return self._search_by_gene(arguments)
        elif self.endpoint == "get_assay_summary":
            return self._get_assay_summary(arguments)
        elif self.endpoint == "concise_activity_table":
            return self._get_concise_activity_table(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_assay(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed description of a bioassay by its AID."""
        aid = arguments.get("aid")
        if not aid:
            return {"status": "error", "error": "aid (Assay ID) parameter is required"}

        url = f"{PUBCHEM_BASE_URL}/assay/aid/{aid}/description/JSON"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        containers = data.get("PC_AssayContainer", [])
        if not containers:
            return {"status": "error", "error": f"No assay found with AID {aid}"}

        assay = containers[0].get("assay", {}).get("descr", {})
        aid_info = assay.get("aid", {})
        source = assay.get("aid_source", {}).get("db", {})

        result = {
            "aid": aid_info.get("id"),
            "name": assay.get("name"),
            "source_name": source.get("name"),
            "description": assay.get("description", []),
            "protocol": assay.get("protocol", []),
            "comment": assay.get("comment", []),
        }

        # Extract target info if present
        targets = assay.get("target", [])
        if targets:
            result["targets"] = []
            for t in targets:
                mol_id = t.get("mol_id")
                target_entry = {
                    "name": t.get("name"),
                    "molecule_type": t.get("molecule_type"),
                }
                if mol_id:
                    target_entry["gi"] = mol_id.get("gi")
                result["targets"].append(target_entry)

        result["description_count"] = len(result["description"])
        result["protocol_count"] = len(result["protocol"])
        result["comment_count"] = len(result["comment"])

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PubChem BioAssay",
                "aid": str(aid),
            },
        }

    def _search_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for bioassays targeting a specific gene."""
        gene_symbol = arguments.get("gene_symbol", "")
        if not gene_symbol:
            return {
                "status": "error",
                "error": "gene_symbol parameter is required (e.g., 'TP53', 'EGFR')",
            }

        limit = max(1, min(int(arguments.get("limit", 20)), 100))
        offset = max(0, int(arguments.get("offset", 0)))

        url = f"{PUBCHEM_BASE_URL}/assay/target/genesymbol/{gene_symbol}/aids/JSON"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        aids_list = data.get("IdentifierList", {}).get("AID", [])

        page_aids = aids_list[offset : offset + limit]

        # Get summaries for these AIDs
        results = []
        if page_aids:
            aids_str = ",".join(str(a) for a in page_aids)
            try:
                summary_url = f"{PUBCHEM_BASE_URL}/assay/aid/{aids_str}/summary/JSON"
                sum_resp = requests.get(summary_url, timeout=self.timeout)
                sum_resp.raise_for_status()
                sum_data = sum_resp.json()

                summaries = sum_data.get("AssaySummaries", {}).get("AssaySummary", [])
                by_aid = {summary.get("AID"): summary for summary in summaries}
                for aid in page_aids:
                    summary = by_aid.get(aid)
                    if summary is None:
                        results.append({"aid": aid})
                        continue
                    targets = summary.get("Target", [])
                    target_names = (
                        [t.get("Name", "") for t in targets] if targets else []
                    )
                    description, description_truncated = _paragraphs(
                        summary.get("Description"), DESCRIPTION_CHARACTERS
                    )
                    results.append(
                        {
                            "aid": summary.get("AID"),
                            "name": summary.get("Name"),
                            "source": summary.get("SourceName"),
                            "source_id": summary.get("SourceID"),
                            "method": summary.get("Method"),
                            "targets": target_names,
                            "number_of_tids": summary.get("NumberOfTIDs"),
                            "has_score": summary.get("HasScore"),
                            "description": description,
                            "description_truncated": description_truncated,
                            "substance_counts": _counts(summary, "SID"),
                            "compound_counts": _counts(summary, "CID"),
                            "last_data_change": _last_data_change(summary),
                            "version": summary.get("Version"),
                            "revision": summary.get("Revision"),
                        }
                    )
            except Exception:
                # Fallback: just return the AID list
                results = [{"aid": a} for a in page_aids]

        has_more = offset + len(page_aids) < len(aids_list)

        return {
            "status": "success",
            "data": {
                "total_assays": len(aids_list),
                "offset": offset,
                "limit": limit,
                "returned": len(results),
                "has_more": has_more,
                "next_offset": offset + len(page_aids) if has_more else None,
                "assays": results,
            },
            "metadata": {
                "source": "PubChem BioAssay",
                "gene_symbol": gene_symbol,
                "description_characters": DESCRIPTION_CHARACTERS,
                "note": "compound_counts.active over compound_counts.all is "
                "the assay's hit rate. get_assay_summary returns the same "
                "assay's full description with its protocol and comment.",
                "total_assays": len(aids_list),
                "returned": len(results),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": offset + len(page_aids) if has_more else None,
            },
        }

    def _get_concise_activity_table(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get the assay-wide concise bioactivity table for an AID.

        Returns one row per tested compound (SID/CID) with Activity Outcome
        and Activity Value across ALL compounds in the assay (not just the
        active CID list and not SID-limited). Large assays can return
        hundreds of thousands of rows, so the row payload is capped while
        the true total row count is always reported.
        """
        aid = arguments.get("aid")
        if not aid:
            return {"status": "error", "error": "aid (Assay ID) parameter is required"}

        max_rows = arguments.get("max_rows", 1000)
        row_offset = arguments.get("row_offset", 0)
        try:
            max_rows = int(max_rows)
        except (TypeError, ValueError):
            max_rows = 1000
        if max_rows < 1:
            max_rows = 1
        if max_rows > 100000:
            max_rows = 100000
        if (
            isinstance(row_offset, bool)
            or not isinstance(row_offset, int)
            or row_offset < 0
        ):
            return {
                "status": "error",
                "error": "row_offset must be a non-negative integer",
            }

        url = f"{PUBCHEM_BASE_URL}/assay/aid/{aid}/concise/JSON"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        table = data.get("Table", {})
        columns = table.get("Columns", {}).get("Column", [])
        all_rows = table.get("Row", [])
        if not columns or not all_rows:
            return {
                "status": "error",
                "error": f"No concise activity table found for AID {aid}",
            }

        total_rows = len(all_rows)
        rows = []
        for row in all_rows[row_offset : row_offset + max_rows]:
            cells = row.get("Cell", [])
            rows.append(dict(zip(columns, cells)))

        next_row_offset = row_offset + len(rows)
        has_more = next_row_offset < total_rows

        return {
            "status": "success",
            "data": {
                "aid": int(aid) if str(aid).isdigit() else aid,
                "columns": columns,
                "total_rows": total_rows,
                "returned_rows": len(rows),
                "row_offset": row_offset,
                "max_rows": max_rows,
                "has_more": has_more,
                "next_row_offset": next_row_offset if has_more else None,
                "result_set_complete": row_offset == 0 and len(rows) == total_rows,
                "rows": rows,
            },
            "metadata": {
                "source": "PubChem BioAssay (concise activity table)",
                "aid": str(aid),
                "total_rows": total_rows,
                "returned_rows": len(rows),
                "row_offset": row_offset,
                "max_rows": max_rows,
                "has_more": has_more,
                "next_row_offset": next_row_offset if has_more else None,
                "truncated": row_offset > 0 or has_more,
            },
        }

    def _get_assay_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary and target information for a bioassay."""
        aid = arguments.get("aid")
        if not aid:
            return {"status": "error", "error": "aid (Assay ID) parameter is required"}

        url = f"{PUBCHEM_BASE_URL}/assay/aid/{aid}/summary/JSON"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        summaries = data.get("AssaySummaries", {}).get("AssaySummary", [])
        if not summaries:
            return {"status": "error", "error": f"No summary found for AID {aid}"}

        summary = summaries[0]
        targets = summary.get("Target", [])
        target_info = []
        for t in targets:
            target_info.append(
                {
                    "accession": t.get("Accession"),
                    "name": t.get("Name"),
                }
            )

        # Also get target gene info
        gene_info = []
        try:
            target_url = f"{PUBCHEM_BASE_URL}/assay/aid/{aid}/targets/ProteinGI,ProteinName,GeneID,GeneSymbol/JSON"
            t_resp = requests.get(target_url, timeout=self.timeout)
            t_resp.raise_for_status()
            t_data = t_resp.json()

            for info in t_data.get("InformationList", {}).get("Information", []):
                gene_symbols = info.get("GeneSymbol", [])
                gene_ids = info.get("GeneID", [])
                protein_names = info.get("ProteinName", [])
                gene_info.append(
                    {
                        "gene_symbols": gene_symbols,
                        "gene_ids": gene_ids,
                        "protein_names": protein_names,
                    }
                )
        except Exception:
            pass

        description, _ = _paragraphs(summary.get("Description"))
        protocol, _ = _paragraphs(summary.get("Protocol"))
        comment, _ = _paragraphs(summary.get("Comment"))
        result = {
            "aid": summary.get("AID"),
            "name": summary.get("Name"),
            "source": summary.get("SourceName"),
            "source_id": summary.get("SourceID"),
            "method": summary.get("Method"),
            "has_score": summary.get("HasScore"),
            "number_of_tids": summary.get("NumberOfTIDs"),
            "targets": target_info,
            "gene_targets": gene_info,
            # Whole text, not the first three paragraphs: the protocol's
            # readout and the comment's caveats are usually at the end.
            "description": description,
            "protocol": protocol,
            "comment": comment,
            "substance_counts": _counts(summary, "SID"),
            "compound_counts": _counts(summary, "CID"),
            "last_data_change": _last_data_change(summary),
            "version": summary.get("Version"),
            "revision": summary.get("Revision"),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PubChem BioAssay",
                "aid": str(aid),
            },
        }
