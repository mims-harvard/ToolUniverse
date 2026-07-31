"""
ThreeDBeacons_get_annotations

Get residue-level structural and functional annotations mapped onto a protein's 3D models from th...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ThreeDBeacons_get_annotations(
    accession: str,
    type_: Optional[str] = None,
    provider: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get residue-level structural and functional annotations mapped onto a protein's 3D models from th...

    Parameters
    ----------
    accession : str
        UniProt protein accession. Examples: 'P38398' (BRCA1), 'P04637' (TP53), 'P005...
    type_ : str
        Filter to one annotation type. Valid values: CARBOHYD, DOMAIN, ACT_SITE, META...
    provider : str
        Optional model provider to source annotations from: 'pdbe' or 'alphafold'.
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
            "accession": accession,
            "type": type_,
            "provider": provider,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ThreeDBeacons_get_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ThreeDBeacons_get_annotations"]
