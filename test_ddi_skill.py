#!/usr/bin/env python3
"""
Test the Drug-Drug Interaction Prediction skill with a real clinical case.

Test Case: Polypharmacy patient taking:
- warfarin (anticoagulant)
- amoxicillin (antibiotic)
- simvastatin (statin)
- omeprazole (PPI)
- aspirin (antiplatelet)
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
    print("Drugs: warfarin, amoxicillin, simvastatin, omeprazole, aspirin")
    print("\n" + "="*80 + "\n")

    # Initialize ToolUniverse
    print("Step 1: Initializing ToolUniverse...")
    tu = ToolUniverse()
    tu.load_tools()
    print(f"✓ ToolUniverse initialized with {len(tu.all_tool_dict)} tools")

    # Define drug list
    drugs = ["warfarin", "amoxicillin", "simvastatin", "omeprazole", "aspirin"]
    print(f"\n✓ Analyzing {len(drugs)} drugs: {', '.join(drugs)}")

    # Step 1: Drug Identification
    print("\n" + "="*80)
    print("STEP 1: DRUG IDENTIFICATION")
    print("="*80)

    drug_ids = {}
    for drug in drugs:
        print(f"\n→ Looking up: {drug}")

        # Try RxNorm first
        try:
            result = tu.run_one_function(
                {"name": "RxNorm_get_drugs_by_name", "arguments": {"name": drug}}
            )
            if result and 'data' in result:
                rxcui = result['data'].get('rxcui') or result['data'].get('results', [{}])[0].get('rxcui')
                if rxcui:
                    drug_ids[drug] = {'rxcui': rxcui, 'source': 'RxNorm'}
                    print(f"  ✓ RxCUI: {rxcui}")
                else:
                    print(f"  ✗ RxNorm: No RxCUI found")
                    print(f"  Response: {result}")
            else:
                print(f"  ✗ RxNorm failed: {result}")
        except Exception as e:
            print(f"  ✗ RxNorm error: {e}")

        # Try DailyMed
        try:
            result = tu.run_one_function(
                {"name": "DailyMed_search_spls", "arguments": {"drug_name": drug}}
            )
            if result and 'data' in result:
                data = result['data']
                if isinstance(data, dict) and 'data' in data:
                    spls = data['data']
                    if spls and len(spls) > 0:
                        setid = spls[0].get('setid')
                        if setid:
                            if drug not in drug_ids:
                                drug_ids[drug] = {}
                            drug_ids[drug]['setid'] = setid
                            drug_ids[drug]['dailymed_source'] = 'DailyMed'
                            print(f"  ✓ DailyMed SetID: {setid}")
                        else:
                            print(f"  ✗ DailyMed: No SetID in results")
                    else:
                        print(f"  ✗ DailyMed: Empty results")
                else:
                    print(f"  ✗ DailyMed: Unexpected format: {data}")
            else:
                print(f"  ✗ DailyMed failed: {result}")
        except Exception as e:
            print(f"  ✗ DailyMed error: {e}")

        # Try PubChem
        try:
            result = tu.run_one_function(
                {"name": "PubChem_get_CID_by_compound_name", "arguments": {"compound_name": drug}}
            )
            if result and 'data' in result:
                cid = result['data'].get('cid')
                if cid:
                    if drug not in drug_ids:
                        drug_ids[drug] = {}
                    drug_ids[drug]['pubchem_cid'] = cid
                    print(f"  ✓ PubChem CID: {cid}")
                else:
                    print(f"  ✗ PubChem: No CID found")
            else:
                print(f"  ✗ PubChem failed: {result}")
        except Exception as e:
            print(f"  ✗ PubChem error: {e}")

    print("\n" + "-"*80)
    print("Drug Identification Summary:")
    for drug, ids in drug_ids.items():
        print(f"\n{drug}:")
        for key, value in ids.items():
            print(f"  {key}: {value}")

    # Step 2: Pairwise DDI Analysis
    print("\n" + "="*80)
    print("STEP 2: PAIRWISE DDI ANALYSIS")
    print("="*80)
    print(f"\nTotal pairs to analyze: {len(drugs) * (len(drugs) - 1) // 2}")

    interactions = {}
    pair_count = 0

    for i, drug_a in enumerate(drugs):
        for drug_b in drugs[i+1:]:
            pair_count += 1
            print(f"\n[{pair_count}] Analyzing: {drug_a} ↔ {drug_b}")
            print("-" * 60)

            interactions[f"{drug_a}_{drug_b}"] = {
                'drug_a': drug_a,
                'drug_b': drug_b,
                'mechanisms': [],
                'evidence': []
            }

            # Check FDA label warnings (DailyMed)
            if drug_a in drug_ids and 'setid' in drug_ids[drug_a]:
                try:
                    print(f"  → Checking FDA label for {drug_a}...")
                    result = tu.run_one_function(
                        {"name": "DailyMed_get_spl_sections_by_setid", "arguments": {"setid": drug_ids[drug_a]['setid']}}
                    )
                    if result and 'data' in result:
                        data = result['data']
                        if isinstance(data, dict):
                            # Check for drug interactions section
                            drug_int = data.get('drug_interactions', '') or data.get('drug_and_or_laboratory_test_interactions', '')
                            if drug_int and drug_b.lower() in drug_int.lower():
                                print(f"  ✓ FDA label mentions {drug_b}")
                                interactions[f"{drug_a}_{drug_b}"]['evidence'].append({
                                    'source': 'FDA_label',
                                    'grade': '★★★',
                                    'details': f'Interaction mentioned in {drug_a} label'
                                })
                            else:
                                print(f"  - No mention of {drug_b} in {drug_a} label")
                        else:
                            print(f"  ✗ Unexpected format: {type(data)}")
                    else:
                        print(f"  ✗ Failed to retrieve label")
                except Exception as e:
                    print(f"  ✗ Error checking FDA label: {e}")

            # Search PubMed for clinical evidence
            try:
                print(f"  → Searching PubMed for '{drug_a} {drug_b} interaction'...")
                result = tu.run_one_function(
                    {"name": "PubMed_search_articles", "arguments": {
                        "query": f"{drug_a} {drug_b} drug interaction",
                        "max_results": 5
                    }}
                )
                if result and 'data' in result:
                    data = result['data']
                    if isinstance(data, dict) and 'data' in data:
                        articles = data['data']
                        if articles and len(articles) > 0:
                            print(f"  ✓ Found {len(articles)} PubMed articles")
                            interactions[f"{drug_a}_{drug_b}"]['evidence'].append({
                                'source': 'PubMed',
                                'count': len(articles),
                                'grade': '★★☆'
                            })
                        else:
                            print(f"  - No PubMed articles found")
                    else:
                        print(f"  - No articles in results")
                else:
                    print(f"  ✗ PubMed search failed")
            except Exception as e:
                print(f"  ✗ PubMed error: {e}")

    # Step 3: Generate Summary Report
    print("\n" + "="*80)
    print("STEP 3: SUMMARY REPORT")
    print("="*80)

    print(f"\nTotal interactions analyzed: {len(interactions)}")

    evidence_found = 0
    for pair_key, data in interactions.items():
        if data['evidence']:
            evidence_found += 1
            print(f"\n{data['drug_a']} ↔ {data['drug_b']}:")
            for ev in data['evidence']:
                print(f"  - {ev['source']}: {ev.get('grade', 'N/A')}")

    print(f"\n✓ Pairs with evidence: {evidence_found}/{len(interactions)}")
    print(f"✓ Pairs without evidence: {len(interactions) - evidence_found}/{len(interactions)}")

    # Check available DDI-related tools
    print("\n" + "="*80)
    print("AVAILABLE DDI TOOLS IN TOOLUNIVERSE")
    print("="*80)

    ddi_keywords = ['interaction', 'cyp', 'drug', 'admet', 'fda', 'dailymed', 'rxnorm', 'faers']
    ddi_tools = []

    for tool_name in tu.all_tool_dict.keys():
        for keyword in ddi_keywords:
            if keyword.lower() in tool_name.lower():
                ddi_tools.append(tool_name)
                break

    print(f"\nFound {len(ddi_tools)} potentially relevant tools:")
    for tool in sorted(ddi_tools):
        print(f"  - {tool}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
