"""
SABIO_RK_search_reactions

Search SABIO-RK database for biochemical reaction kinetic parameters. Returns Km, kcat, Vmax, Ki ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SABIO_RK_search_reactions(
    operation: Optional[str] = None,
    ec_number: Optional[str] = None,
    enzyme_name: Optional[str] = None,
    substrate: Optional[str] = None,
    organism: Optional[str] = None,
    product: Optional[str] = None,
    parameter_type: Optional[str] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search SABIO-RK database for biochemical reaction kinetic parameters. Returns Km, kcat, Vmax, Ki ...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_reactions)
    ec_number : str
        EC number (e.g., 1.1.1.1 for alcohol dehydrogenase, 2.7.1.1 for hexokinase)
    enzyme_name : str
        Enzyme common name (e.g., alcohol dehydrogenase, hexokinase, lactate dehydrog...
    substrate : str
        Substrate name (e.g., ethanol, glucose, ATP)
    organism : str
        Organism name (e.g., Homo sapiens, Escherichia coli, Saccharomyces cerevisiae)
    product : str
        Product name (e.g., acetaldehyde, pyruvate)
    parameter_type : str
        Filter by kinetic parameter type (e.g., Km, kcat, Vmax, Ki)
    limit : int | Any
        Maximum number of kinetic laws to return (default 20, max 100)
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
            "substrate": substrate,
            "organism": organism,
            "product": product,
            "parameter_type": parameter_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SABIO_RK_search_reactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SABIO_RK_search_reactions"]
