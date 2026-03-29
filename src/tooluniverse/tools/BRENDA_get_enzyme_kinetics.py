"""
BRENDA_get_enzyme_kinetics

Get comprehensive enzyme kinetic parameters WITHOUT requiring BRENDA credentials. Retrieves enzym...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BRENDA_get_enzyme_kinetics(
    operation: Optional[str] = None,
    ec_number: Optional[str] = None,
    enzyme_name: Optional[str] = None,
    organism: Optional[str] = None,
    enzyme_id: Optional[str] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get comprehensive enzyme kinetic parameters WITHOUT requiring BRENDA credentials. Retrieves enzym...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_enzyme_kinetics)
    ec_number : str
        EC number (e.g., 1.1.1.1 for alcohol dehydrogenase, 2.7.1.1 for hexokinase, 3...
    enzyme_name : str
        Enzyme common name. Will be resolved to EC number via UniProt. Examples: alco...
    organism : str
        Optional organism filter (e.g., Homo sapiens, Escherichia coli, Saccharomyces...
    enzyme_id : str
        Alias for ec_number. Enzyme identifier in EC notation.
    limit : int | Any
        Maximum number of SABIO-RK kinetic law entries to retrieve (default 20)
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
            "ec_number": ec_number,
            "enzyme_name": enzyme_name,
            "organism": organism,
            "enzyme_id": enzyme_id,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BRENDA_get_enzyme_kinetics",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BRENDA_get_enzyme_kinetics"]
