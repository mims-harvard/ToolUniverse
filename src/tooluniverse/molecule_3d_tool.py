"""
Molecule 3D Visualization Tool
==============================

Tool for visualizing 3D molecular structures using RDKit and py3Dmol.
Supports SMILES, MOL files, SDF content, and various visualization styles.
"""

import warnings
from typing import Any, Dict
from .visualization_tool import VisualizationTool
from .tool_registry import register_tool


@register_tool("Molecule3DTool")
class Molecule3DTool(VisualizationTool):
    """Tool for visualizing 3D molecular structures using RDKit and py3Dmol."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate 3D molecular structure visualization."""
        try:
            # Suppress RDKit RuntimeWarnings about converter registration
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", category=RuntimeWarning, module="importlib._bootstrap"
                )
                import py3Dmol
                from rdkit import Chem
                from rdkit.Chem import AllChem

            # Extract parameters
            smiles = arguments.get("smiles")
            mol_content = arguments.get("mol_content")
            sdf_content = arguments.get("sdf_content")
            style = arguments.get("style", "stick")
            color_scheme = arguments.get("color_scheme", "default")
            width = arguments.get("width", self.default_width)
            height = arguments.get("height", self.default_height)
            show_hydrogens = arguments.get("show_hydrogens", True)
            show_surface = arguments.get("show_surface", False)
            generate_conformers = arguments.get("generate_conformers", True)
            conformer_count = arguments.get("conformer_count", 1)

            # Create molecule object
            mol = None
            input_type = ""
            input_data = ""

            if smiles:
                mol = Chem.MolFromSmiles(smiles)
                input_type = "SMILES"
                input_data = smiles
            elif mol_content:
                mol = Chem.MolFromMolBlock(mol_content)
                input_type = "MOL"
                input_data = (
                    mol_content[:100] + "..." if len(mol_content) > 100 else mol_content
                )
            elif sdf_content:
                mol = Chem.MolFromMolBlock(sdf_content)
                input_type = "SDF"
                input_data = (
                    sdf_content[:100] + "..." if len(sdf_content) > 100 else sdf_content
                )
            else:
                return self.create_error_response(
                    "Either smiles, mol_content, or sdf_content must be provided"
                )

            if mol is None:
                return self.create_error_response(
                    "Failed to create molecule from input"
                )

            # Add hydrogens if requested
            if show_hydrogens:
                mol = Chem.AddHs(mol)

            # Generate 3D coordinates
            if generate_conformers:
                # Generate multiple conformers
                conformers = []
                for _ in range(conformer_count):
                    conf_mol = Chem.Mol(mol)
                    try:
                        AllChem.EmbedMolecule(conf_mol, AllChem.ETKDG())
                        AllChem.MMFFOptimizeMolecule(conf_mol)
                        conformers.append(conf_mol)
                    except Exception:
                        # Fallback to basic embedding
                        AllChem.EmbedMolecule(conf_mol)
                        conformers.append(conf_mol)
                # Use the first conformer for visualization
                mol = conformers[0] if conformers else mol
            else:
                # Generate single conformer
                try:
                    AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                    AllChem.MMFFOptimizeMolecule(mol)
                except Exception:
                    # Fallback to basic embedding
                    AllChem.EmbedMolecule(mol)

            # Convert to MOL block for py3Dmol
            mol_block = Chem.MolToMolBlock(mol)

            # Create py3Dmol viewer
            viewer = py3Dmol.view(width=width, height=height)
            viewer.addModel(mol_block, "mol")

            # Apply visualization style
            if style == "stick":
                viewer.setStyle({"stick": {"color": color_scheme}})
            elif style == "sphere":
                viewer.setStyle({"sphere": {"color": color_scheme}})
            elif style == "cartoon":
                viewer.setStyle({"cartoon": {"color": color_scheme}})
            elif style == "line":
                viewer.setStyle({"line": {"color": color_scheme}})
            elif style == "spacefill":
                viewer.setStyle({"sphere": {"scale": 0.3, "color": color_scheme}})
            else:
                viewer.setStyle({"stick": {"color": color_scheme}})

            # Add surface if requested
            if show_surface:
                viewer.addSurface(py3Dmol.VDW, {"opacity": 0.7, "color": "white"})

            # Zoom to fit
            viewer.zoomTo()

            # Calculate molecular properties first
            mol_props = self._calculate_molecular_properties(mol)

            # Generate HTML with modern UI
            viewer_html = viewer._make_html()

            # Create control panel
            control_panel = self._create_molecule_control_panel(style, color_scheme)

            # Create toolbar
            toolbar = self._create_toolbar()

            # Create info cards
            info_cards = self._create_molecule_info_cards(input_data, mol_props)

            # Generate modern HTML
            html_content = self.create_py3dmol_html(
                viewer_html,
                width,
                height,
                title=f"3D Molecular Structure: {input_data[:20]}{'...' if len(input_data) > 20 else ''}",
                control_panel=control_panel,
                toolbar=toolbar,
                info_cards=info_cards,
            )

            # Add JavaScript controls
            html_content = html_content.replace(
                "</body>", f"{self.add_3d_controls_script()}</body>"
            )

            # Prepare metadata
            metadata = {
                "width": width,
                "height": height,
                "style": style,
                "color_scheme": color_scheme,
                "input_type": input_type,
                "show_hydrogens": show_hydrogens,
                "show_surface": show_surface,
                "generate_conformers": generate_conformers,
                "conformer_count": conformer_count,
                "molecular_properties": mol_props,
            }

            viz_response = self.create_visualization_response(
                html_content=html_content,
                viz_type="molecule_3d",
                data={
                    "input_data": input_data,
                    "molecular_properties": mol_props,
                    "smiles": Chem.MolToSmiles(mol) if mol else None,
                    "conformer_count": len(conformers) if generate_conformers else 1,
                },
                metadata=metadata,
            )

            # Wrap in standard format for test framework compatibility
            return {"status": "success", "data": viz_response}

        except ImportError as e:
            missing_package = "py3Dmol" if "py3Dmol" in str(e) else "rdkit"
            error_response = self.create_error_response(
                f"{missing_package} is not installed. Please install it with: "
                f"pip install {missing_package}",
                "MissingDependency",
            )
            return {"status": "error", "data": error_response}
        except Exception as e:
            error_response = self.create_error_response(
                f"Failed to create molecule 3D visualization: {str(e)}"
            )
            return {"status": "error", "data": error_response}

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
                "num_conformers": mol.GetNumConformers(),
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
        mol_props: Dict[str, Any],
        style: str,
        color_scheme: str,
    ) -> str:
        """Create HTML content for molecule 3D visualization."""
        try:
            from rdkit import Chem

            smiles = Chem.MolToSmiles(mol) if mol else "N/A"

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
                <title>3D Molecule Visualization</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        max-width: 1200px;
                    }}
                    .molecule-container {{
                        border: 1px solid #ccc;
                        border-radius: 5px;
                        padding: 20px;
                        margin: 10px 0;
                        text-align: center;
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
                    .viewer-container {{
                        border: 1px solid #ccc;
                        border-radius: 5px;
                        margin: 10px 0;
                    }}
                </style>
            </head>
            <body>
                <h2>3D Molecular Structure Visualization</h2>

                <div class="info">
                    <h3>Input Information</h3>
                    <p><strong>Type:</strong> {input_type}</p>
                    <p><strong>Data:</strong> {input_data}</p>
                    <p><strong>SMILES:</strong> {smiles}</p>
                </div>

                <div class="molecule-container">
                    <h3>3D Molecular Structure</h3>
                    <div class="viewer-container">
                        <!-- 3D viewer will be embedded here -->
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
                    <p><strong>Style:</strong> {style}</p>
                    <p><strong>Color Scheme:</strong> {color_scheme}</p>
                </div>
            </body>
            </html>
            """
        except Exception as e:
            return f"<div class='error'>Error creating HTML: {str(e)}</div>"

    def _create_molecule_control_panel(
        self, current_style: str, current_color: str
    ) -> str:
        """Create floating control panel HTML for molecules."""
        return f"""
        <div class="control-panel">
            <div class="control-group">
                <label class="control-label">Style</label>
                <select class="control-select" id="styleSelect" onchange="changeStyle()">
                    <option value="stick" {"selected" if current_style == "stick" else ""}>Stick</option>
                    <option value="sphere" {"selected" if current_style == "sphere" else ""}>Sphere</option>
                    <option value="cartoon" {"selected" if current_style == "cartoon" else ""}>Cartoon</option>
                    <option value="line" {"selected" if current_style == "line" else ""}>Line</option>
                    <option value="spacefill" {"selected" if current_style == "spacefill" else ""}>Spacefill</option>
                </select>
            </div>
            <div class="control-group">
                <label class="control-label">Color Scheme</label>
                <select class="control-select" id="colorSelect" onchange="changeColor()">
                    <option value="default" {"selected" if current_color == "default" else ""}>Default</option>
                    <option value="spectrum" {"selected" if current_color == "spectrum" else ""}>Spectrum</option>
                    <option value="rainbow" {"selected" if current_color == "rainbow" else ""}>Rainbow</option>
                    <option value="elem" {"selected" if current_color == "elem" else ""}>Element</option>
                </select>
            </div>
            <div class="control-group">
                <label class="control-label">Background</label>
                <select class="control-select" id="bgSelect" onchange="changeBackground()">
                    <option value="white" selected>White</option>
                    <option value="black">Black</option>
                    <option value="gray">Gray</option>
                </select>
            </div>
        </div>
        """

    def _create_toolbar(self) -> str:
        """Create bottom toolbar HTML."""
        return """
        <div class="toolbar">
            <button class="btn" onclick="resetView()">Reset View</button>
            <button class="btn btn-secondary" onclick="downloadScreenshot()">Screenshot</button>
            <button class="btn btn-outline" onclick="toggleFullscreen()">Fullscreen</button>
        </div>
        """

    def _create_molecule_info_cards(
        self, input_data: str, mol_props: Dict[str, Any]
    ) -> str:
        """Create molecule information cards."""
        smiles = mol_props.get("smiles", "N/A")
        mol_weight = mol_props.get("molecular_weight", 0)
        logp = mol_props.get("logp", 0)
        hbd = mol_props.get("hbd", 0)
        hba = mol_props.get("hba", 0)
        tpsa = mol_props.get("tpsa", 0)
        rotatable_bonds = mol_props.get("rotatable_bonds", 0)
        aromatic_rings = mol_props.get("aromatic_rings", 0)
        heavy_atoms = mol_props.get("heavy_atoms", 0)
        formal_charge = mol_props.get("formal_charge", 0)

        return f"""
        <div class="card">
            <h3 class="card-title">
                <svg class="card-icon" viewBox="0 0 24 24">
                    <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
                </svg>
                Molecule Information
            </h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">SMILES</span>
                    <span class="info-value">{smiles[:30]}{"..." if len(smiles) > 30 else ""}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Molecular Weight</span>
                    <span class="info-value">{mol_weight:.2f} Da</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Heavy Atoms</span>
                    <span class="info-value">{heavy_atoms}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Formal Charge</span>
                    <span class="info-value">{formal_charge}</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h3 class="card-title">
                <svg class="card-icon" viewBox="0 0 24 24">
                    <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
                </svg>
                Drug Properties
            </h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">LogP</span>
                    <span class="info-value">{logp:.2f}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">TPSA</span>
                    <span class="info-value">{tpsa:.2f} Å²</span>
                </div>
                <div class="info-item">
                    <span class="info-label">H-Bond Donors</span>
                    <span class="info-value">{hbd}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">H-Bond Acceptors</span>
                    <span class="info-value">{hba}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Rotatable Bonds</span>
                    <span class="info-value">{rotatable_bonds}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Aromatic Rings</span>
                    <span class="info-value">{aromatic_rings}</span>
                </div>
            </div>
        </div>
        """
