"""
UniProt_id_mapping

Map IDs between databases using UniProt's asynchronous service. Fetches every upstream result pag...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProt_id_mapping(
    ids: list[str] | str,
    from_db: str,
    to_db: Optional[str] = None,
    max_wait_time: Optional[int] = None,
    result_offset: Optional[int] = 0,
    result_limit: Optional[int] = 500,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Map IDs between databases using UniProt's asynchronous service. Fetches every upstream result pag...

    Parameters
    ----------
    ids : list[str] | str
        ID(s) to map. Can be single string or array of strings, e.g., 'ENSG0000014151...
    from_db : str
        Source database. Examples: 'Ensembl', 'Gene_Name', 'RefSeq_Protein', 'PDB', '...
    to_db : str
        Target database (default: 'UniProtKB')
    max_wait_time : int
        Maximum time to wait for async task completion in seconds (default: 30)
    result_offset : int
        Zero-based offset within the complete mapping result set.
    result_limit : int
        Maximum mapped records returned in this response. mapped_count remains the co...
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
            "ids": ids,
            "from_db": from_db,
            "to_db": to_db,
            "max_wait_time": max_wait_time,
            "result_offset": result_offset,
            "result_limit": result_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniProt_id_mapping",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProt_id_mapping"]
