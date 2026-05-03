"""
UniProtIDMap_convert_ids

Convert protein/gene identifiers between databases using the UniProt ID Mapping service. Submits ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtIDMap_convert_ids(
    ids: str,
    from_db: str,
    to_db: Optional[str] = "UniProtKB",
    tax_id: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert protein/gene identifiers between databases using the UniProt ID Mapping service. Submits ...

    Parameters
    ----------
    ids : str
        Comma-separated identifiers to convert. Examples: 'TP53,BRCA1,EGFR' (gene nam...
    from_db : str
        Source database. Common values: 'Gene_Name', 'UniProtKB_AC-ID', 'Ensembl', 'E...
    to_db : str
        Target database. Common values: 'UniProtKB', 'UniProtKB-Swiss-Prot', 'Gene_Na...
    tax_id : int | Any
        NCBI Taxonomy ID to restrict results. Examples: 9606 (human), 10090 (mouse), ...
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
            "ids": ids,
            "from_db": from_db,
            "to_db": to_db,
            "tax_id": tax_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniProtIDMap_convert_ids",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtIDMap_convert_ids"]
