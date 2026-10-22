"""
AlphaFill_get_transplants

Get ligands, cofactors, and ions transplanted into an AlphaFold model by AlphaFill. Source PDB ID...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AlphaFill_get_transplants(
    uniprot: str,
    source_pdb_offset: Optional[int] = 0,
    source_pdb_limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get ligands, cofactors, and ions transplanted into an AlphaFold model by AlphaFill. Source PDB ID...

    Parameters
    ----------
    uniprot : str
        UniProt accession, e.g. 'P00520' (ABL1), 'P00533' (EGFR), 'P24941' (CDK2).
    source_pdb_offset : int
        Zero-based source-PDB offset applied within every compound.
    source_pdb_limit : int
        Source PDB IDs returned per compound (default 10, maximum 500).
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
            "uniprot": uniprot,
            "source_pdb_offset": source_pdb_offset,
            "source_pdb_limit": source_pdb_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AlphaFill_get_transplants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AlphaFill_get_transplants"]
