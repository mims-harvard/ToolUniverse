# Initialize the compose_scripts package


def payload(result):
    """
    Return the data carried by a tool response.

    ToolUniverse tools wrap upstream API responses in a ``{"status": ..., "data": ...}``
    envelope, so a composition that reads the raw upstream shape straight off the
    response always misses and records a populated source as empty. Compose scripts
    should unwrap through this helper rather than re-deriving the envelope contract.

    Returns None when the call did not succeed, so a source that failed is not
    reported as a source that returned nothing.
    """
    if isinstance(result, dict) and "status" in result and "data" in result:
        if result["status"] != "success":
            return None
        return result["data"]
    return result
