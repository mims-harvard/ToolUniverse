# Carbon-X as a ToolUniverse remote tool

Carbon-X is a 14.8B-parameter decoder-only language model trained jointly on
DNA sequences and natural-language text, released 2026-10-21 under the
**Apache-2.0 License** with open weights. It is a collaboration between
Hugging Face, Zhongguancun Academy, and the Telethon Institute of Genetics and
Medicine / University of Naples Federico II. You give it raw DNA inside an
ordinary chat message and it answers in English, with its reasoning.

DNA and text share one token stream in one decoder; there is no separate DNA
encoder. A hybrid tokenizer keeps the Qwen3 BPE vocabulary for text and encodes
DNA as non-overlapping 6-mers, so one DNA token covers six bases.

- Model card and weights: <https://huggingface.co/HuggingFaceBio/Carbon-X>
- The GGUF quantizations this provider serves:
  <https://huggingface.co/HuggingFaceBio/Carbon-X-GGUF>
- Source: <https://github.com/huggingface/carbon>

## What it does, and the four things it does not

`carbonx_ask_dna` takes named DNA sequences and a question and returns prose.
Across the five benchmarks on its model card it averages 66.7% with thinking
disabled — ahead of every other open model the vendor evaluated, close to
GPT-6.1 Sol at about 1/1,800 of the cost per problem, and best in class on
coding-variant effects (74.9) and next-base prediction (39.4).

It is **not clinically validated** and must not drive a medical decision.

It does **not** design sequences — quality degrades when it is asked to
generate long DNA, and it was trained to read and explain, not to create.

It is **weak where its own benchmark says so**: splice sites 29.8% and histone
marks 34.6% on GenomeQA, against 93.2% for organism group and 90.0% for motifs.

And it **miscounts**. Positions, coordinates and edits in long sequences are
unreliable; upstream's own advice is to compute them in code and pass the
answer in as `context`.

## Prose is the output, and that is unusual here

Every other remote provider in this repository returns structured data. This
one returns an English answer, because that is what the model emits and what
every published number scores. A tool that returned a number would mean
inventing a parser upstream does not have and reporting a confidence this
model does not produce.

What keeps it from being a chatbot behind a GPU is that **`sequences` is
required and must be non-empty**. A question with no DNA in it is refused by
the tool rather than forwarded.

Sequences are passed by name — `{"reference": "ACGT…", "variant": "ACGT…"}` —
and the question refers to them by those names. That is upstream's own agent
recipe, and the reason is that language models miscopy long sequences: the
caller names them and the code substitutes the bases.

## The likelihood operation upstream documents is not here

Upstream's `carbon-dna` skill has a second command, `compare`, which ranks
equal-length variants by sequence log-likelihood. It is built on
`prompt_logprobs` and `prompt_token_ids`, which are **vLLM extensions**.
llama-server b11742 implements neither, and an OpenAI-style `echo: true` with
`logprobs: 0` returns `"logprobs": null` — checked against the running engine
rather than inferred. So this provider cannot score likelihoods. That is a
real cost of the quantized path, and it is stated rather than worked around.

## Q8_0 under llama.cpp, and why each half of that was chosen

**Q8_0 rather than bf16.** bf16 is 29.7 GB. Q8_0 is 15.8 GB and the vendor's
own re-run of two benchmarks through `llama-server` puts it inside the stated
standard error of the original served by vLLM: FrontierVEP 69.1 against 70.4
(±1.5), NextBase 39.7 against 39.4 (±1). Half the card for no measurable loss.

