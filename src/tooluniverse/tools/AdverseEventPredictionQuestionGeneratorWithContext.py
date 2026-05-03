"""
AdverseEventPredictionQuestionGeneratorWithContext

Generates a set of personalized adverse‐event prediction questions for a given disease and drug, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AdverseEventPredictionQuestionGeneratorWithContext(
    disease_name: str,
    drug_name: str,
    context_information: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Generates a set of personalized adverse‐event prediction questions for a given disease and drug, ...

    Parameters
    ----------
    disease_name : str
        The name of the disease or condition
    drug_name : str
        The name of the drug
    context_information : str
        Additional context information such as patient medical history, clinical find...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "disease_name": disease_name,
            "drug_name": drug_name,
            "context_information": context_information,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AdverseEventPredictionQuestionGeneratorWithContext",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AdverseEventPredictionQuestionGeneratorWithContext"]
