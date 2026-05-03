#!/usr/bin/env python3
"""
ToolUniverse HTTP API Server CLI

Command-line interface for starting the ToolUniverse HTTP API server.

Usage:
    tooluniverse-http-api --host 0.0.0.0 --port 8080
    tooluniverse-http-api --host 0.0.0.0 --port 8080 --workers 4
"""

import argparse
import os
import sys


def run_http_api_server():
    """Main entry point for the HTTP API server"""
    parser = argparse.ArgumentParser(
        description="Start ToolUniverse HTTP API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server with default settings (single worker, 20 threads)
  tooluniverse-http-api

  # Start on specific host and port
  tooluniverse-http-api --host 0.0.0.0 --port 8080

  # Start with larger thread pool for high concurrency (recommended for GPU)
  tooluniverse-http-api --host 0.0.0.0 --port 8080 --thread-pool-size 50

  # Start with reload for development
  tooluniverse-http-api --reload

  # Start with multiple workers (only for CPU-only workloads, not GPU)
  tooluniverse-http-api --host 0.0.0.0 --port 8080 --workers 4

Features:
  - Auto-discovers all ToolUniverse methods via introspection
  - No manual updates needed when ToolUniverse changes
  - Thread-safe singleton ToolUniverse instance
  - Async execution with thread pool for high concurrency
  - Full API documentation at /docs

Note:
  - Default is 1 worker (recommended for GPU workloads)
  - Single worker uses async + thread pool (default: 20 threads) for concurrency
  - Multiple workers create separate ToolUniverse instances (not recommended for GPU)
  - For CPU-only workloads, you can increase workers if needed
        """,
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1, use 0.0.0.0 for remote access)",
    )

    parser.add_argument(
        "--port", type=int, default=8080, help="Port to bind to (default: 8080)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1). WARNING: Multiple workers create separate ToolUniverse instances, each consuming GPU memory. Use single worker with larger thread pool for GPU workloads.",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development (not for production)",
    )

    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Log level (default: info)",
    )

    parser.add_argument(
        "--thread-pool-size",
        type=int,
        default=20,
        help="Size of thread pool for async execution per worker (default: 20). Increase this for higher concurrency instead of adding workers.",
    )

    args = parser.parse_args()

    # Set thread pool size via environment variable
    os.environ["TOOLUNIVERSE_THREAD_POOL_SIZE"] = str(args.thread_pool_size)

    print("=" * 70)
    print("🚀 ToolUniverse HTTP API Server")
    print("=" * 70)
    print(f"📡 Host: {args.host}")
    print(f"🔌 Port: {args.port}")
    print(f"⚙️  Workers: {args.workers}")
    if args.workers == 1:
        print(
            f"   ⚡ Single worker with {args.thread_pool_size}-thread pool for async concurrency"
        )
    else:
        print(
            f"   🔄 {args.workers} worker processes (each with separate ToolUniverse instance)"
        )
        print(
            f"   ⚡ Each worker uses {args.thread_pool_size}-thread pool for async operations"
        )
    print(f"📝 Log Level: {args.log_level}")
    print(f"🔄 Auto-reload: {'Enabled' if args.reload else 'Disabled'}")
    print()
    print("📚 API Documentation:")
    print(f"   - Swagger UI: http://{args.host}:{args.port}/docs")
    print(f"   - ReDoc: http://{args.host}:{args.port}/redoc")
    print()
    print("🔧 Endpoints:")
    print(f"   - Call method: POST http://{args.host}:{args.port}/api/call")
    print(f"   - List methods: GET http://{args.host}:{args.port}/api/methods")
    print(f"   - Health check: GET http://{args.host}:{args.port}/health")
    print()
    print("💡 Client Usage:")
    print("   from tooluniverse import ToolUniverseClient")
    print(f'   client = ToolUniverseClient("http://{args.host}:{args.port}")')
    print("   client.load_tools(tool_type=['uniprot', 'ChEMBL'])")
    print()
    print("=" * 70)
    print()

    try:
        import uvicorn

        # Use import string when workers > 1 (required by uvicorn)
        if args.workers > 1 and not args.reload:
            app_import = "tooluniverse.http_api_server:app"
            uvicorn.run(
                app_import,
                host=args.host,
                port=args.port,
                workers=args.workers,
                log_level=args.log_level,
            )
        else:
            # Single worker or reload mode: import app directly
            from .http_api_server import app

            uvicorn.run(
                app,
                host=args.host,
                port=args.port,
                workers=1,  # reload requires workers=1
                reload=args.reload,
                log_level=args.log_level,
            )

    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error starting server: {e}")
        print("\nMake sure FastAPI and Uvicorn are installed:")
        print("  pip install fastapi uvicorn")
        sys.exit(1)


if __name__ == "__main__":
    run_http_api_server()
