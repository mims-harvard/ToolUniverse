"""
visualize_protein_structure_3d

Visualize 3D protein structures using py3Dmol. Supports PDB IDs, PDB file content, and various vi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def visualize_protein_structure_3d(
    pdb_id: str,
    pdb_content: str,
    style: Optional[str] = "cartoon",
    color_scheme: Optional[str] = "spectrum",
    width: Optional[int] = 800,
    height: Optional[int] = 600,
    show_sidechains: Optional[bool] = False,
    show_surface: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Visualize 3D protein structures using py3Dmol. Supports PDB IDs, PDB file content, and various vi...

    Parameters
    ----------
    pdb_id : str
        PDB identifier (e.g., '1CRN', '7CGO'). Either pdb_id or pdb_content must be p...
    pdb_content : str
        Raw PDB file content as string. Either pdb_id or pdb_content must be provided.
    style : str
        Visualization style
    color_scheme : str
        Color scheme for the structure
    width : int
        Width of the visualization in pixels
    height : int
        Height of the visualization in pixels
    show_sidechains : bool
        Whether to show sidechain atoms
    show_surface : bool
        Whether to show molecular surface
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
            "pdb_id": pdb_id,
            "pdb_content": pdb_content,
            "style": style,
            "color_scheme": color_scheme,
            "width": width,
            "height": height,
            "show_sidechains": show_sidechains,
            "show_surface": show_surface,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "visualize_protein_structure_3d",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["visualize_protein_structure_3d"]
