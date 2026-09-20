# Protein Structure Retrieval Examples

## Example 1: Find Insulin Structure

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Search for insulin structures
result = tu.tools.PDBeSearch_search_structures(
    query="insulin",
    limit=50
)

print(f"Returned {len(result['data'])} structures "
      f"({result['metadata']['total_found']} entity-level matches)")

# Get first high-resolution structure (results are sorted best-resolution first)
for entry in result["data"]:
    if entry.get("resolution") and entry["resolution"] < 2.0:
        pdb_id = entry["pdb_id"]
        print(f"High-res structure: {pdb_id} ({entry['resolution']} Å)")
        break
```

## Example 2: Get Complete Structure Information

```python
pdb_id = "4INS"  # Human insulin

# Get basic metadata (RCSB GraphQL-shaped: data.entries[0])
metadata = tu.tools.get_protein_metadata_by_pdb_id(pdb_id=pdb_id)
entry = metadata["data"]["entries"][0]

print(f"Title: {entry['struct']['title']}")
print(f"Method: {entry['exptl'][0]['method']}")
print(f"Resolution: {entry['rcsb_entry_info']['resolution_combined'][0]} Å")

# Get experimental details (R-factors, space group, unit cell); keyed by lowercase PDB ID
exp = tu.tools.pdbe_get_entry_experiment(pdb_id=pdb_id)
details = exp["data"][pdb_id.lower()][0]
print(f"R-work: {details['r_work']}, space group: {details['spacegroup']}")

# Get bound ligands
ligands = tu.tools.PDBe_get_structure_ligands(pdb_id=pdb_id)

print(f"Ligands: {len(ligands['data']['ligands'])}")
for lig in ligands["data"]["ligands"]:
    print(f"  - {lig['chem_comp_name']} (chain {lig['chain_id']})")
```

## Example 3: Download Structure File

```python
pdb_id = "6LU7"  # SARS-CoV-2 main protease

# No dedicated PDB-download tool exists; fetch the file from RCSB with
# download_text_content (returns {"content", "size", "url", ...}).
pdb_file = tu.tools.download_text_content(
    url=f"https://files.rcsb.org/download/{pdb_id}.pdb"
)

print(f"PDB file size: {len(pdb_file['content'])} characters")

# Also get as mmCIF (modern format)
cif_file = tu.tools.download_text_content(
    url=f"https://files.rcsb.org/download/{pdb_id}.cif"
)

# Save to file
with open(f"{pdb_id}.pdb", "w") as f:
    f.write(pdb_file["content"])
```

## Example 4: Find Similar Structures

```python
pdb_id = "1ABC"

# Find structurally similar proteins (RCSB structure-similarity search)
similar = tu.tools.PDB_search_similar_structures(
    query=pdb_id,
    search_type="structure",
    similarity_threshold=0.7,
    max_results=5
)

results = similar["data"]["results"]
print(f"Found {similar['data']['total_found']} similar structures")

for sim in results:
    print(f"{sim['pdb_id']}: rank {sim['rank']}, score {sim['score']:.3f}")
    
    # Get metadata for each similar structure
    metadata = tu.tools.get_protein_metadata_by_pdb_id(
        pdb_id=sim["pdb_id"]
    )
    print(f"  {metadata['data']['entries'][0]['struct']['title']}")
```

## Example 5: Filter by Quality

```python
# Search for hemoglobin
result = tu.tools.PDBeSearch_search_structures(
    query="hemoglobin",
    limit=50
)

# Filter by method and resolution
high_quality = []
for entry in result["data"]:
    if "X-ray diffraction" in (entry.get("experimental_method") or []):
        if entry.get("resolution") and entry["resolution"] < 1.5:
            high_quality.append(entry)

print(f"High-quality X-ray structures: {len(high_quality)}")

for entry in high_quality[:5]:
    print(f"{entry['pdb_id']}: {entry['resolution']} Å")
```

## Example 6: Compare Experimental vs AlphaFold

```python
# Get experimental structure
pdb_id = "6LU7"
exp_metadata = tu.tools.get_protein_metadata_by_pdb_id(
    pdb_id=pdb_id
)
exp_entry = exp_metadata["data"]["entries"][0]

