"""
proteins_api_get_protein

Get comprehensive protein information from Proteins API by UniProt accession. Returns protein ann...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def proteins_api_get_protein(
    accession: str | list[Any],
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get comprehensive protein information from Proteins API by UniProt accession. Returns protein ann...

    Parameters
    ----------
    accession : str | list[Any]
        UniProt protein accession(s). Can be a single accession (e.g., 'P05067'), com...
    format : str
        Response format. JSON is recommended for most use cases.
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
        for k, v in {"accession": accession, "format": format}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "proteins_api_get_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["proteins_api_get_protein"]