**llama.cpp rather than Transformers.** Carbon-X's DNA tokenizer is custom
Python loaded with `trust_remote_code=True`, which no GGUF runtime can
execute — and the model card says so, flatly: "llama.cpp and other GGUF
runtimes are not supported". That sentence is now out of date. llama.cpp
**b11742** (PR #30825, merged 2026-10-19) added a native `HybridDNATokenizer`,
the vendor published a GGUF repository of their own that requires exactly that
build, and they report identical token ids and detokenized text against the
Python tokenizer over 1,000 benchmark prompts and 36 edge cases. Older builds
load the same file and tokenize DNA **wrongly, without saying so**, which is
why b11742 is a pinned floor and not a preference.

Verified here rather than taken on trust: the engine tokenizes
`Describe this sequence: ACGTACGATTCA` as
`Describe`, ` this`, ` sequence`, `:`, ` `, `<dna>`, `ACGTAC`, `GATTCA`,
`</dna>` — exactly the output the model card prints for the Python tokenizer.

## The model lives in a child process, and the kernel is what reaps it

This is the first provider on the remote-tool standard whose model is not held
by the worker. There is no llama.cpp Python binding at b11742, and building
one would mean compiling CUDA for `sm_121` from source; the published
`ubuntu-cuda-13.4-arm64` tarball already carries an `sm_121a` cubin, confirmed
with `cuobjdump --list-elf`. So the worker starts upstream's `llama-server`
and speaks HTTP to it over a second Unix socket. The worker itself needs
**nothing but the standard library**.

That creates one hazard and it is handled by the kernel, not by Python. The
shared `worker_base` ends a stranded worker with `os._exit(0)`, which runs no
`atexit` hook, no `finally` and no signal handler — and a `SIGKILL` runs even
less. A child started the ordinary way survives both and keeps holding 16 GiB
that nothing can reach, which is precisely the failure the orphan watchdog
exists to prevent, reintroduced one process deeper. The engine is therefore
started with **`PR_SET_PDEATHSIG(SIGKILL)`**. Measured on this machine: with
the flag, the child dies when the parent calls `os._exit(0)` and when the
parent is `SIGKILL`ed; without it, the child survives `os._exit(0)`.

The engine's socket goes in a short private temporary directory, not beside
the worker's. `sun_path` is 108 bytes, and the first attempt to run this
provider's measurements from a scratch directory failed with `AF_UNIX path too
long` at exactly 108.

## Two things are pinned, in two places, for the same reason

- **The weights** — `carbon-x-q8_0.gguf`, 15,755,742,080 bytes, sha256
  `48241178…`. That digest is upstream's own: it is the `lfs.oid` the Hugging
  Face API publishes, confirmed equal to the sha256 of the bytes measured
  here. It is declared in `provider.toml` and re-checked before every launch.
- **The engine** — every llama.cpp b11742 file the server loads, by size and
  sha256, per architecture, in `environment/llamacpp-b11742.pins`, checked by
  `launch.py` before the worker starts. These files are *executed*, which is a
  stronger reason to pin them than the one that justifies pinning weights.

The engine is not in `[[weights.files]]` because that list cannot vary by
architecture: the aarch64 tarball ships 16 loadable files and the x86_64 one
22, with different names and digests, and listing either would make the
manifest refuse the other machine. The fetch selects the tarball from
`uname -m`, checks it against its GitHub release digest, and refuses with
exit 3 on any other architecture rather than guessing.

## The footprint is set at load and does not move

llama.cpp allocates weights, KV cache and compute buffers when the model
loads, so `-c` decides the budget and requests do not change it. Measured on
the verified card, each row a whole session of load plus four requests from
72 bp to 8,208 bp:

| `-c`  | load  | at load   | across four requests |
|-------|-------|-----------|----------------------|
|  8192 | 11.1s | 17.11 GiB | 17.07 → 17.23        |
| 16384 | 13.8s | 18.12 GiB | 18.01 → 18.20        |
| 40960 | 14.9s | 21.95 GiB | 22.02 → 22.20        |

**There is no session ratchet**, which is worth saying because the previous
provider added to this standard was budgeted wrongly twice by assuming there
was none: BioEmu-2 reserved 18.04 GiB for a request as a fresh worker's first
and 21.15 GiB for the identical request as its second. The 0.16 GiB of drift
above is a shared 128 GB unified pool breathing, not this process growing, so
the declared budget can sit closer to the measurement than a torch provider's.

This provider runs at **`-c 8192`**. The pool reserves the declared budget on
*every* request, so context bought "just in case" is paid for by every
co-tenant all the time; 40,960 costs 4.8 GiB more — a 28% permanent surcharge
— to serve input lengths upstream has not evaluated. Mid-training used
8,192-token sequences and post-training stayed below 16k. The longest input in
the vendor's hardest benchmark, FrontierVEP, is 8,192 **bases**, which is 1,406
tokens here. 8,192 tokens of context leaves 7,168 for a prompt — roughly 43
kbp of DNA, five times that benchmark — and 1,024 for an answer.

**Speed is the honest weakness.** Generation measured 11.9–13.9 tokens per
second and prompt evaluation 300–770, so a 1,024-token answer takes about 80
seconds. That is memory bandwidth on this card, and `max_tokens` is the main
lever a caller has over latency.

## What the model got right and wrong here

This provider does not validate Carbon-X's accuracy and nothing in it could.
What follows is what was observed while verifying the deployment, reported
because a user will meet the same thing in their first hour.

**Right, and checkably so.** Asked whether the smoke sequence is coding, the
model answered yes and volunteered that it translates to `MVHLTPEEKSAVTALWGK`
— which it does. That is not a coin flip: a wrong DNA tokenization could not
produce the right peptide, which is why it is the check the acceptance run
makes.

**Wrong, twice, on 55-base inputs.** Given the model card's own variant
example — human *HBB* `GAG`→`GTG`, which is Glu→Val, the sickle-cell
substitution — it answered **benign on 4 of 5 seeds** when the reference and
variant were passed as named `sequences` with the position supplied in
`context`. Two of those answers identified the Glu→Val change correctly and
then asserted it is *not* the sickle substitution; one described the sickle
variant as "a G>A substitution at position 6". With the card's own
`Reference: / Variant:` wording written into the `question` instead, the same
model answered **pathogenic on 3 of 3 seeds**. Asked which organism the same
55 bases came from, it answered "a positive-sense single-stranded RNA virus
such as a coronavirus".

**What to take from that.** Three things, and not a fourth:

1. **The answer is a sample, not a verdict.** Sampling is on by default
   (temperature 0.6, top-p 0.95, top-k 20) because that is what every
   published benchmark number was produced with. Pass a `seed` to repeat one,
   and do not treat a single call as the model's opinion.
2. **Prompt layout changed the answer** on this one variant, 1-of-5 against
   3-of-3. That is eight samples on one question, so it is suggestive and not
   established — but if you are asking a variant question, writing
   `Reference: …` and `Variant: …` into the `question` is what upstream's own
   example does.
3. **55 bases is a thin prompt.** FrontierVEP gives the model up to 8,192
   bases of reference; the card warns that without context the model may
   invent a sequence's identity or function, and the coronavirus answer is
   exactly that. Give it the window and the annotations you have.

The fourth thing, which these observations do **not** support, is any
conclusion about Q8_0. Distinguishing quantization from a model with 74.9%
balanced accuracy on coding variants needs a benchmark, not an anecdote; the
vendor ran one through `llama-server` and found no measurable loss.

## TOU validation and deployment status (2026-08-16)

> Carbon-X Q8_0 ran on the NVIDIA GB10 (aarch64, cc 12.1, 128 GB unified),
> driver 580.173.02, on 2026-10-25, through this provider's own path. `tu
> remote setup` completed all four steps: weights 1/1 at their pin after an
> independent 5 min 12 s fetch of the 15.8 GB GGUF and the pinned llama.cpp
> b11742 engine, and the smoke OK in 14 s at 15.46 GiB. The engine was
> identified rather than assumed — `cuobjdump` reports an `sm_121a` cubin, and
> the tokenizer splits the model card's own example into exactly the nine
> tokens the card prints. Socket acceptance was 9/9, including a 7,033-token
> prompt in 13.2 s and four refusals by name, with the device footprint flat
> at 15.46–15.47 GiB throughout; the live MCP endpoint on 8064 returned the
> declared keys for three calls and named refusals for six malformed ones,
> four from the tool and two from the published schema. The standard's own
> acceptance harness — `verify_provider.py carbonx --lengths
> 600,6000,24000,42000 --repeats 4` — exits 0 on 2026-10-26, answering 12 of
> 12 requests across an ascending ladder, mixed shapes and four identical
> repeats, with the footprint reading 15.46 GiB at one rung and 15.47 at the
> other eleven. `tu remote check carbonx` and `tu remote run carbonx` both
> exit 0; `check` prints `GPU: held by llama.cpp b11742 (CUDA 13.4), in a
> child process` rather than a CUDA tensor check. The orphan watchdog
> released the card 122 s after the server stopped **and its llama-server
> child died with it**. **Accuracy is measured rather than anecdotal as of
> 2026-10-27, and it is uneven.** On 50 real ClinVar missense SNVs — 25
> pathogenic, 25 benign, every window pulled from UCSC hg38 and checked so
> its centre base is the reference allele ClinVar names — the shipped MCP
> tool scores 40/50 — 80%, 95% CI [67%, 89%] — at an 8,001-base window,
> beside the card's own 74.9% on BioReason Coding and 70.4% on FrontierVEP.
> **Window length, not prompt layout, is what moves it**: 52% [39%, 65%] at
> 55 bases, 76% [63%, 86%] at 1,001 and 80% [67%, 89%] at 8,001, while the
> card's own `Reference:/Variant:` wording and this provider's
> named-sequence layout differ by 2 points. Read those intervals before the
> point estimates: **55 bases is distinguishably worse and 1,001 versus
> 8,001 is not distinguishable at n=50** — the apparent 4-point gain is
> within noise. What is not within noise is the churn underneath it: the
> verdict changes on 8 of 50 variants between those two windows, and
> the canonical sickle-cell variant (ClinVar 15333, pathogenic, multiple
> submitters, no conflicts) is called pathogenic 5/5 at 1,001 bases and
> benign 5/5 at 8,001. Sampling is not the source: 20 of 20 variants are
> unanimous across 5 seeds. Two further capabilities are weaker than that
> headline. Translation is accurate but not exact — 98–99 residues right per
> 100 by alignment, and 0 of 5 transcripts exactly right at 100 amino acids,
> because it drops or repeats one residue and then continues correctly.
> Organism group, asked as GenomeQA poses it (multiple choice), is 4/8 at
> 2,001 bases against the card's 93.2%; **that gap is unmeasured at a useful
> n** and 8 items cannot settle it. Nothing here distinguishes the
> quantization from the model. Reproduce with
> `scripts/remote_validation/carbonx_capability_eval.py`. The likelihood `compare` operation upstream
> documents is **not** exposed: it needs vLLM's `prompt_logprobs`, which
> llama-server b11742 does not implement. Only `-c 8192` has been served; the
> x86_64 engine digests are pinned from the published tarball but that binary
> has never been run here, so this provider is measured on aarch64 only.
> Public publication, cross-user isolation, concurrency and recovery are
> untested; keep this deployment private.

- Operation: `carbonx_ask_dna`
- Start: `python -m tooluniverse.remote.carbonx.carbonx_tool`
- Endpoint: `http://127.0.0.1:8064/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment and the weights are declared with a size
  and a sha256 and verified before the worker starts. It wraps no optimization
  kit, so `tu remote setup` has four steps rather than five. Keep provider
  data, weights, caches and credentials outside Git. Use one worker: the
  resident worker serves one request at a time by design, and a second
  in-flight request queues on its lock rather than doubling peak VRAM. The
  declared VRAM budget is 18.5 GiB against a measured 17.23 GiB high-water
  mark at `-c 8192`, and it is an admission input rather than documentation:
  the pool reserves what the manifest declares on every request, large or
  small. The margin is smaller than a torch provider's on purpose — every
  allocation here is made at load from `-c` and `-np`, so there is no
  allocator high-water mark to cover, only measurement noise. Raising `-c` is
  a scheduling decision as much as a capability one.
- TOU check: `tu doctor --forward http://127.0.0.1:8064/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8064/mcp --name validation-carbonx --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation carbonx`. Add `--check-provider-env` before launch, `--live`
after launch, and `--check-connect-prereqs` before sharing. Live preflight
checks exact MCP discovery only; it does not run or validate a model.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays
online and all 41 operations discoverable. It imported each implementation as
unpublished owner draft(s), configured a 120-second timeout, and invoked it
through `/expert-sessions/{id}/test`. **This implementation was added after
that matrix and was not part of it**, so none of that evidence covers it: it
has not been exercised through the Platform at all, and everything above was
measured locally, on one card. Public publication, independent-caller
authorization/isolation, broad saturation and persistent supervision are
unvalidated here.

## Authorize once, then share with one short command

Log in once per machine, and again after key rotation:

```bash
tu remote login
```

`tu remote login` requests a short-lived device code, opens the TU Platform
approval page and polls until the signed-in user approves; no key is copied or
pasted, and the CLI never displays the computer-only key it stores in a local
0600 file. On a headless machine add `--no-browser`. Then each private share is
one command:

```bash
tu remote share carbonx
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share carbonx --name my-carbonx-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-carbonx-remote-tool/SKILL.md).
The skill is the whole guide for this provider — how to build the environment,
what `tu remote setup`'s four steps each prove, every refusal name with its
fix, and the measured numbers a host schedules on. This file carries the
deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.
