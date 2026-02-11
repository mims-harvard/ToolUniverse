===============================================
Make Your Data Agent-Searchable in ToolUniverse
===============================================

**Goal:**  
Turn your text or JSON data into an **agent-searchable collection** once with ``tu-datastore``.  
After that, any **ToolUniverse agent** can query it as a tool — no extra setup or paths required.  
Optionally, share your collection and tool definition on **Hugging Face** so others can use it too.


What you’ll do
--------------

1. Install ToolUniverse  
2. Choose an embedding service (OpenAI, Azure, Hugging Face, or local)  
3. Build your **collection** — your searchable library  
4. Create an **agent tool JSON** that points to it
5. Install your tool so ToolUniverse/Codex auto-detects it
6. (Optional) Share it via Hugging Face for others to use  

---

1. Install
---------

.. code-block:: bash

   # From the repo root
   python -m venv .venv && source .venv/bin/activate
   pip install tooluniverse

If you’re developing locally, use:

.. code-block:: bash

   pip install -e .

If the ``tu-datastore`` command isn’t found (e.g., running from source),
run the module directly:

.. code-block:: bash

   python -m tooluniverse.database_setup.cli --help

### Available ``tu-datastore`` commands

.. code-block:: text

   build            # Build from JSON
   quickbuild       # Build from folder
   search           # Keyword/embedding/hybrid search
   sync-hf upload   # Upload DB/FAISS (+ tool JSONs)
   sync-hf download # Download DB/FAISS (+ tool JSONs)
   add-tool         # Install a tool JSON into ~/.tooluniverse/data/user_tools

---

2. Choose ONE embedding service
----------------------------

Create a file named **.env** and paste one block below, then run ``source .env``.

**Azure OpenAI**

.. code-block:: bash

   EMBED_PROVIDER=azure
   AZURE_OPENAI_API_KEY=YOUR_KEY
   AZURE_OPENAI_ENDPOINT=https://YOUR_RESOURCE.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=text-embedding-3-small
   OPENAI_API_VERSION=2024-06-01 # example 
   EMBED_MODEL=text-embedding-3-small # your *deployment* name

**OpenAI**

.. code-block:: bash

   EMBED_PROVIDER=openai
   OPENAI_API_KEY=YOUR_KEY
   EMBED_MODEL=text-embedding-3-small

**Hugging Face**

.. code-block:: bash

   EMBED_PROVIDER=huggingface
   HF_TOKEN=YOUR_TOKEN
   EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2 # example

**Local/offline**

.. code-block:: bash

   EMBED_PROVIDER=local
   EMBED_MODEL=all-MiniLM-L6-v2 # example local model name

---

3. Build your agent-searchable collection from your raw data
----------------------------------------------------------

All you need is either a **folder of text files** or a **JSON list of documents**.

**Option 1: QuickBuild (recommended)** — point at a folder of text files.

.. code-block:: bash

   tu-datastore quickbuild --name toy --from-folder ./my_texts

What goes in `./my_texts`:
* **Supported:** ``.txt`` and ``.md`` (your raw data files)

Each file in  `./my_texts` automatically gets converted into a document with the following information:
* ``doc_key`` = relative file path (e.g., ``biology/mitochondria.md``)  
* ``text`` = file contents  
* Basic metadata (title, path, source) which is auto-filled  

**Example:**
.. code-block:: text

my_texts/
├── cells_intro.txt
├── biology/
│   └── mitochondria.md
└── endocrine/
└── insulin.md

**Result of running QuickBuild ( * Collection name: ``toy`` )**

* **One collection:** `toy`
* **One SQLite DB:** `<user_cache_dir>/embeddings/toy.db`
* **One FAISS index:** `<user_cache_dir>/embeddings/toy.faiss`


We automatically detect your embedding model and dimension from ``.env`` or CLI flags.  
Safe to re-run — duplicates are skipped.

---

**Option 2: Build from structured JSON**

Use this when you want explicit IDs and metadata.

.. code-block:: bash

   tu-datastore build --collection toy --docs-json my.json

**Example JSON (can add several documents within one JSON):**

.. code-block:: json

   [
     {
       "doc_key": "d1",
       "text": "Mitochondria is the powerhouse of the cell.",
       "metadata": {"title": "Cells", "tags": ["Biology"]}
     },
     {
       "doc_key": "d2",
       "text": "Insulin regulates glucose.",
       "metadata": {"title": "Endocrine", "tags": ["Medicine"]}
     }
   ]

