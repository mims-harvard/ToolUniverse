"""
OpenTargets_get_disease_ids_by_name

Given a disease or phenotype name, find all cross-referenced external IDs (e.g., OMIM, MONDO, MeS...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_disease_ids_by_name(
    name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Given a disease or phenotype name, find all cross-referenced external IDs (e.g., OMIM, MONDO, MeS...

    Parameters
    ----------
    name : str
        The name of the disease or phenotype (e.g. 'rheumatoid arthritis').
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
    _args = {k: v for k, v in {"name": name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_disease_ids_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_disease_ids_by_name"]
