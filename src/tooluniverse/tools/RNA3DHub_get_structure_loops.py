"""
RNA3DHub_get_structure_loops

List the loops that the BGSU RNA 3D Hub annotates in one PDB structure: hairpin loops (HL), inter...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNA3DHub_get_structure_loops(
    pdb_id: str,
    loop_type: Optional[str] = None,
    model: Optional[int] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any] | dict[str, Any]:
    """
    List the loops that the BGSU RNA 3D Hub annotates in one PDB structure: hairpin loops (HL), inter...

    Parameters
    ----------
    pdb_id : str
        4-character PDB id of an RNA-containing structure, e.g. '4TNA' or '1S72'.
    loop_type : str
        Keep one loop type: 'HL' hairpin, 'IL' internal, 'J3' to 'J7' junctions. Omit...
    model : int
        Keep the loops of one model of a multi-model (NMR) entry, e.g. 1. Omit for al...
    limit : int
        Rows per page (default 100, maximum 500).
    offset : int
        Rows to skip (default 0). Continue with metadata.next_offset while metadata.h...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any] | dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "pdb_id": pdb_id,
            "loop_type": loop_type,
            "model": model,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNA3DHub_get_structure_loops",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNA3DHub_get_structure_loops"]
