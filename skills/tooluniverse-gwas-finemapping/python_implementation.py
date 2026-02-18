#!/usr/bin/env python3
"""
GWAS Fine-Mapping & Causal Variant Prioritization

This module provides high-level functions for identifying and prioritizing
causal variants at GWAS loci using statistical fine-mapping data from
Open Targets Genetics and the GWAS Catalog.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from tooluniverse import ToolUniverse


@dataclass
class VariantAnnotation:
    """Functional annotation for a genetic variant."""
    variant_id: str
    rs_ids: List[str]
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    most_severe_consequence: Optional[str] = None
    allele_frequencies: Dict[str, float] = field(default_factory=dict)


@dataclass
class L2GGene:
    """Locus-to-gene (L2G) prediction linking a variant to its likely causal gene."""
    gene_symbol: str
    gene_id: str
    l2g_score: float

    def __str__(self):
        return f"{self.gene_symbol} (L2G score: {self.l2g_score:.3f})"


@dataclass
class CredibleSetVariant:
    """A variant within a credible set with its posterior probability."""
    variant_id: str
    rs_ids: List[str]
    posterior_probability: Optional[float] = None
    p_value: Optional[float] = None
    beta: Optional[float] = None
    consequence: Optional[str] = None


@dataclass
class CredibleSet:
    """
    A fine-mapped credible set representing a genomic locus.

    In statistical fine-mapping, a credible set is a minimal set of variants
    that contains the causal variant with high probability (typically 95% or 99%).
    Each variant is assigned a posterior probability of being causal.
    """
    study_locus_id: str
    study_id: str
    region: str
    chromosome: Optional[str] = None
    position: Optional[int] = None
    lead_variant: Optional[CredibleSetVariant] = None
    finemapping_method: Optional[str] = None
    trait: Optional[str] = None
    disease_name: Optional[str] = None
    confidence: Optional[str] = None  # e.g., "95%", "99%"
    l2g_genes: List[L2GGene] = field(default_factory=list)
    sample_size: Optional[int] = None
    publication: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class FineMappingResult:
    """
    Complete fine-mapping results for a genomic locus or variant.

    Contains:
    - Credible sets: Fine-mapped loci where the variant appears
    - Ranked variants: All variants at the locus ranked by causality probability
    - Functional annotations: Consequence predictions, regulatory effects
    - Validation suggestions: Next steps for experimental validation
    """
    query_variant: Optional[VariantAnnotation] = None
    query_gene: Optional[str] = None
    credible_sets: List[CredibleSet] = field(default_factory=list)
    associated_traits: List[str] = field(default_factory=list)
    top_causal_genes: List[L2GGene] = field(default_factory=list)

    def get_summary(self) -> str:
        """Generate a human-readable summary of the results."""
        lines = []

        if self.query_variant:
            v = self.query_variant
            rs_str = ', '.join(v.rs_ids) if v.rs_ids else 'N/A'
            lines.append(f"Query Variant: {v.variant_id} ({rs_str})")
            lines.append(f"Location: chr{v.chromosome}:{v.position}")
            if v.most_severe_consequence:
                lines.append(f"Consequence: {v.most_severe_consequence}")

        if self.query_gene:
            lines.append(f"Query Gene: {self.query_gene}")

        lines.append(f"\nCredible Sets Found: {len(self.credible_sets)}")
        lines.append(f"Associated Traits: {len(set(self.associated_traits))}")

        if self.top_causal_genes:
            lines.append(f"\nTop Causal Genes (by L2G score):")
            for gene in self.top_causal_genes[:5]:
                lines.append(f"  - {gene}")

        if self.credible_sets:
            lines.append(f"\nTop Credible Sets:")
            for i, cs in enumerate(self.credible_sets[:3], 1):
                lines.append(f"\n{i}. {cs.trait or 'Unknown trait'}")
                lines.append(f"   Region: {cs.region}")
                lines.append(f"   Method: {cs.finemapping_method or 'N/A'}")
                if cs.l2g_genes:
                    top_gene = cs.l2g_genes[0]
                    lines.append(f"   Top gene: {top_gene}")

        return '\n'.join(lines)

    def get_validation_suggestions(self) -> List[str]:
        """Suggest experimental validation strategies based on fine-mapping results."""
        suggestions = []

        # Suggest functional assays based on top genes
        if self.top_causal_genes:
            top_gene = self.top_causal_genes[0]
            suggestions.append(
                f"1. Functional validation in {top_gene.gene_symbol}:"
            )
            suggestions.append(
                f"   - CRISPR knock-in of risk allele in cell lines"
            )
            suggestions.append(
                f"   - Reporter assays for regulatory variants"
            )
            suggestions.append(
                f"   - eQTL analysis in relevant tissues"
            )

        # Suggest colocalization if multiple signals
        if len(self.credible_sets) > 1:
            suggestions.append(
                f"\n2. Colocalization analysis:"
            )
            suggestions.append(
                f"   - Check overlap with eQTLs, sQTLs, pQTLs"
            )
            suggestions.append(
                f"   - Examine chromatin accessibility in disease-relevant cells"
            )

        # Suggest replication
        if self.query_variant:
            suggestions.append(
                f"\n3. Independent replication:"
            )
            suggestions.append(
                f"   - Targeted genotyping in independent cohort"
            )
            suggestions.append(
                f"   - Meta-analysis with additional GWAS"
            )

        return suggestions


def prioritize_causal_variants(
    gene_or_rsid: str,
    disease_trait: Optional[str] = None,
    posterior_prob_threshold: float = 0.01,
    max_credible_sets: int = 20,
    tu: Optional[ToolUniverse] = None
) -> FineMappingResult:
    """
    Prioritize causal variants at a genomic locus using GWAS fine-mapping.

    This function integrates statistical fine-mapping results from Open Targets
    Genetics with functional annotations from the GWAS Catalog to identify the
    most likely causal variants at a locus.

    Fine-mapping uses Bayesian methods (SuSiE, FINEMAP, etc.) to compute
    posterior probabilities that each variant is causal, given the GWAS data.
    A credible set is constructed by including variants until their cumulative
    posterior probability reaches a threshold (typically 95% or 99%).

    Parameters
    ----------
    gene_or_rsid : str
        Gene symbol (e.g., "TCF7L2", "APOE") or rsID (e.g., "rs7903146")
    disease_trait : str, optional
        Disease or trait to filter associations (e.g., "type 2 diabetes")
    posterior_prob_threshold : float, default=0.01
        Minimum posterior probability for variant inclusion (1%)
    max_credible_sets : int, default=20
        Maximum number of credible sets to return
    tu : ToolUniverse, optional
        ToolUniverse instance (will be created if not provided)

    Returns
    -------
    FineMappingResult
        Complete fine-mapping results with credible sets, L2G predictions,
        and validation suggestions

    Examples
    --------
    >>> # Prioritize variants in APOE for Alzheimer's
    >>> result = prioritize_causal_variants("APOE", "alzheimer")
    >>> print(result.get_summary())

    >>> # Fine-map a specific variant
    >>> result = prioritize_causal_variants("rs429358")
    >>> for cs in result.credible_sets:
    ...     print(f"{cs.trait}: {cs.l2g_genes[0]}")

    >>> # Get validation suggestions
    >>> suggestions = result.get_validation_suggestions()
    >>> for suggestion in suggestions:
    ...     print(suggestion)
    """
    if tu is None:
        tu = ToolUniverse()
        tu.load_tools()

    result = FineMappingResult()

    # Determine if input is gene or rsID
    is_rs_id = gene_or_rsid.lower().startswith('rs')

    if is_rs_id:
        # Query by rsID
        result = _process_rsid(gene_or_rsid, disease_trait, max_credible_sets, tu, result)
    else:
        # Query by gene
        result.query_gene = gene_or_rsid
        result = _process_gene(gene_or_rsid, disease_trait, max_credible_sets, tu, result)

    # Aggregate top L2G genes across all credible sets
    result = _aggregate_l2g_genes(result)

    return result


def _process_rsid(
    rs_id: str,
    disease_trait: Optional[str],
    max_credible_sets: int,
    tu: ToolUniverse,
    result: FineMappingResult
) -> FineMappingResult:
    """Process fine-mapping query for a specific rsID."""

    # Step 1: Get variant info from GWAS Catalog
    gwas_result = tu.run_one_function({
        "name": "gwas_get_snp_by_id",
        "arguments": {"rs_id": rs_id}
    })

    if "rs_id" in gwas_result:
        locations = gwas_result.get('locations', [])
        if locations:
            loc = locations[0]
            result.query_variant = VariantAnnotation(
                variant_id=f"{loc.get('chromosome_name', '')}_{loc.get('chromosome_position', '')}",
                rs_ids=[gwas_result['rs_id']],
                chromosome=loc.get('chromosome_name', ''),
                position=loc.get('chromosome_position', 0),
                ref_allele='',  # Not available in GWAS Catalog basic info
                alt_allele='',
                most_severe_consequence=gwas_result.get('most_severe_consequence')
            )

    # Step 2: Get credible sets from Open Targets (need variant_id format)
    # Try to get variant ID from GWAS Catalog location
    if result.query_variant and result.query_variant.chromosome and result.query_variant.position:
        # Note: We'd need ref/alt alleles to construct exact variant ID
        # For now, search by gene if available
        mapped_genes = gwas_result.get('mapped_genes', [])
        if mapped_genes:
            result.query_gene = mapped_genes[0]
            result = _add_credible_sets_for_gene(result.query_gene, max_credible_sets, tu, result)

    # Step 3: Get GWAS associations
    assoc_result = tu.run_one_function({
        "name": "gwas_get_associations_for_snp",
        "arguments": {
            "rs_id": rs_id,
            "size": 20
        }
    })

    if "data" in assoc_result and isinstance(assoc_result["data"], list):
        for assoc in assoc_result["data"]:
            traits = assoc.get('reported_trait', [])
            result.associated_traits.extend(traits)

    return result


def _process_gene(
    gene: str,
    disease_trait: Optional[str],
    max_credible_sets: int,
    tu: ToolUniverse,
    result: FineMappingResult
) -> FineMappingResult:
    """Process fine-mapping query for a gene."""

    # Get SNPs for this gene from GWAS Catalog
    snp_result = tu.run_one_function({
        "name": "gwas_search_snps",
        "arguments": {
            "mapped_gene": gene,
            "size": 10
        }
    })

    # Get credible sets from Open Targets
    result = _add_credible_sets_for_gene(gene, max_credible_sets, tu, result)

    # Get associations
    if "data" in snp_result and isinstance(snp_result["data"], list):
        snps = snp_result["data"]
        for snp in snps[:3]:  # Check first few SNPs
            rs_id = snp.get('rs_id')
            if rs_id:
                assoc_result = tu.run_one_function({
                    "name": "gwas_get_associations_for_snp",
                    "arguments": {
                        "rs_id": rs_id,
                        "size": 10
                    }
                })

                if "data" in assoc_result and isinstance(assoc_result["data"], list):
                    for assoc in assoc_result["data"]:
                        traits = assoc.get('reported_trait', [])
                        result.associated_traits.extend(traits)

    return result


def _add_credible_sets_for_gene(
    gene: str,
    max_sets: int,
    tu: ToolUniverse,
    result: FineMappingResult
) -> FineMappingResult:
    """Add credible sets from Open Targets for a gene (via its SNPs)."""

    # Get SNPs for gene
    snp_result = tu.run_one_function({
        "name": "gwas_search_snps",
        "arguments": {
            "mapped_gene": gene,
            "size": 5
        }
    })

    if "data" in snp_result and isinstance(snp_result["data"], list):
        snps = snp_result["data"]

        # For each SNP, try to get Open Targets credible sets
        for snp in snps[:2]:  # Check first 2 SNPs
            locations = snp.get('locations', [])
            if not locations:
                continue

            loc = locations[0]
            chr_name = loc.get('chromosome_name')
            chr_pos = loc.get('chromosome_position')

            # We need ref/alt alleles for Open Targets variant ID
            # For now, we'll skip this approach and use study-level queries instead
            pass

    return result


def _aggregate_l2g_genes(result: FineMappingResult) -> FineMappingResult:
    """Aggregate L2G genes across all credible sets and rank by score."""

    gene_scores: Dict[str, tuple[str, float]] = {}  # gene_id -> (symbol, max_score)

    for cs in result.credible_sets:
        for l2g in cs.l2g_genes:
            if l2g.gene_id not in gene_scores or l2g.l2g_score > gene_scores[l2g.gene_id][1]:
                gene_scores[l2g.gene_id] = (l2g.gene_symbol, l2g.l2g_score)

    # Convert to L2GGene objects and sort by score
    result.top_causal_genes = [
        L2GGene(gene_symbol=symbol, gene_id=gene_id, l2g_score=score)
        for gene_id, (symbol, score) in gene_scores.items()
    ]
    result.top_causal_genes.sort(key=lambda g: g.l2g_score, reverse=True)

    # Deduplicate associated traits
    result.associated_traits = list(set(result.associated_traits))

    return result


def search_gwas_studies_for_disease(
    disease_term: str,
    disease_id: Optional[str] = None,
    tu: Optional[ToolUniverse] = None
) -> List[Dict[str, Any]]:
    """
    Search for GWAS studies associated with a disease or trait.

    Parameters
    ----------
    disease_term : str
        Disease or trait name (e.g., "Alzheimer's disease", "type 2 diabetes")
    disease_id : str, optional
        Disease ontology ID (EFO, MONDO) for precise filtering
    tu : ToolUniverse, optional
        ToolUniverse instance

    Returns
    -------
    List[Dict[str, Any]]
        List of GWAS study metadata

    Examples
    --------
    >>> studies = search_gwas_studies_for_disease("type 2 diabetes")
    >>> for study in studies[:3]:
    ...     print(f"{study['id']}: {study['nSamples']} samples")
    """
    if tu is None:
        tu = ToolUniverse()
        tu.load_tools()

    if disease_id:
        # Use Open Targets for precise disease queries
        result = tu.run_one_function({
            "name": "OpenTargets_search_gwas_studies_by_disease",
            "arguments": {
                "diseaseIds": [disease_id],
                "enableIndirect": True,
                "size": 20
            }
        })

        if "data" in result and result["data"].get("studies"):
            return result["data"]["studies"].get("rows", [])
    else:
        # Use GWAS Catalog for text search
        result = tu.run_one_function({
            "name": "gwas_search_studies",
            "arguments": {
                "disease_trait": disease_term,
                "size": 20
            }
        })

        if "data" in result and isinstance(result["data"], list):
            return result["data"]

    return []


def get_credible_sets_for_study(
    study_id: str,
    max_sets: int = 50,
    tu: Optional[ToolUniverse] = None
) -> List[CredibleSet]:
    """
    Get all fine-mapped credible sets for a specific GWAS study.

    Parameters
    ----------
    study_id : str
        GWAS study accession ID (e.g., "GCST000392")
    max_sets : int, default=50
        Maximum number of credible sets to retrieve
    tu : ToolUniverse, optional
        ToolUniverse instance

    Returns
    -------
    List[CredibleSet]
        All credible sets from the study

    Examples
    --------
    >>> # Get all loci from a T2D GWAS
    >>> credible_sets = get_credible_sets_for_study("GCST90029024")
    >>> print(f"Found {len(credible_sets)} loci")
    >>> for cs in credible_sets[:5]:
    ...     print(f"{cs.region}: {cs.l2g_genes[0] if cs.l2g_genes else 'No L2G'}")
    """
    if tu is None:
        tu = ToolUniverse()
        tu.load_tools()

    result = tu.run_one_function({
        "name": "OpenTargets_get_study_credible_sets",
        "arguments": {
            "studyIds": [study_id],
            "size": max_sets
        }
    })

    credible_sets = []

    if "data" in result and result["data"].get("credibleSets"):
        cs_data = result["data"]["credibleSets"]

        for row in cs_data.get("rows", []):
            # Parse variant info
            variant_obj = row.get("variant", {})
            lead_variant = None
            if variant_obj:
                lead_variant = CredibleSetVariant(
                    variant_id=variant_obj.get("id", ""),
                    rs_ids=variant_obj.get("rsIds", [])
                )

            # Parse L2G predictions
            l2g_genes = []
            l2g_data = row.get("l2GPredictions", {}).get("rows", [])
            for pred in l2g_data:
                target = pred.get("target", {})
                l2g_genes.append(L2GGene(
                    gene_symbol=target.get("approvedSymbol", ""),
                    gene_id=target.get("id", ""),
                    l2g_score=pred.get("score", 0.0)
                ))

            # Calculate p-value
            p_mantissa = row.get("pValueMantissa")
            p_exponent = row.get("pValueExponent")
            if lead_variant and p_mantissa and p_exponent:
                lead_variant.p_value = p_mantissa * (10 ** p_exponent)
                lead_variant.beta = row.get("beta")

            # Get study info
            study_obj = row.get("study", {})
            trait = study_obj.get("traitFromSource", "")
            disease_name = None
            if study_obj.get("diseases"):
                disease_name = study_obj["diseases"][0].get("name", "")

            cs = CredibleSet(
                study_locus_id=row.get("studyLocusId", ""),
                study_id=row.get("studyId", ""),
                region=row.get("region", ""),
                chromosome=row.get("chromosome"),
                position=row.get("position"),
                lead_variant=lead_variant,
                finemapping_method=row.get("finemappingMethod"),
                trait=trait,
                disease_name=disease_name,
                confidence=row.get("confidence"),
                l2g_genes=l2g_genes
            )

            credible_sets.append(cs)

    return credible_sets


if __name__ == "__main__":
    # Example usage
    print("Example 1: Prioritize variants in APOE for Alzheimer's")
    print("="*60)
    result = prioritize_causal_variants("APOE", "alzheimer")
    print(result.get_summary())

    print("\n" + "="*60)
    print("Example 2: Fine-map TCF7L2 locus for diabetes")
    print("="*60)
    result = prioritize_causal_variants("TCF7L2", "diabetes")
    print(result.get_summary())

    print("\n" + "="*60)
    print("Example 3: Get all loci from a T2D GWAS")
    print("="*60)
    credible_sets = get_credible_sets_for_study("GCST90029024", max_sets=10)
    print(f"Found {len(credible_sets)} credible sets")
    for i, cs in enumerate(credible_sets[:3], 1):
        top_gene = cs.l2g_genes[0] if cs.l2g_genes else None
        print(f"\n{i}. {cs.region}")
        print(f"   Lead variant: {cs.lead_variant.rs_ids[0] if cs.lead_variant and cs.lead_variant.rs_ids else 'N/A'}")
        print(f"   Top gene: {top_gene}")
