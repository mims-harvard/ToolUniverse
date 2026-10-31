"""The MCP surface for Carbon-X's resident worker.

Runs in ToolUniverse's environment and imports nothing of the model's: the
request crosses a Unix socket as JSON, per STANDARD section 2.

ONE TOOL, AND IT RETURNS PROSE -- WHICH IS UNUSUAL HERE AND DELIBERATE.
Every other remote provider in this repository answers with structured output:
coordinates, embeddings, arrays of scores. Carbon-X answers in English,
because that is what it is: a 14.8B decoder trained jointly on DNA and text,
whose published benchmark numbers are all scored on what it *says*. Wrapping
it in a tool that returned a number would mean inventing a parser upstream
does not have and reporting a confidence this model does not emit.

WHAT KEEPS IT FROM BEING A CHATBOT. ``sequences`` is required and must be
non-empty. A question with no DNA in it is refused here rather than forwarded,
so the tool is a DNA-grounded question-answerer and not a general assistant
that happens to live behind a GPU. Upstream's own agent recipe passes
sequences by name for the same reason this schema does: language models
miscopy long sequences, so the caller names them and the code substitutes the
bases.

THE SECOND OPERATION UPSTREAM DOCUMENTS IS NOT HERE, AND THE REASON IS
MEASURED. Their ``carbon-dna`` skill has a ``compare`` command that ranks
equal-length variants by sequence log-likelihood. It is built on
``prompt_logprobs`` and ``prompt_token_ids``, which are **vLLM extensions**:
llama-server b11742 has neither, and an OpenAI-style ``echo: true`` with
``logprobs: 0`` comes back with ``"logprobs": null`` -- checked against the
running engine, not inferred from documentation. So this provider cannot score
likelihoods, and says so instead of shipping an operation that would quietly
return nothing.
"""

import json
import os
import re
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

MAX_SEQUENCES = 16
MAX_NAME_LEN = 64
MAX_OUTPUT_TOKENS = 4096
MAX_INPUT_BYTES = 2 * 1024 * 1024

# THE TOKEN CEILING IS NOT CHECKED HERE, AND THAT IS DELIBERATE -- the same
# split the BioEmu-2 provider documents, for the same reason. Carbon-X's
# tokenizer is hybrid: BPE for English, non-overlapping 6-mers for canonical
# DNA, dedicated tail tokens for a length that is not a multiple of six, and a
# single `<oov>` for any 6-mer holding an ambiguity code. The arithmetic that
# looks like a substitute -- bases divided by six -- ignores the English half
# of the prompt and the chat template's own tokens, and is therefore a FLOOR.
# A ceiling enforced against a floor admits prompts larger than the context
# the VRAM budget was measured at. The worker renders the template through the
# engine's `/apply-template` and tokenizes the result, so the number it
# refuses on is the number that would have been evaluated, and the refusal
# comes back by name one round trip later.
MAX_PROMPT_TOKENS_ENFORCED_BY_WORKER = 7168

# IUPAC nucleotide codes. Only A/C/G/T form 6-mers; the rest are accepted and
# cost resolution, which the description says out loud.
_DNA = re.compile(r"^[ACGTURYSWKMBDHVN]+$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:+-]*$")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


