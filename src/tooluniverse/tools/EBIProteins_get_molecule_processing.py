"""
EBIProteins_get_molecule_processing

Get and page through molecule-processing features for a protein from the EBI Proteins API. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_molecule_processing(
    accession: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get and page through molecule-processing features for a protein from the EBI Proteins API. Return...

    Parameters
    ----------
    accession : str
        UniProt accession. Examples: 'P01308' (Insulin - classic example), 'P01375' (...
    limit : int
        Maximum features to return on this page.
    offset : int
        Zero-based offset into category features.
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
        for k, v in {"accession": accession, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBIProteins_get_molecule_processing",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_molecule_processing"]
