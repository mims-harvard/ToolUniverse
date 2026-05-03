"""
IEDB_predict_mhci_binding

Predict MHC class I peptide binding using NetMHCpan via the IEDB Analysis Resource API. Given a p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IEDB_predict_mhci_binding(
    sequence: str,
    allele: Optional[str] = "HLA-A*02:01",
    method: Optional[str] = "netmhcpan_el",
    length: Optional[int] = 9,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict MHC class I peptide binding using NetMHCpan via the IEDB Analysis Resource API. Given a p...

    Parameters
    ----------
    sequence : str
        Protein sequence (amino acid letters, e.g., 'TYQRTRALVFQRTRALKMFAL'). Multipl...
    allele : str
        MHC allele name. Human: 'HLA-A*02:01', 'HLA-B*07:02'. Mouse: 'H-2-Kd', 'H-2-D...
    method : str
        Prediction method. 'netmhcpan_el' (recommended, eluted ligand), 'netmhcpan_ba...
    length : int
        Peptide length (8-14 for MHC-I, typically 9)
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
        for k, v in {
            "sequence": sequence,
            "allele": allele,
            "method": method,
            "length": length,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IEDB_predict_mhci_binding",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IEDB_predict_mhci_binding"]
