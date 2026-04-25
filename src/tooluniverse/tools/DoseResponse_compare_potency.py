"""
DoseResponse_compare_potency

Quantify relative potency between two compounds by independently fitting Hill sigmoidal curves to...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DoseResponse_compare_potency(
    operation: str,
    conc_a: list[Any],
    resp_a: list[Any],
    conc_b: list[Any],
    resp_b: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Quantify relative potency between two compounds by independently fitting Hill sigmoidal curves to...

    Parameters
    ----------
    operation : str
        Operation type
    conc_a : list[Any]
        Concentrations for compound A
    resp_a : list[Any]
        Responses for compound A
    conc_b : list[Any]
        Concentrations for compound B
    resp_b : list[Any]
        Responses for compound B
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
    _args = {k: v for k, v in {
        "operation": operation,
                "conc_a": conc_a,
                "resp_a": resp_a,
                "conc_b": conc_b,
                "resp_b": resp_b
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DoseResponse_compare_potency",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["DoseResponse_compare_potency"]
