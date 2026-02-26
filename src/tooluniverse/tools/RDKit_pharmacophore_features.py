"""
RDKit_pharmacophore_features

Extract pharmacophore feature centers from a SMILES string using RDKit SMARTS matching. Identifie...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RDKit_pharmacophore_features(
    smiles: str,
    include_features: Optional[list[str] | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Extract pharmacophore feature centers from a SMILES string using RDKit SMARTS matching. Identifie...

    Parameters
    ----------
    smiles : str
        SMILES string of the molecule. Examples: 'CC(=O)Oc1ccccc1C(=O)O' (aspirin), '...
    include_features : list[str] | Any
        List of feature types to extract (default: all). Options: 'HBD', 'HBA', 'Arom...
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

    return get_shared_client().run_one_function(
        {
            "name": "RDKit_pharmacophore_features",
            "arguments": {"smiles": smiles, "include_features": include_features},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RDKit_pharmacophore_features"]
