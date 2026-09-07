"""
Nextstrain_list_datasets

List available pathogen phylogenetic datasets from Nextstrain. Returns datasets grouped by pathog...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Nextstrain_list_datasets(
    pathogen: Optional[str | Any] = None,
    datasets_per_pathogen: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List available pathogen phylogenetic datasets from Nextstrain. Returns datasets grouped by pathog...

    Parameters
    ----------
    pathogen : str | Any
        Optional pathogen name filter. Examples: 'flu', 'ebola', 'zika', 'dengue', 'm...
    datasets_per_pathogen : int | Any
        Maximum dataset paths listed per pathogen (default 10; 0 lists every da...
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
            "datasets_per_pathogen": datasets_per_pathogen,
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
