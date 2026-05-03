HTTP API - Remote Access
=========================

The ToolUniverse HTTP API server provides remote access to all ToolUniverse methods via HTTP/REST endpoints.

**Key Feature**: When you add or modify methods in ToolUniverse, the server and client automatically support them with zero manual updates!

Quick Start
-----------

Start Server
~~~~~~~~~~~~

On the machine with ToolUniverse installed:

.. code-block:: bash

    # Install full ToolUniverse package
    pip install tooluniverse

    # Start HTTP API server (single worker with async thread pool)
    tooluniverse-http-api --host 0.0.0.0 --port 8080

Use Client
~~~~~~~~~~

Install minimal client on any machine:

.. code-block:: bash

    pip install tooluniverse[client]  # Only needs: requests + pydantic

.. code-block:: python

    from tooluniverse import ToolUniverseClient

    client = ToolUniverseClient("http://your-server:8080")
    client.load_tools(tool_type=['uniprot', 'ChEMBL'])
    result = client.run_one_function({
        "name": "UniProt_get_entry_by_accession",
        "arguments": {"accession": "P05067"}
    })

Client Usage Details
--------------------

Official Client Features
~~~~~~~~~~~~~~~~~~~~~~~~~

The official ``ToolUniverseClient`` includes:

- Automatic method discovery: ``client.list_available_methods()``
- Built-in help: ``client.help("method_name")``
- Health check: ``client.health_check()``
- Context manager support: ``with ToolUniverseClient(url) as client:``
- All ToolUniverse methods via dynamic proxy

Custom Client Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you need a custom client, ensure discovery methods are **real methods** (not proxied):

.. code-block:: python

    import requests
    
    class CustomToolUniverseClient:
        def __init__(self, url):
            self.base_url = url.rstrip("/")
        
        # Real methods for discovery endpoints (not proxied)
        def list_available_methods(self):
            """Uses GET /api/methods (not POST /api/call)"""
            response = requests.get(f"{self.base_url}/api/methods")
            return response.json()["methods"]
        
        def health_check(self):
            """Uses GET /health"""
            response = requests.get(f"{self.base_url}/health")
            return response.json()
        
        # Proxy for ToolUniverse methods
        def __getattr__(self, method_name):
            """Only ToolUniverse methods use POST /api/call"""
            def proxy(**kwargs):
                response = requests.post(
                    f"{self.base_url}/api/call",
                    json={"method": method_name, "kwargs": kwargs}
                )
                result = response.json()
                if not result.get("success"):
                    raise Exception(f"{result['error_type']}: {result['error']}")
                return result["result"]
            return proxy

**Important**: ``list_available_methods()`` must be a real method, not proxied through ``__getattr__``, because it needs to use ``GET /api/methods``, not ``POST /api/call``.

How It Works
------------

Auto-Discovery (Server)
~~~~~~~~~~~~~~~~~~~~~~~

The server uses Python introspection to automatically discover all public methods:

.. code-block:: python

    import inspect

    # Automatically discovers ALL public methods
    for name, method in inspect.getmembers(ToolUniverse, inspect.isfunction):
        if not name.startswith('_'):
            # Extract signature, parameters, docstring
            # Methods are now callable via HTTP!

**Result**: 49+ methods including ``load_tools``, ``prepare_tool_prompts``, ``tool_specification``, ``run_one_function``, etc.

Dynamic Proxying (Client)
~~~~~~~~~~~~~~~~~~~~~~~~~~

The client uses ``__getattr__`` magic to intercept any method call:

.. code-block:: python

    class ToolUniverseClient:
        def __getattr__(self, method_name):
            # Intercepts ANY method call
            def proxy(**kwargs):
                # Forwards to server via HTTP
                return requests.post(url, json={
                    "method": method_name,
                    "kwargs": kwargs
                })
            return proxy

**Workflow Example**:

When you call ``client.load_tools(tool_type=['uniprot'])``:

1. Python looks for ``load_tools`` attribute → NOT FOUND
2. Calls ``__getattr__("load_tools")`` → Returns proxy function
3. Proxy called with ``tool_type=['uniprot']``
4. HTTP POST to server: ``{"method": "load_tools", "kwargs": {...}}``
5. Server calls ``tu.load_tools(tool_type=['uniprot'])``
6. Result returned to client

**Result**: ANY method works automatically, even future ones you haven't written yet!

API Endpoints
-------------

The server exposes the following REST endpoints:

.. list-table:: API Endpoints Reference
 :header-rows: 1
 :widths: 20 10 40 30

 * - Endpoint
 - Method
 - Purpose
 - Client Usage
 * - ``/health``
 - GET
 - Server health check
 - ``client.health_check()``
 * - ``/api/methods``
 - GET
 - List all ToolUniverse methods
 - ``client.list_available_methods()``
 * - ``/api/call``
 - POST
 - Call any ToolUniverse method
 - ``client.method_name(**kwargs)``
 * - ``/api/reset``
 - POST
 - Reset ToolUniverse instance
 - ``client.reset_server(config)``
 * - ``/docs``
 - GET
 - Interactive Swagger UI docs
 - Open in browser
 * - ``/redoc``
 - GET
 - Alternative ReDoc docs
 - Open in browser

