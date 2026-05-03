"""
alphafold_get_annotations

Retrieve AlphaFold MUTAGEN annotations for a given UniProt accession. Returns experimental mutage...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def alphafold_get_annotations(
    qualifier: Optional[str] = None,
    uniprot_id: Optional[str] = None,
    uniprot_accession: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve AlphaFold MUTAGEN annotations for a given UniProt accession. Returns experimental mutage...

    Parameters
    ----------
    qualifier : str
        UniProt ACCESSION (e.g., 'P69905'). Aliases: uniprot_id, uniprot_accession.
    uniprot_id : str
        Alias for qualifier. UniProt accession (e.g., 'P69905').
    uniprot_accession : str
        Alias for qualifier. UniProt accession (e.g., 'P69905').
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
            "name": "alphafold_get_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["alphafold_get_annotations"]
