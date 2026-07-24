"""
ROC_analysis

Deterministic ROC / AUC diagnostic-accuracy analysis for any binary classifier or continuous biom...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ROC_analysis(
    scores: Optional[list[Any]] = None,
    labels: Optional[list[Any]] = None,
    csv_path: Optional[str] = None,
    score_col: Optional[str] = None,
    label_col: Optional[str] = None,
    positive_label: Optional[int | str] = None,
    cutoff: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Deterministic ROC / AUC diagnostic-accuracy analysis for any binary classifier or continuous biom...

    Parameters
    ----------
    scores : list[Any]
        Continuous prediction scores (inline). Pair with 'labels'.
    labels : list[Any]
        Binary class labels aligned to scores (1=positive/0=negative, or any two valu...
    csv_path : str
        Alternative to inline arrays: path to a CSV with score and label columns
    score_col : str
        Score column name in csv_path (default 'score')
    label_col : str
        Label column name in csv_path (default 'label')
    positive_label : int | str
        Which label value is the positive class (default: 1, or the larger of two cla...
    cutoff : float
        Optional fixed cutoff; also reports sensitivity/specificity at score >= cutoff
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
            "scores": scores,
            "labels": labels,
            "csv_path": csv_path,
            "score_col": score_col,
            "label_col": label_col,
            "positive_label": positive_label,
            "cutoff": cutoff,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ROC_analysis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ROC_analysis"]
