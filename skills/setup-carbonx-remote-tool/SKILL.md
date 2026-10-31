---
name: setup-carbonx-remote-tool
description: Set up, launch, validate, and troubleshoot the Carbon-X ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up Carbon-X as a remote tool

> Validation status (2026-10-25): Carbon-X Q8_0 ran on the NVIDIA GB10 (aarch64, cc 12.1, 128 GB unified), driver 580.173.02, through this provider's own path. `tu remote setup` completed all four steps: weights 1/1 at their pin after an independent 5 min 12 s fetch of the 15.8 GB GGUF and the pinned llama.cpp b11742 engine, and the smoke OK in 14 s at 15.46 GiB. The engine was identified rather than assumed: `cuobjdump` reports an `sm_121a` cubin, and the tokenizer splits the model card's own example into exactly the nine tokens the card prints. Socket acceptance was 9/9 — a cold request in 3.9 s, an identical repeat in 4.2 s, a 7,033-token prompt in 13.2 s, four refusals by name including the over-ceiling one naming 7,697 tokens against 7,168, and a tenth request after them that still worked — with the engine's device footprint flat at 15.46–15.47 GiB throughout. The live MCP endpoint on 8064 returned the declared keys for three calls and named refusals for six malformed ones, four from the tool and two from the published schema; that run is also what caught `run()` returning the supervisor's whole envelope, which review had not. The orphan watchdog released the card 122 s after the server stopped and its llama-server child died with it, and PR_SET_PDEATHSIG was tested in isolation on all three paths. **Accuracy is not validated here and two measured answers were wrong**: on the model card's own sickle-cell variant the model answered benign on 4 of 5 seeds with the named-sequence layout and pathogenic on 3 of 3 with the card's own wording, and it placed the human HBB fragment in a coronavirus — both on 55-base inputs, far shorter than the benchmarks the card reports. Nothing here distinguishes the quantization from the model. The likelihood `compare` operation upstream documents is not exposed, because it needs vLLM's `prompt_logprobs` and llama-server b11742 returns null. Only `-c 8192` has been served, and the x86_64 engine digests are pinned from the published tarball but that binary has never been run here, so this provider is measured on aarch64 only. Concurrency and recovery were measured on 2026-10-31: three independent MCP clients were answered with their own work and nothing crossed (100% identity to own input, 15% and 5% to the others), on a 1.3 s staircase that shows the queue; but an engine death was invisible and permanent -- SIGKILL the llama-server child and the worker stayed up answering `ping` with `ready: True` and failing every request in 0.0 s forever, because nothing respawns the engine and the supervisor polls the worker's pid. That is now converted into the death the supervisor can see: one named refusal in 1.0 s, the worker exits, the next request rebuilds in 8.7-49.2 s and answers correctly. Public publication and cross-user isolation remain untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests; CPU is not a target.
- Linux **aarch64 or x86_64**. The engine is a pinned llama.cpp release binary and the provider ships digests for those two architectures only; any other exits 3 at the weights step rather than guessing which build to trust.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation carbonx
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create the two environments

This provider is on the remote-tool standard, so it has two environments, not
one: the MCP server runs in ToolUniverse's, and the model runs in its own.

~~~bash
python3 -m venv .venvs/carbonx
. .venvs/carbonx/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

**The model half is the standard library and nothing else, which is unusual
and deliberate.** `environment/requirements.lock` pins no packages because
there is nothing to pin: Carbon-X is a GGUF file read by a pinned llama.cpp
binary in a child process, and the worker's own job — spawn that child, speak
HTTP over two Unix sockets, count tokens through the engine's `/tokenize`,
validate a request — is all standard library. So creating the model
environment is one command and `tu remote setup --only environment` only
checks it:

~~~bash
uv venv --seed --managed-python --python 3.12.13 ~/carbonx-venv
export TOOLUNIVERSE_CARBONX_PYTHON=~/carbonx-venv/bin/python
export CARBONX_HOME=~/.cache/tooluniverse/carbonx   # optional; this is the default
tu remote setup carbonx
~~~

**`[gpu] driven_by` is why the environment step passes without torch.** The
toolchain probe normally asks a provider's own torch whether it can drive the
card, which is the right question everywhere else and an impossible one here:
there is no torch in that environment and the CUDA context belongs to the
engine's child process. The manifest states what holds the card, and setup
reads it. Without that key a correct install is refused with
`torch_arch_unsupported` — the same false refusal af3_jax hit when jax held
the card.

`tu remote check carbonx` reads the same key, and a correct machine prints

~~~
  ✓ model environment: ~/carbonx-venv/bin/python
    GPU: held by llama.cpp b11742 (CUDA 13.4), in a child process, not by this interpreter
