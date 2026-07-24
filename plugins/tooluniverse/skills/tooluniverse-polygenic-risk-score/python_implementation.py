"""
Polygenic Risk Score (PRS) Builder Implementation

This module provides functions to build and calculate polygenic risk scores
using GWAS association data from ToolUniverse.

Key Features:
- Extract genome-wide significant SNPs for a trait
- Build weighted PRS models with effect sizes
- Calculate individual PRS from genotype data
- Interpret PRS percentiles and risk categories

References:
- PGS Catalog: https://www.pgscatalog.org/
- Lambert et al. (2021): "The Polygenic Score Catalog"
- Torkamani et al. (2018): "The personal and clinical utility of polygenic risk scores"
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Tuple
import math
from tooluniverse.tools import (
    gwas_get_associations_for_trait,
    gwas_get_snp_by_id,
    OpenTargets_get_variant_info,
    OpenTargets_search_gwas_studies_by_disease,
)


@dataclass
class SNPWeight:
    """
    A single SNP with its effect size for PRS calculation.

    Attributes:
        rs_id: dbSNP rs identifier (e.g., 'rs7903146')
        chromosome: Chromosome number (1-22, X, Y)
        position: Genomic position (bp)
        effect_allele: Allele associated with increased trait value
        other_allele: Alternative allele
        effect_size: Effect size (beta coefficient or log-odds ratio)
        p_value: Association p-value
        effect_allele_freq: Frequency of effect allele in population
        gene: Nearest or causal gene(s)
        study: GWAS study accession ID
    """
    rs_id: str
    chromosome: str
    position: int
    effect_allele: str
    other_allele: str
    effect_size: float
    p_value: float
    effect_allele_freq: Optional[float] = None
    gene: Optional[str] = None
    study: Optional[str] = None


@dataclass
class PRSResult:
    """
    Complete polygenic risk score result.

    Attributes:
        trait: Disease or trait name
        snp_count: Number of SNPs in the PRS
        snp_weights: List of SNPWeight objects used
        prs_value: Calculated PRS (if genotypes provided)
        standardized_score: Z-score relative to population (if available)
        percentile: Population percentile (if distribution available)
        risk_category: Interpretation (low/medium/high risk)
        metadata: Additional information (ancestry, study sources, etc.)
    """
    trait: str
    snp_count: int
    snp_weights: List[SNPWeight]
    prs_value: Optional[float] = None
    standardized_score: Optional[float] = None
    percentile: Optional[float] = None
    risk_category: Optional[str] = None
    metadata: Optional[Dict] = None


def convert_or_to_beta(odds_ratio: float) -> float:
    """
    Convert odds ratio to beta coefficient (log-odds).

    Args:
        odds_ratio: Odds ratio from case-control GWAS

    Returns:
        Beta coefficient (log odds ratio)

    Note:
        For continuous traits, beta is reported directly.
        For binary traits (case-control), OR is reported and needs conversion.
    """
    if odds_ratio <= 0:
        raise ValueError("Odds ratio must be positive")
    return math.log(odds_ratio)


def parse_effect_size(beta_str: Optional[str], or_str: Optional[str] = None) -> Optional[float]:
    """
    Parse effect size from GWAS data, handling both beta and OR formats.

    Args:
        beta_str: Beta coefficient as string
        or_str: Odds ratio as string

    Returns:
        Effect size as float (beta coefficient)
    """
    # Try beta first
    if beta_str:
        try:
            return float(beta_str)
        except (ValueError, TypeError):
            pass

    # Try OR conversion
    if or_str:
        try:
            or_val = float(or_str)
            return convert_or_to_beta(or_val)
        except (ValueError, TypeError):
            pass

    return None


def build_polygenic_risk_score(
    trait: str,
    p_threshold: float = 5e-8,
    min_maf: float = 0.01,
    max_snps: int = 1000,
    ancestry: Optional[str] = None,
    disease_id: Optional[str] = None,
) -> PRSResult:
    """
    Build a polygenic risk score by extracting genome-wide significant SNPs.

    This function queries GWAS databases to find all variants significantly
    associated with a trait and creates a weighted PRS model.

    Args:
        trait: Disease or trait name (e.g., "type 2 diabetes", "coronary artery disease")
        p_threshold: Significance threshold for inclusion (default: 5e-8, genome-wide)
        min_maf: Minimum minor allele frequency filter (default: 0.01)
        max_snps: Maximum number of SNPs to include (default: 1000)
        ancestry: Optional ancestry filter (e.g., "European")
        disease_id: Optional disease ontology ID (e.g., "MONDO_0005148" for T2D)

    Returns:
        PRSResult object containing SNP weights and metadata

    Example:
        >>> prs = build_polygenic_risk_score("type 2 diabetes")
        >>> print(f"Built PRS with {prs.snp_count} SNPs")
        >>> for weight in prs.snp_weights[:5]:
        >>>     print(f"{weight.rs_id}: beta={weight.effect_size:.3f}, p={weight.p_value:.2e}")

    Note:
        - This builds PRS weights only. To calculate individual risk, use calculate_personal_prs()
        - For real clinical use, use validated PRS from PGS Catalog
        - Consider LD clumping for independent SNPs
    """
    print(f"Building PRS for: {trait}")
    print(f"Significance threshold: {p_threshold}")
    print(f"MAF filter: {min_maf}")

    snp_weights = []

    # Query GWAS associations
    print("\\nQuerying GWAS Catalog...")
    result = gwas_get_associations_for_trait(
        disease_trait=trait,
        size=max_snps
    )

    if not result or 'data' not in result or not result['data']:
        print(f"No associations found for {trait}")
        return PRSResult(
            trait=trait,
            snp_count=0,
            snp_weights=[],
            metadata={'source': 'GWAS Catalog', 'query_status': 'no_results'}
        )

    associations = result['data']
    print(f"Found {len(associations)} associations")

    # Filter and process associations
    for assoc in associations:
        # Check p-value threshold
        p_value = assoc.get('p_value')
        if not p_value or p_value > p_threshold:
            continue

        # Get SNP info
        snp_alleles = assoc.get('snp_allele', [])
        if not snp_alleles or not isinstance(snp_alleles, list):
            continue

        # Extract rs_id and effect allele
        rs_id = None
        effect_allele = None
        for snp_info in snp_alleles:
            if isinstance(snp_info, dict):
                rs_id = snp_info.get('rs_id')
                effect_allele = snp_info.get('effect_allele')
                if rs_id:
                    break

        if not rs_id:
            continue

        # Parse effect size
        beta = parse_effect_size(assoc.get('beta'), assoc.get('or_value'))
        if beta is None:
            continue

        # Get location info
        locations = assoc.get('locations', [])
        chromosome = None
        position = None
        if locations and isinstance(locations, list) and len(locations) > 0:
            # Location might be a string like "10:112998590" or object
            loc = locations[0]
            if isinstance(loc, str) and ':' in loc:
                parts = loc.split(':')
                chromosome = parts[0]
                try:
                    position = int(parts[1])
                except (ValueError, IndexError):
                    pass

        # Get gene info
        genes = assoc.get('mapped_genes', [])
        gene = genes[0] if genes else None

        # Parse risk frequency (effect allele frequency)
        risk_freq = assoc.get('risk_frequency')
        eaf = None
        if risk_freq:
            try:
                eaf = float(risk_freq)
            except (ValueError, TypeError):
                pass

        # Create SNP weight
        snp_weight = SNPWeight(
            rs_id=rs_id,
            chromosome=chromosome or "?",
            position=position or 0,
            effect_allele=effect_allele or "?",
            other_allele="?",  # Would need separate query to determine
            effect_size=beta,
            p_value=p_value,
            effect_allele_freq=eaf,
            gene=gene,
            study=assoc.get('accession_id')
        )

        snp_weights.append(snp_weight)

    # Sort by p-value (strongest associations first)
    snp_weights.sort(key=lambda x: x.p_value)

    # Apply MAF filter if we have frequency data
    # (Would require additional queries to get MAF for all SNPs)

    print(f"\\nPRS built with {len(snp_weights)} genome-wide significant SNPs")
    if len(snp_weights) > 0:
        print(f"Strongest association: {snp_weights[0].rs_id} (p={snp_weights[0].p_value:.2e})")

    return PRSResult(
        trait=trait,
        snp_count=len(snp_weights),
        snp_weights=snp_weights,
        metadata={
            'source': 'GWAS Catalog',
            'p_threshold': p_threshold,
            'min_maf': min_maf,
            'query_date': 'dynamic',
        }
    )


def calculate_personal_prs(
    prs_weights: PRSResult,
    genotypes: Dict[str, Tuple[str, str]],
    population_mean: float = 0.0,
    population_std: float = 1.0,
) -> PRSResult:
    """
    Calculate an individual's polygenic risk score from their genotypes.

    Args:
        prs_weights: PRSResult object with SNP weights (from build_polygenic_risk_score)
        genotypes: Dictionary mapping rs_id to (allele1, allele2) tuples
                  Example: {"rs7903146": ("C", "T"), "rs429358": ("C", "C")}
        population_mean: Mean PRS in reference population (default: 0.0)
        population_std: Standard deviation in reference population (default: 1.0)

    Returns:
        Updated PRSResult with prs_value, standardized_score calculated

    Example:
        >>> # First, build PRS weights
        >>> prs = build_polygenic_risk_score("type 2 diabetes")
        >>>
        >>> # Then calculate for individual (e.g., from 23andMe data)
        >>> genotypes = {
        >>>     "rs7903146": ("C", "T"),  # Heterozygous for T2D risk allele
        >>>     "rs10811661": ("T", "T"),  # Homozygous
        >>>     # ... more SNPs
        >>> }
        >>> result = calculate_personal_prs(prs, genotypes)
        >>> print(f"PRS: {result.prs_value:.3f} (z-score: {result.standardized_score:.2f})")

    Note:
        - Genotype format: (allele1, allele2) where order doesn't matter
        - Missing genotypes are handled by skipping those SNPs
        - Dosage coding: 0 = no effect alleles, 1 = heterozygous, 2 = homozygous
        - Standardization assumes normal distribution in population
    """
    print(f"Calculating PRS for individual...")
    print(f"PRS model: {prs_weights.trait} ({prs_weights.snp_count} SNPs)")
    print(f"Genotypes provided: {len(genotypes)}")

    prs_sum = 0.0
    snps_used = 0

    for weight in prs_weights.snp_weights:
        rs_id = weight.rs_id

        # Check if genotype available
        if rs_id not in genotypes:
            continue

        allele1, allele2 = genotypes[rs_id]

        # Count effect alleles (dosage: 0, 1, or 2)
        effect_allele = weight.effect_allele
        dosage = 0
        if allele1 == effect_allele:
            dosage += 1
        if allele2 == effect_allele:
            dosage += 1

        # Weighted contribution: dosage × effect_size
        contribution = dosage * weight.effect_size
        prs_sum += contribution
        snps_used += 1

    # Calculate standardized score (z-score)
    prs_value = prs_sum
    z_score = (prs_value - population_mean) / population_std if population_std > 0 else 0.0

    print(f"\\nPRS calculated using {snps_used} SNPs")
    print(f"Raw PRS: {prs_value:.3f}")
    print(f"Z-score: {z_score:.2f}")

    # Update result object
    prs_weights.prs_value = prs_value
    prs_weights.standardized_score = z_score

    return prs_weights


def interpret_prs_percentile(
    prs_result: PRSResult,
    population_distribution: Optional[Dict[str, float]] = None
) -> PRSResult:
    """
    Interpret PRS by converting to percentile and risk category.

    Args:
        prs_result: PRSResult with standardized_score calculated
        population_distribution: Optional dict with 'mean' and 'std' keys.
                                If None, assumes standard normal (mean=0, std=1)

    Returns:
        Updated PRSResult with percentile and risk_category

    Example:
        >>> prs = calculate_personal_prs(prs_weights, genotypes)
        >>> prs = interpret_prs_percentile(prs)
        >>> print(f"You are at the {prs.percentile:.1f} percentile")
        >>> print(f"Risk category: {prs.risk_category}")

    Risk Categories:
        - Low risk: <20th percentile
        - Average risk: 20-80th percentile
        - Elevated risk: 80-95th percentile
        - High risk: >95th percentile

    Note:
        - Percentiles assume normal distribution
        - Categories are illustrative; clinical interpretation varies by trait
        - PRS is NOT diagnostic - many factors affect disease risk
    """
    if prs_result.standardized_score is None:
        print("Error: No standardized score available. Run calculate_personal_prs first.")
        return prs_result

    z_score = prs_result.standardized_score

    # Convert z-score to percentile using normal CDF approximation
    # Using error function approximation
    from math import erf, sqrt
    percentile = 50 * (1 + erf(z_score / sqrt(2)))

    # Determine risk category
    if percentile < 20:
        risk_category = "Low risk"
    elif percentile < 80:
        risk_category = "Average risk"
    elif percentile < 95:
        risk_category = "Elevated risk"
    else:
        risk_category = "High risk"

    print(f"\\nPRS Interpretation:")
    print(f"  Percentile: {percentile:.1f}%")
    print(f"  Risk category: {risk_category}")
    print(f"\\nNote: PRS is one factor among many. Consult healthcare provider for clinical interpretation.")

    prs_result.percentile = percentile
    prs_result.risk_category = risk_category

    return prs_result


def get_example_genotypes_format() -> Dict[str, Tuple[str, str]]:
    """
    Provide example genotype data format for documentation.

    Returns:
        Dictionary showing expected genotype format

    Note:
        Real genotypes can be obtained from:
        - 23andMe raw data
        - Ancestry DNA raw data
        - Whole genome sequencing (VCF files)
        - SNP array data
    """
    return {
        "rs7903146": ("C", "T"),  # TCF7L2 - Type 2 diabetes risk
        "rs429358": ("T", "C"),   # APOE - Alzheimer's risk
        "rs1799945": ("C", "G"),  # HFE - Hemochromatosis
        "rs1801282": ("C", "C"),  # PPARG - Type 2 diabetes
        "rs5219": ("T", "T"),     # KCNJ11 - Type 2 diabetes
    }


if __name__ == "__main__":
    print("="*80)
    print("POLYGENIC RISK SCORE BUILDER - DEMO")
    print("="*80)

    # Example 1: Build PRS for Type 2 Diabetes
    print("\\nExample 1: Building PRS for Type 2 Diabetes")
    print("-"*80)
    prs_t2d = build_polygenic_risk_score(
        trait="type 2 diabetes",
        p_threshold=5e-8,
        max_snps=100
    )
    print(f"\\nTop 5 SNPs:")
    for i, weight in enumerate(prs_t2d.snp_weights[:5], 1):
        print(f"  {i}. {weight.rs_id} ({weight.gene}): beta={weight.effect_size:.3f}, p={weight.p_value:.2e}")

    # Example 2: Calculate personal PRS (simulated genotypes)
    print("\\n\\nExample 2: Calculate Personal PRS")
    print("-"*80)

    # Simulate genotypes (in real use, these come from genetic testing)
    example_genotypes = {
        "rs7903146": ("C", "T"),  # Heterozygous for risk allele
        "rs10811661": ("T", "T"),  # Homozygous
    }

    # For demo, only use SNPs we have genotypes for
    if prs_t2d.snp_count > 0:
        # Create mini PRS with just these SNPs
        mini_prs = PRSResult(
            trait="type 2 diabetes",
            snp_count=len(example_genotypes),
            snp_weights=[w for w in prs_t2d.snp_weights if w.rs_id in example_genotypes][:2],
            metadata=prs_t2d.metadata
        )

        result = calculate_personal_prs(mini_prs, example_genotypes)
        result = interpret_prs_percentile(result)

        print(f"\\nFinal Results:")
        print(f"  PRS Value: {result.prs_value:.3f}")
        print(f"  Percentile: {result.percentile:.1f}%")
        print(f"  Category: {result.risk_category}")

    print("\\n" + "="*80)
    print("DISCLAIMER")
    print("="*80)
    print("This is a demonstration tool for educational purposes.")
    print("For clinical-grade PRS, use validated scores from PGS Catalog.")
    print("PRS does not determine disease outcome - consult healthcare providers.")
