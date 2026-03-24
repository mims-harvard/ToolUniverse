"""
INDRA_get_statements

Get literature-mined biological statements for a gene, protein, or chemical from INDRA DB. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def INDRA_get_statements(
    agent: str,
    operation: Optional[str] = None,
    type_: Optional[str] = None,
    agent2: Optional[str] = None,
    limit: Optional[int] = 10,
    ev_limit: Optional[int] = 2,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get literature-mined biological statements for a gene, protein, or chemical from INDRA DB. Return...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_statements)
    agent : str
        Gene symbol, protein name, or chemical name (e.g., 'TP53', 'EGFR', 'gefitinib...
    type_ : str
        Filter by statement type: Activation, Inhibition, Phosphorylation, Dephosphor...
    agent2 : str
        Second agent for pairwise queries (e.g., agent='BRAF' agent2='MAP2K1')
    limit : int
        Maximum statements to return (default: 10)
    ev_limit : int
        Maximum evidence items per statement (default: 2)
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
            "agent": agent,
            "type": type_,
            "agent2": agent2,
            "limit": limit,
            "ev_limit": ev_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "INDRA_get_statements",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["INDRA_get_statements"]
