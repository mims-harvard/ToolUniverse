"""
EBIProteins_get_epitopes

Get experimentally-determined immune epitope regions for a protein using the EBI Proteins API. Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_epitopes(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get experimentally-determined immune epitope regions for a protein using the EBI Proteins API. Re...

    Parameters
    ----------
    accession : str
        UniProt accession number for the protein. Examples: 'P04637' (TP53), 'P00533'...
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
        {"name": "EBIProteins_get_epitopes", "arguments": {"accession": accession}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_epitopes"]
