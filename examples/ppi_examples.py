"""
Protein-Protein Interaction (PPI) Tools Examples

This module demonstrates how to use PPI tools from ToolUniverse to:
1. Query protein interactions from STRING database
2. Query genetic/physical interactions from BioGRID database
3. Analyze interaction networks
4. Filter by confidence scores and interaction types

PPI tools available:
- STRING_get_protein_interactions: Query known and predicted protein-protein interactions
- BioGRID_get_interactions: Query curated physical and genetic interactions

Author: ToolUniverse
Date: February 2026
"""

import os
from tooluniverse import ToolUniverse


def example_1_basic_string_query():
    """
    Example 1: Basic STRING protein interaction query
    
    Query protein-protein interactions for TP53 and BRCA1 from STRING database.
    STRING provides confidence scores and interaction sources.
    """
    print("\n" + "="*80)
    print("Example 1: Basic STRING Protein Interaction Query")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Query interactions for TP53 and BRCA1
    result = tu.tools.STRING_get_protein_interactions(
        protein_ids=["TP53", "BRCA1"],
        species=9606,  # Human
        confidence_score=0.4,  # Medium confidence
        limit=10
    )
    
    if "data" in result and result["data"]:
        print(f"\n✅ Found {len(result['data'])} interactions")
        print("\nFirst 3 interactions:")
        for i, interaction in enumerate(result["data"][:3], 1):
            print(f"\n{i}. {interaction.get('preferredName_A', 'N/A')} <-> "
                  f"{interaction.get('preferredName_B', 'N/A')}")
            print(f"   Score: {interaction.get('score', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error', 'No data returned')}")


def example_2_high_confidence_string():
    """
    Example 2: High-confidence STRING interactions
    
    Query only high-confidence protein interactions (score > 0.7) for a single protein.
    Useful for finding well-validated interaction partners.
    """
    print("\n" + "="*80)
    print("Example 2: High-Confidence STRING Interactions")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Query high-confidence interactions for BRCA2
    result = tu.tools.STRING_get_protein_interactions(
        protein_ids=["BRCA2"],
        species=9606,  # Human
        confidence_score=0.7,  # High confidence
        limit=20
    )
    
    if "data" in result and result["data"]:
        print(f"\n✅ Found {len(result['data'])} high-confidence interactions for BRCA2")
        print("\nTop 5 interaction partners:")
        for i, interaction in enumerate(result["data"][:5], 1):
            partner_a = interaction.get('preferredName_A', 'N/A')
            partner_b = interaction.get('preferredName_B', 'N/A')
            score = interaction.get('score', 0)
            # Display the partner that's not BRCA2
            partner = partner_b if partner_a == 'BRCA2' else partner_a
            print(f"{i}. BRCA2 <-> {partner} (score: {score})")
    else:
        print(f"❌ Error: {result.get('error', 'No data returned')}")


def example_3_network_type_filtering():
    """
    Example 3: Filter STRING interactions by network type
    
    STRING supports different network types:
    - 'full': All interactions (physical + functional)
    - 'physical': Only physical interactions
    - 'functional': Only functional associations
    """
    print("\n" + "="*80)
    print("Example 3: Filter by Network Type")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Query only physical interactions for EGFR
    result = tu.tools.STRING_get_protein_interactions(
        protein_ids=["EGFR"],
        species=9606,
        confidence_score=0.5,
        network_type="physical",  # Only physical interactions
        limit=15
    )
    
    if "data" in result and result["data"]:
        print(f"\n✅ Found {len(result['data'])} physical interactions for EGFR")
        print("\nPhysical interaction partners:")
        for i, interaction in enumerate(result["data"][:5], 1):
            print(f"{i}. {interaction.get('preferredName_A', 'N/A')} <-> "
                  f"{interaction.get('preferredName_B', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error', 'No data returned')}")


def example_4_biogrid_interactions():
    """
    Example 4: Query BioGRID interactions
    
    BioGRID provides curated protein and genetic interactions.
    Note: Requires a BioGRID API key (free registration at https://webservice.thebiogrid.org/)
    Set BIOGRID_API_KEY environment variable or pass as parameter.
    """
    print("\n" + "="*80)
    print("Example 4: BioGRID Protein Interactions")
    print("="*80)
    
    # Check if API key is available
    api_key = os.getenv("BIOGRID_API_KEY")
    if not api_key:
        print("\n⚠️ BioGRID API key not found!")
        print("To use BioGRID tools:")
        print("1. Register at: https://webservice.thebiogrid.org/")
        print("2. Get your API key")
        print("3. Set environment variable: export BIOGRID_API_KEY='your_key'")
        print("4. Or pass api_key parameter directly")
        return
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Query interactions for TP53
    result = tu.tools.BioGRID_get_interactions(
        gene_names=["TP53"],
        organism="Homo sapiens",
        interaction_type="physical",  # Physical interactions only
        limit=10,
        api_key=api_key  # Or omit if BIOGRID_API_KEY env var is set
    )
    
    if "error" not in result:
        # BioGRID returns complex nested structure
        print("\n✅ Successfully queried BioGRID for TP53 interactions")
        print(f"Result keys: {list(result.keys())}")
        
        # Extract interaction count if available
        if isinstance(result, dict) and result:
            print(f"\nReceived interaction data from BioGRID")
    else:
        print(f"❌ Error: {result['error']}")


