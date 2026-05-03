"""
embedding_sync_download

Download a per-collection datastore from Hugging Face Hub into ./data/embeddings as <name>.db and...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def embedding_sync_download(
    repository: str,
    action: Optional[str] = None,
    local_name: Optional[str] = None,
    overwrite: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Download a per-collection datastore from Hugging Face Hub into ./data/embeddings as <name>.db and...

    Parameters
    ----------
    action : str

    repository : str
        HF dataset repo to download from (e.g., 'user/repo')
    local_name : str
        Local collection name to save as (defaults to repo basename)
    overwrite : bool
        Whether to overwrite existing local files
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
            "action": action,
            "repository": repository,
            "local_name": local_name,
            "overwrite": overwrite,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "embedding_sync_download",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["embedding_sync_download"]
