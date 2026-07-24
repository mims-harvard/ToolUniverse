"""
FAERS_count_drug_characterization

Aggregate FDA adverse event (FAERS) reports for a drug by drugcharacterization, i.e. the role the...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_drug_characterization(
    medicinalproduct: str,
    serious: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Aggregate FDA adverse event (FAERS) reports for a drug by drugcharacterization, i.e. the role the...

    Parameters
    ----------
    medicinalproduct : str
        Drug name (brand or generic, e.g., 'WARFARIN', 'METFORMIN').
    serious : str
        Optional: Filter by event seriousness. Omit this parameter if you don't want ...
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
        for k, v in {"medicinalproduct": medicinalproduct, "serious": serious}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_count_drug_characterization",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_drug_characterization"]
