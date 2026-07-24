"""
IPD_get_hla_allele

Fetch the full IPD-IMGT/HLA record for a single HLA allele by its IPD accession (e.g. 'HLA00001')...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IPD_get_hla_allele(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch the full IPD-IMGT/HLA record for a single HLA allele by its IPD accession (e.g. 'HLA00001')...

    Parameters
    ----------
    accession : str
        IPD-IMGT/HLA allele accession (e.g. 'HLA00001'). Obtain via IPD_search_hla_al...
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "IPD_get_hla_allele",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IPD_get_hla_allele"]
