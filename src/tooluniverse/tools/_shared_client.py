"""
Shared ToolUniverse client for all tools.

This module provides a singleton ToolUniverse client to avoid reloading
tools multiple times when using different tool functions.

Thread Safety:
    The shared client is thread-safe and uses double-checked locking to
    ensure only one ToolUniverse instance is created even in multi-threaded
    environments.

Configuration:
    You can provide custom configuration parameters that will be used during
    the initial creation of the ToolUniverse instance. These parameters are
    ignored if the client has already been initialized.

Custom Instance:
    You can provide your own ToolUniverse instance to be used instead of
    the shared singleton. This is useful when you need specific configurations
    or want to maintain separate instances.

Examples:
    Basic usage (default behavior):
        from tooluniverse.tools import get_shared_client
        client = get_shared_client()

    With custom configuration (only effective on first call):
        client = get_shared_client(hooks_enabled=True, log_level="INFO")

    Using your own instance:
        my_tu = ToolUniverse(hooks_enabled=True)
        client = get_shared_client(custom_instance=my_tu)

    Reset for testing:
        from tooluniverse.tools import reset_shared_client
        reset_shared_client()
"""

import threading
from typing import Optional
from tooluniverse import ToolUniverse

_client: Optional[ToolUniverse] = None
_client_lock = threading.Lock()


def get_shared_client(
    custom_instance: Optional[ToolUniverse] = None, **config_kwargs
) -> ToolUniverse:
    """
    Get the shared ToolUniverse client instance.

    This function implements a thread-safe singleton pattern with support for
    custom configurations and external instances.

    Args:
        custom_instance: Optional ToolUniverse instance to use instead of
                        the shared singleton. If provided, this instance
                        will be returned directly without any singleton logic.

        **config_kwargs: Optional configuration parameters to pass to
                        ToolUniverse constructor. These are only used during
                        the initial creation of the shared instance. If the
                        shared instance already exists, these parameters are
                        ignored.

    Returns
        ToolUniverse: The client instance to use for tool execution

    Thread Safety:
        This function is thread-safe. Multiple threads can call this function
        concurrently without risk of creating multiple ToolUniverse instances.

    Configuration:
        Configuration parameters are only applied during the initial creation
        of the shared instance. Subsequent calls with different parameters
        will not affect the already-created instance.

    Examples
        # Basic usage
        client = get_shared_client()

        # With custom configuration (only effective on first call)
        client = get_shared_client(hooks_enabled=True, log_level="DEBUG")

        # Using your own instance
        my_tu = ToolUniverse(hooks_enabled=True)
        client = get_shared_client(custom_instance=my_tu)
    """
    # If user provides their own instance, use it directly
    if custom_instance is not None:
        return custom_instance

    global _client

    # Double-checked locking pattern for thread safety
    if _client is None:
        with _client_lock:
            # Check again inside the lock to avoid race conditions
            if _client is None:
                # Create new instance with provided configuration
                if config_kwargs:
                    _client = ToolUniverse(**config_kwargs)
                else:
                    _client = ToolUniverse()
                _client.load_tools()

    return _client


def reset_shared_client():
    """
    Reset the shared client (useful for testing or when you need to reload).

    This function clears the shared client instance, allowing a new instance
    to be created on the next call to get_shared_client(). This is primarily
    useful for testing scenarios where you need to ensure a clean state.

    Thread Safety:
        This function is thread-safe and uses the same lock as
        get_shared_client() to ensure proper synchronization.

    Warning:
        Calling this function while other threads are using the shared client
        may cause unexpected behavior. It's recommended to only call this
        function when you're certain no other threads are accessing the client.

    Examples
        # Reset for testing
        reset_shared_client()

        # Now get_shared_client() will create a new instance
        client = get_shared_client(hooks_enabled=True)
    """
    global _client

    with _client_lock:
        if _client:
            _client.close()
        _client = None
