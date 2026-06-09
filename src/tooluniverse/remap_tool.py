import re
import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


# Real ReMap REST API (region-based TR-binding peak retrieval).
REMAP_REST_BASE = "https://remap-rest.univ-amu.fr/api/V1"
# Match "chr1:1000000-1100000" (chrom may be e.g. chrX / chr1 / 1).
_REGION_RE = re.compile(r"^(chr)?[\w]+:\d+-\d+$", re.IGNORECASE)


@register_tool("ReMapRESTTool")
class ReMapRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30
        fields = tool_config.get("fields", {})
        self.endpoint_template = fields.get(
            "endpoint",
            "https://www.encodeproject.org/search/?type=Experiment&assay_title=TF+ChIP-seq&target.label={gene_name}&biosample_ontology.term_name={cell_type}&format=json&limit={limit}",
        )
        # Optional operation hint from config (defaults to legacy ENCODE search).
        self.operation = fields.get("operation", "")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Dispatch: the region-peak operation queries the real ReMap catalog;
        # everything else preserves the legacy ENCODE experiment search so the
        # existing ReMap_get_transcription_factor_binding tool is unchanged.
        operation = arguments.get("operation", self.operation)
        if operation == "get_peaks_in_region":
            return self._get_peaks_in_region(arguments)
        return self._encode_tf_binding(arguments)

    def _get_peaks_in_region(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve all ReMap TR-binding peaks overlapping a genomic region."""
        try:
            region = str(arguments.get("region", "")).strip().replace(",", "")
            if not region:
                return {
                    "status": "error",
                    "error": "region is required (e.g. chr1:1000000-1100000)",
                }
            if not _REGION_RE.match(region):
                return {
                    "status": "error",
                    "error": f"Invalid region format: '{region}'. Use chrom:start-end (e.g. chr1:1000000-1100000).",
                }

            version = str(arguments.get("version", "2022"))
            assembly = str(arguments.get("assembly", "hg38"))
            datatype = str(arguments.get("datatype", "all"))
            limit = arguments.get("limit")

            url = f"{REMAP_REST_BASE}/get_peaks/{version}/{assembly}/{datatype}/{region}?format=json"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            resp_data = response.json()

            raw_peaks = resp_data.get("peaks", []) or []
            peaks = []
            tfs = set()
            for entry in raw_peaks:
                pv = entry.get("peakValues", entry) if isinstance(entry, dict) else {}
                name = pv.get("name", {}) if isinstance(pv, dict) else {}
                if not isinstance(name, dict):
                    name = {}
                treatments = name.get("Treatments", {})
                treat_list = (
                    treatments.get("data", [])
                    if isinstance(treatments, dict)
                    else (treatments if isinstance(treatments, list) else [])
                )
                tf = name.get("TF")
                if tf:
                    tfs.add(tf)
                peaks.append(
                    {
                        "chrom": pv.get("chrom"),
                        "chromStart": pv.get("chromStart"),
                        "chromEnd": pv.get("chromEnd"),
                        "experiment": name.get("Experiment"),
                        "tf": tf,
                        "biotype": name.get("Biotype"),
                        "treatments": treat_list,
                    }
                )

            if limit is not None:
                try:
                    peaks = peaks[: max(1, int(limit))]
                except (TypeError, ValueError):
                    pass

            return {
                "status": "success",
                "data": {
                    "region": resp_data.get("region", region),
                    "assembly": resp_data.get("assembly", assembly),
                    "version": resp_data.get("version", version),
                    "datatype": resp_data.get("datatype", datatype),
                    "size": resp_data.get("size"),
                    "peak_count": len(raw_peaks),
                    "returned_count": len(peaks),
                    "unique_tf_count": len(tfs),
                    "unique_tfs": sorted(tfs),
                    "peaks": peaks,
                    "url": url,
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "ReMap REST request timed out (region may be too large). Try a smaller interval.",
            }
        except Exception as e:
            return {"status": "error", "error": f"ReMap REST API error: {str(e)}"}

    def _encode_tf_binding(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            gene_name = arguments.get("gene_name", "")
            if not gene_name:
                return {"status": "error", "error": "gene_name is required"}
            cell_type = arguments.get("cell_type", "HepG2")
            limit = min(int(arguments.get("limit", 10)), 50)

            url = self.endpoint_template.format(
                gene_name=gene_name,
                cell_type=cell_type,
                limit=limit,
            )

            response = self.session.get(url, timeout=self.timeout)
            # ENCODE returns HTTP 404 when the search yields zero results;
            # treat that as an empty result set rather than a hard error.
            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": {
                        "experiments": [],
                        "count": 0,
                        "gene_name": gene_name,
                        "cell_type": cell_type,
                        "url": url,
                        "note": "No experiments found for this gene/cell-type combination.",
                    },
                }
            response.raise_for_status()
            resp_data = response.json()

            raw_experiments = resp_data.get("@graph", [])
            experiments = [
                {
                    "accession": e.get("accession"),
                    "assay_title": e.get("assay_title"),
                    "target": e.get("target"),
                    "biosample_ontology": e.get("biosample_ontology"),
                    "description": e.get("description"),
                    "status": e.get("status"),
                }
                for e in raw_experiments
            ]

            return {
                "status": "success",
                "data": {
                    "experiments": experiments,
                    "count": len(experiments),
                    "gene_name": gene_name,
                    "cell_type": cell_type,
                    "url": url,
                },
            }
        except Exception as e:
            return {"status": "error", "error": f"ReMap API error: {str(e)}"}
