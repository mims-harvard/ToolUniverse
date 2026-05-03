Profile & Workspace
====================

Two distinct concepts:

- **Profile** (``profile.yaml``) — *what* to load: tools, cache settings, LLM config.
- **Workspace** (``.tooluniverse/``) — *where* config and API keys live on disk.

Quick Start
-----------

.. code-block:: bash

   mkdir .tooluniverse
   echo "OPENAI_API_KEY=sk-..." > .tooluniverse/.env

   cat > .tooluniverse/profile.yaml << 'EOF'
   name: my-profile
   tools:
     categories: [literature, drug]
   EOF

   tooluniverse   # profile.yaml loads automatically

Load a profile on the fly:

.. code-block:: bash

   tooluniverse --load ./life-science.yaml

---

profile.yaml Reference
-----------------------

.. code-block:: yaml

   name: my-profile         # required
   version: "1.0"           # optional
   description: "..."

   tools:
     categories: [literature, drug, gwas]
     include_tools: [UniProt_search]
     exclude_tools: [slow_tool]

   cache:
     enabled: true
     memory_size: 256
     persist: true
     ttl: 3600

   llm_config:
     default_provider: CHATGPT
     models:
       default: gpt-4o

   hooks:
     - type: SummarizationHook
       enabled: true

   sources:
     - hf:community/genomics-tools
     - ./my-local-tools/

   extends: hf:community/base-bio-tools

   log_level: WARNING
   required_env:
     - OPENAI_API_KEY

.. note::
   Put API key *values* in ``.tooluniverse/.env``, not in profile.yaml.

---

Workspace
---------

.. code-block:: text

   .tooluniverse/
   ├── .env          ← API keys (add to .gitignore)
   ├── profile.yaml  ← auto-loaded on startup
   └── tools/        ← custom tool configs

.. code-block:: bash

   tooluniverse                          # local:  ./.tooluniverse/
   tooluniverse --global                 # global: ~/.tooluniverse/
   tooluniverse --workspace /path/to/ws  # explicit path

Priority: ``--workspace`` → ``TOOLUNIVERSE_HOME`` → ``--global`` → ``./.tooluniverse/``

**Python API:**

.. code-block:: python

   from tooluniverse import ToolUniverse

   tu = ToolUniverse()                              # local workspace
   tu = ToolUniverse(use_global=True)               # global workspace
   tu = ToolUniverse(workspace="/path/to/ws")       # explicit path
   tu = ToolUniverse(profile="./life-science.yaml") # load profile

---

Merging
-------

When ``--load`` is used, your workspace ``profile.yaml`` is the base and the
loaded file overrides only what it specifies.
