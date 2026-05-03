"""
EmbeddingCollectionSearchTool — search any datastore collection by name.

Configuration (tool_config.fields)
----------------------------------
- collection : str   (required)  e.g., "my_collection"
- db_path    : str   (optional)  e.g., "<user_cache_dir>/embeddings/my_collection.db"
                                 If omitted, defaults to: <user_cache_dir>/embeddings/<collection>.db
"""

from typing import Any, Dict
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool
from tooluniverse.database_setup.search import SearchEngine
from tooluniverse.utils import get_user_cache_dir
import os


@register_tool("EmbeddingCollectionSearchTool")
class EmbeddingCollectionSearchTool(BaseTool):
    """
    Generic search tool for any embedding datastore collection.

    Runtime arguments
    -----------------
    query  : str (required)
        Search query text.
    method : str = "hybrid"
        One of: "keyword", "embedding", "hybrid".
    top_k  : int = 10
        Number of results to return.
    alpha  : float = 0.5
        Balance for hybrid search (0=keyword only, 1=embedding only).

    Returns
    -------
    List[dict] with keys:
      - doc_id
      - doc_key
      - text
      - metadata
      - score
      - snippet (first ~280 chars)
    """

    def run(self, arguments: Dict[str, Any]) -> Any:
        fields = self.tool_config.get("fields") or {}
        coll = fields.get("collection")
        if not coll:
            return {"error": "Missing fields.collection in tool config"}

        q = arguments.get("query")
        if not q:
            return {"error": "Missing 'query' argument"}

        method = arguments.get("method", "hybrid")
        top_k = int(arguments.get("top_k", 10))
        alpha = float(arguments.get("alpha", 0.5))

        # Allow explicit db path; default to user cache dir ~/Library/Caches/.../embeddings/<collection>.db
        if fields.get("db_path"):
            db_path = fields["db_path"]
        else:
            db_path = os.path.join(get_user_cache_dir(), "embeddings", f"{coll}.db")

        se = getattr(self, "_se", None) or SearchEngine(db_path=db_path)

        try:
            res = se.search_collection(coll, q, method=method, top_k=top_k, alpha=alpha)
            for r in res:
                r["snippet"] = (r.get("text") or "")[:280]
            return res
        except Exception as e:
            return {
                "error": f"search failed: {e}",
                "collection": coll,
                "db_path": db_path,
            }
