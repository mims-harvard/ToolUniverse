EUHealth tools: find and explore EU public-health datasets
=========================================================

Use these tools to:

* **Search** public EU health datasets by topic (e.g., cancer, vaccination, obesity, mental health…)
* **Deep-dive** a dataset’s landing page to surface useful outgoing links (download portals, etc.)

You do **not** need to understand embeddings or FAISS. Everything is handled automatically.
All you need is a Hugging Face token (for downloading or uploading); ToolUniverse handles embedding models, caching, and FAISS indexing under the hood.

The tools read from a local library (a small database + index)::

<user_cache_dir>/embeddings/euhealth.db
<user_cache_dir>/embeddings/euhealth.faiss

Most users will never open these files — the tools use them behind the scenes.

.. note::

   All search methods (``keyword``, ``embedding``, ``hybrid``) always work.  
   If your environment does not support vector search,
   the tools automatically fall back to ``keyword`` with a helpful message.  
   You will still get correct results.

---

Quick start (recommended): use the prebuilt library
---------------------------------------------------

1. **Get a Hugging Face token** (free account).
   Copy it once (Settings → Access Tokens).

2. **Download the ready-to-use EUHealth library:**

.. code-block:: bash

   # download from your own or any public Hugging Face repo

   export HF_TOKEN=YOUR_HF_TOKEN
   tu-datastore sync-hf download --repo "agenticx/tooluniverse-datastores" --collection euhealth --overwrite

That’s it — the files land in `<user_cache_dir>/embeddings/` and the tools will now work with the ToolUniverse agent.

Don’t have a token or prefer not to make an account?
Skip to “Build it yourself” below.

Tip:
If you previously uploaded your own copy of the EUHealth datastore (`tu-datastore sync-hf upload --collection euhealth`),
it lives at `huggingface.co/<your_username>/euhealth`.

---

Codex Configuration
---------------------------------------------------

To enable embedding/hybrid search in Codex, configure the MCP server:

1. Edit ``~/.codex/config.toml``
2. Add the ToolUniverse MCP server block with Azure credentials:

.. code-block:: toml

   [mcp_servers.tooluniverse]
   command = "/path/to/your/.venv/bin/tooluniverse-smcp-stdio"
   args = []
   env = {
     "AZURE_OPENAI_API_KEY" = "your-key-here",
     "AZURE_OPENAI_ENDPOINT" = "https://your-endpoint.openai.azure.com",
     "EMBED_PROVIDER" = "azure",
     "EMBED_MODEL" = "text-embedding-3-small",
     "OPENAI_API_VERSION" = "2024-12-01-preview"
   }

3. Restart Codex.

Without this config, searches fall back to keyword (still works, just slower).

---

Use it
------

With ToolUniverse
-----------------

In Codex (after MCP setup above), just talk to your agent in plain English. Examples:

* “**Find cancer datasets for Germany**.”
  → The agent may use the *euhealth cancer search* tool and returns a list.

* “**Show vaccination datasets in English using euhealth vaccination tools.**.”
  → The agent can call the vaccination topic tool with a language filter.

* “**Deep-dive the first 3 results and give me the best download links**.”
  → The agent calls the deep-dive tool to classify links from each dataset’s landing page (e.g., `html_portal`, `login_or_error`, etc.).

Behind the scenes, the agent uses the tools defined in
`src/tooluniverse/data/euhealth_tools.json`
(20 topics are pre-wired; you don’t have to touch this).

**OR**

Non-agent use
-------------

If you want to sanity-check from Terminal (no coding):

.. code-block:: bash

# Keyword search (works without any API keys)

tu-datastore search --collection euhealth --query cancer --method keyword --top-k 5

You should see a few JSON results (uuid, title, landing_page, etc.).
(Inside the agent you’ll get nicely formatted results. This is just a quick check.)

**That's it!!**
---

Advanced:
---------

Build it yourself (only if you can’t use the prebuilt)
------------------------------------------------------

If you can’t download from Hugging Face, you can build locally. You’ll need any one of:

* **OpenAI** (simplest): `OPENAI_API_KEY`, `EMBED_PROVIDER=openai`, `EMBED_MODEL=text-embedding-3-small`
* **Azure OpenAI**: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `OPENAI_API_VERSION`
* **Hugging Face**: `HF_TOKEN`, `EMBED_PROVIDER=huggingface`, `EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2`

Then run:

.. code-block:: bash

# pick one provider, for example OpenAI:

