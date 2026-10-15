NVIDIA protein model outputs
============================

``NvidiaNIM_proteinmpnn`` designs sequences from a backbone;
``NvidiaNIM_esmfold`` predicts a monomer structure from a sequence. They require
``NVIDIA_API_KEY``. The output format is selected by the tool configuration,
so an HTTP ``text/plain`` response does not automatically mean PDB coordinates.

Reading results
---------------

Check ``status`` before saving or evaluating a prediction. HTTP 200 can contain
an inner model failure; ToolUniverse returns those responses with
``status="error"`` and retains the native JSON in ``data``. An empty or malformed
PDB JSON envelope is also an error, rather than a successful structure.

ProteinMPNN JSON responses retain the native fields (including ``mfasta`` and
any scores) under ``data``. Plain Multi-FASTA responses expose the complete text
as both ``data["mfasta"]`` and ``sequences``, with ``format="mfasta"``.

ESMFold returns PDB text as ``data`` and ``structure``, with ``format="pdb"``.
When a JSON response contains multiple PDB strings, ``structures`` retains all
of them in their original order; ``structure`` remains the first one for
existing callers. A valid single-structure result omits ``structures``.

.. code-block:: python

   # result is the complete response from tu.run_one_function(...).
   if result.get("status") != "success":
       raise RuntimeError(result.get("error", "Prediction failed"))

   if result.get("format") == "mfasta":
       fasta = result["data"]["mfasta"]
   elif result.get("format") == "pdb":
       pdbs = result.get("structures", [result["structure"]])

In a multi-model workflow, retain each original response and all returned
samples alongside model names, versions, inputs and seeds. Count failed calls
separately from completed predictions. Structural confidence scores alone do
not establish binding affinity or pH selectivity.

NVIDIA documents ProteinMPNN's output as Multi-FASTA in its
`ProteinMPNN overview <https://docs.nvidia.com/nim/bionemo/proteinmpnn/1.1.0/overview.html>`_.
