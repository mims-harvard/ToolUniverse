"""
CTD_get_gene_chemicals

PERMANENTLY UNAVAILABLE: this tool always returns an error. CTD's native batchQuery.go is CAPTCHA...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CTD_get_gene_chemicals(
    input_terms: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    PERMANENTLY UNAVAILABLE: this tool always returns an error. CTD's native batchQuery.go is CAPTCHA...

    Parameters
    ----------
    input_terms : str
        Gene symbol or NCBI Gene ID. Unused -- this tool always returns an error; see...
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
    _args = {k: v for k, v in {"input_terms": input_terms}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CTD_get_gene_chemicals",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CTD_get_gene_chemicals"]
