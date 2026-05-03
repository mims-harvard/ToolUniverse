# embedding_database.py
import os
import hashlib
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from ..base_tool import BaseTool
from ..tool_registry import register_tool
from ..logging_config import get_logger

from tooluniverse.database_setup.sqlite_store import SQLiteStore
from tooluniverse.database_setup.vector_store import VectorStore
from tooluniverse.database_setup.embedder import Embedder
from tooluniverse.database_setup.provider_resolver import (
    resolve_provider as _resolve_provider,
    resolve_model as _resolve_model,
)
from tooluniverse.utils import get_user_cache_dir

# ---------------------------
# Misc helpers
# ---------------------------


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    return mat / (norms + 1e-12)


def _matches_filters(metadata: Dict, filters: Dict) -> bool:
    if not filters:
        return True
    for key, filter_value in filters.items():
        if key not in metadata:
            return False
        meta_value = metadata[key]
        if isinstance(filter_value, dict):
            if "$gte" in filter_value and meta_value < filter_value["$gte"]:
                return False
            if "$gt" in filter_value and meta_value <= filter_value["$gt"]:
                return False
            if "$lte" in filter_value and meta_value > filter_value["$lte"]:
                return False
            if "$lt" in filter_value and meta_value >= filter_value["$lt"]:
                return False
            if "$in" in filter_value and meta_value not in filter_value["$in"]:
                return False
            if "$contains" in filter_value:
                needle = filter_value["$contains"]
                if isinstance(meta_value, list):
                    if needle not in meta_value:
                        return False
                else:
                    if needle not in str(meta_value):
                        return False
        else:
            if meta_value != filter_value:
                return False
    return True


# ---------------------------
# Tool
# ---------------------------


