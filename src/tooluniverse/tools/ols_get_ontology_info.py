"""
ols_get_ontology_info

Get detailed information about an ontology
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_get_ontology_info(
    operation: Optional[str] = None,
    ontology_id: Optional[str] = None,
    ontology: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about an ontology

    Parameters
    ----------
    operation : str
        The operation to perform (get_ontology_info)
    ontology_id : str
        The ID of the ontology to retrieve
    ontology : str
        Alias for ontology_id. The ontology abbreviation (e.g. mondo, hp, go, ordo).
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
        for k, v in {
            "operation": operation,
            "ontology_id": ontology_id,
            "ontology": ontology,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ols_get_ontology_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ols_get_ontology_info"]