@register_mcp_tool(
    tool_type_name="carbonx_ask_dna",
    config={
        "description": (
            "Ask Carbon-X a question about DNA sequences you supply. It is a "
            "14.8B language model trained jointly on DNA and English: give it "
            "named sequences and a question and it answers in prose, with its "
            "reasoning. MEASURED HERE on 50 balanced ClinVar missense SNVs: "
            "80% at an 8,001-base window and 76% at 1,001, against 52% at 55, "
            "so GIVE IT THOUSANDS OF BASES AROUND THE SITE, not tens -- at 55 "
            "bases it calls almost everything pathogenic. The two long "
            "windows are not distinguishable at this sample size; the short "
            "one is clearly worse. The window is still an instability: the "
            "verdict changes on 8 of 50 variants between 1,001 and 8,001 "
            "bases with no accuracy gain to show for it, so treat a single "
            "call as one opinion rather than a classification. Variant "
            "effect is its measured "
            "strength. It reads DNA accurately but not exactly -- 98-99 "
            "residues per 100 correct when translating, and almost never a "
            "whole 100-residue protein right -- so do not use it to "
            "transcribe. Organism group measured 4 of 8 here against the "
            "93.2% upstream reports, and splice sites and histone marks are "
            "weak upstream too; it miscounts bases and coordinates, and it "
            "was not trained to design sequences. The answer is a model "
            "prediction, NOT clinically validated, and must not drive a "
            "medical decision. "
            "Sequences are DNA only; 'sequences' is required, because this "
            "tool answers questions about DNA rather than acting as a general "
            "assistant. The prompt is limited to about 7,168 tokens (roughly "
            "43 kbp of DNA); a longer one is refused by name with its real "
            "token count."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "What to ask about the sequences. Put everything in "
                        "one question: Carbon-X was trained and evaluated with "
                        "the sequence and the question in a single message. "
                        "For a variant, give the position and the reference "
                        "and alternate base, computed in code rather than left "
                        "to the model to locate."
                    ),
                },
                "sequences": {
                    "type": "object",
                    "description": (
                        "The DNA to ask about, as name -> sequence. Names are "
                        "how the question refers to them ('reference', "
                        "'variant', 'promoter'). IUPAC ambiguity codes are "
                        "accepted but cost resolution: only A, C, G and T form "
                        "6-mer tokens, and any 6-mer containing another "
                        "character collapses into one <oov> token. SIZE THEM "
                        "FOR THE QUESTION: for a variant, pass the reference "
                        "and alternate as windows of a thousand bases or more "
                        "centred on the site. A 55-base window scored 52% "
                        "here where 8,001 bases scored 80%, and short windows "
                        "fail asymmetrically -- specificity collapsed to 7 of "
                        "25 while sensitivity held. At most "
                        f"{MAX_SEQUENCES} sequences."
                    ),
                    "additionalProperties": {"type": "string"},
                },
                "context": {
                    "type": "string",
                    "description": (
                        "What is already known: gene, strand, assembly, "
                        "coordinates, annotations. Placed before the question. "
                        "Upstream's strongest prompting advice -- without it "
                        "the model may invent a sequence's identity or "
                        "function."
                    ),
                },
                "max_tokens": {
                    "type": "integer",
                    "description": (
                        f"Ceiling on the answer, 1 to {MAX_OUTPUT_TOKENS}. "
                        f"Generation measured about 12-14 tokens per second on "
                        f"the verified card, so this is the main thing that "
                        f"sets how long a call takes. The reply says whether "
                        f"the answer was truncated."
                    ),
                    "default": 1024,
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed. Carbon-X's published results use "
                        "sampling (temperature 0.6, top-p 0.95, top-k 20), so "
                        "answers vary; pass a seed to repeat one."
                    ),
                },
            },
            "required": ["question", "sequences"],
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "answer": {"type": "string"},
                "truncated": {"type": "boolean"},
                "sequences": {"type": "object"},
                "prompt_tokens": {"type": "integer"},
                "completion_tokens": {"type": "integer"},
                "seed": {"type": "integer"},
                "max_tokens": {"type": "integer"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "peak_reserved_gib": {"type": "number"},
                "engine_device_gib": {"type": "number"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "Carbon-X MCP Server",
        "host": "127.0.0.1",
        "port": 8064,
        "transport": "http",
    },
)
class CarbonXAskDnaTool:
    """Ask about DNA. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        try:
            document = self._document(arguments)
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            reply = _worker().request({"op": "predict", "input": json.dumps(document)})
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": f"Carbon-X did not answer ({reason}): {exc}",
                "reason": reason,
            }

        # The supervisor hands back the whole envelope, `{"ok": ..., "result":
        # ...}`. Returning that would nest the answer one level below where
        # `return_schema` says it is, and a caller reading `answer` would get
        # an empty string with no error to explain it -- which is exactly how
        # this was found, through the live endpoint rather than in review.
        # Projecting onto the declared keys also means the published schema
        # and the reply cannot drift apart silently.
        result = reply.get("result") or {}
        return {
            key: result[key]
            for key in (
                "model",
                "answer",
                "truncated",
                "sequences",
                "prompt_tokens",
                "completion_tokens",
                "seed",
                "max_tokens",
                "timing",
                "weights_held_by",
                "peak_reserved_gib",
                "engine_device_gib",
            )
            if result.get(key) is not None
        }

    def _document(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """The request document, validated as far as this side can.

        Everything here is checkable without the engine: types, names, the
        nucleotide alphabet, the sizes. The prompt's token count is not, and
        the module docstring says where that one lives.
        """
        question = arguments.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("'question' must be a non-empty string.")

        sequences = arguments.get("sequences")
        if not isinstance(sequences, dict) or not sequences:
            raise ValueError(
                "'sequences' must be a non-empty object of name -> DNA. This "
                "tool answers questions about DNA you supply; it is not a "
                "general chat endpoint."
            )
        if len(sequences) > MAX_SEQUENCES:
            raise ValueError(
                f"'sequences' has {len(sequences)} entries; the ceiling is "
                f"{MAX_SEQUENCES}."
            )

        cleaned: Dict[str, str] = {}
        total = 0
        for name, dna in sequences.items():
            if (
                not isinstance(name, str)
                or not _NAME.match(name)
                or len(name) > MAX_NAME_LEN
            ):
                raise ValueError(
                    f"sequence name {name!r} must be 1-{MAX_NAME_LEN} characters "
                    f"of letters, digits, spaces and ._:+- , starting "
                    f"alphanumeric."
                )
            if not isinstance(dna, str):
                raise ValueError(f"sequence {name!r} must be a string of DNA.")
            bases = "".join(dna.split()).upper()
            if not bases:
                raise ValueError(f"sequence {name!r} is empty.")
            if not _DNA.match(bases):
                bad = sorted(set(bases) - set("ACGTURYSWKMBDHVN"))
                raise ValueError(
                    f"sequence {name!r} contains {', '.join(bad)}, which are "
                    f"not IUPAC nucleotide codes. Carbon-X reads DNA; it does "
                    f"not read protein."
                )
            cleaned[name] = bases
            total += len(bases)
        if total > MAX_INPUT_BYTES:
            raise ValueError(
                f"the sequences total {total} bases; the hard ceiling is "
                f"{MAX_INPUT_BYTES}, and the real limit is the "
                f"{MAX_PROMPT_TOKENS_ENFORCED_BY_WORKER}-token prompt the "
                f"worker enforces (roughly 43 kbp of DNA)."
            )

        document: Dict[str, Any] = {"question": question, "sequences": cleaned}

        context = arguments.get("context")
        if context is not None:
            if not isinstance(context, str):
                raise ValueError("'context' must be a string.")
            document["context"] = context

        max_tokens = arguments.get("max_tokens", 1024)
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool):
            raise ValueError("'max_tokens' must be an integer.")
        if not 1 <= max_tokens <= MAX_OUTPUT_TOKENS:
            raise ValueError(
                f"'max_tokens' is {max_tokens}; it must be between 1 and "
                f"{MAX_OUTPUT_TOKENS}."
            )
        document["max_tokens"] = max_tokens

        seed = arguments.get("seed")
        if seed is not None:
            if not isinstance(seed, int) or isinstance(seed, bool):
                raise ValueError("'seed' must be an integer.")
            document["seed"] = seed

        return document


if __name__ == "__main__":
    start_mcp_server()
