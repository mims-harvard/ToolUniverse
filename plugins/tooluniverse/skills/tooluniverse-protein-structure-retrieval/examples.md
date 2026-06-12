# Protein Structure Retrieval Examples

## Example 1: Find Insulin Structure

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Search for insulin structures
result = tu.tools.search_structures_by_protein_name(
    protein_name="insulin"
)

print(f"Found {len(result['data'])} insulin structures")

# Get first high-resolution structure
for entry in result["data"]:
    if entry.get("resolution") and entry["resolution"] < 2.0:
        pdb_id = entry["pdb_id"]
        print(f"High-res structure: {pdb_id} ({entry['resolution']} Å)")
        break
```

## Example 2: Get Complete Structure Information

```python
pdb_id = "4INS"  # Human insulin

# Get basic metadata
metadata = tu.tools.get_protein_metadata_by_pdb_id(pdb_id=pdb_id)

print(f"Title: {metadata['data']['title']}")
print(f"Method: {metadata['data']['experimental_method']}")
print(f"Resolution: {metadata['data']['resolution']} Å")

# Get experimental details
exp = tu.tools.get_protein_experimental_details_by_pdb_id(
    pdb_id=pdb_id
)

# Get bound ligands
ligands = tu.tools.get_protein_ligands_by_pdb_id(pdb_id=pdb_id)

print(f"Ligands: {len(ligands['data'])}")
for lig in ligands["data"]:
    print(f"  - {lig['name']}")
```

## Example 3: Download Structure File

```python
pdb_id = "6LU7"  # SARS-CoV-2 main protease

# Download in PDB format
pdb_file = tu.tools.download_pdb_structure_file(
    pdb_id=pdb_id,
    format="pdb"
)

print(f"PDB file size: {len(pdb_file['data'])} characters")

# Also get as mmCIF (modern format)
cif_file = tu.tools.download_pdb_structure_file(
    pdb_id=pdb_id,
    format="cif"
)

# Save to file
with open(f"{pdb_id}.pdb", "w") as f:
    f.write(pdb_file["data"])
```

## Example 4: Find Similar Structures

```python
pdb_id = "1ABC"

# Find structurally similar proteins
similar = tu.tools.get_similar_structures_by_pdb_id(
    pdb_id=pdb_id,
    cutoff=2.0  # RMSD cutoff in Angstroms
)

print(f"Found {len(similar['data'])} similar structures")

for sim in similar["data"][:5]:
    print(f"{sim['pdb_id']}: RMSD {sim['rmsd']} Å")
    
    # Get metadata for each similar structure
    metadata = tu.tools.get_protein_metadata_by_pdb_id(
        pdb_id=sim["pdb_id"]
    )
    print(f"  {metadata['data']['title']}")
```

## Example 5: Filter by Quality

```python
# Search for hemoglobin
result = tu.tools.search_structures_by_protein_name(
    protein_name="hemoglobin"
)

# Filter by method and resolution
high_quality = []
for entry in result["data"]:
    if entry.get("method") == "X-ray":
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

print(f"Experimental: {pdb_id}")
print(f"  Method: {exp_metadata['data']['experimental_method']}")
print(f"  Resolution: {exp_metadata['data']['resolution']}")

# Get AlphaFold prediction
uniprot_id = "P0DTD1"  # Same protein
af_structure = tu.tools.alphafold_get_structure_by_uniprot(
    uniprot_id=uniprot_id
)

print(f"\nAlphaFold: {uniprot_id}")
print(f"  Confidence: {af_structure['data']['confidence_score']}")
```

## Example 7: Analyze Binding Sites

```python
pdb_id = "1ABC"

# Get ligands
ligands = tu.tools.get_protein_ligands_by_pdb_id(pdb_id=pdb_id)

# Get binding site information from PDBe
sites = tu.tools.pdbe_get_binding_sites(pdb_id=pdb_id)

print(f"Binding sites: {len(sites['data'])}")

for site in sites["data"]:
    print(f"Site {site['site_id']}:")
    print(f"  Residues: {site['residues']}")
    print(f"  Ligand: {site['ligand']}")
```

## Example 8: Drug Discovery Target Analysis

```python
# Search for kinase structures
result = tu.tools.search_structures_by_protein_name(
    protein_name="kinase"
)

# Filter for structures with inhibitors
kinases_with_drugs = []

for entry in result["data"][:20]:
    pdb_id = entry["pdb_id"]
    
    # Check for ligands
    ligands = tu.tools.get_protein_ligands_by_pdb_id(
        pdb_id=pdb_id
    )
    
    if ligands["data"]:
        # Get high-resolution structures
        if entry.get("resolution") and entry["resolution"] < 2.5:
            kinases_with_drugs.append({
                "pdb_id": pdb_id,
                "resolution": entry["resolution"],
                "ligands": len(ligands["data"])
            })

print(f"Found {len(kinases_with_drugs)} kinases with inhibitors")

for entry in kinases_with_drugs[:5]:
    print(f"{entry['pdb_id']}: {entry['resolution']} Å, "
          f"{entry['ligands']} ligands")
```

## Example 9: Get Multiple Formats

```python
pdb_id = "4INS"

# Get all available formats
pdb = tu.tools.download_pdb_structure_file(
    pdb_id=pdb_id,
    format="pdb"
)

cif = tu.tools.download_pdb_structure_file(
    pdb_id=pdb_id,
    format="cif"
)

xml = tu.tools.download_pdb_structure_file(
    pdb_id=pdb_id,
    format="xml"
)

print(f"PDB: {len(pdb['data'])} chars")
print(f"mmCIF: {len(cif['data'])} chars")
print(f"XML: {len(xml['data'])} chars")
```

## Example 10: Structure-Based Drug Design Workflow

```python
# 1. Find target protein structures
result = tu.tools.search_structures_by_protein_name(
    protein_name="EGFR kinase"
)

# 2. Filter for drug-bound, high-resolution
candidates = []
for entry in result["data"]:
    if entry.get("resolution") and entry["resolution"] < 2.0:
        ligands = tu.tools.get_protein_ligands_by_pdb_id(
            pdb_id=entry["pdb_id"]
        )
        if ligands["data"]:
            candidates.append(entry["pdb_id"])

# 3. Get structures for docking
for pdb_id in candidates[:3]:
    structure = tu.tools.download_pdb_structure_file(
        pdb_id=pdb_id,
        format="pdb"
    )
    
    # Get binding site details
    sites = tu.tools.pdbe_get_binding_sites(pdb_id=pdb_id)
    
    print(f"{pdb_id}: Ready for docking")
    print(f"  Binding sites: {len(sites['data'])}")
```
