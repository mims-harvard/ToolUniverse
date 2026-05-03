"""
EnsemblReg_get_constrained_elements

Get evolutionarily constrained elements in a genomic region from the Ensembl Compara database. Co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblReg_get_constrained_elements(
    region: str,
    species: Optional[str] = "homo_sapiens",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get evolutionarily constrained elements in a genomic region from the Ensembl Compara database. Co...

    Parameters
    ----------
    species : str
        Species name. Use 'homo_sapiens' for human. Default: 'homo_sapiens'.
    region : str
        Genomic region in format 'chromosome:start-end'. Example: '17:7661779-7687538...
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
        k: v for k, v in {"species": species, "region": region}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblReg_get_constrained_elements",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblReg_get_constrained_elements"]
