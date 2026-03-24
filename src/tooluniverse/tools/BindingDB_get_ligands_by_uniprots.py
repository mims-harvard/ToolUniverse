"""
BindingDB_get_ligands_by_uniprots

Get binding affinity data for multiple proteins by UniProt IDs. Returns SMILES and affinities for...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BindingDB_get_ligands_by_uniprots(
    uniprot_ids: str,
    affinity_cutoff: Optional[int] = 10000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get binding affinity data for multiple proteins by UniProt IDs. Returns SMILES and affinities for...

    Parameters
    ----------
    affinity_cutoff : int
        Maximum affinity in nM (default: 10000)
    uniprot_ids : str
        Comma-separated UniProt IDs (e.g., P00176,P00183)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "affinity_cutoff": affinity_cutoff,
            "uniprot_ids": uniprot_ids,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BindingDB_get_ligands_by_uniprots",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BindingDB_get_ligands_by_uniprots"]
