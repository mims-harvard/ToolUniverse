"""
ESM3 / ESMC Tool

Provides access to EvolutionaryScale protein language models:
  - ESMC (300m/600m): fast protein sequence embeddings
  - ESM3 (open/small): sequence generation, structure prediction, sequence scoring

Requires an API token from https://forge.evolutionaryscale.ai
Set via environment variable ESM_API_KEY.

Install: pip install esm
"""

import os
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


def _get_client(model: str):
    """Return an ESM3ForgeInferenceClient for the given model, using ESM_API_KEY."""
    try:
        from esm.sdk.forge import ESM3ForgeInferenceClient
    except ImportError:
        raise ImportError(
            "esm package is required. Install with: pip install esm"
        )
    token = os.environ.get("ESM_API_KEY", "")
    if not token:
        raise EnvironmentError(
            "ESM_API_KEY environment variable is not set. "
            "Obtain a token at https://forge.evolutionaryscale.ai"
        )
    return ESM3ForgeInferenceClient(model=model, token=token)


@register_tool("ESMTool")
class ESMTool(BaseTool):
    """
    ESM3 / ESMC tool for protein sequence embeddings, generation,
    structure prediction, and sequence scoring via the EvolutionaryScale Forge API.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        try:
            operation = arguments.get("operation", "")

            if operation == "get_protein_embedding":
                return self._get_protein_embedding(arguments)
            elif operation == "generate_protein_sequence":
                return self._generate_protein_sequence(arguments)
            elif operation == "fold_protein":
                return self._fold_protein(arguments)
            elif operation == "score_sequence":
                return self._score_sequence(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {operation!r}. Valid operations: "
                    "get_protein_embedding, generate_protein_sequence, "
                    "fold_protein, score_sequence",
                }
        except ImportError as e:
            return {"status": "error", "error": str(e)}
        except EnvironmentError as e:
            return {"status": "error", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # get_protein_embedding
    # ------------------------------------------------------------------ #
    def _get_protein_embedding(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ESMC per-residue and mean-pooled embeddings for a protein sequence."""
        try:
            from esm.sdk.api import ESMProtein, LogitsConfig

            sequence = arguments.get("sequence")
            if not sequence:
                return {
                    "status": "error",
                    "error": "sequence is required for get_protein_embedding",
                }
            model = arguments.get("model", "esmc-300m-2024-12")
            return_per_residue = arguments.get("return_per_residue", False)

            client = _get_client(model)
            protein = ESMProtein(sequence=sequence)
            logits_output = client.logits(
                protein, LogitsConfig(sequence=True, return_embeddings=True)
            )

            if logits_output.embeddings is None:
                return {
                    "status": "error",
                    "error": "Model did not return embeddings. Ensure LogitsConfig(return_embeddings=True) is supported.",
                }

            embeddings = logits_output.embeddings  # shape: (L+2, D) including BOS/EOS
            # mean pool over residue positions (exclude BOS/EOS tokens)
            import numpy as np

            emb_np = embeddings.detach().cpu().numpy() if hasattr(embeddings, "detach") else embeddings
            mean_emb = emb_np[1:-1].mean(axis=0).tolist()

            result = {
                "status": "success",
                "model": model,
                "sequence_length": len(sequence),
                "embedding_dim": len(mean_emb),
                "mean_embedding": mean_emb,
            }
            if return_per_residue:
                result["per_residue_embeddings"] = emb_np[1:-1].tolist()
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # generate_protein_sequence
    # ------------------------------------------------------------------ #
    def _generate_protein_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate or complete a protein sequence using ESM3."""
        try:
            from esm.sdk.api import ESMProtein, GenerationConfig

            prompt_sequence = arguments.get("prompt_sequence")
            if not prompt_sequence:
                return {
                    "status": "error",
                    "error": "prompt_sequence is required. Use '_' characters to denote masked positions to generate.",
                }
            model = arguments.get("model", "esm3-open-2024-03")
            num_steps = int(arguments.get("num_steps", 8))
            temperature = float(arguments.get("temperature", 1.0))

            client = _get_client(model)
            protein = ESMProtein(sequence=prompt_sequence)
            config = GenerationConfig(
                track="sequence",
                num_steps=num_steps,
                temperature=temperature,
            )
            result_protein = client.generate(protein, config)

            generated_seq = result_protein.sequence if result_protein.sequence else ""
            return {
                "status": "success",
                "model": model,
                "prompt_sequence": prompt_sequence,
                "generated_sequence": generated_seq,
                "sequence_length": len(generated_seq),
                "num_steps": num_steps,
                "temperature": temperature,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # fold_protein
    # ------------------------------------------------------------------ #
    def _fold_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Predict protein structure with ESM3, returning pTM score and coordinates."""
        try:
            from esm.sdk.api import ESMProtein, GenerationConfig

            sequence = arguments.get("sequence")
            if not sequence:
                return {
                    "status": "error",
                    "error": "sequence is required for fold_protein",
                }
            model = arguments.get("model", "esm3-open-2024-03")
            num_steps = int(arguments.get("num_steps", 8))

            client = _get_client(model)
            protein = ESMProtein(sequence=sequence)
            config = GenerationConfig(track="structure", num_steps=num_steps)
            result_protein = client.generate(protein, config)

            coordinates = None
            if result_protein.coordinates is not None:
                coords = result_protein.coordinates
                if hasattr(coords, "tolist"):
                    coordinates = coords.tolist()
                else:
                    coordinates = coords

            ptm = None
            if hasattr(result_protein, "ptm") and result_protein.ptm is not None:
                ptm = float(result_protein.ptm)

            plddt = None
            if hasattr(result_protein, "plddt") and result_protein.plddt is not None:
                p = result_protein.plddt
                if hasattr(p, "tolist"):
                    plddt = p.tolist()
                else:
                    plddt = p

            return {
                "status": "success",
                "model": model,
                "sequence": sequence,
                "sequence_length": len(sequence),
                "pTM_score": ptm,
                "plddt_per_residue": plddt,
                "coordinates_shape": (
                    [len(coordinates), len(coordinates[0]), len(coordinates[0][0])]
                    if coordinates is not None
                    else None
                ),
                "num_steps": num_steps,
                "note": "Coordinates are (L, 37, 3) backbone atom positions in Angstroms.",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # score_sequence
    # ------------------------------------------------------------------ #
    def _score_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Score a protein sequence using ESMC logits (per-residue log-probabilities)."""
        try:
            from esm.sdk.api import ESMProtein, LogitsConfig
            import math

            sequence = arguments.get("sequence")
            if not sequence:
                return {
                    "status": "error",
                    "error": "sequence is required for score_sequence",
                }
            model = arguments.get("model", "esmc-300m-2024-12")

            client = _get_client(model)
            protein = ESMProtein(sequence=sequence)
            logits_output = client.logits(
                protein, LogitsConfig(sequence=True, return_embeddings=False)
            )

            if logits_output.logits is None or logits_output.logits.sequence is None:
                return {
                    "status": "error",
                    "error": "Model did not return sequence logits.",
                }

            # Compute mean log-prob (pseudo-likelihood) per residue
            import torch
            import torch.nn.functional as F

            seq_logits = logits_output.logits.sequence  # (L+2, vocab)
            log_probs = F.log_softmax(seq_logits, dim=-1)

            # ESM tokenizer: map each residue to its token id
            try:
                from esm.utils.constants.esm3 import SEQUENCE_VOCAB
                aa_to_idx = {aa: i for i, aa in enumerate(SEQUENCE_VOCAB)}
            except Exception:
                aa_to_idx = {}

            per_residue_logprobs = []
            if aa_to_idx:
                for i, aa in enumerate(sequence):
                    token_id = aa_to_idx.get(aa)
                    if token_id is not None:
                        lp = log_probs[i + 1, token_id].item()
                        per_residue_logprobs.append(lp)

            mean_logprob = (
                sum(per_residue_logprobs) / len(per_residue_logprobs)
                if per_residue_logprobs
                else None
            )

            return {
                "status": "success",
                "model": model,
                "sequence": sequence,
                "sequence_length": len(sequence),
                "mean_log_probability": mean_logprob,
                "per_residue_log_probabilities": per_residue_logprobs,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
