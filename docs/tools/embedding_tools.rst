Embedding Tools
===============

**Configuration File**: ``embedding_tools.json``
**Tool Type**: Local
**Tools Count**: 5

This page contains all tools defined in the ``embedding_tools.json`` configuration file.

Available Tools
---------------

**embedding_database_add** (Type: EmbeddingDatabase)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Append documents to an existing per-collection datastore (<name>.db + <name>.faiss). Uses the sam...

.. dropdown:: embedding_database_add tool specification

   **Tool Information:**

   * **Name**: ``embedding_database_add``
   * **Type**: ``EmbeddingDatabase``
   * **Description**: Append documents to an existing per-collection datastore (<name>.db + <name>.faiss). Uses the same L2-normalized cosine setup. Enforces model/dimension consistency with the collection.

   **Parameters:**

   * ``action`` (string) (optional)
     No description

   * ``database_name`` (string) (required)
     Existing collection/database name

   * ``documents`` (array) (required)
     List of new document texts to embed and add

   * ``metadata`` (array) (optional)
     Optional metadata per document (must match length of documents if provided)

   * ``provider`` (string) (optional)
     Embedding backend override. If omitted, falls back to collection/env.

   * ``model`` (string) (optional)
     Embedding model/deployment id override. If omitted, uses collection model or env default.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "embedding_database_add",
          "arguments": {
              "database_name": "example_value",
              "documents": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**embedding_database_create** (Type: EmbeddingDatabase)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a per-collection datastore: <name>.db (SQLite) + <name>.faiss (FAISS). Embeds documents us...

.. dropdown:: embedding_database_create tool specification

   **Tool Information:**

   * **Name**: ``embedding_database_create``
   * **Type**: ``EmbeddingDatabase``
   * **Description**: Create a per-collection datastore: <name>.db (SQLite) + <name>.faiss (FAISS). Embeds documents using the chosen provider (openai/azure/huggingface/local). Vectors are L2-normalized; FAISS index uses IndexFlatIP (cosine).

   **Parameters:**

   * ``action`` (string) (optional)
     No description

   * ``database_name`` (string) (required)
     Collection/database name (produces <name>.db and <name>.faiss)

   * ``documents`` (array) (required)
     List of document texts to embed and store

   * ``metadata`` (array) (optional)
     Optional metadata for each document (must match length of documents if provided)

   * ``provider`` (string) (optional)
     Embedding backend. Defaults: EMBED_PROVIDER, else by available creds (azure>openai>huggingface>local).

   * ``model`` (string) (optional)
     Embedding model/deployment id. Defaults: EMBED_MODEL, else provider-specific sensible default.

   * ``description`` (string) (optional)
     Optional human-readable description for the collection

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "embedding_database_create",
          "arguments": {
              "database_name": "example_value",
              "documents": ["item1", "item2"]
          }
      }
      result = tu.run(query)


**embedding_database_search** (Type: EmbeddingDatabase)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Semantic search over a per-collection datastore using FAISS (cosine via L2-normalized vectors). S...

.. dropdown:: embedding_database_search tool specification

   **Tool Information:**

   * **Name**: ``embedding_database_search``
   * **Type**: ``EmbeddingDatabase``
   * **Description**: Semantic search over a per-collection datastore using FAISS (cosine via L2-normalized vectors). Supports optional metadata filtering.

   **Parameters:**

   * ``action`` (string) (optional)
     No description

   * ``database_name`` (string) (required)
     Collection/database name to search

   * ``query`` (string) (required)
     Query text to embed and search with

   * ``top_k`` (integer) (optional)
     Number of most similar documents to return

   * ``filters`` (object) (optional)
     Optional metadata filters ('$gte', '$lte', '$in', '$contains', exact match)

   * ``provider`` (string) (optional)
     Embedding backend for the query vector. Defaults to collection/env.

   * ``model`` (string) (optional)
     Embedding model/deployment id for the query vector. Defaults to collection/env.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "embedding_database_search",
          "arguments": {
              "database_name": "example_value",
              "query": "example_value"
          }
      }
      result = tu.run(query)


**embedding_sync_download** (Type: EmbeddingSync)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download a per-collection datastore from Hugging Face Hub into ./data/embeddings as <name>.db and...

.. dropdown:: embedding_sync_download tool specification

   **Tool Information:**

   * **Name**: ``embedding_sync_download``
   * **Type**: ``EmbeddingSync``
   * **Description**: Download a per-collection datastore from Hugging Face Hub into ./data/embeddings as <name>.db and <name>.faiss.

   **Parameters:**

   * ``action`` (string) (optional)
     No description

   * ``repository`` (string) (required)
     HF dataset repo to download from (e.g., 'user/repo')

   * ``local_name`` (string) (optional)
     Local collection name to save as (defaults to repo basename)

   * ``overwrite`` (boolean) (optional)
     Whether to overwrite existing local files

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "embedding_sync_download",
          "arguments": {
              "repository": "example_value"
          }
      }
      result = tu.run(query)


**embedding_sync_upload** (Type: EmbeddingSync)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Upload a per-collection datastore to Hugging Face Hub: <name>.db and <name>.faiss, plus metadata ...

.. dropdown:: embedding_sync_upload tool specification

   **Tool Information:**

   * **Name**: ``embedding_sync_upload``
   * **Type**: ``EmbeddingSync``
   * **Description**: Upload a per-collection datastore to Hugging Face Hub: <name>.db and <name>.faiss, plus metadata files.

   **Parameters:**

   * ``action`` (string) (optional)
     No description

   * ``database_name`` (string) (required)
     Collection/database name to upload (expects <name>.db and <name>.faiss under data_dir)

   * ``repository`` (string) (required)
     HF dataset repo (e.g., 'user/repo')

   * ``description`` (string) (optional)
     Optional dataset description in the HF README

   * ``private`` (boolean) (optional)
     Create/use a private HF repo

   * ``commit_message`` (string) (optional)
     Commit message for the upload

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "embedding_sync_upload",
          "arguments": {
              "database_name": "example_value",
              "repository": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
