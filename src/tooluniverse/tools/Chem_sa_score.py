"""
Chem_sa_score

Compute the synthetic accessibility (SA) score for a molecule supplied as a SMILES string, using ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Chem_sa_score(
    operation: str,
    smiles: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compute the synthetic accessibility (SA) score for a molecule supplied as a SMILES string, using ...

    Parameters
    ----------
    operation : str
        Operation type
    smiles : str
        SMILES string of the molecule (e.g., 'CC(=O)Oc1ccccc1C(=O)O' for aspirin)
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
        for k, v in {"operation": operation, "smiles": smiles}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Chem_sa_score",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Chem_sa_score"]
