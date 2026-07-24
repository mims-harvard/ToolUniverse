"""UniBind REST API tool.

UniBind (https://unibind.uio.no) is a database of curated, experimentally
derived **direct** transcription factor-DNA binding sites (TFBS), predicted
from ChIP-seq peaks using the DAMO / ChIP-eat pipeline together with JASPAR
profiles. Each "dataset" corresponds to one ChIP-seq experiment for one TF in
one cell type/condition, and exposes the high-confidence TFBS positions
(BED/FASTA), the JASPAR motif(s) used, CentriMo enrichment p-values, score
thresholds and total TFBS counts.

This is distinct from existing ToolUniverse motif tools:
  * JASPAR  -> position frequency MATRICES (the motif models themselves).
  * HOCOMOCO -> position weight matrices for TFs.
  * ReMap   -> raw ChIP-seq peak regions (genomic intervals of binding).
UniBind sits between them: motif-anchored, experimentally supported, direct
TF-DNA binding sites at base-pair resolution, organised per experiment.

Public, no API key. Django REST Framework backend; endpoints require a
trailing slash and ``?format=json``.
"""

import requests
from typing import Any, Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool

UNIBIND_BASE = "https://unibind.uio.no/api/v1"


@register_tool("UniBindRESTTool")
class UniBindRESTTool(BaseTool):
    """Access curated direct TF-DNA binding sites from the UniBind database.

    A single class dispatches three tools via the ``operation`` field declared
    in each JSON config (or passed as an argument):

      * ``search_datasets`` -> filter the TFBS dataset catalog.
      * ``get_dataset``     -> full binding-site detail for one dataset.
      * ``list_tfs``        -> list/filter the catalog of profiled TFs.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "search_datasets")

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", self.operation)
        try:
            if operation == "get_dataset":
                return self._get_dataset(arguments)
            if operation == "list_tfs":
                return self._list_tfs(arguments)
            return self._search_datasets(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "UniBind API request timed out after 30 seconds.",
            }
        except requests.exceptions.RequestException as exc:
            return {
                "status": "error",
                "error": f"UniBind API request failed: {exc}",
            }
        except Exception as exc:  # noqa: BLE001 - never raise to the caller
            return {
                "status": "error",
                "error": f"Unexpected error querying UniBind: {exc}",
            }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _get_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params)
        params["format"] = "json"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _int_arg(
        arguments: Dict[str, Any], key: str, default: int, lo: int, hi: int
    ) -> int:
        try:
            val = int(arguments.get(key, default))
        except (TypeError, ValueError):
            val = default
        return max(lo, min(hi, val))

    # ------------------------------------------------------------------ #
    # search_datasets
    # ------------------------------------------------------------------ #
    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Filter the UniBind dataset catalog.

        Server-side filters (all optional, all compose): ``tf_name``,
        ``species`` (scientific name, e.g. 'Homo sapiens'), ``cell_line``
        (cell type/tissue), ``collection`` ('Robust' or 'Permissive').
        """
        filters: Dict[str, Any] = {}
        for key in ("tf_name", "species", "cell_line", "collection"):
            val = arguments.get(key)
            if val:
                filters[key] = val

        page = self._int_arg(arguments, "page", 1, 1, 10_000_000)
        page_size = self._int_arg(arguments, "page_size", 25, 1, 1000)

        params = dict(filters)
        order = arguments.get("order")
        if order:
            params["order"] = order
        params["page"] = page
        params["page_size"] = page_size

        data = self._get_json(f"{UNIBIND_BASE}/datasets/", params)

        results: List[Dict[str, Any]] = []
        for row in data.get("results", []) or []:
            results.append(
                {
                    "tf_name": row.get("tf_name"),
                    "total_peaks": row.get("total_peaks"),
                    "dataset_url": row.get("url"),
                    "dataset_id": self._dataset_id_from_url(row.get("url")),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_count": data.get("count"),
                "returned": len(results),
                "page": page,
                "page_size": page_size,
                "has_next": bool(data.get("next")),
                "filters": filters,
                "source": "UniBind (unibind.uio.no)",
            },
        }

    @staticmethod
    def _dataset_id_from_url(url: Any) -> Any:
        """Extract the dataset identifier from a dataset detail URL."""
        if not url or not isinstance(url, str):
            return None
        trimmed = url.rstrip("/")
        # Detail URLs end in /datasets/<id>; list-link URLs end in ?tf_name=...
        if "/datasets/" in trimmed and "?" not in trimmed:
            return trimmed.rsplit("/datasets/", 1)[-1]
        return None

    # ------------------------------------------------------------------ #
    # get_dataset
    # ------------------------------------------------------------------ #
    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Full binding-site detail for one UniBind dataset.

        ``dataset_id`` is the UniBind dataset identifier, e.g.
        ``EXP030726.neural_stem_cells.SMAD3`` (visible as ``dataset_id`` /
        ``dataset_url`` in search_datasets results).
        """
        dataset_id = arguments.get("dataset_id")
        if not dataset_id or not str(dataset_id).strip():
            return {
                "status": "error",
                "error": "Missing required argument 'dataset_id'.",
            }
        dataset_id = str(dataset_id).strip().rstrip("/")

        url = f"{UNIBIND_BASE}/datasets/{dataset_id}/"
        resp = self.session.get(url, params={"format": "json"}, timeout=self.timeout)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"UniBind dataset '{dataset_id}' not found.",
            }
        resp.raise_for_status()
        raw = resp.json()

        tfbs_models = self._flatten_tfbs(raw.get("tfbs", []) or [])

        data = {
            "dataset_id": raw.get("tf_id") or dataset_id,
            "tf_name": raw.get("tf_name"),
            "cell_line": raw.get("cell_line") or [],
            "biological_condition": raw.get("biological_condition") or [],
            "identifier": raw.get("identifier") or [],
            "jaspar_id": raw.get("jaspar_id") or [],
            "prediction_models": raw.get("prediction_models") or [],
            "tfbs_models": tfbs_models,
        }
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "n_tfbs_models": len(tfbs_models),
                "source": "UniBind (unibind.uio.no)",
            },
        }

    @staticmethod
    def _flatten_tfbs(tfbs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten the nested ``tfbs`` -> {model_name: [entries]} structure.

        UniBind nests TFBS predictions by prediction model (e.g. 'DAMO'); each
        model maps to a list of per-JASPAR-motif binding-site result blocks.
        """
        flat: List[Dict[str, Any]] = []
        for block in tfbs:
            if not isinstance(block, dict):
                continue
            for model_name, entries in block.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    flat.append(
                        {
                            "prediction_model": model_name,
                            "jaspar_id": entry.get("jaspar_id"),
                            "jaspar_version": entry.get("jaspar_version"),
                            "total_tfbs": entry.get("total_tfbs"),
                            "score_threshold": entry.get("score_threshold"),
                            "distance_threshold": entry.get("distance_threshold"),
                            "adj_centrimo_pvalue": entry.get("adj_centrimo_pvalue"),
                            "bed_url": entry.get("bed_url"),
                            "fasta_url": entry.get("fasta_url"),
                            "summary_plot_url": entry.get("summary_plot_url"),
                        }
                    )
        return flat

    # ------------------------------------------------------------------ #
    # list_tfs
    # ------------------------------------------------------------------ #
    def _list_tfs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the catalog of TFs profiled in UniBind.

        The UniBind ``/tfs/`` endpoint ignores its ``search`` parameter and
        always returns the full list, so any ``search`` term is applied as a
        case-insensitive client-side substring filter on the TF name.
        """
        # Pull the full TF list (592 entries -> one page with page_size=1000).
        data = self._get_json(f"{UNIBIND_BASE}/tfs/", {"page_size": 1000, "page": 1})
        rows = data.get("results", []) or []
        names = [r.get("tf_name") for r in rows if r.get("tf_name")]

        search = arguments.get("search")
        if search:
            needle = str(search).strip().lower()
            names = [n for n in names if needle in n.lower()]

        names = sorted(set(names))
        limit = self._int_arg(arguments, "limit", 200, 1, 1000)
        truncated = len(names) > limit
        names = names[:limit]

        return {
            "status": "success",
            "data": names,
            "metadata": {
                "total_tfs_in_unibind": data.get("count"),
                "returned": len(names),
                "search": search,
                "truncated": truncated,
                "source": "UniBind (unibind.uio.no)",
            },
        }
