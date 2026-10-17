# Acceptance-harness fixtures

Inputs `verify_provider.py`'s shapers need and cannot invent.

Most providers' rungs are built by tiling a sequence, which needs nothing on
disk. A few cannot be: their input is only valid against data the model reads,
so a made-up value is refused rather than scored, and the ladder would measure
a refusal path instead of the model.

- `gpnstar_valid_positions_w128.json` — 3,207 single-nucleotide variants whose
  128 bp window lies inside a present chunk of the gpnstar kit's own sparse
  example alignment store, with each `ref` read back from that store. GPN-Star
  refuses a variant whose `ref` does not equal the alignment's own human base,
  so the rungs are drawn from here rather than generated. Derived from the kit's
  example data; regenerate it against a different store if the store changes.
