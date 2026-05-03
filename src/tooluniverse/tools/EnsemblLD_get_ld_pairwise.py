"""
EnsemblLD_get_ld_pairwise

Get pairwise linkage disequilibrium (LD) statistics between two specific variants from the Ensemb...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblLD_get_ld_pairwise(
    variant1: str,
    variant2: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get pairwise linkage disequilibrium (LD) statistics between two specific variants from the Ensemb...

    Parameters
    ----------
    variant1 : str
        rs ID of the first variant. Examples: 'rs6792369', 'rs429358'.
    variant2 : str
        rs ID of the second variant. Examples: 'rs1042779', 'rs7412'.
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
        for k, v in {"variant1": variant1, "variant2": variant2}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblLD_get_ld_pairwise",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblLD_get_ld_pairwise"]
