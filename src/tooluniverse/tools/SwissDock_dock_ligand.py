"""
SwissDock_dock_ligand

Perform protein-ligand molecular docking using SwissDock service with AutoDock Vina or Attracting...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissDock_dock_ligand(
    ligand_smiles: str,
    pdb_id: str,
    exhaustiveness: Optional[int] = 8,
    box_center: Optional[str] = None,
    box_size: Optional[str] = None,
    docking_engine: Optional[str] = "attracting_cavities",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform protein-ligand molecular docking using SwissDock service with AutoDock Vina or Attracting...

    Parameters
    ----------
    ligand_smiles : str
        SMILES string of the ligand/small molecule to dock. Example: 'CC(=O)Oc1ccccc1...
    pdb_id : str
        4-character PDB ID of the target protein structure. Example: '1ATP' for prote...
    exhaustiveness : int
        Search exhaustiveness (1-20). Higher values increase accuracy but take longer...
    box_center : str
        Binding site center coordinates as 'x,y,z' in Angstroms. If not provided, per...
    box_size : str
        Search box dimensions as 'a,b,c' in Angstroms. If not provided, uses default ...
    docking_engine : str
        Docking engine: 'attracting_cavities' (cavity-based, default, recommended for...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "ligand_smiles": ligand_smiles,
            "pdb_id": pdb_id,
            "exhaustiveness": exhaustiveness,
            "box_center": box_center,
            "box_size": box_size,
            "docking_engine": docking_engine,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SwissDock_dock_ligand",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissDock_dock_ligand"]
