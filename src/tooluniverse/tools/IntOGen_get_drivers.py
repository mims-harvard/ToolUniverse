"""
IntOGen_get_drivers

Get cancer driver genes for a specific cancer type from IntOGen. Returns genes identified as driv...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IntOGen_get_drivers(
    cancer_type: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get cancer driver genes for a specific cancer type from IntOGen. Returns genes identified as driv...

    Parameters
    ----------
    cancer_type : str
        IntOGen cancer type code. Examples: 'BRCA' (breast), 'LUAD' (lung adenocarcin...
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

    return get_shared_client().run_one_function(
        {"name": "IntOGen_get_drivers", "arguments": {"cancer_type": cancer_type}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IntOGen_get_drivers"]