Produces the same ``toy.db`` and ``toy.faiss`` artifacts as QuickBuild.
Note: 
* **Required:** `doc_key` (unique per collection), `text`
* **Optional:** `metadata` (any JSON object), `text_hash` (string)
---

4. Create the agent tool for your collection
-----------------------------------------

Now the last step is to tell ToolUniverse how agents should search your dataset by creating a small **tool JSON**.

Example:
Save as ``toy_search_tool.json``:

.. code-block:: json

   [
     {
       "name": "toy_search", # choose an appropriate name for your tool 
       "description": "Provides biology data on cells, mitochondria, endocrine topics, and insulin.",  # make sure "description" is as detailed as possible so the agent gets a good explanation of what your data is
       "type": "EmbeddingCollectionSearchTool",
       "fields": {"collection": "toy"}, # name of the data collection this tool will look into
       "parameter": {
         "type": "object",
         "properties": {
           "query":  {"type": "string",  "description": "Search text"},
           "method": {"type": "string",  "default": "hybrid", "enum": ["keyword", "embedding", "hybrid"]},
           "top_k":  {"type": "integer", "default": 5},
           "alpha":  {"type": "number",  "default": 0.5, "description": "Hybrid mix (0 = keyword, 1 = embedding)"}
         },
         "required": ["query"]
       }
     }
   ]

> **Note:** Tool files must be a JSON **array** (even if only one tool).

If you want your tool to load automatically in all ToolUniverse or Codex sessions (explained below):

.. code-block:: bash

   tu-datastore add-tool toy_search_tool.json

---

5. Install your tool for automatic discovery (recommended)
-----------------------------------------------------------

ToolUniverse automatically loads any tool placed in:

```

~/.tooluniverse/data/user_tools/

```

Install your tool with:

.. code-block:: bash

   tu-datastore add-tool toy_search_tool.json

This copies your tool into the auto-load directory:

```

~/.tooluniverse/data/user_tools/toy_search_tool.json

```

Optional arguments:

.. code-block:: bash

   tu-datastore add-tool toy_search_tool.json --name toy.json
   tu-datastore add-tool toy_search_tool.json --overwrite # overwrites json file if exists

Once installed, **any ToolUniverse or Codex session** will immediately expose your tool:

```

tu.tools.toy_search(...)

```

**You are done! ToolUniverse agents now have access to your data collection and associated tool to use in their work as an AI Scientist!**

How it works
------------

