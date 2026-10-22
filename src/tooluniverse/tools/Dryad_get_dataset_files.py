"""
Dryad_get_dataset_files

Get one page of downloadable files for a specific Dryad dataset version. Returns file names, size...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Dryad_get_dataset_files(
    version_id: int,
    per_page: Optional[int] = 20,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get one page of downloadable files for a specific Dryad dataset version. Returns file names, size...

    Parameters
    ----------
    version_id : int
        Version ID from Dryad dataset metadata. Found in _links.stash:version.href of...
    per_page : int
        Number of files per page (1-100). Defaults to Dryad's native page size of 20.
    page : int
        One-based file-list page. Dryad silently treats page 0 as page 1, so the wrap...
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
            "version_id": version_id,
            "per_page": per_page,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Dryad_get_dataset_files",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Dryad_get_dataset_files"]
