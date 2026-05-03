"""
ENAPortal_count_records

Count the number of records matching a query in the European Nucleotide Archive (ENA). Supports c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENAPortal_count_records(
    query: str,
    result_type: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Count the number of records matching a query in the European Nucleotide Archive (ENA). Supports c...

    Parameters
    ----------
    query : str
        ENA search query. Examples: 'description="cancer"', 'tax_tree(9606)', 'descri...
    result_type : str | Any
        Type of records to count. Options: 'study', 'sample', 'read_run', 'analysis',...
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
        for k, v in {"query": query, "result_type": result_type}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENAPortal_count_records",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENAPortal_count_records"]
