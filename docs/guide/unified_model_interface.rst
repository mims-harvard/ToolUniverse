Unified Model Interface
=======================

ToolUniverse wraps many interchangeable predictors. Fourteen tools can answer
"how damaging is this missense variant?", six can fold a sequence, several
predict the same ADMET endpoint. Each one takes different arguments, returns a
differently shaped payload, and reports a score on its own scale in its own
direction.

The unified model interface puts one canonical input/output contract in front
of each of those groups, so you can swap the model without rewriting the call,
run them all at once to see where they disagree, and benchmark them against
public datasets.

.. contents:: On this page
   :local:
   :depth: 2

The problem it solves
---------------------

These four tools all score the same missense variant:

.. list-table::
   :header-rows: 1
   :widths: 26 26 24 24

   * - Tool
     - Input it wants
     - Score it returns
     - Direction
   * - ``CADD_get_variant_score``
     - ``chrom/pos/ref/alt``
     - PHRED, 0-99
     - higher = damaging
   * - ``ProtVar_map_variant`` (AlphaMissense)
     - UniProt accession + ``R175H``
     - probability, 0-1
     - higher = damaging
   * - ``ESM2_score_missense_variant``
     - sequence + position + mutant AA
     - log-likelihood ratio, unbounded
     - **lower** = damaging
   * - ``GeneBe_classify_variant``
     - ``chrom/pos/ref/alt``
     - ``"Pathogenic"``
     - a label, not a number

Four coordinate systems, four scales, two directions and one string. Comparing
them by hand means writing that translation every time, and getting the
direction wrong silently inverts the answer.

Quick start
-----------

One tool per task. For variant effect:

.. code-block:: bash

   # What models exist, and can they run here? No computation, costs nothing.
   tu run predict_variant_effect '{"list_models": true}'

   # Every applicable model at once -- the default -- with a consensus
   tu run predict_variant_effect '{"variant": "TP53 R175H"}'

   # Just one model, when you know which you want and want it cheap
   tu run predict_variant_effect '{"variant": "rs28934578", "backend": "alphamissense"}'

The same shape exists for ``predict_protein_structure``,
``predict_molecular_property`` and ``predict_binding_affinity``.

There were once four tools per task -- ``predict``, ``compare``, ``list`` and
``benchmark``. The first three shared 13 of their 18 parameters and ran the
identical resolution path, so they are one tool with a ``backend`` that takes
one id, a list, or ``"all"``, plus a ``list_models`` flag. Benchmarking moved
out of the agent-facing catalogue entirely; see `Benchmarking`_.

The input is normalized for you. All of these describe the same variant and all
of them work:

.. code-block:: python

   from tooluniverse import ToolUniverse

   tu = ToolUniverse()
   tu.load_tools()

   for query in [
       {"variant": "TP53 R175H"},
       {"variant": "17-7675088-C-T"},
       {"variant": "rs28934578"},
       {"chrom": "17", "pos": 7675088, "ref": "C", "alt": "T"},
       {"gene": "TP53", "protein_change": "p.Arg175His"},
   ]:
       result = tu.run_one_function(
           {"name": "predict_variant_effect", "arguments": query}
       )
       print(result["summary"]["majority_call"])

Reading the output
------------------

``predict_*`` returns a row per model, plus a summary when several ran:

.. code-block:: text

   backend               score    norm  call          calibration
   alphamissense        0.9857   0.986  deleterious   published
   eve                   5.982   0.923  deleterious   heuristic
   esm1v                -7.744   0.798  deleterious   heuristic
   cadd                   25.9   0.647  deleterious   published
   sift                   0.04   0.583  deleterious   published
   revel                 0.922   0.922  deleterious   published

Four fields matter and are easy to misread:

``score``
   The model's own output, untouched. This is the number to quote.

``normalized_score``
   A monotone rescaling to 0-1 where higher always means more of the task's
   positive class. It exists so scores can be ranked and plotted on one axis.
   **It is not a probability** and it is not a claim that two models are
   calibrated to each other.

``calibration``
   ``published`` means the threshold and range come from the model's own paper.
   ``heuristic`` means we set them from observed score ranges. Treat a
   ``heuristic`` call as a rough indication, not a verdict.

