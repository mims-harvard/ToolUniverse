"""
Epidemiology_vaccine_coverage

Derive vaccine effectiveness from field surveillance data using the screening method (Farrington ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Epidemiology_vaccine_coverage(
    operation: str,
    R0: float,
    PCV: float,
    PPV: float,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Derive vaccine effectiveness from field surveillance data using the screening method (Farrington ...

    Parameters
    ----------
    operation : str
        Operation type
    R0 : float
        Basic reproduction number (must be > 1)
    PCV : float
        Proportion of disease cases that were vaccinated (0, 1)
    PPV : float
        Proportion of total population that is vaccinated (0, 1)
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
        for k, v in {"operation": operation, "R0": R0, "PCV": PCV, "PPV": PPV}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Epidemiology_vaccine_coverage",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Epidemiology_vaccine_coverage"]
