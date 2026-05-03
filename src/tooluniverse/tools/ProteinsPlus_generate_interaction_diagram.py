"""
ProteinsPlus_generate_interaction_diagram

Generate 2D protein-ligand interaction diagrams using PoseView. Creates publication-quality visua...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteinsPlus_generate_interaction_diagram(
    pdb_id: str,
    ligand: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Generate 2D protein-ligand interaction diagrams using PoseView. Creates publication-quality visua...

    Parameters
    ----------
    pdb_id : str
        PDB identifier (e.g., '1KZK', '2OZR', '4HHB'). Required.
    ligand : str
        Ligand identifier in format 'residue_name_residue_chain_residue_number' (e.g....
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
        k: v for k, v in {"pdb_id": pdb_id, "ligand": ligand}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProteinsPlus_generate_interaction_diagram",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteinsPlus_generate_interaction_diagram"]