``call`` / ``call_label``
   ``call`` uses **one vocabulary per task**, whatever the backend or endpoint:
   ``deleterious``/``tolerated`` for variant effect, ``confident``/
   ``low_confidence`` for structure, ``positive``/``negative`` for ADMET. That
   uniformity is what lets a benchmark score every model against the same
   ``positive_class``. Where a backend has a more natural domain word --
   ADMET-AI says "penetrant" for BBB and "mutagenic" for Ames -- it is kept
   alongside as ``call_label``, so the reader gets the domain term and the
   metrics get a consistent one.

``group``
   Which question the model answers. SpliceAI scores splicing disruption and
   CancerVar scores somatic oncogenicity; neither is answering "does this
   change damage the protein". They are reported under ``other_questions`` and
   left out of the consensus, because averaging them in makes a unanimous call
   look contested.

The ``summary`` gives a consensus, a ``spread``, an ``agreement`` grade and
named ``outliers``. A wide spread is the most useful thing a multi-model call
produces: it means the models genuinely disagree, which is a reason to look at
the variant rather than to trust the average.

Nothing is hidden
-----------------

Every backend is accounted for, as a result or as a skip with a reason:

.. code-block:: json

   {"backend": "nim_alphafold2", "reason": "missing_api_key",
    "detail": "Set NVIDIA_API_KEY to enable this backend."}
   {"backend": "cadd", "reason": "input_not_resolved",
    "detail": "Needs genomic.pos, which could not be derived from the input supplied."}

This matters more than it looks. Four models agreeing is convincing until you
learn the other six were skipped.

When *nothing* can run, the error carries the reasons itself rather than
pointing at a field the CLI does not print:

.. code-block:: text

   No variant_effect model could run on this input. 13 skipped
   (input_not_resolved: alphamissense, eve, esm1v, popeve and 9 more) --
   Needs protvar_canonical... Setting HF_TOKEN would enable more models.

Verified or merely written
--------------------------

``list_models`` reports ``output_verified`` per model: whether its output
mapping has been checked against a real response, or only written from a
schema. The distinction is not pedantic. Three mappings in this registry were
wrong in ways that returned a plausible **empty** result rather than an error
-- Boltz-2's nested envelope, OpenFold2's ranked structure list, and ESM-2
reading past ``data`` -- and each was caught only by looking at an actual
payload. A model whose mapping is unverified also reports
``output_unverified_reason``.

Benchmarking
------------

Benchmarking is **not** an agent-facing tool. A run takes minutes, issues
hundreds of API calls, and against a paid provider costs real money; an agent
solving a scientific task needs a prediction, not a leaderboard, and should not
be able to trigger that by setting a flag. It lives in a script instead:

.. code-block:: bash

   python scripts/run_model_benchmark.py --list-datasets

   python scripts/run_model_benchmark.py variant_effect \
       --dataset proteingym_dms --limit 40

   python scripts/run_model_benchmark.py molecular_property \
       --dataset tdc_admet --property bbb_martins --limit 24

The same machinery is importable as ``UnifiedModelBenchmarkTool``. Use it to
decide which backend to trust, and to check that a newly added backend actually
works.

Public datasets currently wired up:

.. list-table::
   :header-rows: 1
   :widths: 20 20 34 26

   * - Dataset
     - Task
     - Labels
     - Leakage risk
   * - ``proteingym_dms``
     - variant effect
     - Experimental deep-mutational-scanning fitness (87 assays)
     - None known
   * - ``clinvar_missense``
     - variant effect
     - Clinical pathogenic/benign, balanced
     - **High** for 6 backends
   * - ``tdc_admet``
     - molecular property
     - TDC ADMET leaderboard measurements
     - ADMET-AI is trained on TDC
   * - ``file``
     - any
     - Your own CSV/TSV/JSONL
     - --

Three things keep the leaderboard honest:

**Rank metrics never use** ``normalized_score``. AUROC, AUPRC and Spearman are
computed on each model's native score plus its declared direction. If they used
the normalized value, re-tuning one heuristic midpoint could reorder the
leaderboard without any model changing.

**Coverage is a first-class metric.** A model that scores 40% of a set can post
a flattering AUROC on the easy remainder, so every metric is reported with the
``n`` it was computed on, and anything below half coverage sorts last. This is
not hypothetical: an ADMET-AI run once reported AUPRC 1.000 from a single
surviving prediction, and only ``coverage`` (0.042) revealed it.

