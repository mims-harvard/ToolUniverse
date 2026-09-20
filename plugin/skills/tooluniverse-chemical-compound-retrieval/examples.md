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
props = tu.tools.PubChem_get_compound_properties_by_CID(
    cid=cid,
    properties=["MolecularFormula", "MolecularWeight", "ConnectivitySMILES"]
)
p = props["data"]["PropertyTable"]["Properties"][0]

print(f"CID: {cid}")
print(f"Formula: {p['MolecularFormula']}")
print(f"Weight: {p['MolecularWeight']}")
print(f"SMILES: {p['ConnectivitySMILES']}")
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
# Start with a known compound (similarity search takes a SMILES, not a CID)
cid = 2244  # Aspirin
smiles = tu.tools.PubChem_get_compound_properties_by_CID(
    cid=cid, properties=["ConnectivitySMILES"]
)["data"]["PropertyTable"]["Properties"][0]["ConnectivitySMILES"]

# Find similar compounds (threshold is a Tanimoto fraction 0-1; 85 is rejected with HTTP 400)
similar = tu.tools.PubChem_search_compounds_by_similarity(
    smiles=smiles,
    threshold=0.85  # 85% similarity
)
similar_cids = similar["data"]["IdentifierList"]["CID"]

print(f"Found {len(similar_cids)} similar compounds")

# Get properties of similar compounds
for sim_cid in similar_cids[:5]:
    props = tu.tools.PubChem_get_compound_properties_by_CID(
        cid=sim_cid, properties=["MolecularFormula"]
    )
    print(f"CID {sim_cid}: {props['data']['PropertyTable']['Properties'][0]['MolecularFormula']}")
```

## Example 4: Get Drug Information

```python
# Find drug
cid_result = tu.tools.PubChem_get_CID_by_compound_name(
    compound_name="ibuprofen"
)
cid = cid_result["data"]["cid"]

# Get bioactivity
bioactivity = tu.tools.PubChem_get_compound_bioactivity(
    cid=cid
)

print(f"Active in {bioactivity['data']['active_assay_count']} assays")

# Get drug label information
# FDA labels are keyed by drug name, not CID -- resolve the name first
_syn = tu.tools.PubChem_get_compound_synonyms_by_CID(cid=cid)
_name = _syn['data'][0] if isinstance(_syn, dict) and _syn.get('data') else None
drug_info = tu.tools.FDA_get_drug_label(drug_name=_name)

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
chembl_result = tu.tools.ChEMBL_search_molecules(
    query="gefitinib",
    limit=5
)

if chembl_result["data"]["molecules"]:
    chembl_id = chembl_result["data"]["molecules"][0]["molecule_chembl_id"]
    
    # Get bioactivity from ChEMBL
    activity = tu.tools.ChEMBL_search_activities(
        molecule_chembl_id=chembl_id
    )
    
    # Get targets (via the molecule's mechanisms of action; ChEMBL_get_target takes a target ID)
    targets = tu.tools.ChEMBL_get_drug_mechanisms(
        molecule_chembl_id=chembl_id
    )
    
    print(f"ChEMBL ID: {chembl_id}")
    print(f"Bioactivities: {len(activity['data']['activities'])}")
    print(f"Targets: {len(targets['data']['mechanisms'])}")
```

## Example 6: Substructure Search

```python
# Search for compounds containing benzene ring
benzene_smiles = "c1ccccc1"

result = tu.tools.PubChem_search_compounds_by_substructure(
    smiles=benzene_smiles,
    max_results=100
)

# Returns CIDs only: {data: {IdentifierList: {CID: [...]}}}
cids = result["data"]["IdentifierList"]["CID"]
print(f"Found {len(cids)} compounds with benzene ring")

# Get properties of first 10
for cid in cids[:10]:
    props = tu.tools.PubChem_get_compound_properties_by_CID(cid=cid)
    row = props["data"]["PropertyTable"]["Properties"][0]
    print(f"CID {cid}: {row['IUPACName'][:50]}...")
```

## Example 7: Drug Discovery Workflow

```python
# 1. Start with target compound
cid = tu.tools.PubChem_get_CID_by_compound_name(
    compound_name="erlotinib"
)["data"]["cid"]

# 2. Get properties (check drug-likeness)
props = tu.tools.PubChem_get_compound_properties_by_CID(
    cid=cid, properties=["MolecularWeight", "XLogP", "ConnectivitySMILES"]
)
p = props["data"]["PropertyTable"]["Properties"][0]
mw, logp, smiles = p["MolecularWeight"], p["XLogP"], p["ConnectivitySMILES"]

print(f"MW: {mw}, LogP: {logp}")

# 3. Get bioactivity
bio = tu.tools.PubChem_get_compound_bioactivity(cid=cid)
print(f"Active in {bio['data']['active_assay_count']} assays")

# 4. Find similar active compounds
# Similarity search takes a SMILES (e.g. from PubChem_get_compound_properties_by_CID) and a 0-1 threshold
similar = tu.tools.PubChem_search_compounds_by_similarity(
    smiles=smiles,
    threshold=0.80
)

print(f"Found {len(similar['data']['IdentifierList']['CID'])} similar compounds for SAR analysis")
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
