"""
OpenTargets_get_target_prioritisation

Retrieve OpenTargets target prioritisation scores for a target by Ensembl gene ID. Returns ~16 we...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_target_prioritisation(
    ensemblId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve OpenTargets target prioritisation scores for a target by Ensembl gene ID. Returns ~16 we...

    Parameters
    ----------
    ensemblId : str
        Ensembl gene ID of the target (e.g., 'ENSG00000146648' for EGFR).
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
    _args = {k: v for k, v in {"ensemblId": ensemblId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_target_prioritisation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_target_prioritisation"]
