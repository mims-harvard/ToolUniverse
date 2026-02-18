# genome_nexus_tool.py
"""
Genome Nexus tool for ToolUniverse.

Genome Nexus (Memorial Sloan Kettering Cancer Center) is a cancer variant
annotation aggregator that integrates data from VEP, SIFT, PolyPhen-2,
AlphaMissense, cancer hotspots, mutation assessor, and more.

API: https://www.genomenexus.org/
No authentication required. Uses GRCh37/hg19 coordinates.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

GENOME_NEXUS_BASE_URL = "https://www.genomenexus.org"


@register_tool("GenomeNexusTool")
class GenomeNexusTool(BaseTool):
    """
    Tool for annotating cancer variants using Genome Nexus (MSK).

    Supports:
    - Full variant annotation (VEP + SIFT + PolyPhen + AlphaMissense + hotspots)
    - Cancer hotspot lookup
    - Canonical transcript retrieval
    - Coordinate-based mutation annotation

    No authentication required. All coordinates in GRCh37/hg19.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "annotate_variant")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Genome Nexus API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Genome Nexus API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Genome Nexus API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 400:
                return {
                    "error": "Invalid variant format. Use GRCh37/hg19 HGVS notation (e.g., '7:g.140453136A>T')."
                }
            if status == 404:
                return {"error": "Variant or gene not found in Genome Nexus."}
            return {"error": f"Genome Nexus API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "annotate_variant":
            return self._annotate_variant(arguments)
        elif self.endpoint == "get_cancer_hotspots":
            return self._get_cancer_hotspots(arguments)
        elif self.endpoint == "get_canonical_transcript":
            return self._get_canonical_transcript(arguments)
        elif self.endpoint == "annotate_mutation":
            return self._annotate_mutation(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _annotate_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a variant by HGVS genomic notation."""
        hgvsg = arguments.get("hgvsg", "")
        if not hgvsg:
            return {"error": "hgvsg is required (e.g., '7:g.140453136A>T')."}

        url = f"{GENOME_NEXUS_BASE_URL}/annotation/{hgvsg}"
        params = {"fields": "hotspots,annotation_summary,mutation_assessor"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not data.get("successfully_annotated", True):
            return {
                "error": data.get(
                    "errorMessage", f"Failed to annotate variant '{hgvsg}'"
                )
            }

        return self._format_annotation(data)

    def _annotate_mutation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a mutation by genomic coordinates."""
        chromosome = arguments.get("chromosome", "")
        start = arguments.get("start")
        end = arguments.get("end")
        ref = arguments.get("reference_allele", "")
        alt = arguments.get("variant_allele", "")

        if not all([chromosome, start, end, ref, alt]):
            return {
                "error": "chromosome, start, end, reference_allele, and variant_allele are all required."
            }

        # Use the genomic format endpoint
        query = f"{chromosome},{start},{end},{ref},{alt}"
        url = f"{GENOME_NEXUS_BASE_URL}/annotation/genomic/{query}"
        params = {"fields": "hotspots,annotation_summary,mutation_assessor"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not data.get("successfully_annotated", True):
            return {
                "error": data.get(
                    "errorMessage",
                    f"Failed to annotate mutation at {chromosome}:{start}",
                )
            }

        return self._format_annotation(data)

    def _format_annotation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a variant annotation response."""
        # Extract transcript consequences with pathogenicity scores
        tc_list = []
        for tc in data.get("transcript_consequences", []):
            tc_entry = {
                "gene_symbol": tc.get("gene_symbol"),
                "transcript_id": tc.get("transcript_id"),
                "consequence_terms": tc.get("consequence_terms", []),
                "hgvsp": tc.get("hgvsp"),
                "hgvsc": tc.get("hgvsc"),
                "amino_acids": tc.get("amino_acids"),
                "codons": tc.get("codons"),
                "polyphen_prediction": tc.get("polyphen_prediction"),
                "polyphen_score": tc.get("polyphen_score"),
                "sift_prediction": tc.get("sift_prediction"),
                "sift_score": tc.get("sift_score"),
                "alphaMissense": tc.get("alphaMissense"),
                "canonical": tc.get("canonical"),
                "exon": tc.get("exon"),
            }
            tc_list.append(tc_entry)

        # Extract colocated variants (dbSNP IDs)
        colocated = []
        for cv in data.get("colocatedVariants", []):
            colocated.append({"dbSnpId": cv.get("dbSnpId")})

        # Extract hotspots
        hotspots_data = data.get("hotspots")
        hotspots_formatted = None
        if hotspots_data and hotspots_data.get("annotation"):
            hotspots_formatted = {
                "annotation": hotspots_data.get("annotation", []),
            }

        return {
            "data": {
                "variant": data.get("variant"),
                "hgvsg": data.get("hgvsg"),
                "assembly_name": data.get("assembly_name"),
                "most_severe_consequence": data.get("most_severe_consequence"),
                "annotation_summary": data.get("annotation_summary"),
                "transcript_consequences": tc_list,
                "hotspots": hotspots_formatted,
                "colocated_variants": colocated,
            },
            "metadata": {
                "source": "Genome Nexus (genomenexus.org) - Memorial Sloan Kettering",
            },
        }

    def _get_cancer_hotspots(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cancer hotspot data for a variant."""
        hgvsg = arguments.get("hgvsg", "")
        if not hgvsg:
            return {"error": "hgvsg is required (e.g., '7:g.140453136A>T')."}

        url = f"{GENOME_NEXUS_BASE_URL}/annotation/{hgvsg}"
        params = {"fields": "hotspots,annotation_summary"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not data.get("successfully_annotated", True):
            return {
                "error": data.get(
                    "errorMessage", f"Failed to annotate variant '{hgvsg}'"
                )
            }

        # Extract gene symbol from annotation summary
        gene_symbol = None
        ann_summary = data.get("annotation_summary", {})
        tc_summary = ann_summary.get("transcriptConsequences", [])
        if tc_summary:
            gene_symbol = tc_summary[0].get("hugoGeneSymbol")

        # Extract hotspots
        hotspot_data = data.get("hotspots", {})
        hotspot_annotations = hotspot_data.get("annotation", [])
        flat_hotspots = []
        for group in hotspot_annotations:
            if isinstance(group, list):
                for item in group:
                    flat_hotspots.append(
                        {
                            "hugoSymbol": item.get("hugoSymbol"),
                            "residue": item.get("residue"),
                            "tumorCount": item.get("tumorCount"),
                            "type": item.get("type"),
                        }
                    )
            elif isinstance(group, dict):
                flat_hotspots.append(
                    {
                        "hugoSymbol": group.get("hugoSymbol"),
                        "residue": group.get("residue"),
                        "tumorCount": group.get("tumorCount"),
                        "type": group.get("type"),
                    }
                )

        return {
            "data": {
                "variant": data.get("variant"),
                "gene_symbol": gene_symbol,
                "is_hotspot": len(flat_hotspots) > 0,
                "hotspots": flat_hotspots,
            },
            "metadata": {
                "source": "Genome Nexus Cancer Hotspots (genomenexus.org)",
            },
        }

    def _get_canonical_transcript(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get canonical transcript for a gene."""
        gene_symbol = arguments.get("gene_symbol", "")
        if not gene_symbol:
            return {"error": "gene_symbol is required (e.g., 'TP53')."}

        url = f"{GENOME_NEXUS_BASE_URL}/ensembl/canonical-transcript/hgnc/{gene_symbol}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Format Pfam domains
        pfam_domains = []
        for d_item in data.get("pfamDomains", []):
            pfam_domains.append(
                {
                    "pfamDomainId": d_item.get("pfamDomainId"),
                    "pfamDomainStart": d_item.get("pfamDomainStart"),
                    "pfamDomainEnd": d_item.get("pfamDomainEnd"),
                    "pfamDomainDescription": d_item.get("pfamDomainDescription"),
                }
            )

        return {
            "data": {
                "transcriptId": data.get("transcriptId"),
                "geneId": data.get("geneId"),
                "proteinId": data.get("proteinId"),
                "proteinLength": data.get("proteinLength"),
                "hugoSymbols": data.get("hugoSymbols", []),
                "refseqMrnaId": data.get("refseqMrnaId"),
                "ccdsId": data.get("ccdsId"),
                "pfamDomains": pfam_domains,
            },
            "metadata": {
                "source": "Genome Nexus (genomenexus.org) - Memorial Sloan Kettering",
            },
        }
