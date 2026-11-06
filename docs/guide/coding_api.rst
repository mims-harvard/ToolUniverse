Coding API - Typed Functions
=============================

Import and call tools like normal Python functions:

.. code-block:: python

    from tooluniverse.tools import UniProt_get_entry_by_accession

    # Call the function
    result = UniProt_get_entry_by_accession(accession="P05067")
    print(result)

What You Get Back
-----------------

A tool call returns a **value**, never an exception, and that value is where you
find out whether it worked. A failure carries ``status`` and ``error``, and,
when the framework was the one to classify it, an ``error_details`` block:

.. code-block:: python

    {
        "status": "error",
        "error": "Parameter validation failed for 'root': 'start' is a required property",
        "error_details": {
            "type": "ToolValidationError",
            "message": "Parameter validation failed for 'root': ...",
            "retriable": False,
            "next_steps": [
                "Check parameter types and values",
                "Review tool documentation",
                "Verify required parameters are provided",
            ],
            "details": {"validation_error": "..."},
        },
    }

On success the shape is the tool's own. Most tools wrap their payload as
``{"status": "success", "data": ...}``; others hand the payload back directly.
Read the tool's ``Returns`` docstring rather than assuming — that variation is
why the generated annotations are unions such as ``list[Any] | dict[str, Any]``.

Error Handling
--------------

Check the returned value. ``error_details`` carries the error class name under
``type``, the suggested actions under ``next_steps``, and whether another
attempt is worth making under ``retriable``.

``error_details`` is not always there. A bad argument is classified by the
framework and gets the full block; a tool reporting an upstream failure of its
own may not. ``UniProt_get_entry_by_accession(accession="")`` passes schema
validation, reaches UniProt, and comes back as
``{"status": "error", "error": "UniProt API returned status code: 404"}`` with
no ``error_details`` at all -- so read it with ``.get()``:

.. code-block:: python

    from tooluniverse.tools import UniProt_get_entry_by_accession

    result = UniProt_get_entry_by_accession(accession="invalid")

    if isinstance(result, dict) and result.get("status") == "error":
        details = result.get("error_details", {})
        print("Error:", result["error"])
        print("Kind:", details.get("type"))           # e.g. "ToolValidationError"
        print("What to do:", details.get("next_steps"))
        if details.get("retriable"):
            ...  # worth another attempt

``tooluniverse.exceptions`` defines ``ToolError`` and its subclasses, but the
tool-call path turns them into the dict above instead of letting them out, on
every calling pattern — the generated wrappers, ``tu.tools.X(...)``,
``tu.run(...)`` and their ``await`` forms. So wrapping a call in
``try``/``except ToolValidationError`` catches nothing and leaves the error to
be used as though it were data.

One exception does reach you, and it is not from the call: ``tu.tools`` raises
``AttributeError`` for a tool name that does not exist.

.. code-block:: python

    try:
        tu.tools.NameThatDoesNotExist(param="x")
    except AttributeError as e:
        print(e)  # Tool 'NameThatDoesNotExist' not found ...

With Options
------------

.. code-block:: python

    result = UniProt_get_entry_by_accession(
        accession="P05067",
        use_cache=True,
        validate=True
    )

``validate`` defaults to ``True`` and checks the arguments against the tool's
parameter schema before the call.

Caching
-------

Caching is **off** by default; ``use_cache=True`` turns it on for that call.

.. code-block:: python

    result = UniProt_get_entry_by_accession(
        accession="P05067",
        use_cache=True
    )

Cache deterministic work such as a database lookup or an ML prediction; leave it
off for anything time-sensitive.

Examples
--------

See ``examples/coding_api_example.py`` for more examples.
