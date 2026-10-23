"""
InterPro_get_proteins_by_domain

Find proteins that contain a specific InterPro domain. Results are cursor-paginated: when has_mor...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_proteins_by_domain(
    domain_id: str,
    page_size: Optional[int] = 20,
    reviewed_only: Optional[bool] = False,
    cursor: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find proteins that contain a specific InterPro domain. Results are cursor-paginated: when has_mor...

    Parameters
    ----------
    domain_id : str
        InterPro accession ID. Examples: 'IPR011615' (p53 DNA-binding domain, 6K prot...
    page_size : int
        Number of proteins to return (1-50, default 20).
    reviewed_only : bool
        If true, only return Swiss-Prot reviewed entries (default false returns all U...
    cursor : str
        Opaque InterPro cursor returned as next_cursor by a previous call.
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
            "domain_id": domain_id,
            "page_size": page_size,
            "reviewed_only": reviewed_only,
            "cursor": cursor,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "InterPro_get_proteins_by_domain",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_proteins_by_domain"]
