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


def _hotspot(item: Dict[str, Any]) -> Dict[str, Any]:
    """One cancer-hotspots record, with the counts that make up the total.

    `tumorCount` alone says how many tumours carry a mutation at the residue;
    the breakdown says what kind. BRAF V600 is 897 missense and 0
    truncating, and a truncating-dominated residue is a different finding
    from a missense-dominated one even at the same total. `transcriptId` is
    what the residue number is counted against, without which "R175" is not
    a position.
    """
    return {
        "hugoSymbol": item.get("hugoSymbol"),
        "residue": item.get("residue"),
        "tumorCount": item.get("tumorCount"),
        "type": item.get("type"),
        "transcriptId": item.get("transcriptId"),
        "transcriptIdVersion": item.get("transcriptIdVersion"),
        "missenseCount": item.get("missenseCount"),
        "truncatingCount": item.get("truncatingCount"),
        "inframeCount": item.get("inframeCount"),
        "spliceCount": item.get("spliceCount"),
        "version": item.get("version"),
    }


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
            return {
                "status": "error",
                "error": f"Genome Nexus API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Genome Nexus API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 400:
                return {
                    "status": "error",
                    "error": "Invalid variant format. Use GRCh37/hg19 HGVS notation (e.g., '7:g.140453136A>T').",
                }
            if status == 404:
                return {
                    "status": "error",
                    "error": "Variant or gene not found in Genome Nexus.",
                }
            return {"status": "error", "error": f"Genome Nexus API HTTP {status}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

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
        elif self.endpoint == "annotate_dbsnp":
            return self._annotate_dbsnp(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _annotate_dbsnp(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a variant directly by dbSNP rsID.

        Genome Nexus resolves the rsID to genomic coordinates and returns the
        same aggregated annotation (VEP + SIFT + PolyPhen-2 + AlphaMissense +
        cancer hotspots) as the HGVS endpoint.
        """
        rsid = (arguments.get("rsid") or "").strip()
        if not rsid:
            return {
                "status": "error",
                "error": "rsid is required (e.g., 'rs121913529').",
            }
        # Tolerate a bare numeric id by prefixing 'rs'.
        if rsid.lower().startswith("rs"):
            rsid = "rs" + rsid[2:]
        elif rsid.isdigit():
            rsid = f"rs{rsid}"

        url = f"{GENOME_NEXUS_BASE_URL}/annotation/dbsnp/{rsid}"
        params = {"fields": "hotspots,annotation_summary,mutation_assessor"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        # The dbsnp endpoint returns a single object for one rsID.
        if isinstance(data, list):
            if not data:
                return {
                    "status": "error",
                    "error": f"No annotation returned for dbSNP '{rsid}'.",
                }
            data = data[0]

        if not data.get("successfully_annotated", True):
            return {
                "status": "error",
                "error": data.get("errorMessage", f"Failed to annotate dbSNP '{rsid}'"),
            }

        return self._format_annotation(data)

    def _annotate_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a variant by HGVS genomic notation."""
        hgvsg = arguments.get("hgvsg", "")
        if not hgvsg:
            return {
                "status": "error",
                "error": "hgvsg is required (e.g., '7:g.140453136A>T').",
            }

        url = f"{GENOME_NEXUS_BASE_URL}/annotation/{hgvsg}"
        params = {"fields": "hotspots,annotation_summary,mutation_assessor"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not data.get("successfully_annotated", True):
            return {
                "status": "error",
                "error": data.get(
                    "errorMessage", f"Failed to annotate variant '{hgvsg}'"
                ),
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
                "status": "error",
                "error": "chromosome, start, end, reference_allele, and variant_allele are all required.",
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
                "status": "error",
                "error": data.get(
                    "errorMessage",
                    f"Failed to annotate mutation at {chromosome}:{start}",
                ),
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
                # Which kind of transcript the consequence is on. BRAF
                # 7:g.140453136A>T has four consequences and two of them are
                # on `nonsense_mediated_decay` transcripts, where a missense
                # call at p.28 is not the same claim as p.V600E on the
                # protein_coding one. Without it the four read as equals.
                "biotype": tc.get("biotype"),
                # The residue the change lands on, as a number rather than
                # only inside the hgvsp string a caller would have to parse.
                "protein_start": tc.get("protein_start"),
                "protein_end": tc.get("protein_end"),
                # The identifiers the annotation can be joined on: Ensembl
                # gene and protein, the HGNC id, and the RefSeq transcripts
                # this Ensembl transcript corresponds to.
                "gene_id": tc.get("gene_id"),
                "protein_id": tc.get("protein_id"),
                "hgnc_id": tc.get("hgnc_id"),
                "refseq_transcript_ids": tc.get("refseq_transcript_ids") or [],
                "variant_allele": tc.get("variant_allele"),
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
            "status": "success",
            "data": {
                "variant": data.get("variant"),
                "hgvsg": data.get("hgvsg"),
                "assembly_name": data.get("assembly_name"),
                "most_severe_consequence": data.get("most_severe_consequence"),
                "annotation_summary": data.get("annotation_summary"),
                "transcript_consequences": tc_list,
                "hotspots": hotspots_formatted,
                "colocated_variants": colocated,
                # Asked for in the `fields` parameter of every one of these
                # three calls, and then dropped from the answer. The class
                # docstring names Mutation Assessor among the sources it
                # aggregates; for BRAF V600E it reports functionalImpactScore
                # 7.11 / "high", which is one of the four predictors a caller
                # would weigh beside SIFT, PolyPhen and AlphaMissense.
                "mutation_assessor": data.get("mutation_assessor"),
            },
            "metadata": {
                "source": "Genome Nexus (genomenexus.org) - Memorial Sloan Kettering",
            },
        }

    def _get_cancer_hotspots(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cancer hotspot data for a variant."""
        hgvsg = arguments.get("hgvsg", "")
        if not hgvsg:
            return {
                "status": "error",
                "error": "hgvsg is required (e.g., '7:g.140453136A>T').",
            }

        url = f"{GENOME_NEXUS_BASE_URL}/annotation/{hgvsg}"
        params = {"fields": "hotspots,annotation_summary"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if not data.get("successfully_annotated", True):
            return {
                "status": "error",
                "error": data.get(
                    "errorMessage", f"Failed to annotate variant '{hgvsg}'"
                ),
            }

        # Extract gene symbol from annotation summary. The canonical
        # transcript's summary is read first and the list only as a fallback,
        # so the symbol is the one Genome Nexus itself calls canonical rather
        # than whichever consequence happens to be listed first.
        gene_symbol = None
        ann_summary = data.get("annotation_summary") or {}
        canonical = ann_summary.get("transcriptConsequenceSummary") or {}
        gene_symbol = canonical.get("hugoGeneSymbol")
        if not gene_symbol:
            for tc_summary in (
                ann_summary.get("transcriptConsequences") or [],
                ann_summary.get("transcriptConsequenceSummaries") or [],
            ):
                if tc_summary:
                    gene_symbol = tc_summary[0].get("hugoGeneSymbol")
                    break

        # Extract hotspots
        hotspot_data = data.get("hotspots", {})
        hotspot_annotations = hotspot_data.get("annotation", [])
        flat_hotspots = [
            _hotspot(item)
            for group in hotspot_annotations
            for item in (group if isinstance(group, list) else [group])
            if isinstance(item, dict)
        ]

        return {
            "status": "success",
            "data": {
                "variant": data.get("variant"),
                "gene_symbol": gene_symbol,
                "is_hotspot": len(flat_hotspots) > 0,
                "hotspots": flat_hotspots,
                # `is_hotspot: true` without the protein change does not say
                # WHICH hotspot. The canonical summary this handler already
                # fetched to read the gene symbol carries p.V600E, the
                # Missense_Mutation classification, the transcript, the exon
                # and the SIFT/PolyPhen/AlphaMissense calls, and all of it was
                # dropped.
                "variant_summary": {
                    "protein_change": canonical.get("hgvspShort"),
                    "protein_change_long": canonical.get("hgvsp"),
                    "coding_change": canonical.get("hgvsc"),
                    "variant_classification": canonical.get("variantClassification"),
                    "consequence_terms": canonical.get("consequenceTerms"),
                    "transcript_id": canonical.get("transcriptId"),
                    "exon": canonical.get("exon"),
                    "protein_position": canonical.get("proteinPosition"),
                    "codon_change": canonical.get("codonChange"),
                    "amino_acids": canonical.get("aminoAcids"),
                    "uniprot_id": canonical.get("uniprotId"),
                    "refseq": canonical.get("refSeq"),
                    "entrez_gene_id": canonical.get("entrezGeneId"),
                    "sift_prediction": canonical.get("siftPrediction"),
                    "sift_score": canonical.get("siftScore"),
                    "polyphen_prediction": canonical.get("polyphenPrediction"),
                    "polyphen_score": canonical.get("polyphenScore"),
                    "alpha_missense": canonical.get("alphaMissense"),
                },
                "most_severe_consequence": data.get("most_severe_consequence"),
                # Every consequence term across the transcripts, which differ:
                # the same base change is a missense on three BRAF transcripts
                # and a 3'-UTR variant on a fourth.
                "consequence_terms": sorted(
                    {
                        term
                        for tc in (data.get("transcript_consequences") or [])
                        if isinstance(tc, dict)
                        for term in (tc.get("consequence_terms") or [])
                        if isinstance(term, str)
                    }
                ),
                # The ids this position is already known by -- COSMIC, dbSNP
                # -- which is how a hotspot call is cross-checked.
                "colocated_variant_ids": [
                    cv.get("dbSnpId")
                    for cv in (data.get("colocatedVariants") or [])
                    if isinstance(cv, dict) and cv.get("dbSnpId")
                ],
            },
            "metadata": {
                "source": "Genome Nexus Cancer Hotspots (genomenexus.org)",
            },
        }

    def _get_canonical_transcript(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get canonical transcript for a gene."""
        gene_symbol = arguments.get("gene_symbol", "")
        if not gene_symbol:
            return {
                "status": "error",
                "error": "gene_symbol is required (e.g., 'TP53').",
            }

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

        # The exon structure is what a transcript IS. TP53's canonical
        # transcript has 11 exons, and the tool returned the transcript id,
        # the protein length and the Pfam domains while dropping every exon
        # boundary -- so nothing in the answer could place a variant in an
        # exon, or tell a coding exon from a UTR.
        exons = [
            {
                "exonId": e.get("exonId"),
                "exonStart": e.get("exonStart"),
                "exonEnd": e.get("exonEnd"),
                "rank": e.get("rank"),
                "strand": e.get("strand"),
                "version": e.get("version"),
            }
            for e in data.get("exons") or []
            if isinstance(e, dict)
        ]
        utrs = [
            {
                "type": u.get("type"),
                "start": u.get("start"),
                "end": u.get("end"),
                "strand": u.get("strand"),
            }
            for u in data.get("utrs") or []
            if isinstance(u, dict)
        ]

        return {
            "status": "success",
            "data": {
                "transcriptId": data.get("transcriptId"),
                "transcriptIdVersion": data.get("transcriptIdVersion"),
                "geneId": data.get("geneId"),
                "proteinId": data.get("proteinId"),
                "proteinLength": data.get("proteinLength"),
                "hugoSymbols": data.get("hugoSymbols", []),
                "refseqMrnaId": data.get("refseqMrnaId"),
                "ccdsId": data.get("ccdsId"),
                # The UniProt accession this transcript's protein is, which is
                # the join key to every protein-level resource.
                "uniprotId": data.get("uniprotId"),
                "exons": exons,
                "exon_count": len(exons),
                "utrs": utrs,
                "pfamDomains": pfam_domains,
            },
            "metadata": {
                "source": "Genome Nexus (genomenexus.org) - Memorial Sloan Kettering",
            },
        }
