"""
IEDB_predict_mhcii_binding

Predict MHC class II peptide binding using NetMHCIIpan via the IEDB Analysis Resource API. Predic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IEDB_predict_mhcii_binding(
    sequence: str,
    allele: Optional[str] = "HLA-DRB1*01:01",
    method: Optional[str] = "netmhciipan_el",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict MHC class II peptide binding using NetMHCIIpan via the IEDB Analysis Resource API. Predic...

    Parameters
    ----------
    sequence : str
        Protein sequence (amino acid letters)
    allele : str
        MHC-II allele. Examples: 'HLA-DRB1*01:01', 'HLA-DRB1*15:01'. Default: HLA-DRB...
    method : str
        Prediction method: 'netmhciipan_el' (recommended), 'netmhciipan_ba', 'nn_align'
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
    _args = {
        k: v
        for k, v in {"sequence": sequence, "allele": allele, "method": method}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IEDB_predict_mhcii_binding",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IEDB_predict_mhcii_binding"]
