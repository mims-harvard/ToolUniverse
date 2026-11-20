"""Inspect branch, history, and sample metadata in an authorized Gen repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base_tool import BaseTool
from .remote_data_path import resolve_remote_data_directory
from .tool_registry import register_tool

GEN_ROOT_ENV = "TOOLUNIVERSE_GEN_ROOT"
_MAX_LIMIT = 100
_DEFAULT_LIMIT = 20
_REQUIRED_DATABASES = ("gen.db", "default.db")


def _resolve_gen_repository(value: Any) -> Path:
    """Resolve an existing Gen workspace inside the administrator-approved root."""

    repository_path = resolve_remote_data_directory(value, root_env=GEN_ROOT_ENV)
    if repository_path.name == ".gen":
        raise ValueError("pass the Gen workspace directory, not its .gen directory")

    gen_directory = repository_path / ".gen"
    if gen_directory.is_symlink() or not gen_directory.is_dir():
        raise ValueError("the requested directory is not an existing Gen repository")

    for database_name in _REQUIRED_DATABASES:
        database_path = gen_directory / database_name
        if database_path.is_symlink() or not database_path.is_file():
            raise ValueError(
                "the requested directory is not an existing Gen repository"
            )
        try:
            if database_path.stat().st_size == 0:
                raise ValueError(
                    "the requested directory is not an existing Gen repository"
                )
        except OSError:
            raise ValueError(
                "the requested directory is not an existing Gen repository"
            ) from None

    return repository_path


def _branch_metadata(branch: Any) -> dict[str, Any]:
    """Return public branch state without configured remote details."""

    return {
        "name": branch.name,
        "is_current": branch.is_current,
        "head": str(branch.head),
        "dirty": branch.dirty,
    }


def _operation_metadata(operation: Any) -> dict[str, Any]:
    """Return history identifiers and dates without author or message fields."""

    return {
        "id": str(operation.id),
        "parent_id": str(operation.parent_id) if operation.parent_id else None,
        "date": operation.date,
        "is_head": operation.is_head,
    }


@register_tool("GenRepositoryInspectTool")
class GenRepositoryInspectTool(BaseTool):
    """Inspect bounded metadata from a Gen genome version control repository."""

    def run(self, arguments=None, stream_callback=None, use_cache=False, validate=True):
        arguments = arguments or {}
        view = arguments.get("view")
        limit = arguments.get("limit", _DEFAULT_LIMIT)
        branch = arguments.get("branch")

        if view not in ("branches", "operations", "samples"):
            return {
                "status": "error",
                "error": "view must be one of: branches, operations, samples",
            }
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= _MAX_LIMIT
        ):
            return {
                "status": "error",
                "error": f"limit must be an integer from 1 to {_MAX_LIMIT}",
            }
        if branch is not None and (not isinstance(branch, str) or not branch.strip()):
            return {
                "status": "error",
                "error": "branch must be a non-empty string when provided",
            }
        if branch is not None and view != "operations":
            return {
                "status": "error",
                "error": "branch can only be supplied when view is operations",
            }

        try:
            repository_path = _resolve_gen_repository(arguments.get("repository_path"))
        except ValueError as error:
            return {"status": "error", "error": str(error)}

        try:
            import gen
        except ImportError:
            return {
                "status": "error",
                "error": (
                    "Gen's Python package is required. Install it with "
                    "`pip install 'gen>=0.5.1'`."
                ),
            }

        try:
            repository = gen.Repository(str(repository_path))
            if view == "branches":
                all_items = repository.get_branches()
                current_branch = next(
                    (item for item in all_items if item.is_current), None
                )
                items = [_branch_metadata(item) for item in all_items[:limit]]
                total_count = len(all_items)
                truncated = total_count > limit
            else:
                current_branch = repository.current_branch
                if view == "operations":
                    all_items = repository.get_operations(
                        branch=branch, limit=limit + 1
                    )
                    truncated = len(all_items) > limit
                    items = [_operation_metadata(item) for item in all_items[:limit]]
                    total_count = None
                else:
                    all_items = repository.samples
                    items = [
                        {
                            "name": sample.name,
                            "collection": sample.collection,
                        }
                        for sample in all_items[:limit]
                    ]
                    total_count = len(all_items)
                    truncated = total_count > limit
        except Exception as error:
            return {
                "status": "error",
                "error": (
                    "Gen could not inspect the requested repository "
                    f"({type(error).__name__})."
                ),
            }

        return {
            "status": "success",
            "data": {
                "view": view,
                "branch": branch,
                "current_branch": current_branch.name if current_branch else None,
                "items": items,
                "returned": len(items),
                "total_count": total_count,
                "truncated": truncated,
            },
        }
