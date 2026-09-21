"""
MetaAnalysis_run

Run a fixed-effects or random-effects meta-analysis from a set of effect sizes and standard error...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetaAnalysis_run(
    studies: list[Any],
    method: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Run a fixed-effects or random-effects meta-analysis from a set of effect sizes and standard error...

    Parameters
    ----------
    studies : list[Any]
        List of studies, each with name, effect_size, se, and optional n.
    method : str
        Meta-analysis method: 'fixed' for fixed-effects (inverse-variance), 'random' ...
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
        k: v for k, v in {"studies": studies, "method": method}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetaAnalysis_run",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetaAnalysis_run"]
