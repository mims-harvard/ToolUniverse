# embedding_sync.py
"""
EmbeddingSync — thin wrapper over the modular HF sync helpers.

Upload:   pushes <collection>.db and <collection>.faiss to a HF dataset repo
Download: restores <local_name>.db and <local_name>.faiss from that repo
"""

import os
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime

from ..base_tool import BaseTool
from ..tool_registry import register_tool
from ..logging_config import get_logger

from huggingface_hub import whoami

from tooluniverse.database_setup.hf.sync_hf import (
    upload as hf_upload,
    download as hf_download,  # ensure you pulled the "rename-on-download" fix in sync_hf.py
    db_path_for_collection,
)
from tooluniverse.database_setup.sqlite_store import SQLiteStore
from tooluniverse.utils import get_user_cache_dir


def _collection_paths(name: str) -> Tuple[Path, Path]:
    db_path = db_path_for_collection(name)
    faiss_path = db_path.parent / f"{name}.faiss"
    return db_path, faiss_path


def _get_db_info(collection: str) -> Dict[str, Any]:
    db_path, _ = _collection_paths(collection)
    info = {
        "name": collection,
        "description": "",
        "embedding_model": None,
        "embedding_dimensions": None,
        "document_count": None,
        "created_at": None,
    }
    if not db_path.exists():
        return info
    try:
        store = SQLiteStore(db_path.as_posix())
        cur = store.conn.execute(
            "SELECT description, embedding_model, embedding_dimensions, created_at "
            "FROM collections WHERE name=?",
            (collection,),
        )
        row = cur.fetchone()
        if row:
            (
                info["description"],
                info["embedding_model"],
                info["embedding_dimensions"],
                info["created_at"],
            ) = row
        cur2 = store.conn.execute(
            "SELECT COUNT(1) FROM docs WHERE collection=?", (collection,)
        )
        info["document_count"] = int(cur2.fetchone()[0])
    except Exception:
        pass
    return info


@register_tool("EmbeddingSync")
class EmbeddingSync(BaseTool):
    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.logger = get_logger("EmbeddingSync")
        hf_cfg = tool_config.get("configs", {}).get("huggingface_config", {})
        self.hf_token = hf_cfg.get("token") or os.getenv("HF_TOKEN")
        self.hf_endpoint = hf_cfg.get("endpoint", "https://huggingface.co")

        storage_cfg = tool_config.get("configs", {}).get("storage_config", {})
        self.data_dir = Path(
            storage_cfg.get(
                "data_dir", os.path.join(get_user_cache_dir(), "embeddings")
            )
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def run(self, arguments: Dict[str, Any]):
        action = arguments.get("action")
        if action == "upload":
            return self._upload(arguments)
        elif action == "download":
            return self._download(arguments)
        return {"error": f"Unknown action: {action}"}

    # ---------------- Upload ----------------

    def _upload(self, args: Dict[str, Any]):
        collection = args.get("database_name")
        repo = args.get("repository")
        description = args.get("description", "")
        private = bool(args.get("private", True))
        commit_message = args.get("commit_message", f"Upload {collection} datastore")
        tool_json = args.get("tool_json")

        if not collection:
            return {"error": "database_name is required"}
        if not self.hf_token:
            return {"error": "HF_TOKEN is required in env or tool config"}
        # Default repo to <username>/<collection> if not provided
        if not repo:
            try:
                username = whoami(token=self.hf_token)["name"]
                repo = f"{username}/{collection}"
            except Exception as e:
                return {"error": f"Could not resolve HF username from HF_TOKEN: {e}"}

        db_path, faiss_path = _collection_paths(collection)
        if not db_path.exists():
            return {"error": f"Local DB not found: {db_path}"}
        if not faiss_path.exists():
            return {"error": f"FAISS index not found: {faiss_path}"}

        try:
            hf_upload(
                collection=collection,
                repo=repo,
                private=private,
                commit_message=commit_message,
                tool_json=tool_json,
            )
        except Exception as e:
            return {"error": f"Failed to upload: {e}"}

        info = _get_db_info(collection)
        return {
            "status": "success",
            "database_name": collection,
            "repository": repo,
            "document_count": info.get("document_count"),
            "embedding_model": info.get("embedding_model"),
            "embedding_dimensions": info.get("embedding_dimensions"),
            "description": description or info.get("description", ""),
            "upload_url": f"{self.hf_endpoint}/datasets/{repo}",
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
        }

    # ---------------- Download ----------------

    def _download(self, args: Dict[str, Any]):
        repo = args.get("repository")
        local_name = args.get("local_name") or (repo.split("/")[-1] if repo else None)
        overwrite = bool(args.get("overwrite", False))

        if not repo:
            return {"error": "repository is required (format: username/repo-name)"}
        if not local_name:
            return {"error": "local_name is required"}

        try:
            hf_download(repo=repo, collection=local_name, overwrite=overwrite)
        except Exception as e:
            return {"error": f"Failed to download: {e}"}

        # verify artifacts landed where we expect
        db_path, faiss_path = _collection_paths(local_name)
        missing = []
        if not db_path.exists():
            missing.append(str(db_path))
        if not faiss_path.exists():
            missing.append(str(faiss_path))
        if missing:
            return {
                "error": "Download completed but expected artifacts were not found locally",
                "missing": missing,
                "hint": "Ensure the HF repo contains '<original>.db' and '<original>.faiss'. "
                "The downloader copies/renames them to match 'local_name'.",
            }

        info = _get_db_info(local_name)
        return {
            "status": "success",
            "repository": repo,
            "local_name": local_name,
            "db_path": str(db_path),
            "index_path": str(faiss_path),
            "document_count": info.get("document_count"),
            "embedding_model": info.get("embedding_model"),
            "embedding_dimensions": info.get("embedding_dimensions"),
            "downloaded_at": datetime.utcnow().isoformat() + "Z",
        }