**Key distinction:**

- **Discovery endpoints** (``/health``, ``/api/methods``): Use GET, handled by client as real methods
- **Execution endpoint** (``/api/call``): Use POST, calls actual ToolUniverse methods

Example Usage
-------------

See ``examples/http_api_usage_example.py`` for comprehensive examples including:

- Listing methods and getting help
- Loading tools and getting specifications 
- Executing tools and checking health
- Tool prompts preparation

Production Deployment
---------------------

GPU-Optimized Configuration (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For GPU-based inference workloads (default, recommended):

.. code-block:: bash

    # Single worker with async thread pool (default: 20 threads)
    tooluniverse-http-api --host 0.0.0.0 --port 8080

    # High concurrency: increase thread pool size
    tooluniverse-http-api --host 0.0.0.0 --port 8080 --thread-pool-size 50

    # Very high concurrency
    tooluniverse-http-api --host 0.0.0.0 --port 8080 --thread-pool-size 100

**Why single worker for GPU?**

- Single ToolUniverse instance → Single GPU model in memory (~2GB)
- Multiple workers → Multiple GPU model copies (~16GB+ wasted memory)
- High concurrency via async thread pool (20-100 concurrent operations)
- Efficient GPU memory usage

Multi-Worker Configuration (CPU-Only Workloads)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Only use multiple workers for CPU-only workloads without GPU:

.. code-block:: bash

    # Multiple workers (only for CPU-only operations)
    tooluniverse-http-api --host 0.0.0.0 --port 8080 --workers 8

**Warning**: Multiple workers create separate ToolUniverse instances, each consuming GPU memory if GPU is used.

Development Mode
~~~~~~~~~~~~~~~~

For development with auto-reload:

.. code-block:: bash

    tooluniverse-http-api --host 127.0.0.1 --port 8080 --reload

Installation
------------

- **Server**: ``pip install tooluniverse``
- **Client**: ``pip install tooluniverse[client]`` (only requests + pydantic)

Testing
-------

.. code-block:: bash

    # Run tests
    pytest tests/test_http_api_server.py -v
    
    # Run examples
    python examples/http_api_usage_example.py

Implementation Files
--------------------

Core Implementation
~~~~~~~~~~~~~~~~~~~

- ``src/tooluniverse/http_api_server.py`` - FastAPI server with auto-discovery
- ``src/tooluniverse/http_api_server_cli.py`` - CLI entry point
- ``src/tooluniverse/http_client.py`` - Auto-proxying client (minimal dependencies)

Examples & Tests
~~~~~~~~~~~~~~~~

- ``examples/http_api_usage_example.py`` - 7 comprehensive usage examples
- ``tests/test_http_api_server.py`` - Comprehensive test suite

Configuration Options
---------------------

Command-Line Arguments
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    tooluniverse-http-api --help

Available options:

- ``--host`` - Host to bind to (default: 127.0.0.1)
- ``--port`` - Port to bind to (default: 8080)
- ``--workers`` - Number of worker processes (default: 1, recommended for GPU)
- ``--thread-pool-size`` - Async thread pool size per worker (default: 20)
- ``--log-level`` - Log level: debug, info, warning, error, critical
- ``--reload`` - Enable auto-reload for development

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Set thread pool size via environment variable
    export TOOLUNIVERSE_THREAD_POOL_SIZE=50
    tooluniverse-http-api --host 0.0.0.0 --port 8080

Performance Tuning
~~~~~~~~~~~~~~~~~~

For GPU workloads, scale concurrency with thread pool size:

.. code-block:: bash

    # Low traffic (20 concurrent requests)
    tooluniverse-http-api --thread-pool-size 20

    # Medium traffic (50 concurrent requests)
    tooluniverse-http-api --thread-pool-size 50

    # High traffic (100 concurrent requests)
    tooluniverse-http-api --thread-pool-size 100

**Rule of thumb**: ``thread_pool_size = GPU_batch_size × 2 to 5``

Benefits
--------

1. **Zero Maintenance** - Add ToolUniverse methods → They automatically work over HTTP
2. **Minimal Client** - Only needs ``requests`` + ``pydantic`` (no ToolUniverse package)
3. **Full API Access** - All 49+ ToolUniverse methods available remotely
4. **Stateful** - Server maintains ToolUniverse instance across requests
5. **Type Discovery** - Client can query available methods at runtime
6. **Automatic** - Both server and client use introspection/magic methods
7. **Flexible Install** - Server needs full package, client uses ``tooluniverse[client]``
8. **GPU-Optimized** - Single worker with async thread pool for efficient GPU usage
9. **High Concurrency** - 20-100+ concurrent operations via async thread pool

Docker Deployment
-----------------

With GPU Support
~~~~~~~~~~~~~~~~

.. code-block:: dockerfile

    FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

    WORKDIR /app
    COPY . .
    RUN pip install tooluniverse uvicorn fastapi

    EXPOSE 8080

    # Single worker with high thread pool for GPU
    CMD ["tooluniverse-http-api", \
         "--host", "0.0.0.0", \
         "--port", "8080", \
         "--workers", "1", \
         "--thread-pool-size", "50"]

Run with GPU:

.. code-block:: bash

    docker run --gpus all -p 8080:8080 tooluniverse-api

Without GPU (CPU-Only)
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: dockerfile

    FROM python:3.12-slim

    WORKDIR /app
    COPY . .
    RUN pip install tooluniverse uvicorn fastapi

    EXPOSE 8080

    # Multiple workers for CPU workloads
    CMD ["tooluniverse-http-api", \
         "--host", "0.0.0.0", \
         "--port", "8080", \
         "--workers", "4"]

Monitoring
----------

GPU Memory Usage
~~~~~~~~~~~~~~~~

Check GPU memory usage:

.. code-block:: bash

    # Monitor GPU in real-time
    watch -n 1 nvidia-smi

Expected output with single worker:

.. code-block:: text

    +-----------------------------------------------------------------------------+
    | Processes:                                                                  |
    |  GPU   PID   Type   Process name                             GPU Memory    |
    |============================================================================|
    |    0   12345  C     python3 tooluniverse-http-api              2048MiB    |
    +-----------------------------------------------------------------------------+

Only ONE process should be using GPU memory.

Server Health
~~~~~~~~~~~~~

.. code-block:: bash

    # Check server health
    curl http://localhost:8080/health

    # Monitor logs
    tooluniverse-http-api --log-level info

Interactive Documentation
--------------------------

Once the server is running, you can access interactive API documentation:

- **Swagger UI**: http://server:8080/docs
- **ReDoc**: http://server:8080/redoc

These provide a web interface to explore and test all API endpoints.

Troubleshooting
---------------

Most Common Issue
~~~~~~~~~~~~~~~~~

**Error: "Method 'list_available_methods' not found on ToolUniverse"**

This is the most common error when using a custom client.

**What's happening:**

Your custom client uses ``__getattr__`` to proxy ALL method calls to ``POST /api/call``, including ``list_available_methods()``. But ``list_available_methods()`` is NOT a ToolUniverse method - it's a client-side utility that should use ``GET /api/methods``.

**Why this happens:**

.. code-block:: text

    # Your custom client code:
    client.list_available_methods()
    ↓
    __getattr__("list_available_methods") intercepts it
    ↓
    POST /api/call {"method": "list_available_methods", "kwargs": {}}
    ↓
    Server tries: tu.list_available_methods()
    ↓
    ❌ ERROR: "Method 'list_available_methods' not found on ToolUniverse"

**The fix:**

 **Wrong**: Custom client that proxies everything

.. code-block:: python

    class ToolUniverseClient:
        def __getattr__(self, method_name):
            # This proxies EVERYTHING, including list_available_methods!
            def proxy(**kwargs):
                return requests.post(url, json={"method": method_name, "kwargs": kwargs})
            return proxy

    client.list_available_methods()  # ❌ Tries to call it on ToolUniverse (doesn't exist)

 **Solution**: Use the official client

.. code-block:: python

    from tooluniverse import ToolUniverseClient
    
    client = ToolUniverseClient("http://server:8080")
    methods = client.list_available_methods()  # ✅ Works correctly

Or if implementing a custom client, see the "Custom Client Implementation" section above for the correct pattern.

**Key insight**: ``list_available_methods()`` must be a real method using ``GET /api/methods``, not proxied through ``__getattr__`` to ``POST /api/call``.

**Server Not Starting**

.. code-block:: bash

    # Check if port is in use
    lsof -i :8080
    
    # Use different port
    tooluniverse-http-api --port 8081

**High Memory Usage**

If you see multiple worker processes consuming GPU memory:

.. code-block:: bash

    # Use single worker (default)
    tooluniverse-http-api --workers 1
    
    # Increase thread pool instead
    tooluniverse-http-api --thread-pool-size 50

**Connection Refused**

Ensure server is accessible:

.. code-block:: bash

    # Listen on all interfaces
    tooluniverse-http-api --host 0.0.0.0 --port 8080
    
    # Check firewall
    curl http://server:8080/health

**Tool_RAG Tensor Copy Error**

If you encounter a tensor copy error when using ``Tool_RAG``:

.. code-block:: text

    RuntimeError: Trying to copy tensor from CPU to CUDA device...

This was a device mismatch bug where cached embeddings (CPU) didn't match the model device (GPU). 

**Fixed in latest version:**

- Tool_RAG model automatically loads on GPU if available
- Cached embeddings are automatically moved to model's device
- Device compatibility checks before tensor operations

**Solution**: Update to the latest version:

.. code-block:: bash

    pip install --upgrade tooluniverse[embedding]

The model will now automatically use GPU when available for faster inference.