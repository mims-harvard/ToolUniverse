"""
TCIA_get_modality_values

Get the imaging modalities available in a specific TCIA collection or across all collections. Ret...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_get_modality_values(
    Collection: Optional[str | Any] = None,
    BodyPartExamined: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the imaging modalities available in a specific TCIA collection or across all collections. Ret...

    Parameters
    ----------
    Collection : str | Any
        Collection name to filter by (e.g., 'LIDC-IDRI'). Omit to get all modalities.
    BodyPartExamined : str | Any
        Body part to filter by (e.g., 'CHEST')
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
            "name": "TCIA_get_modality_values",
            "arguments": {
                "Collection": Collection,
                "BodyPartExamined": BodyPartExamined,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_get_modality_values"]
