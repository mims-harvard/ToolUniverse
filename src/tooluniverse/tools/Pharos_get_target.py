"""
Pharos_get_target

Get detailed drug target information from Pharos/TCRD by gene symbol or UniProt ID. Returns Targe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pharos_get_target(
    gene: Optional[str] = None,
    uniprot: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed drug target information from Pharos/TCRD by gene symbol or UniProt ID. Returns Targe...

    Parameters
    ----------
    gene : str
        Gene symbol (e.g., 'EGFR', 'TP53', 'BRCA1'). Use either gene or uniprot.
    uniprot : str
        UniProt accession (e.g., 'P00533'). Use either gene or uniprot.
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
        k: v for k, v in {"gene": gene, "uniprot": uniprot}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pharos_get_target",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pharos_get_target"]
