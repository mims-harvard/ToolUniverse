"""
ProteinsPlus_predict_binding_sites

Predict druggable binding sites and pockets in protein structures using DoGSiteScorer algorithm. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteinsPlus_predict_binding_sites(
    pdb_id: Optional[str] = None,
    pdb_content: Optional[str] = None,
    chain: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict druggable binding sites and pockets in protein structures using DoGSiteScorer algorithm. ...

    Parameters
    ----------
    pdb_id : str
        PDB identifier (e.g., '1A2B', '4HHB'). Use either pdb_id or pdb_content, not ...
    pdb_content : str
        Raw PDB file content as string (multi-line text starting with 'HEADER'). Use ...
    chain : str
        Specific chain to analyze (e.g., 'A'). Optional - if not provided, all chains...
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
            "pdb_id": pdb_id,
            "pdb_content": pdb_content,
            "chain": chain,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProteinsPlus_predict_binding_sites",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteinsPlus_predict_binding_sites"]
