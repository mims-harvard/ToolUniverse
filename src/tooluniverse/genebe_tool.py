"""
GeneBe variant ACMG-classification tool for ToolUniverse.

GeneBe (genebe.net) automatically classifies a germline variant under the
ACMG/AMP guidelines and returns the verdict, the numeric score, and the exact
triggered criteria (e.g. ``PS3,PM1,PM2,PM5,PP2,PP3_Moderate,PP5``), alongside
gene/transcript context, dbSNP id, gnomAD allele frequency, ClinVar
classification, and an AlphaMissense score.

It is complementary to ``InterVar_classify_variant`` (a different group's
implementation of ACMG/AMP): GeneBe is independently maintained and layers in
AlphaMissense / APOGEE2 and gene-specific ACMG, so cross-checking the two
sources is useful when a classification is borderline.

API: https://api.genebe.net/cloud/api-public/v1/variant (public, no key; a
free account raises the anonymous rate limit). Input is chromosome / position
/ ref / alt on genome build hg38 (default) or hg19.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

GENEBE_API = "https://api.genebe.net/cloud/api-public/v1/variant"
GENEBE_BATCH_API = "https://api.genebe.net/cloud/api-public/v1/variants"

# Max variants per batch request accepted by the public GeneBe endpoint.
GENEBE_BATCH_MAX = 1000

# Accept common build aliases; GeneBe expects hg38 / hg19.
_BUILD_MAP = {
    "hg38": "hg38",
    "grch38": "hg38",
    "38": "hg38",
    "hg19": "hg19",
    "grch37": "hg19",
    "37": "hg19",
}

# The raw record has ~54 fields; surface the clinically useful subset.
# hgvs_c/hgvs_p/effects are NOT among the variant's own top-level fields
# despite living in this same "useful" tier -- they only exist nested one
# level down, per gene, under acmg_by_gene[*] (see _GENE_LEVEL_FIELDS
# below and where it's applied in run()). Confirmed live: the top-level
# lookup `v.get("hgvs_c")` always misses and these fields were silently
# dropped from every response.
_USEFUL_FIELDS = (
    "gene_symbol",
    "transcript",
    "acmg_classification",
    "acmg_score",
    "acmg_criteria",
    "clinvar_classification",
    "alphamissense_score",
    "alphamissense_prediction",
    "dbsnp",
    "gnomad_exomes_af",
    "frequency_reference_population",
)

# Present only under variant["acmg_by_gene"][0], not at the variant's own
# top level -- pulled in separately in run().
_GENE_LEVEL_FIELDS = ("hgvs_c", "hgvs_p", "effects")

# A ClinVar classification without its review status and submission counts
# cannot be weighed. BRAF V600E comes back "Conflicting classifications of
# pathogenicity" with review status "criteria provided, conflicting
# classifications" and a summary of "P:3 LP:1 US:5 O:1" -- five of the ten
# submissions call it uncertain -- and the row reported the conflict alone.
# The other predictors, the combined calls and the gnomAD counts were dropped
# with them. The batch handler in this same module returns the raw variant
# record whole, so none of this costs a request: the projection was a choice.
_CLINICAL_FIELDS = (
    "clinvar_disease",
    "clinvar_review_status",
    "clinvar_submissions_summary",
    "pathogenicity_classification_combined",
    "phenotype_combined",
    "effect",
    "gene_hgnc_id",
    "warning",
)
_PREDICTION_FIELDS = (
    "revel_score",
    "revel_prediction",
    "spliceai_max_score",
    "spliceai_max_prediction",
    "phylop100way_score",
    "phylop100way_prediction",
    "bayesdelnoaf_score",
    "bayesdelnoaf_prediction",
    "computational_prediction_selected",
    "computational_score_selected",
    "computational_source_selected",
    "splice_prediction_selected",
    "splice_score_selected",
    "splice_source_selected",
)
_FREQUENCY_FIELDS = (
    "gnomad_exomes_ac",
    "gnomad_exomes_filter",
    "gnomad_exomes_homalt",
    "gnomad_genomes_af",
    "gnomad_genomes_ac",
    "gnomad_genomes_filter",
    "gnomad_genomes_homalt",
    "allele_count_reference_population",
    "hom_count_reference_population",
)

# Per-transcript consequence rows. BRAF V600E has 43 of them; the MANE and
# canonical ones are what a report cites, so they are ordered first and the
# rest are cut with the count disclosed.
CONSEQUENCES_PER_VARIANT = 12
_CONSEQUENCE_FIELDS = (
    "transcript",
    "feature",
    "gene_symbol",
    "gene_hgnc_id",
    "biotype",
    "protein_coding",
    "consequences",
    "hgvs_c",
    "hgvs_p",
    "exon_rank",
    "exon_count",
    "intron_rank",
    "aa_start",
    "aa_ref",
    "aa_alt",
    "aa_length",
    "cds_length",
    "cdna_length",
    "strand",
    "canonical",
    "mane_select",
    "mane_plus",
    "transcript_support_level",
    "protein_id",
)


def _consequences(variant: dict) -> list:
    """The per-transcript consequences, MANE and canonical rows first.

    A variant's effect depends on the transcript, and the row reported one
    `transcript` with no way to see that 43 were annotated or which of them
    is MANE Select. For BRAF V600E that is NM_004333.6 / ENST00000646891.2.
    """
    rows = [
        {
            key: row.get(key)
            for key in _CONSEQUENCE_FIELDS
            if row.get(key) not in (None, "", [])
        }
        for row in (variant.get("consequences") or [])
        if isinstance(row, dict)
    ]
    rows.sort(
        key=lambda r: (
            0 if r.get("mane_select") else 1,
            0 if r.get("canonical") else 1,
        )
    )
    return rows[:CONSEQUENCES_PER_VARIANT]


@register_tool("GeneBeTool")
class GeneBeTool(BaseTool):
    """Classify a germline variant with GeneBe's ACMG/AMP auto-classifier."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Batch mode: a JSON array of variants is provided under "variants".
        if arguments.get("variants") is not None:
            return self._run_batch(arguments)

        chrom = arguments.get("chr") or arguments.get("chrom")
        pos = arguments.get("pos")
        ref = arguments.get("ref")
        alt = arguments.get("alt")
        missing = [
            name
            for name, val in (("chr", chrom), ("pos", pos), ("ref", ref), ("alt", alt))
            if val in (None, "")
        ]
        if missing:
            return {
                "status": "error",
                "error": f"Missing required parameter(s): {', '.join(missing)}. "
                "Provide chr, pos, ref, alt (and optionally genome=hg38/hg19).",
            }

        build_in = str(arguments.get("genome") or arguments.get("build") or "hg38")
        genome = _BUILD_MAP.get(build_in.lower())
        if genome is None:
            return {
                "status": "error",
                "error": f"Unsupported genome build '{build_in}'. Use hg38/GRCh38 or hg19/GRCh37.",
            }

        params = {
            "chr": str(chrom).replace("chr", ""),
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "genome": genome,
        }
        try:
            resp = requests.get(
                GENEBE_API,
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.Timeout:
            return {
                "status": "error",
                "error": f"GeneBe request timed out after {self.timeout}s.",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Failed to reach GeneBe: {str(e)}"}

        if resp.status_code == 429:
            return {
                "status": "error",
                "error": "GeneBe rate limit reached. Create a free account at https://genebe.net to raise it.",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"GeneBe returned HTTP {resp.status_code}",
                "detail": resp.text[:300],
            }
        try:
            variants = resp.json().get("variants", [])
        except ValueError:
            return {"status": "error", "error": "GeneBe returned a non-JSON response."}

        if not variants:
            return {
                "status": "error",
                "error": f"GeneBe returned no result for {params['chr']}-{pos}-{ref}-{alt} ({genome}).",
            }

        v = variants[0]
        selected = (
            _USEFUL_FIELDS + _CLINICAL_FIELDS + _PREDICTION_FIELDS + _FREQUENCY_FIELDS
        )
        data = {k: v[k] for k in selected if v.get(k) not in (None, "")}
        consequences = _consequences(v)
        data["consequences"] = consequences
        data["consequence_count"] = len(v.get("consequences") or [])
        data["consequences_truncated"] = data["consequence_count"] > len(consequences)
        # A variant in an overlapping-gene region gets one ACMG block per
        # gene. Both variants measured return exactly one, so taking the
        # first is right today and the count says when it stops being.
        by_gene_rows = [g for g in (v.get("acmg_by_gene") or []) if isinstance(g, dict)]
        by_gene = by_gene_rows[0] if by_gene_rows else {}
        data["acmg_gene_count"] = len(by_gene_rows)
        data["acmg_gene_symbol"] = by_gene.get("gene_symbol")
        for key in _GENE_LEVEL_FIELDS:
            val = by_gene.get(key)
            if val not in (None, "", []):
                data[key] = val
        data["variant"] = f"{params['chr']}-{pos}-{ref}-{alt}"
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "GeneBe (genebe.net)",
                "genome": genome,
                "consequences_per_variant": CONSEQUENCES_PER_VARIANT,
                "note": "consequences are ordered MANE Select first, then "
                "canonical; consequence_count is how many GeneBe annotated. "
                "clinvar_submissions_summary counts the submissions behind "
                "clinvar_classification (P/LP/US/LB/B/O).",
            },
        }

    def _run_batch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Classify up to 1000 variants in a single POST to GeneBe.

        Expects ``variants``: a list of objects each with chr/pos/ref/alt. Returns
        the full per-variant ACMG output (verdict, score, criteria, per-gene HGVS,
        AlphaMissense, gnomAD AF, ClinVar) for every variant.
        """
        raw = arguments.get("variants")
        if not isinstance(raw, list) or not raw:
            return {
                "status": "error",
                "error": "Parameter 'variants' must be a non-empty list of "
                "objects, each with chr, pos, ref, alt.",
            }
        if len(raw) > GENEBE_BATCH_MAX:
            return {
                "status": "error",
                "error": f"GeneBe accepts at most {GENEBE_BATCH_MAX} variants per "
                f"batch; received {len(raw)}.",
            }

        build_in = str(arguments.get("genome") or arguments.get("build") or "hg38")
        genome = _BUILD_MAP.get(build_in.lower())
        if genome is None:
            return {
                "status": "error",
                "error": f"Unsupported genome build '{build_in}'. Use hg38/GRCh38 or hg19/GRCh37.",
            }

        body = []
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                return {
                    "status": "error",
                    "error": f"variants[{i}] must be an object with chr, pos, ref, alt.",
                }
            chrom = item.get("chr") or item.get("chrom")
            pos = item.get("pos")
            ref = item.get("ref")
            alt = item.get("alt")
            missing = [
                name
                for name, val in (
                    ("chr", chrom),
                    ("pos", pos),
                    ("ref", ref),
                    ("alt", alt),
                )
                if val in (None, "")
            ]
            if missing:
                return {
                    "status": "error",
                    "error": f"variants[{i}] is missing required field(s): "
                    f"{', '.join(missing)}.",
                }
            body.append(
                {
                    "chr": str(chrom).replace("chr", ""),
                    "pos": pos,
                    "ref": ref,
                    "alt": alt,
                }
            )

        try:
            resp = requests.post(
                GENEBE_BATCH_API,
                params={"genome": genome},
                json=body,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        except requests.Timeout:
            return {
                "status": "error",
                "error": f"GeneBe batch request timed out after {self.timeout}s.",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Failed to reach GeneBe: {str(e)}"}

        if resp.status_code == 429:
            return {
                "status": "error",
                "error": "GeneBe rate limit reached. Create a free account at https://genebe.net to raise it.",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"GeneBe returned HTTP {resp.status_code}",
                "detail": (resp.text or "")[:300],
            }
        try:
            variants = resp.json().get("variants", [])
        except ValueError:
            return {"status": "error", "error": "GeneBe returned a non-JSON response."}

        if not variants:
            return {
                "status": "error",
                "error": f"GeneBe returned no results for the {len(body)} submitted variant(s).",
            }

        return {
            "status": "success",
            "data": {"variants": variants},
            "metadata": {
                "source": "GeneBe (genebe.net)",
                "genome": genome,
                "submitted_count": len(body),
                "result_count": len(variants),
            },
        }
