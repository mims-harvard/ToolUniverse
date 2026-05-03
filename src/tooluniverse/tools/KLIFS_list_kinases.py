"""
KLIFS_list_kinases

List kinases in the Kinase-Ligand Interaction Fingerprints and Structures (KLIFS) database. KLIFS...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KLIFS_list_kinases(
    kinase_group: Optional[str | Any] = None,
    species: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List kinases in the Kinase-Ligand Interaction Fingerprints and Structures (KLIFS) database. KLIFS...

    Parameters
    ----------
    kinase_group : str | Any
        Filter by kinase group: 'TK' (tyrosine kinase), 'TKL' (TK-like), 'STE', 'CK1'...
    species : str | Any
        Filter by species: 'Human', 'Mouse', 'Rat'
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
        for k, v in {"kinase_group": kinase_group, "species": species}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KLIFS_list_kinases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KLIFS_list_kinases"]
