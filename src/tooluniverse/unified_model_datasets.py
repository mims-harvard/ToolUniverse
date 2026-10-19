"""Public benchmark datasets for the unified model interface.

Every dataset here is public, citable and fetched from its canonical home, so
a leaderboard produced by ``benchmark_*`` can be checked by someone else:

``proteingym_dms``
    ProteinGym deep-mutational-scanning substitution assays (217 of them),
    from the OATML-Markslab HuggingFace dataset. Labels are *experimental*
    fitness measurements, not other models' opinions or curated clinical
    calls, which makes this the strongest available ground truth for
    variant-effect models -- and the benchmark those models are published
    against.

``clinvar_missense``
    Clinically labelled pathogenic/benign missense variants, assembled live
    through MyVariant.info rather than downloaded in bulk. Convenient and
    current, but see the label-leakage warning below.

``tdc_admet``
    The Therapeutics Data Commons ADMET collection from Harvard Dataverse
    (DOI 10.7910/DVN/21LKWG) -- the same splits the public TDC ADMET
    leaderboards are scored on, and the source of the canonical property ids
    this interface uses.

``file``
    Any local CSV/TSV/JSONL, for private or in-house evaluation sets.

**Label leakage is a real hazard and is checked, not assumed away.** Several
backends were trained on, or directly consult, the labels a benchmark might
use: GeneBe reads ClinVar at query time, REVEL and CADD were trained partly on
ClinVar-derived sets, and dbNSFP redistributes clinical annotations. Scoring
those against ``clinvar_missense`` measures memorization, not prediction.
``leakage_risk`` records which backends are compromised by which dataset and
the benchmark runner surfaces it in its report rather than quietly producing a
99% AUROC that looks like a result.

Downloads are cached under ``$TOOLUNIVERSE_CACHE_DIR`` (default
``~/.cache/tooluniverse/benchmarks``) so repeated runs and CI do not re-fetch.
"""

from __future__ import annotations

import csv
import io
import json
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_HF_PROTEINGYM = "https://huggingface.co/datasets/OATML-Markslab/ProteinGym"
_HF_TREE = "https://huggingface.co/api/datasets/OATML-Markslab/ProteinGym/tree/main"
_HF_RESOLVE = _HF_PROTEINGYM + "/resolve/main"
# The reference index is taken from the *same* HuggingFace repo as the assay
# files, not from the ProteinGym website. They are different releases: the
# website serves the v1.1 index (217 assays) while this repo holds v1.0 (87),
# and pairing them means two thirds of the lookups resolve to an assay whose
# data file does not exist here.
_PG_REFERENCE = _HF_RESOLVE + "/ProteinGym_reference_file_substitutions.csv"
_DATAVERSE_SEARCH = "https://dataverse.harvard.edu/api/search"
_DATAVERSE_FILE = "https://dataverse.harvard.edu/api/access/datafile/"
_TDC_DOI = "doi:10.7910/DVN/21LKWG"

# Which backends must not be scored against which dataset, and why.
LEAKAGE_RISK: Dict[str, Dict[str, str]] = {
    "tdc_admet": {
        # The catalogue already advertised this risk, but the runner did not
        # act on it, so a TDC benchmark printed "leakage: none" while scoring a
        # model against the very data it was trained on. The two must agree.
        "admet_ai": (
            "ADMET-AI is trained on the TDC ADMET datasets. Scores here are "
            "in-distribution and are not a held-out evaluation; they are not "
            "comparable with a model that never saw this data."
        ),
        "tdc_oracle": (
            "TDC oracles are the scoring functions these datasets are built "
            "around, so agreement with the labels is close to definitional."
        ),
    },
    "clinvar_missense": {
        "genebe_acmg": "Queries ClinVar directly at prediction time -- it is reading the answer key.",
        "revel": "Trained on ClinVar-derived pathogenic/benign sets; overlap with any ClinVar benchmark is likely.",
        "vest4": "Trained on clinical variant databases overlapping ClinVar.",
        "metarnn": "Trained on ClinVar-derived labels.",
        "cadd": "Training data includes clinically curated variant sets.",
        "cancervar": "Consults clinical evidence databases at query time.",
    },
}


