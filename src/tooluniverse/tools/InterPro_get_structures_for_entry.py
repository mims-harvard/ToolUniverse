"""
InterPro_get_structures_for_entry

List the experimentally-solved PDB structures whose chains contain a given InterPro domain/family...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_structures_for_entry(
    interpro_id: str,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List the experimentally-solved PDB structures whose chains contain a given InterPro domain/family...

    Parameters
    ----------
    interpro_id : str
        An integrated InterPro accession, e.g. IPR000719 (Protein kinase domain).
    page_size : int
        Number of structures to return (1-100, default 20).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"interpro_id": interpro_id, "page_size": page_size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "InterPro_get_structures_for_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_structures_for_entry"]
