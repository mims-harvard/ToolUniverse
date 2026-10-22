"""
UniProtIDMap_to_pdb

Convert UniProt accessions to PDB IDs. All upstream pages are fetched and exposed through local l...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtIDMap_to_pdb(
    uniprot_ids: str,
    limit: Optional[int] = 500,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert UniProt accessions to PDB IDs. All upstream pages are fetched and exposed through local l...

    Parameters
    ----------
    uniprot_ids : str
        Comma-separated UniProt accession IDs. Examples: 'P04637' (TP53), 'P38398' (B...
    limit : int
        Maximum mappings to return in this local page.
    offset : int
        Zero-based mapping offset; continue with next_offset.
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
            "uniprot_ids": uniprot_ids,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniProtIDMap_to_pdb",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtIDMap_to_pdb"]
