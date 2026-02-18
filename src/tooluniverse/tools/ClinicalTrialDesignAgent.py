"""
ClinicalTrialDesignAgent

AI agent that designs clinical trial protocols based on preclinical data and regulatory requirements
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalTrialDesignAgent(
    drug_name: str,
    indication: str,
    preclinical_data: Optional[str] = "",
    target_population: Optional[str] = "General adult population",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    AI agent that designs clinical trial protocols based on preclinical data and regulatory requirements

    Parameters
    ----------
    drug_name : str
        Name of the drug candidate
    indication : str
        Disease indication
    preclinical_data : str
        Preclinical efficacy and safety data
    target_population : str
        Target patient population
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

    return get_shared_client().run_one_function(
        {
            "name": "ClinicalTrialDesignAgent",
            "arguments": {
                "drug_name": drug_name,
                "indication": indication,
                "preclinical_data": preclinical_data,
                "target_population": target_population,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalTrialDesignAgent"]
