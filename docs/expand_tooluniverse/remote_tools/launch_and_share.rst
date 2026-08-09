Launch and Share a Tool
=======================

ToolUniverse can turn a typed Python function into a local Streamable HTTP MCP
server. The same command can connect that server to ToolUniverse Platform
without opening a public inbound port on the provider machine.

Define a Tool
-------------

Create ``my_model.py``:

.. code-block:: python

   from tooluniverse import remote_tool

   @remote_tool
   def predict(sequence: str, threshold: float = 0.5) -> dict:
       """Run my sequence model."""
       return model.predict(sequence, threshold=threshold)

``@remote_tool`` derives the MCP input schema from type hints and defaults. It
returns the original function unchanged, so ordinary unit tests can call
``predict(...)`` directly.

Run Locally or on a LAN
-----------------------

.. code-block:: bash

   tu serve my_model.py

The default endpoint is ``http://127.0.0.1:8080/mcp``. To make it reachable on
a trusted LAN, opt in to a non-loopback bind:

.. code-block:: bash

   tu serve my_model.py --host 0.0.0.0 --port 8080

Do not expose an unauthenticated development server directly to the public
internet.

Connect the Tool from Another Machine
-------------------------------------

Register the MCP endpoint once:

.. code-block:: bash

   tu connect http://gpu-host:8080/mcp --name my-model

On later ``ToolUniverse.load_tools()`` calls, the remote operation is discovered
and appears with the stable prefix ``my_model_``.

For a bearer-authenticated MCP endpoint, store only the environment-variable
name, never the secret itself:

.. code-block:: bash

   export MY_MCP_TOKEN=...
   tu connect https://gpu.example/mcp --name my-model --auth-env MY_MCP_TOKEN

Share Without a Public IP
-------------------------

Install the maintained platform relay once:

.. code-block:: bash

   pip install "tuplatform-connect @ git+https://github.com/tooluniverse/tuplatform.git@afbc47ff91504273cd18d11ccdae121847d1724f#subdirectory=sdk/tuplatform-connect"

Then run:

.. code-block:: bash

   tu serve my_model.py --share --name "My sequence model"

Enter a full-access private connection key at the hidden prompt. For an
unattended service, provide it in a protected ``TOOLUNIVERSE_SERVICE_KEY``
environment variable. The key is not written into the connection file or the
command line.

The provider machine makes the outbound WebSocket connection; no inbound
firewall rule or public IP is required. Open **My Computers** in ToolUniverse
Connect to inspect the discovered manifest. Publishing remains an explicit
step: import and live-test exactly one operation before making it public. The
platform does not give marketplace callers access to ``tools/list`` or sibling
tools on the same provider server.

Share an Existing MCP Server
----------------------------

If a database or model already exposes Streamable HTTP MCP, do not wrap it
again:

.. code-block:: bash

   tu serve --forward http://127.0.0.1:9000/mcp --name "Existing model"

Use a Published Tool in ToolUniverse
------------------------------------

Connect one public automated resource by its Discover URL or UUID:

.. code-block:: bash

   export TU_API_KEY=...
   tu connect https://connect.aiscientist.tools/discover/<tool-uuid>

Only that selected resource is saved. Calls go through the platform's narrow
``/tools/call`` gateway; this does not grant direct relay or sibling-tool
access.
