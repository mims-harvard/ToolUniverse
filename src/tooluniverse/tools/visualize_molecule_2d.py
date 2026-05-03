"""
visualize_molecule_2d

Visualize 2D molecular structures using RDKit. Supports SMILES, InChI, molecule names, and variou...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def visualize_molecule_2d(
    smiles: str,
    inchi: str,
    molecule_name: str,
    width: Optional[int] = 400,
    height: Optional[int] = 400,
    output_format: Optional[str] = "png",
    show_atom_numbers: Optional[bool] = False,
    show_bond_numbers: Optional[bool] = False,
    include_stereo: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Visualize 2D molecular structures using RDKit. Supports SMILES, InChI, molecule names, and variou...

    Parameters
    ----------
    smiles : str
        SMILES string representation of the molecule
    inchi : str
        InChI string representation of the molecule
    molecule_name : str
        Common name of the molecule (will be resolved to SMILES via PubChem)
    width : int
        Width of the visualization in pixels
    height : int
        Height of the visualization in pixels
    output_format : str
        Output format
    show_atom_numbers : bool
        Whether to show atom numbers
    show_bond_numbers : bool
        Whether to show bond numbers
    include_stereo : bool
        Whether to include stereochemistry information
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
            "inchi": inchi,
            "molecule_name": molecule_name,
            "width": width,
            "height": height,
            "output_format": output_format,
            "show_atom_numbers": show_atom_numbers,
            "show_bond_numbers": show_bond_numbers,
            "include_stereo": include_stereo,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "visualize_molecule_2d",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["visualize_molecule_2d"]
