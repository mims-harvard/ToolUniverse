"""
Protein Interaction Network Analysis - Python Implementation

This module provides functions for analyzing protein interaction networks using
STRING, BioGRID, and SASBDB databases. Follows 4-phase workflow with fallback
strategies for robustness.

Usage:
    from tooluniverse import ToolUniverse
    from python_implementation import analyze_protein_network

    tu = ToolUniverse()
    result = analyze_protein_network(
        tu=tu,
        proteins=["TP53", "MDM2", "ATM"],
        species=9606
    )
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ProteinNetworkResult:
    """Results from protein network analysis."""

    # Phase 1: Identifier mapping
    mapped_proteins: List[Dict[str, Any]]
    mapping_success_rate: float

    # Phase 2: Network retrieval
    network_edges: List[Dict[str, Any]]
    total_interactions: int

    # Phase 3: Enrichment analysis
    enriched_terms: List[Dict[str, Any]]
    ppi_enrichment: Dict[str, Any]

    # Phase 4: Structural data (optional)
    structural_data: Optional[List[Dict[str, Any]]]

    # Metadata
    primary_source: str  # "STRING" or "BioGRID"
    warnings: List[str]


def analyze_protein_network(
    tu,
    proteins: List[str],
    species: int = 9606,
    confidence_score: float = 0.7,
    include_biogrid: bool = False,
    include_structure: bool = False,
    suppress_warnings: bool = True
) -> ProteinNetworkResult:
    """
    Analyze protein interaction network using ToolUniverse tools.

    This function implements a 4-phase workflow:
    1. Identifier mapping (STRING)
    2. Network retrieval (STRING primary, BioGRID fallback)
    3. Enrichment analysis (functional + PPI)
    4. Structural data (optional, SASBDB)

    Parameters
    ----------
    tu : ToolUniverse
        ToolUniverse instance with loaded tools
    proteins : list[str]
        List of protein identifiers (gene symbols, UniProt IDs)
    species : int
        NCBI taxonomy ID (default: 9606 for human)
    confidence_score : float
        Minimum interaction confidence (0-1, default: 0.7)
    include_biogrid : bool
        Attempt BioGRID queries if API key available (default: False)
    include_structure : bool
        Include SASBDB structural data queries (default: False)
    suppress_warnings : bool
        Suppress ToolUniverse loading warnings (default: True)

    Returns
    -------
    ProteinNetworkResult
        Comprehensive analysis results with all phases
    """
    import sys
    import os

    warnings = []

    # Suppress ToolUniverse stderr warnings if requested (OS-level redirect)
    stderr_fd = None
    stderr_backup_fd = None
    if suppress_warnings:
        # Save original stderr file descriptor
        stderr_backup_fd = os.dup(2)
        # Redirect stderr to /dev/null
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 2)
        os.close(devnull)

    # ============================================================================
    # PHASE 1: Identifier Mapping (STRING)
    # ============================================================================
    print(f"\n🔍 Phase 1: Mapping {len(proteins)} protein identifiers...")

    try:
        mapping_result = tu.tools.STRING_map_identifiers(
            protein_ids=proteins,
            species=species,
            limit=1,
            echo_query=1
        )

        if mapping_result["status"] == "success":
            mapped_proteins = mapping_result["data"]
            success_rate = len(mapped_proteins) / len(proteins)
            print(f"✅ Mapped {len(mapped_proteins)}/{len(proteins)} proteins ({success_rate:.1%})")

            # Extract STRING IDs for next phase
            string_ids = [p["stringId"] for p in mapped_proteins]
        else:
            warnings.append(f"Mapping failed: {mapping_result.get('error', 'Unknown')}")
            mapped_proteins = []
            string_ids = proteins  # Try with original IDs
            success_rate = 0.0

    except Exception as e:
        warnings.append(f"Mapping error: {str(e)}")
        mapped_proteins = []
        string_ids = proteins
        success_rate = 0.0

    # ============================================================================
    # PHASE 2: Network Retrieval (STRING primary, BioGRID fallback)
    # ============================================================================
    print(f"\n🕸️  Phase 2: Retrieving interaction network...")

    network_edges = []
    primary_source = "STRING"

    # Try STRING first (always available)
    try:
        network_result = tu.tools.STRING_get_network(
            protein_ids=string_ids,
            species=species,
            confidence_score=confidence_score,
            add_nodes=0,
            network_type="functional"
        )

        if network_result["status"] == "success":
            network_edges = network_result["data"]
            print(f"✅ STRING: Retrieved {len(network_edges)} interactions")
        else:
            warnings.append(f"STRING network failed: {network_result.get('error', 'Unknown')}")

    except Exception as e:
        warnings.append(f"STRING network error: {str(e)}")

    # Fallback to BioGRID if enabled and API key available
    if include_biogrid and len(network_edges) == 0:
        print("⚠️  Falling back to BioGRID...")
        try:
            biogrid_result = tu.tools.BioGRID_get_interactions(
                gene_names=proteins,  # Use original names (plural!)
                organism=str(species),
                interaction_type="both",
                limit=100
            )

            if biogrid_result["status"] == "success":
                # BioGRID returns different format, adapt it
                network_edges = _adapt_biogrid_format(biogrid_result["data"])
                primary_source = "BioGRID"
                print(f"✅ BioGRID: Retrieved {len(network_edges)} interactions")
            else:
                warnings.append(f"BioGRID failed: {biogrid_result.get('error', 'Unknown')}")

        except Exception as e:
            warnings.append(f"BioGRID error: {str(e)}")

    total_interactions = len(network_edges)

    # ============================================================================
    # PHASE 3: Enrichment Analysis (Functional + PPI)
    # ============================================================================
    print(f"\n🧬 Phase 3: Performing enrichment analysis...")

    enriched_terms = []
    ppi_enrichment = {}

    # Functional enrichment (requires 3+ proteins)
    if len(string_ids) >= 3:
        try:
            func_result = tu.tools.STRING_functional_enrichment(
                protein_ids=string_ids,
                species=species,
                category="Process"  # GO Biological Process
            )

            if func_result["status"] == "success":
                enriched_terms = func_result["data"]
                # Filter to significant terms (FDR < 0.05)
                enriched_terms = [t for t in enriched_terms if t.get("fdr", 1.0) < 0.05]
                print(f"✅ Found {len(enriched_terms)} enriched GO terms (FDR < 0.05)")
            else:
                warnings.append(f"Functional enrichment failed: {func_result.get('error', 'Unknown')}")

        except Exception as e:
            warnings.append(f"Functional enrichment error: {str(e)}")
    else:
        warnings.append(f"Functional enrichment skipped: need 3+ proteins, have {len(string_ids)}")

    # PPI enrichment (tests if proteins interact more than random)
    if len(string_ids) >= 3:
        try:
            ppi_result = tu.tools.STRING_ppi_enrichment(
                protein_ids=string_ids,
                species=species,
                confidence_score=confidence_score
            )

            if ppi_result["status"] == "success":
                ppi_enrichment = ppi_result["data"]
                # Handle both dict and list responses
                if isinstance(ppi_enrichment, list) and len(ppi_enrichment) > 0:
                    ppi_enrichment = ppi_enrichment[0]
                p_value = ppi_enrichment.get("p_value", 1.0) if isinstance(ppi_enrichment, dict) else 1.0

                if p_value < 0.05:
                    print(f"✅ PPI enrichment significant (p={p_value:.2e})")
                else:
                    print(f"⚠️  PPI enrichment not significant (p={p_value:.2e})")
                    warnings.append(f"Proteins may not form functional module (p={p_value:.2e})")
            else:
                warnings.append(f"PPI enrichment failed: {ppi_result.get('error', 'Unknown')}")

        except Exception as e:
            warnings.append(f"PPI enrichment error: {str(e)}")
    else:
        warnings.append(f"PPI enrichment skipped: need 3+ proteins, have {len(string_ids)}")

    # ============================================================================
    # PHASE 4: Structural Data (Optional, SASBDB)
    # ============================================================================
    structural_data = None

    if include_structure:
        print(f"\n🔬 Phase 4: Searching structural data...")
        structural_data = []

        for protein in proteins[:3]:  # Limit to first 3 proteins
            try:
                struct_result = tu.tools.SASBDB_search_entries(
                    query=protein,
                    method="all",
                    limit=5
                )

                if struct_result["status"] == "success":
                    results = struct_result.get("data", {}).get("results", [])
                    if results:
                        structural_data.extend(results)
                        print(f"  ✅ {protein}: Found {len(results)} SAXS/SANS entries")
                    else:
                        print(f"  ℹ️  {protein}: No structural data")
                else:
                    warnings.append(f"SASBDB search failed for {protein}")

            except Exception as e:
                warnings.append(f"SASBDB error for {protein}: {str(e)}")

    # ============================================================================
    # Return Results
    # ============================================================================

    # Restore stderr (OS-level)
    if suppress_warnings and stderr_backup_fd is not None:
        os.dup2(stderr_backup_fd, 2)
        os.close(stderr_backup_fd)

    print(f"\n✅ Analysis complete!")
    print(f"   - Mapped: {len(mapped_proteins)} proteins")
    print(f"   - Interactions: {total_interactions}")
    print(f"   - Enriched terms: {len(enriched_terms)}")
    print(f"   - Source: {primary_source}")
    if warnings:
        print(f"   - Warnings: {len(warnings)}")

    return ProteinNetworkResult(
        mapped_proteins=mapped_proteins,
        mapping_success_rate=success_rate,
        network_edges=network_edges,
        total_interactions=total_interactions,
        enriched_terms=enriched_terms,
        ppi_enrichment=ppi_enrichment,
        structural_data=structural_data,
        primary_source=primary_source,
        warnings=warnings
    )


def _adapt_biogrid_format(biogrid_data: Any) -> List[Dict[str, Any]]:
    """
    Adapt BioGRID response format to STRING-like format for consistency.

    BioGRID returns different structure - this normalizes it.
    """
    # BioGRID format varies, implement conversion if needed
    # For now, return as-is
    if isinstance(biogrid_data, list):
        return biogrid_data
    elif isinstance(biogrid_data, dict):
        return [biogrid_data]
    else:
        return []


# ============================================================================
# Example Usage
# ============================================================================

def example_tp53_analysis():
    """
    Example: Analyze TP53 tumor suppressor network.

    This demonstrates the typical workflow for analyzing a protein network
    centered around TP53 and its key interaction partners.
    """
    import sys
    import os
    from tooluniverse import ToolUniverse

    print("=" * 80)
    print("Example: TP53 Tumor Suppressor Network Analysis")
    print("=" * 80)

    # Suppress ToolUniverse loading warnings (OS-level redirect)
    stderr_backup_fd = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    os.close(devnull)

    # Initialize ToolUniverse (only once!)
    tu = ToolUniverse()

    # Restore stderr
    os.dup2(stderr_backup_fd, 2)
    os.close(stderr_backup_fd)

    # Define proteins of interest
    proteins = [
        "TP53",    # Tumor suppressor
        "MDM2",    # TP53 negative regulator
        "ATM",     # DNA damage kinase
        "CHEK2",   # Checkpoint kinase
        "CDKN1A",  # p21, TP53 target
    ]

    # Run analysis
    result = analyze_protein_network(
        tu=tu,
        proteins=proteins,
        species=9606,  # Human
        confidence_score=0.7,  # High confidence
        include_biogrid=False,  # STRING only (no API key needed)
        include_structure=False  # Skip SASBDB (faster)
    )

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"\n📊 Mapping Success: {result.mapping_success_rate:.1%}")
    for p in result.mapped_proteins:
        print(f"   - {p['queryItem']} → {p['preferredName']} ({p['stringId']})")

    print(f"\n🕸️  Network: {result.total_interactions} interactions")
    print(f"   Source: {result.primary_source}")
    if result.network_edges:
        print(f"   Top interactions:")
        for edge in result.network_edges[:5]:
            score = edge.get("score", 0)
            print(f"      {edge.get('preferredName_A')} ↔ {edge.get('preferredName_B')} (score: {score})")

    print(f"\n🧬 Enrichment: {len(result.enriched_terms)} significant GO terms")
    if result.enriched_terms:
        print(f"   Top enriched processes:")
        for term in result.enriched_terms[:5]:
            print(f"      {term.get('term')} (FDR: {term.get('fdr', 1):.2e})")

    if result.ppi_enrichment and isinstance(result.ppi_enrichment, dict):
        p_val = result.ppi_enrichment.get("p_value", 1.0)
        print(f"\n🔗 PPI Enrichment: p-value = {p_val:.2e}")
        print(f"   Expected edges: {result.ppi_enrichment.get('expected_number_of_edges', 0):.1f}")
        print(f"   Observed edges: {result.ppi_enrichment.get('number_of_edges', 0)}")

    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"   - {warning}")

    return result


if __name__ == "__main__":
    # Run example analysis
    example_tp53_analysis()
