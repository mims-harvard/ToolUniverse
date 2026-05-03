"""
SIMBAD_query_object

Query the SIMBAD astronomical database for information about celestial objects. Supports queries ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIMBAD_query_object(
    query_type: Optional[str] = "object_name",
    object_name: Optional[str] = None,
    ra: Optional[float] = None,
    dec: Optional[float] = None,
    radius: Optional[float] = 1.0,
    identifier: Optional[str] = None,
    output_format: Optional[str] = "basic",
    max_results: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Query the SIMBAD astronomical database for information about celestial objects. Supports queries ...

    Parameters
    ----------
    query_type : str
        Type of query to perform. Options: 'object_name' (search by name), 'coordinat...
    object_name : str
        Name of the astronomical object (e.g., 'M31', 'Sirius', 'NGC 1068'). Required...
    ra : float
        Right Ascension in degrees (0-360). Required when query_type='coordinates'
    dec : float
        Declination in degrees (-90 to +90). Required when query_type='coordinates'
    radius : float
        Search radius in arcminutes for coordinate queries. Default is 1.0 arcmin
    identifier : str
        Identifier pattern with wildcards (e.g., 'HD *', 'NGC 10*'). Required when qu...
    output_format : str
        Level of detail in output. Options: 'basic' (ID, coordinates, type), 'detaile...
    max_results : int
        Maximum number of results to return for coordinate or identifier queries
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
        k: v
        for k, v in {
            "query_type": query_type,
            "object_name": object_name,
            "ra": ra,
            "dec": dec,
            "radius": radius,
            "identifier": identifier,
            "output_format": output_format,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SIMBAD_query_object",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIMBAD_query_object"]
