"""
Molecule 2D Visualization Tool
==============================

Tool for visualizing 2D molecular structures using RDKit.
Supports SMILES, InChI, molecule names, and various output formats.
"""

import base64
import requests
import io
import warnings
from typing import Any, Dict, Optional
from .visualization_tool import VisualizationTool
from .tool_registry import register_tool


@register_tool("Molecule2DTool")
class Molecule2DTool(VisualizationTool):
    """Tool for visualizing 2D molecular structures using RDKit."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate 2D molecular structure visualization."""
        try:
            # Suppress RDKit RuntimeWarnings about converter registration
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", category=RuntimeWarning, module="importlib._bootstrap"
                )
                from rdkit import Chem
                from rdkit.Chem import Draw
                from rdkit.Chem import rdDepictor

            # Extract parameters
            smiles = arguments.get("smiles")
            inchi = arguments.get("inchi")
            molecule_name = arguments.get("molecule_name")
            width = arguments.get("width", 400)
            height = arguments.get("height", 400)
            output_format = arguments.get("output_format", "png")
            show_atom_numbers = arguments.get("show_atom_numbers", False)
            show_bond_numbers = arguments.get("show_bond_numbers", False)

            # Create molecule object
            mol = None
            input_type = ""
            input_data = ""

            if smiles:
                mol = Chem.MolFromSmiles(smiles)
                input_type = "SMILES"
                input_data = smiles
            elif inchi:
                mol = Chem.MolFromInchi(inchi)
                input_type = "InChI"
                input_data = inchi
            elif molecule_name:
                # Try to resolve molecule name to SMILES using PubChem
                smiles_resolved = self._resolve_molecule_name(molecule_name)
                if smiles_resolved:
                    mol = Chem.MolFromSmiles(smiles_resolved)
                    input_type = "Molecule Name"
                    input_data = f"{molecule_name} -> {smiles_resolved}"
                else:
                    return self.create_error_response(
                        f"Could not resolve molecule name: {molecule_name}"
                    )
            else:
                return self.create_error_response(
                    "Either smiles, inchi, or molecule_name must be provided"
                )

            if mol is None:
                return self.create_error_response(
                    "Failed to create molecule from input"
                )

            # Generate 2D coordinates
            rdDepictor.Compute2DCoords(mol)

            # Generate image
            if output_format.lower() == "svg":
                img_data = Draw.MolToSVG(mol, size=(width, height))
                static_image = base64.b64encode(img_data.encode("utf-8")).decode(
                    "utf-8"
                )
            else:
                # Generate PNG
                img = Draw.MolToImage(mol, size=(width, height))

                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                img_data = buffer.getvalue()
                static_image = self.convert_to_base64_image(img_data, "PNG")

            # Calculate molecular properties
            mol_props = self._calculate_molecular_properties(mol)

            # Create modern HTML content
            html_content = self.create_molecule_2d_html(
                static_image,
                mol_props,
                width,
                height,
                title=f"2D Molecular Structure: {input_data[:20]}{'...' if len(input_data) > 20 else ''}",
            )

            # Prepare metadata
            metadata = {
                "width": width,
                "height": height,
                "output_format": output_format,
                "input_type": input_type,
                "show_atom_numbers": show_atom_numbers,
                "show_bond_numbers": show_bond_numbers,
                "molecular_properties": mol_props,
            }

            viz_response = self.create_visualization_response(
                html_content=html_content,
                viz_type="molecule_2d",
                data={
                    "input_data": input_data,
                    "molecular_properties": mol_props,
                    "smiles": Chem.MolToSmiles(mol) if mol else None,
                },
                static_image=static_image,
                metadata=metadata,
            )
            # Wrap in data field for test compatibility
            return {"status": "success", "data": viz_response}

        except ImportError:
            error_response = self.create_error_response(
                "RDKit is not installed. Please install it with: pip install rdkit",
                "MissingDependency",
            )
            return {"status": "error", "data": error_response}
        except Exception as e:
            error_response = self.create_error_response(
                f"Failed to create molecule visualization: {str(e)}"
            )
            return {"status": "error", "data": error_response}

    def _resolve_molecule_name(self, name: str) -> Optional[str]:
        """Resolve molecule name to SMILES using PubChem."""
        try:
            # Use PubChem PUG REST API
            url = (
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
                f"{name}/property/IsomericSMILES/JSON"
            )
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "PropertyTable" in data and "Properties" in data["PropertyTable"]:
                    props = data["PropertyTable"]["Properties"]
                    if props and "IsomericSMILES" in props[0]:
                        return props[0]["IsomericSMILES"]
        except Exception:
            pass
        return None

    def _calculate_molecular_properties(self, mol) -> Dict[str, Any]:
        """Calculate basic molecular properties."""
        try:
            from rdkit import Chem
            from rdkit.Chem import rdMolDescriptors

            return {
                "molecular_weight": rdMolDescriptors.CalcExactMolWt(mol),
                "logp": rdMolDescriptors.CalcCrippenDescriptors(mol)[0],
                "hbd": rdMolDescriptors.CalcNumHBD(mol),
                "hba": rdMolDescriptors.CalcNumHBA(mol),
                "tpsa": rdMolDescriptors.CalcTPSA(mol),
                "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
                "aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(mol),
                "heavy_atoms": mol.GetNumHeavyAtoms(),
                "formal_charge": Chem.rdmolops.GetFormalCharge(mol),
            }
        except Exception:
            return {}

    def _create_molecule_html(
        self,
        mol,
        input_data: str,
        input_type: str,
        width: int,
        height: int,
        static_image: str,
        output_format: str,
    ) -> str:
        """Create HTML content for molecule visualization."""
        try:
            from rdkit import Chem

            smiles = Chem.MolToSmiles(mol)
            mol_props = self._calculate_molecular_properties(mol)

            # Create properties table
            props_html = ""
            if mol_props:
                props_html = (
                    "<table border='1' "
                    "style='border-collapse: collapse; margin: 10px 0;'>"
                )
                props_html += "<tr><th>Property</th><th>Value</th></tr>"
                for prop, value in mol_props.items():
                    if isinstance(value, float):
                        value = f"{value:.2f}"
                    props_html += f"<tr><td>{prop}</td><td>{value}</td></tr>"
                props_html += "</table>"

            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>2D Molecule Visualization</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        max-width: 1000px;
                    }}
                    .molecule-container {{
                        border: 1px solid #ccc;
                        border-radius: 5px;
                        padding: 20px;
                        margin: 10px 0;
                        text-align: center;
                    }}
                    .molecule-image {{
                        margin: 10px 0;
                    }}
                    .properties {{
                        margin: 20px 0;
                        text-align: left;
                    }}
                    .info {{
                        background-color: #f5f5f5;
                        padding: 10px;
                        border-radius: 5px;
                        margin: 10px 0;
                    }}
                </style>
            </head>
            <body>
                <h2>2D Molecular Structure Visualization</h2>

                <div class="info">
                    <h3>Input Information</h3>
                    <p><strong>Type:</strong> {input_type}</p>
                    <p><strong>Data:</strong> {input_data}</p>
                    <p><strong>SMILES:</strong> {smiles}</p>
                </div>

                <div class="molecule-container">
                    <h3>Molecular Structure</h3>
                    <div class="molecule-image">
                        <img src="data:image/{output_format.lower()};base64,{static_image}"
                             alt="2D Molecular Structure"
                             style="max-width: 100%; height: auto;" />
                    </div>
                </div>

                <div class="properties">
                    <h3>Molecular Properties</h3>
                    {props_html}
                </div>

                <div class="info">
                    <h3>Visualization Details</h3>
                    <p><strong>Dimensions:</strong> {width} × {height} "
                    "pixels</p>
                    <p><strong>Format:</strong> {output_format.upper()}</p>
                </div>
            </body>
            </html>
            """
        except Exception as e:
            return f"<div class='error'>Error creating HTML: {str(e)}</div>"
