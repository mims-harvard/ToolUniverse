"""
proteins_api_get_genome_mappings

Get reference genome mappings for a protein using the Proteins API. Supports batch operations: pa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def proteins_api_get_genome_mappings(
    accession: str | list[Any],
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get reference genome mappings for a protein using the Proteins API. Supports batch operations: pa...

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
    list[Any]
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
            "name": "proteins_api_get_genome_mappings",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["proteins_api_get_genome_mappings"]
