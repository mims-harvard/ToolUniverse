"""
InterPro_get_structures_for_domain

Find all PDB structures containing a specific Pfam domain using the InterPro API. Returns experim...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_structures_for_domain(
    pfam_accession: str,
    max_results: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find all PDB structures containing a specific Pfam domain using the InterPro API. Returns experim...

    Parameters
    ----------
    pfam_accession : str
        Pfam domain accession. Examples: 'PF00870' (P53 DNA-binding, 215 structures),...
    max_results : int
        Maximum number of PDB structures to return (default 20, max 200).
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
        {
            "name": "InterPro_get_structures_for_domain",
            "arguments": {"pfam_accession": pfam_accession, "max_results": max_results},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_structures_for_domain"]
