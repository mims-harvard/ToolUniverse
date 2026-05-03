"""
tu-datastore: CLI for building, searching, syncing, and registering embedding datastores and tools.

Subcommands
-----------
build
    Upsert a collection, insert documents (with de-dup), embed texts, and write FAISS.

quickbuild
    Build a collection from a folder of text files (.txt/.md).

search
    Query an existing collection by keyword, embedding, or hybrid.

sync-hf upload|download
    Upload/download <collection>.db and <collection>.faiss to/from Hugging Face and
    (on upload) optionally include --tool-json <file1.json> [file2.json ...].

add-tool
    Copy a tool JSON into ~/.tooluniverse/data/user_tools for auto-loading by
    ToolUniverse and Codex. This enables users to create their own tools from
    local JSON definitions without modifying the ToolUniverse repo.

Environment
-----------
Set EMBED_PROVIDER, EMBED_MODEL, and provider-specific keys (OPENAI / AZURE_* / HF_TOKEN).
All datastore files default to <user_cache_dir>/embeddings/<collection>.db unless overridden.

Exit codes
----------
0 on success; non-zero on I/O, validation, or runtime errors.
"""

import argparse
import json
import os
import shutil
from pathlib import Path
from .pipeline import build_collection, search
from .hf.sync_hf import upload as sync_upload, download as sync_download
from .packager import pack_folder
from tooluniverse.utils import get_user_cache_dir


def resolve_db_path(db_arg, collection):
    """Return resolved db path (user-specified or default cache dir)."""
    if db_arg:
        return os.path.expanduser(db_arg)
    default_db_dir = os.path.join(get_user_cache_dir(), "embeddings")
    os.makedirs(default_db_dir, exist_ok=True)
    return os.path.join(default_db_dir, f"{collection}.db")


def resolve_provider_model(provider_arg, model_arg):
    """Use CLI args or fall back to environment variables."""
    provider = provider_arg or os.getenv("EMBED_PROVIDER")
    model = model_arg or os.getenv("EMBED_MODEL")
    if not provider or not model:
        raise SystemExit(
            "Missing embedding provider or model. "
            "Use --provider/--model or set EMBED_PROVIDER/EMBED_MODEL in your .env."
        )
    return provider, model


USER_TOOLS_DIR = os.path.expanduser("~/.tooluniverse/data/user_tools")


def add_tool(json_file: str, name: str | None = None, overwrite: bool = False):
    """Copy a tool JSON into ~/.tooluniverse/data/user_tools for auto-loading."""
    src = Path(json_file).expanduser()
    if not src.exists() or not src.is_file():
        raise SystemExit(f"[ERROR] Tool JSON not found: {src}")

    os.makedirs(USER_TOOLS_DIR, exist_ok=True)

    if name is None:
        name = src.name
    if not name.endswith(".json"):
        name = name + ".json"

    dest = Path(USER_TOOLS_DIR) / name
    if dest.exists() and not overwrite:
        raise SystemExit(
            f"[ERROR] A tool file named '{name}' already exists at {dest}.\n"
            f"Use --overwrite if you want to replace it."
        )

    shutil.copyfile(src, dest)
    print(f"[INFO] Copied tool JSON to: {dest}")
    print(
        "[INFO] Any ToolUniverse/Codex instance that reads ~/.tooluniverse/data/user_tools will now see this tool."
    )


