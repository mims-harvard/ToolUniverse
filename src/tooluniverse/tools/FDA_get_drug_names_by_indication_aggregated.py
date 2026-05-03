"""
FDA_get_drug_names_by_indication_aggregated

Retrieve and aggregate drug names by indication, grouping by generic name with all brand names. T...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_get_drug_names_by_indication_aggregated(
    indication: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve and aggregate drug names by indication, grouping by generic name with all brand names. T...

    Parameters
    ----------
    indication : str
        The indication or usage of the drug.
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
    _args = {k: v for k, v in {"indication": indication}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FDA_get_drug_names_by_indication_aggregated",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_get_drug_names_by_indication_aggregated"]