export EMBED_PROVIDER=openai
export EMBED_MODEL=text-embedding-3-small
export OPENAI_API_KEY=YOUR_KEY

# build (crawl the portal, normalize, embed, index)

python -m tooluniverse.euhealth.euhealth_live

This writes the same two files to `<user_cache_dir>/embeddings/`.
Re-running is safe; it adds new items and skips duplicates.

.. note::

   A self-built datastore is treated as a **custom build**, so the tools will
   **honor embedding/hybrid directly** with whichever provider/model you used.

---

Optional (for understanding):
-----------------------------

How search methods are chosen
-----------------------------------

The public tools accept ``method="keyword"|"embedding"|"hybrid"`` (default ``"hybrid"``).

The EUHealth library downloaded from Hugging Face is built using:

**Azure OpenAI + text-embedding-3-small**

To keep everything working smoothly:

1. **If your environment resolves to Azure + text-embedding-3-small**
   (e.g., you set):

   .. code-block:: bash

      export EMBED_PROVIDER=azure
      export EMBED_MODEL=text-embedding-3-small
      export AZURE_OPENAI_API_KEY=...
      export AZURE_OPENAI_ENDPOINT=...

   → the tools perform **true vector search** (embedding or hybrid).

2. **Otherwise**  
   → ToolUniverse **automatically falls back to keyword search** so everything keeps working.

   You will see a message like:

   ``Requested 'embedding' is not available without Azure + text-embedding-3-small. Falling back to 'keyword'.``

3. **If you build the EUHealth library yourself**  
   using any provider/model (OpenAI, Azure, HuggingFace, local),  
   the requested method is **always honored with no fallback**.

This design ensures the **prebuilt library “just works” everywhere**,  
while advanced users can opt-in to embedding search.

What each tool returns
----------------------

**Topic search tools** (e.g., cancer, vaccination, mental health) return a list of:

.. code-block:: json

   {
     "uuid": "…",
     "title": "…",
     "landing_page": "https://…",
     "license": "…",
     "keywords": ["…"],
     "themes": ["…"],
     "language": ["…"],
     "spatial": "…",
     "snippet": "first ~280 chars of text"
   }


**Deep-dive tool** (for selected datasets) returns:

.. code-block:: json

   {
     "uuid": "…",
     "title": "…",
     "landing_page": "…",
     "candidates": [
       {
         "url": "…",
         "classification": "html_portal | login_or_error | error",
         "http_status": 200,
         "content_type": "text/html",
         "notes": "…"
       }
     ]
   }

---

Common questions
-------------------

* **Do I need to configure anything in code?**
  No, the tools are already registered. If the library exists in `<user_cache_dir>/embeddings/`, you can just ask the agent.

* **Can I filter by country/language?**
  Yes, just say ask for it in your query (“Germany”, “DE”, “English”, “en”). The tools accept both plain names and codes.

* **What if some links say `login_or_error`?**
  Some portals require accounts or block automated requests. The tool still shows you what’s there.

* **My agent says the EUHealth library isn’t found.**
  Make sure the files exist at::

  <user_cache_dir>/embeddings/euhealth.db
  <user_cache_dir>/embeddings/euhealth.faiss

  If not, use the **Quick start** download or the **Build it yourself** step.

* **Why did embedding fall back to keyword?**
Either the Codex MCP config (above) isn't set, or your environment doesn't have Azure + text-embedding-3-small configured. Add the config block to `~/.codex/config.toml` and restart Codex to enable embedding search.

* **Where does my data upload now?**
  When you run `tu-datastore sync-hf upload --collection euhealth`, ToolUniverse automatically detects your `HF_TOKEN` and uploads to **your own Hugging Face namespace** (`your_username/euhealth`).
  The `--repo` flag is optional; if omitted, it defaults to `<your_username>/<collection>`.

---

You’re set
----------

* Prefer the **Quick start** download.
* Ask the agent normal questions (“Find cancer datasets in Germany”). Or use tu-datastore search from Terminal if you don't want to use agents.
* Use **deep-dive** when you want the actual outgoing links.

If you later want the nitty-gritty (how we crawl, embed, index), see the developer notes in:
`src/tooluniverse/euhealth/*` and `src/tooluniverse/database_setup/*`.

.. note::

Want to build or share your **own** searchable dataset or tool (like EUHealth)?
See: :doc:`make_your_data_agent_searchable` - the 3-minute guide to creating and publishing your own ToolUniverse datastore.