* ToolUniverse has a built-in **search tool** (`EmbeddingCollectionSearchTool`) that queries the agent-searchable dataset you’ve built from your raw data. `
* Your JSON simply tells ToolUniverse **which collection** to open and **which search options it supports**:
      - the user’s search text (``query``),
      - search type (``method``: keyword/embedding/hybrid),
      - number of results (``top_k``),
      - You can optionally control the hybrid mix with alpha (``alpha``).

ToolUniverse automatically resolves paths in ``<user_cache_dir>/embeddings/``.  
* Agents can now call ``toy_search`` immediately after loading your JSON — no local setup needed.  

---

6. Share or back up via Hugging Face (optional)
--------------------------------------------

After making your agent-searchable dataset you can share it publicly. You can also download other's public agent-searchable datasets and their tools so that you can use the community's data and tools in your research!

This is the **final step for making your collection “public-ready.”**
Use it when you want to:
* publish your dataset so anyone can search or integrate it,
* share your work across teammates or servers, or


**Upload (defaults to your username/collection if --repo is omitted):**

.. code-block:: bash

   # uploads your agent searchable dataset to your HF
   tu-datastore sync-hf upload --collection toy

   # can override HF destination and make public:
   tu-datastore sync-hf upload --collection toy --repo "your_username/my-toy-db" --no-private

   # add tool JSON(s) to the dataset so others have your ToolUniverse agent for the dataset you uploaded above. This way others have the full pipeline to add your data to their own ToolUniverse
   tu-datastore sync-hf upload --collection toy --tool-json toy_search_tool.json

**Download (works for public repos; private requires permission or a valid HF token):**

.. code-block:: bash

   # Download DB + FAISS only (preserves existing files unless --overwrite)
   tu-datastore sync-hf download --repo "your_username/my-toy-db" --collection toy --overwrite

   # Download DB + FAISS + tool JSONs (downloads any *.json in the dataset) 
   tu-datastore sync-hf download --repo "your_username/my-toy-db" --collection toy --overwrite --include-tools

All files download into your local cache at: ``<user_cache_dir>/embeddings/<collection>/``.

How it works
------------

* Using the above commands, ToolUniverse syncs your local datastore, the `.db` and `.faiss` files (e.g. `<user_cache_dir>/embeddings/toy.db` and `<user_cache_dir>/embeddings/toy.faiss`) and associated JSON tools you create to search the associated `.db` and `.faiss` (e.g. `toy_search_tool.json`) directly with your **Hugging Face account**. This way others can download and use the exact same searchable dataset you built with ToolUniverse agents — complete with your embeddings and metadata.

-------------------------------------------------------------


Optional
--------

Use your dataset manually (for quick exploration without an agent)
------------------------------------------------------------------
If you’re prototyping in a notebook or wiring custom logic, you can directly search your searchable dataset.

**CLI search**

.. code-block:: bash

   # Exact word match
   tu-datastore search --collection toy --query glucose --method keyword
   # Embedding (semantic)
   tu-datastore search --collection toy --query glucose --method embedding
   # Hybrid (recommended): best of both (alpha 0=words only, 1=embeddings only)
   tu-datastore search --collection toy --query glucose --method hybrid --alpha 0.5

**Example result**:

.. code-block:: json

   [
     {
       "doc_id": "2",
       "doc_key": "d2",
       "text": "Insulin is a hormone regulating glucose.",
       "metadata": {"title":"Endocrine","tags":["Medicine"]},
       "score": 0.83
     }
   ]

   

Optional (for developers):
--------------------------

Programmatic use of customized tools (rather than agent use)
------------------------------------------------------------------

**A) Create and run your tool directly in Python (no agent)**

.. code-block:: python

   from tooluniverse.database_setup.generic_embedding_search_tool import EmbeddingCollectionSearchTool

   tool = EmbeddingCollectionSearchTool(tool_config={"fields": {"collection": "toy"}})
   results = tool.run({"query": "glucose", "method": "hybrid", "top_k": 5})
   print(results)

**B) Register a tool and include it in all ToolUniverse tools for this Python session. Then search your tool directly within ToolUniverse (temporary for this python session)**

.. code-block:: python

   from tooluniverse import ToolUniverse
   from tooluniverse.database_setup.generic_embedding_search_tool import EmbeddingCollectionSearchTool

   tu = ToolUniverse()

   tool_cfg = {
     "name": "toy_search",
     "type": "EmbeddingCollectionSearchTool",
     "fields": {"collection": "toy"},
     "parameter": {
       "type": "object",
       "properties": {
         "query":  {"type": "string"},
         "method": {"type": "string",  "default": "hybrid", "enum": ["keyword","embedding","hybrid"]},
         "top_k":  {"type": "integer", "default": 5},
         "alpha":  {"type": "number",  "default": 0.5}
       },
       "required": ["query"]
     }
   }

   tu.register_custom_tool(EmbeddingCollectionSearchTool, tool_config=tool_cfg)
   results = tu.tools.toy_search(query="glucose", method="hybrid", top_k=5)
   print(results)

**C) Load your custom JSON tool inside ToolUniverse to use your searchable dataset (same as agents do, but manually in Python)**

This lets you interact with your tool exactly the way an agent would but directly from your Python session, for testing or local exploration.

.. code-block:: python

   from tooluniverse import ToolUniverse

   tu = ToolUniverse()
   tu.load_tools(tool_config_files={"local": "toy_search_tool.json"})

   # Now any agent (or you) can call:
   results = tu.tools.toy_search(query="glucose", method="hybrid", top_k=5)
   print(results)

Results contain: ``doc_key``, ``text``, ``metadata``, ``score``, and a short snippet.

-------------------------------------------------------------

Mini FAQ
--------
- **Do I need EMBED_PROVIDER/EMBED_MODEL?** You only need EMBED_PROVIDER/EMBED_MODEL for building collections or for embedding/hybrid search. ``keyword`` search and ``sync-hf`` do **not** require an embedding provider/model.

- **What’s “hybrid” search?** A smart mix of exact words + meaning. Start here.

- **Do I need to set an embedding dimension?** No — it’s detected automatically.  

- **Changed models?** Rebuild; dimensions are auto-handled. 

- **Re-running build?** Safe. Duplicates (same ``doc_key``) are ignored; new text is added.  

- **“No results”?** Try ``--method keyword`` or confirm the ``--collection`` name.  

- **Where are my searchable datasets stored locally?** ``<user_cache_dir>/embeddings/``. Examples:  
  - macOS → ``~/Library/Caches/ToolUniverse``  
  - Linux → ``~/.cache/tooluniverse``  
  - Windows → ``%LOCALAPPDATA%\\ToolUniverse``  

- **Where do my tools live?**  
  ``~/.tooluniverse/data/user_tools/`` (auto-loaded)
  
- **Where does my data upload?** ``tu-datastore sync-hf upload`` targets your **own** HF account by default (based on your token).  

- **What is the`EmbeddingCollectionSearchTool`?**
  -`EmbeddingCollectionSearchTool` is a **real ToolUniverse tool** (registered in code). Check ``src/tooluniverse/database_setup/generic_embedding_search_tool.py`` for details.  
  - We don’t ship a pre-bound JSON for it because the collection name is yours.
  - Use the example JSON under ``docs/tools/``, set ``"fields.collection"`` to your collection (e.g., ``"toy"``), and load it
  - If you prefer not to create a JSON, you can also instantiate the tool directly from Python and pass the collection name via ``fields``

- **Can I upload my tool with the datastore?** Yes, pass one or more files via ``--tool-json`` during ``sync-hf upload``; they’re stored at the dataset root.

- **How do I pull tool JSONs too?** Use ``--include-tools`` with ``sync-hf download`` to download any ``*.json`` in the dataset.

- **Is upload private by default?** Yes auto upload **private** datasets unless you opt out (CLI: ``--no-private``; tool: set ``"private": false``).

- **Do I have to pass --db to search/build?**  
  - No — both commands write and read from your cache automatically.  
  - Use `--db` only if you want a **custom output path** (for example, a shared directory).  
  - When using the **JSON tool** or agents, no paths are ever needed — everything resolves automatically from the collection name.

- **When building my custom datastore what if I want to use different provider(s) and/or model(s) for my embeddings?** You can use a different provider/model when building your searchable datastore like we do in the example below — just make sure that if you want to keep the initial provider/model based datastore, you give this new build's collection a new name or else it will override the initial build.

.. code-block:: bash

    tu-datastore build --collection toy --docs-json my.json --provider openai --model text-embedding-3-small 

- **Can I have JSON files in a folder I use with 'quickbuild'?** `quickbuild` does **not** read JSON files in a folder; use `build --docs-json` for JSON ingestion.

---

Glossary
--------

- **Collection** — your named library of texts (e.g., ``toy``).  
- **doc_key** — unique ID per document
- **text** — the searchable content.  
- **metadata** — optional tags or annotations.  
- **FAISS** — vector index used for “search by meaning”.   You don’t need to configure its dimensions—**detected automatically**.  
- **tu-datastore** — CLI for building, searching, and syncing collections.

---

Deeper Reference
----------------

- CLI orchestration – ``src/tooluniverse/database_setup/cli.py``  
- Content store / keyword search – ``src/tooluniverse/database_setup/sqlite_store.py``  
- Vector index (FAISS) – ``src/tooluniverse/database_setup/vector_store.py``  
- Embedding providers – ``src/tooluniverse/database_setup/embedder.py``  
- Hybrid retrieval – ``src/tooluniverse/database_setup/search.py``  
- Build/search pipeline – ``src/tooluniverse/database_setup/pipeline.py``  
- HF upload/download helpers – ``src/tooluniverse/database_setup/hf/sync_hf.py``  
- Programmatic build/sync tools – ``src/tooluniverse/database_setup/embedding_database.py`` / ``embedding_sync.py``  (Check these files for support on using `build`, `sync-hf` as first-class ToolUniverse tools, so you can call them programmatically in CI, notebooks, or an agent if you prefer.)
- Agent search tool – ``src/tooluniverse/database_setup/generic_embedding_search_tool.py``  
- Example tool JSON – ``docs/examples/make_your_agent_searchable_example/make_your_agent_searchable_example_JSON.json``  

**Developer note: database_setup tests**

ToolUniverse includes 8 tests under `tests/test_database_setup/`:
* **2 core tests** (SQLite + FAISS) always run automatically and require *no* API keys.
* The **other 6 tests** exercise real embedding pipelines (OpenAI, Azure, HF, or local). These are **skipped by default** unless you export:

  ```bash
  export EMBED_PROVIDER=azure|openai|huggingface|local
  export EMBED_MODEL=your-model-or-deployment
  ```

You can run all embedding-enabled tests with:

```bash
pytest -m api
```

These optional tests pass for all supported providers once credentials are set.

---

With these steps, your data becomes **searchable, agent-ready, and shareable** — powering everything from local testing to public, reproducible ToolUniverse tools.


