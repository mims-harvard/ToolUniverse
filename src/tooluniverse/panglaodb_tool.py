# panglaodb_tool.py
"""
PanglaoDB cell-type marker gene tool for ToolUniverse.

PanglaoDB (https://panglaodb.se) is a curated database of cell-type marker
genes for single-cell RNA-seq annotation. The canonical marker table contains
8,286 records covering 178 cell types across 30 organs, with per-gene
sensitivity and specificity metrics for human and mouse.

This tool wraps the static, public marker table that PanglaoDB distributes at
    https://panglaodb.se/markers/PanglaoDB_markers_27_Mar_2020.tsv.gz
PanglaoDB has no JSON REST API; this gzipped TSV is the canonical machine
readable distribution. The file is downloaded once per process and cached in
memory, then queried locally for marker lookups.

No authentication required.
"""

import csv
import gzip
import io
import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

PANGLAODB_MARKERS_URL = (
    "https://panglaodb.se/markers/PanglaoDB_markers_27_Mar_2020.tsv.gz"
)

# A real browser User-Agent is required; the server rejects the default
# python-requests UA on some paths.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
}


def _to_float(value: Optional[str]) -> Optional[float]:
    """Parse a PanglaoDB numeric cell; 'NA'/''/None -> None."""
    if value is None:
        return None
    value = value.strip()
    if value == "" or value.upper() == "NA":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _species_tokens(raw: Optional[str]) -> List[str]:
    """Normalize the PanglaoDB 'species' cell into tokens ('Hs', 'Mm')."""
    if not raw:
        return []
    return [tok for tok in raw.split() if tok in ("Hs", "Mm")]


