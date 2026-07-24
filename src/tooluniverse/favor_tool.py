"""
FAVOR tool for ToolUniverse — comprehensive functional annotation of a variant.

FAVOR (Functional Annotation of Variants Online Resource, Harvard/HSPH) provides
integrated whole-genome single-variant annotation: allele frequencies (BRAVO/TOPMed,
gnomAD, 1000 Genomes), gene/consequence, deleteriousness scores (CADD, SIFT, PolyPhen,
AlphaMissense, MetaSVM, ...), conservation (GERP, phyloP, phastCons), ClinVar clinical
significance, and regulatory/epigenomic context — in a single call.

API: https://api.genohub.org/v1/variants/{chr}-{pos}-{ref}-{alt}  (GRCh38/hg38,
public, no authentication). Returns a flat record of ~180 annotations; this tool
groups the high-value ones and passes the full record through under all_annotations.
"""

from typing import Any, Dict, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

FAVOR_BASE = "https://api.genohub.org/v1/variants"


def _normalize_variant(raw: str) -> Optional[str]:
    """Normalize a variant string to FAVOR's 'chr-pos-ref-alt' form (hg38).

    Accepts 'chr19:44908822:C:T', '19-44908822-C-T', 'chr19-44908822-C-T', etc.
    Returns None if it cannot be parsed into 4 fields.
    """
    if not raw:
        return None
    s = raw.strip()
    for sep in (":", "-", "_", "/", " "):
        s = s.replace(sep, "|")
    parts = [p for p in s.split("|") if p != ""]
    if len(parts) != 4:
        return None
    chrom, pos, ref, alt = parts
    if chrom.lower().startswith("chr"):
        chrom = chrom[3:]
    if not pos.isdigit():
        return None
    ref, alt = ref.upper(), alt.upper()
    if not ref or not alt:
        return None
    return f"{chrom}-{pos}-{ref}-{alt}"


@register_tool("FAVORVariantAnnotationTool")
class FAVORVariantAnnotationTool(BaseTool):
    """Comprehensive functional annotation for a single GRCh38 variant via FAVOR."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        variant = _normalize_variant(arguments.get("variant", ""))
        if variant is None:
            return {
                "status": "error",
                "error": (
                    "'variant' must be a GRCh38 SNV/indel as chr-pos-ref-alt "
                    "(e.g. '19-44908822-C-T' or 'chr19:44908822:C:T')."
                ),
            }

        url = f"{FAVOR_BASE}/{variant}"
        try:
            resp = requests.get(
                url, headers={"Accept": "application/json"}, timeout=self.timeout
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": {"variant": variant, "found": False},
                    "metadata": {
                        "found": False,
                        "note": f"Variant {variant} not found in FAVOR (GRCh38). "
                        "Check the genome build and allele orientation.",
                        "source": "FAVOR",
                    },
                }
            resp.raise_for_status()
            rec = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"FAVOR request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"FAVOR request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "FAVOR returned a non-JSON response"}

        if not isinstance(rec, dict) or not rec.get("variant_vcf"):
            return {
                "status": "success",
                "data": {"variant": variant, "found": False},
                "metadata": {
                    "found": False,
                    "note": f"No annotation record returned for {variant}.",
                    "source": "FAVOR",
                },
            }

        return {
            "status": "success",
            "data": self._curate(rec),
            "metadata": {
                "found": True,
                "genome_build": "GRCh38",
                "source": "FAVOR (Functional Annotation of Variants Online Resource)",
            },
        }

    @staticmethod
    def _curate(rec: Dict[str, Any]) -> Dict[str, Any]:
        g = rec.get  # shorthand
        ancestry_af = {
            k.replace("af_", ""): g(k)
            for k in (
                "af_total",
                "af_afr",
                "af_amr",
                "af_eas",
                "af_nfe",
                "af_sas",
                "af_asj",
                "af_fin",
                "af_ami",
                "af_oth",
            )
            if g(k) is not None
        }
        thousand_genomes = {
            k.replace("tg_", ""): g(k)
            for k in ("tg_all", "tg_afr", "tg_amr", "tg_eas", "tg_eur", "tg_sas")
            if g(k) is not None
        }
        return {
            "found": True,
            "variant": {
                "variant_vcf": g("variant_vcf"),
                "rsid": g("rsid"),
                "chromosome": g("chromosome"),
                "position": g("position"),
                "hgvs_genomic": g("hgvsg"),
            },
            "gene_consequence": {
                "gene": g("genecode_comprehensive_info") or g("geneinfo"),
                "category": g("genecode_comprehensive_category"),
                "exonic_category": g("genecode_comprehensive_exonic_category"),
                "so_term": g("so_term"),
                "protein_variant": g("protein_variant") or g("aa"),
                "hgvs_c": g("hgvsc") or g("cds"),
                "hgvs_p": g("hgvsp"),
                "is_canonical": g("is_canonical"),
            },
            "allele_frequency": {
                "bravo_topmed_af": g("bravo_af"),
                "bravo_topmed_ac": g("bravo_ac"),
                "bravo_topmed_an": g("bravo_an"),
                "gnomad_af_by_ancestry": ancestry_af,
                "thousand_genomes_af": thousand_genomes,
            },
            "deleteriousness": {
                "cadd_phred": g("cadd_phred"),
                "sift": g("sift_cat"),
                "polyphen2": g("polyphen_cat"),
                "alphamissense_class": g("am_class"),
                "alphamissense_pathogenicity": g("am_pathogenicity"),
                "metasvm_pred": g("metasvm_pred"),
                "mutation_assessor_score": g("mutation_assessor_score"),
                "mutation_taster_score": g("mutation_taster_score"),
                "fathmm_xf": g("fathmm_xf"),
                "grantham": g("grantham"),
                "linsight": g("linsight"),
                "funseq": g("funseq_description"),
            },
            "conservation": {
                "gerp_s": g("gerp_s"),
                "phylop_mammalian": g("mamphylop"),
                "phylop_primate": g("priphylop"),
                "phylop_vertebrate": g("verphylop"),
                "phastcons_mammalian": g("mamphcons"),
                "apc_conservation": g("apc_conservation_v2"),
            },
            "clinical": {
                "clinvar_significance": g("clnsig"),
                "clinvar_disease": g("clndn"),
                "clinvar_review_status": g("clnrevstat"),
                "clinvar_disease_db": g("clndisdb"),
            },
            "regulatory": {
                "cage_promoter": g("cage_promoter"),
                "cage_enhancer": g("cage_enhancer"),
                "genehancer": g("genehancer"),
                "super_enhancer": g("super_enhancer"),
                "encode_dnase_sum": g("encode_dnase_sum"),
                "apc_epigenetics_active": g("apc_epigenetics_active"),
                "remap_overlap_tf": g("remap_overlap_tf"),
            },
            "all_annotations": rec,
        }
