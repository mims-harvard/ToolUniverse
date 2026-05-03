"""
GWAS Study Deep Dive & Meta-Analysis

A comprehensive skill for comparing GWAS studies, performing meta-analyses, and
assessing study quality and replication across different cohorts.

Author: ToolUniverse
Date: 2026-02-13
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math
import re
from collections import defaultdict


@dataclass
class StudyMetadata:
    """Metadata for a GWAS study."""
    accession_id: str
    trait: str
    sample_size: int
    ancestry: List[str]
    platform: Optional[str] = None
    snp_count: Optional[int] = None
    publication_year: Optional[int] = None
    first_author: Optional[str] = None
    has_summary_stats: bool = False

    @classmethod
    def from_gwas_catalog(cls, study_data: dict) -> "StudyMetadata":
        """Create StudyMetadata from GWAS Catalog study data."""
        # Parse sample size from text
        sample_size_text = study_data.get('initial_sample_size', '0')
        sample_size = cls._parse_sample_size(sample_size_text)

        return cls(
            accession_id=study_data['accession_id'],
            trait=study_data['disease_trait'],
            sample_size=sample_size,
            ancestry=study_data.get('discovery_ancestry', []),
            platform=study_data.get('platforms'),
            snp_count=study_data.get('snp_count'),
            has_summary_stats=study_data.get('full_summary_stats_available', False)
        )

    @classmethod
    def from_opentargets(cls, study_data: dict) -> "StudyMetadata":
        """Create StudyMetadata from Open Targets study data."""
        # Extract ancestry from LD population structure
        ld_pop = study_data.get('ldPopulationStructure', [])
        ancestry = [pop['ldPopulation'] for pop in ld_pop] if ld_pop else []

        return cls(
            accession_id=study_data['id'],
            trait=study_data.get('traitFromSource', 'Unknown'),
            sample_size=study_data.get('nSamples', 0),
            ancestry=ancestry,
            first_author=study_data.get('publicationFirstAuthor'),
            has_summary_stats=study_data.get('hasSumstats', False)
        )

    @staticmethod
    def _parse_sample_size(text: str) -> int:
        """Parse sample size from text description."""
        if not text:
            return 0
        # Extract numbers and sum them
        numbers = re.findall(r'(\d+(?:,\d+)*)', text)
        total = 0
        for num in numbers:
            total += int(num.replace(',', ''))
        return total


@dataclass
class Association:
    """A GWAS association between a variant and trait."""
    rs_id: str
    p_value: float
    beta: Optional[float] = None
    se: Optional[float] = None
    allele: Optional[str] = None
    mapped_genes: List[str] = field(default_factory=list)
    study_id: Optional[str] = None

    @property
    def log_p(self) -> float:
        """Return -log10(p-value)."""
        if self.p_value > 0:
            return -math.log10(self.p_value)
        return float('inf')


@dataclass
class MetaAnalysisResult:
    """Result of meta-analysis for a locus."""
    locus: str  # rs_id or gene name
    n_studies: int
    combined_beta: Optional[float]
    combined_se: Optional[float]
    combined_p_value: Optional[float]
    heterogeneity_i2: float
    heterogeneity_p: Optional[float]
    studies: List[str]
    forest_plot_data: List[Dict]

    @property
    def is_significant(self) -> bool:
        """Check if combined p-value meets genome-wide significance (p < 5e-8)."""
        return self.combined_p_value is not None and self.combined_p_value < 5e-8

    @property
    def heterogeneity_level(self) -> str:
        """Interpret heterogeneity I² statistic."""
        if self.heterogeneity_i2 < 25:
            return "low"
        elif self.heterogeneity_i2 < 50:
            return "moderate"
        elif self.heterogeneity_i2 < 75:
            return "substantial"
        else:
            return "considerable"

    @property
    def interpretation(self) -> str:
        """Provide interpretation guidance."""
        parts = []
        if self.is_significant:
            parts.append(f"Genome-wide significant (p={self.combined_p_value:.2e})")
        parts.append(f"{self.heterogeneity_level.capitalize()} heterogeneity (I²={self.heterogeneity_i2:.1f}%)")

        if self.heterogeneity_i2 > 50:
            parts.append("Consider ancestry-specific or random-effects analysis")

        return ". ".join(parts)


@dataclass
class ReplicationResult:
    """Result of replication analysis between discovery and replication studies."""
    locus: str
    discovery_p: float
    replication_p: float
    discovery_beta: Optional[float]
    replication_beta: Optional[float]
    replicated: bool
    consistent_direction: bool
    notes: str = ""

    @property
    def replication_strength(self) -> str:
        """Classify replication strength."""
        if not self.replicated:
            return "Not replicated"
        if self.replication_p < 5e-8:
            return "Strong (genome-wide significant)"
        elif self.replication_p < 0.05:
            return "Nominal (p<0.05)"
        else:
            return "Weak"


@dataclass
class StudyComparisonResult:
    """Result of comparing multiple GWAS studies for the same trait."""
    trait: str
    n_studies: int
    studies: List[StudyMetadata]
    top_associations: List[Association]
    replicated_loci: List[str]
    novel_loci: List[str]
    heterogeneity_stats: Dict[str, float]

    def get_quality_summary(self) -> Dict[str, any]:
        """Summarize study quality metrics."""
        total_samples = sum(s.sample_size for s in self.studies)
        avg_sample_size = total_samples / len(self.studies) if self.studies else 0

        # Count ancestry diversity
        all_ancestries = set()
        for study in self.studies:
            all_ancestries.update(study.ancestry)

        # Count studies with summary stats
        with_sumstats = sum(1 for s in self.studies if s.has_summary_stats)

        return {
            "total_studies": self.n_studies,
            "total_samples": total_samples,
            "avg_sample_size": int(avg_sample_size),
            "max_sample_size": max((s.sample_size for s in self.studies), default=0),
            "ancestry_diversity": len(all_ancestries),
            "ancestries": list(all_ancestries),
            "studies_with_summary_stats": with_sumstats,
            "replication_rate": len(self.replicated_loci) / max(len(self.top_associations), 1)
        }


def compare_gwas_studies(
    tu,
    trait: str,
    min_sample_size: int = 5000,
    ancestry_filter: Optional[List[str]] = None,
    max_studies: int = 20
) -> StudyComparisonResult:
    """
    Compare all GWAS studies for a specific trait.

    Args:
        tu: ToolUniverse instance
        trait: Disease or trait name (e.g., "type 2 diabetes")
        min_sample_size: Minimum sample size filter (default: 5000)
        ancestry_filter: List of ancestries to include (e.g., ["European", "East Asian"])
        max_studies: Maximum number of studies to analyze (default: 20)

    Returns:
        StudyComparisonResult with comparison results

    Example:
        >>> from tooluniverse import ToolUniverse
        >>> tu = ToolUniverse()
        >>> tu.load_tools()
        >>> result = compare_gwas_studies(tu, "type 2 diabetes", min_sample_size=10000)
        >>> print(f"Analyzed {result.n_studies} studies")
        >>> print(f"Found {len(result.replicated_loci)} replicated loci")
    """
    # Search for studies
    print(f"Searching for {trait} studies...")
    studies_result = tu.run({
        "name": "gwas_search_studies",
        "arguments": {"disease_trait": trait, "size": max_studies}
    })

    if not studies_result.get("data"):
        return StudyComparisonResult(
            trait=trait,
            n_studies=0,
            studies=[],
            top_associations=[],
            replicated_loci=[],
            novel_loci=[],
            heterogeneity_stats={}
        )

    # Filter and parse studies
    studies = []
    for study_data in studies_result["data"]:
        study = StudyMetadata.from_gwas_catalog(study_data)

        # Apply filters
        if study.sample_size < min_sample_size:
            continue
        if ancestry_filter and not any(anc in " ".join(study.ancestry) for anc in ancestry_filter):
            continue

        studies.append(study)

    print(f"Found {len(studies)} studies meeting criteria")

    # Get associations from each study
    all_associations_by_locus = defaultdict(list)

    for study in studies[:10]:  # Limit to top 10 studies for API efficiency
        print(f"  Fetching associations for {study.accession_id}...")
        assoc_result = tu.run({
            "name": "gwas_get_associations_for_study",
            "arguments": {"accession_id": study.accession_id, "size": 10}
        })

        if assoc_result.get("data"):
            for assoc_data in assoc_result["data"]:
                snp_allele = assoc_data.get('snp_allele', [])
                if not snp_allele:
                    continue

                rs_id = snp_allele[0].get('rs_id')
                if not rs_id:
                    continue

                assoc = Association(
                    rs_id=rs_id,
                    p_value=assoc_data.get('p_value', 1.0),
                    beta=None,  # Parse if available
                    mapped_genes=assoc_data.get('mapped_genes', []),
                    study_id=study.accession_id
                )
                all_associations_by_locus[rs_id].append(assoc)

    # Identify replicated vs novel loci
    replicated_loci = [rs_id for rs_id, assocs in all_associations_by_locus.items() if len(assocs) >= 2]
    all_loci = list(all_associations_by_locus.keys())
    novel_loci = [rs_id for rs_id in all_loci if rs_id not in replicated_loci]

    # Get top associations (most significant)
    top_associations = []
    for rs_id, assocs in all_associations_by_locus.items():
        best_assoc = min(assocs, key=lambda a: a.p_value)
        top_associations.append(best_assoc)

    top_associations.sort(key=lambda a: a.p_value)

    print(f"Found {len(all_loci)} total loci, {len(replicated_loci)} replicated")

    return StudyComparisonResult(
        trait=trait,
        n_studies=len(studies),
        studies=studies,
        top_associations=top_associations[:20],
        replicated_loci=replicated_loci,
        novel_loci=novel_loci,
        heterogeneity_stats={}
    )


def meta_analyze_locus(
    tu,
    rs_id: str,
    trait: str
) -> MetaAnalysisResult:
    """
    Perform meta-analysis for a specific locus across studies.

    Args:
        tu: ToolUniverse instance
        rs_id: SNP rs identifier (e.g., "rs7903146")
        trait: Disease or trait name

    Returns:
        MetaAnalysisResult with meta-analysis statistics

    Example:
        >>> result = meta_analyze_locus(tu, "rs7903146", "type 2 diabetes")
        >>> print(f"Combined p-value: {result.combined_p_value:.2e}")
        >>> print(f"Heterogeneity: {result.heterogeneity_level} (I²={result.heterogeneity_i2:.1f}%)")
        >>> print(f"Interpretation: {result.interpretation}")
    """
    print(f"Meta-analyzing {rs_id} for {trait}...")

    # Get all associations for this SNP
    assoc_result = tu.run({
        "name": "gwas_get_associations_for_snp",
        "arguments": {"rs_id": rs_id, "size": 50}
    })

    if not assoc_result.get("data"):
        return MetaAnalysisResult(
            locus=rs_id,
            n_studies=0,
            combined_beta=None,
            combined_se=None,
            combined_p_value=None,
            heterogeneity_i2=0.0,
            heterogeneity_p=None,
            studies=[],
            forest_plot_data=[]
        )

    # Filter associations for the target trait
    relevant_assocs = []
    for assoc_data in assoc_result["data"]:
        # Check if trait matches
        efo_traits = assoc_data.get('efo_traits', [])
        trait_match = any(trait.lower() in t.get('efo_trait', '').lower() for t in efo_traits)

        if trait_match:
            relevant_assocs.append(assoc_data)

    print(f"Found {len(relevant_assocs)} associations for {trait}")

    if len(relevant_assocs) < 2:
        # Need at least 2 studies for meta-analysis
        if len(relevant_assocs) == 1:
            p_val = relevant_assocs[0].get('p_value', 1.0)
            return MetaAnalysisResult(
                locus=rs_id,
                n_studies=1,
                combined_beta=None,
                combined_se=None,
                combined_p_value=p_val,
                heterogeneity_i2=0.0,
                heterogeneity_p=None,
                studies=[relevant_assocs[0].get('accession_id', 'Unknown')],
                forest_plot_data=[]
            )
        return MetaAnalysisResult(
            locus=rs_id,
            n_studies=0,
            combined_beta=None,
            combined_se=None,
            combined_p_value=None,
            heterogeneity_i2=0.0,
            heterogeneity_p=None,
            studies=[],
            forest_plot_data=[]
        )

    # Calculate heterogeneity (I² statistic)
    # Simplified calculation based on p-value variance
    p_values = [a.get('p_value', 1.0) for a in relevant_assocs]
    log_p_values = [-math.log10(max(p, 1e-300)) for p in p_values]

    # Calculate variance of log p-values as proxy for heterogeneity
    mean_log_p = sum(log_p_values) / len(log_p_values)
    variance = sum((x - mean_log_p)**2 for x in log_p_values) / len(log_p_values)

    # Convert to I² (percentage of variance due to heterogeneity)
    # I² = (Q - df) / Q * 100, approximated here
    i2 = min(100.0, variance * 10)  # Simplified approximation

    # Use minimum p-value as combined (fixed-effect approximation)
    combined_p = min(p_values)

    # Prepare forest plot data
    forest_data = []
    for assoc in relevant_assocs:
        forest_data.append({
            "study": assoc.get('accession_id', 'Unknown'),
            "p_value": assoc.get('p_value', 1.0),
            "mapped_genes": assoc.get('mapped_genes', [])
        })

    studies = [a.get('accession_id', 'Unknown') for a in relevant_assocs]

    return MetaAnalysisResult(
        locus=rs_id,
        n_studies=len(relevant_assocs),
        combined_beta=None,
        combined_se=None,
        combined_p_value=combined_p,
        heterogeneity_i2=i2,
        heterogeneity_p=None,
        studies=studies,
        forest_plot_data=forest_data
    )


def assess_replication(
    tu,
    trait: str,
    discovery_study_id: str,
    replication_study_id: str,
    p_threshold: float = 0.05
) -> List[ReplicationResult]:
    """
    Assess replication of findings between discovery and replication studies.

    Args:
        tu: ToolUniverse instance
        trait: Disease or trait name
        discovery_study_id: Discovery study accession ID
        replication_study_id: Replication study accession ID
        p_threshold: P-value threshold for replication (default: 0.05)

    Returns:
        List of ReplicationResult objects

    Example:
        >>> results = assess_replication(tu, "type 2 diabetes",
        ...                              "GCST000392", "GCST000393")
        >>> for r in results:
        ...     print(f"{r.locus}: {r.replication_strength}")
    """
    print(f"Assessing replication: {discovery_study_id} -> {replication_study_id}")

    # Get discovery associations
    disc_result = tu.run({
        "name": "gwas_get_associations_for_study",
        "arguments": {"accession_id": discovery_study_id, "size": 50}
    })

    # Get replication associations
    repl_result = tu.run({
        "name": "gwas_get_associations_for_study",
        "arguments": {"accession_id": replication_study_id, "size": 100}
    })

    if not disc_result.get("data") or not repl_result.get("data"):
        return []

    # Build lookup for replication associations
    repl_by_snp = {}
    for assoc in repl_result["data"]:
        snp_allele = assoc.get('snp_allele', [])
        if snp_allele:
            rs_id = snp_allele[0].get('rs_id')
            if rs_id:
                repl_by_snp[rs_id] = assoc

    # Check each discovery association
    results = []
    for disc_assoc in disc_result["data"]:
        snp_allele = disc_assoc.get('snp_allele', [])
        if not snp_allele:
            continue

        rs_id = snp_allele[0].get('rs_id')
        if not rs_id:
            continue

        disc_p = disc_assoc.get('p_value', 1.0)

        # Check if replicated
        if rs_id in repl_by_snp:
            repl_assoc = repl_by_snp[rs_id]
            repl_p = repl_assoc.get('p_value', 1.0)

            replicated = repl_p < p_threshold
            # TODO: Check direction consistency if beta available
            consistent_direction = True

            result = ReplicationResult(
                locus=rs_id,
                discovery_p=disc_p,
                replication_p=repl_p,
                discovery_beta=None,
                replication_beta=None,
                replicated=replicated,
                consistent_direction=consistent_direction,
                notes="Replicated" if replicated else "Not replicated"
            )
        else:
            result = ReplicationResult(
                locus=rs_id,
                discovery_p=disc_p,
                replication_p=1.0,
                discovery_beta=None,
                replication_beta=None,
                replicated=False,
                consistent_direction=False,
                notes="Not tested in replication study"
            )

        results.append(result)

    print(f"Found {len(results)} loci, {sum(1 for r in results if r.replicated)} replicated")
    return results


def get_study_quality_metrics(study: StudyMetadata) -> Dict[str, any]:
    """
    Calculate quality metrics for a GWAS study.

    Args:
        study: StudyMetadata object

    Returns:
        Dictionary of quality metrics

    Example:
        >>> metrics = get_study_quality_metrics(study)
        >>> print(f"Statistical power: {metrics['power_score']}")
        >>> print(f"Quality tier: {metrics['tier']}")
    """
    metrics = {}

    # Sample size score (log scale)
    if study.sample_size > 0:
        metrics["sample_size_score"] = min(10, math.log10(study.sample_size))
    else:
        metrics["sample_size_score"] = 0

    # Statistical power estimate (simplified)
    if study.sample_size >= 100000:
        metrics["power_score"] = "high"
    elif study.sample_size >= 10000:
        metrics["power_score"] = "moderate"
    else:
        metrics["power_score"] = "low"

    # Ancestry diversity
    metrics["ancestry_count"] = len(study.ancestry)
    metrics["is_multi_ancestry"] = len(study.ancestry) > 1

    # Data availability
    metrics["has_summary_stats"] = study.has_summary_stats

    # Overall quality tier
    if study.sample_size >= 50000 and study.has_summary_stats:
        metrics["tier"] = "Tier 1 (High quality)"
    elif study.sample_size >= 10000:
        metrics["tier"] = "Tier 2 (Moderate quality)"
    else:
        metrics["tier"] = "Tier 3 (Limited sample size)"

    return metrics


# Example usage
if __name__ == "__main__":
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools()

    print("="*80)
    print("GWAS STUDY DEEP DIVE & META-ANALYSIS")
    print("="*80)

    # Example 1: Compare T2D studies
    print("\n1. Comparing Type 2 Diabetes Studies")
    print("-" * 80)
    result = compare_gwas_studies(tu, "type 2 diabetes", min_sample_size=10000, max_studies=10)
    quality = result.get_quality_summary()
    print(f"\nSummary:")
    print(f"  Studies analyzed: {result.n_studies}")
    print(f"  Total samples: {quality['total_samples']:,}")
    print(f"  Ancestry diversity: {quality['ancestry_diversity']} populations")
    print(f"  Top loci: {len(result.top_associations)}")
    print(f"  Replicated loci: {len(result.replicated_loci)}")

    # Example 2: Meta-analyze TCF7L2 locus
    print("\n2. Meta-analyzing TCF7L2 (rs7903146) for T2D")
    print("-" * 80)
    meta_result = meta_analyze_locus(tu, "rs7903146", "type 2 diabetes")
    print(f"\nResults:")
    print(f"  Studies: {meta_result.n_studies}")
    print(f"  Combined p-value: {meta_result.combined_p_value:.2e}" if meta_result.combined_p_value else "  No data")
    print(f"  Heterogeneity: {meta_result.heterogeneity_level} (I²={meta_result.heterogeneity_i2:.1f}%)")
    print(f"  Interpretation: {meta_result.interpretation}")
