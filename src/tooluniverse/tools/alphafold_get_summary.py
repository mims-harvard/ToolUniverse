"""
alphafold_get_summary

Retrieve summary details of AlphaFold 3D models for a given protein. IMPORTANT: The qualifier mus...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def alphafold_get_summary(
    qualifier: Optional[str] = None,
    uniprot_id: Optional[str] = None,
    uniprot_accession: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve summary details of AlphaFold 3D models for a given protein. IMPORTANT: The qualifier mus...

    Parameters
    ----------
    qualifier : str
        Protein identifier: UniProt ACCESSION (e.g., 'Q5SWX9'). Aliases: uniprot_id, ...
    uniprot_id : str
        Alias for qualifier. UniProt accession (e.g., 'P04637').
    uniprot_accession : str
        Alias for qualifier. UniProt accession (e.g., 'P04637').
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
            "qualifier": qualifier,
            "uniprot_id": uniprot_id,
            "uniprot_accession": uniprot_accession,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "alphafold_get_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["alphafold_get_summary"]
