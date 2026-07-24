"""
PRIDE_get_projects_for_protein

Reverse lookup: list every PRIDE Archive project (PXD accession) that identified a given protein,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PRIDE_get_projects_for_protein(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse lookup: list every PRIDE Archive project (PXD accession) that identified a given protein,...

    Parameters
    ----------
    accession : str
        UniProt protein accession (e.g., 'P38398' for BRCA1, 'P04637' for TP53, 'P005...
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
            "name": "PRIDE_get_projects_for_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PRIDE_get_projects_for_protein"]
