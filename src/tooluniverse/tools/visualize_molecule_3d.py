"""
visualize_molecule_3d

Visualize 3D molecular structures using RDKit and py3Dmol. Supports SMILES, MOL files, SDF conten...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def visualize_molecule_3d(
    smiles: Optional[str] = None,
    mol_content: Optional[str] = None,
    sdf_content: Optional[str] = None,
    style: Optional[str] = "stick",
    color_scheme: Optional[str] = "default",
    width: Optional[int] = 800,
    height: Optional[int] = 600,
    show_hydrogens: Optional[bool] = True,
    show_surface: Optional[bool] = False,
    generate_conformers: Optional[bool] = True,
    conformer_count: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Visualize 3D molecular structures using RDKit and py3Dmol. Supports SMILES, MOL files, SDF conten...

    Parameters
    ----------
    smiles : str
        SMILES string representation of the molecule
    mol_content : str
        MOL file content as string
    sdf_content : str
        SDF file content as string
    style : str
        Visualization style
    color_scheme : str
        Color scheme for the molecule
    width : int
        Width of the visualization in pixels
    height : int
        Height of the visualization in pixels
    show_hydrogens : bool
        Whether to show hydrogen atoms
    show_surface : bool
        Whether to show molecular surface
    generate_conformers : bool
        Whether to generate multiple conformers
    conformer_count : int
        Number of conformers to generate
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "smiles": smiles,
            "mol_content": mol_content,
            "sdf_content": sdf_content,
            "style": style,
            "color_scheme": color_scheme,
            "width": width,
            "height": height,
            "show_hydrogens": show_hydrogens,
            "show_surface": show_surface,
            "generate_conformers": generate_conformers,
            "conformer_count": conformer_count,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "visualize_molecule_3d",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["visualize_molecule_3d"]
