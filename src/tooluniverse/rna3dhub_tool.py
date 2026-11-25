# rna3dhub_tool.py
"""
BGSU RNA 3D Hub tools for ToolUniverse.

RNA 3D Hub (Bowling Green State University) annotates every RNA-containing
structure in the PDB each week. It publishes two curated resources:

- Representative sets: RNA chains grouped into equivalence classes (same
  molecule, same organism), with the best-modelled chain picked as the
  representative. This is the standard non-redundant list for RNA 3D work.
- The RNA 3D Motif Atlas: hairpin, internal and multi-helix junction loops
  from the representative structures, clustered by 3D geometry into motif
  groups (GNRA tetraloop, kink-turn, T-loop, ...).

ToolUniverse had RNA sequence and family sources (RNAcentral, Rfam) but no
source for curated RNA 3D structure sets or 3D motifs. These tools read the
representative set, list and read motif groups, and list the loops of one
PDB entry.

Site: https://rna.bgsu.edu/rna3dhub (data licence CC BY 4.0). No key.

The download routes answer some bad requests with HTTP 200 and a one-line
text ("Invalid release id", "No loops found"), and return the
representative set in a row order that changes between requests. The tools
turn the texts into errors or explained empty results and sort the rows.
"""

import csv
import io
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

RNA3DHUB_BASE_URL = "https://rna.bgsu.edu/rna3dhub"

# Resolution cutoffs (in angstrom) that every representative-set release has.
_RESOLUTIONS = ("1.5", "2.0", "2.5", "3.0", "3.5", "4.0", "20.0", "all")
# Loop types with a Motif Atlas release. The site lists J8 and J9 too, but
# their release routes answer 404.
_LOOP_TYPES = {
    "HL": "hairpin loop",
    "IL": "internal loop",
    "J3": "3-way junction",
    "J4": "4-way junction",
    "J5": "5-way junction",
    "J6": "6-way junction",
    "J7": "7-way junction",
}
_RELEASE_RE = re.compile(r"^\d+\.\d+$")
_PDB_ID_RE = re.compile(r"^[0-9][A-Za-z0-9]{3}$")
_MOTIF_ID_RE = re.compile(r"^(HL|IL|J\d{1,2})_\d+\.\d+$")
_INVALID_RELEASE = "invalid release id"
_NO_LOOPS = "no loops found"


class _RNA3DHubError(Exception):
    """An RNA 3D Hub answer that the tool reports as an error."""


def _pdb_of(unit_or_chain_id: str) -> str:
    """'4TNA' from a unit id '4TNA|1|A|G|15' or a chain id '4TNA|1|A'."""
    return str(unit_or_chain_id).split("|", 1)[0]


def _sequence(unit_ids: List[str]) -> str:
    """Loop sequence from unit ids; a modified residue is written as (H2U)."""
    parts = []
    for unit_id in unit_ids:
        fields = str(unit_id).split("|")
        component = fields[3] if len(fields) > 3 else "?"
        parts.append(component if len(component) == 1 else f"({component})")
    return "".join(parts)


def _model(unit_ids: List[str]) -> Optional[int]:
    """Model number of a loop, from its first unit id ('2KZL|3|A|C|27' -> 3)."""
    fields = str(unit_ids[0]).split("|") if unit_ids else []
    return int(fields[1]) if len(fields) > 1 and fields[1].isdigit() else None


def _chains(unit_ids: List[str]) -> List[str]:
    """Chain ids of the unit ids, in order of first use."""
    chains: List[str] = []
    for unit_id in unit_ids:
        fields = str(unit_id).split("|")
        if len(fields) > 2 and fields[2] not in chains:
            chains.append(fields[2])
    return chains


