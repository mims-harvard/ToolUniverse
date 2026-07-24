"""
HFInference_zero_shot_classify

Classify text against a caller-supplied set of candidate labels using any HuggingFace zero-shot-c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HFInference_zero_shot_classify(
    operation: str,
    model_id: str,
    text: str,
    candidate_labels: list[str],
    multi_label: Optional[bool] = None,
    wait_for_model: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Classify text against a caller-supplied set of candidate labels using any HuggingFace zero-shot-c...

    Parameters
    ----------
    operation : str
        Operation selector (fixed).
    model_id : str
        HuggingFace repo id of a zero-shot-classification / NLI model, e.g. 'facebook...
    text : str
        Input text to classify.
    candidate_labels : list[str]
        Non-empty list of candidate label strings to score the text against, e.g. ['r...
    multi_label : bool
        If true, each label is scored independently (probabilities need not sum to 1)...
    wait_for_model : bool
        If true, send x-wait-for-model so the server blocks until a cold model finish...
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
            "operation": operation,
            "model_id": model_id,
            "text": text,
            "candidate_labels": candidate_labels,
            "multi_label": multi_label,
            "wait_for_model": wait_for_model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HFInference_zero_shot_classify",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HFInference_zero_shot_classify"]
