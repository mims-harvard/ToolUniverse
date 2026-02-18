"""
NvidiaNIM_vista3d

3D medical image segmentation using VISTA-3D via NVIDIA NIM. Segment organs and structures from C...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_vista3d(
    image: str,
    prompts: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    3D medical image segmentation using VISTA-3D via NVIDIA NIM. Segment organs and structures from C...

    Parameters
    ----------
    image : str
        URL to NIfTI or NRRD CT image file
    prompts : dict[str, Any]
        Segmentation prompts: classes and optional point coordinates
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

    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_vista3d",
            "arguments": {"image": image, "prompts": prompts},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_vista3d"]