@register_tool("RNA3DHubTool")
class RNA3DHubTool(BaseTool):
    """
    Query the BGSU RNA 3D Hub: representative sets and the RNA 3D Motif Atlas.

    Operations (``fields.operation`` in the tool config):

    - ``get_representative_set``: the non-redundant RNA structure list.
    - ``list_motifs``: the motif groups of one loop type.
    - ``get_motif``: the loop instances of one motif group.
    - ``get_structure_loops``: the loops annotated in one PDB entry.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_representative_set"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run the configured RNA 3D Hub operation."""
        arguments = arguments or {}
        operations = {
            "get_representative_set": self._get_representative_set,
            "list_motifs": self._list_motifs,
            "get_motif": self._get_motif,
            "get_structure_loops": self._get_structure_loops,
        }
        handler = operations.get(self.operation)
        if handler is None:
            return {"status": "error", "error": f"Unknown operation: {self.operation}"}
        try:
            return handler(arguments)
        except _RNA3DHubError as e:
            return {"status": "error", "error": str(e)}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"RNA 3D Hub request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to RNA 3D Hub. Check network.",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "RNA 3D Hub returned a response that is not valid JSON",
            }
        except Exception as e:  # never raise out of run()
            return {"status": "error", "error": f"Error querying RNA 3D Hub: {e}"}

    # -- HTTP -------------------------------------------------------------

    def _get(self, path: str) -> requests.Response:
        """GET an RNA 3D Hub path; raise _RNA3DHubError on an HTTP error.

        The site answers an HTTP error with a JSON body that holds a
        ``message`` and a PHP stack trace. Only the message is passed on.
        """
        url = f"{RNA3DHUB_BASE_URL}/{path.lstrip('/')}"
        response = requests.get(url, timeout=self.timeout)
        if response.status_code >= 400:
            message = None
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    message = payload.get("message")
            except ValueError:
                pass
            raise _RNA3DHubError(
                f"RNA 3D Hub returned HTTP {response.status_code}"
                + (f": {message}" if message else "")
            )
        return response

    @staticmethod
    def _metadata(**extra: Any) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "source": "BGSU RNA 3D Hub (rna.bgsu.edu/rna3dhub), CC BY 4.0"
        }
        metadata.update({k: v for k, v in extra.items() if v is not None})
        return metadata

    # -- argument checks --------------------------------------------------

    @staticmethod
    def _int(arguments: Dict[str, Any], name: str, default: Any) -> Any:
        value = arguments.get(name)
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            raise _RNA3DHubError(f"{name} must be an integer")
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise _RNA3DHubError(f"{name} must be an integer, not '{value}'")
        if isinstance(value, float) and value != number:
            raise _RNA3DHubError(f"{name} must be an integer, not {value}")
        return number

    def _paging(
        self, arguments: Dict[str, Any], default: int, maximum: int
    ) -> Tuple[int, int]:
        """(limit, offset) from the arguments, checked before any request."""
        limit = self._int(arguments, "limit", default)
        offset = self._int(arguments, "offset", 0)
        if limit < 1 or limit > maximum:
            raise _RNA3DHubError(f"limit must be between 1 and {maximum}")
        if offset < 0:
            raise _RNA3DHubError("offset must be 0 or more")
        return limit, offset

    @staticmethod
    def _page(
        rows: List[Any], paging: Tuple[int, int]
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """One page of ``rows`` and the paging fields for the metadata."""
        limit, offset = paging
        page = rows[offset : offset + limit]
        has_more = offset + len(page) < len(rows)
        return page, {
            "returned": len(page),
            "offset": offset,
            "has_more": has_more,
            "next_offset": offset + len(page) if has_more else None,
        }

    @staticmethod
    def _release(arguments: Dict[str, Any]) -> str:
        release = str(arguments.get("release") or "current").strip().lower()
        if release != "current" and not _RELEASE_RE.match(release):
            raise _RNA3DHubError(
                f"release must be 'current' or a release id such as '4.66', "
                f"not '{arguments.get('release')}'"
            )
        return release

    @staticmethod
    def _pdb_id(value: Any, required: bool) -> Optional[str]:
        pdb_id = str(value or "").strip()
        if not pdb_id:
            if required:
                raise _RNA3DHubError("pdb_id is required, e.g. '4TNA'")
            return None
        if not _PDB_ID_RE.match(pdb_id):
            raise _RNA3DHubError(
                f"pdb_id must be a 4-character PDB id such as '4TNA', not '{value}'"
            )
        return pdb_id.upper()

    @staticmethod
    def _loop_type(value: Any, required: bool) -> Optional[str]:
        loop_type = str(value or "").strip().upper()
        if not loop_type:
            if required:
                raise _RNA3DHubError(
                    "loop_type is required: one of " + ", ".join(_LOOP_TYPES)
                )
            return None
        if loop_type not in _LOOP_TYPES:
            raise _RNA3DHubError(
                f"loop_type must be one of {', '.join(_LOOP_TYPES)} "
                f"(hairpin, internal, 3- to 7-way junction), not '{value}'"
            )
        return loop_type

    @staticmethod
    def _resolution(arguments: Dict[str, Any]) -> str:
        raw = arguments.get("resolution")
        if raw is None or raw == "":
            return "4.0"
        text = str(raw).strip().lower().rstrip("a").strip()
        if text == "all":
            return "all"
        try:
            text = f"{float(text):.1f}"
        except ValueError:
            pass
        if text not in _RESOLUTIONS or isinstance(raw, bool):
            raise _RNA3DHubError(
                f"resolution must be one of {', '.join(_RESOLUTIONS)} "
                f"(angstrom cutoff), not '{raw}'"
            )
        return text

    # -- representative sets ----------------------------------------------

    def _read_representative_set(
        self, release: str, resolution: str
    ) -> List[Dict[str, Any]]:
        """Equivalence classes of one release and cutoff, sorted by class id."""
        cutoff = "all" if resolution == "all" else f"{resolution}A"
        text = self._get(f"nrlist/download/{release}/{cutoff}/csv").text
        if text.strip().lower() == _INVALID_RELEASE:
            # HTTP 200 with this one line: read as CSV it is one bogus row.
            raise _RNA3DHubError(
                f"RNA 3D Hub has no representative-set release '{release}'. "
                "Use 'current' or a release id from "
                "https://rna.bgsu.edu/rna3dhub/nrlist, e.g. '4.66'."
            )
        classes = []
        for row in csv.reader(io.StringIO(text)):
            if not row:
                continue
            if len(row) != 3 or not row[0].startswith("NR_"):
                raise _RNA3DHubError(
                    "RNA 3D Hub returned an unexpected representative set: "
                    + text.strip()[:120]
                )
            members = [m for m in row[2].split(",") if m]
            classes.append(
                {"class_id": row[0], "representative": row[1], "members": members}
            )
        if not classes:
            raise _RNA3DHubError(
                f"RNA 3D Hub returned an empty representative set for release "
                f"'{release}' at resolution {resolution}"
            )
        # The server changes the row order between requests.
        classes.sort(key=lambda c: c["class_id"])
        return classes

    def _get_representative_set(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Equivalence classes of RNA chains with their representative chain."""
        release = self._release(arguments)
        resolution = self._resolution(arguments)
        pdb_id = self._pdb_id(arguments.get("pdb_id"), required=False)
        include_members = bool(arguments.get("include_members"))
        paging_args = self._paging(arguments, default=50, maximum=500)
        classes = self._read_representative_set(release, resolution)

        rows: List[Dict[str, Any]] = []
        for item in classes:
            matched = [
                member
                for member in item["members"]
                if pdb_id and pdb_id in {_pdb_of(c) for c in member.split("+")}
            ]
            if pdb_id and not matched:
                continue
            row: Dict[str, Any] = {
                "class_id": item["class_id"],
                "representative": item["representative"],
                "representative_pdb_id": _pdb_of(item["representative"]),
                "member_count": len(item["members"]),
            }
            if pdb_id:
                row["matched_members"] = matched
            if include_members:
                row["members"] = item["members"]
            rows.append(row)

        if pdb_id and not rows and resolution == "all" and release == "current":
            # No cutoff and the newest release: the Hub has no RNA chain of it.
            raise _RNA3DHubError(self._unknown_entry(pdb_id))
        page, paging = self._page(rows, paging_args)
        cutoff_text = (
            "any resolution" if resolution == "all" else f"{resolution} A or better"
        )
        if pdb_id and not rows:
            note = (
                f"No equivalence class of release '{release}' at {cutoff_text} "
                f"holds a chain of {pdb_id}. The entry can have a resolution "
                "worse than the cutoff or a release date after this release. "
                "resolution='all' with release='current' removes both limits "
                "and returns an error for an id that the Hub does not hold."
            )
        elif pdb_id:
            note = (
                f"Classes with a chain of {pdb_id}. matched_members are its "
                "chains; representative is the chain to use for the class."
            )
        else:
            note = (
                "One row per equivalence class, sorted by class_id. "
                "representative is the best-modelled chain of the class. "
                "Set include_members=true for the full member list."
            )
        return {
            "status": "success",
            "data": page,
            "metadata": self._metadata(
                release=release,
                resolution=resolution,
                pdb_id=pdb_id,
                total_classes=len(classes),
                matched_classes=len(rows),
                note=note,
                **paging,
            ),
        }

    # -- motif atlas ------------------------------------------------------

    @staticmethod
    def _annotation_counts(annotations: Any) -> Dict[str, int]:
        """{'GNRA': 247, ...}: how many loop instances carry each annotation."""
        counts: Dict[str, int] = {}
        values = annotations.values() if isinstance(annotations, dict) else []
        for text in values:
            if text:
                counts[str(text)] = counts.get(str(text), 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    def _list_motifs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Motif groups of one loop type in a Motif Atlas release."""
        loop_type = self._loop_type(arguments.get("loop_type"), required=True)
        release = self._release(arguments)
        min_instances = self._int(arguments, "min_instances", 0)
        if min_instances < 0:
            raise _RNA3DHubError("min_instances must be 0 or more")
        paging_args = self._paging(arguments, default=50, maximum=500)
        query = str(arguments.get("query") or "").strip().lower()
        groups = self._get(f"motifs/release/{loop_type.lower()}/{release}/json").json()
        if not isinstance(groups, list):
            raise _RNA3DHubError("RNA 3D Hub returned an unexpected motif list")

        rows: List[Dict[str, Any]] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            counts = self._annotation_counts(group.get("annotations"))
            text = " ".join(
                [
                    str(group.get("motif_id") or ""),
                    str(group.get("common_name") or ""),
                    str(group.get("annotation") or ""),
                ]
                + list(counts)
            ).lower()
            num_instances = group.get("num_instances") or 0
            if (query and query not in text) or num_instances < min_instances:
                continue
            rows.append(
                {
                    "motif_id": group.get("motif_id"),
                    "common_name": group.get("common_name") or None,
                    "annotation": group.get("annotation") or None,
                    "instance_annotations": counts,
                    "bp_signature": group.get("bp_signature"),
                    "num_instances": num_instances,
                    "num_nucleotides": group.get("num_nucleotides"),
                }
            )
        rows.sort(key=lambda r: (-r["num_instances"], str(r["motif_id"])))
        page, paging = self._page(rows, paging_args)
        if rows:
            note = (
                "Sorted by num_instances, largest group first. A group name such "
                "as GNRA is in instance_annotations (annotation text -> number of "
                "loops) when common_name is null. Pass motif_id to "
                "RNA3DHub_get_motif for the loops."
            )
        else:
            note = (
                f"No {_LOOP_TYPES[loop_type]} motif group of release '{release}' "
                "matches the filters. query is matched against the motif id, the "
                "group name and the loop annotations, not the base-pair signature."
            )
        return {
            "status": "success",
            "data": page,
            "metadata": self._metadata(
                loop_type=loop_type,
                loop_type_name=_LOOP_TYPES[loop_type],
                release=release,
                query=query or None,
                total_motifs=len(groups),
                matched_motifs=len(rows),
                note=note,
                **paging,
            ),
        }

    def _get_motif(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """The loop instances of one motif group, aligned position by position."""
        raw = str(arguments.get("motif_id") or "").strip()
        if not raw:
            raise _RNA3DHubError("motif_id is required, e.g. 'HL_27656.2'")
        motif_id = raw.upper()
        if not _MOTIF_ID_RE.match(motif_id):
            raise _RNA3DHubError(
                f"motif_id must look like 'HL_27656.2' (loop type, group number, "
                f"version), not '{raw}'. RNA3DHub_list_motifs lists the ids."
            )
        paging_args = self._paging(arguments, default=50, maximum=500)
        group = self._get(f"motif/view/{motif_id}/json").json()
        if not isinstance(group, dict) or "alignment" not in group:
            raise _RNA3DHubError(f"RNA 3D Hub returned no motif group for {motif_id}")
        alignment = group.get("alignment")
        if not isinstance(alignment, dict):
            alignment = {}
        annotations = group.get("annotations")
        if not isinstance(annotations, dict):
            annotations = {}

        instances: List[Dict[str, Any]] = []
        for loop_id, positions in alignment.items():
            if not isinstance(positions, dict):
                continue
            ordered = sorted(
                positions.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0
            )
            unit_ids = [str(unit_id) for _, unit_id in ordered]
            instances.append(
                {
                    "loop_id": loop_id,
                    "pdb_id": _pdb_of(unit_ids[0]) if unit_ids else None,
                    "annotation": annotations.get(loop_id) or None,
                    "chains": _chains(unit_ids),
                    "sequence": _sequence(unit_ids),
                    "unit_ids": unit_ids,
                }
            )
        page, paging = self._page(instances, paging_args)
        loop_type = motif_id.split("_", 1)[0]
        data = {
            "motif_id": group.get("motif_id") or motif_id,
            "loop_type": loop_type,
            "common_name": group.get("common_name") or None,
            "annotation": group.get("annotation") or None,
            "instance_annotations": self._annotation_counts(annotations),
            "bp_signature": group.get("bp_signature"),
            "num_instances": group.get("num_instances", len(instances)),
            "num_nucleotides": group.get("num_nucleotides"),
            "chainbreak": group.get("chainbreak") or [],
            "instances": page,
        }
        return {
            "status": "success",
            "data": data,
            "metadata": self._metadata(
                total_instances=len(instances),
                note="unit_ids are aligned: position N of every instance is the "
                "same 3D position of the motif. A unit id reads "
                "PDB|model|chain|residue|number. chainbreak lists the positions "
                "after which the loop moves to its next strand.",
                **paging,
            ),
        }

    # -- loops of one structure -------------------------------------------

    def _get_structure_loops(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Hairpin, internal and junction loops annotated in one PDB entry."""
        pdb_id = self._pdb_id(arguments.get("pdb_id"), required=True)
        loop_type = self._loop_type(arguments.get("loop_type"), required=False)
        model = self._int(arguments, "model", None)
        if model is not None and model < 1:
            raise _RNA3DHubError("model must be 1 or more")
        paging_args = self._paging(arguments, default=100, maximum=500)
        text = self._get(f"loops/download/{pdb_id}").text

        loops: List[Dict[str, Any]] = []
        if text.strip().lower() != _NO_LOOPS:
            for row in csv.reader(io.StringIO(text)):
                if not row:
                    continue
                if len(row) != 2 or "_" not in row[0]:
                    raise _RNA3DHubError(
                        f"RNA 3D Hub returned an unexpected loop list for {pdb_id}: "
                        + text.strip()[:120]
                    )
                unit_ids = [u for u in row[1].split(",") if u]
                loops.append(
                    {
                        "loop_id": row[0],
                        "loop_type": row[0].split("_", 1)[0],
                        "model": _model(unit_ids),
                        "chains": _chains(unit_ids),
                        "nucleotide_count": len(unit_ids),
                        "sequence": _sequence(unit_ids),
                        "unit_ids": unit_ids,
                    }
                )
        if not loops:
            # "No loops found" (HTTP 200) is the answer for an RNA with no loop
            # and for an id that RNA 3D Hub does not hold. Tell them apart.
            return self._no_loops(pdb_id)

        # A multi-model (NMR) entry has one row per loop per model.
        models = sorted({loop["model"] for loop in loops if loop["model"] is not None})
        if model is not None:
            if model not in models:
                if not models:
                    where = "Its loops carry no model number."
                elif len(models) == 1:
                    where = f"Its loops are in model {models[0]} only."
                else:
                    where = f"Its loops are in the models {models[0]} to {models[-1]}."
                raise _RNA3DHubError(
                    f"{pdb_id} has no model {model} in RNA 3D Hub. {where}"
                )
            loops = [loop for loop in loops if loop["model"] == model]
        counts: Dict[str, int] = {}
        for loop in loops:
            counts[loop["loop_type"]] = counts.get(loop["loop_type"], 0) + 1
        loops.sort(key=lambda loop: loop["loop_id"])
        rows = [
            loop for loop in loops if not loop_type or loop["loop_type"] == loop_type
        ]
        page, paging = self._page(rows, paging_args)
        note = (
            "A modified residue is written in brackets in sequence, e.g. (H2U). "
            "A unit id reads PDB|model|chain|residue|number."
        )
        if loop_type and not rows:
            note = (
                f"{pdb_id} has no {_LOOP_TYPES[loop_type]} ({loop_type}). "
                "loop_type_counts shows the loop types it has."
            )
        if model is None and len(models) > 1:
            note = (
                f"{pdb_id} has {len(models)} models (usual for an NMR entry), and "
                "RNA 3D Hub lists each loop one time per model with its own "
                "loop_id. total_loops and loop_type_counts count all "
                f"{len(models)} models, so they are not the number of loops of "
                "the molecule. Set model=1 to read one model. " + note
            )
        return {
            "status": "success",
            "data": page,
            "metadata": self._metadata(
                pdb_id=pdb_id,
                loop_type=loop_type,
                model=model,
                model_count=len(models),
                total_loops=len(loops),
                loop_type_counts=dict(sorted(counts.items())),
                matched_loops=len(rows),
                note=note,
                **paging,
            ),
        }

    @staticmethod
    def _unknown_entry(pdb_id: str) -> str:
        return (
            f"RNA 3D Hub holds no RNA structure with the id {pdb_id}: no chain "
            "of this entry is in the current representative set at any "
            "resolution. The id can be wrong, the entry can have no RNA, or it "
            "can be newer than the weekly release."
        )

    def _no_loops(self, pdb_id: str) -> Dict[str, Any]:
        """Explain a 'No loops found' answer with the representative set."""
        try:
            classes = self._read_representative_set("current", "all")
        except (_RNA3DHubError, requests.exceptions.RequestException) as e:
            raise _RNA3DHubError(
                f"RNA 3D Hub answered 'No loops found' for {pdb_id}. It gives this "
                "answer for an RNA with no loop and for an id it does not hold, "
                f"and the check that tells them apart failed: {e}"
            )
        known = any(
            pdb_id == _pdb_of(chain)
            for item in classes
            for member in item["members"]
            for chain in member.split("+")
        )
        if not known:
            raise _RNA3DHubError(
                "The Hub answered 'No loops found'. " + self._unknown_entry(pdb_id)
            )
        return {
            "status": "success",
            "data": [],
            "metadata": self._metadata(
                pdb_id=pdb_id,
                model_count=0,
                total_loops=0,
                loop_type_counts={},
                matched_loops=0,
                returned=0,
                offset=0,
                has_more=False,
                note=f"{pdb_id} is an RNA structure in RNA 3D Hub, and it has no "
                "annotated hairpin, internal or junction loop. This is usual for "
                "a short single strand or a plain duplex.",
            ),
        }
