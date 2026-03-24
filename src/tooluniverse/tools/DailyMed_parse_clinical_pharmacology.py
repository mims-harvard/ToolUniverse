"""
DailyMed_parse_clinical_pharmacology

Parse clinical pharmacology section from SPL XML. Returns PK parameters (Cmax, Tmax, t1/2, AUC), ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DailyMed_parse_clinical_pharmacology(
    operation: Optional[str] = None,
    setid: Optional[str] = None,
    drug_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Parse clinical pharmacology section from SPL XML. Returns PK parameters (Cmax, Tmax, t1/2, AUC), ...

    Parameters
    ----------
    operation : str
        Operation type (fixed)
    setid : str
        SPL Set ID to parse
    drug_name : str
        Drug name for automatic Set ID lookup (alternative to setid)
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
            "setid": setid,
            "drug_name": drug_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DailyMed_parse_clinical_pharmacology",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DailyMed_parse_clinical_pharmacology"]