def cache_dir() -> Path:
    root = os.environ.get("TOOLUNIVERSE_CACHE_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "tooluniverse"
    )
    path = Path(root) / "benchmarks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fetch(url: str, filename: str, timeout: int = 180) -> bytes:
    """Download once, then serve from disk.

    Benchmarks re-run constantly while a model or a threshold is being tuned;
    re-downloading a dataset each time would dominate the runtime and hammer
    someone else's server for no reason.
    """
    target = cache_dir() / filename
    if target.exists() and target.stat().st_size > 0:
        return target.read_bytes()

    import requests

    response = requests.get(
        url, timeout=timeout, headers={"User-Agent": "ToolUniverse/benchmark"}
    )
    response.raise_for_status()
    payload = response.content
    tmp = target.with_suffix(target.suffix + ".part")
    tmp.write_bytes(payload)
    tmp.replace(target)  # atomic, so an interrupted run cannot cache a truncated file
    return payload


def _read_delimited(
    payload: bytes, delimiter: Optional[str] = None
) -> List[Dict[str, str]]:
    text = payload.decode("utf-8", errors="replace")
    if delimiter is None:
        head = text.split("\n", 1)[0]
        delimiter = "\t" if head.count("\t") > head.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


@dataclass
class Dataset:
    """A benchmark: items with canonical inputs, plus a label per item."""

    id: str
    name: str
    task: str
    items: List[Dict[str, Any]]
    label_type: str  # "binary" | "continuous"
    source_url: str = ""
    citation: str = ""
    license: str = ""
    notes: str = ""
    label_field: str = "label"
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def labels(self) -> List[Any]:
        return [item.get(self.label_field) for item in self.items]

    def describe(self) -> Dict[str, Any]:
        positives = (
            sum(1 for value in self.labels if value == 1)
            if self.label_type == "binary"
            else None
        )
        return {
            "dataset": self.id,
            "name": self.name,
            "task": self.task,
            "n_items": len(self.items),
            "label_type": self.label_type,
            "n_positive": positives,
            "source": self.source_url,
            "citation": self.citation,
            "license": self.license,
            "notes": self.notes,
            **self.extra,
        }


# --------------------------------------------------------------------------- #
# ProteinGym
# --------------------------------------------------------------------------- #
def _proteingym_index() -> List[Dict[str, str]]:
    return _read_delimited(_fetch(_PG_REFERENCE, "proteingym_reference.csv"), ",")


def _proteingym_files() -> List[str]:
    """Filenames actually present in the substitutions directory.

    Listing the *subdirectory* rather than the repository root matters: the
    root also holds reference CSVs whose paths have no directory component,
    and the HuggingFace tree endpoint pages at 1000 entries, so the limit is
    raised to cover all 217 assays in one request.
    """
    payload = _fetch(
        _HF_TREE + "/ProteinGym_substitutions?limit=1000", "proteingym_tree.json"
    )
    entries = json.loads(payload.decode("utf-8"))
    return [
        e["path"].rsplit("/", 1)[-1]
        for e in entries
        if e.get("type") == "file" and e.get("path", "").endswith(".csv")
    ]


