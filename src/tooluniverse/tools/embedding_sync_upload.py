"""
embedding_sync_upload

Upload a per-collection datastore to Hugging Face Hub: <name>.db and <name>.faiss, plus metadata ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def embedding_sync_upload(
    database_name: str,
    repository: str,
    action: Optional[str] = None,
    description: Optional[str] = "",
    private: Optional[bool] = False,
    commit_message: Optional[str] = "Upload datastore",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Upload a per-collection datastore to Hugging Face Hub: <name>.db and <name>.faiss, plus metadata ...

    Parameters
    ----------
    action : str

    database_name : str
        Collection/database name to upload (expects <name>.db and <name>.faiss under ...
    repository : str
        HF dataset repo (e.g., 'user/repo')
    description : str
        Optional dataset description in the HF README
    private : bool
        Create/use a private HF repo
    commit_message : str
        Commit message for the upload
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
            "database_name": database_name,
            "repository": repository,
            "description": description,
            "private": private,
            "commit_message": commit_message,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "embedding_sync_upload",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["embedding_sync_upload"]
