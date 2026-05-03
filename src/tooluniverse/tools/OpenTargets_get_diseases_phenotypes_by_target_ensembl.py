"""
OpenTargets_get_diseases_phenotypes_by_target_ensembl

Find diseases or phenotypes associated with a specific target using ensemblId.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_diseases_phenotypes_by_target_ensembl(
    ensemblId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find diseases or phenotypes associated with a specific target using ensemblId.

    Parameters
    ----------
    ensemblId : str
        The ensemblId of a target.
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
    _args = {k: v for k, v in {"ensemblId": ensemblId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_diseases_phenotypes_by_target_ensembl"]