def load_proteingym(
    assay: Optional[str] = None, limit: int = 200, seed: int = 0, **_: Any
) -> Dataset:
    """One ProteinGym DMS assay as a variant-effect benchmark.

    ``assay`` matches a DMS id, a UniProt accession or a gene substring; the
    default is a small well-characterized human assay so that a first run is
    quick. Labels are ProteinGym's own ``DMS_score_bin`` (1 = functionally
    damaging) with the continuous ``DMS_score`` retained for rank metrics.

    The protein sequence comes from the reference index rather than from a
    database lookup, because the assay was performed on *that* construct --
    scoring a different isoform would silently misalign every position.
    """
    index = {row["DMS_id"]: row for row in _proteingym_index() if row.get("DMS_id")}
    available = _proteingym_files()

    wanted = (assay or "").strip().lower()
    chosen_id = None
    if wanted:
        for dms_id, row in index.items():
            haystack = " ".join(
                [
                    dms_id,
                    row.get("UniProt_ID", "") or "",
                    row.get("molecule_name", "") or "",
                    row.get("coarse_selection_type", "") or "",
                ]
            ).lower()
            if wanted in haystack:
                chosen_id = dms_id
                break
        if chosen_id is None:
            raise ValueError(
                f"No ProteinGym assay matches {assay!r}. Match on a UniProt entry "
                f"name (e.g. 'TADBP_HUMAN' -- the index keys on entry names, not "
                f"accessions), a DMS id, or a protein name. "
                f"{len(index)} assays are available."
            )
    else:
        chosen_id = _default_assay(index)

    row = index[chosen_id]
    filename = _match_file(chosen_id, row.get("DMS_filename", ""), available)
    if filename is None:
        raise ValueError(
            f"ProteinGym assay {chosen_id!r} is in the reference index but its data "
            "file is not in the HuggingFace repository."
        )

    payload = _fetch(
        f"{_HF_RESOLVE}/ProteinGym_substitutions/{filename}", f"pg_{filename}"
    )
    rows = _read_delimited(payload, ",")
    sequence = (row.get("target_seq") or "").strip().upper()
    entry_name = (row.get("UniProt_ID") or "").strip()
    identity = _resolve_entry_name(entry_name)
    uniprot = identity.get("accession")
    gene = identity.get("gene")

    items: List[Dict[str, Any]] = []
    for record in rows:
        mutant = (record.get("mutant") or "").strip()
        # Multi-mutant entries ("A1B:C2D") are a different prediction problem;
        # none of the registered single-substitution models can score them.
        if not mutant or ":" in mutant:
            continue
        parsed = re.match(r"^([A-Z])(\d+)([A-Z])$", mutant)
        if not parsed:
            continue
        ref_aa, position, alt_aa = (
            parsed.group(1),
            int(parsed.group(2)),
            parsed.group(3),
        )
        try:
            label = int(float(record.get("DMS_score_bin", "")))
        except (TypeError, ValueError):
            continue
        items.append(
            {
                "id": f"{chosen_id}:{mutant}",
                "sequence": sequence,
                "position": position,
                "mutant": alt_aa,
                "wild_type": ref_aa,
                "uniprot": uniprot,
                "gene": gene,
                "protein_change": mutant,
                # ProteinGym's bin is 1 for *functional* in some assays and for
                # *damaging* in others; it is normalized upstream so that 1
                # always means the fitness-reducing direction.
                "label": 1 - label,
                # Negated on purpose. ProteinGym orients DMS_score so that
                # higher = fitter, while every model here scores higher =
                # more damaging, so correlating them directly yields a
                # *negative* Spearman for a good model -- which reads as
                # failure on a leaderboard sorted descending. Flipping the
                # target here puts it in the same direction as `label`
                # (1 = damaging) so that, for both metrics and for every
                # backend, larger is better.
                "continuous_label": _negate(_as_float(record.get("DMS_score"))),
            }
        )

    items = _subsample(items, limit, seed)
    return Dataset(
        id="proteingym_dms",
        name=f"ProteinGym DMS: {chosen_id}",
        task="variant_effect",
        items=items,
        label_type="binary",
        source_url=f"{_HF_PROTEINGYM} ({filename})",
        citation="Notin et al., ProteinGym, NeurIPS 2023",
        license="MIT (ProteinGym)",
        notes=(
            f"Experimental deep-mutational-scanning labels for {gene or entry_name}. "
            "Label 1 = fitness-reducing, and the continuous target is the negated "
            "DMS score so that higher means more damaging for both. No registered "
            "backend is trained on these measurements, so this dataset carries no "
            "known leakage risk -- unlike clinvar_missense."
        ),
        extra={
            "assay": chosen_id,
            "uniprot": uniprot,
            "uniprot_entry_name": entry_name,
            "gene": gene,
            "organism": row.get("source_organism"),
            "selection_assay": row.get("selection_assay"),
            "sequence_length": len(sequence),
            "n_assays_available": len(index),
        },
    )


