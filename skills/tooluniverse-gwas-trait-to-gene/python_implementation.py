"""
GWAS Trait-to-Gene Discovery Implementation

This module provides a high-level function to discover genes associated with
diseases/traits using GWAS data from GWAS Catalog and Open Targets Genetics.

Example:
    >>> from tooluniverse_skills import discover_gwas_genes
    >>> results = discover_gwas_genes("type 2 diabetes")
    >>> for gene in results[:5]:
    ...     print(f"{gene.symbol}: p={gene.min_p_value:.2e}, evidence={gene.evidence_count}")
"""

from dataclasses import dataclass, field
from typing import List, Optional
from collections import defaultdict
import warnings

try:
    from tooluniverse.tools import (
        gwas_get_associations_for_trait,
        OpenTargets_search_gwas_studies_by_disease,
        OpenTargets_get_study_credible_sets,
    )
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False
    warnings.warn("ToolUniverse not installed. Install with: pip install tooluniverse")


@dataclass
class GWASGeneResult:
    """
    A gene with GWAS evidence for trait association.

    Attributes:
        symbol: Gene symbol (e.g., 'TCF7L2')
        min_p_value: Most significant p-value across all associations
        evidence_count: Number of independent GWAS associations
        snps: List of associated SNP rs IDs
        studies: List of GWAS study accession IDs
        l2g_score: Best locus-to-gene score (0-1) from fine-mapping (if available)
        credible_sets: Number of credible sets containing this gene
    """
    symbol: str
    min_p_value: float
    evidence_count: int
    snps: List[str] = field(default_factory=list)
    studies: List[str] = field(default_factory=list)
    l2g_score: Optional[float] = None
    credible_sets: int = 0

    @property
    def confidence_level(self) -> str:
        """
        Categorize confidence based on evidence strength.

        Returns:
            'High', 'Medium', or 'Low' confidence
        """
        if self.l2g_score and self.l2g_score > 0.5:
            return "High"
        elif self.evidence_count >= 3 and self.min_p_value < 5e-10:
            return "High"
        elif self.evidence_count >= 2 and self.min_p_value < 5e-8:
            return "Medium"
        else:
            return "Low"


