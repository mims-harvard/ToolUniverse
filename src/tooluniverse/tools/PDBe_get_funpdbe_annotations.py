"""
PDBe_get_funpdbe_annotations

Get functional annotations from the FunPDBe consortium for a PDB structure. FunPDBe aggregates re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBe_get_funpdbe_annotations(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get functional annotations from the FunPDBe consortium for a PDB structure. FunPDBe aggregates re...

    Parameters
    ----------
    pdb_id : str
        PDB identifier (4-character code). Examples: '4hhb' (hemoglobin, has depth an...
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
    _args = {k: v for k, v in {"pdb_id": pdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PDBe_get_funpdbe_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBe_get_funpdbe_annotations"]
