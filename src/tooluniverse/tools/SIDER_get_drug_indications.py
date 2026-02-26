"""
SIDER_get_drug_indications

Get the therapeutic indications for a drug from SIDER. Indications are medical conditions that a ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIDER_get_drug_indications(
    operation: str,
    drug_name: Optional[str | Any] = None,
    sider_drug_id: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the therapeutic indications for a drug from SIDER. Indications are medical conditions that a ...

    Parameters
    ----------
    operation : str
        Operation type
    drug_name : str | Any
        Drug name (e.g., 'aspirin', 'metformin'). Will search SIDER and use first match.
    sider_drug_id : str | Any
        SIDER drug ID (PubChem CID) from SIDER_search_drug (e.g., '2244' for aspirin)
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
        {
            "name": "SIDER_get_drug_indications",
            "arguments": {
                "operation": operation,
                "drug_name": drug_name,
                "sider_drug_id": sider_drug_id,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIDER_get_drug_indications"]
