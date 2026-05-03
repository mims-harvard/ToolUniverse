"""
Statistics_test

Perform basic statistical tests using pure Python (no scipy/numpy required). Supports: (1) Chi-sq...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Statistics_test(
    operation: str,
    observed: Optional[list[Any] | Any] = None,
    expected: Optional[list[Any] | Any] = None,
    a: Optional[int | Any] = None,
    b: Optional[int | Any] = None,
    c: Optional[int | Any] = None,
    d: Optional[int | Any] = None,
    alternative: Optional[str | Any] = "two-sided",
    data_x: Optional[list[Any] | Any] = None,
    data_y: Optional[list[Any] | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform basic statistical tests using pure Python (no scipy/numpy required). Supports: (1) Chi-sq...

    Parameters
    ----------
    operation : str
        Test type: 'chi_square' for goodness-of-fit, 'fisher_exact' for 2x2 tables, '...
    observed : list[Any] | Any
        Observed counts/frequencies (required for chi_square).
    expected : list[Any] | Any
        Expected counts/frequencies (required for chi_square). Will be rescaled to ma...
    a : int | Any
        Top-left cell of 2x2 table (required for fisher_exact).
    b : int | Any
        Top-right cell of 2x2 table (required for fisher_exact).
    c : int | Any
        Bottom-left cell of 2x2 table (required for fisher_exact).
    d : int | Any
        Bottom-right cell of 2x2 table (required for fisher_exact).
    alternative : str | Any
        Alternative hypothesis for Fisher's exact test (default: two-sided).
    data_x : list[Any] | Any
        X values for linear_regression, or group 1 data for t_test.
    data_y : list[Any] | Any
        Y values for linear_regression, or group 2 data for t_test.
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
        for k, v in {
            "operation": operation,
            "observed": observed,
            "expected": expected,
            "a": a,
            "b": b,
            "c": c,
            "d": d,
            "alternative": alternative,
            "data_x": data_x,
            "data_y": data_y,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Statistics_test",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Statistics_test"]
