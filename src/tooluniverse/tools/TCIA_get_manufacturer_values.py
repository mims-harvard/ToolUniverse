"""
TCIA_get_manufacturer_values

Get the distinct scanner Manufacturer values present in a TCIA collection (optionally filtered by...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_get_manufacturer_values(
    Collection: Optional[str] = None,
    Modality: Optional[str] = None,
    BodyPartExamined: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the distinct scanner Manufacturer values present in a TCIA collection (optionally filtered by...

    Parameters
    ----------
    Collection : str
        Collection name to filter by (e.g., 'LIDC-IDRI'). Omit to get manufacturers a...
    Modality : str
        Imaging modality to filter by (e.g., 'CT', 'MR')
    BodyPartExamined : str
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "Collection": Collection,
            "Modality": Modality,
            "BodyPartExamined": BodyPartExamined,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TCIA_get_manufacturer_values",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_get_manufacturer_values"]
