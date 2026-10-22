"""AlphaProtein Novo resident worker: holds the generator, serves a socket.

Runs in the MODEL's environment (jax 0.10.2, alphafold3, alphaprotein_novo) and
imports nothing from ToolUniverse: `worker_base.py` is loaded by path, and that
module loads `protocol.py` the same way.

WHAT RESIDENCY BUYS HERE, measured on an NVIDIA GB10 with upstream's own
2-design 50-step test manifest (every design pads to one fixed shape):

    design 0 (cold, includes the XLA compile)          61.3 s
    design 1 (held)                                     1.06 s

Two things are held and neither survives a process exit: the Haiku parameters
read out of a 547 MB zstd record set -- upstream's own comment says parameter
loading dominates start-up, which is why `resolve_params` is hoisted here --
and the compiled diffusion trajectory, which upstream memoises per
(sampling_steps, partial_diffusion_steps) in a module-level `lru_cache` that
only a surviving process can collect.

READ THE RATIO WITH ITS STEP COUNT. That 58x is at 50 denoising steps, where
compilation dominates. The published campaigns run 1000, where real compute
does, so the multiple there is much smaller. A residency figure quoted without
its step count flatters itself.

HOW THE GENERATION STAGE IS DRIVEN, and what is deliberately not reproduced.
Upstream's entry point is a script, but unlike af2ig's it is importable: flags
are parsed only inside `main`, and every step of the work is a module-level
function. So this calls upstream's own `build_spec`,
`parse_and_prepare_diffusion_input`, `run_sampling` and `save_outputs` with the
held parameters, rather than re-implementing any of them. What is NOT
reproduced is `main`'s campaign bookkeeping -- the resume scan and the job
index -- because this worker gives every request its own run root, so there is
nothing to resume into.

That last point is not a preference, it is a defect this worker exists to
avoid: `design_manifest.metadata_dir` puts a stage's metadata at
`<run_root>/metadata`, i.e. BESIDE the stage directory rather than inside it.
Two campaigns whose output directories are siblings therefore share resume
state, and the second silently reports "0 generated, 2 skipped" having done
nothing. Measured, while establishing the budget below.

The evaluation stage runs as a SUBPROCESS, on purpose. It is CPU work with
nothing to hold between calls, so residency buys it nothing, and a subprocess
cannot drift from upstream's own argument handling.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SLUG = "apnovo"
GIB = 1024**3
# Upstream ships five reaction-specific suites; anything else is refused by
# `evaluate_design.py` itself, and this list only shapes the error message.
SUITES = (
    "kemp_eliminase",
    "serine_esterase",
    "dehp_esterase",
    "carbene_transfer",
    "nitrene_transfer",
)


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    `raise SystemExit("text")` prints the text and exits 1, which the standard
    reserves for "failed" -- a distinction a caller branches on.
    """
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def _load_worker_base():
    override = os.environ.get("TOOLUNIVERSE_REMOTE_WORKER_BASE")
    path = Path(override) if override else None
    if path is None or not path.is_file():
        raise _refuse(
            "TOOLUNIVERSE_REMOTE_WORKER_BASE must point at "
            "remote_resident/worker_base.py; this worker never imports "
            "tooluniverse"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _np():
    import numpy  # noqa: PLC0415 - the model's env, not ours

    return numpy


def _say(msg: str) -> None:
    print(f"[{SLUG}-resident] {msg}", flush=True)


def _lay_out(work: Path, manifest: dict, files: dict) -> Path:
    """Writes the manifest and its CIF inputs where upstream expects them.

    Relative `input_file` paths resolve against the manifest's own directory,
    so both land in the same place and the caller never names a path on this
    host.
    """
    for name, text in files.items():
        # The server already refused separators and dot-leading names; this is
        # the second check because the first is on the other side of a socket.
        if "/" in name or name.startswith("."):
            raise ValueError(f"refusing file name {name!r}")
        (work / name).write_text(text)
    path = work / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def _sampled_lengths(parsed_specs):
    """The residue count each parsed spec drew, which is what the fixed input
    shape is checked against (`create_designable_protein_features` compares
    `len(res_map.source_residue_ids)`)."""
    out = []
    for p in parsed_specs:
        res_map = getattr(p, "residue_map", None)
        out.append(None if res_map is None else len(res_map.source_residue_ids))
    return out


def _diffusion_input(gen, spec, seed, global_config):
    """Upstream's own conversion, with its one unactionable error reworded.

    `run_generator.parse_and_prepare_diffusion_input` passes `max_num_res=512`
    as a LITERAL -- not from config, not from the manifest -- so a design
    above that length is not more expensive, it is REFUSED, by
    `motif_spec.create_designable_protein_features`. Upstream's message is
    "Number of residues in motif_spec > 512. Set max_num_res to a higher
    value.", which names a knob reachable from neither a manifest, nor this
    worker, nor the published operation. A caller who followed it would go
    looking for a parameter that does not exist.

    The ceiling is deliberately NOT restated here as a constant of our own.
    Upstream owns the number and sets it in a function body, so a copy here
    would drift silently the first time the pin moves. What is ours is the
    advice.
    """
    try:
        return gen.parse_and_prepare_diffusion_input(
            spec=spec, seed=seed, global_config=global_config
        )
    except ValueError as exc:
        if "max_num_res" not in str(exc):
            raise
        raise ValueError(
            f"{exc} That ceiling is fixed in the model's input pipeline and is "
            f"not a budget this provider can raise: every design is padded to "
            f"one shape, which is also why the declared VRAM figure does not "
            f"move with design length. Shorten the design instead -- "
            f"`seq_length` and the gap ranges in `motif_str` together set the "
            f"sampled length. That length is sampled PER SEED (this was seed "
            f"{seed}), so a design near the ceiling fails intermittently "
            f"rather than every time; `apnovo_validate_motif` reports the "
            f"lengths it samples."
        ) from exc


class Engine:
    """Holds the generator parameters and upstream's compiled trajectory."""

    def __init__(self, args):
        self.repo = Path(args.repo)
        self.model_dir = Path(os.path.expanduser(args.model_dir))
        self.lmp_checkpoint = Path(os.path.expanduser(args.ligandmpnn_checkpoint)) if args.ligandmpnn_checkpoint else None
        self.lmp_dir = Path(os.path.expanduser(args.ligandmpnn_dir)) if args.ligandmpnn_dir else None
        self.lmp_python = Path(os.path.expanduser(args.ligandmpnn_python)) if args.ligandmpnn_python else None
        self.params = None
        self.build_s = None
        self.requests = 0
        self._gen = None
        self._manifest_mod = None

    # -- build ------------------------------------------------------------

    def build(self) -> None:
        started = time.time()
        if not self.repo.is_file() and not (self.repo / "run_generator.py").is_file():
            raise _refuse(
                f"--repo must be the alphaprotein-novo checkout holding "
                f"run_generator.py; {self.repo} does not. `tu remote setup "
                f"apnovo --only kit` lays it out."
            )
        if not self.model_dir.is_dir():
            raise _refuse(
                f"--model-dir {self.model_dir} does not exist. The generator "
                f"parameters are licensed for non-commercial use and are "
                f"fetched only after you accept their terms: see "
                f"`tu remote setup apnovo --only weights`."
            )
        # Upstream's entry points are scripts at the repository root, so the
        # checkout itself goes on the path. The installed package is already
        # importable; this is only for `run_generator`.
        sys.path.insert(0, str(self.repo))
        try:
            import run_generator  # noqa: PLC0415 - the model's env, not ours
            from alphaprotein_novo.data import design_manifest  # noqa: PLC0415
        except ImportError as exc:
            raise _refuse(
                f"the model environment cannot import upstream ({exc}). Run "
                f"`tu remote setup apnovo --only environment` and read its "
                f"refusal."
            ) from exc
        self._gen = run_generator
        self._manifest_mod = design_manifest

        # Upstream registers absl flags at module level and expects `app.run`
        # to parse them. A worker never calls `app.run`, so FLAGS stays
        # unparsed -- and the first `absl.logging` call from inside upstream's
        # own functions then makes absl parse OUR argv and die on
        # `UnrecognizedFlagError: Unknown command line flag 'socket'`, after
        # the model has already been built. Marking them parsed is safe here
        # because run_generator marks no flag as required and the worker reads
        # none of their values: everything this provider varies arrives in the
        # request, not on a command line.
        from absl import flags as absl_flags  # noqa: PLC0415

        if not absl_flags.FLAGS.is_parsed():
            absl_flags.FLAGS.mark_as_parsed()
        from alphaprotein_novo.data import unindexed_motif  # noqa: PLC0415
        from alphaprotein_novo.model import config as apn_config  # noqa: PLC0415

        self._unindexed = unindexed_motif
        # Upstream's `main` reads this once and threads it through every
        # design; it carries the vocabulary and the length bounds that
        # `parse_and_prepare_diffusion_input` needs, and there is no default.
        self._global_config = apn_config.get_global_config()

        import jax  # noqa: PLC0415

        if jax.default_backend() != "gpu":
            raise _refuse(
                f"jax.default_backend() is {jax.default_backend()!r}, not "
                f"'gpu'. This provider holds its model on the card; CPU is "
                f"not a target. Check the driver: sm_121 is only enumerated "
                f"by the 580 series."
            )
        # The expensive half, hoisted out of every request. Upstream's own
        # comment: "Parameter loading dominates startup cost".
        self.params = run_generator.resolve_params(self.model_dir)
        self.build_s = round(time.time() - started, 1)
        _say(f"built in {self.build_s}s; parameters held from {self.model_dir}")

    # -- reporting --------------------------------------------------------

    @property
    def compute_capability(self) -> str:
        import jax  # noqa: PLC0415

        try:
            return str(jax.devices()[0].compute_capability)
        except Exception:  # noqa: BLE001 - a missing figure is not a failure
            return "unknown"

    def memory(self) -> dict:
        """Peak device memory, JAX's way.

        `nvidia-smi` reports `[N/A]` for memory.used on this unified-memory
        part, so a figure from there is not available at all. Of JAX's own
        fields, `peak_pool_bytes` is the analogue of torch's *reserved* and is
        what the budget is declared on; the field actually named
        `peak_bytes_reserved` means something else in XLA and reads 0 here.
        """
        import jax  # noqa: PLC0415

        out: dict = {}
        try:
            stats = jax.devices()[0].memory_stats() or {}
        except Exception:  # noqa: BLE001
            return out
        if stats.get("peak_pool_bytes") is not None:
            out["peak_reserved_gib"] = round(stats["peak_pool_bytes"] / GIB, 2)
        if stats.get("peak_bytes_in_use") is not None:
            out["peak_bytes_in_use"] = stats["peak_bytes_in_use"]
        if stats.get("bytes_limit") is not None:
            out["bytes_limit"] = stats["bytes_limit"]
        return out

    # -- dispatch ---------------------------------------------------------

    def predict(self, req: dict) -> dict:
        """The socket defines one model op; this provider's three ride on it."""
        task = req.get("task")
        if task is None and "input" in req:
            # `tu remote setup --only smoke` sends a neutral envelope -- the
            # smoke file's TEXT as `input`, plus `out_dir`, `name` and `seed`
            # -- and leaves the meaning to the provider. The main operation is
            # generation, so that is what an unlabelled request means here.
            payload = req["input"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            merged = {**payload, **{k: v for k, v in req.items() if k != "input"}}
            merged["task"] = "generate"
            if req.get("out_dir"):
                merged["out_dir"] = req["out_dir"]
            return self._generate(merged)
        if task == "validate_motif":
            return self._validate(req)
        if task == "generate":
            return self._generate(req)
        if task == "resequence":
            return self._resequence(req)
        if task == "ingest_folded":
            return self._ingest_folded(req)
        if task == "evaluate":
            return self._evaluate(req)
        raise ValueError(
            f"unknown task {task!r}; this worker serves validate_motif, "
            f"generate, resequence, ingest_folded and evaluate"
        )

    # -- tasks ------------------------------------------------------------

    def _validate(self, req: dict) -> dict:
        """Parse the manifest and every design's motif spec. No card touched."""
        with tempfile.TemporaryDirectory(prefix="apnovo-validate-") as tmp:
            path = _lay_out(Path(tmp), req["manifest"], req.get("files") or {})
            manifest = self._manifest_mod.Manifest.from_file(path)
            designs = []
            for job in manifest.designs:
                spec = self._gen.build_spec(job)
                # Segment lengths are sampled per seed, so a spec that parses
                # at one seed is not proof for every seed; check a few.
                parsed = [spec.parsed(seed=s) for s in (0, 1, 2)]
                designs.append(
                    {
                        "name": job.name,
                        "motif_str": job.motif_str,
                        "motif_atoms": job.motif_atoms or None,
                        "seq_length": job.seq_length,
                        # The DECLARED constraint above is a string the caller
                        # wrote; these are the lengths actually sampled at the
                        # probe seeds, which is the number the model's fixed
                        # input shape is checked against. A design whose
                        # sampled length exceeds that shape is refused rather
                        # than run more slowly, and because the length is
                        # sampled per seed a design near the ceiling fails on
                        # some seeds and not others.
                        "sampled_design_lengths": _sampled_lengths(parsed),
                        "num_designs": job.num_designs,
                        "num_sampling_steps": job.num_sampling_steps,
                        "is_author_naming": job.is_author_naming,
                        "indexed_conditioning": not parsed[0].is_unindexed,
                        "partial_diffusion": parsed[0].is_partial_diffusion,
                        "parsed_at_seeds": [0, 1, 2],
                    }
                )
        return {
            "status": "ok",
            "designs": designs,
            "folding_states": [s["name"] for s in (manifest.folding.states or ())],
            "evaluation_suite": manifest.evaluation.suite,
            "note": (
                "A spec that parses is not a spec that scaffolds: segment "
                "lengths are sampled per design, and only generation shows "
                "whether the motif is satisfiable at the sampled lengths. "
                "`sampled_design_lengths` is what each probe seed drew; the "
                "model pads every design to one fixed shape and refuses a "
                "design above it, so a spec whose lengths vary across those "
                "seeds will behave inconsistently near the ceiling."
            ),
        }

    def _generate(self, req: dict) -> dict:
        """Run the generation stage with the held parameters.

        The upstream calls below mirror `run_generator.main`'s own loop rather
        than paraphrasing it -- including the detail that `spec` is passed
        whole and re-parsed per design inside
        `parse_and_prepare_diffusion_input`, which is what resamples the linker
        lengths, and that `validate_output` and `save_outputs` take the
        `initial_dinput` that `run_sampling` RETURNS and not the one it was
        given.
        """
        overrides = req.get("overrides") or {}
        # Its own run root, never a sibling of another campaign's: see the
        # module docstring on `<run_root>/metadata`.
        if req.get("out_dir"):
            run_root = Path(req["out_dir"])
            run_root.mkdir(parents=True, exist_ok=True)
        else:
            run_root = Path(tempfile.mkdtemp(prefix="apnovo-run-"))
        stage = run_root / "01_generation"
        stage.mkdir(parents=True, exist_ok=True)
        # The laid-out inputs go OUTSIDE the run root, and that placement is
        # load-bearing. `[runtime] outputs` is matched with fnmatch against
        # BASENAMES over a recursive walk of the run root, so an input motif
        # left at `run_root/inputs/foo.cif` is matched by `*.cif` -- and it is
        # written before any sampling happens. A generation that died after the
        # lay-out would then still satisfy the outputs assertion on the
        # strength of its own input. Measured: the first green smoke listed
        # `apnovo-smoke/inputs/set1_tsa_top20_E_S_X_tsa-310.cif` among its
        # matched outputs.
        inputs_tmp = tempfile.mkdtemp(prefix="apnovo-inputs-")
        inputs = Path(inputs_tmp)

        manifest_doc = dict(req["manifest"])
        if overrides:
            defaults = dict(manifest_doc.get("defaults") or {})
            defaults.update(overrides)
            manifest_doc["defaults"] = defaults
        path = _lay_out(inputs, manifest_doc, req.get("files") or {})

        started = time.time()
        manifest = self._manifest_mod.Manifest.from_file(path)
        folding_states = manifest.folding.state_specs()
        per_design_s: list = []
        for job in manifest.designs:
            spec = self._gen.build_spec(job)
            partial_steps = job.partial_diffusion_num_steps
            for design in self._manifest_mod.expand_designs(job):
                t0 = time.time()
                dinput = _diffusion_input(
                    self._gen, spec, design.seed, self._global_config
                )
                output, initial_dinput, aux = self._gen.run_sampling(
                    dinput=dinput,
                    model_dir=self.model_dir,
                    sampling_steps=job.num_sampling_steps,
                    seed=design.seed,
                    return_all_data=False,
                    num_partial_diffusion_steps=partial_steps,
                    params=self.params,
                )
                unindexed_result = None
                if spec.is_unindexed:
                    # Under unindexed conditioning the motif is located after
                    # the fact by geometric matching, and skipping this step
                    # would save a structure whose motif residues are unlabelled.
                    logits = (
                        output.predicted_motif_indices_mask_logits
                        if output.predicted_motif_indices_mask_logits is not None
                        else None
                    )
                    unindexed_result = (
                        self._unindexed.prepare_unindexed_motif_sample(
                            sampled_struct=output.protein.to_structure(),
                            spec=spec,
                            unindexed_motif_data=initial_dinput,
                            predicted_motif_indices_mask_logits=(
                                None if logits is None else _np().asarray(logits)
                            ),
                        )
                    )
                self._gen.validate_output(
                    output=output, dinput=initial_dinput, aux=aux
                )
                self._gen.save_outputs(
                    output=output,
                    dinput=initial_dinput,
                    spec=spec,
                    seed=design.seed,
                    output_dir=stage,
                    unindexed_result=unindexed_result,
                    output_prefix=design.prefix,
                    design_num=design.design_num,
                    num_partial_diffusion_steps=partial_steps,
                    num_sampling_steps=job.num_sampling_steps,
                    model_dir=self.model_dir,
                    folding_states=folding_states,
                )
                per_design_s.append(round(time.time() - t0, 2))
        self.requests += 1

        shutil.rmtree(inputs_tmp, ignore_errors=True)
        designs = self._collect(stage, req.get("return_designs"),
                                req.get("max_returned") or 32)
        # Reported as well as walked: the outputs assertion matches both, and a
        # provider that lists what it wrote is cheaper to debug than one that
        # makes the caller go looking.
        files = [os.fspath(q) for q in sorted(run_root.rglob("*")) if q.is_file()]
        body = {
            "status": "ok",
            "run_dir": str(run_root),
            "n_designs": len(designs),
            "designs": designs,
            "files": files,
            "timing": {
                "total_s": round(time.time() - started, 1),
                "per_design_s": per_design_s,
            },
            "weights_held_by": "worker",
            "output_terms_of_use": (
                "These structures and sequences are AP Novo Output, subject to "
                "the AP Novo Generator Output Terms of Use at "
                "https://github.com/google-deepmind/alphaprotein-novo/blob/main/"
                "OUTPUT_TERMS_OF_USE.md. The mmCIF text carries upstream's own "
                "notice; keep it if you redistribute, and cite "
                "doi 10.64898/2026.10.01.756017."
            ),
        }
        body.update(self.memory())
        return body

    def _collect(self, stage: Path, inline: bool, cap: int) -> list:
        """One row per design that actually landed."""
        out = []
        # The metadata JSON is written last, after every structure save, so it
        # is the file that witnesses a design rather than one written on the
        # way to failing.
        meta_dir = self._manifest_mod.metadata_dir(stage)
        for meta_path in sorted(Path(meta_dir).glob("*_metadata.json")):
            prefix = meta_path.name[: -len("_metadata.json")]
            row = {"name": prefix}
            fasta = stage / f"{prefix}.fa"
            if fasta.is_file():
                lines = fasta.read_text().splitlines()
                row["sequence"] = "".join(
                    ln.strip() for ln in lines if not ln.startswith(">")
                )
            if inline and len(out) < cap:
                cif = stage / f"{prefix}.cif"
                if cif.is_file():
                    row["cif"] = cif.read_text()
            out.append(row)
        return out

    def _can_resequence(self) -> bool:
        """Whether the three per-machine pieces the stage needs are present."""
        return bool(
            self.lmp_dir
            and (self.lmp_dir / "run.py").is_file()
            and self.lmp_python
            and self.lmp_python.is_file()
            and self.lmp_checkpoint
            and self.lmp_checkpoint.is_file()
        )

    def _resequence(self, req: dict) -> dict:
        """LigandMPNN over a campaign's generated backbones.

        A subprocess, and a THIRD interpreter: LigandMPNN pins torch 2.2.1 and
        CUDA 12.1 wheels, which this environment's jax stack cannot host. It
        runs on the CPU because torch below 2.7 drives no sm_121 part at all --
        see provider.toml for the measurement. Nothing here competes with the
        generator for the card.
        """
        if not self._can_resequence():
            missing = []
            if not (self.lmp_dir and (self.lmp_dir / "run.py").is_file()):
                missing.append(
                    "LIGANDMPNN_DIR must name the LigandMPNN checkout holding "
                    "run.py (git clone https://github.com/dauparas/LigandMPNN)"
                )
            if not (self.lmp_python and self.lmp_python.is_file()):
                missing.append(
                    "TOOLUNIVERSE_LIGANDMPNN_PYTHON must name a Python 3.11 "
                    "interpreter carrying LigandMPNN's own pins; it must be a "
                    "CPU-only torch build, because LigandMPNN picks its device "
                    "with torch.cuda.is_available() and a CUDA build would make "
                    "it choose a card whose kernels it does not ship"
                )
            if not (self.lmp_checkpoint and self.lmp_checkpoint.is_file()):
                missing.append(
                    f"the checkpoint is not at {self.lmp_checkpoint} -- run "
                    f"`tu remote setup apnovo --only weights`"
                )
            raise ValueError(
                "resequencing is not configured on this host: "
                + "; ".join(missing)
            )

        run_dir = Path(req["run_dir"])
        stage_in = run_dir / "01_generation"
        if not stage_in.is_dir():
            raise ValueError(
                f"{run_dir} is not a campaign directory: it has no "
                f"01_generation stage"
            )
        stage_out = run_dir / "02_resequence"

        temperature = req.get("temperature", 0.1)
        num_sequences = req.get("num_sequences", 1)
        argv = [
            sys.executable,
            str(self.repo / "run_ligandmpnn.py"),
            f"--input_dir={stage_in}",
            f"--output_dir={stage_out}",
            f"--ligandmpnn_dir={self.lmp_dir}",
            f"--checkpoint={self.lmp_checkpoint}",
            f"--python_executable={self.lmp_python}",
            f"--temperature={float(temperature)}",
            f"--num_sequences={int(num_sequences)}",
            "--noresume",
        ]
        if req.get("model_type"):
            argv.append(f"--model_type={req['model_type']}")
        if req.get("use_side_chain_context") is not None:
            argv.append(
                f"--use_side_chain_context={1 if req['use_side_chain_context'] else 0}"
            )

        started = time.time()
        proc = subprocess.run(argv, capture_output=True, text=True, cwd=self.repo)
        if proc.returncode:
            raise RuntimeError(
                f"run_ligandmpnn.py exited {proc.returncode}: "
                f"{proc.stderr.strip()[-2000:]}"
            )

        # One row per resequenced design, and the confidences come from a
        # DIFFERENT file than the sequences. There are two FASTA formats here
        # and only one of them carries a score:
        #
        #   02_resequence/<design>_seqNN.fa   AP Novo's per-design file. Its
        #       header is the design name plus the AP Novo Output Terms of Use
        #       notice -- upstream puts it in the description field precisely so
        #       that FASTA readers still parse the record -- and NO confidences.
        #   02_resequence/seqs/<design>.fa    LigandMPNN's own file. Record 0 is
        #       the input row; records id=1..N are the samples, each carrying
        #       overall_confidence, ligand_confidence and seq_rec.
        #
        # So `_seq00` joins to `id=1`, `_seq01` to `id=2`, and reading the
        # scores off the first file silently yields None for every design --
        # which is how this was found.
        scores: dict = {}
        for src in sorted(stage_out.glob("seqs/*.fa")):
            design = src.stem
            for line in src.read_text().splitlines():
                if not line.startswith(">"):
                    continue
                fields = {}
                for part in line[1:].split(","):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        fields[k.strip()] = v.strip()
                if "id" not in fields:
                    continue  # record 0: the input row, not a sample
                row = {}
                for key in ("overall_confidence", "ligand_confidence", "seq_rec", "T"):
                    if key in fields:
                        try:
                            row[key] = float(fields[key])
                        except ValueError:
                            row[key] = fields[key]
                scores[(design, int(fields["id"]))] = row

        rows = []
        for fasta in sorted(stage_out.glob("*_seq*.fa")):
            seq = [
                ln.strip()
                for ln in fasta.read_text().splitlines()
                if not ln.startswith(">")
            ]
            name = fasta.stem
            row = {"name": name, "sequence": "".join(seq)}
            # `<design>_seqNN` -> (design, NN+1)
            design, _, index = name.rpartition("_seq")
            if index.isdigit():
                row.update(scores.get((design, int(index) + 1), {}))
            cif = stage_out / f"{name}_reseq.cif"
            if cif.is_file():
                row["resequenced_cif_path"] = str(cif)
            rows.append(row)
        if not rows:
            raise RuntimeError(
                f"run_ligandmpnn.py exited 0 but wrote no sequence under "
                f"{stage_out}; its last output was: "
                f"{(proc.stdout or proc.stderr).strip()[-800:]}"
            )
        return {
            "status": "ok",
            "run_dir": str(run_dir),
            "n_designs": len(rows),
            "designs": rows,
            "device": "cpu",
            "timing": {"total_s": round(time.time() - started, 1)},
            "note": (
                "Resequencing is the input to the paper's highest-value filter: "
                "hold the backbone, generate N sequences, and score the BACKBONE "
                "by how many of them pass your filter set (multi-resequence, MR "
                "-- worth x2.5 to x5.4 at 50% recall). One sequence per design "
                "is the default pipeline; MR needs 7 to 10."
            ),
        }

    # Upstream's own filename rules, read from
    # `alphaprotein_novo/data/design_manifest.py` at the pinned commit rather
    # than inferred from a directory listing:
    #   folded_state_paths() -> f"{sample}_{state}_folded_seed{n}.cif"
    #                           f"{sample}_{state}_confidences_seed{n}.json"
    #   find_state_confidences() counts seeds UP FROM 0 and STOPS at the first
    #   gap, so seeds must be contiguous from 0 or the tail is silently lost.
    #   metadata_dir(stage) is `stage.parent / "metadata"`, i.e. the run root's
    #   -- shared by every stage, which is why ingesting a folded stage needs
    #   no metadata of its own.
    FOLDED_STAGE = "03_folded"

    def _ingest_folded(self, req: dict) -> dict:
        """Lay externally predicted structures out as upstream's folded stage.

        This provider has no folding operation and will not get one while the
        AlphaFold 3 weights question is unsettled, but `evaluate_design.py`
        does not need THIS provider to have folded anything -- it needs a
        directory shaped like `run_alphafold.py` output. Any structure
        predictor that has settled its own weights question can produce the
        structures; this writes them where upstream looks.
        """
        run_dir = Path(req["run_dir"])
        if not run_dir.is_dir():
            raise ValueError(
                f"run_dir {run_dir} does not exist on this host; pass the "
                f"run_dir that apnovo_generate_designs returned"
            )
        if not (run_dir / "01_generation").is_dir():
            raise ValueError(
                f"{run_dir} is not a campaign directory: it has no "
                f"01_generation stage"
            )
        states = req.get("states")
        if not isinstance(states, list) or not states:
            raise ValueError(
                "'states' must be a non-empty list of folded states, each "
                "naming its design, its state and its seed"
            )

        stage = run_dir / self.FOLDED_STAGE
        stage.mkdir(parents=True, exist_ok=True)
        written: list = []
        designed_cifs: set = set()
        for i, entry in enumerate(states):
            if not isinstance(entry, dict):
                raise ValueError(f"states[{i}] must be an object")
            sample = entry.get("sample_name")
            state = entry.get("state")
            seed = entry.get("seed", 0)
            cif = entry.get("folded_cif")
            conf = entry.get("confidences")
            designed = entry.get("designed_cif")
            for label, value in (("sample_name", sample), ("state", state)):
                # These two become a filename, so they are checked the way
                # _lay_out checks a caller-supplied name: this is the second
                # check, the first being on the other side of a socket.
                if not isinstance(value, str) or not value:
                    raise ValueError(f"states[{i}].{label} must be a non-empty string")
                if "/" in value or value.startswith("."):
                    raise ValueError(f"refusing states[{i}].{label} {value!r}")
            if not isinstance(seed, int) or seed < 0:
                raise ValueError(f"states[{i}].seed must be an integer >= 0")
            if not isinstance(cif, str) or not cif.strip():
                raise ValueError(f"states[{i}].folded_cif must be mmCIF text")
            if conf is not None and not isinstance(conf, dict):
                raise ValueError(f"states[{i}].confidences must be an object")

            stem = f"{sample}_{state}"
            (stage / f"{stem}_folded_seed{seed}.cif").write_text(cif)
            # Whatever the predictor reported rides along: _load_confidences
            # turns every key it does not recognise into a prefixed metric, so
            # a sibling's pTM/ipTM/pLDDT reach the rows without a mapping here.
            # Only `seed` and `designed_cif` are load-bearing -- _load_metadata
            # reads exactly those two and nothing else from this file.
            payload = dict(conf or {})
            payload["seed"] = seed
            if designed:
                if "/" in designed or designed.startswith("."):
                    raise ValueError(f"refusing states[{i}].designed_cif {designed!r}")
                payload["designed_cif"] = designed
                designed_cifs.add(designed)
            (stage / f"{stem}_confidences_seed{seed}.json").write_text(
                json.dumps(payload)
            )
            written.append({"sample_name": sample, "state": state, "seed": seed})

        # `designed_cif` is resolved as `folded_dir / designed_cif`, so the
        # generated structure has to be reachable from the folded stage too.
        # It already exists one directory over; link rather than copy, and
        # fall back to copying where linking is refused.
        gen = run_dir / "01_generation"
        missing: list = []
        for name in sorted(designed_cifs):
            dst = stage / name
            if dst.exists():
                continue
            src = gen / name
            if not src.is_file():
                missing.append(name)
                continue
            try:
                os.link(src, dst)
            except OSError:
                shutil.copyfile(src, dst)

        # find_state_confidences() stops at the first missing seed index, so a
        # non-contiguous ingest loses its tail without saying so. Say so.
        gaps: list = []
        by_key: dict = {}
        for row in written:
            by_key.setdefault((row["sample_name"], row["state"]), []).append(row["seed"])
        for (sample, state), seeds in sorted(by_key.items()):
            got = sorted(set(seeds))
            # How far upstream actually gets: the contiguous run from 0.
            reach = 0
            while reach in got:
                reach += 1
            if reach != len(got):
                gaps.append(
                    f"{sample}/{state}: ingested seeds {got}, but upstream "
                    f"counts up from 0 and stops at the first gap, so it will "
                    f"read {list(range(reach))} and ignore the rest"
                )

        return {
            "status": "success",
            "folded_dir": str(stage),
            "n_states_written": len(written),
            "states": written,
            "designed_cifs_missing": missing,
            "seed_gaps": gaps,
        }

    def _evaluate(self, req: dict) -> dict:
        """Upstream's metrics, as a subprocess. CPU work, nothing to hold."""
        run_dir = Path(req["run_dir"])
        if not run_dir.is_dir():
            raise ValueError(
                f"run_dir {run_dir} does not exist on this host; pass the "
                f"run_dir that apnovo_generate_designs returned"
            )
        stage = run_dir / "01_generation"
        if not stage.is_dir():
            raise ValueError(
                f"{run_dir} is not a campaign directory: it has no "
                f"01_generation stage"
            )
        suite = req.get("eval_suite")
        if suite is not None and suite not in SUITES:
            raise ValueError(
                f"unknown eval_suite {suite!r}; upstream ships {list(SUITES)}"
            )
        # `--input_dir` must be the FOLDING output, not the generation stage.
        # Its help says "Directory with the output of run_alphafold.py", and
        # the code backs that: `_discover_folded_designs_for_metadata` lists
        # `in_dir` and `find_state_confidences` looks for
        # `<sample>_<state>_confidences_seed<n>.json` IN IT. A generation
        # stage holds none, so every design resolves to zero seeds and
        # `_load_metadata` raises "records no folding seed".
        #
        # This used to pass `01_generation` unconditionally, which meant a
        # campaign that HAD been folded failed identically to one that had
        # not -- and since this provider could not fold, the two causes were
        # indistinguishable and the error got read as the stronger claim
        # ("upstream refuses an unfolded campaign") when the weaker one
        # ("we pointed it at the wrong directory") was also true. Only the
        # metadata directory is shared between stages: `metadata_dir(stage)`
        # is `stage.parent / "metadata"`, the run root's, either way.
        folded = run_dir / self.FOLDED_STAGE
        if not folded.is_dir():
            raise RuntimeError(
                f"{run_dir} has no {self.FOLDED_STAGE} stage, so there are no "
                f"predicted structures to evaluate. Upstream's evaluation "
                f"reads folding output and does not fall back to the metrics "
                f"that need no structure prediction -- measured, not assumed. "
                f"This provider has no folding operation, because AlphaFold 3 "
                f"weights carry terms separate from AP Novo's and that "
                f"question is unsettled here. Fold this campaign's designs "
                f"with a structure predictor that has settled its own weights "
                f"question, then send the results to apnovo_ingest_folded, "
                f"which lays them out as upstream expects."
            )
        out_dir = run_dir / "04_eval"
        argv = [
            sys.executable,
            str(self.repo / "evaluate_design.py"),
            # `--input_dir`, singular, repeatable. The module-level variable
            # is named `_INPUT_DIRS` and the flag it declares is not: reading
            # the variable rather than the flag string cost a round here.
            f"--input_dir={folded}",
            f"--output_dir={out_dir}",
            "--noresume",
        ]
        if suite:
            argv.append(f"--eval_suite={suite}")
        proc = subprocess.run(argv, capture_output=True, text=True, cwd=self.repo)
        if proc.returncode:
            tail = proc.stderr.strip()[-2000:]
            # MEASURED, and it corrects what this provider used to claim:
            # evaluate_design.py does NOT degrade to the metrics that need no
            # prediction. It reads each design's metadata, finds no folding
            # seed, and refuses the whole run. So on a campaign that was never
            # folded this operation cannot produce a partial answer -- it
            # cannot produce any answer.
            if "records no folding seed" in tail:
                raise RuntimeError(
                    "this campaign has not been folded, and upstream's "
                    "evaluation refuses an unfolded campaign outright rather "
                    "than computing the subset of metrics that need no "
                    "structure prediction. This provider has no folding "
                    "operation: AlphaFold 3 weights carry terms separate from "
                    "AP Novo's and that question is unsettled here (see the "
                    "provider README). Fold the campaign's 01_generation "
                    "output with a structure predictor that has settled its "
                    "own weights question, lay the result out as upstream's "
                    "03_folded stage, and evaluate that."
                )
            raise RuntimeError(
                f"evaluate_design.py exited {proc.returncode}: {tail}"
            )

        rows = []
        for path in sorted(out_dir.glob("*_evaluation.json")):
            data = json.loads(path.read_text())
            rows.append(
                {
                    "sample_name": data.get("sample_name"),
                    "spec_name": data.get("spec_name"),
                    **{
                        k: v
                        for k, v in (data.get("metrics") or {}).items()
                        if isinstance(v, (int, float, str, bool))
                    },
                }
            )
        families = sorted(
            {k.split("/", 1)[0] for row in rows for k in row if "/" in k}
        )
        summary = out_dir / "evaluation_summary.csv"
        # A reaction suite that cannot run is SKIPPED WITH A WARNING, not an
        # error: `_evaluate_state` catches MissingAtomError and ValueError,
        # logs "Skipping <suite> suite metrics for ...", and carries on. Those
        # warnings go to this subprocess's stderr, which is read only when the
        # exit code is non-zero -- so a caller who asked for `eval_suite` got
        # `status: ok` and silently none of its metrics. MEASURED on a folded
        # two-design kemp campaign: every generic family came back and the
        # kemp suite contributed nothing, with no way to tell from the reply.
        skipped = [
            line.split("Skipping ", 1)[1].strip()
            for line in (proc.stderr or "").splitlines()
            if "Skipping " in line and "suite metrics" in line
        ]
        out: dict = {
            "status": "ok",
            "n_designs": len(rows),
            "metric_families": families,
            "metrics": rows,
            "summary_csv_path": str(summary) if summary.is_file() else None,
        }
        if suite:
            out["eval_suite"] = suite
            out["eval_suite_skipped"] = skipped
        folded = sorted(f for f in families if f not in ("sequence", "sampled"))
        if folded:
            out["note"] = (
                f"Folded states were present, so the state-prefixed families "
                f"{folded} were computed from them. The confidence record each "
                f"prediction arrived with is carried through as "
                f"<state>/plddt, /ptm, /iptm and the rest."
            )
            if suite and skipped:
                out["note"] += (
                    f" The {suite} suite was SKIPPED for {len(skipped)} "
                    f"(design, state) pair(s) -- see eval_suite_skipped. An "
                    f"absent metric is not a passing one."
                )
        else:
            out["note"] = (
                "This campaign holds no predicted structures, so only the "
                "families listed in metric_families were computable. Every "
                "state-prefixed metric the published threshold sets use is "
                "absent, and an absent metric is not a passing one. Fold the "
                "designs elsewhere and send them to apnovo_ingest_folded."
            )
        return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="AlphaProtein Novo resident worker")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--ligandmpnn-checkpoint", default="")
    parser.add_argument("--ligandmpnn-dir", default="")
    parser.add_argument("--ligandmpnn-python", default="")
    args = parser.parse_args(argv)

    base = _load_worker_base()
    engine = Engine(args)
    engine.build()

    def ready():
        body = {
            "build_s": engine.build_s,
            "weights_held_by": "worker",
            "compute_capability": engine.compute_capability,
            "requests_served": engine.requests,
            "stages_served": [
                "validate_motif",
                "generate",
                "resequence"
                if engine._can_resequence()
                else "resequence(unconfigured)",
                "evaluate",
            ],
            "stages_absent": ["folding"],
            "resequence_device": "cpu",
        }
        body.update(engine.memory())
        return body

    return base.serve(
        slug=args.slug,
        socket_path=args.socket,
        on_predict=engine.predict,
        ready=ready,
        log=_say,
    )


if __name__ == "__main__":
    sys.exit(main())