print(f"Experimental: {pdb_id}")
print(f"  Method: {exp_entry['exptl'][0]['method']}")
print(f"  Resolution: {exp_entry['rcsb_entry_info']['resolution_combined'][0]}")

# Get AlphaFold prediction (qualifier must be a UniProt ACCESSION)
uniprot_id = "P0DTD1"  # Same protein
af_structure = tu.tools.alphafold_get_prediction(
    qualifier=uniprot_id
)

print(f"\nAlphaFold: {uniprot_id}")
print(f"  Mean pLDDT: {af_structure['data'][0]['globalMetricValue']}")
```

## Example 7: Analyze Binding Sites

```python
pdb_id = "1ABC"

# Get ligands bound in this structure (with chain and residue number)
ligands = tu.tools.PDBe_get_structure_ligands(pdb_id=pdb_id)

for lig in ligands["data"]["ligands"]:
    print(f"{lig['chem_comp_id']} ({lig['chem_comp_name']}): "
          f"chain {lig['chain_id']}, residue {lig['author_residue_number']}")

# Protein-level binding-site residues (UniProt numbering) across ALL PDB
# entries come from PDBe-KB, keyed by UniProt accession rather than PDB ID
sites = tu.tools.PDBe_KB_get_ligand_sites(uniprot_accession="P00533")

for lig in sites["data"]["ligands"][:5]:
    residues = [r["start"] for r in lig["binding_residues"]]
    print(f"{lig['name']} ({lig['accession']}): residues {residues}")
```

## Example 8: Drug Discovery Target Analysis

```python
# Search for kinase structures
result = tu.tools.PDBeSearch_search_structures(
    query="kinase",
    limit=20
)

# Filter for structures with inhibitors
kinases_with_drugs = []

for entry in result["data"]:
    pdb_id = entry["pdb_id"]
    
    # Check for ligands
    ligands = tu.tools.PDBe_get_structure_ligands(
        pdb_id=pdb_id
    )
    ligand_list = ligands["data"]["ligands"] if ligands.get("status") == "success" else []
    
    if ligand_list:
        # Get high-resolution structures
        if entry.get("resolution") and entry["resolution"] < 2.5:
            kinases_with_drugs.append({
                "pdb_id": pdb_id,
                "resolution": entry["resolution"],
                "ligands": len(ligand_list)
            })

print(f"Found {len(kinases_with_drugs)} kinases with inhibitors")

for entry in kinases_with_drugs[:5]:
    print(f"{entry['pdb_id']}: {entry['resolution']} Å, "
          f"{entry['ligands']} ligands")
```

## Example 9: Get Multiple Formats

```python
pdb_id = "4INS"

# Get all available formats from RCSB via download_text_content
base = f"https://files.rcsb.org/download/{pdb_id}"
pdb = tu.tools.download_text_content(url=f"{base}.pdb")
cif = tu.tools.download_text_content(url=f"{base}.cif")
xml = tu.tools.download_text_content(url=f"{base}.xml")

print(f"PDB: {len(pdb['content'])} chars")
print(f"mmCIF: {len(cif['content'])} chars")
print(f"XML: {len(xml['content'])} chars")
```

## Example 10: Structure-Based Drug Design Workflow

```python
# 1. Find target protein structures
result = tu.tools.PDBeSearch_search_structures(
    query="EGFR kinase",
    limit=50
)

# 2. Filter for drug-bound, high-resolution
candidates = []
for entry in result["data"]:
    if entry.get("resolution") and entry["resolution"] < 2.0:
        ligands = tu.tools.PDBe_get_structure_ligands(
            pdb_id=entry["pdb_id"]
        )
        if ligands.get("status") == "success" and ligands["data"]["ligands"]:
            candidates.append(entry["pdb_id"])

# 3. Get structures for docking
for pdb_id in candidates[:3]:
    structure = tu.tools.download_text_content(
        url=f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    )
    
    # Get bound-ligand details
    ligands = tu.tools.PDBe_get_structure_ligands(pdb_id=pdb_id)
    
    print(f"{pdb_id}: Ready for docking")
    print(f"  Bound ligands: {len(ligands['data']['ligands'])}")
```
