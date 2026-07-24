"""
metabolights_get_reference_compound

Retrieve a record from the MetaboLights Reference Compound database (the curated metabolite/compo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def metabolights_get_reference_compound(
    compound_id: Optional[str] = None,
    list: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a record from the MetaboLights Reference Compound database (the curated metabolite/compo...

    Parameters
    ----------
    compound_id : str
        MetaboLights reference-compound accession, e.g. 'MTBLC10'. Always starts with...
    list : bool
        If true, return the full list of all reference-compound accessions (MTBLC*) i...
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
        for k, v in {"compound_id": compound_id, "list": list}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "metabolights_get_reference_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["metabolights_get_reference_compound"]