~~~

rather than a CUDA tensor check. If it instead prints
`GPU error: No module named 'torch'` and `CUDA tensor check: failed`, the
install is fine and the checkout predates that fix.

**This provider wraps no optimization kit**, so its setup has four steps
rather than five. Upstream publishes the inference runtime itself, as a
llama.cpp release.

Run one step at a time with `--only preflight|environment|weights|smoke`
while bringing a machine up. The weights step downloads 15.8 GB and about 150
MB of engine and took **5 min 12 s** here; the smoke step holds the model,
sends one request, asserts the reply carries the keys the manifest says a
successful run fills, and records the measurement to
`~/.cache/tooluniverse/measured/carbonx.json`.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- No credential is needed. The GGUF is public on the Hugging Face Hub under Apache-2.0, and the engine is a public GitHub release asset.
- `CARBONX_HOME` names the directory holding both; it defaults to `~/.cache/tooluniverse/carbonx` and does not have to be set. It ends up with `carbon-x-q8_0.gguf` and `llama.cpp-b11742/`.
- **The 15.8 GB GGUF's digest is upstream's own**: `48241178b67ab5423a74f65552dd04628ac16f2fa5d1a60dc94019d86fa6f453` is the `lfs.oid` the Hub API publishes, confirmed equal to the sha256 of the bytes measured here.
- **The engine is pinned too, and that pin is checked at every launch.** `environment/llamacpp-b11742.pins` lists every llama.cpp file the server loads, by size and sha256, for `aarch64` and `x86_64`. These files are *executed*; a drifted `libggml-cuda.so` runs whatever it now contains. The fetch picks the tarball from `uname -m`, checks it against its GitHub release digest, and `launch.py` re-checks the extracted files before the worker starts.
- **b11742 is a floor, not a preference.** It is the first llama.cpp release that knows Carbon-X's `HybridDNATokenizer` (PR #30825, merged 2026-10-19). An older build loads the same GGUF and tokenizes DNA **wrongly without saying so**, which is the failure mode a version check exists to prevent.
- Nothing is fetched at request time. The launch refuses if the weights or any engine file is off its pin.

## Authorize once, then share with one short command

After installing dependencies, exporting the provider resources above, and
installing the pinned relay SDK described under Connect below, run from the
repository root. Log in only once per machine (and again after key
rotation):

~~~bash
tu remote login
# Or import an existing protected 0600 file without sourcing it:
tu remote login --env-file /path/to/tooluniverse-service.env
~~~

Then each private share is one short command:

~~~bash
tu remote share carbonx
~~~

By default, `tu remote login` requests a short-lived device code, opens the
TU Platform approval page, and polls until the signed-in user approves. No key
copy/paste is required. On a headless machine, add `--no-browser` and open the
printed link elsewhere. The CLI exchanges the approval for a computer-only key,
verifies `/remote-servers/preflight`, stores it in a local 0600 config file, and
never displays it.

The share command runs environment and TU Platform preflights, starts or reuses
the exact loopback endpoint, validates discovery, and keeps the relay in the
foreground until Ctrl-C. It automatically uses the reviewed Python, name,
and worker count. Override them only when needed:

~~~bash
tu remote share carbonx --name my-carbonx-remote --workers 1
~~~

Use `tu remote check carbonx` for a non-sharing readiness check and
`tu remote run carbonx` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.carbonx.carbonx_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8064/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8064/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains carbonx_ask_dna; stop on empty, duplicate, or
schema-drifted discovery.

