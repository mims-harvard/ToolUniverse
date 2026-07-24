"""
iDigBio_search_media

Search the iDigBio specimen MEDIA index (specimen photographs and scans) for a Darwin Core query....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iDigBio_search_media(
    scientificname: Optional[str] = None,
    genus: Optional[str] = None,
    family: Optional[str] = None,
    country: Optional[str] = None,
    stateprovince: Optional[str] = None,
    recordedby: Optional[str] = None,
    catalognumber: Optional[str] = None,
    collectioncode: Optional[str] = None,
    phylum: Optional[str] = None,
    class_: Optional[str] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the iDigBio specimen MEDIA index (specimen photographs and scans) for a Darwin Core query....

    Parameters
    ----------
    scientificname : str
        Full scientific name, e.g. 'Puma concolor'.
    genus : str
        Genus, e.g. 'Puma'.
    family : str
        Family name.
    country : str
        Country, e.g. 'United States'.
    stateprovince : str
        State/province.
    recordedby : str
        Collector name.
    catalognumber : str
        Catalog number.
    collectioncode : str
        Collection code.
    phylum : str
        Phylum.
    class_ : str
        Class.
    order : str
        Order.
    limit : int
        Max media records (default 10, max 100).
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
            "scientificname": scientificname,
            "genus": genus,
            "family": family,
            "country": country,
            "stateprovince": stateprovince,
            "recordedby": recordedby,
            "catalognumber": catalognumber,
            "collectioncode": collectioncode,
            "phylum": phylum,
            "class": class_,
            "order": order,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iDigBio_search_media",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iDigBio_search_media"]
