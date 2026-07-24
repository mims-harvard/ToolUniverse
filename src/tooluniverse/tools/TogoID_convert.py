"""
TogoID_convert

Convert biological identifiers between databases using TogoID (DBCLS), which links 117 ID types (...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TogoID_convert(
    ids: str,
    source: str,
    target: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert biological identifiers between databases using TogoID (DBCLS), which links 117 ID types (...

    Parameters
    ----------
    ids : str
        Source identifier(s), comma-separated, in the source dataset's native format ...
    source : str
        Source TogoID dataset name, e.g. 'ensembl_gene', 'ncbigene', 'uniprot', 'pubc...
    target : str
        Target TogoID dataset name, e.g. 'uniprot', 'hgnc', 'chebi', 'pdb', 'ensembl_...
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
        for k, v in {"ids": ids, "source": source, "target": target}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TogoID_convert",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TogoID_convert"]
