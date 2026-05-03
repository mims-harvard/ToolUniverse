"""
FourDN_get_experiment_metadata

Get metadata for 4DN experiments including experimental design, biosource information, protocol d...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FourDN_get_experiment_metadata(
    operation: str,
    experiment_accession: str,
    include_full_metadata: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get metadata for 4DN experiments including experimental design, biosource information, protocol d...

    Parameters
    ----------
    operation : str

    experiment_accession : str
        4DN experiment accession (e.g., '4DNEXHVF8WA9'). Obtain by searching with Fou...
    include_full_metadata : bool
        Include complete API response in 'metadata' field (default: false). Set to tr...
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
            "experiment_accession": experiment_accession,
            "include_full_metadata": include_full_metadata,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FourDN_get_experiment_metadata",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FourDN_get_experiment_metadata"]
