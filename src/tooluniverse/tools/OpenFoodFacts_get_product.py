"""
OpenFoodFacts_get_product

Get detailed information about a specific food product by barcode using the Open Food Facts datab...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFoodFacts_get_product(
    barcode: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific food product by barcode using the Open Food Facts datab...

    Parameters
    ----------
    barcode : str
        Product barcode (EAN-13 or UPC). Examples: '3017620422003' (Nutella 400g), '0...
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
        {"name": "OpenFoodFacts_get_product", "arguments": {"barcode": barcode}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFoodFacts_get_product"]