def example_5_cross_species_comparison():
    """
    Example 5: Cross-species protein interaction comparison
    
    Query protein interactions in different species to study conservation.
    Useful for evolutionary analysis and model organism research.
    """
    print("\n" + "="*80)
    print("Example 5: Cross-Species Interaction Comparison")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Define species to compare
    species_data = {
        "Human": 9606,
        "Mouse": 10090,
        "Fly": 7227
    }
    
    protein = "TP53"  # p53 tumor suppressor
    
    for species_name, taxon_id in species_data.items():
        result = tu.tools.STRING_get_protein_interactions(
            protein_ids=[protein],
            species=taxon_id,
            confidence_score=0.5,
            limit=5
        )
        
        if "data" in result and result["data"]:
            print(f"\n{species_name} (taxon: {taxon_id}):")
            print(f"  Found {len(result['data'])} interactions for {protein}")
        else:
            print(f"\n{species_name} (taxon: {taxon_id}): No data or error")


def example_6_pathway_reconstruction():
    """
    Example 6: Reconstruct pathway by querying multiple proteins
    
    Query interactions for multiple proteins involved in the same pathway
    to reconstruct interaction networks.
    """
    print("\n" + "="*80)
    print("Example 6: Pathway Reconstruction - DNA Repair Proteins")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # DNA repair pathway proteins
    dna_repair_proteins = ["BRCA1", "BRCA2", "RAD51", "ATM", "CHEK2"]
    
    # Query interactions for all proteins together
    result = tu.tools.STRING_get_protein_interactions(
        protein_ids=dna_repair_proteins,
        species=9606,
        confidence_score=0.6,
        limit=50
    )
    
    if "data" in result and result["data"]:
        print(f"\n✅ Found {len(result['data'])} interactions in DNA repair network")
        print("\nInteractions within pathway:")
        
        # Filter for interactions within our protein set
        pathway_interactions = []
        for interaction in result["data"]:
            protein_a = interaction.get('preferredName_A', '')
            protein_b = interaction.get('preferredName_B', '')
            if protein_a in dna_repair_proteins and protein_b in dna_repair_proteins:
                pathway_interactions.append((protein_a, protein_b, interaction.get('score', 0)))
        
        print(f"\nFound {len(pathway_interactions)} intra-pathway interactions")
        for i, (prot_a, prot_b, score) in enumerate(pathway_interactions[:10], 1):
            print(f"{i}. {prot_a} <-> {prot_b} (score: {score})")
    else:
        print(f"❌ Error: {result.get('error', 'No data returned')}")


def example_7_interaction_statistics():
    """
    Example 7: Analyze interaction network statistics
    
    Query interactions and compute basic network statistics like
    degree distribution and score distributions.
    """
    print("\n" + "="*80)
    print("Example 7: Network Statistics for Cancer Proteins")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Key cancer proteins
    cancer_proteins = ["TP53", "EGFR", "MYC", "KRAS", "PIK3CA"]
    
    result = tu.tools.STRING_get_protein_interactions(
        protein_ids=cancer_proteins,
        species=9606,
        confidence_score=0.4,
        limit=100
    )
    
    if "data" in result and result["data"]:
        interactions = result["data"]
        print(f"\n✅ Analyzed {len(interactions)} interactions")
        
        # Count interactions per protein
        protein_degree = {}
        scores = []
        
        for interaction in interactions:
            protein_a = interaction.get('preferredName_A', '')
            protein_b = interaction.get('preferredName_B', '')
            score = float(interaction.get('score', 0))
            
            protein_degree[protein_a] = protein_degree.get(protein_a, 0) + 1
            protein_degree[protein_b] = protein_degree.get(protein_b, 0) + 1
            scores.append(score)
        
        print("\nProtein degree (number of interactions):")
        for protein in sorted(protein_degree.items(), key=lambda x: x[1], reverse=True):
            if protein[0] in cancer_proteins:
                print(f"  {protein[0]}: {protein[1]} interactions")
        
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"\nAverage interaction score: {avg_score:.3f}")
            print(f"Score range: {min(scores):.3f} - {max(scores):.3f}")
    else:
        print(f"❌ Error: {result.get('error', 'No data returned')}")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("PROTEIN-PROTEIN INTERACTION (PPI) TOOLS - USAGE EXAMPLES")
    print("="*80)
    print("\nThese examples demonstrate STRING and BioGRID tools for querying")
    print("protein-protein interactions from major databases.")
    
    # Run examples
    example_1_basic_string_query()
    example_2_high_confidence_string()
    example_3_network_type_filtering()
    example_4_biogrid_interactions()
    example_5_cross_species_comparison()
    example_6_pathway_reconstruction()
    example_7_interaction_statistics()
    
    print("\n" + "="*80)
    print("All examples completed!")
    print("="*80)
    print("\n📚 Resources:")
    print("- STRING Database: https://string-db.org/")
    print("- BioGRID Database: https://thebiogrid.org/")
    print("- BioGRID API Registration: https://webservice.thebiogrid.org/")
    print("\n💡 Tips:")
    print("- Use confidence_score >= 0.7 for high-confidence interactions")
    print("- STRING includes predicted interactions, BioGRID is curated")
    print("- Set BIOGRID_API_KEY environment variable for BioGRID tools")
    print("- Combine data from both databases for comprehensive coverage")


if __name__ == "__main__":
    main()
