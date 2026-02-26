"""
RDKit_matched_molecular_pair

Find the Matched Molecular Pair (MMP) transformation between two SMILES compounds using the Hussa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RDKit_matched_molecular_pair(
    smiles_a: str,
    smiles_b: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find the Matched Molecular Pair (MMP) transformation between two SMILES compounds using the Hussa...

    Parameters
    ----------
    smiles_a : str
        SMILES of compound A (reference/starting compound). Example: 'CC(=O)Nc1ccc(O)...
    smiles_b : str
        SMILES of compound B (analog/modified compound). Example: 'CC(=O)Nc1ccc(F)cc1...
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
            "name": "RDKit_matched_molecular_pair",
            "arguments": {"smiles_a": smiles_a, "smiles_b": smiles_b},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RDKit_matched_molecular_pair"]
