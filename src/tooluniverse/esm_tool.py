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
        raise ImportError("esm package is required. Install with: pip install esm")
    token = os.environ.get("ESM_API_KEY", "")
    if not token:
        raise EnvironmentError(
            "ESM_API_KEY environment variable is not set. "
            "Obtain a token at https://forge.evolutionaryscale.ai"
        )
    return ESM3ForgeInferenceClient(model=model, token=token)


def _get_esmc_client(model: str):
    """Return an ESMCForgeInferenceClient (needed for SAE inference).

    ESMC SAE features require the dedicated ESMCForgeInferenceClient (not
    ESM3ForgeInferenceClient) because SAE outputs are exposed through ESMC's
    logits endpoint via LogitsConfig(sae_config=...).
    """
    try:
        from esm.sdk.forge import ESMCForgeInferenceClient
    except ImportError:
        raise ImportError(
            "esm package with SAE support is required. The current PyPI "
            "release (esm 3.2.x) does NOT include SAEConfig — SAE features "
            "live on an unmerged feature branch. Install from there:\n"
            "  pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'"
        )
    token = os.environ.get("ESM_API_KEY", "")
    if not token:
        raise EnvironmentError(
            "ESM_API_KEY environment variable is not set. "
            "Obtain a token at https://forge.evolutionaryscale.ai"
        )
    return ESMCForgeInferenceClient(model=model, token=token)