def discover_gwas_genes(
    trait: str,
    p_value_threshold: float = 5e-8,
    min_evidence_count: int = 1,
    max_results: int = 100,
    use_fine_mapping: bool = True,
    disease_ontology_id: Optional[str] = None,
) -> List[GWASGeneResult]:
    """
    Discover genes associated with a trait/disease from GWAS data.

    This function:
    1. Searches GWAS Catalog for trait associations
    2. Filters by genome-wide significance threshold
    3. Aggregates evidence across studies
    4. Optionally enriches with fine-mapping data from Open Targets
    5. Ranks genes by statistical significance and evidence count

    Args:
        trait: Disease or trait name (e.g., "type 2 diabetes", "coronary artery disease")
        p_value_threshold: Significance threshold (default: 5e-8 for genome-wide significance)
        min_evidence_count: Minimum number of associations required (default: 1)
        max_results: Maximum number of genes to return (default: 100)
        use_fine_mapping: Include locus-to-gene predictions from Open Targets (default: True)
        disease_ontology_id: Optional disease ontology ID (e.g., "MONDO_0005148" for T2D)

    Returns:
        List of GWASGeneResult objects ranked by significance

    Example:
        >>> # Find genes for type 2 diabetes
        >>> results = discover_gwas_genes(
        ...     "type 2 diabetes",
        ...     p_value_threshold=5e-8,
        ...     min_evidence_count=2
        ... )
        >>> for gene in results[:10]:
        ...     print(f"{gene.symbol}: {gene.confidence_level} confidence")
        TCF7L2: High confidence
        KCNJ11: High confidence
        ...

    Note:
        Some GWAS tools have validation bugs and require validate=False.
        This is automatically handled in the implementation.
    """
    if not TOOLS_AVAILABLE:
        raise ImportError("ToolUniverse not available. Install with: pip install tooluniverse")

    # Data structures for aggregation
    gene_data = defaultdict(lambda: {
        'min_p': float('inf'),
        'snps': set(),
        'studies': set(),
        'l2g_score': None,
        'credible_sets': 0
    })

    # Step 1: Get associations from GWAS Catalog
    print(f"Searching GWAS Catalog for '{trait}'...")
    try:
        # Note: validate=False due to oneOf validation bug in some tools
        assoc_result = gwas_get_associations_for_trait(
            disease_trait=trait,
            size=max_results * 2,  # Get extra to ensure enough after filtering
            validate=False
        )

        associations = assoc_result.get('data', [])
        print(f"  Found {len(associations)} associations")

        # Extract gene-level evidence
        for assoc in associations:
            p_value = assoc.get('p_value')
            # Handle p_value == 0.0 (underflow in very significant associations)
            # and valid p-values below threshold
            if p_value is None or (p_value != 0.0 and p_value >= p_value_threshold):
                continue

            study_id = assoc.get('accession_id')
            snp_alleles = assoc.get('snp_allele', [])
            snps = [s.get('rs_id') for s in snp_alleles if s.get('rs_id')]
            genes = assoc.get('mapped_genes', [])

            for gene in genes:
                # Use small value for p=0.0 (underflow)
                effective_p = p_value if p_value > 0 else 1e-300
                gene_data[gene]['min_p'] = min(gene_data[gene]['min_p'], effective_p)
                gene_data[gene]['snps'].update(snps)
                if study_id:
                    gene_data[gene]['studies'].add(study_id)

    except Exception as e:
        print(f"  Warning: GWAS Catalog search failed: {e}")

    # Step 2: Optionally enrich with Open Targets fine-mapping data
    if use_fine_mapping and disease_ontology_id:
        print(f"Enriching with Open Targets fine-mapping data...")
        try:
            # Search for GWAS studies
            studies_result = OpenTargets_search_gwas_studies_by_disease(
                diseaseIds=[disease_ontology_id],
                size=20
            )

            study_ids = [
                s['id'] for s in studies_result.get('data', {}).get('studies', {}).get('rows', [])
            ]

            if study_ids:
                print(f"  Found {len(study_ids)} Open Targets studies")
                # Get credible sets (fine-mapped loci)
                for study_id in study_ids[:5]:  # Limit to top 5 studies
                    credible_result = OpenTargets_get_study_credible_sets(
                        studyIds=[study_id],
                        size=50
                    )

                    credible_sets = credible_result.get('data', {}).get('credibleSets', {}).get('rows', [])

                    for cs in credible_sets:
                        # Extract locus-to-gene predictions
                        l2g_predictions = cs.get('l2GPredictions', {}).get('rows', [])
                        for pred in l2g_predictions:
                            target = pred.get('target', {})
                            gene = target.get('approvedSymbol')
                            score = pred.get('score')

                            if gene and score:
                                gene_data[gene]['credible_sets'] += 1
                                if gene_data[gene]['l2g_score'] is None or score > gene_data[gene]['l2g_score']:
                                    gene_data[gene]['l2g_score'] = score

        except Exception as e:
            print(f"  Warning: Open Targets enrichment failed: {e}")

    # Step 3: Build result objects
    print(f"Aggregating evidence for {len(gene_data)} genes...")
    results = []
    for gene, data in gene_data.items():
        evidence_count = len(data['studies'])
        if evidence_count < min_evidence_count:
            continue

        results.append(GWASGeneResult(
            symbol=gene,
            min_p_value=data['min_p'],
            evidence_count=evidence_count,
            snps=list(data['snps']),
            studies=list(data['studies']),
            l2g_score=data['l2g_score'],
            credible_sets=data['credible_sets']
        ))

    # Step 4: Rank by significance and evidence
    # Primary sort: p-value (lower is better)
    # Secondary sort: evidence count (higher is better)
    # Tertiary sort: L2G score (higher is better)
    results.sort(key=lambda x: (
        x.min_p_value,
        -x.evidence_count,
        -(x.l2g_score or 0)
    ))

    print(f"Returning top {min(max_results, len(results))} genes")
    return results[:max_results]


# Convenience exports
__all__ = ['discover_gwas_genes', 'GWASGeneResult']
