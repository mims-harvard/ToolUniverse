"""
HFInference_fill_mask

Predict the most likely token(s) for a masked position using any HuggingFace fill-mask (masked-LM...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HFInference_fill_mask(
    operation: str,
    model_id: str,
    text: str,
    top_k: Optional[int] = None,
    wait_for_model: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Predict the most likely token(s) for a masked position using any HuggingFace fill-mask (masked-LM...

    Parameters
    ----------
    operation : str
        Operation selector (fixed).
    model_id : str
        HuggingFace repo id of a fill-mask model, e.g. 'google-bert/bert-base-uncased...
    text : str
        Input text containing exactly the model's mask token ([MASK] for BERT, <mask>...
    top_k : int
        Number of top candidate tokens to return (default model-dependent, typically 5).
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
            "top_k": top_k,
            "wait_for_model": wait_for_model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HFInference_fill_mask",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HFInference_fill_mask"]
