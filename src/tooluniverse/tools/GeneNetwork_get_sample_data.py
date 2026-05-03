"""
GeneNetwork_get_sample_data

Get expression or phenotype values for a specific gene/trait across all samples in a GeneNetwork ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GeneNetwork_get_sample_data(
    dataset_name: str,
    trait_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get expression or phenotype values for a specific gene/trait across all samples in a GeneNetwork ...

    Parameters
    ----------
    dataset_name : str
        Dataset long abbreviation (e.g., 'HC_M2_0606_P' for BXD hippocampus, 'BXDPubl...
    trait_name : str
        Probe/trait identifier within the dataset (e.g., '1436869_at' for a microarra...
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
        for k, v in {"dataset_name": dataset_name, "trait_name": trait_name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GeneNetwork_get_sample_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GeneNetwork_get_sample_data"]
