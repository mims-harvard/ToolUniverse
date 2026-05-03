#!/usr/bin/env python3
"""
ToolUniverse HTTP API Server

Auto-generating FastAPI server that exposes ALL ToolUniverse class methods via HTTP.
Uses Python introspection to automatically discover methods - no manual updates needed!

When you add/modify methods in ToolUniverse, they automatically work over HTTP.

Usage:
    python -m tooluniverse.http_api_server --host 0.0.0.0 --port 8080
"""

import asyncio
import inspect
import json
import os
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .execute_function import ToolUniverse
from .logging_config import get_logger

logger = get_logger("HTTPAPIServer")

# Thread pool for running sync ToolUniverse methods asynchronously
# Can be configured via TOOLUNIVERSE_THREAD_POOL_SIZE environment variable
_thread_pool_size = int(os.getenv("TOOLUNIVERSE_THREAD_POOL_SIZE", "20"))
_thread_pool = ThreadPoolExecutor(max_workers=_thread_pool_size)
logger.info(
    f"Initialized thread pool with {_thread_pool_size} workers for async execution"
)


class CallMethodRequest(BaseModel):
    """Request model for calling any ToolUniverse method"""

    method: str = Field(..., description="Name of the ToolUniverse method to call")
    kwargs: Dict[str, Any] = Field(
        default_factory=dict, description="Method arguments as key-value pairs"
    )


class CallMethodResponse(BaseModel):
    """Response model for method calls"""

    success: bool = Field(..., description="Whether the call succeeded")
    result: Optional[Any] = Field(
        None, description="Result from the method (if successful)"
    )
    error: Optional[str] = Field(None, description="Error message (if failed)")
    error_type: Optional[str] = Field(None, description="Type of error that occurred")


class MethodInfo(BaseModel):
    """Information about a ToolUniverse method"""

    name: str
    parameters: List[Dict[str, Any]]
    docstring: Optional[str]


class MethodsListResponse(BaseModel):
    """Response model for listing available methods"""

    methods: List[MethodInfo]
    total: int


class ToolUniverseManager:
    """
    Singleton manager for ToolUniverse instance.

    Ensures thread-safe access to a single ToolUniverse instance
    that persists across requests.
    """

    def __init__(self):
        self._instance: Optional[ToolUniverse] = None
        self._lock = threading.Lock()
        self._init_kwargs: Dict[str, Any] = {}

    def get_instance(self) -> ToolUniverse:
        """Get or create the ToolUniverse instance (thread-safe)"""
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    logger.info("Creating new ToolUniverse instance")
                    self._instance = ToolUniverse(**self._init_kwargs)
        return self._instance

    def reset(self, **kwargs):
        """Reset the ToolUniverse instance with new configuration"""
        with self._lock:
            if self._instance is not None:
                try:
                    self._instance.close()
                except Exception as e:
                    logger.warning(f"Error closing ToolUniverse instance: {e}")
            self._init_kwargs = kwargs
            self._instance = None
            logger.info("ToolUniverse instance reset")

    def configure(self, **kwargs):
        """Configure the ToolUniverse instance initialization parameters"""
        with self._lock:
            self._init_kwargs.update(kwargs)
            logger.info(f"Updated ToolUniverse configuration: {kwargs}")


# Global instance manager
_tu_manager = ToolUniverseManager()


def discover_public_methods(cls) -> Dict[str, Dict[str, Any]]:
    """
    Automatically discover all public methods from a class using introspection.

    Args:
        cls: The class to inspect

    Returns:
        Dictionary mapping method names to their metadata
    """
    methods = {}

    _empty = inspect.Parameter.empty

    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        # Skip private/magic methods
        if name.startswith("_"):
            continue

        try:
            sig = inspect.signature(method)
            params = [
                {
                    "name": param_name,
                    "type": str(param.annotation)
                    if param.annotation is not _empty
                    else "Any",
                    "required": param.default is _empty,
                    "default": str(param.default)
                    if param.default is not _empty
                    else None,
                }
                for param_name, param in sig.parameters.items()
                if param_name != "self"
            ]

            methods[name] = {
                "signature": sig,
                "parameters": params,
                "docstring": inspect.getdoc(method),
            }
        except Exception as e:
            logger.warning(f"Could not inspect method '{name}': {e}")
            continue

    return methods


