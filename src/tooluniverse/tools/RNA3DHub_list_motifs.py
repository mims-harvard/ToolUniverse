"""
RNA3DHub_list_motifs

List the motif groups of the BGSU RNA 3D Motif Atlas for one loop type. The Atlas takes the hairp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNA3DHub_list_motifs(
    loop_type: str,
    query: Optional[str] = None,
    min_instances: Optional[int] = None,
    release: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any] | dict[str, Any]:
    """
    List the motif groups of the BGSU RNA 3D Motif Atlas for one loop type. The Atlas takes the hairp...

    Parameters
    ----------
    loop_type : str
        Loop type: 'HL' hairpin loop, 'IL' internal loop, 'J3' to 'J7' 3-way to 7-way...
    query : str
        Text to find in the motif id, group name or loop annotations, e.g. 'GNRA', 'T...
    min_instances : int
        Keep groups with at least this number of loops (default 0: no filter). Many g...
    release : str
        Motif Atlas release id, e.g. '4.16'. Default 'current'. An unknown id returns...
    limit : int
        Rows per page (default 50, maximum 500).
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
            "loop_type": loop_type,
            "query": query,
            "min_instances": min_instances,
            "release": release,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNA3DHub_list_motifs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNA3DHub_list_motifs"]
