Result Caching
==============

ToolUniverse ships with a two-tier result cache (in-memory + SQLite) so
expensive tool calls can be reused across runs without any extra setup. This
page explains what is cached, how to configure the cache, and how to inspect or
clear cached entries.

Why Use Caching?
----------------

**The Problem**: Scientific API calls can be slow and rate-limited:

- PubMed searches: 0.3-2 seconds per query
- UniProt lookups: 0.5-1 second per protein
- ChEMBL queries: 1-3 seconds per compound
- Rate limits: 3-10 requests/second (even with API keys)

**The Solution**: Cache results to avoid redundant API calls.

**Benefits**:

- **Speed**: Cached queries return in <1ms (vs 0.3-3 seconds)
- **Rate limit protection**: Avoid hitting API limits in batch workflows
- **Reproducibility**: Same query always returns same result (until source data changes)
- **Cost savings**: Fewer API calls = lower costs for paid services
- **Offline work**: Previously cached data available without internet

**Example Impact**: A 1000-protein batch analysis:

- Without cache: 1000 API calls × 0.5s = **8.3 minutes**
- With cache (90% hit rate): 100 API calls × 0.5s + 900 cached × 0.001s = **51 seconds**
- **10x faster** with caching!

Overview
--------

* **In-memory LRU** – Fastest path for repeated calls during a single session.
* **SQLite persistence** – Stores results in ``~/.tooluniverse/cache.sqlite`` by
  default so results survive restarts (path configurable via environment
  variables).
* **Per-tool fingerprints** – Each tool automatically fingerprints its source
  code and parameter schema. When either changes, the cache key changes and old
  entries are ignored.

Quick Start
-----------

Caching is enabled by default. You only need to pass ``use_cache=True`` when
calling a tool to reuse results:

.. code-block:: python

    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    result = tu.run({
        "name": "UniProt_get_entry_by_accession",
        "arguments": {"accession": "P05067"},
    }, use_cache=True)

    # Second call reuses the cached payload
    cached = tu.run({
        "name": "UniProt_get_entry_by_accession",
        "arguments": {"accession": "P05067"},
    }, use_cache=True)

For model-training style workloads you can pass a list of calls to ``tu.run`` and
enable parallel workers. Each call still consults the cache before hitting the
network:

.. code-block:: python

    import json

    batch = [
        {"name": "UniProt_get_entry_by_accession", "arguments": {"accession": acc}}
        for acc in accession_list
    ]
    messages = tu.run(batch, use_cache=True, max_workers=16)

    # Extract tool payloads (assistant metadata is at messages[0])
    payloads = [json.loads(msg["content"])["content"] for msg in messages[1:]]

Batch Execution Tips
--------------------

The batch runner performs several optimisations automatically:

* **Call deduplication** – identical ``name``/``arguments`` pairs are executed
  once and fanned out to every requester. With ``use_cache=True`` the result is
  also stored so later batches return instantly.
* **Per-tool concurrency** – each tool can advertise a
  ``batch_max_concurrency`` limit in its JSON/definition. During a batch run the
  scheduler enforces that limit so that a slow or rate-limited API does not
  seize all workers.
* **Configurable capacity** – increase
  ``TOOLUNIVERSE_CACHE_MEMORY_SIZE`` if you expect millions of cached entries.
  For example, setting it to ``5000000`` keeps roughly five million results in
  RAM (watch RSS usage and adjust according to payload size).

Configuration
-------------

Use environment variables to tune cache behavior before creating a
``ToolUniverse`` instance:

===============================  ==============================================
Variable                         Description
===============================  ==============================================
``TOOLUNIVERSE_CACHE_ENABLED``   Turn caching on/off (``true`` by default)
``TOOLUNIVERSE_CACHE_PERSIST``   Enable SQLite persistence (``true`` by default)
``TOOLUNIVERSE_CACHE_PATH``      Full path to the SQLite file
``TOOLUNIVERSE_CACHE_DIR``       Directory for the SQLite file (default:
                                 ``~/.tooluniverse``) if ``CACHE_PATH`` unset
``TOOLUNIVERSE_CACHE_MEMORY_SIZE``  Max entries in the in-memory LRU (default 256)
``TOOLUNIVERSE_CACHE_DEFAULT_TTL``  Expiration in seconds (None disables TTL)
``TOOLUNIVERSE_CACHE_SINGLEFLIGHT``  Deduplicate concurrent misses (``true``)
``TOOLUNIVERSE_CACHE_ASYNC_PERSIST``  Write cache entries to SQLite on a background thread (``true``)
===============================  ==============================================

.. seealso::
   :doc:`../reference/environment_variables` for complete environment variable reference including logging, LLM, and other configuration options.

Example configuration:

.. code-block:: python

    import os
    from tooluniverse import ToolUniverse

    os.environ["TOOLUNIVERSE_CACHE_PATH"] = "/tmp/tooluniverse/cache.sqlite"
    os.environ["TOOLUNIVERSE_CACHE_MEMORY_SIZE"] = "1024"
    os.environ["TOOLUNIVERSE_CACHE_DEFAULT_TTL"] = "3600"  # expire after 1 hour

    tu = ToolUniverse()

Inspecting & Managing Cache
---------------------------

``ToolUniverse`` exposes helpers to understand and control the cache:

.. code-block:: python

    stats = tu.get_cache_stats()
    print(stats)

    # Export persisted entries (returns an iterator of dicts)
    entries = list(tu.dump_cache())

    # Clear all cached data (both layers)
    tu.clear_cache()

Versioning & TTL
----------------

Every tool inherits a default fingerprint (`get_cache_version`) that combines
its source code and parameter schema. You can override the hook in a custom tool
if you want finer control (for example, adding a manual ``STATIC_CACHE_VERSION``
counter). Tools can also override ``get_cache_ttl`` to specify per-result
expiration.

Asynchronous Persistence
------------------------

SQLite persistence is still enabled by default, but writes now happen on a
background thread so tool calls are not blocked on disk I/O. You can tune this
behaviour in two ways:

* Set ``TOOLUNIVERSE_CACHE_ASYNC_PERSIST=false`` before constructing
  ``ToolUniverse`` to fall back to fully synchronous writes (useful when you
  need the result on disk immediately).
* Create a custom ``ResultCacheManager`` with a larger queue if you expect an
  extremely write-heavy workload:

  .. code-block:: python

      from tooluniverse import ToolUniverse
      from tooluniverse.cache.result_cache_manager import ResultCacheManager

      tu = ToolUniverse()
      tu.cache_manager.close()  # replace the default manager
      tu.cache_manager = ResultCacheManager(
          memory_size=1_000_000,
          async_queue_size=50_000,
      )

Use ``tu.cache_manager.flush()`` if you need to wait for pending writes (for
example, before shutting down a worker). ``tu.get_cache_stats()`` now reports
``pending_writes`` so you can monitor the queue depth during batch jobs.

Best Practices
--------------

* Use caching for deterministic or idempotent operations (read-only API calls,
  expensive computations, etc.).
* Set an explicit TTL when results are time-sensitive.
* Call ``tu.clear_cache()`` in long-running services if you need a fresh start.
* For hands-on demos, run ``examples/cache_usage_example.py`` (basic walkthrough)
  or ``examples/cache_stress_test.py`` (randomized load test with summary stats).
  .. code-block:: json

      {
        "name": "SlowTool",
        "type": "SlowTool",
        "batch_max_concurrency": 2,
        "parameter": {"type": "object", "properties": {}}
      }
