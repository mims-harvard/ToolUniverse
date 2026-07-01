"""
CellMarker 2.0 Tool

Provides access to the CellMarker 2.0 database for querying curated
cell type marker genes from single-cell RNA-seq and experimental studies.

CellMarker 2.0 is a comprehensive database of cell type markers curated
from >26,000 publications, covering >500 cell types across >400 tissue types
for human and mouse.

The CellMarker 2.0 web site was restructured and no longer exposes the JSP
search endpoints this tool previously scraped; the only public interface now is
the bulk marker download. This tool therefore downloads the full marker table
once (`Cell_marker_All.xlsx`), caches it on disk, and answers all queries
locally from the cached table.

Website: http://bio-bigdata.hrbmu.edu.cn/CellMarker/
No authentication required.

Reference: Hu et al., Nucleic Acids Research, 2023 (PMID: 36300619)
"""

import os
import tempfile
import threading
from typing import Dict, Any, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool


# Bulk marker table. The primary domain sometimes 404s the download path; the
# published IP mirror is used as a fallback.
_DOWNLOAD_URLS = [
    "http://bio-bigdata.hrbmu.edu.cn/CellMarker/CellMarker_download_files/file/Cell_marker_All.xlsx",
    "http://117.50.127.228/CellMarker/CellMarker_download_files/file/Cell_marker_All.xlsx",
]
_CACHE_PATH = os.path.join(tempfile.gettempdir(), "tooluniverse_cellmarker_all.xlsx")
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_DF = None  # cached pandas DataFrame (loaded once per process)
_LOAD_LOCK = threading.Lock()


def _download_marker_table(timeout: int) -> None:
    """Download the bulk marker table to the on-disk cache."""
    last_err: Optional[Exception] = None
    for url in _DOWNLOAD_URLS:
        try:
            resp = requests.get(
                url, headers={"User-Agent": _BROWSER_UA}, timeout=timeout
            )
            resp.raise_for_status()
            with open(_CACHE_PATH, "wb") as fh:
                fh.write(resp.content)
            return
        except requests.RequestException as err:  # try the next mirror
            last_err = err
    raise RuntimeError(f"Could not download the CellMarker marker table: {last_err}")


def _load_dataframe(timeout: int = 180):
    """Load (and cache) the CellMarker marker table as a normalized DataFrame."""
    global _DF
    if _DF is not None:
        return _DF
    with _LOAD_LOCK:
        if _DF is not None:
            return _DF
        import pandas as pd

        if not os.path.exists(_CACHE_PATH) or os.path.getsize(_CACHE_PATH) == 0:
            _download_marker_table(timeout)

        df = pd.read_excel(
            _CACHE_PATH,
            usecols=[
                "species",
                "tissue_class",
                "tissue_type",
                "cancer_type",
                "cell_type",
                "cell_name",
                "marker",
                "Symbol",
                "marker_source",
            ],
        )
        # Marker gene symbol: prefer the curated Symbol, fall back to marker.
        df["cell_marker"] = (
            df["Symbol"].fillna(df["marker"]).fillna("").astype(str).str.strip()
        )
        df["source"] = df["marker_source"].fillna("").astype(str).str.strip()
        for col in ("species", "tissue_class", "tissue_type", "cell_type", "cell_name"):
            df[col] = df[col].fillna("").astype(str).str.strip()
        # "supports" = number of curated records for the same marker/cell/tissue,
        # i.e. how many studies back the marker–cell assignment.
        df["supports"] = df.groupby(
            ["species", "tissue_type", "cell_name", "cell_marker"]
        )["cell_marker"].transform("size")
        _DF = df
        return _DF


def _records(df, limit: int = 200) -> List[Dict[str, Any]]:
    """Convert a filtered DataFrame to the tool's record dict list."""
    out = []
    for _, row in df.head(limit).iterrows():
        out.append(
            {
                "species": row["species"],
                "tissue_class": row["tissue_class"],
                "tissue_type": row["tissue_type"],
                "cell_type": row["cell_type"],
                "cell_name": row["cell_name"],
                "cell_marker": row["cell_marker"],
                "source": row["source"],
                "supports": int(row["supports"]),
            }
        )
    return out


def _apply_species(df, species: Optional[str]):
    if species:
        return df[df["species"].str.lower() == species.strip().lower()]
    return df


def _apply_tissue(df, tissue_type: Optional[str]):
    if tissue_type:
        t = tissue_type.strip().lower()
        return df[
            df["tissue_type"].str.lower().str.contains(t, regex=False)
            | df["tissue_class"].str.lower().str.contains(t, regex=False)
        ]
    return df


