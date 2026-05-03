"""
Hugging Face sync utilities for SQLite + FAISS datastore artifacts.

Artifacts
---------
- <collection>.db     : SQLite content store (docs, FTS5 mirror, metadata)
- <collection>.faiss  : FAISS index (IndexFlatIP), sibling to the DB under the user cache dir (<user_cache_dir>/embeddings)

Public API
----------
db_path_for_collection(collection) -> Path
    Resolve the on-disk SQLite path for a collection.

upload(collection, repo=None, private=True, commit_message="Update", tool_json=None)
    Create/ensure a HF dataset repo and upload <collection>.db/.faiss, plus optional tool JSON file(s).

download(repo, collection, overwrite=False, include_tools=False)
    Download *.db/*.faiss from a HF dataset repo snapshot (and optionally any *.json tool files) and restores
    them under the user cache dir (<user_cache_dir>/embeddings) as <collection>.db/.faiss.

Notes
-----
- Requires HF_TOKEN (env or HF cache) for private repos or authenticated uploads.
- Upload streams large files; download uses tooluniverse.utils.download_from_hf.
- Existing local files are preserved unless overwrite=True.
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import HfApi, whoami, get_token
from tooluniverse.utils import download_from_hf
from tooluniverse.utils import get_user_cache_dir  # ensure imported for DATA_DIR setup

# Always load .env if present
load_dotenv()

DATA_DIR = Path(
    os.environ.get("TU_DATA_DIR", os.path.join(get_user_cache_dir(), "embeddings"))
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------
# Helpers
# ---------------------------


def db_path_for_collection(collection: str) -> Path:
    """Return the absolute path for the user cache dir (<user_cache_dir>/embeddings/<collection>.db)."""
    return DATA_DIR / f"{collection}.db"


def get_hf_api():
    """Return an authenticated (HfApi, token) tuple."""
    token = os.getenv("HF_TOKEN") or get_token()
    if not token:
        raise RuntimeError("HF_TOKEN not set in environment or .env file")
    return HfApi(token=token), token


# ---------------------------
# Upload
# ---------------------------


def upload(
    collection: str,
    repo: str = None,
    private: bool = True,
    commit_message: str = "Update",
    tool_json: list[str] | None = None,
):
    """Upload a collection’s DB and FAISS index (and optional tool JSON file(s)) to the user’s own HF account."""
    api, token = get_hf_api()
    username = whoami(token=token)["name"]

    # Default to user's own namespace if not provided
    if repo is None:
        repo = f"{username}/{collection}"
        print(f"No repo specified — using default: {repo}")

    api.create_repo(
        repo_id=repo, repo_type="dataset", private=private, exist_ok=True, token=token
    )

    # Upload SQLite DB
    db_path = db_path_for_collection(collection)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    api.upload_file(
        path_or_fileobj=str(db_path),
        path_in_repo=f"{collection}.db",
        repo_id=repo,
        repo_type="dataset",
        commit_message=commit_message,
        token=token,
    )

    # Upload FAISS index
    faiss_path = DATA_DIR / f"{collection}.faiss"
    if faiss_path.exists():
        api.upload_file(
            path_or_fileobj=str(faiss_path),
            path_in_repo=f"{collection}.faiss",
            repo_id=repo,
            repo_type="dataset",
            commit_message=commit_message,
            token=token,
        )
    else:
        print(f"No FAISS index found for {collection}")

    # upload tool JSON(s), if provided
    if tool_json:
        for p in tool_json:
            src = Path(p).expanduser().resolve()
            if not src.exists() or not src.is_file():
                raise FileNotFoundError(f"--tool-json not found or not a file: {src}")
            api.upload_file(
                path_or_fileobj=str(src),
                path_in_repo=src.name,  # place at repo root by basename
                repo_id=repo,
                repo_type="dataset",
                commit_message=commit_message,
                token=token,
            )

    print(f"Uploaded {collection} to HF repo {repo}")


# ---------------------------
# Download (via utils.download_from_hf)
# ---------------------------


def _download_one(
    repo: str, filename: str, local_target: Path, overwrite: bool = False
):
    """
    Helper to fetch one file (DB or FAISS) using tooluniverse.utils.download_from_hf.
    Returns tuple: (success: bool, path: Path) where success indicates actual download occurred.
    """

    token = os.getenv("HF_TOKEN") or get_token() or ""
    cfg = {
        "hf_dataset_path": {
            "repo_id": repo,
            "path_in_repo": filename,
            "save_to_local_dir": str(DATA_DIR),
            "token": token,
        }
    }

    # Track if file existed before download (to detect cache fallback)
    file_existed_before = local_target.exists()
    mtime_before = local_target.stat().st_mtime if file_existed_before else None

    res = download_from_hf(cfg)
    if not res.get("success"):
        error_msg = res.get('error', 'Unknown error')
        # Make error message more helpful
        if "Repository Not Found" in error_msg or "404" in error_msg:
            error_msg = f"Repository '{repo}' not found on HuggingFace. Check that the repo exists and the name is correct. Error: {error_msg}"
        raise RuntimeError(f"Failed to download {filename}: {error_msg}")

    downloaded_path = Path(res["local_path"])
    if downloaded_path.resolve() == local_target.resolve():
        # Check if file was actually updated from HF or just returned from local cache
        # Even with overwrite=True, hf_hub_download may fall back to cache if repo doesn't exist
        if file_existed_before:
            mtime_after = local_target.stat().st_mtime
            # If mtime didn't change, HF fell back to cache (repo is unreachable/doesn't exist)
            if mtime_after == mtime_before:
                if not overwrite:
                    print(f" {local_target.name} already exists. Skipping (use --overwrite).")
                else:
                    print(f" [WARNING] Repository '{repo}' is unreachable. Using local cache for {local_target.name}.")
                return False, local_target  # file was not downloaded, using local cache
        return True, local_target  # successfully downloaded to correct location

    if local_target.exists() and not overwrite:
        print(f" {local_target.name} already exists. Skipping (use --overwrite).")
        return False, local_target  # file was not downloaded, using local cache

    shutil.copyfile(downloaded_path, local_target)
    return True, local_target  # successfully downloaded and copied


# def download(repo: str, collection: str, overwrite: bool = False, include_tools: bool = False):
# """Download <collection>.db and <collection>.faiss using the unified helper."""
# dest_db = db_path_for_collection(collection)
# dest_faiss = DATA_DIR / f"{collection}.faiss"
# dest_tool = anything.json
# if include_tools:
# Download tool
# try:
# file_path = _download_one(repo, f"{.endswith}.db", dest_tool, overwrite)
#    print(f" Restored {file_path.name} from {repo}")
# except Exception as e:
#    print(f" Failed to download file: {e}")
#     return

# Download DB
# try:
#   db_path = _download_one(repo, f"{collection}.db", dest_db, overwrite)
#  print(f" Restored {db_path.name} from {repo}")
# except Exception as e:
#  print(f" Failed to download DB: {e}")
#  return

# Download FAISS (optional)
# try:
#  faiss_path = _download_one(repo, f"{collection}.faiss", dest_faiss, overwrite)
#  print(f" Restored {faiss_path.name} from {repo}")
# except Exception as e:
#    print(f" No FAISS index found or failed to download: {e}")

# print(f" Download complete for {collection} from {repo}")


def download(
    repo: str, collection: str, overwrite: bool = False, include_tools: bool = False
):
    """Download <collection>.db and <collection>.faiss (and optionally any .json tool files) using the unified helper."""
    dest_db = db_path_for_collection(collection)
    dest_faiss = DATA_DIR / f"{collection}.faiss"

    download_succeeded = False

    print(f" Downloading from {repo} into {DATA_DIR}...")

    # -------------------------------------------------
    # (1) Optionally fetch tool JSONs (*.json)
    # -------------------------------------------------
    if include_tools:
        token = os.getenv("HF_TOKEN") or get_token()
        api = HfApi(token=token) if token else HfApi()

        try:
            # list all files in the dataset repo
            files = api.list_repo_files(repo_id=repo, repo_type="dataset")
            for filename in files:
                if filename.endswith(".json"):
                    target_path = DATA_DIR / filename
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        success, _ = _download_one(repo, filename, target_path, overwrite)
                        if success:
                            print(f" Restored tool file: {filename}")
                        else:
                            print(f" Using cached tool file: {filename}")
                    except Exception as e:
                        print(f" Skipped {filename}: {e}")
        except Exception as e:
            print(f" Failed to list or download tool JSONs: {e}")

    # -------------------------------------------------
    # (2) Download the DB
    # -------------------------------------------------
    try:
        db_success, db_path = _download_one(repo, f"{collection}.db", dest_db, overwrite)
        if db_success:
            print(f" Restored {db_path.name} from {repo}")
            download_succeeded = True
        else:
            print(f" Using cached {db_path.name}")
    except Exception as e:
        print(f" Failed to download DB: {e}")
        return

    # -------------------------------------------------
    # (3) Download the FAISS index
    # -------------------------------------------------
    try:
        faiss_success, faiss_path = _download_one(repo, f"{collection}.faiss", dest_faiss, overwrite)
        if faiss_success:
            print(f" Restored {faiss_path.name} from {repo}")
        else:
            print(f" Using cached {faiss_path.name}")
    except Exception as e:
        print(f" No FAISS index found or failed to download: {e}")

    if download_succeeded:
        print(f"Download complete for {collection} from {repo}")
    else:
        print(f"Download complete for {collection} from {repo} (using cached files)")


# ---------------------------
# Entrypoint
# ---------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync datastore collections with Hugging Face Hub"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Upload
    up = subparsers.add_parser("upload", help="Upload a collection to HF Hub")
    up.add_argument(
        "--collection", required=True, help="Collection name (e.g., euhealth, demo)"
    )
    up.add_argument(
        "--repo",
        required=False,
        help="HF dataset repo ID (default: <your_username>/<collection> based on HF_TOKEN)",
    )
    up.add_argument(
        "--repo",
        required=False,
        help="HF dataset repo ID (default: <your_username>/<collection> based on HF_TOKEN)",
    )
    up.add_argument(
        "--private",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Make repo private (default: True). Use --no-private to make it public.",
    )
    up.add_argument(
        "--commit_message", default="Update", help="Commit message for upload"
    )
    up.add_argument(
        "--tool-json",
        nargs="*",
        default=None,
        help="Path(s) to Tool JSON file(s) to upload with the datastore.",
    )

    # Download
    down = subparsers.add_parser("download", help="Download a collection from HF Hub")
    down.add_argument("--repo", required=True, help="HF dataset repo ID")
    down.add_argument(
        "--collection",
        required=True,
        help="Local collection name (e.g., euhealth, demo)",
    )
    down.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing local DB/FAISS"
    )
    down.add_argument(
        "--include-tools",
        action="store_true",
        help="Also download any *.json tool files",
    )

    args = parser.parse_args()

    if args.command == "upload":
        upload(
            collection=args.collection,
            repo=args.repo,
            private=args.private,
            commit_message=args.commit_message,
            tool_json=args.tool_json,
        )
    elif args.command == "download":
        download(
            repo=args.repo,
            collection=args.collection,
            overwrite=args.overwrite,
            include_tools=args.include_tools,
        )
    else:
        parser.print_help()
