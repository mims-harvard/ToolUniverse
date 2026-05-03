"""
TCIA_get_body_part_values

Get the body parts examined in TCIA imaging collections. Returns body part names for filtering se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_get_body_part_values(
    Collection: Optional[str | Any] = None,
    Modality: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the body parts examined in TCIA imaging collections. Returns body part names for filtering se...

    Parameters
    ----------
    Collection : str | Any
        Collection name to filter by (e.g., 'TCGA-GBM')
    Modality : str | Any
        Imaging modality to filter by (e.g., 'CT', 'MR')
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
        for k, v in {"Collection": Collection, "Modality": Modality}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TCIA_get_body_part_values",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_get_body_part_values"]
