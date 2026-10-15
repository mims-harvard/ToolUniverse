"""The Carbon-A benchmark genome collection.

Carbon-A (``HuggingFaceBio/Carbon-A-1.2B``) predicts protein-coding sequence in
eukaryotic genomes. Its publisher keeps the evaluation genomes, each with the
NCBI reference annotation it is scored against, in a public Hugging Face bucket:
``HuggingFaceBio/Carbon-A-training-data``, under ``eval/``.

These tools read that collection. They return accessions, organisms, file
inventories with checksums, download URLs and per-molecule sequence reports --
never the sequence payloads, which run from 8 MB to 3 GB per genome and belong
in a file rather than a tool result. ``Carbon_A_get_benchmark_genome`` gives the
URLs to fetch and the md5 to check them against.

The three ``eval/`` subdirectories are the publisher's own split names, reported
here as given: ``seen``, ``unseen`` and ``nonstandard_code``. The model card
states that training covered 2,055 RefSeq assemblies across 2,047 species, and
the one genome under ``nonstandard_code`` -- *Tetrahymena thermophila* -- uses
NCBI translation table 6, which the annotation pipeline selects for it
automatically. Nothing published with the collection defines ``seen`` and
``unseen`` further, and the bucket's ``train/`` side is clade-level parquet
shards rather than per-accession directories, so membership cannot be checked
from the bucket either. The labels are passed through, not interpreted.

Organism names come from NCBI and are baked in below rather than fetched: an
assembly accession names one immutable assembly, and two of the 41 are no
longer served by the NCBI Datasets v2 ``dataset_report`` endpoint at all
(``GCF_000003025.6``, ``GCF_049306965.1``), so a live lookup would leave holes
in the catalog that a static map does not have.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

BUCKET = "HuggingFaceBio/Carbon-A-training-data"
_TREE_URL = f"https://huggingface.co/api/buckets/{BUCKET}/tree"
_RESOLVE_URL = f"https://huggingface.co/buckets/{BUCKET}/resolve"
MODEL_REPO = "HuggingFaceBio/Carbon-A-1.2B"

SPLITS = ("seen", "unseen", "nonstandard_code")

_TIMEOUT = 60
# The tree endpoint answers with a flat list and no cursor. eval/ holds 319
# entries today; a response at or above this size is treated as truncated
# rather than reported as the whole collection.
_TREE_PAGE_LIMIT = 1000

_MAX_SEQUENCES_REPORTED = 200

# Resolved 2026-10-13, one accession per request. A single dataset_report call
# listing all 41 accessions came back mis-keyed -- 21 of the organism names
# belonged to a different accession in the list -- so each row here was fetched
# on its own, with the response rejected unless its "accession" matched what was
# asked for. 38 of the 41 are corroborated independently by the assembly name in
# the bucket's own genome file name. The exceptions: GCF_034140825.1, where NCBI
# has renamed the assembly ASM3414082v1 to AGIS1.0 (Oryza sativa, confirmed
# against the Entrez assembly summary as a third source); and GCF_000003025.6
# and GCF_049306965.1, for which dataset_report serves no report at all and the
# organism comes from the Entrez assembly summary, each agreeing with the
# assembly name in the bucket file name.
_ORGANISMS: Dict[str, Tuple[str, int]] = {
    "GCF_000001215.4": ("Drosophila melanogaster", 7227),
    "GCF_000001405.40": ("Homo sapiens", 9606),
    "GCF_000001635.27": ("Mus musculus", 10090),
    "GCF_000001735.4": ("Arabidopsis thaliana", 3702),
    "GCF_000002235.5": ("Strongylocentrotus purpuratus", 7668),
    "GCF_000002425.5": ("Physcomitrium patens", 3218),
    "GCF_000002435.2": ("Giardia duodenalis", 5741),
    "GCF_000002445.2": ("Trypanosoma brucei brucei TREU927", 185431),
    "GCF_000002595.2": ("Chlamydomonas reinhardtii", 3055),
    "GCF_000002765.6": ("Plasmodium falciparum 3D7", 36329),
    "GCF_000002775.5": ("Populus trichocarpa", 3694),
    "GCF_000002945.2": ("Schizosaccharomyces pombe", 4896),
    "GCF_000002985.6": ("Caenorhabditis elegans", 6239),
    "GCF_000003025.6": ("Sus scrofa", 9823),
    "GCF_000004195.4": ("Xenopus tropicalis", 8364),
    "GCF_000004695.1": ("Dictyostelium discoideum AX4", 352472),
    "GCF_000146045.2": ("Saccharomyces cerevisiae S288C", 559292),
    "GCF_000182895.1": ("Coprinopsis cinerea okayama7#130", 240176),
    "GCF_000182925.2": ("Neurospora crassa OR74A", 367110),
    "GCF_000189635.1": ("Tetrahymena thermophila SB210", 312017),
    "GCF_000327385.1": ("Lottia gigantea", 225164),
    "GCF_008403515.1": ("Naegleria fowleri", 5763),
    "GCF_016097725.1": ("Ips typographus", 55986),
    "GCF_016699485.2": ("Gallus gallus", 9031),
    "GCF_026210795.1": ("Rhizophagus irregularis", 588596),
    "GCF_034140825.1": ("Oryza sativa Japonica Group", 39947),
    "GCF_049306965.1": ("Danio rerio", 7955),
    "GCF_054371585.1": ("Giraffa tippelskirchi", 439328),
    "GCF_054392235.1": ("Sus scrofa", 9823),
    "GCF_054491055.1": ("Hypomesus nipponensis", 182223),
    "GCF_055000105.1": ("Myodes glareolus", 447135),
    "GCF_055505025.1": ("Bos grunniens", 30521),
    "GCF_055691185.1": ("Crinia signifera", 326986),
    "GCF_055883805.1": ("Amblyomma maculatum", 34609),
    "GCF_056783735.1": ("Eptatretus burgeri", 7764),
    "GCF_056956725.1": ("Heliconius melpomene rosina", 171916),
    "GCF_057233095.1": ("Heloderma suspectum", 8554),
    "GCF_905368555.1": ("Meleagris gallopavo", 9103),
    "GCF_932526225.1": ("Nematostella vectensis", 45351),
    "GCF_963924565.1": ("Ascidiella aspersa", 201961),
    "GCF_978046115.1": ("Saccoglossus kowalevskii", 10224),
}


def _error(message: str) -> Dict[str, Any]:
    return {"status": "error", "error": message}


def _strip_dataset_prefix(path: str) -> str:
    """md5sum.txt names files by their path inside the NCBI Datasets zip.

    ``ncbi_dataset/data/GCF_000146045.2/genomic.gff`` is the bucket's
    ``genomic.gff``; only the basename identifies the file here.
    """
    return path.rsplit("/", 1)[-1]


@register_tool("CarbonABenchmarkTool")
class CarbonABenchmarkTool(BaseTool):
    """Read the Carbon-A evaluation genome collection from its public bucket."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {}) or {}
        self.operation = fields.get("operation", "list_genomes")
        # One tree listing serves every call on this instance. The bucket is
        # append-only published data, so a per-process read is not a staleness
        # risk within one session.
        self._tree: Optional[List[Dict[str, Any]]] = None

    # --- bucket access ----------------------------------------------------

    def _get(self, url: str, as_json: bool, timeout: int = _TIMEOUT):
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json() if as_json else response.text

    def _eval_tree(self) -> List[Dict[str, Any]]:
        if self._tree is None:
            self._tree = self._get(f"{_TREE_URL}/eval", as_json=True)
        return self._tree

    def _genomes(self) -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
        """Group the flat tree listing by accession.

        Returns the accessions and a truncation note, which is not an error:
        a partial catalog is still usable as long as it says it is partial.
        """
        tree = self._eval_tree()
        truncated = (
            f"The bucket listing returned {len(tree)} entries, the endpoint's "
            "page limit, so this catalog may be incomplete."
            if len(tree) >= _TREE_PAGE_LIMIT
            else None
        )
        genomes: Dict[str, Dict[str, Any]] = {}
        for entry in tree:
            parts = entry.get("path", "").split("/")
            if len(parts) != 4 or parts[0] != "eval":
                continue
            _, split, accession, filename = parts
            record = genomes.setdefault(
                accession,
                {"accession": accession, "split": split, "files": {}},
            )
            record["files"][filename] = entry.get("size")
        for accession, record in genomes.items():
            organism, tax_id = _ORGANISMS.get(accession, (None, None))
            record["organism"] = organism
            record["tax_id"] = tax_id
            genome = [f for f in record["files"] if f.endswith("_genomic.fna")]
            record["genome_fasta"] = genome[0] if genome else None
            record["genome_fasta_bytes"] = (
                record["files"][genome[0]] if genome else None
            )
            record["assembly_name"] = (
                genome[0][len(accession) + 1 : -len("_genomic.fna")]
                if genome and genome[0].startswith(accession + "_")
                else None
            )
            record["total_bytes"] = sum(
                size for size in record["files"].values() if isinstance(size, int)
            )
        return genomes, truncated

    # --- operations -------------------------------------------------------

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        arguments = arguments or {}
        try:
            if self.operation == "list_genomes":
                return self._list_genomes(arguments)
            if self.operation == "get_genome":
                return self._get_genome(arguments)
            return _error(f"Unknown operation '{self.operation}'")
        except requests.exceptions.Timeout:
            return _error(
                f"The Hugging Face bucket {BUCKET} did not respond within {_TIMEOUT} s."
            )
        except requests.exceptions.HTTPError as exc:
            status = getattr(exc.response, "status_code", "unknown")
            return _error(
                f"The Hugging Face bucket {BUCKET} returned HTTP {status}. "
                "The collection is public; a 401 or 403 means the bucket's "
                "visibility changed."
            )
        except requests.exceptions.RequestException as exc:
            return _error(f"Could not reach the Hugging Face bucket {BUCKET}: {exc}")

    def _list_genomes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        split = arguments.get("split") or "all"
        if split != "all" and split not in SPLITS:
            return _error(
                f"split must be 'all' or one of {', '.join(SPLITS)}, got {split!r}"
            )
        query = (arguments.get("organism_contains") or "").strip().lower()

        genomes, truncated = self._genomes()
        rows = []
        for record in genomes.values():
            if split != "all" and record["split"] != split:
                continue
            if query and query not in (record["organism"] or "").lower():
                continue
            rows.append(
                {
                    "accession": record["accession"],
                    "organism": record["organism"],
                    "tax_id": record["tax_id"],
                    "split": record["split"],
                    "assembly_name": record["assembly_name"],
                    "genome_fasta_bytes": record["genome_fasta_bytes"],
                    "files": len(record["files"]),
                }
            )
        rows.sort(key=lambda r: (r["split"], r["organism"] or "", r["accession"]))

        counts: Dict[str, int] = {}
        for record in genomes.values():
            counts[record["split"]] = counts.get(record["split"], 0) + 1

        result = {
            "status": "success",
            "data": {
                "bucket": BUCKET,
                "model": MODEL_REPO,
                "genomes": rows,
                "count": len(rows),
                "total_in_collection": len(genomes),
                "counts_by_split": counts,
                "note": (
                    "split is the publisher's own label for the eval/ "
                    "subdirectory a genome sits in, passed through as given. "
                    "Call Carbon_A_get_benchmark_genome for file URLs, "
                    "checksums and the per-molecule sequence report."
                ),
            },
        }
        if truncated:
            result["data"]["truncated"] = truncated
        return result

    def _get_genome(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return _error("accession is required, for example 'GCF_000146045.2'")

        genomes, truncated = self._genomes()
        record = genomes.get(accession)
        if record is None:
            known = sorted(genomes)
            return _error(
                f"{accession} is not in the Carbon-A benchmark collection. "
                f"It holds {len(known)} genomes; call "
                "Carbon_A_list_benchmark_genomes to see them."
                + (f" {truncated}" if truncated else "")
            )

        base = f"{_RESOLVE_URL}/eval/{record['split']}/{accession}"
        checksums = self._checksums(base, record["files"])

        files = []
        for filename in sorted(record["files"]):
            files.append(
                {
                    "filename": filename,
                    "bytes": record["files"][filename],
                    "url": f"{base}/{filename}",
                    "md5": checksums.get(filename),
                    # Matched by name, not by suffix: cds_from_genomic.fna also
                    # ends in "_genomic.fna" and is reference CDS, not the
                    # genome.
                    "role": _FILE_ROLES.get(
                        "genome_fasta"
                        if filename == record["genome_fasta"]
                        else filename,
                        None,
                    ),
                }
            )

        data = {
            "accession": accession,
            "organism": record["organism"],
            "tax_id": record["tax_id"],
            "split": record["split"],
            "assembly_name": record["assembly_name"],
            "bucket": BUCKET,
            "download_url_base": base,
            "total_bytes": record["total_bytes"],
            "files": files,
        }
        if accession == "GCF_000189635.1":
            data["genetic_code_note"] = (
                "This genome uses NCBI translation table 6. The Carbon-A "
                "annotation pipeline selects that table for this accession "
                "automatically; any other tool needs it passed explicitly."
            )

        if arguments.get("include_sequence_report", True):
            data["sequence_report"] = self._sequence_report(base, record["files"])
        if truncated:
            data["truncated"] = truncated
        return {"status": "success", "data": data}

    # --- per-genome detail ------------------------------------------------

    def _checksums(self, base: str, files: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Map filename to md5, empty when the collection has no md5sum.txt."""
        if "md5sum.txt" not in files:
            return {}
        try:
            text = self._get(f"{base}/md5sum.txt", as_json=False)
        except requests.exceptions.RequestException:
            return {}
        checksums = {}
        for line in text.splitlines():
            parts = line.split()
            if len(parts) == 2:
                checksums[_strip_dataset_prefix(parts[1])] = parts[0]
        return checksums

    def _sequence_report(self, base: str, files: Dict[str, Any]) -> Dict[str, Any]:
        if "sequence_report.jsonl" not in files:
            return {"available": False}
        try:
            text = self._get(f"{base}/sequence_report.jsonl", as_json=False)
        except requests.exceptions.RequestException as exc:
            return {"available": False, "error": f"could not be read: {exc}"}

        molecules = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                molecules.append(json.loads(line))
            except ValueError:
                continue
        if not molecules:
            return {"available": False, "error": "no records"}

        total = sum(m.get("length", 0) for m in molecules)
        roles: Dict[str, int] = {}
        for molecule in molecules:
            role = molecule.get("role") or "unknown"
            roles[role] = roles.get(role, 0) + 1

        sequences = [
            {
                "name": m.get("chrName") or m.get("sequenceName"),
                "refseq_accession": m.get("refseqAccession"),
                "length": m.get("length"),
                "gc_percent": m.get("gcPercent"),
                "role": m.get("role"),
            }
            for m in sorted(
                molecules, key=lambda m: m.get("length") or 0, reverse=True
            )[:_MAX_SEQUENCES_REPORTED]
        ]
        report: Dict[str, Any] = {
            "available": True,
            "sequences_in_assembly": len(molecules),
            "total_length_bp": total,
            "roles": roles,
            "sequences": sequences,
        }
        if len(molecules) > _MAX_SEQUENCES_REPORTED:
            report["sequences_note"] = (
                f"Showing the {_MAX_SEQUENCES_REPORTED} longest of "
                f"{len(molecules)} sequences, by length. The full report is "
                "sequence_report.jsonl in the file list."
            )
        return report


_FILE_ROLES = {
    "genome_fasta": "Genomic DNA, the input to annotation.",
    "genomic.gff": "NCBI reference annotation, the target a prediction is scored against.",
    "cds_from_genomic.fna": "Reference CDS nucleotide sequences.",
    "protein.faa": "Reference protein sequences.",
    "rna.fna": "Reference RNA sequences.",
    "sequence_report.jsonl": "Per-molecule assembly report.",
    "md5sum.txt": "Checksums for the files in this directory.",
    "README.md": "NCBI Datasets boilerplate, no genome-specific content.",
}
