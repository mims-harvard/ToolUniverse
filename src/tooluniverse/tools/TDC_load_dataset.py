"""
TDC_load_dataset

Load a named Therapeutics Data Commons (TDC) benchmark dataset locally via the PyTDC package and ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TDC_load_dataset(
    problem: str,
    name: str,
    sample_rows: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Load a named Therapeutics Data Commons (TDC) benchmark dataset locally via the PyTDC package and ...

    Parameters
    ----------
    problem : str
        TDC problem (case-insensitive). single_pred: ADME, Tox, HTS, QM, Yields, Epit...
    name : str
        Dataset name within the problem (case-insensitive). Example: 'Caco2_Wang' for...
    sample_rows : int
        Number of head rows to include in the sample (default 5, max 20).
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
            "problem": problem,
            "name": name,
            "sample_rows": sample_rows,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TDC_load_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TDC_load_dataset"]
