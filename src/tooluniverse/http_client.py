#!/usr/bin/env python3
"""
ToolUniverse API Client - Minimal Dependencies HTTP Client

This client automatically supports ALL ToolUniverse methods via dynamic proxying.
Uses __getattr__ magic to intercept method calls and forward them to the HTTP server.

NO MANUAL UPDATES NEEDED - when ToolUniverse methods change, client automatically works!

Dependencies:
    - requests>=2.32.0
    - pydantic>=2.11.0

Install:
    pip install tooluniverse[client]

Usage:
    from tooluniverse import ToolUniverseClient

    client = ToolUniverseClient("http://server:8080")

    # All ToolUniverse methods work automatically!
    client.load_tools(tool_type=['uniprot', 'ChEMBL'])
    spec = client.tool_specification("UniProt_get_entry_by_accession")
    result = client.run_one_function({...})

Documentation:
    https://zitniklab.hms.harvard.edu/ToolUniverse/guide/http_api.html
"""

import requests
from typing import Any, Dict, Optional, List


class ToolUniverseClient:
    """
    Standalone client that mirrors ALL ToolUniverse methods via HTTP.

    Uses __getattr__ magic to dynamically proxy any method call to the server.
    When you call client.some_method(**kwargs), it makes an HTTP POST to the server
    with the method name and arguments.

    Benefits:
    - No need to update client when ToolUniverse changes
    - Standalone (only needs 'requests', no ToolUniverse package)
    - Automatic method discovery
    - Identical API to local ToolUniverse

    Example:
        client = ToolUniverseClient("http://localhost:8080")

        # These all work automatically:
        client.load_tools(tool_type=['uniprot', 'ChEMBL'])
        prompts = client.prepare_tool_prompts(tool_list, mode="prompt")
        result = client.run_one_function(function_call_json)

        # Tomorrow you add a new method to ToolUniverse?
        # It automatically works:
        client.your_new_method(param="value")
    """

    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Initialize client.

        Args:
            base_url: Base URL of ToolUniverse HTTP API server
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self._methods_cache: Optional[List[Dict]] = None

    def _get_available_methods(self) -> List[Dict]:
        """Fetch list of available methods from server (cached)"""
        if self._methods_cache is None:
            try:
                response = self.session.get(f"{self.base_url}/api/methods", timeout=10)
                response.raise_for_status()
                data = response.json()
                self._methods_cache = data.get("methods", [])
            except Exception as e:
                # Fallback: continue without method info
                print(f"Warning: Could not fetch methods list: {e}")
                self._methods_cache = []
        return self._methods_cache

    def __getattr__(self, method_name: str):
        """
        Magic method that intercepts attribute access.

        When you call client.some_method(**kwargs), Python:
        1. Looks for 'some_method' attribute - doesn't find it
        2. Calls this __getattr__("some_method")
        3. We return a function that makes HTTP call
        4. That function gets called with your arguments
        5. HTTP request sent to server with method name + args
        6. Server calls tu.some_method(**kwargs)
        7. Result returned to client

        This means ANY ToolUniverse method works automatically!
        No need to define methods in this class.
        """
        # Don't intercept private attributes
        if method_name.startswith("_"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{method_name}'"
            )

        def method_proxy(**kwargs) -> Any:
            """
            Proxy function that sends method call to server.

            Args:
                **kwargs: Arguments to pass to the ToolUniverse method

            Returns:
                Result from ToolUniverse method execution

            Raises:
                Exception: If server returns an error
            """
            try:
                response = self.session.post(
                    f"{self.base_url}/api/call",
                    json={"method": method_name, "kwargs": kwargs},
                    timeout=30,  # 30s for fast training operations
                )
                response.raise_for_status()

                result = response.json()

                if not result.get("success", False):
                    error_msg = result.get("error", "Unknown error")
                    error_type = result.get("error_type", "UnknownError")
                    raise Exception(f"[{error_type}] {error_msg}")

                return result.get("result")
            
            except requests.exceptions.ReadTimeout:
                print(method_name, kwargs, "timed out")
                return f"Error: Tool execution timed out after 30 seconds"

            except requests.exceptions.RequestException as e:
                return f"Error: HTTP request failed for '{method_name}': {e}"

        # Try to add docstring from server (best effort)
        try:
            methods = self._get_available_methods()
            for method_info in methods:
                if method_info.get("name") == method_name:
                    method_proxy.__doc__ = method_info.get("docstring", "")
                    method_proxy.__name__ = method_name
                    break
        except Exception:
            pass  # Ignore errors in documentation lookup

        return method_proxy

    def list_available_methods(self) -> List[Dict]:
        """
        List all available ToolUniverse methods from the server.

        Returns:
            List of method information dicts with:
            - name: Method name
            - parameters: List of parameter info
            - docstring: Method documentation

        Example:
            methods = client.list_available_methods()
            for m in methods:
                print(f"{m['name']}: {m['docstring']}")
        """
        return self._get_available_methods()

    def help(self, method_name: Optional[str] = None):
        """
        Get help about available methods.

        Args:
            method_name: Optional specific method to get help for.
                        If None, lists all methods.

        Example:
            client.help()  # List all methods
            client.help("load_tools")  # Help for specific method
        """
        methods = self.list_available_methods()

        if method_name:
            for m in methods:
                if m["name"] == method_name:
                    print(f"\nMethod: {m['name']}")
                    print(f"Description: {m.get('docstring', 'No description')}")
                    print("\nParameters:")
                    for p in m.get("parameters", []):
                        req = " (required)" if p.get("required") else " (optional)"
                        default = f" = {p.get('default')}" if p.get("default") else ""
                        print(f"  {p['name']}: {p.get('type', 'Any')}{default}{req}")
                    return
            print(f"Method '{method_name}' not found")
        else:
            print(f"\nAvailable methods ({len(methods)}):")
            for m in methods:
                desc = m.get("docstring", "")
                if desc:
                    desc = desc.split("\n")[0][:60] + "..."
                print(f"  - {m['name']}: {desc}")

    def reset_server(self, config: Optional[Dict[str, Any]] = None):
        """
        Reset the ToolUniverse instance on the server.

        Args:
            config: Optional configuration for the new instance

        Example:
            client.reset_server()  # Reset with default config
            client.reset_server({"log_level": "DEBUG"})  # With custom config
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/reset", json=config if config else {}, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to reset server: {e}")

    def health_check(self) -> Dict[str, Any]:
        """
        Check server health status.

        Returns:
            Health status information
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Health check failed: {e}")

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __repr__(self):
        return f"ToolUniverseClient(base_url='{self.base_url}')"


