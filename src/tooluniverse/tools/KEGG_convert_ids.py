"""
KEGG_convert_ids

Convert KEGG gene/compound identifiers to external database IDs using the KEGG /conv API.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_convert_ids(
    kegg_id: str,
    target_db: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert KEGG gene/compound identifiers to external database IDs.

    Parameters
    ----------
    kegg_id : str
        KEGG entry ID (e.g., 'hsa:7157' for TP53, 'cpd:C00002' for ATP).
    target_db : str
        External database: 'uniprot', 'ncbi-geneid', 'ncbi-proteinid', 'chebi', 'pubchem'.
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
    _args = {
        k: v
        for k, v in {"kegg_id": kegg_id, "target_db": target_db}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_convert_ids",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_convert_ids"]