@register_tool("CellMarkerTool")
class CellMarkerTool(BaseTool):
    """
    Tool for querying the CellMarker 2.0 cell type marker database.

    Supported operations:
    - search_by_gene: Find cell types that express a given marker gene
    - search_by_cell_type: Find marker genes for a specific cell type
    - list_cell_types: List available cell types in a tissue
    - search_cancer_markers: Search cancer-specific cell markers
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.timeout = 180

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "search_by_gene": self._search_by_gene,
            "search_by_cell_type": self._search_by_cell_type,
            "list_cell_types": self._list_cell_types,
            "search_cancer_markers": self._search_cancer_markers,
        }
        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}".format(operation),
                "available_operations": list(handlers.keys()),
            }

        try:
            df = _load_dataframe(self.timeout)
            return handler(arguments, df)
        except Exception as e:  # noqa: BLE001 - report any failure via the envelope
            return {"status": "error", "error": "CellMarker error: {}".format(str(e))}

    def _search_by_gene(self, arguments, df) -> Dict[str, Any]:
        gene_symbol = arguments.get("gene_symbol")
        if not gene_symbol:
            return {
                "status": "error",
                "error": "Missing required parameter: gene_symbol",
            }
        species = arguments.get("species")
        tissue_type = arguments.get("tissue_type")

        sub = df[df["cell_marker"].str.lower() == gene_symbol.strip().lower()]
        sub = _apply_species(sub, species)
        sub = _apply_tissue(sub, tissue_type)

        return {
            "status": "success",
            "data": {
                "gene_symbol": gene_symbol,
                "species": species if species else "all",
                "total_records": int(len(sub)),
                "records": _records(sub),
            },
        }

    def _search_by_cell_type(self, arguments, df) -> Dict[str, Any]:
        cell_name = arguments.get("cell_name")
        if not cell_name:
            return {"status": "error", "error": "Missing required parameter: cell_name"}
        species = arguments.get("species")
        tissue_type = arguments.get("tissue_type")

        sub = df[
            df["cell_name"]
            .str.lower()
            .str.contains(cell_name.strip().lower(), regex=False)
        ]
        sub = _apply_species(sub, species)
        sub = _apply_tissue(sub, tissue_type)

        marker_genes = sorted(m for m in sub["cell_marker"].unique() if m)
        return {
            "status": "success",
            "data": {
                "cell_name": cell_name,
                "species": species if species else "all",
                "total_records": int(len(sub)),
                "unique_markers": len(marker_genes),
                "marker_genes": marker_genes[:500],
                "records": _records(sub),
            },
        }

    def _list_cell_types(self, arguments, df) -> Dict[str, Any]:
        tissue_type = arguments.get("tissue_type")
        species = arguments.get("species", "Human")
        cell_class = arguments.get("cell_class")

        sub = _apply_species(df, species)
        sub = _apply_tissue(sub, tissue_type)
        if cell_class and cell_class.strip().lower() == "cancer":
            sub = sub[sub["cell_type"] == "Cancer cell"]

        seen = {}
        for _, row in sub.iterrows():
            name = row["cell_name"]
            if name and name not in seen:
                seen[name] = {"cell_name": name, "tissue_class": row["tissue_class"]}
        cell_types = list(seen.values())

        return {
            "status": "success",
            "data": {
                "species": species if species else "all",
                "tissue_type": tissue_type if tissue_type else "all",
                "total_cell_types": len(cell_types),
                "cell_types": cell_types,
            },
        }

    def _search_cancer_markers(self, arguments, df) -> Dict[str, Any]:
        cancer_type = arguments.get("cancer_type")
        gene_symbol = arguments.get("gene_symbol")
        cell_type = arguments.get("cell_type")

        if not any([cancer_type, gene_symbol, cell_type]):
            return {
                "status": "error",
                "error": "At least one parameter required: cancer_type, gene_symbol, or cell_type",
            }

        sub = df[df["cell_type"] == "Cancer cell"]
        if gene_symbol:
            sub = sub[sub["cell_marker"].str.lower() == gene_symbol.strip().lower()]
        if cancer_type:
            sub = _apply_tissue(sub, cancer_type)
        if cell_type:
            sub = sub[
                sub["cell_name"]
                .str.lower()
                .str.contains(cell_type.strip().lower(), regex=False)
            ]

        query = {}
        if cancer_type:
            query["cancer_type"] = cancer_type
        if gene_symbol:
            query["gene_symbol"] = gene_symbol
        if cell_type:
            query["cell_type"] = cell_type

        return {
            "status": "success",
            "data": {
                "query": query,
                "total_records": int(len(sub)),
                "records": _records(sub),
            },
        }
