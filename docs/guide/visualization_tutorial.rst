Scientific Visualization Tools
==============================

ToolUniverse provides simple and powerful visualization tools for proteins and molecules. Generate beautiful interactive HTML visualizations with just a few lines of code.

Quick Start
-----------

.. code-block:: python

    from tooluniverse import ToolUniverse

    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Visualize a protein
    result = tu.run({
        "name": "visualize_protein_structure_3d",
        "arguments": {"pdb_id": "1CRN"}
    })

    # Save the visualization
    with open("protein.html", "w") as f:
        f.write(result["visualization"]["html"])

Installation
------------

Install with visualization dependencies:

.. code-block:: bash

    pip install tooluniverse[visualization]

Available Tools
---------------

1. Protein 3D Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Tool:** ``visualize_protein_structure_3d``

Visualize 3D protein structures from PDB database.

**Basic Usage:**

.. code-block:: python

    result = tu.run({
        "name": "visualize_protein_structure_3d",
        "arguments": {"pdb_id": "1CRN"}
    })

**Options:**
- ``pdb_id``: PDB ID (e.g., "1CRN", "7CGO")
- ``style``: "cartoon", "stick", "sphere", "line" (default: "cartoon")
- ``color_scheme``: "spectrum", "rainbow", "ssPyMOL" (default: "spectrum")
- ``width``: Width in pixels (default: 800)
- ``height``: Height in pixels (default: 600)

2. Molecule 2D Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Tool:** ``visualize_molecule_2d``

Generate 2D molecular structure images.

**Basic Usage:**

.. code-block:: python

    result = tu.run({
        "name": "visualize_molecule_2d",
        "arguments": {"smiles": "CCO"}
    })

**Options:**
- ``smiles``: SMILES string (e.g., "CCO" for ethanol)
- ``molecule_name``: Common name (e.g., "aspirin", "caffeine")
- ``width``: Width in pixels (default: 400)
- ``height``: Height in pixels (default: 400)
- ``output_format``: "png" or "svg" (default: "png")

3. Molecule 3D Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Tool:** ``visualize_molecule_3d``

Create interactive 3D molecular structures.

**Basic Usage:**

.. code-block:: python

    result = tu.run({
        "name": "visualize_molecule_3d",
        "arguments": {"smiles": "CCO"}
    })

**Options:**
- ``smiles``: SMILES string
- ``style``: "stick", "sphere", "cartoon", "line", "spacefill" (default: "stick")
- ``color_scheme``: "default", "spectrum", "rainbow" (default: "default")
- ``width``: Width in pixels (default: 800)
- ``height``: Height in pixels (default: 600)

Output Format
-------------

All tools return the same format:

.. code-block:: python

    {
        "success": True,
        "visualization": {
            "html": "<html>...</html>",  # Interactive HTML
            "type": "protein_structure_3d",
            "data": {...},  # Input data
            "metadata": {...}  # Additional info
        }
    }

Examples
--------

Run the examples:

.. code-block:: bash

    # Quick examples
    python examples/visualization_quickstart.py

    # More examples
    python examples/visualization_examples.py

Common Examples
~~~~~~~~~~~~~~~

**Visualize different proteins:**

.. code-block:: python

    proteins = ["1CRN", "7CGO", "1HTM"]
    for pdb_id in proteins:
        result = tu.run({
            "name": "visualize_protein_structure_3d",
            "arguments": {"pdb_id": pdb_id}
        })
        with open(f"{pdb_id}.html", "w") as f:
            f.write(result["visualization"]["html"])

**Visualize different molecules:**

.. code-block:: python

    molecules = ["CCO", "CC(=O)O", "c1ccccc1"]  # ethanol, acetic acid, benzene
    for smiles in molecules:
        result = tu.run({
            "name": "visualize_molecule_2d",
            "arguments": {"smiles": smiles}
        })
        with open(f"{smiles}.html", "w") as f:
            f.write(result["visualization"]["html"])

Troubleshooting
---------------

**Common Issues:**

1. **Missing dependencies:**
   .. code-block:: bash

       pip install py3Dmol rdkit

2. **Invalid SMILES:**
   - Check SMILES syntax
   - Use valid chemical notation

3. **PDB ID not found:**
   - Verify PDB ID exists at https://www.rcsb.org/
   - Check spelling

**Performance Tips:**
- Use smaller dimensions for large molecules
- Disable surface rendering for better performance

Resources
---------

- `PDB Database <https://www.rcsb.org/>`_
- `PubChem Database <https://pubchem.ncbi.nlm.nih.gov/>`_
- `RDKit Documentation <https://www.rdkit.org/docs/>`_