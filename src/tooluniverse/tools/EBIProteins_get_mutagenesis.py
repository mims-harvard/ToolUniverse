"""
EBIProteins_get_mutagenesis

Get mutagenesis experiment data for a protein from the EBI Proteins API with limit/offset paginat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_mutagenesis(
    accession: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get mutagenesis experiment data for a protein from the EBI Proteins API with limit/offset paginat...

    Parameters
    ----------
    accession : str
        UniProt accession. Examples: 'P04637' (TP53/p53), 'P38398' (BRCA1), 'P00533' ...
    limit : int
        Maximum number of mutagenesis features to return in this page.
    offset : int
        Zero-based feature offset. Use data.next_offset for the next page.
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
            "name": "EBIProteins_get_mutagenesis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_mutagenesis"]
