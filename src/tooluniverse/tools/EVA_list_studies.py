"""
EVA_list_studies

List EVA variant studies with deterministic local limit/offset pagination. The upstream endpoint ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EVA_list_studies(
    species: Optional[str] = "hsapiens_grch38",
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List EVA variant studies with deterministic local limit/offset pagination. The upstream endpoint ...

    Parameters
    ----------
    species : str
        Species and assembly (e.g., 'hsapiens_grch38', 'hsapiens_grch37', 'mmusculus_...
    limit : int
        Studies per deterministic local page (default 20, max 1000).
    offset : int
        Zero-based offset after sorting by studyId. Continue with metadata.next_offset.
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
        for k, v in {"species": species, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EVA_list_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EVA_list_studies"]
