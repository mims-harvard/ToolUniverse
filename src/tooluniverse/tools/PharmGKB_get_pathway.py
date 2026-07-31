"""
PharmGKB_get_pathway

Get a curated pharmacogenomic pathway from PharmGKB/ClinPGx by pathway ID (e.g., 'PA145011113' = ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmGKB_get_pathway(
    pathway_id: str,
    id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a curated pharmacogenomic pathway from PharmGKB/ClinPGx by pathway ID (e.g., 'PA145011113' = ...

    Parameters
    ----------
    pathway_id : str
        PharmGKB Pathway Accession ID (e.g., 'PA145011113' for the Warfarin Pharmacok...
    id : str
        Alias for pathway_id.
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
        k: v for k, v in {"pathway_id": pathway_id, "id": id}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PharmGKB_get_pathway",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmGKB_get_pathway"]