@register_tool("EmbeddingDatabase")
class EmbeddingDatabase(BaseTool):
    """
    Exposes actions:
      - create_from_docs
      - add_docs
      - search
    Backed by SQLiteStore + VectorStore + Embedder.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.logger = get_logger("EmbeddingDatabase")

        storage_config = tool_config.get("configs", {}).get("storage_config", {})
        self.data_dir = Path(
            storage_config.get(
                "data_dir", os.path.join(get_user_cache_dir(), "embeddings")
            )
        )
        self.faiss_index_type = storage_config.get("faiss_index_type", "IndexFlatIP")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ---------- infra helpers (per collection) ----------

    def _paths(self, name: str) -> Tuple[Path, Path]:
        db_path = self.data_dir / f"{name}.db"
        index_path = self.data_dir / f"{name}.faiss"
        return db_path, index_path

    def _stores(self, name: str) -> Tuple[SQLiteStore, VectorStore, Path, Path]:
        db_path, index_path = self._paths(name)
        sqlite_store = SQLiteStore(db_path.as_posix())
        vector_store = VectorStore(
            db_path.as_posix(), data_dir=self.data_dir.as_posix()
        )
        return sqlite_store, vector_store, db_path, index_path

    def _embedder(self, provider: str, model: str) -> Embedder:
        return Embedder(
            provider=provider,
            model=model,
            batch_size=100 if provider in ("openai", "azure") else 32,
            max_retries=5,
        )

    def _get_collection_meta(
        self, store: SQLiteStore, name: str
    ) -> Tuple[Optional[str], Optional[int]]:
        cur = store.conn.execute(
            "SELECT embedding_model, embedding_dimensions FROM collections WHERE name=? LIMIT 1",
            (name,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)

    def _existing_vector_doc_ids(
        self, vs: VectorStore, collection: str, doc_ids: List[int]
    ) -> set:
        if not doc_ids:
            return set()
        placeholders = ",".join("?" for _ in doc_ids)
        q = f"SELECT doc_id FROM vectors WHERE collection=? AND doc_id IN ({placeholders})"
        args = [collection] + doc_ids
        cur = vs.db.execute(q, args)
        return {r[0] for r in cur.fetchall()}

    @staticmethod
    def _validate_doc_args(
        args: Dict[str, Any],
    ) -> Tuple[Optional[Dict], str, List[str], List[Dict[str, Any]]]:
        """Validate and extract common arguments for document operations.

        Returns (error_dict, name, docs, metas) where error_dict is None on success.
        """
        name = args.get("database_name")
        docs: List[str] = args.get("documents", [])
        metas: List[Dict[str, Any]] = args.get("metadata", [])

        if not name:
            return {"error": "database_name is required"}, "", [], []
        if not docs:
            return {"error": "documents list cannot be empty"}, "", [], []
        if metas and len(metas) != len(docs):
            return (
                {
                    "error": "metadata length must match documents length (or omit 'metadata')"
                },
                "",
                [],
                [],
            )
        if not metas:
            metas = [{} for _ in docs]
        return None, name, docs, metas

    @staticmethod
    def _build_doc_rows(
        docs: List[str], metas: List[Dict[str, Any]]
    ) -> Tuple[List[Tuple], List[str]]:
        """Build (doc_key, text, meta, text_hash) rows and the corresponding key list."""
        rows = []
        doc_keys: List[str] = []
        for text, meta in zip(docs, metas):
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            doc_keys.append(text_hash)
            rows.append((text_hash, text, meta, text_hash))
        return rows, doc_keys

    # ---------------- entry point ----------------
    def run(self, arguments):
        action = arguments.get("action")
        if action == "create_from_docs":
            return self._create_from_documents(arguments)
        elif action == "add_docs":
            return self._add_documents(arguments)
        elif action == "search":
            return self._search(arguments)
        else:
            return {"error": f"Unknown action: {action}"}

    # ---------------- actions ----------------

    def _create_from_documents(self, args: Dict[str, Any]):
        error, name, docs, metas = self._validate_doc_args(args)
        if error:
            return error

        provider = _resolve_provider(args.get("provider"))
        model = _resolve_model(provider, args.get("model"))
        description = args.get("description", "")

        sqlite_store, vector_store, db_path, index_path = self._stores(name)

        if index_path.exists():
            return {
                "error": f"Database '{name}' already exists. Use 'add_docs' to add more documents."
            }

        rows, doc_keys = self._build_doc_rows(docs, metas)

        sqlite_store.upsert_collection(
            name,
            description=description,
            embedding_model="precomputed",  # placeholder until we write vectors
            embedding_dimensions=None,
            index_type=self.faiss_index_type,
        )
        sqlite_store.insert_docs(name, rows)

        # Map keys -> ids
        inserted = sqlite_store.fetch_docs(name, doc_keys=doc_keys, limit=len(rows))
        doc_ids = [r["id"] for r in inserted]

        # Embed + add to FAISS
        vecs = self._embedder(provider, model).embed(docs)
        vecs = _l2_normalize(np.asarray(vecs, dtype="float32"))

        vector_store.load_index(name, dim=vecs.shape[1])
        vector_store.add_embeddings(name, doc_ids, vecs)

        # Update collection with the real model + dimension
        sqlite_store.upsert_collection(
            name,
            description=description,
            embedding_model=model,
            embedding_dimensions=int(vecs.shape[1]),
            index_type=self.faiss_index_type,
        )

        self.logger.info(f"Created collection '{name}' with {len(docs)} docs")
        return {
            "status": "success",
            "database_name": name,
            "documents_added": len(docs),
            "embedding_model": model,
            "dimensions": int(vecs.shape[1]),
            "db_path": str(db_path),
            "index_path": str(index_path),
        }

    def _add_documents(self, args: Dict[str, Any]):
        error, name, docs, metas = self._validate_doc_args(args)
        if error:
            return error

        provider = _resolve_provider(args.get("provider"))
        model_override = args.get("model")

        sqlite_store, vector_store, db_path, index_path = self._stores(name)
        if not index_path.exists() or not db_path.exists():
            return {
                "error": f"Database '{name}' does not exist. Use 'create_from_docs' first."
            }

        col_model, col_dim = self._get_collection_meta(sqlite_store, name)
        if col_model in (None, "precomputed"):
            col_model = _resolve_model(provider, model_override)
        elif model_override and model_override != col_model:
            return {
                "error": f"Embedding model mismatch: collection uses '{col_model}', request uses '{model_override}'"
            }

        emb = self._embedder(provider, col_model)

        rows, doc_keys = self._build_doc_rows(docs, metas)

        # Insert (duplicates ignored by UNIQUE constraints)
        sqlite_store.insert_docs(name, rows)

        # Map keys -> ids
        inserted = sqlite_store.fetch_docs(name, doc_keys=doc_keys, limit=len(rows))
        key_to_id = {r["doc_key"]: r["id"] for r in inserted}
        doc_ids_all = [key_to_id[k] for k in doc_keys if k in key_to_id]

        # Compute embeddings once
        vecs_all = emb.embed(docs)
        vecs_all = _l2_normalize(np.asarray(vecs_all, dtype="float32"))

        if col_dim and col_dim != vecs_all.shape[1]:
            return {
                "error": f"Embedding dimension mismatch: {col_dim} vs {vecs_all.shape[1]}"
            }

        # Filter out doc_ids that already have vectors
        existing = self._existing_vector_doc_ids(vector_store, name, doc_ids_all)
        doc_ids_to_add: List[int] = []
        vecs_to_add: List[np.ndarray] = []
        for i, k in enumerate(doc_keys):
            did = key_to_id.get(k)
            if did is not None and did not in existing:
                doc_ids_to_add.append(did)
                vecs_to_add.append(vecs_all[i])

        # Load index, add only the missing ones
        index = vector_store.load_index(name, dim=col_dim or vecs_all.shape[1])
        before = index.ntotal

        if doc_ids_to_add:
            vecs_to_add_arr = np.vstack(vecs_to_add).astype("float32")
            vector_store.add_embeddings(name, doc_ids_to_add, vecs_to_add_arr)

        after = before + len(doc_ids_to_add)
        return {
            "status": "success",
            "database_name": name,
            "documents_added": len(doc_ids_to_add),
            "skipped_existing": len(docs) - len(doc_ids_to_add),
            "total_vectors": after,
            "db_path": str(db_path),
            "index_path": str(index_path),
        }

    def _search(self, args: Dict[str, Any]):
        name = args.get("database_name")
        query = args.get("query")
        top_k = int(args.get("top_k", 5))
        filters = args.get("filters", args.get("metadata_filter", {}))
        provider = _resolve_provider(args.get("provider"))
        model_override = args.get("model")

        if not name:
            return {"error": "database_name is required"}
        if not query:
            return {"error": "query is required"}

        sqlite_store, vector_store, db_path, index_path = self._stores(name)
        if not index_path.exists() or not db_path.exists():
            return {"error": f"Database '{name}' does not exist"}

        col_model, col_dim = self._get_collection_meta(sqlite_store, name)
        # pick model for query embedding
        model = (
            model_override or (None if col_model == "precomputed" else col_model)
        ) or _resolve_model(provider, None)
        emb = self._embedder(provider, model)

        # Embed query
        q = emb.embed([query])
        q = _l2_normalize(np.asarray(q, dtype="float32"))
        qdim = int(q.shape[1])
        if col_dim and col_dim != qdim:
            return {"error": f"Embedding dimension mismatch: {col_dim} vs {qdim}"}

        # Search
        vector_store.load_index(name, dim=col_dim or qdim)
        results = vector_store.search_embeddings(name, q[0], top_k=top_k)

        # Hydrate + filter
        doc_ids = [doc_id for doc_id, _ in results]
        docs = sqlite_store.fetch_docs_by_ids(name, doc_ids)
        doc_map = {d["id"]: d for d in docs}

        out = []
        for doc_id, score in results:
            d = doc_map.get(doc_id)
            if not d:
                continue
            md = d.get("metadata") or {}
            if _matches_filters(md, filters):
                out.append(
                    {
                        "text": d["text"],
                        "metadata": md,
                        "similarity_score": float(score),
                    }
                )

        return {
            "status": "success",
            "database_name": name,
            "query": query,
            "results": out[:top_k],
            "total_found": len(out),
        }