**Label leakage is named, not assumed away.** GeneBe reads ClinVar at query
time; REVEL, VEST4, MetaRNN and CADD were trained on ClinVar-derived sets;
ADMET-AI is trained on TDC. The runner flags exactly which backends are
affected, and ``proteingym_dms`` -- experimental measurements no registered
model was trained on -- is the clean comparison.

The report also includes a between-model Spearman matrix, direction-corrected
so that two models which agree but score in opposite directions read as
correlated rather than opposed.

Adding a backend
----------------

Most backends are a JSON entry in
``src/tooluniverse/data/unified_model_backends.json`` and no Python:

.. code-block:: json

   {
     "id": "mymodel",
     "task": "variant_effect",
     "tool": "MyModel_score_variant",
     "model": {"name": "MyModel", "family": "transformer", "citation": "..."},
     "needs": ["genomic.pos"],
     "input_map": {
       "chrom": "{genomic.chrom}", "pos": "{genomic.pos}",
       "ref": "{genomic.ref}", "alt": "{genomic.alt}"
     },
     "output_map": {"score": "$.data.my_score"},
     "score_type": "MyModel score",
     "transform": {"kind": "logistic", "x0": 0.0, "k": 1.0, "invert": true},
     "call": {"from": "raw", "threshold": 0.0,
              "above": "tolerated", "below": "deleterious"},
     "calibration": "published"
   }

Key fields:

``needs``
   Canonical representations this backend requires. If they are missing the
   backend is skipped with that reason rather than called with ``None``.

``input_map``
   Templates over the resolved input. A template that is exactly one
   placeholder keeps the value's type, so ``"{genomic.pos}"`` arrives as an
   ``int``.

``output_map``
   JSONPath per canonical field. Use ``{"path": ..., "agg": "max"}`` for the
   per-transcript arrays that dbNSFP-style sources return, and ``"mul"`` to
   reconcile units.

``transform``
   ``identity``, ``linear``, ``logistic``, ``categorical``, or ``none``. Use
   ``none`` when a common axis would be a lie -- a kcal/mol binding energy and
   a diffusion confidence logit are not two views of one quantity.

``from_context``
   Read a payload the resolver already fetched instead of making a call. Five
   variant-effect models share one ``ProtVar_map_variant`` reply this way.

``thread_safe``
   Set to ``false`` for a backend that runs a model **inside this process**
   rather than over HTTP. ADMET-AI (chemprop + Lightning) is not thread-safe:
   scoring a TDC set with ``item_workers=2`` raised "pop from empty list" on 23
   of 24 molecules. The run still reported success, with AUPRC 1.000 from the
   single surviving prediction -- only ``coverage`` (0.042) gave it away. The
   engine serializes these per backend while HTTP backends stay parallel.

   This is also why ``coverage`` is worth reading first on any leaderboard.

Backends whose payload is too irregular for a declarative map name a function
in ``unified_model_normalizers.py`` instead.

Architecture
------------

.. code-block:: text

   predict_* (4 tools)                          agent-facing
   scripts/run_model_benchmark.py               maintainer-facing
            |
            v
   UnifiedModelEngine                           resolve -> select -> fan out
            |
            +-- unified_model_resolvers.py      one input -> every coordinate system
            +-- unified_model_spec.py           TaskSpec / BackendSpec / ScoreTransform
            +-- unified_model_normalizers.py    irregular payloads
            +-- unified_model_metrics.py        AUROC, AUPRC, Spearman, MCC, coverage
            +-- unified_model_datasets.py       ProteinGym, ClinVar, TDC, local files
            |
            v
   data/unified_model_backends.json             the declarative registry
            |
            v
   existing ToolUniverse tools                  CADD, ProtVar, VEP, MyVariant, ESMFold, ...

Resolution pays for itself. Three of the requests it has to make anyway carry
other models' answers with them:

* ``ProtVar_map_variant`` -- the UniProt mapping, plus AlphaMissense, EVE,
  ESM-1v and popEVE (4 backends)
* ``EnsemblVEP_annotate_hgvs`` -- the protein consequence, plus SIFT and
  PolyPhen-2 (2 backends)
* ``MyVariant_get_pathogenicity_scores`` -- REVEL, VEST4 and MetaRNN
  (3 backends), fetched lazily and only when one of them is selected

So 9 of the 14 variant-effect backends cost 3 HTTP requests between them rather
than 9. Measured end to end, a full 14-model comparison of ``TP53 R175H``
issues 10 tool calls in total.
