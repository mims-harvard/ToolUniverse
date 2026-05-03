"""
OpenTargets_drug_pharmacogenomics_data

Retrieve pharmacogenomics data for a specific drug, including evidence levels and genotype annota...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_drug_pharmacogenomics_data(
    chemblId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve pharmacogenomics data for a specific drug, including evidence levels and genotype annota...

    Parameters
    ----------
    chemblId : str
        The ChEMBL ID of the drug (e.g., 'CHEMBL25' for aspirin, 'CHEMBL1201583' for ...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"chemblId": chemblId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_drug_pharmacogenomics_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_drug_pharmacogenomics_data"]
