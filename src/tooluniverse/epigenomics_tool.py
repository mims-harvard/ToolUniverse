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

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the epigenomics API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"API request timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to API. Check network connectivity."}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {"error": f"API HTTP error: {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

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
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

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

    def _encode_histone_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ENCODE histone ChIP-seq experiments."""
        params = {
            "type": "Experiment",
            "assay_title": "Histone ChIP-seq",
            "status": "released",
        }

        histone_mark = arguments.get("histone_mark")
        if histone_mark:
            params["target.label"] = histone_mark

        biosample = arguments.get("biosample_term_name")
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
            "data": {
                "total": raw.get("total", 0),
                "experiments": experiments,
            },
            "metadata": {
                "source": "ENCODE Project (encodeproject.org)",
                "assay": "Histone ChIP-seq",
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

        biosample = arguments.get("biosample_term_name")
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

        biosample = arguments.get("biosample_term_name")
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

        biosample = arguments.get("biosample_term_name")
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

        biosample = arguments.get("biosample_term_name")
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

        # Build search term with methylation context
        term_parts = [query, "methylation"]
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
                if isinstance(uid_data, dict) and "accession" in uid_data:
                    datasets.append(
                        {
                            "accession": uid_data.get("accession", ""),
                            "title": uid_data.get("title", ""),
                            "summary": uid_data.get("summary", "")[:500],
                            "platform": uid_data.get("gpl"),
                            "organism": uid_data.get("taxon", ""),
                            "n_samples": uid_data.get("n_samples", 0),
                            "date_published": uid_data.get("pdat"),
                        }
                    )

        return {
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
                if isinstance(uid_data, dict) and "accession" in uid_data:
                    datasets.append(
                        {
                            "accession": uid_data.get("accession", ""),
                            "title": uid_data.get("title", ""),
                            "summary": uid_data.get("summary", "")[:500],
                            "organism": uid_data.get("taxon", ""),
                            "n_samples": uid_data.get("n_samples", 0),
                            "date_published": uid_data.get("pdat"),
                        }
                    )

        return {
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
            return {"error": "geo_id parameter is required (e.g., '200291249')"}

        summary_result = self._geo_esummary([geo_id])
        result = summary_result.get("result", {})
        uid_data = result.get(str(geo_id), {})

        if not isinstance(uid_data, dict) or "accession" not in uid_data:
            return {"error": f"Dataset with ID '{geo_id}' not found in GEO"}

        ftplink = uid_data.get("ftplink", "")
        suppfile = uid_data.get("suppfile", "")
        supp_data = []
        if ftplink:
            supp_data.append(ftplink)
        if suppfile:
            supp_data.append(suppfile)

        return {
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
            return {"error": "chrom, start, and end parameters are required"}

        # Ensure region is not too large (max 5Mb)
        if end - start > 5000000:
            return {"error": "Region too large. Maximum region size is 5 Mb."}

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
            return {"error": f"UCSC API request timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to UCSC API."}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {"error": f"UCSC API HTTP error: {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "cpg_islands":
            return self._get_cpg_islands(arguments)
        elif self.endpoint == "encode_ccres":
            return self._get_encode_ccres(arguments)
        elif self.endpoint == "tf_binding":
            return self._get_tf_binding_clusters(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

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
            return {"error": "chrom, start, and end parameters are required"}

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
            return {"error": "chrom, start, and end parameters are required"}

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
            return {"error": "chrom, start, and end parameters are required"}

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
