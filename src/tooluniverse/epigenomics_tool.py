# epigenomics_tool.py
"""
Epigenomics and methylation analysis tools for ToolUniverse.

Integrates data from:
- ENCODE Project (histone ChIP-seq, WGBS methylation, ATAC-seq, DNase-seq, annotations)
- UCSC Genome Browser (CpG islands, ENCODE4 cCREs, TF binding clusters)
- NCBI GEO (methylation array datasets, ChIP-seq datasets)
- Ensembl Regulatory Build (regulatory features, enhancers, promoters)

No authentication required for any of these APIs.
"""

import json
import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

ENCODE_BASE_URL = "https://www.encodeproject.org"
UCSC_API_URL = "https://api.genome.ucsc.edu"
NCBI_EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ENSEMBL_REST_URL = "https://rest.ensembl.org"


@register_tool("EpigenomicsTool")
class EpigenomicsTool(BaseTool):
    """
    Tool for epigenomics and methylation analysis across multiple databases.

    Supports:
    - ENCODE histone ChIP-seq, methylation (WGBS/RRBS), chromatin accessibility
    - ENCODE annotations (cCREs, chromatin states)
    - GEO methylation and ChIP-seq dataset search
    - Ensembl regulatory features

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "histone_chipseq")

    _ORGANISM_ALIASES = {
        "human": "Homo sapiens",
        "homo sapiens": "Homo sapiens",
        "mouse": "Mus musculus",
        "mus musculus": "Mus musculus",
        "rat": "Rattus norvegicus",
        "zebrafish": "Danio rerio",
        "fly": "Drosophila melanogaster",
        "worm": "Caenorhabditis elegans",
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the epigenomics API call."""
        # Normalize organism aliases to scientific names required by ENCODE API
        if "organism" in arguments:
            org = arguments["organism"].lower()
            if org in self._ORGANISM_ALIASES:
                arguments = dict(arguments, organism=self._ORGANISM_ALIASES[org])
        try:
            result = self._dispatch(arguments)
            if isinstance(result, dict) and "status" not in result:
                if "error" in result:
                    return {"status": "error", **result}
                return {"status": "success", **result}
            return result
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"API HTTP error: {status}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint == "histone_chipseq":
            return self._encode_histone_search(arguments)
        elif self.endpoint == "methylation":
            return self._encode_methylation_search(arguments)
        elif self.endpoint == "chromatin_accessibility":
            return self._encode_chromatin_accessibility_search(arguments)
        elif self.endpoint == "annotations":
            return self._encode_annotations_search(arguments)
        elif self.endpoint == "chromatin_state":
            return self._encode_chromatin_state_search(arguments)
        elif self.endpoint == "geo_methylation_search":
            return self._geo_methylation_search(arguments)
        elif self.endpoint == "geo_chipseq_search":
            return self._geo_chipseq_search(arguments)
        elif self.endpoint == "geo_dataset_details":
            return self._geo_dataset_details(arguments)
        elif self.endpoint == "ensembl_regulatory":
            return self._ensembl_regulatory_features(arguments)
        elif self.endpoint == "geo_rnaseq_search":
            return self._geo_rnaseq_search(arguments)
        elif self.endpoint == "geo_atacseq_search":
            return self._geo_atacseq_search(arguments)
        elif self.endpoint == "encode_rnaseq":
            return self._encode_rnaseq_search(arguments)
        elif self.endpoint == "encode_hic":
            return self._encode_hic_search(arguments)
        elif self.endpoint == "encode_microrna":
            return self._encode_microrna_search(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    # =========================================================================
    # ENCODE Search Tools
    # =========================================================================

    def _encode_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generic ENCODE search helper."""
        url = f"{ENCODE_BASE_URL}/search/"
        params["format"] = "json"
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _is_histone_mark(target: str) -> bool:
        """Return True if target looks like a histone modification (e.g. H3K27ac, H3K4me3)."""
        import re

        return bool(re.match(r"^H[1-4][A-Za-z0-9]", target))

    def _encode_histone_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENCODE histone or TF ChIP-seq experiments."""
        histone_mark = arguments.get("histone_mark") or arguments.get("target")

        # Auto-detect TF targets and route to the correct ENCODE assay type
        if histone_mark and not self._is_histone_mark(histone_mark):
            assay_title = "TF ChIP-seq"
        else:
            assay_title = "Histone ChIP-seq"

        params = {
            "type": "Experiment",
            "assay_title": assay_title,
            "status": "released",
        }

        if histone_mark:
            params["target.label"] = histone_mark

        biosample = (
            arguments.get("biosample_term_name")
            or arguments.get("biosample")
            or arguments.get("biosample_term")
            or arguments.get("cell_type")
            or arguments.get("tissue")
        )
        if biosample:
            params["biosample_ontology.term_name"] = biosample

        organism = arguments.get("organism", "Homo sapiens")
        if organism:
            params["replicates.library.biosample.organism.scientific_name"] = organism

        limit = arguments.get("limit", 25)
        params["limit"] = min(int(limit), 100)

        # Feature-70A-003: ambiguous/non-leaf biosample terms (e.g. "heart") combined with
        # the organism filter can produce HTTP 404 from ENCODE. Fall back without
        # the organism filter in that case.
        # Feature-79E: if biosample_term_name is not a valid ENCODE ontology term
        # (e.g. disease names like "AML"), both attempts 404; return empty with hint.
        try:
            raw = self._encode_search(params)
        except Exception:
            fallback_params = {
                k: v
                for k, v in params.items()
                if k != "replicates.library.biosample.organism.scientific_name"
            }
            try:
                raw = self._encode_search(fallback_params)
            except Exception:
                return {
                    "status": "success",
                    "data": [],
                    "metadata": {
                        "source": "ENCODE",
                        "total": 0,
                        "note": f"No results for biosample='{biosample}'. "
                        "ENCODE requires exact ontology names for cell lines or tissues "
                        "(e.g., 'K562', 'HepG2', 'liver', 'brain', 'breast epithelium', 'MCF-7'). "
                        "Common anatomy terms like 'breast' must be spelled as ENCODE uses them "
                        "(try 'breast epithelium', 'mammary gland', or a cell line like 'MCF-7'). "
                        "Use GEO_search_chipseq_datasets for disease-based searches.",
                    },
                }

        experiments = []
        for exp in raw.get("@graph", []):
            target = exp.get("target", {})
            mark = target.get("label", "") if isinstance(target, dict) else str(target)
            lab = exp.get("lab", {})
            lab_name = lab.get("title", "") if isinstance(lab, dict) else str(lab)

            experiments.append(
                {
                    "accession": exp.get("accession", ""),
                    "histone_mark": mark,
                    "biosample_summary": exp.get("biosample_summary", ""),
                    "status": exp.get("status", ""),
                    "lab": lab_name,
                    "date_released": exp.get("date_released"),
                }
            )

        return {
            "status": "success",
            "data": {
                "total": raw.get("total", 0),
                "experiments": experiments,
            },
            "metadata": {
                "source": "ENCODE Project (encodeproject.org)",
                "assay": assay_title,
                "histone_mark_filter": histone_mark,
                "organism": organism,
            },
        }

    def _encode_methylation_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENCODE methylation experiments (WGBS/RRBS)."""
        assay_type = arguments.get("assay_type", "WGBS")
        params = {
            "type": "Experiment",
            "assay_title": assay_type,
            "status": "released",
        }

        biosample = (
            arguments.get("biosample_term_name")
            or arguments.get("biosample")
            or arguments.get("biosample_term")
            or arguments.get("cell_type")
            or arguments.get("tissue")
        )
        if biosample:
            params["biosample_ontology.term_name"] = biosample

        organism = arguments.get("organism", "Homo sapiens")
        if organism:
            params["replicates.library.biosample.organism.scientific_name"] = organism

        limit = arguments.get("limit", 25)
        params["limit"] = min(int(limit), 100)

        raw = self._encode_search(params)

        experiments = []
        for exp in raw.get("@graph", []):
            lab = exp.get("lab", {})
            lab_name = lab.get("title", "") if isinstance(lab, dict) else str(lab)

            experiments.append(
                {
                    "accession": exp.get("accession", ""),
                    "assay_title": exp.get("assay_title", ""),
                    "biosample_summary": exp.get("biosample_summary", ""),
                    "status": exp.get("status", ""),
                    "lab": lab_name,
                }
            )

        return {
            "status": "success",
            "data": {
                "total": raw.get("total", 0),
                "experiments": experiments,
            },
            "metadata": {
                "source": "ENCODE Project (encodeproject.org)",
                "assay": assay_type,
                "organism": organism,
            },
        }

    def _encode_chromatin_accessibility_search(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search ENCODE chromatin accessibility experiments (ATAC-seq / DNase-seq)."""
        assay_type = arguments.get("assay_type", "ATAC-seq")
        params = {
            "type": "Experiment",
            "assay_title": assay_type,
            "status": "released",
        }

        biosample = (
            arguments.get("biosample_term_name")
            or arguments.get("biosample")
            or arguments.get("biosample_term")
            or arguments.get("cell_type")
            or arguments.get("tissue")
        )
        if biosample:
            params["biosample_ontology.term_name"] = biosample

        organism = arguments.get("organism", "Homo sapiens")
        if organism:
            params["replicates.library.biosample.organism.scientific_name"] = organism

        limit = arguments.get("limit", 25)
        params["limit"] = min(int(limit), 100)

        # Feature-70A-003: biosample+organism combos can 404; fall back without organism.
        try:
            raw = self._encode_search(params)
        except Exception:
            fallback_params = {
                k: v
                for k, v in params.items()
                if k != "replicates.library.biosample.organism.scientific_name"
            }
            try:
                raw = self._encode_search(fallback_params)
            except Exception:
                return {
                    "status": "success",
                    "data": [],
                    "metadata": {
                        "source": "ENCODE",
                        "total": 0,
                        "note": f"No results for biosample='{biosample}'. "
                        "ENCODE requires exact ontology names for cell lines or tissues "
                        "(e.g., 'K562', 'HepG2', 'liver', 'brain', 'breast epithelium', 'MCF-7'). "
                        "Use GEO_search_atacseq_datasets for disease-based searches.",
                    },
                }

        experiments = []
        for exp in raw.get("@graph", []):
            lab = exp.get("lab", {})
            lab_name = lab.get("title", "") if isinstance(lab, dict) else str(lab)

            experiments.append(
                {
                    "accession": exp.get("accession", ""),
                    "assay_title": exp.get("assay_title", ""),
                    "biosample_summary": exp.get("biosample_summary", ""),
                    "status": exp.get("status", ""),
                    "lab": lab_name,
                }
            )

        return {
            "status": "success",
            "data": {
                "total": raw.get("total", 0),
                "experiments": experiments,
            },
            "metadata": {
                "source": "ENCODE Project (encodeproject.org)",
                "assay": assay_type,
                "organism": organism,
            },
        }

    def _encode_annotations_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENCODE annotations (cCREs, chromatin states)."""
        annotation_type = arguments.get(
            "annotation_type", "candidate Cis-Regulatory Elements"
        )
        params = {
            "type": "Annotation",
            "annotation_type": annotation_type,
            "status": "released",
        }

        biosample = (
            arguments.get("biosample_term_name")
            or arguments.get("biosample")
            or arguments.get("biosample_term")
            or arguments.get("cell_type")
            or arguments.get("tissue")
        )
        if biosample:
            params["biosample_ontology.term_name"] = biosample

        organism = arguments.get("organism", "Homo sapiens")
        if organism:
            params["organism.scientific_name"] = organism

        assembly = arguments.get("assembly", "GRCh38")
        if assembly:
            params["assembly"] = assembly

        limit = arguments.get("limit", 25)
        params["limit"] = min(int(limit), 100)

        raw = self._encode_search(params)

        annotations = []
        for ann in raw.get("@graph", []):
            annotations.append(
                {
                    "accession": ann.get("accession", ""),
                    "annotation_type": ann.get("annotation_type"),
                    "description": ann.get("description", ""),
                    "biosample_summary": ann.get("biosample_summary"),
                    "status": ann.get("status", ""),
                }
            )

        return {
            "status": "success",
            "data": {
                "total": raw.get("total", 0),
                "annotations": annotations,
            },
            "metadata": {
                "source": "ENCODE Project (encodeproject.org)",
                "annotation_type": annotation_type,
                "organism": organism,
                "assembly": assembly,
            },
        }

    def _encode_chromatin_state_search(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search ENCODE chromatin state annotations (ChromHMM)."""
        params = {
            "type": "Annotation",
            "annotation_type": "chromatin state",
            "status": "released",
        }

        biosample = (
            arguments.get("biosample_term_name")
            or arguments.get("biosample")
            or arguments.get("biosample_term")
            or arguments.get("cell_type")
            or arguments.get("tissue")
        )
        if biosample:
            params["biosample_ontology.term_name"] = biosample

        organism = arguments.get("organism", "Homo sapiens")
        if organism:
            params["organism.scientific_name"] = organism

        limit = arguments.get("limit", 25)
        params["limit"] = min(int(limit), 100)

        raw = self._encode_search(params)

        annotations = []
        for ann in raw.get("@graph", []):
            annotations.append(
                {
                    "accession": ann.get("accession", ""),
                    "annotation_type": ann.get("annotation_type"),
                    "description": ann.get("description", ""),
                    "biosample_summary": ann.get("biosample_summary"),
                    "status": ann.get("status", ""),
                }
            )

        return {
            "status": "success",
            "data": {
                "total": raw.get("total", 0),
                "annotations": annotations,
            },
            "metadata": {
                "source": "ENCODE Project (encodeproject.org)",
                "annotation_type": "chromatin state",
                "organism": organism,
            },
        }

    # =========================================================================
    # GEO Search Tools
    # =========================================================================

    def _geo_esearch(self, term: str, limit: int = 20) -> Dict[str, Any]:
        """Search GEO datasets via NCBI E-utilities."""
        url = f"{NCBI_EUTILS_URL}/esearch.fcgi"
        params = {
            "db": "gds",
            "term": term,
            "retmax": min(int(limit), 100),
            "retmode": "json",
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _geo_esummary(self, ids: list) -> Dict[str, Any]:
        """Get summary for GEO dataset IDs via NCBI E-utilities."""
        if not ids:
            return {"result": {}}
        url = f"{NCBI_EUTILS_URL}/esummary.fcgi"
        params = {
            "db": "gds",
            "id": ",".join(str(i) for i in ids),
            "retmode": "json",
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _geo_methylation_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search GEO for methylation array datasets."""
        query = arguments.get("query", "")
        organism = arguments.get("organism", "Homo sapiens")
        limit = arguments.get("limit", 20)

        # Feature-70A-008: avoid double-adding "methylation" if query already contains it
        term_parts = [query]
        if "methylation" not in query.lower():
            term_parts.append("methylation")
        if organism:
            term_parts.append(f"{organism}[Organism]")
        term = " AND ".join(term_parts)

        search_result = self._geo_esearch(term, limit)
        esearch = search_result.get("esearchresult", {})
        total = int(esearch.get("count", 0))
        ids = esearch.get("idlist", [])

        datasets = []
        if ids:
            summary_result = self._geo_esummary(ids)
            result = summary_result.get("result", {})
            for uid in ids:
                uid_data = result.get(str(uid), {})
                if not isinstance(uid_data, dict) or "accession" not in uid_data:
                    continue
                # Filter out platform records (GPL) — only return dataset series (GSE)
                acc = uid_data.get("accession", "")
                if acc.startswith("GPL"):
                    continue
                datasets.append(
                    {
                        "accession": acc,
                        "title": uid_data.get("title", ""),
                        "summary": uid_data.get("summary", "")[:500],
                        "platform": uid_data.get("gpl"),
                        "organism": uid_data.get("taxon", ""),
                        "n_samples": uid_data.get("n_samples", 0),
                        "date_published": uid_data.get("pdat"),
                    }
                )

        return {
            "status": "success",
            "data": {
                "total": total,
                "datasets": datasets,
            },
            "metadata": {
                "source": "NCBI GEO (ncbi.nlm.nih.gov/geo)",
                "query": query,
                "search_term": term,
                "organism": organism,
            },
        }

    def _geo_chipseq_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search GEO for ChIP-seq datasets."""
        query = arguments.get("query", "")
        organism = arguments.get("organism", "Homo sapiens")
        limit = arguments.get("limit", 20)

        # Build search term with ChIP-seq context
        term_parts = [query, "ChIP-seq"]
        if organism:
            term_parts.append(f"{organism}[Organism]")
        term = " AND ".join(term_parts)

        search_result = self._geo_esearch(term, limit)
        esearch = search_result.get("esearchresult", {})
        total = int(esearch.get("count", 0))
        ids = esearch.get("idlist", [])

        datasets = []
        if ids:
            summary_result = self._geo_esummary(ids)
            result = summary_result.get("result", {})
            for uid in ids:
                uid_data = result.get(str(uid), {})
                if not isinstance(uid_data, dict) or "accession" not in uid_data:
                    continue
                # Filter out platform records (GPL) — only return dataset series (GSE)
                acc = uid_data.get("accession", "")
                if acc.startswith("GPL"):
                    continue
                datasets.append(
                    {
                        "accession": acc,
                        "title": uid_data.get("title", ""),
                        "summary": uid_data.get("summary", "")[:500],
                        "organism": uid_data.get("taxon", ""),
                        "n_samples": uid_data.get("n_samples", 0),
                        "date_published": uid_data.get("pdat"),
                    }
                )

        return {
            "status": "success",
            "data": {
                "total": total,
                "datasets": datasets,
            },
            "metadata": {
                "source": "NCBI GEO (ncbi.nlm.nih.gov/geo)",
                "query": query,
                "search_term": term,
                "organism": organism,
            },
        }

    def _geo_dataset_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed metadata for a GEO dataset."""
        geo_id = arguments.get("geo_id", "")
        if not geo_id:
            return {
                "status": "error",
                "error": "geo_id parameter is required (e.g., '200291249')",
            }

        summary_result = self._geo_esummary([geo_id])
        result = summary_result.get("result", {})
        uid_data = result.get(str(geo_id), {})

        if not isinstance(uid_data, dict) or "accession" not in uid_data:
            return {
                "status": "error",
                "error": f"Dataset with ID '{geo_id}' not found in GEO",
            }

        ftplink = uid_data.get("ftplink", "")
        suppfile = uid_data.get("suppfile", "")
        supp_data = []
        if ftplink:
            supp_data.append(ftplink)
        if suppfile:
            supp_data.append(suppfile)

        return {
            "status": "success",
            "data": {
                "accession": uid_data.get("accession", ""),
                "title": uid_data.get("title", ""),
                "summary": uid_data.get("summary", ""),
                "experiment_type": uid_data.get("gdstype"),
                "platform": uid_data.get("gpl"),
                "organism": uid_data.get("taxon", ""),
                "n_samples": uid_data.get("n_samples", 0),
                "date_published": uid_data.get("pdat"),
                "supplementary_data": supp_data if supp_data else None,
            },
            "metadata": {
                "source": "NCBI GEO (ncbi.nlm.nih.gov/geo)",
                "geo_id": geo_id,
            },
        }

    def _geo_rnaseq_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search GEO for RNA-seq datasets."""
        query = arguments.get("query", "")
        organism = arguments.get("organism", "Homo sapiens")
        limit = arguments.get("limit") or arguments.get("max_results") or 20

        term_parts = [query, "RNA-seq"]
        if organism:
            term_parts.append(f"{organism}[Organism]")
        term = " AND ".join(t for t in term_parts if t)

        search_result = self._geo_esearch(term, limit)
        esearch = search_result.get("esearchresult", {})
        total = int(esearch.get("count", 0))
        ids = esearch.get("idlist", [])

        datasets = []
        if ids:
            summary_result = self._geo_esummary(ids)
            result = summary_result.get("result", {})
            for uid in ids:
                uid_data = result.get(str(uid), {})
                if not isinstance(uid_data, dict) or "accession" not in uid_data:
                    continue
                acc = uid_data.get("accession", "")
                if acc.startswith("GPL"):
                    continue
                datasets.append(
                    {
                        "accession": acc,
                        "title": uid_data.get("title", ""),
                        "summary": uid_data.get("summary", "")[:500],
                        "organism": uid_data.get("taxon", ""),
                        "n_samples": uid_data.get("n_samples", 0),
                        "date_published": uid_data.get("pdat"),
                    }
                )

        return {
            "status": "success",
            "data": {
                "total": total,
                "datasets": datasets,
            },
            "metadata": {
                "source": "NCBI GEO (ncbi.nlm.nih.gov/geo)",
                "query": query,
                "search_term": term,
                "organism": organism,
            },
        }

    def _geo_atacseq_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search GEO for ATAC-seq datasets (chromatin accessibility)."""
        query = arguments.get("query", "")
        organism = arguments.get("organism", "Homo sapiens")
        limit = arguments.get("limit") or arguments.get("max_results") or 20

        term_parts = [query, "ATAC-seq"]
        if organism:
            term_parts.append(f"{organism}[Organism]")
        term = " AND ".join(t for t in term_parts if t)

        search_result = self._geo_esearch(term, limit)
        esearch = search_result.get("esearchresult", {})
        total = int(esearch.get("count", 0))
        ids = esearch.get("idlist", [])

        datasets = []
        if ids:
            summary_result = self._geo_esummary(ids)
            result = summary_result.get("result", {})
            for uid in ids:
                uid_data = result.get(str(uid), {})
                if not isinstance(uid_data, dict) or "accession" not in uid_data:
                    continue
                acc = uid_data.get("accession", "")
                if acc.startswith("GPL"):
                    continue
                datasets.append(
                    {
                        "accession": acc,
                        "title": uid_data.get("title", ""),
                        "summary": uid_data.get("summary", "")[:500],
                        "organism": uid_data.get("taxon", ""),
                        "n_samples": uid_data.get("n_samples", 0),
                        "date_published": uid_data.get("pdat"),
                    }
                )

        return {
            "status": "success",
            "data": {
                "total": total,
                "datasets": datasets,
            },
            "metadata": {
                "source": "NCBI GEO (ncbi.nlm.nih.gov/geo)",
                "query": query,
                "search_term": term,
                "organism": organism,
            },
        }

    def _encode_rnaseq_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENCODE RNA-seq experiments by biosample, organism, or assay type."""
        biosample = (
            arguments.get("biosample_term_name")
            or arguments.get("biosample")
            or arguments.get("cell_type")
            or arguments.get("tissue")
        )
        organism = arguments.get("organism", "Homo sapiens")
        assay_type = arguments.get("assay_type", "total RNA-seq")
        limit = arguments.get("limit", 25)

        # Normalize common aliases for ENCODE RNA-seq assay titles
        _assay_map = {
            "total": "total RNA-seq",
            "polya": "polyA plus RNA-seq",
            "poly-a": "polyA plus RNA-seq",
            "polyA": "polyA plus RNA-seq",
            "mirna": "microRNA-seq",
            "microrna": "microRNA-seq",
            "small": "small RNA-seq",
        }
        assay_type = _assay_map.get(assay_type.lower(), assay_type)

        params = {
            "type": "Experiment",
            "assay_title": assay_type,
            "status": "released",
        }
        if biosample:
            params["biosample_ontology.term_name"] = biosample
        if organism:
            params["replicates.library.biosample.organism.scientific_name"] = organism
        params["limit"] = min(int(limit), 100)

        try:
            raw = self._encode_search(params)
        except Exception:
            # Fall back without organism filter (mirrors histone search fix)
            fallback = {
                k: v
                for k, v in params.items()
                if k != "replicates.library.biosample.organism.scientific_name"
            }
            try:
                raw = self._encode_search(fallback)
            except Exception:
                return {
                    "status": "success",
                    "data": {"total": 0, "experiments": []},
                    "metadata": {
                        "source": "ENCODE",
                        "note": (
                            f"No results for biosample='{biosample}'. "
                            "ENCODE requires exact ontology names (e.g., 'K562', 'HepG2', 'liver')."
                        ),
                    },
                }

        # If no results and assay was 'total RNA-seq', retry with 'polyA plus RNA-seq'
        # Some cell lines (e.g. HeLa-S3) have no total RNA-seq but have polyA plus RNA-seq.
        if raw.get("total", 0) == 0 and biosample and assay_type == "total RNA-seq":
            polya_params = dict(params)
            polya_params["assay_title"] = "polyA plus RNA-seq"
            try:
                polya_raw = self._encode_search(polya_params)
                if polya_raw.get("total", 0) > 0:
                    raw = polya_raw
                    assay_type = "polyA plus RNA-seq"
            except Exception:
                pass

        experiments = []
        for exp in raw.get("@graph", []):
            experiments.append(
                {
                    "accession": exp.get("accession", ""),
                    "assay_title": exp.get("assay_title", ""),
                    "biosample_summary": exp.get("biosample_summary", ""),
                    "status": exp.get("status", ""),
                    "lab": exp.get("lab", {}).get("title", "")
                    if isinstance(exp.get("lab"), dict)
                    else "",
                    "date_released": exp.get("date_released"),
                }
            )

        metadata: Dict[str, Any] = {
            "source": "ENCODE Project (encodeproject.org)",
            "assay_type": assay_type,
            "organism": organism,
            "note": "Available assay types: 'total RNA-seq', 'polyA plus RNA-seq', 'small RNA-seq', 'microRNA-seq'.",
        }
        if raw.get("total", 0) == 0 and biosample:
            metadata["note"] = (
                f"No results for biosample='{biosample}' with assay_type='{assay_type}'. "
                "Try a different assay_type: 'polyA plus RNA-seq', 'small RNA-seq', 'microRNA-seq'. "
                "ENCODE requires exact ontology names (e.g., 'K562', 'HepG2', 'liver')."
            )
        return {
            "status": "success",
            "data": {
                "total": raw.get("total", 0),
                "experiments": experiments,
            },
            "metadata": metadata,
        }

    # =========================================================================
    # Ensembl Regulatory Features
    # =========================================================================

    def _ensembl_regulatory_features(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get Ensembl regulatory features for a genomic region."""
        species = arguments.get("species", "homo_sapiens")
        chrom = arguments.get("chrom", "")
        start = arguments.get("start")
        end = arguments.get("end")

        if not chrom or start is None or end is None:
            return {
                "status": "error",
                "error": "chrom, start, and end parameters are required",
            }

        # Ensure region is not too large (max 5Mb)
        if end - start > 5000000:
            return {
                "status": "error",
                "error": "Region too large. Maximum region size is 5 Mb.",
            }

        url = (
            f"{ENSEMBL_REST_URL}/overlap/region/{species}/{chrom}:{start}-{end}"
            f"?feature=regulatory;content-type=application/json"
        )
        # Ensembl REST API can be slow - use 90s timeout
        response = requests.get(url, timeout=max(self.timeout, 90))
        response.raise_for_status()
        raw = response.json()

        features = []
        for feat in raw:
            features.append(
                {
                    "id": feat.get("id", ""),
                    "description": feat.get("description", ""),
                    "feature_type": feat.get("feature_type", ""),
                    "start": feat.get("start"),
                    "end": feat.get("end"),
                    "strand": feat.get("strand", 0),
                    "seq_region_name": feat.get("seq_region_name", ""),
                }
            )

        return {
            "status": "success",
            "data": {
                "species": species,
                "region": f"{chrom}:{start}-{end}",
                "feature_count": len(features),
                "regulatory_features": features,
            },
            "metadata": {
                "source": "Ensembl Regulatory Build (rest.ensembl.org)",
                "species": species,
                "region": f"{chrom}:{start}-{end}",
            },
        }

    # =========================================================================
    # ENCODE Hi-C / 3D Genome Tools
    # =========================================================================

    def _encode_hic_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENCODE Hi-C and intact Hi-C experiments for 3D genome data."""
        assay_type = arguments.get("assay_type", "intact Hi-C")
        params = {
            "type": "Experiment",
            "assay_title": assay_type,
            "status": "released",
        }

        biosample = (
            arguments.get("biosample_term_name")
            or arguments.get("biosample")
            or arguments.get("cell_type")
            or arguments.get("tissue")
        )
        if biosample:
            params["biosample_ontology.term_name"] = biosample

        organism = arguments.get("organism", "Homo sapiens")
        if organism:
            params["replicates.library.biosample.organism.scientific_name"] = organism

        limit = arguments.get("limit", 25)
        params["limit"] = min(int(limit), 100)

        raw = self._encode_search(params)

        experiments = []
        for exp in raw.get("@graph", []):
            lab = exp.get("lab", {})
            lab_name = lab.get("title", "") if isinstance(lab, dict) else str(lab)

            experiments.append(
                {
                    "accession": exp.get("accession", ""),
                    "assay_title": exp.get("assay_title", ""),
                    "biosample_summary": exp.get("biosample_summary", ""),
                    "description": exp.get("description", ""),
                    "status": exp.get("status", ""),
                    "lab": lab_name,
                    "date_released": exp.get("date_released", ""),
                }
            )

        return {
            "status": "success",
            "data": {
                "total": raw.get("total", 0),
                "experiments": experiments,
            },
            "metadata": {
                "source": "ENCODE Project (encodeproject.org)",
                "assay": assay_type,
                "organism": organism,
            },
        }

    # =========================================================================
    # ENCODE microRNA-seq Tools
    # =========================================================================

    def _encode_microrna_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENCODE microRNA-seq experiments."""
        params = {
            "type": "Experiment",
            "assay_title": "microRNA-seq",
            "status": "released",
        }

        biosample = (
            arguments.get("biosample_term_name")
            or arguments.get("biosample")
            or arguments.get("cell_type")
            or arguments.get("tissue")
        )
        if biosample:
            params["biosample_ontology.term_name"] = biosample

        organism = arguments.get("organism", "Homo sapiens")
        if organism:
            params["replicates.library.biosample.organism.scientific_name"] = organism

        limit = arguments.get("limit", 25)
        params["limit"] = min(int(limit), 100)

        raw = self._encode_search(params)

        experiments = []
        for exp in raw.get("@graph", []):
            lab = exp.get("lab", {})
            lab_name = lab.get("title", "") if isinstance(lab, dict) else str(lab)

            experiments.append(
                {
                    "accession": exp.get("accession", ""),
                    "assay_title": exp.get("assay_title", ""),
                    "biosample_summary": exp.get("biosample_summary", ""),
                    "status": exp.get("status", ""),
                    "lab": lab_name,
                    "date_released": exp.get("date_released", ""),
                }
            )

        return {
            "status": "success",
            "data": {
                "total": raw.get("total", 0),
                "experiments": experiments,
            },
            "metadata": {
                "source": "ENCODE Project (encodeproject.org)",
                "assay": "microRNA-seq",
                "organism": organism,
            },
        }


@register_tool("UCSCEpigenomicsTool")
class UCSCEpigenomicsTool(BaseTool):
    """
    UCSC Genome Browser epigenomics-specific tools.

    Provides access to:
    - CpG island annotations
    - ENCODE4 candidate cis-Regulatory Elements (cCREs)
    - Transcription Factor binding site clusters

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "cpg_islands")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UCSC epigenomics API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"UCSC API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to UCSC API."}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"UCSC API HTTP error: {status}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "cpg_islands":
            return self._get_cpg_islands(arguments)
        elif self.endpoint == "encode_ccres":
            return self._get_encode_ccres(arguments)
        elif self.endpoint == "tf_binding":
            return self._get_tf_binding_clusters(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _ucsc_get_track(
        self, genome: str, track: str, chrom: str, start: int, end: int
    ) -> Dict[str, Any]:
        """Helper to fetch UCSC track data."""
        url = (
            f"{UCSC_API_URL}/getData/track"
            f"?genome={genome}&track={track}&chrom={chrom}&start={start}&end={end}"
        )
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _get_cpg_islands(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get CpG island annotations for a genomic region."""
        genome = arguments.get("genome", "hg38")
        chrom = arguments.get("chrom", "")
        start = arguments.get("start")
        end = arguments.get("end")

        if not chrom or start is None or end is None:
            return {
                "status": "error",
                "error": "chrom, start, and end parameters are required",
            }

        raw = self._ucsc_get_track(genome, "cpgIslandExt", chrom, start, end)
        items = raw.get("cpgIslandExt", [])
        if not isinstance(items, list):
            items = []

        cpg_islands = []
        for item in items:
            cpg_islands.append(
                {
                    "chrom": item.get("chrom", ""),
                    "chromStart": item.get("chromStart"),
                    "chromEnd": item.get("chromEnd"),
                    "name": item.get("name", ""),
                    "length": item.get("length", 0),
                    "cpgNum": item.get("cpgNum", 0),
                    "gcNum": item.get("gcNum", 0),
                    "perCpg": item.get("perCpg", 0),
                    "perGc": item.get("perGc", 0),
                    "obsExp": item.get("obsExp", 0),
                }
            )

        return {
            "status": "success",
            "data": {
                "genome": genome,
                "region": f"{chrom}:{start}-{end}",
                "cpg_island_count": len(cpg_islands),
                "cpg_islands": cpg_islands,
            },
            "metadata": {
                "source": "UCSC Genome Browser (api.genome.ucsc.edu)",
                "track": "cpgIslandExt",
                "genome": genome,
            },
        }

    def _get_encode_ccres(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ENCODE4 candidate cis-Regulatory Elements for a genomic region."""
        genome = arguments.get("genome", "hg38")
        chrom = arguments.get("chrom", "")
        start = arguments.get("start")
        end = arguments.get("end")

        if not chrom or start is None or end is None:
            return {
                "status": "error",
                "error": "chrom, start, and end parameters are required",
            }

        raw = self._ucsc_get_track(genome, "cCREregistry", chrom, start, end)
        items = raw.get("cCREregistry", [])
        if not isinstance(items, list):
            items = []

        ccres = []
        for item in items:
            ccres.append(
                {
                    "name": item.get("name", ""),
                    "chrom": item.get("chrom", ""),
                    "chromStart": item.get("chromStart"),
                    "chromEnd": item.get("chromEnd"),
                    "cCRE_class": item.get("cCRE_class", ""),
                    "DNase_maxZ": item.get("DNase_maxZ", 0),
                    "H3K4me3_maxZ": item.get("H3K4me3_maxZ", 0),
                    "H3K27ac_maxZ": item.get("H3K27ac_maxZ", 0),
                    "CTCF_maxZ": item.get("CTCF_maxZ", 0),
                }
            )

        return {
            "status": "success",
            "data": {
                "genome": genome,
                "region": f"{chrom}:{start}-{end}",
                "ccre_count": len(ccres),
                "ccres": ccres,
            },
            "metadata": {
                "source": "UCSC Genome Browser / ENCODE4 (api.genome.ucsc.edu)",
                "track": "cCREregistry",
                "genome": genome,
            },
        }

    def _get_tf_binding_clusters(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get TF binding site clusters from ENCODE3."""
        genome = arguments.get("genome", "hg38")
        chrom = arguments.get("chrom", "")
        start = arguments.get("start")
        end = arguments.get("end")

        if not chrom or start is None or end is None:
            return {
                "status": "error",
                "error": "chrom, start, and end parameters are required",
            }

        raw = self._ucsc_get_track(genome, "encRegTfbsClustered", chrom, start, end)
        items = raw.get("encRegTfbsClustered", [])
        if not isinstance(items, list):
            items = []

        tf_clusters = []
        for item in items:
            tf_clusters.append(
                {
                    "name": item.get("name", ""),
                    "chrom": item.get("chrom", ""),
                    "chromStart": item.get("chromStart"),
                    "chromEnd": item.get("chromEnd"),
                    "score": item.get("score", 0),
                    "sourceCount": item.get("sourceCount", 0),
                }
            )

        return {
            "status": "success",
            "data": {
                "genome": genome,
                "region": f"{chrom}:{start}-{end}",
                "tf_cluster_count": len(tf_clusters),
                "tf_clusters": tf_clusters,
            },
            "metadata": {
                "source": "UCSC Genome Browser / ENCODE3 (api.genome.ucsc.edu)",
                "track": "encRegTfbsClustered",
                "genome": genome,
                "description": "340 TFs across 129 cell types",
            },
        }
