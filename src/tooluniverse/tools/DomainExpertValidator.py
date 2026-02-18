"""
DomainExpertValidator

Provides domain-specific validation and expert recommendations for tools with deep expertise acro...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DomainExpertValidator(
    tool_config: str,
    domain: str,
    validation_aspects: Optional[str] = '["accuracy", "methodology", "best-practices"]',
    implementation_code: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Provides domain-specific validation and expert recommendations for tools with deep expertise acro...

    Parameters
    ----------
    tool_config : str
        JSON string of tool configuration to validate
    domain : str
        Domain expertise area for validation
    validation_aspects : str
        JSON array string of specific aspects to validate
    implementation_code : str
        Implementation code to validate (optional)
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
            "name": "DomainExpertValidator",
            "arguments": {
                "tool_config": tool_config,
                "domain": domain,
                "validation_aspects": validation_aspects,
                "implementation_code": implementation_code,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DomainExpertValidator"]
