"""
OpenGWAS_get_mr_instruments

Assemble harmonized two-sample Mendelian randomization (MR) instruments from the IEU OpenGWAS dat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenGWAS_get_mr_instruments(
    exposure_id: str,
    outcome_id: Optional[str] = None,
    pval: Optional[float] = 5e-08,
    clump: Optional[int] = 1,
    r2: Optional[float] = 0.001,
    kb: Optional[int] = 10000,
    pop: Optional[str] = "EUR",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Assemble harmonized two-sample Mendelian randomization (MR) instruments from the IEU OpenGWAS dat...

    Parameters
    ----------
    exposure_id : str
        IEU OpenGWAS study ID for the exposure (e.g. 'ieu-a-2'). Find IDs via EpiGrap...
    outcome_id : str
        IEU OpenGWAS study ID for the outcome (e.g. 'ieu-a-7'). Optional — omit to re...
    pval : float
        Instrument p-value threshold for the exposure (default 5e-8, genome-wide sign...
    clump : int
        1 to LD-clump instruments to independent SNPs (default), 0 to skip clumping.
    r2 : float
        LD r2 threshold for clumping (default 0.001).
    kb : int
        Clumping window in kb (default 10000).
    pop : str
        Reference population for LD clumping (default 'EUR').
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
            "exposure_id": exposure_id,
            "outcome_id": outcome_id,
            "pval": pval,
            "clump": clump,
            "r2": r2,
            "kb": kb,
            "pop": pop,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenGWAS_get_mr_instruments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenGWAS_get_mr_instruments"]
