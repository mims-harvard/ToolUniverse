"""
GeneNetwork_get_trait_info

Get detailed information about a specific trait (probe/gene) in a GeneNetwork dataset. Returns tr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GeneNetwork_get_trait_info(
    dataset_name: str,
    trait_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific trait (probe/gene) in a GeneNetwork dataset. Returns tr...

    Parameters
    ----------
    dataset_name : str
        Dataset name/abbreviation. Examples: 'HC_M2_0606_P' (Hippocampus Consortium M...
    trait_name : str
        Trait/probe identifier. Examples: '1436869_at' (Shh probe), '1457211_at', '14...
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

    return get_shared_client().run_one_function(
        {
            "name": "GeneNetwork_get_trait_info",
            "arguments": {"dataset_name": dataset_name, "trait_name": trait_name},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GeneNetwork_get_trait_info"]
