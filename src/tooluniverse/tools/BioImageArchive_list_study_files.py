"""
BioImageArchive_list_study_files

List the file/image manifest of a BioImage Archive study, giving per-file download paths and per-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioImageArchive_list_study_files(
    accession: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the file/image manifest of a BioImage Archive study, giving per-file download paths and per-...

    Parameters
    ----------
    accession : str
        BioImage Archive study accession. Format S-BIAD#### / S-BSST#### (e.g. 'S-BIA...
    limit : int
        Maximum number of files to return (default 25, max 500).
    offset : int
        Number of files to skip for pagination (default 0).
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
        for k, v in {"accession": accession, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioImageArchive_list_study_files",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioImageArchive_list_study_files"]
