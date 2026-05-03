"""
EBITaxonomy_get_by_id

Get taxonomy classification by NCBI Taxonomy ID from the EBI Taxonomy service. Returns scientific...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBITaxonomy_get_by_id(
    tax_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get taxonomy classification by NCBI Taxonomy ID from the EBI Taxonomy service. Returns scientific...

    Parameters
    ----------
    tax_id : str
        NCBI Taxonomy ID (numeric). Examples: '9606' (human), '10090' (mouse), '562' ...
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
    _args = {k: v for k, v in {"tax_id": tax_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EBITaxonomy_get_by_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBITaxonomy_get_by_id"]