The first request after a restart pays the engine load, which measured 11–15 s
with a warm page cache. After that the weights, the KV cache and the compute
buffers are all resident and a request pays only for its own tokens.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8064/mcp --json
tu serve --share --forward http://127.0.0.1:8064/mcp --name validation-carbonx --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply
`TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use
`tu remote login --manual-key`; never put a key in shell arguments.

This implementation was added after the authenticated 2026-08-16 Platform
matrix and was not part of it. That matrix imported each implementation it
covered as unpublished owner drafts and invoked them through
`/expert-sessions/{id}/test`; this provider was imported as no such draft and
invoked through no such route. It has not been exercised through the Platform
at all: the evidence above is local, on one card, through the loopback
endpoint. Public publication, independent-caller authorization/isolation,
saturation, and persistent supervision are untested -- eight simultaneous
loopback callers were measured, all answered and all attributed to their own
input on an even staircase 1.3-1.5 s apart -- though NOT in submission order,
so no caller starves but none is promised a position either. That says nothing
about authorization.

## Run a verified example

Operation: carbonx_ask_dna

~~~json
{"question": "Is this sequence more likely coding or non-coding? Answer in one or two sentences.", "sequences": {"hbb_start": "ATGGTGCATCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGG"}, "context": "Human HBB (beta-globin), the first 55 bases of the coding sequence on the plus strand.", "max_tokens": 160, "seed": 0}
~~~

That is the sequence from Carbon-X's own model card: the first 55 bases of
human *HBB*. Read in frame from the ATG it translates to `MVHLTPEEKSAVTALWGK`,
beta-globin's N-terminus — so the input can be checked rather than taken on
trust. It is also what the provider ships as its smoke input at
`src/tooluniverse/remote/carbonx/smoke/hbb_coding.json`, so this is a request
that works rather than only a shape.

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

HBB = "ATGGTGCATCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGG"
# The same sequence with GAG -> GTG at codon 6: Glu6Val, sickle-cell disease.
HBB_E6V = "ATGGTGCATCTGACTCCTGTGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGG"

async def main():
    async with Client("http://127.0.0.1:8064/mcp") as client:
        result = await client.call_tool(
            "carbonx_ask_dna",
            {
                "question": "Is this variant likely benign or pathogenic, and what disease if any does it cause? Answer briefly.",
                "sequences": {"reference": HBB, "variant": HBB_E6V},
                "context": "Human HBB coding sequence, plus strand; the variant differs from the reference at position 20, A>T.",
                "max_tokens": 320,
                "seed": 0,
            },
        )
        print(result.content[0].text)

asyncio.run(main())
PY
~~~

Expected success shape: `answer` (prose), `truncated`, `sequences` as name ->
length, `prompt_tokens`, `completion_tokens`, `seed`, `max_tokens`, a `timing`
object with `total_s`, `prompt_eval_per_s` and `generate_per_s`, and
`weights_held_by`. Check scientific meaning, output bounds, invalid-input
behavior, and absence of paths, secrets, and traces.

**The answer is prose, and that is what this model emits.** Every published
Carbon-X number is scored on what it says. There is no confidence score to
read, and a tool that returned one would be inventing it.

**The 55-base variant snippet above is a SHAPE, not a usage pattern.** It is
short so the example can be read and checked by hand. Sized that way for a
real question it is in the regime measured below as unreliable.

## What it is measured to do, and the one rule that decides it

Measured 2026-10-27 on the GB10, through this MCP tool, against ground truth
nobody here chose: 50 real ClinVar missense SNVs, 25 pathogenic and 25
benign, each reference window pulled from UCSC hg38 and checked so its centre
base is the reference allele ClinVar names. Reproduce with
`python scripts/remote_validation/carbonx_capability_eval.py`.

| window around the site | accuracy | 95% CI | sensitivity | specificity |
|---|---|---|---|---|
| 55 bases | 52% | [39%, 65%] | 19/25 | 7/25 |
| 1,001 bases | 76% | [63%, 86%] | 19/25 | 19/25 |
| 8,001 bases | 80% | [67%, 89%] | 19/25 | 21/25 |

**Read the intervals before the point estimates.** Fifty items is a small
sample. 55 bases is distinguishably worse than either longer window; 1,001
versus 8,001 is **not** distinguishable at this n, so the apparent 4-point
gain is noise and "longer is better" is not what this measured. An
independent 22-variant draw at 1,001 bases, run by the same script with
`--per-gene 1`, scored 68% [47%, 84%] — consistent, and a useful reminder of
how wide these intervals are.

- **GIVE IT THOUSANDS OF BASES AROUND THE SITE, NOT TENS.** This is the
  single most consequential thing a caller controls, and nothing in the API
  enforces it. Short windows fail *asymmetrically*: sensitivity holds at
  19/25 while specificity collapses to 7/25, so a 55-base window does not
  degrade gracefully — it turns the model into something that calls almost
  everything pathogenic, which is the failure mode that looks like caution
  and is not.
- **Prompt layout is not the lever it looks like.** The model card's own
  `Reference:/Variant:` wording and this provider's named-sequence layout
  differ by 2 points at an adequate window (78% vs 80%). This was tested
  because an early anecdote suggested the opposite; it did not survive.
- **Treat one call as one opinion.** The verdict changes on 8 of 50 variants
  between 1,001 and 8,001 bases. That churn is the finding, not the 4-point
  difference it nets out to: the same variant gets a different answer
  because the caller chose a different window, with no accuracy gain to show
  for it. The canonical sickle-cell variant (ClinVar 15333) is
  called pathogenic 5/5 at 1,001 bases and benign 5/5 at 8,001 — the longest
  window gets the most famous pathogenic variant in medicine wrong.
- **It is not the sampler.** 20 of 20 variants are unanimous across 5 seeds.
  When it is wrong it is confidently and reproducibly wrong, so repeating a
  call buys nothing; changing the window changes the answer.
- **It reads DNA accurately but not exactly.** Translating a CDS it gets
  98–99 residues per 100 right by alignment, and 0 of 5 transcripts exactly
  right at 100 amino acids: it drops or repeats one residue and then
  continues correctly. Use it to read, never to transcribe.
- **Do not use it for organism group.** Asked as GenomeQA poses it — multiple
  choice, which is the shape the card's 93.2% is scored in — it was 4/8 at
  2,001 bases and 1/8 at 300. Eight items cannot settle the gap to 93.2%, but
  they are enough not to build on it.
- Every number here is one card, one quantization and one day. Nothing in it
  distinguishes Q8_0 from the model, and none of it is clinical validation.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM. `llama-server` is started with `-np 1` for the same reason: its default of four slots would split `-c` four ways and make every co-tenant pay for KV cache no request can use.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. The declared 18.5 GiB sits above a measured 17.23 GiB high-water mark at `-c 8192`, and the pool reserves what is declared on **every** request, large or small.
- **The footprint is static, which no other provider here can say.** llama.cpp allocates weights, KV cache and compute buffers at load, so `-c` fixes the budget and requests do not move it: four requests spanning 72 bp to 8,208 bp held it within 0.16 GiB, and that drift is a shared unified pool breathing rather than growth. The margin here is 7% where a torch provider's is 25–30%, because there is no allocator high-water mark to cover.
- **`-c` is the budget knob and it is a scheduling decision.** 8192 → 17.11 GiB at load, 16384 → 18.12, 40960 → 21.95. The full 40,960 context is a 28% permanent surcharge on every co-tenant, to serve input lengths upstream has not evaluated: mid-training used 8,192-token sequences, post-training stayed below 16k, and the longest input in the vendor's hardest benchmark (FrontierVEP) is 8,192 *bases*, which is 1,406 tokens.
- **Tokens are not bases, and the arithmetic that looks like a substitute is a floor.** One token covers six canonical bases, but an ambiguity code collapses a whole 6-mer into one `<oov>`, the English half of the prompt is BPE, and the chat template adds tokens of its own. The worker renders the template through the engine's `/apply-template` and tokenizes the result, so the 7,168-token ceiling is enforced on the number that would actually have been evaluated, and a refusal names it.
- **`max_tokens` is the latency knob.** Generation measured 11.9–14.4 tokens per second; prompt evaluation 300–770. A 1,024-token answer takes about 80 s. That is memory bandwidth on this card.
- Measure cold start, then at least four consecutive identical requests, then a mixed-shape sequence (small, small, large, small). A repeat and a shape change are different tests and a resident provider has to survive both.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/carbonx-resident.log`, and **the engine writes its own beside it** at `~/.cache/tooluniverse/remote-logs/carbonx-engine.log`. The engine log is deliberately not inside the worker's temporary directory, which is removed on exit — it is worth least at exactly the moment a crash would delete it.
- **`peak_reserved_gib` is absent from this provider's replies and that is not a bug.** It comes from `torch.cuda.max_memory_reserved()` everywhere else; there is no torch here and the CUDA context is the child's. The budget is a static figure measured externally and recorded in the manifest, not something a request reports.
- **An engine that never becomes healthy is a start-up refusal, not a failed request.** The worker tails the engine log into its own refusal message. The usual causes are a GGUF off its pin, a missing CUDA runtime, and a driver below 580.
- **`AF_UNIX path too long`**: the engine's socket lives in a short private temporary directory precisely to avoid this — `sun_path` is 108 bytes. If you are driving `llama-server` by hand, do not put its socket under a deep scratch path; the measurements for this provider first failed at exactly 108 characters.
- **Older llama.cpp silently mis-tokenizes DNA.** If answers are fluent but wrong about sequences, check the build: `llama-server --version` must report `build 11742` or newer. `launch.py` refuses anything whose files are off the pinned digests, so this should only happen to a hand-run server.
- Weights or engine off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-carbonx`.
- A worker outliving its server is a known shape. Here it has a second half: the engine is a *child* of the worker, and `os._exit(0)` in the orphan watchdog runs no cleanup at all. The child is started with `PR_SET_PDEATHSIG(SIGKILL)` so the kernel reaps it whatever happens to the worker — measured: with the flag the child dies on both `os._exit(0)` and `SIGKILL` to the parent; without it, it survives. Judge liveness by PID, never by `ls` on the socket directory.
- Revoke temporary keys. After confirmation, remove only .venvs/carbonx and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