# Create FastAPI app
app = FastAPI(
    title="ToolUniverse HTTP API",
    description="Auto-generated API exposing all ToolUniverse methods via HTTP",
    version="1.0.0",
)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": "ToolUniverse HTTP API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/api/call": "Call any ToolUniverse method",
            "/api/methods": "List all available methods",
            "/api/reset": "Reset ToolUniverse instance",
            "/health": "Health check",
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        tu = _tu_manager.get_instance()
        return {
            "status": "healthy",
            "tooluniverse_initialized": tu is not None,
            "loaded_tools_count": len(tu.all_tools) if tu else 0,
        }
    except Exception as e:
        return JSONResponse(
            status_code=503, content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/api/methods", response_model=MethodsListResponse, tags=["Discovery"])
async def list_methods():
    """
    List all available ToolUniverse methods with their signatures.

    Returns detailed information about each method including:
    - Method name
    - Parameters (name, type, required, default)
    - Docstring documentation
    """
    try:
        methods_dict = discover_public_methods(ToolUniverse)

        methods_list = [
            MethodInfo(
                name=name, parameters=info["parameters"], docstring=info["docstring"]
            )
            for name, info in sorted(methods_dict.items())
        ]

        return MethodsListResponse(methods=methods_list, total=len(methods_list))
    except Exception as e:
        logger.error(f"Error listing methods: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/call", response_model=CallMethodResponse, tags=["Execution"])
async def call_method(request: CallMethodRequest):
    """
    Generic endpoint to call any ToolUniverse method.

    This is the main endpoint - it can call ANY public method on ToolUniverse.

    Example request body:
    ```json
    {
        "method": "load_tools",
        "kwargs": {
            "tool_type": ["uniprot", "ChEMBL"],
            "exclude_tools": []
        }
    }
    ```

    Example request body:
    ```json
    {
        "method": "run_one_function",
        "kwargs": {
            "function_call_json": {
                "name": "UniProt_get_entry_by_accession",
                "arguments": {"accession": "P05067"}
            }
        }
    }
    ```
    """
    try:
        # Get ToolUniverse instance
        tu = _tu_manager.get_instance()

        # Validate method exists and is public
        if not hasattr(tu, request.method):
            return CallMethodResponse(
                success=False,
                error=f"Method '{request.method}' not found on ToolUniverse",
                error_type="MethodNotFoundError",
            )

        if request.method.startswith("_"):
            return CallMethodResponse(
                success=False,
                error=f"Cannot call private method '{request.method}'",
                error_type="PrivateMethodError",
            )

        # Get the method
        method = getattr(tu, request.method)

        if not callable(method):
            return CallMethodResponse(
                success=False,
                error=f"'{request.method}' is not a callable method",
                error_type="NotCallableError",
            )

        # Call the method with provided kwargs
        logger.info(
            f"Calling method: {request.method} with kwargs: {list(request.kwargs.keys())}"
        )

        # Run the synchronous method in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _thread_pool, partial(method, **request.kwargs)
        )

        # Serialize result (handle non-JSON-serializable objects)
        try:
            json.dumps(result)  # Test if serializable
            serialized_result = result
        except (TypeError, ValueError):
            # Convert to string if not JSON-serializable
            serialized_result = str(result)
            logger.warning(
                f"Result from {request.method} was not JSON-serializable, converted to string"
            )

        return CallMethodResponse(success=True, result=serialized_result)

    except TypeError as e:
        # Invalid arguments
        error_msg = f"Invalid arguments for method '{request.method}': {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        return CallMethodResponse(
            success=False, error=error_msg, error_type="InvalidArgumentsError"
        )

    except Exception as e:
        # Any other error during execution
        error_msg = f"Error executing method '{request.method}': {str(e)}"
        logger.error(error_msg)
        logger.debug(traceback.format_exc())
        return CallMethodResponse(
            success=False, error=error_msg, error_type=type(e).__name__
        )


@app.post("/api/reset", tags=["Management"])
async def reset_instance(config: Optional[Dict[str, Any]] = None):
    """
    Reset the ToolUniverse instance.

    Optionally provide configuration for the new instance:
    ```json
    {
        "log_level": "DEBUG",
        "hooks_enabled": true
    }
    ```
    """
    try:
        if config:
            _tu_manager.reset(**config)
        else:
            _tu_manager.reset()

        return {"success": True, "message": "ToolUniverse instance reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# CORS middleware (optional - uncomment if needed)
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
