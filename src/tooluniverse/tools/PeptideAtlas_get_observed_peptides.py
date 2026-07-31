"""
PeptideAtlas_get_observed_peptides

Query PeptideAtlas (SBEAMS PeptideAtlas, ISB) for the mass-spectrometry-OBSERVED peptides of a pr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PeptideAtlas_get_observed_peptides(
    biosequence_name: Optional[str] = None,
    atlas_build_id: Optional[int | str] = None,
    row_limit: Optional[int | str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query PeptideAtlas (SBEAMS PeptideAtlas, ISB) for the mass-spectrometry-OBSERVED peptides of a pr...

    Parameters
    ----------
    biosequence_name : str
        Protein/gene constraint: a UniProt accession or PeptideAtlas biosequence name...
    atlas_build_id : int | str
        PeptideAtlas build to query. Default 572 (Human 2024-01).
    row_limit : int | str
        Maximum number of peptide rows to return (default 500). Use a small value (e....
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
            "biosequence_name": biosequence_name,
            "atlas_build_id": atlas_build_id,
            "row_limit": row_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PeptideAtlas_get_observed_peptides",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PeptideAtlas_get_observed_peptides"]
