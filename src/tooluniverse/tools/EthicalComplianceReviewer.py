"""
EthicalComplianceReviewer

Checks adherence to ethical standards and disclosure practices.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EthicalComplianceReviewer(
    ethics_section: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Checks adherence to ethical standards and disclosure practices.

    Parameters
    ----------
    ethics_section : str

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
            "name": "EthicalComplianceReviewer",
            "arguments": {"ethics_section": ethics_section},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EthicalComplianceReviewer"]
