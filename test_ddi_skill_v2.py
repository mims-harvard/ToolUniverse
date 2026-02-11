#!/usr/bin/env python3
"""
Test the Drug-Drug Interaction Prediction skill with a real clinical case.

Test Case: Polypharmacy patient taking:
- warfarin (anticoagulant)
- amoxicillin (antibiotic)
- simvastatin (statin)
- omeprazole (PPI)
- aspirin (antiplatelet)

This test follows the skill's documented workflow.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tooluniverse import ToolUniverse

def main():
    print("="*80)
    print("DDI SKILL TEST: Polypharmacy Analysis")
    print("="*80)
    print("\nTest Case: 5-drug polypharmacy regimen")
    drugs = ["warfarin", "amoxicillin", "simvastatin", "omeprazole", "aspirin"]
    print(f"Drugs: {', '.join(drugs)}")
    print("\n" + "="*80 + "\n")

    # Initialize ToolUniverse
    print("Step 1: Initializing ToolUniverse...")
    tu = ToolUniverse()
    tu.load_tools()
    print(f"✓ ToolUniverse initialized with {len(tu.all_tool_dict)} tools\n")

    # STEP 1: Drug Identification
    print("="*80)
    print("STEP 1: DRUG IDENTIFICATION")
    print("="*80)

    drug_ids = {}
    for drug in drugs:
        print(f"\n→ Looking up: {drug}")
        drug_ids[drug] = {}

        # Try DailyMed for SPL set ID
        try:
            result = tu.run_one_function(
                {"name": "DailyMed_search_spls", "arguments": {"drug_name": drug}}
            )
            if result and result.get('status') == 'success' and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and 'data' in data:
                    spls = data['data']
                    if spls and len(spls) > 0:
                        setid = spls[0].get('setid')
                        title = spls[0].get('title', 'Unknown')
                        if setid:
                            drug_ids[drug]['setid'] = setid
                            drug_ids[drug]['spl_title'] = title
                            print(f"  ✓ DailyMed SetID: {setid}")
                            print(f"    Title: {title[:80]}...")
        except Exception as e:
            print(f"  ✗ DailyMed error: {e}")

        # Try PubChem
        try:
            result = tu.run_one_function(
                {"name": "PubChem_get_CID_by_compound_name", "arguments": {"compound_name": drug}}
            )
            if result and result.get('status') == 'success':
                cid = result.get('data', {}).get('cid')
                if cid:
                    drug_ids[drug]['pubchem_cid'] = cid
                    print(f"  ✓ PubChem CID: {cid}")
        except Exception as e:
            print(f"  ✗ PubChem error: {e}")

    print("\n" + "-"*80)
    print("Drug Identification Summary:")
    identified_count = sum(1 for d in drug_ids.values() if d)
    print(f"✓ Identified {identified_count}/{len(drugs)} drugs\n")
    for drug, ids in drug_ids.items():
        if ids:
            print(f"{drug}:")
            for key, value in ids.items():
                if key == 'spl_title':
                    print(f"  {key}: {value[:60]}...")
                else:
                    print(f"  {key}: {value}")

    # STEP 2: Check Key DDI Pairs
    print("\n" + "="*80)
    print("STEP 2: CHECK HIGH-PRIORITY DDI PAIRS")
    print("="*80)

    # Focus on the most clinically important pairs
    priority_pairs = [
        ("warfarin", "amoxicillin", "Gut flora alteration → ↑warfarin effect"),
        ("warfarin", "aspirin", "Additive bleeding risk"),
        ("warfarin", "omeprazole", "CYP2C19 inhibition → ↑warfarin levels"),
    ]

    findings = []

    for drug_a, drug_b, clinical_concern in priority_pairs:
        print(f"\n→ Analyzing: {drug_a} ↔ {drug_b}")
        print(f"  Clinical concern: {clinical_concern}")

        # Check FDA label for drug_a
        if drug_a in drug_ids and 'setid' in drug_ids[drug_a]:
            try:
                print(f"  → Checking {drug_a} FDA label...")
                result = tu.run_one_function(
                    {"name": "DailyMed_parse_drug_interactions", "arguments": {"setid": drug_ids[drug_a]['setid']}}
                )
                if result and result.get('status') == 'success':
                    interactions_text = result.get('data', {}).get('drug_interactions', '')
                    if interactions_text:
                        # Check if drug_b is mentioned
                        if drug_b.lower() in interactions_text.lower():
                            print(f"  ✓ FDA label mentions {drug_b}")
                            findings.append({
                                'pair': f"{drug_a} + {drug_b}",
                                'source': 'FDA Label',
                                'evidence': f'★★★ (FDA-approved label)',
                                'details': f'{drug_b} mentioned in {drug_a} drug interactions section'
                            })
                        else:
                            # Check for drug class mentions
                            drug_classes = {
                                'amoxicillin': ['antibiotic', 'penicillin', 'beta-lactam'],
                                'aspirin': ['antiplatelet', 'NSAID', 'salicylate'],
                                'omeprazole': ['proton pump inhibitor', 'PPI'],
                                'simvastatin': ['statin', 'HMG-CoA reductase'],
                                'warfarin': ['anticoagulant', 'coumarin']
                            }
                            found_class = False
                            for drug_class in drug_classes.get(drug_b, []):
                                if drug_class.lower() in interactions_text.lower():
                                    print(f"  ✓ FDA label mentions {drug_class} (class of {drug_b})")
                                    findings.append({
                                        'pair': f"{drug_a} + {drug_b}",
                                        'source': 'FDA Label (drug class)',
                                        'evidence': f'★★★ (FDA-approved label)',
                                        'details': f'{drug_class} mentioned in {drug_a} drug interactions section'
                                    })
                                    found_class = True
                                    break
                            if not found_class:
                                print(f"  - No mention of {drug_b} in {drug_a} label")
                    else:
                        print(f"  - No drug interactions section found")
            except Exception as e:
                print(f"  ✗ Error checking FDA label: {e}")

        # Search PubMed for literature
        try:
            print(f"  → Searching PubMed...")
            result = tu.run_one_function(
                {"name": "PubMed_search_articles", "arguments": {
                    "query": f"{drug_a} {drug_b} drug interaction",
                    "max_results": 3
                }}
            )
            if result and result.get('status') == 'success':
                data = result.get('data', {})
                if isinstance(data, dict) and 'data' in data:
                    articles = data['data']
                    if articles and len(articles) > 0:
                        print(f"  ✓ Found {len(articles)} PubMed articles")
                        findings.append({
                            'pair': f"{drug_a} + {drug_b}",
                            'source': 'PubMed Literature',
                            'evidence': f'★★☆ (Clinical studies)',
                            'details': f'{len(articles)} relevant articles found'
                        })
                    else:
                        print(f"  - No PubMed articles found")
                else:
                    print(f"  - No articles in results")
        except Exception as e:
            print(f"  ✗ PubMed error: {e}")

    # STEP 3: Summary Report
    print("\n" + "="*80)
    print("STEP 3: SUMMARY REPORT")
    print("="*80)

    print(f"\nTotal interactions with evidence: {len(findings)}")
    print(f"Priority pairs analyzed: {len(priority_pairs)}")

    if findings:
        print("\n" + "-"*80)
        print("EVIDENCE FOUND:")
        print("-"*80)
        for i, finding in enumerate(findings, 1):
            print(f"\n{i}. {finding['pair']}")
            print(f"   Source: {finding['source']}")
            print(f"   Evidence: {finding['evidence']}")
            print(f"   Details: {finding['details']}")
    else:
        print("\n⚠️  No direct evidence found for priority interactions")
        print("   This may indicate:")
        print("   - Tools returned empty results")
        print("   - API rate limiting or errors")
        print("   - Drug names not matching FDA label terminology")

    # STEP 4: Tool Assessment
    print("\n" + "="*80)
    print("STEP 4: AVAILABLE DDI TOOLS")
    print("="*80)

    ddi_keywords = ['drug', 'interaction', 'admet', 'cyp', 'dailymed', 'fda', 'faers']
    ddi_tools = []

    for tool_name in tu.all_tool_dict.keys():
        for keyword in ddi_keywords:
            if keyword.lower() in tool_name.lower():
                ddi_tools.append(tool_name)
                break

    print(f"\nFound {len(ddi_tools)} potentially relevant tools")
    print("\nKey tools for DDI analysis:")
    key_tools = [t for t in ddi_tools if any(x in t.lower() for x in ['dailymed', 'admet', 'drugbank', 'faers'])]
    for tool in sorted(key_tools)[:20]:
        print(f"  - {tool}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

    # Return summary
    return {
        'drugs_identified': identified_count,
        'total_drugs': len(drugs),
        'evidence_found': len(findings),
        'priority_pairs': len(priority_pairs),
        'tools_available': len(ddi_tools)
    }

if __name__ == "__main__":
    result = main()
    print("\nFinal Summary:")
    print(f"  Drugs identified: {result['drugs_identified']}/{result['total_drugs']}")
    print(f"  Evidence found: {result['evidence_found']} interactions")
    print(f"  Tools available: {result['tools_available']}")
