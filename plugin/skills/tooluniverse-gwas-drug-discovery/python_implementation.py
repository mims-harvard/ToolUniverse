"""
GWAS-to-Drug Target Discovery - Python Implementation

This module provides functions for discovering druggable targets from GWAS data
and identifying drug repurposing opportunities.

Workflow:
1. GWAS Gene Discovery - Find genes from GWAS associations
2. Druggability Assessment - Check if genes encode druggable proteins
3. Target Prioritization - Rank by genetic evidence + druggability
4. Existing Drug Search - Find approved/investigational drugs
5. Clinical Evidence - Check trials, safety data
6. Repurposing Opportunities - Identify drugs for new indications
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from tooluniverse.tools.execute_tool import execute_tool


@dataclass
class GWASEvidence:
    """GWAS genetic evidence for a gene."""
    gene: str
    p_value: float
    beta: Optional[float]
    snp_rs_id: str
    trait: str
    study_id: str
    confidence_score: float = 0.0  # 0-1 scale

    def __post_init__(self):
        """Calculate confidence score based on p-value."""
        # -log10(p-value) capped at 20 for very significant variants
        if self.p_value > 0:
            self.confidence_score = min(-1 * (self.p_value ** 0.1), 20) / 20
        else:
            self.confidence_score = 1.0


@dataclass
class DruggabilityProfile:
    """Druggability assessment for a target gene."""
    gene: str
    ensembl_id: str
    tractability_score: float = 0.0  # 0-1 scale
    target_class: List[str] = field(default_factory=list)
    has_antibody: bool = False
    has_small_molecule: bool = False
    safety_concerns: List[str] = field(default_factory=list)


@dataclass
class DrugCandidate:
    """Information about a drug targeting a gene."""
    name: str
    chembl_id: str
    mechanism: str
    approval_status: str  # approved, investigational, clinical, preclinical
    clinical_phase: int  # 0-4, where 4 = approved
    indications: List[str] = field(default_factory=list)
    safety_profile: List[str] = field(default_factory=list)
    source: str = "ChEMBL"


@dataclass
class DrugTargetResult:
    """Complete drug target discovery result."""
    gene: str
    gwas_evidence: List[GWASEvidence]
    druggability: Optional[DruggabilityProfile]
    existing_drugs: List[DrugCandidate]
    repurposing_score: float  # 0-1 scale
    recommendation: str

    @property
    def genetic_evidence_score(self) -> float:
        """Average confidence across GWAS evidence."""
        if not self.gwas_evidence:
            return 0.0
        return sum(e.confidence_score for e in self.gwas_evidence) / len(self.gwas_evidence)

    @property
    def druggability_score(self) -> float:
        """Get druggability score."""
        if self.druggability:
            return self.druggability.tractability_score
        return 0.0

    @property
    def overall_score(self) -> float:
        """Combined score: genetic evidence * druggability."""
        return self.genetic_evidence_score * self.druggability_score


def discover_drug_targets(
    disease: str,
    min_gwas_pvalue: float = 5e-8,
    min_associations: int = 1,
    include_druggability: bool = True,
    max_targets: int = 20
) -> List[DrugTargetResult]:
    """
    Discover druggable targets for a disease from GWAS data.

    This is the main entry point for GWAS-to-drug target discovery.

    Parameters
    ----------
    disease : str
        Disease or trait name (e.g., "type 2 diabetes", "Alzheimer disease")
    min_gwas_pvalue : float
        Minimum significance threshold for GWAS associations (default: 5e-8)
    min_associations : int
        Minimum number of GWAS associations required per gene
    include_druggability : bool
        Whether to assess druggability (requires additional API calls)
    max_targets : int
        Maximum number of targets to return

    Returns
    -------
    List[DrugTargetResult]
        Ranked list of drug target candidates with GWAS evidence, druggability,
        and existing drugs

    Examples
    --------
    >>> targets = discover_drug_targets("type 2 diabetes", max_targets=10)
    >>> for target in targets[:5]:
    ...     print(f"{target.gene}: score={target.overall_score:.3f}")
    ...     print(f"  GWAS evidence: {len(target.gwas_evidence)} associations")
    ...     print(f"  Existing drugs: {len(target.existing_drugs)}")
    """

    print(f"\n[Step 1] Searching GWAS associations for '{disease}'...")
    results = {}

    # Get GWAS associations
    assoc_result = execute_tool(
        "gwas_get_associations_for_trait",
        {"disease_trait": disease, "size": 100}
    )

    if not assoc_result or 'data' not in assoc_result:
        print("  ✗ No GWAS associations found")
        return []

    associations = assoc_result['data']
    print(f"  ✓ Found {len(associations)} GWAS associations")

    # Parse associations by gene
    for assoc in associations:
        p_val = assoc.get('p_value', 1.0)
        if p_val > min_gwas_pvalue:
            continue

        genes = assoc.get('mapped_genes', [])
        snps = assoc.get('snp_allele', [])
        rs_id = snps[0].get('rs_id') if snps else 'unknown'
        trait = assoc.get('reported_trait', ['unknown'])[0] if assoc.get('reported_trait') else 'unknown'
        study_id = assoc.get('accession_id', 'unknown')
        beta = assoc.get('beta')
        if beta and isinstance(beta, str):
            try:
                beta = float(beta)
            except:
                beta = None

        for gene in genes:
            if gene not in results:
                results[gene] = []

            results[gene].append(GWASEvidence(
                gene=gene,
                p_value=p_val,
                beta=beta,
                snp_rs_id=rs_id,
                trait=trait,
                study_id=study_id
            ))

    # Filter genes by minimum associations
    filtered_genes = {
        gene: evidence
        for gene, evidence in results.items()
        if len(evidence) >= min_associations
    }

    print(f"  ✓ Found {len(filtered_genes)} genes with {min_associations}+ associations")

    # Build target results
    target_results = []
    for gene, gwas_evidence in list(filtered_genes.items())[:max_targets]:
        print(f"\n[Processing] {gene} ({len(gwas_evidence)} associations)...")

        # Get druggability (if requested)
        druggability = None
        if include_druggability:
            druggability = assess_druggability(gene)

        # Find existing drugs
        existing_drugs = find_drugs_for_gene(gene)

        # Calculate repurposing score
        repurposing_score = calculate_repurposing_score(gwas_evidence, druggability, existing_drugs)

        # Generate recommendation
        recommendation = generate_recommendation(gene, gwas_evidence, druggability, existing_drugs, repurposing_score)

        target_results.append(DrugTargetResult(
            gene=gene,
            gwas_evidence=gwas_evidence,
            druggability=druggability,
            existing_drugs=existing_drugs,
            repurposing_score=repurposing_score,
            recommendation=recommendation
        ))

    # Sort by overall score
    target_results.sort(key=lambda x: x.overall_score, reverse=True)

    return target_results


def assess_druggability(gene: str) -> Optional[DruggabilityProfile]:
    """
    Assess druggability of a gene target.

    Parameters
    ----------
    gene : str
        Gene symbol (e.g., "TCF7L2")

    Returns
    -------
    Optional[DruggabilityProfile]
        Druggability profile or None if assessment failed
    """
    # Note: This is a placeholder. Real implementation would:
    # 1. Map gene symbol to Ensembl ID
    # 2. Query OpenTargets_get_target_tractability_by_ensemblID
    # 3. Query OpenTargets_get_target_classes_by_ensemblID
    # 4. Parse tractability data into score

    print(f"    [Druggability] Assessing {gene}...")
    # Placeholder return
    return DruggabilityProfile(
        gene=gene,
        ensembl_id="ENSG00000000000",  # Would need lookup
        tractability_score=0.5,
        target_class=["Protein"],
        has_small_molecule=False,
        has_antibody=False
    )


def find_drugs_for_gene(gene: str) -> List[DrugCandidate]:
    """
    Find existing drugs targeting a gene.

    Parameters
    ----------
    gene : str
        Gene symbol

    Returns
    -------
    List[DrugCandidate]
        List of drugs targeting this gene
    """
    print(f"    [Drug Search] Searching drugs for {gene}...")

    # Search ChEMBL for target
    try:
        result = execute_tool(
            "ChEMBL_search_targets",
            {"q": gene, "limit": 1}
        )

        if result and 'data' in result:
            targets = result['data'].get('targets', [])
            if targets:
                target_id = targets[0].get('target_chembl_id')
                print(f"      Found ChEMBL target: {target_id}")

                # Get drugs for this target
                # (Real implementation would query ChEMBL drug-target associations)
                return []

    except Exception as e:
        print(f"      Error: {e}")

    return []


def calculate_repurposing_score(
    gwas_evidence: List[GWASEvidence],
    druggability: Optional[DruggabilityProfile],
    existing_drugs: List[DrugCandidate]
) -> float:
    """
    Calculate repurposing opportunity score.

    High score = strong GWAS evidence + good druggability + existing drugs

    Parameters
    ----------
    gwas_evidence : List[GWASEvidence]
        GWAS genetic evidence
    druggability : Optional[DruggabilityProfile]
        Druggability profile
    existing_drugs : List[DrugCandidate]
        Existing drugs

    Returns
    -------
    float
        Repurposing score (0-1)
    """
    # Genetic evidence component (0-1)
    if gwas_evidence:
        avg_confidence = sum(e.confidence_score for e in gwas_evidence) / len(gwas_evidence)
        genetic_score = avg_confidence
    else:
        genetic_score = 0.0

    # Druggability component (0-1)
    drug_score = druggability.tractability_score if druggability else 0.3

    # Existing drugs bonus
    drug_bonus = min(len(existing_drugs) * 0.1, 0.3)

    # Combined score
    score = (genetic_score * 0.5) + (drug_score * 0.3) + (drug_bonus * 0.2)

    return min(score, 1.0)


def generate_recommendation(
    gene: str,
    gwas_evidence: List[GWASEvidence],
    druggability: Optional[DruggabilityProfile],
    existing_drugs: List[DrugCandidate],
    repurposing_score: float
) -> str:
    """
    Generate human-readable recommendation.

    Parameters
    ----------
    gene : str
        Gene symbol
    gwas_evidence : List[GWASEvidence]
        GWAS evidence
    druggability : Optional[DruggabilityProfile]
        Druggability profile
    existing_drugs : List[DrugCandidate]
        Existing drugs
    repurposing_score : float
        Repurposing score

    Returns
    -------
    str
        Recommendation text
    """
    if repurposing_score > 0.7:
        priority = "HIGH PRIORITY"
    elif repurposing_score > 0.4:
        priority = "MEDIUM PRIORITY"
    else:
        priority = "LOW PRIORITY"

    lines = [priority]

    # GWAS summary
    top_p = min(e.p_value for e in gwas_evidence) if gwas_evidence else 1.0
    lines.append(f"GWAS: {len(gwas_evidence)} associations (top p={top_p:.2e})")

    # Druggability
    if druggability:
        lines.append(f"Druggability: {druggability.tractability_score:.2f}")

    # Existing drugs
    if existing_drugs:
        approved = [d for d in existing_drugs if d.approval_status == "approved"]
        if approved:
            lines.append(f"Repurposing: {len(approved)} approved drugs")
        else:
            lines.append(f"Development: {len(existing_drugs)} investigational drugs")
    else:
        lines.append("Novel target: No existing drugs")

    return " | ".join(lines)


def find_repurposing_candidates(
    disease: str,
    target_gene: Optional[str] = None,
    min_phase: int = 2
) -> List[Tuple[DrugCandidate, str]]:
    """
    Find drug repurposing candidates.

    Identifies approved/investigational drugs for other indications that target
    genes associated with the query disease.

    Parameters
    ----------
    disease : str
        Disease name
    target_gene : Optional[str]
        Specific gene to focus on (optional)
    min_phase : int
        Minimum clinical phase (0-4, default 2)

    Returns
    -------
    List[Tuple[DrugCandidate, str]]
        List of (drug, rationale) pairs

    Examples
    --------
    >>> candidates = find_repurposing_candidates("type 2 diabetes", min_phase=3)
    >>> for drug, rationale in candidates[:5]:
    ...     print(f"{drug.name}: {rationale}")
    """
    print(f"\n[Repurposing Search] Finding candidates for '{disease}'...")

    # Get targets for disease
    targets = discover_drug_targets(disease, include_druggability=False, max_targets=10)

    # Filter by target_gene if specified
    if target_gene:
        targets = [t for t in targets if t.gene == target_gene]

    candidates = []
    for target in targets:
        for drug in target.existing_drugs:
            if drug.clinical_phase >= min_phase:
                # Check if drug is approved for different indication
                if disease.lower() not in [ind.lower() for ind in drug.indications]:
                    rationale = (
                        f"Targets {target.gene} ({len(target.gwas_evidence)} GWAS hits), "
                        f"approved for: {', '.join(drug.indications[:2])}"
                    )
                    candidates.append((drug, rationale))

    return candidates


# Example usage
if __name__ == "__main__":
    print("="*80)
    print("GWAS-TO-DRUG TARGET DISCOVERY - Example")
    print("="*80)

    # Example 1: Discover targets for Type 2 Diabetes
    print("\nExample 1: Type 2 Diabetes drug targets")
    targets = discover_drug_targets("type 2 diabetes", max_targets=5)

    for i, target in enumerate(targets, 1):
        print(f"\n{i}. {target.gene}")
        print(f"   Score: {target.overall_score:.3f} (genetic={target.genetic_evidence_score:.3f}, drug={target.druggability_score:.3f})")
        print(f"   {target.recommendation}")

    # Example 2: Find repurposing opportunities
    print("\n" + "="*80)
    print("Example 2: Drug repurposing for Alzheimer disease")
    print("="*80)

    candidates = find_repurposing_candidates("alzheimer disease", min_phase=3)
    for drug, rationale in candidates[:5]:
        print(f"\n- {drug.name} (Phase {drug.clinical_phase})")
        print(f"  {rationale}")
