"""
Protein Structure 3D Visualization Tool
=======================================

Tool for visualizing 3D protein structures using py3Dmol.
Supports PDB IDs, PDB file content, and various visualization styles.
"""

import requests
from typing import Any, Dict
from .visualization_tool import VisualizationTool
from .tool_registry import register_tool


@register_tool("ProteinStructure3DTool")
class ProteinStructure3DTool(VisualizationTool):
    """Tool for visualizing 3D protein structures using py3Dmol."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate 3D protein structure visualization."""
        try:
            import py3Dmol

            # Extract parameters
            pdb_id = arguments.get("pdb_id")
            pdb_content = arguments.get("pdb_content")
            style = arguments.get("style", "cartoon")
            color_scheme = arguments.get("color_scheme", "spectrum")
            width = arguments.get("width", self.default_width)
            height = arguments.get("height", self.default_height)
            show_sidechains = arguments.get("show_sidechains", False)
            show_surface = arguments.get("show_surface", False)

            # Get PDB content
            if pdb_content:
                pdb_data = pdb_content
            elif pdb_id:
                pdb_data = self._fetch_pdb_content(pdb_id)
            else:
                return self.create_error_response(
                    "Either pdb_id or pdb_content must be provided"
                )

            # Create py3Dmol viewer
            viewer = py3Dmol.view(width=width, height=height)
            viewer.addModel(pdb_data, "pdb")

            # Apply visualization style
            if style == "cartoon":
                viewer.setStyle({"cartoon": {"color": color_scheme}})
            elif style == "stick":
                viewer.setStyle({"stick": {"color": color_scheme}})
            elif style == "sphere":
                viewer.setStyle({"sphere": {"color": color_scheme}})
            elif style == "line":
                viewer.setStyle({"line": {"color": color_scheme}})
            else:
                viewer.setStyle({"cartoon": {"color": color_scheme}})

            # Add sidechains if requested
            if show_sidechains:
                resn_list = [
                    "ALA",
                    "ARG",
                    "ASN",
                    "ASP",
                    "CYS",
                    "GLN",
                    "GLU",
                    "GLY",
                    "HIS",
                    "ILE",
                    "LEU",
                    "LYS",
                    "MET",
                    "PHE",
                    "PRO",
                    "SER",
                    "THR",
                    "TRP",
                    "TYR",
                    "VAL",
                ]
                viewer.addStyle(
                    {"stick": {"radius": 0.1}}, {"and": [{"resn": resn_list}]}
                )

            # Add surface if requested
            if show_surface:
                viewer.addSurface(py3Dmol.VDW, {"opacity": 0.7, "color": "white"})

            # Zoom to fit
            viewer.zoomTo()

            # Generate HTML with modern UI
            viewer_html = viewer._make_html()

            # Create control panel
            control_panel = self._create_control_panel(style, color_scheme)

            # Create toolbar
            toolbar = self._create_toolbar()

            # Create info cards
            info_cards = self._create_protein_info_cards(pdb_id, pdb_data)

            # Generate modern HTML
            html_content = self.create_py3dmol_html(
                viewer_html,
                width,
                height,
                title=f"Protein Structure: {pdb_id or 'Custom PDB'}",
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
                "pdb_id": pdb_id,
                "show_sidechains": show_sidechains,
                "show_surface": show_surface,
            }

            viz_response = self.create_visualization_response(
                html_content=html_content,
                viz_type="protein_structure_3d",
                data={
                    "pdb_content": (
                        pdb_data[:500] + "..." if len(pdb_data) > 500 else pdb_data
                    )
                },
                metadata=metadata,
            )
            # Wrap in data field for test compatibility
            return {"status": "success", "data": viz_response}

        except ImportError:
            error_response = self.create_error_response(
                "py3Dmol is not installed. Please install it with: pip install py3Dmol",
                "MissingDependency",
            )
            return {"status": "error", "data": error_response}
        except Exception as e:
            error_response = self.create_error_response(
                f"Failed to create protein visualization: {str(e)}"
            )
            return {"status": "error", "data": error_response}

    def _fetch_pdb_content(self, pdb_id: str) -> str:
        """Fetch PDB content from RCSB PDB database."""
        try:
            url = f"https://files.rcsb.org/view/{pdb_id.upper()}.pdb"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch PDB file for {pdb_id}: {str(e)}")

    def _create_control_panel(self, current_style: str, current_color: str) -> str:
        """Create floating control panel HTML."""
        return f"""
        <div class="control-panel">
            <div class="control-group">
                <label class="control-label">Style</label>
                <select class="control-select" id="styleSelect" onchange="changeStyle()">
                    <option value="cartoon" {"selected" if current_style == "cartoon" else ""}>Cartoon</option>
                    <option value="stick" {"selected" if current_style == "stick" else ""}>Stick</option>
                    <option value="sphere" {"selected" if current_style == "sphere" else ""}>Sphere</option>
                    <option value="line" {"selected" if current_style == "line" else ""}>Line</option>
                    <option value="surface" {"selected" if current_style == "surface" else ""}>Surface</option>
                </select>
            </div>
            <div class="control-group">
                <label class="control-label">Color Scheme</label>
                <select class="control-select" id="colorSelect" onchange="changeColor()">
                    <option value="spectrum" {"selected" if current_color == "spectrum" else ""}>Spectrum</option>
                    <option value="rainbow" {"selected" if current_color == "rainbow" else ""}>Rainbow</option>
                    <option value="ss" {"selected" if current_color == "ss" else ""}>Secondary Structure</option>
                    <option value="chain" {"selected" if current_color == "chain" else ""}>Chain</option>
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

    def _create_protein_info_cards(self, pdb_id: str, pdb_data: str) -> str:
        """Create protein information cards."""
        # Parse basic PDB info
        lines = pdb_data.split("\n")
        title = "Unknown Protein"
        organism = "Unknown"
        resolution = "N/A"
        method = "Unknown"
        residue_count = 0
        atom_count = 0

        for line in lines:
            if line.startswith("TITLE"):
                title = line[10:].strip()
            elif line.startswith("SOURCE"):
                if "ORGANISM_SCIENTIFIC" in line:
                    organism = (
                        line.split("ORGANISM_SCIENTIFIC:")[1].split(";")[0].strip()
                    )
            elif line.startswith("REMARK   2 RESOLUTION"):
                resolution = line.split("RESOLUTION.")[1].split("ANGSTROMS")[0].strip()
            elif line.startswith("EXPDTA"):
                method = line[10:].strip()
            elif line.startswith("ATOM"):
                atom_count += 1
                if atom_count == 1:
                    residue_count = 1
                elif line[22:26].strip() != lines[atom_count - 2][22:26].strip():
                    residue_count += 1

        return f"""
        <div class="card">
            <h3 class="card-title">
                <svg class="card-icon" viewBox="0 0 24 24">
                    <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
                </svg>
                Protein Information
            </h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">PDB ID</span>
                    <span class="info-value">{pdb_id or "Custom"}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Title</span>
                    <span class="info-value">{title[:30]}{"..." if len(title) > 30 else ""}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Organism</span>
                    <span class="info-value">{organism[:20]}{"..." if len(organism) > 20 else ""}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Method</span>
                    <span class="info-value">{method}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Resolution</span>
                    <span class="info-value">{resolution}</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h3 class="card-title">
                <svg class="card-icon" viewBox="0 0 24 24">
                    <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/>
                </svg>
                Structure Statistics
            </h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Residues</span>
                    <span class="info-value">{residue_count}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Atoms</span>
                    <span class="info-value">{atom_count}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Chains</span>
                    <span class="info-value">1</span>
                </div>
            </div>
        </div>
        """
