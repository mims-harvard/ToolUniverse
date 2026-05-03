#!/usr/bin/env python3
"""
Usage examples for gnomAD tools in ToolUniverse

This script demonstrates how to use the gnomAD database tools for variant search,
gene constraint analysis, and population frequency retrieval.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse


def example_get_gene_constraints():
    """Get gene constraint metrics for BRCA1"""
    print("\n🧬 Getting gene constraints for BRCA1...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "gnomad_get_gene_constraints",
        "arguments": {
            "gene_symbol": "BRCA1"
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        # The data is nested: result['data']['data']['gene']
        nested_data = data.get('data', {})
        gene = nested_data.get('gene', {})
        if gene:
            print(f"Gene Symbol: {gene.get('symbol')}")
            print(f"Gene ID: {gene.get('gene_id')}")
            
            # Check for gnomAD constraint data
            gnomad_constraint = gene.get('gnomad_constraint', {})
            if gnomad_constraint:
                print(f"gnomAD pLI: {gnomad_constraint.get('pLI')}")
                print(f"gnomAD LOEUF (oe_lof): {gnomad_constraint.get('oe_lof')}")
                print(f"gnomAD Missense O/E: {gnomad_constraint.get('oe_mis')}")
                print(f"gnomAD Synonymous O/E: {gnomad_constraint.get('oe_syn')}")
            
            # Check for ExAC constraint data
            exac_constraint = gene.get('exac_constraint', {})
            if exac_constraint:
                print(f"ExAC pLI: {exac_constraint.get('pLI')}")
                print(f"ExAC Expected LoF: {exac_constraint.get('exp_lof')}")
                print(f"ExAC Observed LoF: {exac_constraint.get('obs_lof')}")
        else:
            print("No gene constraint data found")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_gene_constraints_tp53():
    """Get gene constraint metrics for TP53"""
    print("\n🧬 Getting gene constraints for TP53...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "gnomad_get_gene_constraints",
        "arguments": {
            "gene_symbol": "TP53"
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        # The data is nested: result['data']['data']['gene']
        nested_data = data.get('data', {})
        gene = nested_data.get('gene', {})
        if gene:
            print(f"Gene Symbol: {gene.get('symbol')}")
            
            # Check for gnomAD constraint data
            gnomad_constraint = gene.get('gnomad_constraint', {})
            if gnomad_constraint:
                print(f"gnomAD pLI: {gnomad_constraint.get('pLI')}")
                print(f"gnomAD LOEUF (oe_lof): {gnomad_constraint.get('oe_lof')}")
            
            # Check for ExAC constraint data
            exac_constraint = gene.get('exac_constraint', {})
            if exac_constraint:
                print(f"ExAC pLI: {exac_constraint.get('pLI')}")
        else:
            print("No gene constraint data found")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_combined_analysis():
    """Get gene constraints for multiple genes"""
    print("\n🔗 Combined gene constraint analysis...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Get gene constraints for multiple genes
    genes = ["BRCA1", "TP53", "APOE"]
    
    for gene_symbol in genes:
        constraints_result = tu.run({
            "name": "gnomad_get_gene_constraints",
            "arguments": {
                "gene_symbol": gene_symbol
            }
        })
        
        if constraints_result.get('status') == 'success':
            data = constraints_result.get('data', {})
            # The data is nested: result['data']['data']['gene']
            nested_data = data.get('data', {})
            gene = nested_data.get('gene', {})
            if gene:
                print(f"Gene: {gene.get('symbol')}")
                
                # Check for gnomAD constraint data
                gnomad_constraint = gene.get('gnomad_constraint', {})
                if gnomad_constraint:
                    print(f"  gnomAD pLI: {gnomad_constraint.get('pLI')}")
                    print(f"  gnomAD LOEUF: {gnomad_constraint.get('oe_lof')}")
                
                # Check for ExAC constraint data
                exac_constraint = gene.get('exac_constraint', {})
                if exac_constraint:
                    print(f"  ExAC pLI: {exac_constraint.get('pLI')}")
        else:
            print(f"Error getting constraints for {gene_symbol}: {constraints_result.get('error')}")
    
    return constraints_result

def main():
    """Run all gnomAD tool examples"""
    print("🚀 gnomAD Tools Usage Examples")
    print("=" * 40)
    
    try:
        # Run examples
        example_get_gene_constraints()
        example_get_gene_constraints_tp53()
        example_combined_analysis()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
