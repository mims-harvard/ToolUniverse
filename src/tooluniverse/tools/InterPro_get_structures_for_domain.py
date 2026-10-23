"""
InterPro_get_structures_for_domain

Find PDB structures containing a specific Pfam domain using the InterPro API. Results are cursor-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_structures_for_domain(
    pfam_accession: str,
    max_results: Optional[int] = 20,
    cursor: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find PDB structures containing a specific Pfam domain using the InterPro API. Results are cursor-...

    Parameters
    ----------
    pfam_accession : str
        Pfam domain accession. Examples: 'PF00870' (P53 DNA-binding, 215 structures),...
    max_results : int
        Maximum number of PDB structures to return (default 20, max 200).
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
            "pfam_accession": pfam_accession,
            "max_results": max_results,
            "cursor": cursor,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "InterPro_get_structures_for_domain",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_structures_for_domain"]
