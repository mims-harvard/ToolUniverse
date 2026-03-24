"""
GPCRdb_list_proteins

List GPCR protein families or proteins in a specific family from GPCRdb. Without family parameter...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GPCRdb_list_proteins(
    operation: Optional[str] = None,
    family: Optional[str] = None,
    protein_class: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List GPCR protein families or proteins in a specific family from GPCRdb. Without family parameter...

    Parameters
    ----------
    operation : str
        Operation type (fixed: list_proteins)
    family : str
        GPCR family code (e.g., '001' for Class A Rhodopsin, '002' for Class B). If n...
    protein_class : str
        Human-readable family name (e.g., 'Chemokine receptors', 'Class A'). Alias for family.
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
            "operation": operation,
            "family": family,
            "protein_class": protein_class,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GPCRdb_list_proteins",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GPCRdb_list_proteins"]
