"""
HFInference_summarize

Summarize a passage of text using any HuggingFace summarization model (serverless hf-inference pr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HFInference_summarize(
    operation: str,
    model_id: str,
    text: str,
    max_length: Optional[int] = None,
    min_length: Optional[int] = None,
    wait_for_model: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Summarize a passage of text using any HuggingFace summarization model (serverless hf-inference pr...

    Parameters
    ----------
    operation : str
        Operation selector (fixed).
    model_id : str
        HuggingFace repo id of a summarization model, e.g. 'facebook/bart-large-cnn' ...
    text : str
        Input text / article to summarize.
    max_length : int
        Maximum length of the generated summary, in tokens (model-dependent default).
    min_length : int
        Minimum length of the generated summary, in tokens (model-dependent default).
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
            "max_length": max_length,
            "min_length": min_length,
            "wait_for_model": wait_for_model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HFInference_summarize",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HFInference_summarize"]