@register_tool("ESMTool")
class ESMTool(BaseTool):
    """
    ESM3 / ESMC tool for protein sequence embeddings, generation,
    structure prediction, and sequence scoring via the EvolutionaryScale Forge API.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Bind this instance to one operation via fields.operation, matching
        # the AlphaMissense / MaveDB multi-op pattern. Callers no longer need
        # to pass operation= explicitly via tu.tools.X() / tu.run_one_function().
        # Falls back to arguments["operation"] when fields.operation isn't set,
        # for backward compatibility with tests / direct instantiation.
        self.operation = tool_config.get("fields", {}).get("operation", "")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        try:
            operation = self.operation or arguments.get("operation", "")

            if operation == "get_protein_embedding":
                return self._get_protein_embedding(arguments)
            elif operation == "generate_protein_sequence":
                return self._generate_protein_sequence(arguments)
            elif operation == "fold_protein":
                return self._fold_protein(arguments)
            elif operation == "score_sequence":
                return self._score_sequence(arguments)
            elif operation == "get_sae_features":
                return self._get_sae_features(arguments)
            elif operation == "score_variant_sae_disruption":
                return self._score_variant_sae_disruption(arguments)
            elif operation == "describe_sae_feature":
                return self._describe_sae_feature(arguments)
            elif operation == "score_variant_sae_batch":
                return self._score_variant_sae_batch(arguments)
            elif operation == "get_region_sae_features":
                return self._get_region_sae_features(arguments)
            elif operation == "explain_variant_mechanism":
                return self._explain_variant_mechanism(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {operation!r}. Valid operations: "
                    "get_protein_embedding, generate_protein_sequence, "
                    "fold_protein, score_sequence, get_sae_features, "
                    "score_variant_sae_disruption, describe_sae_feature, "
                    "score_variant_sae_batch, get_region_sae_features, "
                    "explain_variant_mechanism",
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

            emb_np = (
                embeddings.detach().cpu().numpy()
                if hasattr(embeddings, "detach")
                else embeddings
            )
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

    # ------------------------------------------------------------------ #
    # get_sae_features
    # ------------------------------------------------------------------ #
    def _get_sae_features(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run a protein sequence through an ESMC Sparse Autoencoder (SAE) and
        return sparse feature activations per residue.

        ESMC SAEs decompose the model's hidden states into a 16,384-feature
        sparse codebook with top-k=64 sparsity per residue. Each feature is an
        interpretable latent dimension (catalytic site, binding region, PTM
        sequon, etc., once labelled separately via ESM_describe_sae_feature).

        License note: SAE outputs are governed by the EvolutionaryScale
        Cambrian Inference Clickthrough License Agreement — non-commercial use
        only unless covered by a separate commercial agreement.
        """
        # Validate input arguments first — fail fast with clear errors before
        # checking environment / imports, so a user calling with bad args sees
        # the input problem (not "install esm").
        sequence = arguments.get("sequence")
        if not sequence:
            return {
                "status": "error",
                "error": "sequence is required for get_sae_features",
            }
        model = arguments.get("model", "esmc-6b-2024-12")
        sae_model = arguments.get(
            "sae_model", "esmc-6b-2024-12_k64_codebook16384_layer60"
        )
        position = arguments.get("position")  # 1-indexed, optional
        window = arguments.get("window", 8)
        top_k_per_residue = arguments.get("top_k_per_residue", 64)

        seq_len = len(sequence)
        # Sequence length cap — ESMC-6B Forge handles up to ~2,700 AA in
        # practice (per EvolutionaryScale docs). Longer sequences
        # fail with opaque server errors; catch up front with a clear message.
        MAX_SEQ_LEN = 2700
        if seq_len > MAX_SEQ_LEN:
            return {
                "status": "error",
                "error": (
                    f"sequence length {seq_len} exceeds practical Forge SAE "
                    f"limit (~{MAX_SEQ_LEN} AA). Either truncate to a region "
                    f"of interest or split the protein and run separately."
                ),
            }
        if position is not None and (position < 1 or position > seq_len):
            return {
                "status": "error",
                "error": (
                    f"position {position} out of range [1, {seq_len}] "
                    f"for sequence of length {seq_len}"
                ),
            }

        # Now check for SDK + API key (env-side problems)
        try:
            from esm.sdk.api import ESMProtein, SAEConfig, LogitsConfig
        except ImportError:
            return {
                "status": "error",
                "error": (
                    "esm package with SAE support is required. The PyPI "
                    "release does NOT include SAEConfig. Install from the "
                    "feature branch: pip install 'esm @ "
                    "git+https://github.com/evolutionaryscale/esm@ee891c52'"
                ),
            }

        try:
            client = _get_esmc_client(model)
        except (ImportError, EnvironmentError) as e:
            return {"status": "error", "error": str(e)}

        try:
            protein = ESMProtein(sequence=sequence)
            protein_tensor = client.encode(protein)
            output = client.logits(
                protein_tensor,
                config=LogitsConfig(
                    sae_config=SAEConfig(model=sae_model, normalize_features=True)
                ),
            )
        except Exception as e:
            return {
                "status": "error",
                "error": f"Forge SAE inference failed: {type(e).__name__}: {e}",
            }

        sae_outputs = output.sae_outputs
        if not sae_outputs or sae_model not in sae_outputs:
            return {
                "status": "error",
                "error": (
                    f"Forge response did not include sae_outputs for "
                    f"{sae_model}. Available: {list(sae_outputs.keys()) if sae_outputs else None}"
                ),
            }

        sae_tensor = sae_outputs[sae_model]
        # sae_tensor is torch.sparse_coo_tensor with shape (L+2, 16384):
        # row 0 = BOS, row L+1 = EOS, rows 1..L correspond to residues 1..L
        try:
            indices = sae_tensor.coalesce().indices()  # shape (2, nnz)
            values = sae_tensor.coalesce().values()  # shape (nnz,)
        except Exception:
            # Fallback if tensor is dense
            indices = sae_tensor.nonzero(as_tuple=False).t()
            values = sae_tensor[indices[0], indices[1]]

        rows = indices[0].tolist()
        cols = indices[1].tolist()
        vals = values.tolist()

        # Determine residue rows to return (1-indexed positions → tensor row idx)
        if position is not None:
            lo_1idx = max(1, position - window)
            hi_1idx = min(seq_len, position + window)
            wanted_rows = set(range(lo_1idx, hi_1idx + 1))
        else:
            wanted_rows = set(range(1, seq_len + 1))

        # Bucket non-zero entries by residue row (skip BOS row 0 and EOS row L+1)
        per_residue: Dict[int, List[tuple]] = {}
        for r, c, v in zip(rows, cols, vals):
            if r in wanted_rows:
                per_residue.setdefault(r, []).append((c, v))

        # Sort each residue's features by |activation| descending, take top-K
        residues_out: List[Dict[str, Any]] = []
        for r in sorted(per_residue.keys()):
            feats = sorted(per_residue[r], key=lambda x: -abs(x[1]))[:top_k_per_residue]
            residues_out.append(
                {
                    "residue_idx_1based": r,
                    "active_features": [
                        {"feature_id": int(c), "activation": float(v)} for c, v in feats
                    ],
                }
            )

        return {
            "status": "success",
            "data": {
                "sequence_length": seq_len,
                "model": model,
                "sae_model": sae_model,
                "residues_returned": len(residues_out),
                "position": position,
                "window": window if position is not None else None,
                "top_k_per_residue": top_k_per_residue,
                "activations": residues_out,
            },
            "metadata": {
                "total_features_in_codebook": 16384,
                "sparsity_k": 64,
                "license": (
                    "Outputs are governed by EvolutionaryScale Cambrian "
                    "Inference License — non-commercial use only"
                ),
            },
        }

    # ------------------------------------------------------------------ #
    # score_variant_sae_disruption
    # ------------------------------------------------------------------ #
    def _score_variant_sae_disruption(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Composite tool: compare SAE features for reference vs mutant sequence
        and return per-feature delta scores ranked by absolute magnitude.

        This is the convenience layer that variant-interpretation skills use to
        avoid two manual ESM_get_sae_features calls plus manual delta
        computation. It builds the mutant sequence, runs both ref + mut through
        the SAE, sums activations over a residue window, and ranks features by
        gain or loss.

        For each ranked feature, the response includes the ref/mut activation
        sums so the agent can sanity-check whether a delta reflects a strong
        feature flipping off versus a weak feature appearing.
        """
        sequence = arguments.get("sequence")
        position = arguments.get("position")
        ref_aa = arguments.get("ref_aa")
        alt_aa = arguments.get("alt_aa")
        window = arguments.get("window", 8)
        top_k_features = arguments.get("top_k_features", 10)

        # Validate inputs
        if not sequence:
            return {
                "status": "error",
                "error": "sequence is required for score_variant_sae_disruption",
            }
        if position is None or not isinstance(position, int):
            return {
                "status": "error",
                "error": "position (1-indexed int) is required",
            }
        if not ref_aa or len(ref_aa) != 1:
            return {
                "status": "error",
                "error": "ref_aa must be a single amino-acid letter",
            }
        if not alt_aa or len(alt_aa) != 1:
            return {
                "status": "error",
                "error": "alt_aa must be a single amino-acid letter",
            }
        seq_len = len(sequence)
        if position < 1 or position > seq_len:
            return {
                "status": "error",
                "error": (
                    f"position {position} out of range [1, {seq_len}] "
                    f"for sequence of length {seq_len}"
                ),
            }
        actual_aa = sequence[position - 1]
        if actual_aa != ref_aa:
            return {
                "status": "error",
                "error": (
                    f"ref_aa mismatch: position {position} in sequence is "
                    f"{actual_aa!r}, but ref_aa was given as {ref_aa!r}. "
                    f"Double-check the sequence is the canonical reference for "
                    f"this variant."
                ),
            }

        # Build mutant
        mutant = sequence[: position - 1] + alt_aa + sequence[position:]

        # Get SAE features for ref + mut (reuse the existing operation)
        common_args = {
            "operation": "get_sae_features",
            "position": position,
            "window": window,
            "top_k_per_residue": 64,
            "model": arguments.get("model", "esmc-6b-2024-12"),
            "sae_model": arguments.get(
                "sae_model", "esmc-6b-2024-12_k64_codebook16384_layer60"
            ),
        }
        ref_result = self._get_sae_features({**common_args, "sequence": sequence})
        if ref_result["status"] != "success":
            return {**ref_result, "stage": "ref_sae"}

        mut_result = self._get_sae_features({**common_args, "sequence": mutant})
        if mut_result["status"] != "success":
            return {**mut_result, "stage": "mut_sae"}

        # Aggregate feature activations by feature_id (summed over window)
        def sum_features(activations_list):
            sums: Dict[int, float] = {}
            for r in activations_list:
                for f in r["active_features"]:
                    sums[f["feature_id"]] = (
                        sums.get(f["feature_id"], 0.0) + f["activation"]
                    )
            return sums

        ref_sums = sum_features(ref_result["data"]["activations"])
        mut_sums = sum_features(mut_result["data"]["activations"])

        all_feats = set(ref_sums) | set(mut_sums)
        deltas = [(f, mut_sums.get(f, 0.0) - ref_sums.get(f, 0.0)) for f in all_feats]

        top_lost = sorted(deltas, key=lambda x: x[1])[:top_k_features]
        top_gained = sorted(deltas, key=lambda x: -x[1])[:top_k_features]

        def feat_row(fid: int, delta: float) -> Dict[str, Any]:
            return {
                "feature_id": int(fid),
                "delta": float(delta),
                "ref_activation_sum": float(ref_sums.get(fid, 0.0)),
                "mut_activation_sum": float(mut_sums.get(fid, 0.0)),
            }

        return {
            "status": "success",
            "data": {
                "variant": f"{ref_aa}{position}{alt_aa}",
                "position": position,
                "window": window,
                "n_unique_features_touched": len(all_feats),
                "top_features_lost": [feat_row(f, d) for f, d in top_lost],
                "top_features_gained": [feat_row(f, d) for f, d in top_gained],
            },
            "metadata": {
                "method": (
                    "ESMC-6B SAE per-feature activation delta, summed over "
                    f"+/-{window} residue window centered on the mutation site"
                ),
                "ref_residues_analyzed": ref_result["data"]["residues_returned"],
                "mut_residues_analyzed": mut_result["data"]["residues_returned"],
                "forge_calls_made": 2,
                "license": (
                    "Outputs are governed by EvolutionaryScale Cambrian "
                    "Inference License — non-commercial use only"
                ),
            },
        }

    # ------------------------------------------------------------------ #
    # describe_sae_feature — on-demand SAE feature labeling
    # ------------------------------------------------------------------ #

    # Curated panel of well-annotated diverse human proteins. Used to label
    # SAE features by aggregating which UniProt feature types the SAE feature
    # activates on across the panel. Selected for category diversity:
    # transcription factor, kinase, GTPase, serine protease, P450 enzyme,
    # processed hormone, oxygen carrier, fibrinolytic protease, transport
    # protein, kinase.
    _SAE_LABELING_PANEL = [
        "P04637",  # TP53 — tumor suppressor / DNA binding
        "P00533",  # EGFR — receptor tyrosine kinase
        "P01116",  # KRAS — small GTPase
        "P00734",  # F2 thrombin — serine protease, catalytic triad
        "P08684",  # CYP3A4 — cytochrome P450, heme binding
        "P01308",  # INS — insulin (signal + disulfide + processing)
        "P68871",  # HBB — hemoglobin beta, oxygen / heme binding
        "P00750",  # PLAT/tPA — fibrinolytic protease
        "P02768",  # ALB — serum albumin, ligand binding
        "P31749",  # AKT1 — serine/threonine kinase
    ]

    # Map raw UniProt feature.type strings to high-level interpretable
    # categories. Types with value None are dropped from labeling counts
    # (too generic or uninformative for variant interpretation).
    _UNIPROT_TYPE_TO_CATEGORY = {
        "Active site": "catalytic",
        "Site": "catalytic",
        "Binding site": "ligand-binding",
        "Metal binding": "ligand-binding",
        "DNA binding": "ligand-binding",
        "Modified residue": "ptm",
        "Cross-link": "ptm",
        "Glycosylation": "ptm",
        "Lipidation": "ptm",
        "Domain": "domain",
        "Motif": "motif",
        "Repeat": "domain",
        "Zinc finger": "domain",
        "Disulfide bond": "structural-stability",
        "Helix": "secondary-structure",
        "Beta strand": "secondary-structure",
        "Turn": "secondary-structure",
        "Transmembrane": "transmembrane",
        "Intramembrane": "transmembrane",
        "Signal": "signal-peptide",
        "Propeptide": "propeptide",
        "Coiled coil": "structural-stability",
        "Region": None,
        "Compositional bias": None,
        "Natural variant": None,
        "Mutagenesis": None,
        "Alternative sequence": None,
        "Chain": None,
        "Peptide": None,
        "Initiator methionine": None,
    }

    def _fetch_uniprot_entry(self, accession: str) -> Optional[Dict[str, Any]]:
        """Fetch the full UniProt entry (sequence + features) for an accession.

        Returns None on network failure — caller will skip this protein.
        """
        import urllib.request
        import urllib.error

        url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "tooluniverse/esm_tool"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                import json as _json

                return _json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
            return None

    def _uniprot_features_at_position(
        self, features: List[Dict[str, Any]], position_1idx: int
    ) -> List[Dict[str, Any]]:
        """Return UniProt features whose annotated position/range covers
        the 1-indexed residue position."""
        hits = []
        for f in features:
            loc = f.get("location", {})
            start = loc.get("start", {}).get("value")
            end = loc.get("end", {}).get("value", start)
            if start is None or end is None:
                continue
            if start <= position_1idx <= end:
                hits.append(f)
        return hits

    def _cache_path_for_feature(self, sae_model: str, feature_id: int):
        """Per-feature label cache path under ~/.cache/tooluniverse/."""
        from pathlib import Path
        import re

        safe_model = re.sub(r"[^A-Za-z0-9._-]", "_", sae_model)
        cache_dir = Path.home() / ".cache" / "tooluniverse" / "sae_labels" / safe_model
        return cache_dir / f"feature_{feature_id}.json"

    def _describe_sae_feature(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """On-demand labeling for a single SAE feature_id.

        Runs SAE inference across a curated panel of well-annotated human
        proteins, finds where the target feature activates most strongly,
        and aggregates the UniProt feature types at those positions to
        infer a biological category. Caches results under
        ~/.cache/tooluniverse/sae_labels/{sae_model}/feature_{id}.json.

        Cost: 1 Forge credit per protein in the panel (default 10, so 10
        credits per first-time label). UniProt fetches are free.
        Subsequent calls for the same feature_id hit the cache (free).

        Categories returned: catalytic, ligand-binding, ptm, domain,
        motif, structural-stability, secondary-structure, transmembrane,
        signal-peptide, propeptide, or 'uncategorized'.
        """
        feature_id = arguments.get("feature_id")
        sae_model = arguments.get(
            "sae_model", "esmc-6b-2024-12_k64_codebook16384_layer60"
        )
        model = arguments.get("model", "esmc-6b-2024-12")
        n_proteins = arguments.get("n_proteins", 10)
        top_residues_per_protein = arguments.get("top_residues_per_protein", 3)
        use_cache = arguments.get("use_cache", True)

        # Validate input
        if feature_id is None or not isinstance(feature_id, int):
            return {
                "status": "error",
                "error": "feature_id (int 0-16383) is required",
            }
        if feature_id < 0 or feature_id >= 16384:
            return {
                "status": "error",
                "error": f"feature_id {feature_id} out of range [0, 16383]",
            }
        if n_proteins < 1 or n_proteins > len(self._SAE_LABELING_PANEL):
            return {
                "status": "error",
                "error": (
                    f"n_proteins must be in [1, {len(self._SAE_LABELING_PANEL)}], "
                    f"got {n_proteins}"
                ),
            }

        # Cache check
        cache_path = self._cache_path_for_feature(sae_model, feature_id)
        if use_cache and cache_path.exists():
            try:
                import json as _json

                cached = _json.loads(cache_path.read_text())
                cached.setdefault("metadata", {})["from_cache"] = True
                return cached
            except Exception:
                pass  # fall through and recompute

        # Run SAE labeling pipeline across the panel
        panel = self._SAE_LABELING_PANEL[:n_proteins]
        evidence: List[Dict[str, Any]] = []

        for accession in panel:
            entry = self._fetch_uniprot_entry(accession)
            if entry is None:
                continue
            seq = entry.get("sequence", {}).get("value")
            uniprot_features = entry.get("features", []) or []
            if not seq:
                continue

            sae_response = self._get_sae_features(
                {
                    "operation": "get_sae_features",
                    "sequence": seq,
                    "model": model,
                    "sae_model": sae_model,
                    "top_k_per_residue": 64,
                }
            )
            if sae_response.get("status") != "success":
                # Likely a panel protein too long, Forge errored, etc.; skip
                continue

            # Find residues where target feature_id activates
            activating: List[Dict[str, Any]] = []
            for residue in sae_response["data"]["activations"]:
                for feat in residue["active_features"]:
                    if feat["feature_id"] == feature_id:
                        activating.append(
                            {
                                "position": residue["residue_idx_1based"],
                                "activation": feat["activation"],
                            }
                        )
                        break
            if not activating:
                continue

            activating.sort(key=lambda x: -abs(x["activation"]))
            top = activating[:top_residues_per_protein]

            for hit in top:
                pos = hit["position"]
                overlapping = self._uniprot_features_at_position(uniprot_features, pos)
                informative_types = [
                    f["type"]
                    for f in overlapping
                    if self._UNIPROT_TYPE_TO_CATEGORY.get(f["type"]) is not None
                ]
                evidence.append(
                    {
                        "protein": accession,
                        "position_1based": pos,
                        "activation": float(hit["activation"]),
                        "uniprot_types": informative_types,
                        "uniprot_categories": [
                            self._UNIPROT_TYPE_TO_CATEGORY[t] for t in informative_types
                        ],
                    }
                )

        # Aggregate categories across all evidence rows
        category_counts: Dict[str, int] = {}
        for e in evidence:
            for cat in e["uniprot_categories"]:
                category_counts[cat] = category_counts.get(cat, 0) + 1

        if category_counts:
            dominant = max(category_counts.items(), key=lambda x: x[1])
            category = dominant[0]
            total_votes = sum(category_counts.values())
            confidence = dominant[1] / total_votes
        else:
            category = "uncategorized"
            confidence = 0.0

        result = {
            "status": "success",
            "data": {
                "feature_id": feature_id,
                "sae_model": sae_model,
                "category": category,
                "confidence": round(confidence, 3),
                "n_proteins_with_activation": len(set(e["protein"] for e in evidence)),
                "n_proteins_analyzed": len(panel),
                "category_vote_counts": category_counts,
                "supporting_evidence": evidence,
            },
            "metadata": {
                "from_cache": False,
                "method": (
                    "Aggregated UniProt feature-type overlap at SAE-activating "
                    "residues across a curated 10-protein panel"
                ),
                "forge_credits_used_first_call": n_proteins,
                "license": (
                    "Outputs are governed by EvolutionaryScale Cambrian "
                    "Inference License — non-commercial use only"
                ),
            },
        }

        # Write cache (best-effort)
        try:
            import json as _json

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(_json.dumps(result, indent=2))
        except Exception:
            pass

        return result

    @staticmethod
    def _build_per_pos_map(
        activations: List[Dict[str, Any]],
    ) -> Dict[int, Dict[int, float]]:
        """Index SAE activations as {residue_idx_1based: {feature_id: activation}}."""
        return {
            r["residue_idx_1based"]: {
                f["feature_id"]: f["activation"] for f in r["active_features"]
            }
            for r in activations
        }

    @staticmethod
    def _validate_batch_variant(
        v: Dict[str, Any], i: int, sequence: str, seq_len: int
    ) -> Optional[str]:
        """Return None if the variant dict is valid, else an error string."""
        for key in ("position", "ref_aa", "alt_aa"):
            if key not in v:
                return f"variants[{i}] missing key {key!r}"
        pos = v["position"]
        if not isinstance(pos, int) or pos < 1 or pos > seq_len:
            return f"variants[{i}] position {pos} out of range [1, {seq_len}]"
        if not isinstance(v["ref_aa"], str) or len(v["ref_aa"]) != 1:
            return f"variants[{i}] ref_aa must be a single letter"
        if not isinstance(v["alt_aa"], str) or len(v["alt_aa"]) != 1:
            return f"variants[{i}] alt_aa must be a single letter"
        actual = sequence[pos - 1]
        if actual != v["ref_aa"]:
            return (
                f"variants[{i}]: position {pos} in sequence is "
                f"{actual!r}, but ref_aa was {v['ref_aa']!r}"
            )
        return None

    # ------------------------------------------------------------------ #
    # score_variant_sae_batch — N variants, N+1 Forge calls (not 2N)
    # ------------------------------------------------------------------ #
    def _score_variant_sae_batch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Score many missense variants against one reference sequence.

        Standard score_variant_sae_disruption makes 2 Forge calls per variant
        (ref + mut). For N variants on the same reference this tool runs the
        reference SAE once and one mutant SAE per variant — N+1 calls total.
        Use for saturation mutagenesis (all 19 alts at one position),
        DMS-style sweeps, or scoring a clinical-variant panel.
        """
        sequence = arguments.get("sequence")
        variants = arguments.get("variants")
        window = arguments.get("window", 8)
        top_k_features = arguments.get("top_k_features", 10)
        model = arguments.get("model", "esmc-6b-2024-12")
        sae_model = arguments.get(
            "sae_model", "esmc-6b-2024-12_k64_codebook16384_layer60"
        )

        if not sequence:
            return {"status": "error", "error": "sequence is required"}
        if not variants or not isinstance(variants, list):
            return {
                "status": "error",
                "error": "variants must be a non-empty list of {position, ref_aa, alt_aa}",
            }
        # Cap batch size — Forge cost scales linearly and a runaway list
        # of 1000 variants would silently burn the user's credit budget.
        MAX_VARIANTS = 100
        if len(variants) > MAX_VARIANTS:
            return {
                "status": "error",
                "error": (
                    f"too many variants ({len(variants)}); cap is {MAX_VARIANTS} "
                    f"per call. Split into multiple calls."
                ),
            }

        seq_len = len(sequence)
        for i, v in enumerate(variants):
            err = self._validate_batch_variant(v, i, sequence, seq_len)
            if err is not None:
                return {"status": "error", "error": err}

        # One reference SAE call over the full sequence — reused for every
        # variant's per-window delta computation.
        ref_full = self._get_sae_features(
            {
                "operation": "get_sae_features",
                "sequence": sequence,
                "model": model,
                "sae_model": sae_model,
                "top_k_per_residue": 64,
            }
        )
        if ref_full["status"] != "success":
            return {**ref_full, "stage": "ref_sae"}

        ref_by_pos = self._build_per_pos_map(ref_full["data"]["activations"])

        def sum_in_window(per_pos_map, pos, window):
            lo = max(1, pos - window)
            hi = min(seq_len, pos + window)
            sums: Dict[int, float] = {}
            for p in range(lo, hi + 1):
                for fid, act in per_pos_map.get(p, {}).items():
                    sums[fid] = sums.get(fid, 0.0) + act
            return sums

        per_variant: List[Dict[str, Any]] = []
        forge_calls = 1  # the ref_full call above
        for v in variants:
            pos = v["position"]
            mutant = sequence[: pos - 1] + v["alt_aa"] + sequence[pos:]
            variant_label = f"{v['ref_aa']}{pos}{v['alt_aa']}"

            mut_result = self._get_sae_features(
                {
                    "operation": "get_sae_features",
                    "sequence": mutant,
                    "model": model,
                    "sae_model": sae_model,
                    "position": pos,
                    "window": window,
                    "top_k_per_residue": 64,
                }
            )
            forge_calls += 1
            if mut_result["status"] != "success":
                per_variant.append(
                    {
                        "variant": variant_label,
                        "status": "error",
                        "error": mut_result.get("error", "mut SAE failed"),
                    }
                )
                continue

            mut_by_pos = self._build_per_pos_map(mut_result["data"]["activations"])
            ref_sums = sum_in_window(ref_by_pos, pos, window)
            mut_sums = sum_in_window(mut_by_pos, pos, window)

            all_feats = set(ref_sums) | set(mut_sums)
            deltas = [
                (f, mut_sums.get(f, 0.0) - ref_sums.get(f, 0.0)) for f in all_feats
            ]
            top_lost = sorted(deltas, key=lambda x: x[1])[:top_k_features]
            top_gained = sorted(deltas, key=lambda x: -x[1])[:top_k_features]

            def feat_row(fid, delta):
                return {
                    "feature_id": int(fid),
                    "delta": float(delta),
                    "ref_activation_sum": float(ref_sums.get(fid, 0.0)),
                    "mut_activation_sum": float(mut_sums.get(fid, 0.0)),
                }

            per_variant.append(
                {
                    "variant": variant_label,
                    "status": "success",
                    "position": pos,
                    "n_unique_features_touched": len(all_feats),
                    "top_features_lost": [feat_row(f, d) for f, d in top_lost],
                    "top_features_gained": [feat_row(f, d) for f, d in top_gained],
                }
            )

        return {
            "status": "success",
            "data": {
                "sequence_length": seq_len,
                "n_variants": len(variants),
                "n_succeeded": sum(1 for v in per_variant if v["status"] == "success"),
                "window": window,
                "results": per_variant,
            },
            "metadata": {
                "method": (
                    f"ESMC-6B SAE per-feature activation delta, summed over "
                    f"+/-{window} residue window. Reference SAE computed once "
                    f"and reused across all variants."
                ),
                "forge_calls_made": forge_calls,
                "forge_calls_saved_vs_per_variant": len(variants) - 1,
                "license": (
                    "Outputs are governed by EvolutionaryScale Cambrian "
                    "Inference License — non-commercial use only"
                ),
            },
        }

    # ------------------------------------------------------------------ #
    # get_region_sae_features — domain/epitope-level feature signature
    # ------------------------------------------------------------------ #
    def _get_region_sae_features(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate SAE features over a residue range.

        Characterizes a contiguous region (a domain, epitope, binding pocket,
        signal peptide, etc.) by its dominant SAE features. Each returned
        feature has its total |activation| over the region, mean activation,
        and which residues in the region activate it. Feed feature_ids into
        ESM_describe_sae_feature to get biological category labels.
        """
        sequence = arguments.get("sequence")
        start = arguments.get("start_position")
        end = arguments.get("end_position")
        top_k_features = arguments.get("top_k_features", 20)
        model = arguments.get("model", "esmc-6b-2024-12")
        sae_model = arguments.get(
            "sae_model", "esmc-6b-2024-12_k64_codebook16384_layer60"
        )

        if not sequence:
            return {"status": "error", "error": "sequence is required"}
        if not isinstance(start, int) or not isinstance(end, int):
            return {
                "status": "error",
                "error": "start_position and end_position must be integers (1-indexed)",
            }
        seq_len = len(sequence)
        if start < 1 or end > seq_len or start > end:
            return {
                "status": "error",
                "error": (
                    f"region [{start}, {end}] out of range [1, {seq_len}] "
                    f"or start > end"
                ),
            }
        region_len = end - start + 1
        # Region cap — beyond this, top-K aggregation becomes a coarse summary
        # and the user is better off making multiple smaller calls.
        MAX_REGION_LEN = 500
        if region_len > MAX_REGION_LEN:
            return {
                "status": "error",
                "error": (
                    f"region length {region_len} exceeds {MAX_REGION_LEN}; "
                    f"split into smaller windows for meaningful aggregation"
                ),
            }

        sae_result = self._get_sae_features(
            {
                "operation": "get_sae_features",
                "sequence": sequence,
                "model": model,
                "sae_model": sae_model,
                "top_k_per_residue": 64,
            }
        )
        if sae_result["status"] != "success":
            return sae_result

        abs_sums: Dict[int, float] = {}
        signed_sums: Dict[int, float] = {}
        hit_residues: Dict[int, List[int]] = {}
        for residue in sae_result["data"]["activations"]:
            pos = residue["residue_idx_1based"]
            if pos < start or pos > end:
                continue
            for feat in residue["active_features"]:
                fid = feat["feature_id"]
                act = feat["activation"]
                abs_sums[fid] = abs_sums.get(fid, 0.0) + abs(act)
                signed_sums[fid] = signed_sums.get(fid, 0.0) + act
                hit_residues.setdefault(fid, []).append(pos)

        ranked = sorted(abs_sums.items(), key=lambda x: -x[1])[:top_k_features]
        features_out: List[Dict[str, Any]] = []
        for fid, total_abs in ranked:
            positions = hit_residues[fid]
            features_out.append(
                {
                    "feature_id": int(fid),
                    "total_abs_activation": float(total_abs),
                    "mean_activation": float(signed_sums[fid] / len(positions)),
                    "n_residues_active": len(positions),
                    "fraction_residues_active": round(len(positions) / region_len, 3),
                    "active_positions": sorted(positions),
                }
            )

        return {
            "status": "success",
            "data": {
                "sequence_length": seq_len,
                "region": [start, end],
                "region_length": region_len,
                "n_features_active_in_region": len(abs_sums),
                "top_features": features_out,
            },
            "metadata": {
                "method": (
                    "SAE features summed over a residue range, ranked by "
                    "total |activation|. Feed top feature_ids into "
                    "ESM_describe_sae_feature for biological category labels."
                ),
                "forge_calls_made": 1,
                "license": (
                    "Outputs are governed by EvolutionaryScale Cambrian "
                    "Inference License — non-commercial use only"
                ),
            },
        }

    # ------------------------------------------------------------------ #
    # explain_variant_mechanism — disruption + describe + summary in one call
    # ------------------------------------------------------------------ #
    def _explain_variant_mechanism(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Composite tool: variant disruption + describe top affected features.

        Runs score_variant_sae_disruption to find the most-changed features,
        then describe_sae_feature on each (cached after first call) to get
        biological category labels, then composes a 1-line mechanism summary
        (e.g. "Disrupted feature categories (lost): catalytic=2, ligand-binding=1").
        Use when the calling skill wants mechanism in one call rather than
        orchestrating two tool calls and parsing both results.
        """
        sequence = arguments.get("sequence")
        position = arguments.get("position")
        ref_aa = arguments.get("ref_aa")
        alt_aa = arguments.get("alt_aa")
        window = arguments.get("window", 8)
        top_k_features = arguments.get("top_k_features", 5)
        include_descriptions = arguments.get("include_descriptions", True)
        model = arguments.get("model", "esmc-6b-2024-12")
        sae_model = arguments.get(
            "sae_model", "esmc-6b-2024-12_k64_codebook16384_layer60"
        )

        # Delegate input validation to disruption sub-call
        disruption = self._score_variant_sae_disruption(
            {
                "operation": "score_variant_sae_disruption",
                "sequence": sequence,
                "position": position,
                "ref_aa": ref_aa,
                "alt_aa": alt_aa,
                "window": window,
                "top_k_features": top_k_features,
                "model": model,
                "sae_model": sae_model,
            }
        )
        if disruption["status"] != "success":
            return disruption

        top_lost = disruption["data"]["top_features_lost"]
        top_gained = disruption["data"]["top_features_gained"]

        described_lost: List[Dict[str, Any]] = []
        described_gained: List[Dict[str, Any]] = []
        describe_calls = 0
        describe_credits = 0

        if include_descriptions:
            label_cache: Dict[int, Dict[str, Any]] = {}

            def label_for(fid: int) -> Dict[str, Any]:
                nonlocal describe_calls, describe_credits
                if fid in label_cache:
                    return label_cache[fid]
                result = self._describe_sae_feature(
                    {
                        "operation": "describe_sae_feature",
                        "feature_id": fid,
                        "sae_model": sae_model,
                        "model": model,
                    }
                )
                describe_calls += 1
                meta = result.get("metadata", {}) if isinstance(result, dict) else {}
                if meta.get("from_cache") is False:
                    describe_credits += meta.get("forge_credits_used_first_call", 0)
                if result.get("status") == "success":
                    cat_label = {
                        "category": result["data"]["category"],
                        "confidence": result["data"]["confidence"],
                    }
                else:
                    cat_label = {"category": "unknown", "confidence": 0.0}
                label_cache[fid] = cat_label
                return cat_label

            for feat in top_lost:
                described_lost.append({**feat, **label_for(feat["feature_id"])})
            for feat in top_gained:
                described_gained.append({**feat, **label_for(feat["feature_id"])})
        else:
            described_lost = list(top_lost)
            described_gained = list(top_gained)

        def categorize(items: List[Dict[str, Any]]) -> List[tuple]:
            cats: Dict[str, int] = {}
            for it in items:
                cat = it.get("category", "unknown")
                cats[cat] = cats.get(cat, 0) + 1
            return sorted(cats.items(), key=lambda x: -x[1])

        lost_cats = categorize(described_lost)
        gained_cats = categorize(described_gained)

        if not include_descriptions:
            summary = (
                "Descriptions skipped (include_descriptions=False); "
                "see top_features_lost/gained for raw feature_ids."
            )
        else:
            summary_parts: List[str] = []
            if lost_cats:
                summary_parts.append(
                    "Disrupted feature categories (lost): "
                    + ", ".join(f"{c}={n}" for c, n in lost_cats[:3])
                )
            if gained_cats:
                summary_parts.append(
                    "Induced feature categories (gained): "
                    + ", ".join(f"{c}={n}" for c, n in gained_cats[:3])
                )
            summary = (
                "; ".join(summary_parts)
                if summary_parts
                else "No interpretable feature changes detected."
            )

        return {
            "status": "success",
            "data": {
                "variant": disruption["data"]["variant"],
                "position": position,
                "window": window,
                "mechanism_summary": summary,
                "lost_feature_categories": dict(lost_cats),
                "gained_feature_categories": dict(gained_cats),
                "top_features_lost": described_lost,
                "top_features_gained": described_gained,
            },
            "metadata": {
                "method": (
                    "ESMC-6B SAE variant disruption + per-feature biological "
                    "labeling, composed into a 1-line mechanism category summary."
                ),
                "disruption_forge_calls": 2,
                "describe_feature_calls": describe_calls,
                "describe_forge_credits_used": describe_credits,
                "license": (
                    "Outputs are governed by EvolutionaryScale Cambrian "
                    "Inference License — non-commercial use only"
                ),
            },
        }
