"""
Epidemiology_bayesian

Compute post-test probability via Bayes' theorem given pre-test prevalence, test sensitivity, and...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Epidemiology_bayesian(
    operation: str,
    prevalence: float,
    sensitivity: float,
    specificity: float,
    test_result: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compute post-test probability via Bayes' theorem given pre-test prevalence, test sensitivity, and...

    Parameters
    ----------
    operation : str
        Operation type
    prevalence : float
        Pre-test probability (disease prevalence) [0, 1]
    sensitivity : float
        Test sensitivity P(test+ | disease+) [0, 1]
    specificity : float
        Test specificity P(test- | disease-) [0, 1]
    test_result : str
        Whether to compute post-test probability for a positive or negative result (d...
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
            "prevalence": prevalence,
            "sensitivity": sensitivity,
            "specificity": specificity,
            "test_result": test_result,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Epidemiology_bayesian",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Epidemiology_bayesian"]