def main():
    p = argparse.ArgumentParser(
        "tu-datastore", description="Manage local searchable datastores."
    )
    sub = p.add_subparsers(dest="cmd")

    # --------------------------------------------------------------------------
    # build
    # --------------------------------------------------------------------------
    b = sub.add_parser("build", help="Build or extend a collection from JSON docs")
    b.add_argument("--collection", required=True, help="Collection name (e.g. toy)")
    b.add_argument("--docs-json", required=True, help="Path to JSON list of docs")
    b.add_argument("--db", required=False, help="Optional path to SQLite DB")
    b.add_argument(
        "--provider", help="Embedding provider (openai, azure, huggingface, local)"
    )
    b.add_argument("--model", help="Embedding model name or deployment")
    b.add_argument(
        "--overwrite", action="store_true", help="Rebuild FAISS index if exists"
    )

    # --------------------------------------------------------------------------
    # quickbuild
    # --------------------------------------------------------------------------
    qb = sub.add_parser(
        "quickbuild", help="Build from a folder of text files (.txt/.md)"
    )
    qb.add_argument("--name", required=True, help="Collection name (e.g. mydata)")
    qb.add_argument("--from-folder", required=True, help="Folder containing text files")
    qb.add_argument(
        "--provider", help="Embedding provider (openai, azure, huggingface, local)"
    )
    qb.add_argument("--model", help="Embedding model name or deployment")
    qb.add_argument(
        "--overwrite", action="store_true", help="Rebuild FAISS index if exists"
    )

    # --------------------------------------------------------------------------
    # search
    # --------------------------------------------------------------------------
    s = sub.add_parser("search", help="Query an existing collection")
    s.add_argument("--collection", required=True, help="Collection name (e.g. toy)")
    s.add_argument("--query", required=True, help="Search query text")
    s.add_argument("--db", required=False, help="Optional path to SQLite DB")
    s.add_argument(
        "--method",
        default="hybrid",
        choices=["keyword", "embedding", "hybrid"],
        help="Search method",
    )
    s.add_argument("--top-k", default=10, type=int, help="Number of results")
    s.add_argument("--alpha", default=0.5, type=float, help="Hybrid mix weight")
    s.add_argument("--provider", help="Embedding provider (optional)")
    s.add_argument("--model", help="Embedding model (optional)")

    # --------------------------------------------------------------------------
    # sync-hf
    # --------------------------------------------------------------------------
    sh = sub.add_parser(
        "sync-hf", help="Upload/download datastore artifacts to/from Hugging Face"
    )
    sh_sub = sh.add_subparsers(dest="action", required=True)

    up = sh_sub.add_parser("upload", help="Upload collection artifacts to HF")
    up.add_argument("--collection", required=True)
    up.add_argument(
        "--repo", help="HF dataset repo ID (defaults to <username>/<collection>)"
    )
    up.add_argument(
        "--private",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Make dataset private (default True). Use --no-private to make it public.",
    )
    up.add_argument(
        "--tool-json",
        nargs="*",
        default=None,
        help="Path(s) to Tool JSON file(s) to upload with the datastore.",
    )

    down = sh_sub.add_parser("download", help="Download collection artifacts from HF")
    down.add_argument("--repo", required=True)
    down.add_argument("--collection", required=True)
    down.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing index"
    )
    down.add_argument(
        "--include-tools", action="store_true", help="Also download tool JSON files"
    )

    # --------------------------------------------------------------------------
    # add-tool
    # --------------------------------------------------------------------------
    at = sub.add_parser(
        "add-tool",
        help="Register a tool JSON in ~/.tooluniverse/data/user_tools for auto-loading",
    )
    at.add_argument("json_file", help="Path to tool JSON file")
    at.add_argument(
        "--name",
        help="Optional filename to use under ~/.tooluniverse/data/user_tools "
        "(default = source filename)",
    )
    at.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing file if the same name already exists",
    )

    # --------------------------------------------------------------------------
    # Parse
    # --------------------------------------------------------------------------
    args = p.parse_args()

    if args.cmd == "build":
        with open(args.docs_json) as f:
            raw = json.load(f)
        docs = [
            (
                (
                    d.get("doc_key"),
                    d.get("text"),
                    d.get("metadata", {}),
                    d.get("text_hash"),
                )
                if isinstance(d, dict)
                else tuple(d)
            )
            for d in raw
        ]

        provider, model = resolve_provider_model(args.provider, args.model)
        db_path = resolve_db_path(args.db, args.collection)

        build_collection(
            db_path=db_path,
            collection=args.collection,
            docs=docs,
            embed_provider=provider,
            embed_model=model,
            overwrite=args.overwrite,
        )
        print(f"[INFO] Collection '{args.collection}' written to {db_path}")

    elif args.cmd == "quickbuild":
        docs = pack_folder(args.from_folder)
        if not docs:
            raise SystemExit("No supported files found. Put .txt or .md in the folder.")

        provider, model = resolve_provider_model(args.provider, args.model)
        db_path = resolve_db_path(None, args.name)

        build_collection(
            db_path=db_path,
            collection=args.name,
            docs=docs,
            embed_provider=provider,
            embed_model=model,
            overwrite=args.overwrite,
        )
        print(
            f"[INFO] Built collection '{args.name}' with {len(docs)} docs at {db_path}"
        )

    elif args.cmd == "search":
        db_path = resolve_db_path(args.db, args.collection)
        # Only require provider/model when embeddings are needed
        if args.method == "keyword":
            provider = model = None
        else:
            provider, model = resolve_provider_model(args.provider, args.model)
        res = search(
            db_path=db_path,
            collection=args.collection,
            query=args.query,
            method=args.method,
            top_k=args.top_k,
            alpha=args.alpha,
            embed_provider=provider,
            embed_model=model,
        )
        print(json.dumps(res, indent=2))

    elif args.cmd == "sync-hf":
        if args.action == "upload":
            sync_upload(
                collection=args.collection,
                repo=args.repo,
                private=args.private,
                tool_json=args.tool_json,
            )
        elif args.action == "download":
            sync_download(
                repo=args.repo,
                collection=args.collection,
                overwrite=args.overwrite,
                include_tools=args.include_tools,
            )
    elif args.cmd == "add-tool":
        add_tool(
            json_file=args.json_file,
            name=args.name,
            overwrite=args.overwrite,
        )

    else:
        p.print_help()
