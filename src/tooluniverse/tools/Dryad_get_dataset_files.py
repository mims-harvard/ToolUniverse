"""
Dryad_get_dataset_files

Get the list of downloadable files for a specific Dryad dataset version. Returns file names, size...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Dryad_get_dataset_files(
    version_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the list of downloadable files for a specific Dryad dataset version. Returns file names, size...

    Parameters
    ----------
    version_id : int
        Version ID from Dryad dataset metadata. Found in _links.stash:version.href of...
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
        {"name": "Dryad_get_dataset_files", "arguments": {"version_id": version_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Dryad_get_dataset_files"]
