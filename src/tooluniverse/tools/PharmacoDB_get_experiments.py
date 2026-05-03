"""
PharmacoDB_get_experiments

Get drug sensitivity experiments from PharmacoDB with dose-response curves and pharmacological pr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmacoDB_get_experiments(
    operation: str,
    compound_name: Optional[str | Any] = None,
    cell_line_name: Optional[str | Any] = None,
    dataset_name: Optional[str | Any] = None,
    per_page: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get drug sensitivity experiments from PharmacoDB with dose-response curves and pharmacological pr...

    Parameters
    ----------
    operation : str
        Operation type
    compound_name : str | Any
        Compound/drug name to filter experiments (e.g., 'Paclitaxel', 'Erlotinib')
    cell_line_name : str | Any
        Cell line name to filter experiments (e.g., 'MCF-7', 'A549')
    dataset_name : str | Any
        Dataset name to filter (e.g., 'GDSC1', 'CCLE', 'CTRPv2', 'PRISM')
    per_page : int
        Number of experiments to return per page (default 10, max 100)
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
            "compound_name": compound_name,
            "cell_line_name": cell_line_name,
            "dataset_name": dataset_name,
            "per_page": per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PharmacoDB_get_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmacoDB_get_experiments"]