@register_tool("PanglaoDBMarkerTool")
class PanglaoDBMarkerTool(BaseTool):
    """
    Tool for querying PanglaoDB curated cell-type marker genes.

    Three operations (selected via the 'operation' field in the tool config):
      - markers_for_cell_type: marker genes for a given cell type
      - cell_types_for_gene:   which cell types a gene marks (reverse lookup)
      - list_cell_types:       catalog of cell types and organs

    No authentication required.
    """

    # Class-level cache so the marker table is downloaded/parsed at most once
    # per process and shared across all PanglaoDB tool instances.
    _MARKER_ROWS: Optional[List[Dict[str, Any]]] = None

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "markers_for_cell_type"
        )

    def _load_markers(self) -> List[Dict[str, Any]]:
        """Download and parse the PanglaoDB marker table (cached)."""
        if PanglaoDBMarkerTool._MARKER_ROWS is not None:
            return PanglaoDBMarkerTool._MARKER_ROWS

        response = requests.get(
            PANGLAODB_MARKERS_URL, headers=_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        text = gzip.decompress(response.content).decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")

        rows: List[Dict[str, Any]] = []
        for r in reader:
            rows.append(
                {
                    "gene_symbol": (r.get("official gene symbol") or "").strip(),
                    "cell_type": (r.get("cell type") or "").strip(),
                    "organ": (r.get("organ") or "").strip(),
                    "germ_layer": (r.get("germ layer") or "").strip() or None,
                    "species": (r.get("species") or "").strip(),
                    "species_tokens": _species_tokens(r.get("species")),
                    "canonical_marker": (r.get("canonical marker") or "").strip()
                    == "1",
                    "nicknames": (r.get("nicknames") or "").strip() or None,
                    "product_description": (r.get("product description") or "").strip()
                    or None,
                    "gene_type": (r.get("gene type") or "").strip() or None,
                    "ubiquitousness_index": _to_float(r.get("ubiquitousness index")),
                    "sensitivity_human": _to_float(r.get("sensitivity_human")),
                    "sensitivity_mouse": _to_float(r.get("sensitivity_mouse")),
                    "specificity_human": _to_float(r.get("specificity_human")),
                    "specificity_mouse": _to_float(r.get("specificity_mouse")),
                }
            )

        PanglaoDBMarkerTool._MARKER_ROWS = rows
        return rows

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the requested PanglaoDB lookup."""
        if arguments is None:
            arguments = {}
        try:
            rows = self._load_markers()
            if self.operation == "markers_for_cell_type":
                return self._markers_for_cell_type(arguments, rows)
            if self.operation == "cell_types_for_gene":
                return self._cell_types_for_gene(arguments, rows)
            if self.operation == "list_cell_types":
                return self._list_cell_types(arguments, rows)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PanglaoDB request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to panglaodb.se. Check network.",
            }
        except Exception as e:  # never raise to caller
            return {
                "status": "error",
                "error": f"Error querying PanglaoDB: {str(e)}",
            }

    @staticmethod
    def _species_matches(row: Dict[str, Any], species: Optional[str]) -> bool:
        """Filter a row by requested species ('human'/'Hs' or 'mouse'/'Mm')."""
        if not species:
            return True
        s = species.strip().lower()
        if s in ("human", "hs", "homo sapiens"):
            return "Hs" in row["species_tokens"]
        if s in ("mouse", "mm", "mus musculus"):
            return "Mm" in row["species_tokens"]
        # Unknown species string -> do not filter out.
        return True

    def _markers_for_cell_type(
        self, arguments: Dict[str, Any], rows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Return marker genes for a given cell type."""
        cell_type = (arguments.get("cell_type") or "").strip()
        if not cell_type:
            return {
                "status": "error",
                "error": "cell_type is required (e.g., 'B cells', 'Hepatocytes'). "
                "Use list_cell_types to see available cell types.",
            }

        ct_lower = cell_type.lower()
        species = arguments.get("species")
        organ = arguments.get("organ")
        canonical_only = bool(arguments.get("canonical_only", False))

        matches = [
            r
            for r in rows
            if r["cell_type"].lower() == ct_lower
            and self._species_matches(r, species)
            and (not organ or r["organ"].lower() == organ.strip().lower())
            and (not canonical_only or r["canonical_marker"])
        ]

        # Sort canonical markers first, then by descending human specificity.
        matches.sort(
            key=lambda r: (
                0 if r["canonical_marker"] else 1,
                -(r["specificity_human"] if r["specificity_human"] is not None else -1),
            )
        )

        total = len(matches)
        limit = arguments.get("limit", 50)
        if isinstance(limit, int) and limit > 0:
            matches = matches[:limit]

        data = [self._format_marker(r) for r in matches]
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "PanglaoDB (panglaodb.se)",
                "cell_type": cell_type,
                "species_filter": species,
                "organ_filter": organ,
                "canonical_only": canonical_only,
                "total_matching": total,
                "returned": len(data),
            },
        }

    def _cell_types_for_gene(
        self, arguments: Dict[str, Any], rows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Reverse lookup: which cell types is a gene a marker for."""
        gene = (arguments.get("gene") or "").strip()
        if not gene:
            return {
                "status": "error",
                "error": "gene is required (official human gene symbol, e.g., 'CD19').",
            }

        gene_upper = gene.upper()
        species = arguments.get("species")
        matches = [
            r
            for r in rows
            if r["gene_symbol"].upper() == gene_upper
            and self._species_matches(r, species)
        ]

        matches.sort(
            key=lambda r: -(
                r["specificity_human"] if r["specificity_human"] is not None else -1
            )
        )

        total = len(matches)
        limit = arguments.get("limit", 50)
        if isinstance(limit, int) and limit > 0:
            matches = matches[:limit]

        data = [self._format_marker(r) for r in matches]
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "PanglaoDB (panglaodb.se)",
                "gene": gene,
                "species_filter": species,
                "total_matching": total,
                "returned": len(data),
            },
        }

    def _list_cell_types(
        self, arguments: Dict[str, Any], rows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """List available cell types (optionally filtered by organ)."""
        organ = arguments.get("organ")
        organ_lower = organ.strip().lower() if organ else None

        agg: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            if organ_lower and r["organ"].lower() != organ_lower:
                continue
            ct = r["cell_type"]
            if not ct:
                continue
            entry = agg.setdefault(
                ct,
                {"cell_type": ct, "organs": set(), "marker_count": 0},
            )
            if r["organ"]:
                entry["organs"].add(r["organ"])
            entry["marker_count"] += 1

        data = [
            {
                "cell_type": e["cell_type"],
                "organs": sorted(e["organs"]),
                "marker_count": e["marker_count"],
            }
            for e in agg.values()
        ]
        data.sort(key=lambda e: e["cell_type"].lower())

        all_organs = sorted({r["organ"] for r in rows if r["organ"]})
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "PanglaoDB (panglaodb.se)",
                "organ_filter": organ,
                "num_cell_types": len(data),
                "all_organs": all_organs,
            },
        }

    @staticmethod
    def _format_marker(r: Dict[str, Any]) -> Dict[str, Any]:
        """Project an internal row to the public output shape."""
        return {
            "gene_symbol": r["gene_symbol"],
            "cell_type": r["cell_type"],
            "organ": r["organ"],
            "germ_layer": r["germ_layer"],
            "species": r["species"],
            "canonical_marker": r["canonical_marker"],
            "nicknames": r["nicknames"],
            "product_description": r["product_description"],
            "gene_type": r["gene_type"],
            "ubiquitousness_index": r["ubiquitousness_index"],
            "sensitivity_human": r["sensitivity_human"],
            "sensitivity_mouse": r["sensitivity_mouse"],
            "specificity_human": r["specificity_human"],
            "specificity_mouse": r["specificity_mouse"],
        }
