# Chemical Compound Retrieval Examples

## Example 1: Find Aspirin Information

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Get CID from name
cid_result = tu.tools.PubChem_get_CID_by_compound_name(
    compound_name="aspirin"
)
cid = cid_result["data"]["cid"]  # 2244

# Get properties
props = tu.tools.PubChem_get_compound_properties_by_CID(cid=cid)

print(f"CID: {cid}")
print(f"Formula: {props['data']['MolecularFormula']}")
print(f"Weight: {props['data']['MolecularWeight']}")
print(f"SMILES: {props['data']['CanonicalSMILES']}")
```

## Example 2: Search by Chemical Structure

```python
# Search by SMILES
smiles = "CC(=O)Oc1ccccc1C(=O)O"  # Aspirin

cid_result = tu.tools.PubChem_get_CID_by_SMILES(smiles=smiles)
cid = cid_result["data"]["cid"]

# Get compound details
props = tu.tools.PubChem_get_compound_properties_by_CID(cid=cid)
print(f"Found: {props['data']['IUPACName']}")
```

## Example 3: Find Similar Compounds

```python
# Start with a known compound
cid = 2244  # Aspirin

# Find similar compounds
similar = tu.tools.PubChem_search_compounds_by_similarity(
    cid=cid,
    threshold=85  # 85% similarity
)

print(f"Found {len(similar['data'])} similar compounds")

# Get properties of similar compounds
for sim_cid in similar["data"][:5]:
    props = tu.tools.PubChem_get_compound_properties_by_CID(
        cid=sim_cid
    )
    print(f"CID {sim_cid}: {props['data']['MolecularFormula']}")
```

## Example 4: Get Drug Information

```python
# Find drug
cid_result = tu.tools.PubChem_get_CID_by_compound_name(
    compound_name="ibuprofen"
)
cid = cid_result["data"]["cid"]

# Get bioactivity
bioactivity = tu.tools.PubChem_get_bioactivity_summary_by_CID(
    cid=cid
)

print(f"Active in {bioactivity['data']['active_assay_count']} assays")

# Get drug label information
drug_info = tu.tools.PubChem_get_drug_label_info_by_CID(cid=cid)

# Get patents
patents = tu.tools.PubChem_get_associated_patents_by_CID(cid=cid)
print(f"Related patents: {len(patents['data'])}")
```

## Example 5: ChEMBL Cross-Reference

```python
# Find in PubChem
cid_result = tu.tools.PubChem_get_CID_by_compound_name(
    compound_name="gefitinib"
)

# Search in ChEMBL
chembl_result = tu.tools.ChEMBL_search_compounds(
    query="gefitinib",
    limit=5
)

if chembl_result["data"]:
    chembl_id = chembl_result["data"][0]["molecule_chembl_id"]
    
    # Get bioactivity from ChEMBL
    activity = tu.tools.ChEMBL_get_bioactivity_by_chemblid(
        chembl_id=chembl_id
    )
    
    # Get targets
    targets = tu.tools.ChEMBL_get_target_by_chemblid(
        chembl_id=chembl_id
    )
    
    print(f"ChEMBL ID: {chembl_id}")
    print(f"Bioactivities: {len(activity['data'])}")
    print(f"Targets: {len(targets['data'])}")
```

## Example 6: Substructure Search

```python
# Search for compounds containing benzene ring
benzene_smiles = "c1ccccc1"

result = tu.tools.PubChem_search_compounds_by_substructure(
    smiles=benzene_smiles,
    limit=100
)

print(f"Found {len(result['data'])} compounds with benzene ring")

# Get properties of first 10
for cid in result["data"][:10]:
    props = tu.tools.PubChem_get_compound_properties_by_CID(cid=cid)
    print(f"CID {cid}: {props['data']['IUPACName'][:50]}...")
```

## Example 7: Drug Discovery Workflow

```python
# 1. Start with target compound
cid = tu.tools.PubChem_get_CID_by_compound_name(
    compound_name="erlotinib"
)["data"]["cid"]

# 2. Get properties (check drug-likeness)
props = tu.tools.PubChem_get_compound_properties_by_CID(cid=cid)
mw = props["data"]["MolecularWeight"]
logp = props["data"]["XLogP"]

print(f"MW: {mw}, LogP: {logp}")

# 3. Get bioactivity
bio = tu.tools.PubChem_get_bioactivity_summary_by_CID(cid=cid)
print(f"Active in {bio['data']['active_assay_count']} assays")

# 4. Find similar active compounds
similar = tu.tools.PubChem_search_compounds_by_similarity(
    cid=cid,
    threshold=80
)

print(f"Found {len(similar['data'])} similar compounds for SAR analysis")
```

## Example 8: Get 2D Structure Image

```python
# Get compound
cid = 2244  # Aspirin

# Get structure image
image = tu.tools.PubChem_get_compound_2D_image_by_CID(cid=cid)

print(f"Image URL: {image['data']['url']}")
# Can be displayed or saved for documentation
```
