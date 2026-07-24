"""
HFInference_embed_text

Generate a dense embedding vector for text using any HuggingFace feature-extraction model (server...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HFInference_embed_text(
    operation: str,
    model_id: str,
    text: str,
    wait_for_model: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generate a dense embedding vector for text using any HuggingFace feature-extraction model (server...

    Parameters
    ----------
    operation : str
        Operation selector (fixed).
    model_id : str
        HuggingFace repo id of an embedding / feature-extraction model, e.g. 'sentenc...
    text : str
        Input text to embed.
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
            "wait_for_model": wait_for_model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HFInference_embed_text",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HFInference_embed_text"]
