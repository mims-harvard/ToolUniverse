"""Render the blog's aggregate data and ToolUniverse workflow with Matplotlib.

Run with Python 3.12+, matplotlib and numpy. CSVs contain all 33 paired
reference combinations from the native preparation pilot, not assay replicates.
Optional --qa-scripts enables the figure alignment auditor before export.
"""

import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent
mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def export(fig, stem, qa_scripts):
    fig.canvas.draw()
    if qa_scripts:
        sys.path.insert(0, str(qa_scripts))
        from audit_panel_alignment import require_matplotlib_panel_alignment

        require_matplotlib_panel_alignment(
            fig,
            json_out=str(ROOT / f"{stem}.alignment.json"),
            tolerance_pt=1.5,
            strict=True,
        )
    else:
        (ROOT / f"{stem}.alignment.json").write_text(
            json.dumps(
                {
                    "status": "NOT APPLICABLE",
                    "reason": "One axes; no comparable panels.",
                }
            )
            + "\n"
        )
    fig.savefig(ROOT / f"{stem}.svg", facecolor="white")
    svg_path = ROOT / f"{stem}.svg"
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text().splitlines()) + "\n"
    )
    fig.savefig(ROOT / f"{stem}.pdf", facecolor="white")
    fig.savefig(ROOT / f"{stem}.png", dpi=300, facecolor="white")
    plt.close(fig)


def sensitivity(qa_scripts):
    rows = list(csv.DictReader((ROOT / "reference_sensitivity.csv").open()))
    # Every row is displayed. Ranges are extrema of the specified correlated
    # reference combinations; no bootstrap, CI, SD, or statistical test is used.
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    fig.subplots_adjust(left=0.31, right=0.96, bottom=0.23, top=0.77)
    models = ["Protenix", "Boltz", "RoseTTAFold3"]
    labels = []
    for i, (model, reference) in enumerate(
        (m, r) for m in models for r in ["Independent", "Same-coordinate"]
    ):
        y = 5 - i
        labels.append(f"{model} · {reference}")
        for stage, shift, color in [
            ("original", 0.13, "#9AA3AF"),
            ("reprepared", -0.13, "#1E7086"),
        ]:
            row = next(
                r
                for r in rows
                if r["model"] == model
                and r["free_reference"] == reference
                and r["preparation"] == stage
            )
            lo, hi = float(row["min_kcal_mol"]), float(row["max_kcal_mol"])
            if int(row["n_matched_reference_combinations"]) == 1:
                ax.plot(lo, y + shift, "o", color=color, ms=5, zorder=3)
            else:
                ax.plot(
                    [lo, hi],
                    [y + shift, y + shift],
                    color=color,
                    lw=3,
                    solid_capstyle="round",
                    zorder=3,
                )
    ax.axvline(0, color="#C7CDD4", lw=1, zorder=0)
    ax.set_yticks(range(6), list(reversed(labels)), fontsize=8.7)
    ax.set_ylim(-0.65, 5.65)
    ax.set_xlim(-0.43, 0.38)
    ax.set_xticks([-0.4, -0.2, 0, 0.2])
    ax.set_xlabel(
        "M48L − parent: change in acidic-release linkage (kcal/mol)", labelpad=10
    )
    ax.tick_params(axis="y", length=0, pad=10)
    ax.spines["left"].set_visible(False)
    fig.text(
        0.06,
        0.93,
        "The pH comparison changed with preparation",
        fontsize=15,
        weight="bold",
        color="#202E3D",
    )
    fig.text(
        0.06,
        0.865,
        "Complete 174-group PROPKA diagnostic · pH 6.0 relative to 7.4 · 298.15 K",
        fontsize=9,
        color="#506176",
    )
    fig.text(
        0.06,
        0.10,
        "← Smaller release-direction term                         Larger release-direction term →",
        fontsize=9,
        color="#506176",
    )
    fig.text(
        0.06,
        0.045,
        "Ranges: 10 matched free-reference combinations; points: one same-coordinate reference. No assay data.",
        fontsize=8,
        color="#506176",
    )
    fig.legend(
        handles=[
            Line2D([0], [0], color="#9AA3AF", lw=3, label="Original"),
            Line2D([0], [0], color="#1E7086", lw=3, label="Re-prepared"),
        ],
        loc="upper right",
        bbox_to_anchor=(0.965, 0.835),
        ncol=2,
        frameon=False,
        fontsize=9,
        handlelength=2,
    )
    export(fig, "reference_sensitivity", qa_scripts)


def workflow(qa_scripts):
    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.015, top=0.985)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    def box(x, y, w, h, title, body, fill="#F2F6F9", edge="#D3DFE8"):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.5,rounding_size=1.4",
                facecolor=fill,
                edgecolor=edge,
                lw=1,
            )
        )
        ax.text(
            x + w / 2,
            y + h - 3,
            title,
            ha="center",
            va="center",
            fontsize=11,
            weight="bold",
            color="#203A50",
        )
        ax.text(
            x + w / 2,
            y + (h - 4) / 2,
            body,
            ha="center",
            va="center",
            fontsize=9,
            color="#40566B",
            linespacing=1.6,
        )

    def arrow(a, b):
        ax.add_patch(
            FancyArrowPatch(
                a,
                b,
                arrowstyle="-|>",
                mutation_scale=11,
                color="#6B8498",
                lw=1.3,
                connectionstyle="arc3",
            )
        )

    ax.text(
        3,
        46,
        "An agent uses ToolUniverse’s skills and tools together",
        fontsize=15,
        weight="bold",
        color="#202E3D",
    )
    box(
        2,
        22,
        19,
        18,
        "Researcher + agent",
        "Set the objective\nInspect evidence\nChoose the next task",
    )
    box(29, 17, 40, 25, "ToolUniverse", "", fill="#EAF3F7", edge="#93BACB")
    box(
        31,
        19,
        17,
        15,
        "Skills",
        "Research judgment\nSetup and recovery\nClaim boundaries",
        fill="white",
    )
    box(
        50,
        19,
        17,
        15,
        "Tools",
        "Public data + local QC\nTyped model calls\nProvenance",
        fill="white",
    )
    box(
        77,
        22,
        21,
        18,
        "DGX Spark",
        "GPU remote tools\nModel environments\nAdmission + execution",
    )
    box(
        28,
        1,
        43,
        10,
        "Evidence for the next decision",
        "Results · controls · failures · uncertainty",
        fill="#F6F8FA",
    )
    arrow((21.5, 31), (28.5, 31))
    arrow((69.5, 31), (76.5, 31))
    arrow((87, 21.3), (71.5, 6))
    arrow((27.5, 6), (11.5, 21.2))
    export(fig, "workflow", qa_scripts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa-scripts", type=Path)
    args = parser.parse_args()
    sensitivity(args.qa_scripts)
    workflow(args.qa_scripts)
