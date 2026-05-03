"""
metabolights_get_study_data_files

Search for data files in a MetaboLights study. Returns a list of files matching the search criter...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def metabolights_get_study_data_files(
    study_id: str,
    search_pattern: Optional[str] = "FILES/*",
    file_match: Optional[bool] = True,
    folder_match: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for data files in a MetaboLights study. Returns a list of files matching the search criter...

    Parameters
    ----------
    study_id : str
        MetaboLights study ID (e.g., 'MTBLS1')
    search_pattern : str
        Search pattern for files (e.g., '*.mzML', '*.zip', '*.d'). Default is 'FILES/...
    file_match : bool
        Include file matches in results. At least one of file_match or folder_match m...
    folder_match : bool
        Include folder matches in results. At least one of file_match or folder_match...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "study_id": study_id,
            "search_pattern": search_pattern,
            "file_match": file_match,
            "folder_match": folder_match,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "metabolights_get_study_data_files",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["metabolights_get_study_data_files"]
