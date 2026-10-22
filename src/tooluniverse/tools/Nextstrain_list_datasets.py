"""
Nextstrain_list_datasets

List available pathogen phylogenetic datasets from Nextstrain, grouped by pathogen. Nested datase...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Nextstrain_list_datasets(
    pathogen: Optional[str] = None,
    dataset_limit: Optional[int] = 10,
    dataset_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List available pathogen phylogenetic datasets from Nextstrain, grouped by pathogen. Nested datase...

    Parameters
    ----------
    pathogen : str
        Optional pathogen name filter. Examples: 'flu', 'ebola', 'zika', 'dengue', 'm...
    dataset_limit : int
        Maximum datasets to return per matched pathogen group.
    dataset_offset : int
        Zero-based offset applied within every matched pathogen group. Continue each ...
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
        for k, v in {
            "pathogen": pathogen,
            "dataset_limit": dataset_limit,
            "dataset_offset": dataset_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Nextstrain_list_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Nextstrain_list_datasets"]