# Convenience function for quick one-off calls
def call_tooluniverse_method(
    method_name: str, kwargs: Dict[str, Any], server_url: str = "http://localhost:8080"
) -> Any:
    """
    Quick function to call a ToolUniverse method without creating client.

    Args:
        method_name: Name of the ToolUniverse method
        kwargs: Arguments for the method
        server_url: URL of the ToolUniverse API server

    Returns:
        Result from method execution

    Example:
        result = call_tooluniverse_method(
            "run_one_function",
            {
                "function_call_json": {
                    "name": "UniProt_get_entry_by_accession",
                    "arguments": {"accession": "P05067"}
                }
            }
        )
    """
    with ToolUniverseClient(server_url) as client:
        method = getattr(client, method_name)
        return method(**kwargs)


if __name__ == "__main__":
    """Example usage and testing."""
    import sys

    # Default server URL
    server_url = "http://localhost:8080"
    if len(sys.argv) > 1:
        server_url = sys.argv[1]

    print(f"🔍 Testing ToolUniverse API Client")
    print(f"📡 Server: {server_url}\n")

    try:
        with ToolUniverseClient(server_url) as client:
            # Test 1: Health check
            print("1️⃣  Health check...")
            health = client.health_check()
            print(f"   ✅ Status: {health.get('status')}")
            print(f"   ✅ Loaded tools: {health.get('loaded_tools_count', 0)}\n")

            # Test 2: List methods
            print("2️⃣  Listing available methods...")
            methods = client.list_available_methods()
            print(f"   ✅ Found {len(methods)} methods")
            if methods:
                print(f"   First 5 methods:")
                for method in methods[:5]:
                    name = method.get("name", "Unknown")
                    print(f"   - {name}")
            print()

            # Test 3: Get help
            if methods:
                method_name = methods[0]["name"]
                print(f"3️⃣  Getting help for: {method_name}")
                client.help(method_name)

            print("\n" + "=" * 70)
            print("✅ All tests passed!")
            print("=" * 70)
            print("\n💡 Usage example:")
            print("   from tooluniverse import ToolUniverseClient")
            print(f'   client = ToolUniverseClient("{server_url}")')
            print('   client.load_tools(tool_type=["uniprot", "ChEMBL"])')
            print("   result = client.run_one_function({...})")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure the ToolUniverse HTTP API server is running:")
        print("   tooluniverse-http-api --host 0.0.0.0 --port 8080")
        sys.exit(1)
