
import sys
import os

# Ensure src is in python path
sys.path.append(os.path.join(os.getcwd(), "src"))

from tooluniverse.fda_pharmacogenomic_biomarkers_tool import FDAPharmacogenomicBiomarkersTool

def run_example():
    print("Running FDA Pharmacogenomic Biomarkers Tool Example...")
    
    # Initialize the tool
    config = {
        "name": "fda_pharmacogenomic_biomarkers",
        "type": "FDAPharmacogenomicBiomarkersTool"
    }
    tool = FDAPharmacogenomicBiomarkersTool(config)
    
    # Example: Search for 'Warfarin'
    print("\n1. Searching for 'Warfarin'...")
    results = tool.run({"drug_name": "Warfarin"})
    
    if "results" in results:
        count = results.get("count", 0)
        print(f"Found {count} records.")
        for item in results["results"]:
            print(f"- Drug: {item.get('Drug')}")
            print(f"  Biomarker: {item.get('Biomarker')}")
            print(f"  Section: {item.get('LabelingSection')}\n")
    else:
        print("No results found or error occurred.")

    # Example: Search for a biomarker
    print("\n2. Searching for Biomarker 'HLA-B'...")
    results_bio = tool.run({"biomarker": "HLA-B", "limit": 3})
    
    if "results" in results_bio:
        count = results_bio.get("count", 0)
        shown = results_bio.get("shown", 0)
        print(f"Found {count} records (Showing {shown}).")
        for item in results_bio["results"]:
             print(f"- Drug: {item.get('Drug')} ({item.get('TherapeuticArea')})")

if __name__ == "__main__":
    run_example()
