"""
INDRA_get_evidence_count

Get the total number of literature evidence items in INDRA DB for a gene, protein, or chemical wi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def INDRA_get_evidence_count(
    agent: str,
    operation: Optional[str] = None,
    type_: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the total number of literature evidence items in INDRA DB for a gene, protein, or chemical wi...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_evidence_count)
    agent : str
        Gene symbol, protein name, or chemical name (e.g., 'TP53', 'EGFR')
    type_ : str
        Optional: filter by statement type (e.g., 'Activation', 'Inhibition', 'Phosph...
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
        for k, v in {"operation": operation, "agent": agent, "type": type_}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "INDRA_get_evidence_count",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["INDRA_get_evidence_count"]
