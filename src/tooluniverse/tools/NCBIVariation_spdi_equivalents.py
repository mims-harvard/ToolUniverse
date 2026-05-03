"""
NCBIVariation_spdi_equivalents

Get all equivalent SPDI representations of a variant across different reference sequences and gen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIVariation_spdi_equivalents(
    spdi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all equivalent SPDI representations of a variant across different reference sequences and gen...

    Parameters
    ----------
    spdi : str
        Variant in SPDI notation. Examples: 'NC_000001.11:230710047:A:G' (GRCh38 AGT ...
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
    _args = {k: v for k, v in {"spdi": spdi}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NCBIVariation_spdi_equivalents",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIVariation_spdi_equivalents"]
