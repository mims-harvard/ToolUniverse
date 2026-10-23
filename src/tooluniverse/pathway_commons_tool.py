"""Compatibility import for the historical Pathway Commons module path.

The maintained implementation lives in :mod:`tooluniverse.pathwaycommons_tool`.
Keeping a second registered class here made ``PathwayCommonsTool`` depend on
module import order and exposed an obsolete, truncating ``action`` API.  This
module intentionally performs no registration of its own.
"""

from .pathwaycommons_tool import PathwayCommonsTool

__all__ = ["PathwayCommonsTool"]