# Preferred default assays, best first. All are human loss-of-function readouts
# with *manual* (biologically motivated) binarization rather than a median
# split, and all are standard references in the variant-effect literature.
#
# The default matters more than it looks. Picking by size alone landed on
# TADBP_HUMAN_Bolognesi_2019 -- a TDP-43 aggregation-toxicity assay binarized
# at its own median. Every predictor here is trained to recognize loss of
# function, not gain-of-function aggregation, so they all scored near chance
# (AUROC 0.40-0.68) and a first run looked like the pipeline was broken when it
# was in fact reporting a genuine, known limitation of the models on that
# phenotype. A default should exercise the system, not sandbag it.
_PREFERRED_ASSAYS = (
    "P53_HUMAN_Kotler_2018",
    "BRCA1_HUMAN_Findlay_2018",
    "NUD15_HUMAN_Suiter_2020",
    "TPMT_HUMAN_Matreyek_2018",
    "SUMO1_HUMAN_Weile_2017",
)


def _default_assay(index: Dict[str, Dict[str, str]]) -> str:
    for candidate in _PREFERRED_ASSAYS:
        if candidate in index:
            return candidate
    manual = [
        (dms_id, row)
        for dms_id, row in index.items()
        if (row.get("taxon") or "").strip().lower() == "human"
        and (row.get("DMS_binarization_method") or "").strip().lower() == "manual"
        and (row.get("DMS_number_single_mutants") or "0").isdigit()
        and 200 <= int(row["DMS_number_single_mutants"]) <= 4000
    ]
    if manual:
        manual.sort(key=lambda kv: int(kv[1]["DMS_number_single_mutants"]))
        return manual[len(manual) // 2][0]
    return next(iter(index))


_UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"


def _resolve_entry_name(entry_name: str) -> Dict[str, Optional[str]]:
    """UniProt entry name -> accession and gene symbol.

    ProteinGym's reference file keys on the entry name (``TADBP_HUMAN``), but
    every non-sequence backend needs an accession (``Q13148``) or a gene
    symbol. Without this the benchmark could only ever exercise the
    sequence-based models, which is one backend out of fourteen -- and the
    whole point is to compare them against each other.
    """
    if not entry_name or "_" not in entry_name:
        return {"accession": entry_name or None, "gene": None}

    cache_file = cache_dir() / "uniprot_entry_names.json"
    try:
        known = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    except (ValueError, OSError):
        known = {}
    if entry_name in known:
        return known[entry_name]

    resolved: Dict[str, Optional[str]] = {"accession": None, "gene": None}
    try:
        import requests

        response = requests.get(
            _UNIPROT_SEARCH,
            params={
                "query": f"id:{entry_name}",
                "fields": "accession,id,gene_primary",
                "format": "json",
                "size": "1",
            },
            timeout=60,
            headers={"User-Agent": "ToolUniverse/benchmark"},
        )
        response.raise_for_status()
        results = response.json().get("results") or []
        if results:
            resolved["accession"] = results[0].get("primaryAccession")
            genes = results[0].get("genes") or []
            if genes:
                resolved["gene"] = (genes[0].get("geneName") or {}).get("value")
    except Exception:
        # A failed lookup costs the coordinate-keyed backends on this assay but
        # must not abort the run; the sequence-based models still work.
        pass

    known[entry_name] = resolved
    try:
        cache_file.write_text(json.dumps(known))
    except OSError:
        pass
    return resolved


def _match_file(dms_id: str, declared: str, available: List[str]) -> Optional[str]:
    """Reconcile the reference index's filename with what the repo actually has.

    The two disagree in practice -- the index lists
    ``A0A140D2T1_ZIKV_Sourisseau_2019.csv`` while the repository holds
    ``A0A140D2T1_ZIKV_Sourisseau_growth_2019.csv`` -- so an exact-name fetch
    404s. Fall back to matching on the stable leading tokens.
    """
    if declared in available:
        return declared
    if f"{dms_id}.csv" in available:
        return f"{dms_id}.csv"
    prefix = "_".join(dms_id.split("_")[:2])
    matches = [f for f in available if f.startswith(prefix)]
    return matches[0] if matches else None


# --------------------------------------------------------------------------- #
# TDC ADMET
# --------------------------------------------------------------------------- #
def load_tdc_admet(
    property: str = "bbb_martins", limit: int = 200, seed: int = 0, **_: Any
) -> Dataset:
    """One Therapeutics Data Commons ADMET dataset.

    The Dataverse file id is looked up by name at run time rather than
    hard-coded. That matters: a hand-recorded id silently resolves to a
    *different* dataset if it is wrong, and the benchmark would then report
    confident numbers against the wrong labels.
    """
    import requests

    prop = property.strip().lower()
    response = requests.get(
        _DATAVERSE_SEARCH,
        params={"q": prop, "type": "file", "per_page": "20"},
        timeout=90,
        headers={"User-Agent": "ToolUniverse/benchmark"},
    )
    response.raise_for_status()
    items = (response.json().get("data") or {}).get("items") or []
    match = None
    for item in items:
        if item.get("dataset_persistent_id") != _TDC_DOI:
            continue
        if Path(item.get("name", "")).stem.lower() == prop:
            match = item
            break
    if match is None:
        raise ValueError(
            f"No Therapeutics Data Commons file named {prop!r} under {_TDC_DOI}. "
            "Use the canonical TDC dataset name, e.g. 'bbb_martins', 'caco2_wang', "
            "'herg', 'ames', 'ld50_zhu', 'solubility_aqsoldb'."
        )

    file_id = match["file_id"]
    payload = _fetch(_DATAVERSE_FILE + str(file_id), f"tdc_{prop}.tab")
    rows = _read_delimited(payload, "\t")

    values = [_as_float(r.get("Y")) for r in rows]
    numeric = [v for v in values if v is not None]
    # TDC ships both classification and regression sets in the same format;
    # infer which from the labels rather than maintaining a second table.
    binary = bool(numeric) and set(numeric) <= {0.0, 1.0}

    items_out = [
        {
            "id": row.get("Drug_ID") or f"{prop}:{i}",
            "smiles": row.get("Drug"),
            "property": prop,
            "label": int(value) if binary else value,
        }
        for i, (row, value) in enumerate(zip(rows, values))
        if row.get("Drug") and value is not None
    ]

    items_out = _subsample(items_out, limit, seed)
    return Dataset(
        id="tdc_admet",
        name=f"TDC ADMET: {prop}",
        task="molecular_property",
        items=items_out,
        label_type="binary" if binary else "continuous",
        source_url=f"https://dataverse.harvard.edu/api/access/datafile/{file_id}",
        citation="Huang et al., Therapeutics Data Commons, NeurIPS 2021 (doi:10.7910/DVN/21LKWG)",
        license="CC0 (Harvard Dataverse)",
        notes=(
            f"The TDC leaderboard set for {prop}. ADMET-AI is trained on TDC data, so "
            "its scores here reflect in-distribution performance and are not "
            "comparable to a held-out evaluation; the runner flags this."
        ),
        extra={
            "property": prop,
            "dataverse_file_id": file_id,
            "n_rows_total": len(rows),
        },
    )


# --------------------------------------------------------------------------- #
# ClinVar
# --------------------------------------------------------------------------- #
def load_clinvar_missense(
    limit: int = 100,
    seed: int = 0,
    caller: Optional[Callable] = None,
    gene: Optional[str] = None,
    **_: Any,
) -> Dataset:
    """Pathogenic and benign missense variants, assembled live via MyVariant.

    Built through ToolUniverse's own tools instead of the 400 MB ClinVar bulk
    release, so it works without a large download. Classes are drawn in equal
    numbers: ClinVar is heavily skewed, and an unbalanced draw would let a
    model that always answers "benign" post a high accuracy.
    """
    if caller is None:
        raise ValueError(
            "load_clinvar_missense needs a tool caller; run it via the benchmark tool."
        )

    per_class = max(1, limit // 2)
    items: List[Dict[str, Any]] = []
    for significance, label in (("Pathogenic", 1), ("Benign", 0)):
        query = f'clinvar.rcv.clinical_significance:"{significance}" AND snpeff.ann.effect:missense_variant'
        if gene:
            query += f' AND clinvar.gene.symbol:"{gene}"'
        payload = caller(
            "MyVariant_query_variants",
            {
                "query": query,
                "size": per_class,
                "assembly": "hg38",
                "fields": "_id,chrom,vcf,clinvar.gene.symbol,clinvar.rcv.clinical_significance",
            },
        )
        for hit in _hits(payload):
            vcf = hit.get("vcf") or {}
            chrom = hit.get("chrom") or _chrom_from_id(hit.get("_id"))
            if not (
                chrom and vcf.get("position") and vcf.get("ref") and vcf.get("alt")
            ):
                continue
            items.append(
                {
                    "id": hit.get("_id"),
                    "chrom": str(chrom),
                    "pos": int(vcf["position"]),
                    "ref": vcf["ref"],
                    "alt": vcf["alt"],
                    "assembly": "GRCh38",
                    "label": label,
                }
            )

    items = _subsample(items, limit, seed)
    return Dataset(
        id="clinvar_missense",
        name="ClinVar missense (pathogenic vs benign)",
        task="variant_effect",
        items=items,
        label_type="binary",
        source_url="https://myvariant.info (ClinVar submissions)",
        citation="Landrum et al., ClinVar, NAR 2018",
        license="Public domain (NCBI ClinVar)",
        notes=(
            "Convenient and current, but several backends were trained on or "
            "directly consult ClinVar. Results for those models measure recall of "
            "the answer key, not prediction. Use proteingym_dms for a clean "
            "comparison; the runner reports which backends are affected."
        ),
        extra={"balanced": True},
    )


def _hits(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("data", "hits", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [v for v in value if isinstance(v, dict)]
            if isinstance(value, dict):
                return _hits(value)
    if isinstance(payload, list):
        return [v for v in payload if isinstance(v, dict)]
    return []


def _chrom_from_id(variant_id: Any) -> Optional[str]:
    match = re.match(r"^chr([\dXYMT]+):", str(variant_id or ""))
    return match.group(1) if match else None


# --------------------------------------------------------------------------- #
# Local files
# --------------------------------------------------------------------------- #
def load_file(
    path: str = "", task: str = "", label_field: str = "label", limit: int = 0, **_: Any
) -> Dataset:
    """A local CSV, TSV or JSONL evaluation set.

    Each row supplies the same fields the task's ``predict``/``compare`` tools
    accept, plus a label column. Nothing is uploaded anywhere.
    """
    if not path:
        raise ValueError("load_file needs 'path'.")
    source = Path(path).expanduser()
    if not source.exists():
        raise ValueError(f"No such dataset file: {source}")

    if source.suffix.lower() in (".jsonl", ".ndjson"):
        rows = [
            json.loads(line) for line in source.read_text().splitlines() if line.strip()
        ]
    elif source.suffix.lower() == ".json":
        loaded = json.loads(source.read_text())
        rows = loaded if isinstance(loaded, list) else loaded.get("items", [])
    else:
        rows = _read_delimited(source.read_bytes())

    items = []
    for i, row in enumerate(rows):
        if label_field not in row:
            continue
        item = dict(row)
        item.setdefault("id", f"{source.stem}:{i}")
        item["label"] = _as_float(row[label_field])
        items.append(item)
    if not items:
        raise ValueError(
            f"No rows in {source} carried a '{label_field}' column. Columns seen: "
            f"{sorted(rows[0].keys()) if rows else 'none'}"
        )

    values = {item["label"] for item in items}
    binary = values <= {0.0, 1.0}
    if binary:
        for item in items:
            item["label"] = int(item["label"])

    return Dataset(
        id="file",
        name=f"Local dataset: {source.name}",
        task=task or "unknown",
        items=_subsample(items, limit, 0),
        label_type="binary" if binary else "continuous",
        source_url=str(source),
        notes="User-supplied evaluation set.",
    )


# --------------------------------------------------------------------------- #
LOADERS: Dict[str, Callable[..., Dataset]] = {
    "proteingym_dms": load_proteingym,
    "tdc_admet": load_tdc_admet,
    "clinvar_missense": load_clinvar_missense,
    "file": load_file,
}

# Public datasets whose loaders are not implemented. Listed rather than hidden:
# a user asking "what can I benchmark docking on" deserves the pointer even
# when the pipeline cannot yet drive it end to end.
DOCUMENTED_ONLY: Dict[str, Dict[str, str]] = {
    "posebusters": {
        "task": "binding_affinity",
        "name": "PoseBusters benchmark set (428 protein-ligand complexes)",
        "url": "https://zenodo.org/records/8278563",
        "citation": "Buttenschoen et al., Chem Sci 2024",
        "status": (
            "Not implemented. Needs receptor PDB and ligand SDF handling, and every "
            "registered docking backend requires NVIDIA_API_KEY, so a loader could "
            "not be verified end to end. Use dataset='file' with your own pose set."
        ),
    },
    "pdbbind_core": {
        "task": "binding_affinity",
        "name": "PDBbind core set / CASF-2016 scoring benchmark",
        "url": "http://www.pdbbind.org.cn",
        "citation": "Su et al., J Chem Inf Model 2019",
        "status": "Not implemented: PDBbind requires registration, so it cannot be fetched unattended.",
    },
    "cameo_targets": {
        "task": "structure_prediction",
        "name": "CAMEO weekly structure-prediction targets",
        "url": "https://www.cameo3d.org",
        "citation": "Robin et al., Proteins 2021",
        "status": (
            "Not implemented. Scoring folds needs structural superposition (TM-score "
            "/ GDT-TS) against the reference, which no registered tool provides; the "
            "structure task currently reports self-assessed pLDDT only."
        ),
    },
}


def load(name: str, **kwargs: Any) -> Dataset:
    loader = LOADERS.get(name)
    if loader is None:
        if name in DOCUMENTED_ONLY:
            info = DOCUMENTED_ONLY[name]
            raise ValueError(
                f"Dataset {name!r} ({info['name']}) is documented but has no loader. "
                f"{info['status']} See {info['url']}."
            )
        raise ValueError(
            f"Unknown dataset {name!r}. Available: {sorted(LOADERS)}. "
            f"Documented without a loader: {sorted(DOCUMENTED_ONLY)}."
        )
    return loader(**kwargs)


def catalogue() -> Dict[str, Any]:
    return {
        "loadable": {
            "proteingym_dms": {
                "task": "variant_effect",
                "name": "ProteinGym DMS substitution assays (87 assays in the mirrored release)",
                "labels": "experimental fitness (binary + continuous)",
                "url": _HF_PROTEINGYM,
                "citation": "Notin et al., NeurIPS 2023",
                "options": {
                    "assay": "UniProt entry name (e.g. TADBP_HUMAN), DMS id, or protein name",
                    "limit": "int",
                },
                "leakage_risk": "none known",
            },
            "clinvar_missense": {
                "task": "variant_effect",
                "name": "ClinVar pathogenic vs benign missense (balanced, live)",
                "labels": "clinical classification (binary)",
                "url": "https://www.ncbi.nlm.nih.gov/clinvar/",
                "citation": "Landrum et al., NAR 2018",
                "options": {"limit": "int", "gene": "optional gene symbol"},
                "leakage_risk": sorted(LEAKAGE_RISK["clinvar_missense"]),
            },
            "tdc_admet": {
                "task": "molecular_property",
                "name": "Therapeutics Data Commons ADMET datasets",
                "labels": "experimental ADMET measurements (binary or continuous)",
                "url": "https://tdcommons.ai/single_pred_tasks/adme/",
                "citation": "Huang et al., NeurIPS 2021",
                "options": {
                    "property": "TDC dataset name e.g. bbb_martins",
                    "limit": "int",
                },
                "leakage_risk": ["admet_ai (trained on TDC)"],
            },
            "file": {
                "task": "any",
                "name": "Local CSV/TSV/JSONL",
                "options": {"path": "str", "label_field": "str", "task": "str"},
            },
        },
        "documented_only": DOCUMENTED_ONLY,
        "cache_dir": str(cache_dir()),
    }


def _subsample(
    items: List[Dict[str, Any]], limit: int, seed: int
) -> List[Dict[str, Any]]:
    """Take a reproducible random sample, not the first N rows.

    Benchmark files are frequently sorted -- by position, by score, by class --
    so a head-of-file slice is a biased sample that can look dramatically
    better or worse than the real thing.
    """
    if not limit or limit <= 0 or len(items) <= limit:
        return items
    rng = random.Random(seed)
    return rng.sample(items, limit)


def _negate(value: Optional[float]) -> Optional[float]:
    return None if value is None else -value


def _as_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if result != result else result
