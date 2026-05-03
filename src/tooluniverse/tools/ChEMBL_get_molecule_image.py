"""
ChEMBL_get_molecule_image

Get molecular structure image (SVG or PNG format) for a molecule by ChEMBL ID. Returns the image ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_molecule_image(
    chembl_id: str,
    format: Optional[str] = "svg",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Get molecular structure image (SVG or PNG format) for a molecule by ChEMBL ID. Returns the image ...

    Parameters
    ----------
    chembl_id : str
        ChEMBL molecule ID (e.g., 'CHEMBL25'). To find a molecule ID, use ChEMBL_sear...
    format : str
        Image format
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"chembl_id": chembl_id, "format": format}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_molecule_image",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_molecule_image"]
