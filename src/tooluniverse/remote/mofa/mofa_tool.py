"""
MOFA+ multi-omics factor analysis — MCP Server.

MOFA+ (Multi-Omics Factor Analysis v2; Argelaguet et al., Genome Biology 2020)
is an unsupervised, generative framework that integrates several omics layers
measured on the SAME set of samples. It infers a small number of latent
"factors" — analogous to principal components — that capture the dominant axes
of variation shared across (and specific to) the omics views, and reports how
much variance each factor explains in each view.

This module exposes MOFA+ as a ToolUniverse *remote* tool because it carries a
heavy dependency stack (`mofapy2` -> a probabilistic Bayesian inference engine
built on numpy/scipy). Running it on a dedicated server keeps the core
ToolUniverse install light.

Inputs are inlined as a ``views`` object — one matrix per omics view over the
same samples — because the integration is run over a single shared sample set,
which is typically modest in size.

One operation is served:
  * run_mofa_factors -> per-sample latent factor matrix + variance explained

References
----------
Argelaguet R, Arnol D, Bredikhin D, et al. "MOFA+: a statistical framework for
comprehensive integration of multi-modal single-cell data." Genome Biology 21,
111 (2020).
Argelaguet R, Velten B, Arnol D, et al. "Multi-Omics Factor Analysis — a
framework for unsupervised integration of multi-omics data sets." Molecular
Systems Biology 14, e8124 (2018).
"""

from typing import Any, Dict

import numpy as np
from mofapy2.run.entry_point import entry_point

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server


def _view_to_matrix(view: Dict[str, Any], n_samples: int):
    """Transpose a feature-major view {feature: [value_per_sample]} to a
    (samples x features) numpy matrix; validate consistent sample counts."""
    features = list(view.keys())
    if not features:
        raise ValueError("a view has no features")
    cols = []
    for feat in features:
        values = view[feat]
        if not isinstance(values, (list, tuple)):
            raise ValueError(f"feature '{feat}' values must be a list")
        if len(values) != n_samples:
            raise ValueError(
                f"feature '{feat}' has {len(values)} values but expected "
                f"{n_samples} (one per sample)"
            )
        cols.append([float(v) for v in values])
    # cols is features x samples -> transpose to samples x features
    mat = np.asarray(cols, dtype=float).T
    return mat, features


@register_mcp_tool(
    tool_type_name="run_mofa_factors",
    config={
        "description": (
            "Run MOFA+ (Multi-Omics Factor Analysis v2; Argelaguet 2020) to "
            "integrate multiple omics 'views' measured on the SAME samples into "
            "a small set of unsupervised latent factors. Returns the per-sample "
            "factor matrix and the fraction of variance each factor explains in "
            "each view."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "views": {
                    "type": "object",
                    "description": (
                        "Omics views over the SAME samples: "
                        "{view_name: {feature: [value_per_sample]}}. Every "
                        "feature list (across all views) must have the same "
                        "length = number of samples, in the same sample order."
                    ),
                },
                "samples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional sample names; length must match the per-feature "
                        "value-list length. Defaults to sample_0..sample_{N-1}."
                    ),
                },
                "n_factors": {
                    "type": "integer",
                    "description": "Number of latent factors to infer (default 10).",
                },
                "n_iter": {
                    "type": "integer",
                    "description": "Maximum training iterations (default 1000).",
                },
            },
            "required": ["views"],
        },
    },
    mcp_config={
        "server_name": "MOFA+ MCP Server",
        "host": "127.0.0.1",
        "port": 8024,
        "transport": "http",
    },
)
class MofaFactorsTool:
    """Run MOFA+ and return per-sample latent factors + variance explained."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            views = arguments.get("views")
            if not views or not isinstance(views, dict):
                return {
                    "error": "Missing/invalid required parameter: views "
                    "(expected {view_name: {feature: [value_per_sample]}})"
                }

            view_names = list(views.keys())

            # Infer the shared sample count from the first feature of the first view.
            first_view = views[view_names[0]]
            if not isinstance(first_view, dict) or not first_view:
                return {"error": f"view '{view_names[0]}' has no features"}
            first_feature = next(iter(first_view.values()))
            if not isinstance(first_feature, (list, tuple)) or not first_feature:
                return {
                    "error": f"view '{view_names[0]}' features must be non-empty lists"
                }
            n_samples = len(first_feature)

            samples = arguments.get("samples")
            if samples:
                if len(samples) != n_samples:
                    return {
                        "error": f"samples length ({len(samples)}) does not match "
                        f"per-feature value-list length ({n_samples})"
                    }
                samples = [str(s) for s in samples]
            else:
                samples = [f"sample_{i}" for i in range(n_samples)]

            n_factors = int(arguments.get("n_factors") or 10)
            n_iter = int(arguments.get("n_iter") or 1000)

            # Build per-view (samples x features) matrices.
            data = []
            features_names = []
            for vname in view_names:
                mat, feats = _view_to_matrix(views[vname], n_samples)
                # MOFA expects data[view][group] = matrix; single group per view.
                data.append([mat])
                features_names.append(feats)

            ent = entry_point()
            ent.set_data_options(scale_views=True)
            ent.set_data_matrix(
                data,
                views_names=view_names,
                samples_names=[samples],
                features_names=features_names,
            )
            ent.set_model_options(factors=n_factors)
            ent.set_train_options(
                iter=n_iter, convergence_mode="fast", verbose=False, seed=0
            )
            ent.build()
            ent.run()

            # Per-sample factor matrix (samples x factors).
            z = ent.model.getExpectations()["Z"]["E"]
            factors = np.asarray(z, dtype=float)
            n_factors_out = int(factors.shape[1])

            # Variance explained: r2 per view per factor.
            r2 = ent.model.calculate_variance_explained()
            # r2[0] -> (n_views x n_factors) array for the single group.
            r2_group = np.asarray(r2[0], dtype=float)
            variance_explained = {
                vname: [float(x) for x in r2_group[i]]
                for i, vname in enumerate(view_names)
            }

            return {
                "n_samples": n_samples,
                "n_views": len(view_names),
                "n_factors": n_factors_out,
                "view_names": view_names,
                "variance_explained": variance_explained,
                "factors": factors.tolist(),
                "samples": samples,
            }
        except Exception as exc:  # never raise out of run()
            return {"error": f"MOFA+ run failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
