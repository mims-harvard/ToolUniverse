# Local Tools Guide: PLIP & Fpocket

This guide covers two powerful structural biology tools that require local installation. These are recommended additions to ToolUniverse for users who need protein-ligand interaction analysis and pocket detection.

---

## 🔬 PLIP - Protein-Ligand Interaction Profiler

**Version**: PLIP 2025 (latest update includes protein-protein interactions)
**Website**: https://plip-tool.biotec.tu-dresden.de/
**GitHub**: https://github.com/pharmai/plip
**Publication**: [NAR 2025](https://academic.oup.com/nar/article/53/W1/W463/8128215)

### Overview

PLIP automatically detects and visualizes non-covalent protein-ligand interactions from 3D structures. Identifies 8 interaction types:
- Hydrogen bonds
- Hydrophobic contacts
- π-stacking
- π-cation interactions
- Salt bridges
- Water bridges
- Halogen bonds
- Metal complexes

### Installation

```bash
# Via pip (recommended)
pip install plip

# Via conda
conda install -c conda-forge plip

# From source
git clone https://github.com/pharmai/plip.git
cd plip
pip install .
```

### Command-Line Usage

```bash
# Analyze PDB file
plip -f protein.pdb -o output/

# Analyze PDB ID from RCSB
plip -i 1EVE -o output/

# Specify output formats (XML, TXT, PyMOL)
plip -f protein.pdb -x -t -y -o output/

# Batch processing
plip -f complex1.pdb complex2.pdb complex3.pdb -o batch_results/
```

### Python API Example

```python
from plip.structure.preparation import PDBComplex

# Load structure
pdb_complex = PDBComplex()
pdb_complex.load_pdb('1EVE.pdb')  # or use pdb_id='1EVE' for auto-download

# Analyze all binding sites
for ligand in pdb_complex.ligands:
    pdb_complex.characterize_complex(ligand)

# Get interactions for first binding site
interactions = pdb_complex.interaction_sets[0]

# Access specific interaction types
hbonds = interactions.hbonds
hydrophobic = interactions.hydrophobic_contacts
pistacking = interactions.pistacking
saltbridges = interactions.saltbridges

# Print summary
for hbond in hbonds:
    print(f"H-bond: {hbond.restype}{hbond.resnr} - {hbond.dist_h_a:.2f}Å")
```

### Integration with ToolUniverse (Future)

**Potential tool**: `PLIP_analyze_interactions`

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Future usage (when implemented)
result = tu.tools.PLIP_analyze_interactions(
    pdb_id="1EVE",
    ligand="ZN_A_801",
    output_format="json"
)
```

### Output Formats

1. **XML**: Machine-readable, full detail
2. **TXT**: Human-readable summary
3. **PyMOL**: Session file for visualization
4. **JSON**: Structured data (via custom parsing)

### Use Cases

- **Drug Discovery**: Analyze protein-ligand binding modes
- **Structure-Activity Relationships**: Compare interactions across analogues
- **Virtual Screening Validation**: Verify predicted binding poses
- **Mutation Studies**: Understand how mutations affect binding
- **Publication Figures**: Generate interaction diagrams

### Limitations

- Requires 3D structures (PDB files)
- No web REST API (command-line or Python only)
- Large structures may be slow
- Needs proper structure preparation (hydrogens, charge states)

---

## 🎯 Fpocket - Fast Pocket Detection

**Version**: fpocket 4.x
**Website**: https://fpocket.sourceforge.net/
**GitHub**: https://github.com/Discngine/fpocket
**Web Server**: https://bioserv.rpbs.univ-paris-diderot.fr/services/fpocket/

### Overview

Fpocket is an ultra-fast pocket detection algorithm based on Voronoi tessellation and alpha-sphere theory. Identifies potential small-molecule binding sites on protein surfaces without requiring bound ligands.

### Installation

#### Linux/macOS

```bash
# Via conda (easiest)
conda install -c bioconda fpocket

# From source
git clone https://github.com/Discngine/fpocket.git
cd fpocket
make
sudo make install
```

#### Using Precompiled Binaries

Download from: https://github.com/Discngine/fpocket/releases

```bash
# Extract and add to PATH
tar -xzf fpocket-4.0.tar.gz
export PATH=$PATH:/path/to/fpocket/bin
```

### Command-Line Usage

```bash
# Basic pocket detection
fpocket -f protein.pdb

# Detect pockets with custom parameters
fpocket -f protein.pdb -m 3.0 -M 6.0 -i 35

# Specify output directory
fpocket -f protein.pdb -o output/

# Multiple structures
fpocket -f protein1.pdb protein2.pdb protein3.pdb
```

### Key Parameters

- `-m`: Minimum alpha-sphere radius (default: 3.0 Å)
- `-M`: Maximum alpha-sphere radius (default: 6.0 Å)
- `-i`: Minimum pocket atoms (default: 35)
- `-r`: Pocket clustering distance (default: 2.5 Å)
- `-D`: Calculate druggability score

### Output Files

```
protein_out/
├── protein_pockets.pqr     # All pockets (PQR format)
├── protein_pocket1.pqr     # Individual pocket 1
├── protein_pocket2.pqr     # Individual pocket 2
├── protein_info.txt        # Summary information
└── protein_pockets.json    # JSON format results
```

### Python Wrapper Example

```python
import subprocess
import json
import os

def run_fpocket(pdb_file, output_dir="fpocket_output"):
    """Run fpocket and parse results."""
    os.makedirs(output_dir, exist_ok=True)

    # Run fpocket
    cmd = ["fpocket", "-f", pdb_file, "-o", output_dir]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return {"error": result.stderr}

    # Parse output
    base_name = os.path.splitext(os.path.basename(pdb_file))[0]
    info_file = os.path.join(output_dir, f"{base_name}_out", f"{base_name}_info.txt")

    pockets = []
    if os.path.exists(info_file):
        with open(info_file, 'r') as f:
            # Parse pocket information
            for line in f:
                if line.startswith("Pocket"):
                    # Extract pocket data
                    pockets.append(parse_pocket_line(line))

    return {
        "pockets": pockets,
        "output_dir": output_dir,
        "status": "success"
    }

def parse_pocket_line(line):
    """Parse fpocket output line."""
    # Custom parsing logic
    parts = line.split()
    return {
        "pocket_id": int(parts[1]),
        "score": float(parts[3]),
        "volume": float(parts[5]),
        "residues": int(parts[7])
    }

# Usage
result = run_fpocket("1EVE.pdb")
print(f"Found {len(result['pockets'])} pockets")
for pocket in result['pockets'][:3]:
    print(f"Pocket {pocket['pocket_id']}: Score={pocket['score']:.2f}, Volume={pocket['volume']:.1f}Å³")
```

### Integration with ToolUniverse (Future)

**Potential tool**: `Fpocket_detect_pockets`

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Future usage (when implemented)
result = tu.tools.Fpocket_detect_pockets(
    pdb_id="1EVE",
    min_radius=3.0,
    max_radius=6.0,
    min_atoms=35,
    druggability=True
)
```

### Use Cases

- **Drug Target Identification**: Find potential binding sites
- **Allosteric Site Discovery**: Identify cryptic pockets
- **Structure-Based Design**: Locate druggable cavities
- **Protein Engineering**: Design binding sites
- **Virtual Screening Prep**: Define search boxes

### Comparison with Other Tools

| Tool | Speed | Accuracy | Ligand Required | Druggability |
|------|-------|----------|-----------------|--------------|
| **Fpocket** | ⚡⚡⚡ Fast | Good | ❌ No | ✅ Yes |
| DoGSiteScorer | ⚡⚡ Medium | Excellent | ❌ No | ✅ Yes |
| SiteMap | ⚡ Slow | Excellent | ❌ No | ✅ Yes |
| LigandScout | ⚡⚡ Medium | Good | ✅ Yes | ❌ No |

### Limitations

- Requires local installation (no REST API)
- Best for apo structures (without ligands)
- May miss very shallow or cryptic pockets
- Output parsing requires custom code

---

## 🚀 Integration Roadmap

### Phase 1: Current (v1.0) ✅
- ✅ SwissDock for docking (REST API)
- ✅ ProteinsPlus DoGSiteScorer for binding sites
- 📝 PLIP & Fpocket documented for local use

### Phase 2: Future (v1.1)
- 🔄 PLIP wrapper tool with command-line integration
- 🔄 Fpocket wrapper tool with result parsing
- 🔄 Integrated workflow: Fpocket → SwissDock → PLIP

### Phase 3: Advanced (v1.2+)
- 🔄 Local PLIP Python API direct integration
- 🔄 Batch processing support
- 🔄 Visualization output (PyMOL, ChimeraX)
- 🔄 Comparative analysis across multiple structures

---

## 📚 Additional Resources

### PLIP
- **Tutorial**: https://projects.volkamerlab.org/teachopencadd/talktorials/T016_protein_ligand_interactions.html
- **Documentation**: https://github.com/pharmai/plip/blob/master/DOCUMENTATION.md
- **Citation**: Schake, P., et al. (2025). PLIP 2025. Nucleic Acids Research.

### Fpocket
- **Manual**: https://fpocket.sourceforge.net/manual.html
- **Paper**: Le Guilloux, V., et al. (2009). BMC Bioinformatics.
- **Browser Version**: https://github.com/durrantlab/fpocketweb

### Related ToolUniverse Tools
- `ProteinsPlus_predict_binding_sites` - DoGSiteScorer (online)
- `ProteinsPlus_predict_binding_sites_v3` - DoGSite3 (online)
- `SwissDock_dock_ligand` - Molecular docking (online)
- `ProteinsPlus_generate_interaction_diagram` - PoseView (online)

---

## 🤝 Contributing

To add PLIP or Fpocket as full ToolUniverse tools:

1. Fork the ToolUniverse repository
2. Create tool class with command-line wrapper
3. Add JSON configuration
4. Include comprehensive tests
5. Submit pull request with documentation

See `CONTRIBUTING.md` in the ToolUniverse repo for guidelines.

---

**Last Updated**: 2026-02-08
**ToolUniverse Version**: 1.0
**Author**: ToolUniverse Development Team
