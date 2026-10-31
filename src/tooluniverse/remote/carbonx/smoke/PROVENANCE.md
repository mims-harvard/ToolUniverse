# Where the smoke input comes from

`hbb_coding.json` is the reference sequence from **Carbon-X's own model card**,
in the "How to use" example: the first 55 bases of the human *HBB* (beta-globin)
coding sequence, `ATGGTGCATCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGG`. Read in
frame from the ATG it translates to `MVHLTPEEKSAVTALWGK`, which is beta-globin's
N-terminus — so the sequence can be checked rather than taken on trust, and a
transcription error would not translate.

It was chosen for three reasons:

* **It touches no third party at run time.** The bases are in this file. The
  smoke needs the GGUF and the engine and nothing else, so
  `tu remote setup carbonx --only smoke` depends on no network.
* **It is the example upstream picked to demonstrate the model**, which makes a
  wrong answer here informative rather than ambiguous.
* **It is short.** 55 bases is ten DNA tokens; the smoke's cost is the 160
  tokens of answer, not the prompt.

The question asks for coding vs non-coding, which this sequence settles
unambiguously: it begins at a start codon and reads as a known protein. The
smoke asserts that an answer came back with token counts, not that the answer
is correct — correctness is checked in the provider README's acceptance run,
where the model is also given the sickle-cell variant (HBB E6V, `GAG`→`GTG` at
codon 6) that the same model card uses as its variant example.
