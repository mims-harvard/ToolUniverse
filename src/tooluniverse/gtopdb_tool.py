"""Guide to Pharmacology (GtoPdb) tools, backed by the open bulk downloads.

GtoPdb's REST web services closed. Every path under /services now answers 401:

    {"message":"API key is missing. In order to use the GtoPdb Web Services
     you must register and request an API Key."}

Their published web-services page does not document how to send a key, and
seven ways of sending one -- ?apiKey=, ?api_key=, ?key=, X-API-Key, apiKey and
Authorization headers, bare and Bearer -- all come back with that same "key is
missing" body, so there is no mechanism to implement even for a registered
user. See data/broken_apis/gtopdb_rest.json.

The bulk CSVs under /DATA are still open and carry the same records, so that is
where these tools read from now. Measured 2026-10-03:

    targets_and_families.csv        1.81 MB   2.3 s    3392 targets
    ligands.csv                     6.54 MB   3.0 s   13991 ligands
    interactions.csv                7.20 MB   3.2 s   24936 interactions
    ligand_physchem_properties.csv  0.80 MB   2.0 s   11266 ligands

Each file is parsed once per process and kept, so only the first call in a
session pays the download. The two disease tools are gone: GtoPdb publishes no
open disease file, so there is nothing to read them from.

Filtering was always client-side here. The old REST service ignored ?type= when
?name= was present and ignored ?approved= entirely, so this module already
matched types and flags against the records itself; the bulk files just make
that the whole story instead of a workaround.
"""

from __future__ import annotations

import csv
import io
import re
import threading
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

GTOPDB_BULK_BASE = "https://www.guidetopharmacology.org/DATA"

TARGETS_FILE = "targets_and_families.csv"
LIGANDS_FILE = "ligands.csv"
INTERACTIONS_FILE = "interactions.csv"
PHYSCHEM_FILE = "ligand_physchem_properties.csv"

DEFAULT_LIMIT = 25
MAX_LIMIT = 200

# GtoPdb writes names with markup -- "5-HT<sub>1A</sub> receptor",
# "&alpha;<sub>1A</sub>" -- in both the CSVs and the old JSON. Searching for
# "5-HT1A" has to reach that record, so matching runs on the stripped text and
# the original is returned alongside it.
_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;")

def _norm_type(value: Any) -> str:
    """Case-, space- and underscore-insensitive type token.

    Collapses the query vocabulary ("CatalyticReceptor"), the record
    vocabulary ("catalytic_receptor") and human spellings ("Catalytic
    receptor") onto one key.
    """
    if value is None:
        return ""
    return re.sub(r"[\s_\-]+", " ", str(value).strip().lower())


class _TypeSpec:
    """One accepted `type` value.

    canonical      display spelling used in messages
    record_types   record `type` values that satisfy the filter, or None when
                   the filter is a boolean record field instead
    flag           record boolean field that satisfies the filter, e.g.
                   'approved'

    Carried over from the REST implementation unchanged apart from dropping
    server_value: there is no upstream query to push a value into any more.
    The vocabulary itself is verified knowledge and worth keeping -- notably
    AccessoryProtein, whose records carry an empty `type`, and the Ion channel
    umbrella, which GtoPdb has no single value for.
    """

    __slots__ = ("canonical", "flag", "record_types")

    def __init__(self, canonical, record_types=None, flag=None):
        self.canonical = canonical
        self.record_types = (
            frozenset(_norm_type(item) for item in record_types)
            if record_types is not None
            else None
        )
        self.flag = flag

    def matches(self, record: Any) -> bool:
        if not isinstance(record, dict):
            return False
        if self.flag is not None:
            return record.get(self.flag) is True
        return _norm_type(record.get("type")) in self.record_types


def _build_specs(entries) -> dict:
    table = {}
    for aliases, spec in entries:
        for alias in aliases:
            table[_norm_type(alias)] = spec
    return table


_LIGAND_TYPE_SPECS = _build_specs(
    [
        (("Synthetic organic",), _TypeSpec("Synthetic organic", ["Synthetic organic"])),
        (("Peptide",), _TypeSpec("Peptide", ["Peptide"])),
        (("Natural product",), _TypeSpec("Natural product", ["Natural product"])),
        (("Metabolite",), _TypeSpec("Metabolite", ["Metabolite"])),
        (("Antibody",), _TypeSpec("Antibody", ["Antibody"])),
        (("Nucleic acid",), _TypeSpec("Nucleic acid", ["Nucleic acid"])),
        (("Inorganic",), _TypeSpec("Inorganic", ["Inorganic"])),
        # Boolean fields on every ligand record, which GtoPdb also accepted
        # through ?type=.
        (("Approved",), _TypeSpec("Approved", None, "approved")),
        (("Withdrawn",), _TypeSpec("Withdrawn", None, "withdrawn")),
        (("Labelled", "Labeled"), _TypeSpec("Labelled", None, "labelled")),
    ]
)

_TARGET_TYPE_SPECS = _build_specs(
    [
        # The spelled-out forms are added here, not carried over: _norm_type
        # collapses case, spaces, hyphens and underscores, so they resolve to
        # the same spec and only widen what a caller may type.
        (
            ("GPCR", "G protein coupled receptor", "G protein-coupled receptor"),
            _TypeSpec("GPCR", ["gpcr"]),
        ),
        (
            ("NHR", "Nuclear receptor", "Nuclear hormone receptor"),
            _TypeSpec("NHR", ["nhr"]),
        ),
        (
            ("LGIC", "Ligand-gated ion channel"),
            _TypeSpec("LGIC", ["lgic"]),
        ),
        (
            ("VGIC", "Voltage-gated ion channel"),
            _TypeSpec("VGIC", ["vgic"]),
        ),
        (("OtherIC", "Other ion channel"), _TypeSpec("OtherIC", ["other_ic"])),
        (("Enzyme",), _TypeSpec("Enzyme", ["enzyme"])),
        (
            ("CatalyticReceptor", "Catalytic receptor"),
            _TypeSpec("CatalyticReceptor", ["catalytic_receptor"]),
        ),
        (("Transporter",), _TypeSpec("Transporter", ["transporter"])),
        (
            ("OtherProtein", "Other protein"),
            _TypeSpec("OtherProtein", ["other_protein"]),
        ),
        # These records carry an empty `type`.
        (
            ("AccessoryProtein", "Accessory protein"),
            _TypeSpec("AccessoryProtein", [""]),
        ),
        # GtoPdb splits ion channels into three record types with no single
        # value covering them.
        (
            ("Ion channel", "Ion channels"),
            _TypeSpec("Ion channel", ["lgic", "vgic", "other_ic"]),
        ),
    ]
)

# Values GtoPdb's own documentation lists that match no record.
_LIGAND_TYPE_DEAD_VALUES = {
    "endogenous peptide": "Peptide",
    "inn": "Approved",
}


def _type_validation_error(raw_value: Any, specs: dict, dead: dict, kind: str) -> dict:
    """Reject an unrecognised `type` rather than returning everything."""
    valid = sorted({spec.canonical for spec in specs.values()})
    message = (
        f"Invalid {kind} type={raw_value!r}. GtoPdb does not use this value, so "
        f"filtering on it would return every record unfiltered. "
        f"Valid values: {', '.join(valid)}."
    )
    hint = dead.get(_norm_type(raw_value))
    if hint:
        message += (
            f" Note: {raw_value!r} appears in GtoPdb's web-service documentation "
            f"but matches no record in the database -- use {hint!r} instead."
        )
    return {"status": "error", "error": message, "valid_types": valid}


_BULK_CACHE: Dict[str, List[Dict[str, str]]] = {}
_BULK_LOCK = threading.Lock()


def _plain(value: Any) -> str:
    """Markup-free text for matching and for display."""
    text = str(value or "")
    text = _TAG_RE.sub("", text)
    return _ENTITY_RE.sub("", text).strip()


def _norm(value: Any) -> str:
    return _plain(value).lower()


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    """True for every spelling GtoPdb uses across the bulk files.

    The files disagree: ligands.csv writes "yes" or an empty cell, while
    interactions.csv writes "true"/"false" for both Approved and Primary
    Target. Reading either one with the other's vocabulary makes the field
    silently always False, which is what the retired REST implementation did
    with its interaction `approved` check.
    """
    return str(value or "").strip().lower() in {"yes", "true", "t", "1", "y"}


def _as_number(value: Any) -> Any:
    """GtoPdb's REST service returned these as numbers; the CSV has strings.

    Kept numeric so anything built against the old /molecularProperties shape
    still gets 180.0422588 rather than "180.0422588".
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _limit(arguments: Dict[str, Any]) -> int:
    requested = _as_int(arguments.get("limit") or arguments.get("max_results"))
    if requested is None or requested <= 0:
        return DEFAULT_LIMIT
    return min(requested, MAX_LIMIT)


def load_bulk(file_name: str, timeout: int = 60) -> List[Dict[str, str]]:
    """Download and parse one GtoPdb bulk CSV, once per process.

    The first line is a version banner -- "# GtoPdb Version: 2026.3 -
    published: 2026-09-16" -- quoted as a single CSV field, so it is dropped
    before the header is read.
    """
    cached = _BULK_CACHE.get(file_name)
    if cached is not None:
        return cached

    with _BULK_LOCK:
        cached = _BULK_CACHE.get(file_name)
        if cached is not None:
            return cached

        session = requests.Session()
        try:
            response = request_with_retry(
                session,
                "GET",
                f"{GTOPDB_BULK_BASE}/{file_name}",
                timeout=timeout,
                max_attempts=3,
            )
        finally:
            session.close()
        if response.status_code != 200:
            raise RuntimeError(
                f"GtoPdb bulk download {file_name} returned HTTP "
                f"{response.status_code}"
            )

        text = response.text
        first, newline, rest = text.partition("\n")
        if first.lstrip('"').startswith("#"):
            text = rest if newline else ""
        rows = list(csv.DictReader(io.StringIO(text)))
        _BULK_CACHE[file_name] = rows
        return rows


def clear_bulk_cache() -> None:
    """Drop the parsed files. For tests; a process otherwise keeps them."""
    with _BULK_LOCK:
        _BULK_CACHE.clear()


def _relevance(record: Dict[str, Any], needle: str, *fields: str) -> tuple:
    """Rank an exact hit above a prefix hit above a substring hit.

    Searching targets for "EGFR" matched PKR1 and PKR2 first, because GtoPdb
    lists EGFR in their synonyms, and buried `epidermal growth factor receptor`
    in third place. Searching ligands for "morphine" led with apomorphine.
    Both results were right and both read as wrong.
    """
    for rank, field in enumerate(fields):
        value = _norm(record.get(field))
        if not value:
            continue
        if value == needle:
            return (0, rank, len(value))
        if value.startswith(needle):
            return (1, rank, len(value))
        if needle in value:
            return (2, rank, len(value))
    return (3, len(fields), 0)


def _target_record(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "targetId": _as_int(row.get("Target id")),
        "name": _plain(row.get("Target name")),
        "rawName": (row.get("Target name") or "").strip(),
        "abbreviation": _plain(row.get("Target abbreviated name")),
        "systematicName": _plain(row.get("Target systematic name")),
        "type": (row.get("Type") or "").strip(),
        "familyId": _as_int(row.get("Family id")),
        "familyName": _plain(row.get("Family name")),
        "geneSymbol": (row.get("HGNC symbol") or "").strip(),
        "hgncId": (row.get("HGNC id") or "").strip(),
        "synonyms": _plain(row.get("synonyms")),
    }


def _ligand_record(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "ligandId": _as_int(row.get("Ligand ID")),
        "name": _plain(row.get("Name")),
        "rawName": (row.get("Name") or "").strip(),
        "type": (row.get("Type") or "").strip(),
        "approved": _as_bool(row.get("Approved")),
        "withdrawn": _as_bool(row.get("Withdrawn")),
        "labelled": _as_bool(row.get("Labelled")),
        "species": (row.get("Species") or "").strip(),
        "pubchemCid": (row.get("PubChem CID") or "").strip(),
        "chemblId": (row.get("ChEMBL ID") or "").strip(),
        "uniprotId": (row.get("UniProt ID") or "").strip(),
        # The retired /structure endpoint returned these four, and ligands.csv
        # carries them with the same values -- checked against the recorded
        # aspirin (4139) fixture: CC(=O)Oc1ccccc1C(=O)O and
        # BSYNRYMUTXBXSQ-UHFFFAOYSA-N match exactly.
        "iupacName": (row.get("IUPAC name") or "").strip(),
        "inn": (row.get("INN") or "").strip(),
        "smiles": (row.get("SMILES") or "").strip(),
        "inchi": (row.get("InChI") or "").strip(),
        "inchiKey": (row.get("InChIKey") or "").strip(),
        "synonyms": _plain(row.get("Synonyms")),
    }


def _interaction_record(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "targetId": _as_int(row.get("Target ID")),
        "targetName": _plain(row.get("Target")),
        "targetGeneSymbol": (row.get("Target Gene Symbol") or "").strip(),
        "targetUniprotId": (row.get("Target UniProt ID") or "").strip(),
        "targetSpecies": (row.get("Target Species") or "").strip(),
        "ligandId": _as_int(row.get("Ligand ID")),
        "ligandName": _plain(row.get("Ligand")),
        "ligandType": (row.get("Ligand Type") or "").strip(),
        "approvedLigand": _as_bool(row.get("Approved")),
        "type": (row.get("Type") or "").strip(),
        "action": (row.get("Action") or "").strip(),
        "affinityUnits": (row.get("Affinity Units") or "").strip(),
        "affinityHigh": (row.get("Affinity High") or "").strip(),
        "affinityMedian": (row.get("Affinity Median") or "").strip(),
        "affinityLow": (row.get("Affinity Low") or "").strip(),
        "selectivity": (row.get("Selectivity") or "").strip(),
        "primaryTarget": _as_bool(row.get("Primary Target")),
    }


@register_tool("GtoPdbRESTTool")
class GtoPdbRESTTool(BaseTool):
    """One GtoPdb lookup, served from the open bulk files.

    The class name is kept because the tool configs and the static lazy
    registry name it; the transport is no longer REST.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        endpoint = (tool_config.get("fields") or {}).get("endpoint", "") or ""
        self.operation = self._operation_for(endpoint, tool_config.get("name") or "")

    @staticmethod
    def _operation_for(endpoint: str, name: str) -> str:
        path = endpoint.rstrip("/")
        if path.endswith("/ligandProperties") or "ligand_properties" in name.lower():
            return "ligand_properties"
        if path.endswith("/interactions") or "interactions" in name.lower():
            return "interactions"
        if path.endswith("/ligands") or "ligand" in name.lower():
            return "search_ligands"
        return "search_targets"

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Never raises; returns {status, data} or {status, error}."""
        arguments = dict(arguments or {})
        try:
            if self.operation == "search_targets":
                return self._search_targets(arguments)
            if self.operation == "search_ligands":
                return self._search_ligands(arguments)
            if self.operation == "interactions":
                return self._interactions(arguments)
            return self._ligand_properties(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": (
                    f"GtoPdb bulk download timed out after {self.timeout}s. The "
                    "files are a few MB each and are fetched once per session."
                ),
            }
        except requests.exceptions.RequestException as exc:
            return {
                "status": "error",
                "error": f"Failed to reach the GtoPdb bulk downloads: {exc}",
            }
        except Exception as exc:  # noqa: BLE001 - run() must never raise
            return {"status": "error", "error": f"Unexpected GtoPdb error: {exc}"}

    # ----------------------------------------------------------------- #
    # Targets
    # ----------------------------------------------------------------- #
    def _search_targets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("name") or arguments.get("query")
        gene_symbol = arguments.get("gene_symbol")
        wanted_type = arguments.get("type")

        if not query and not gene_symbol and wanted_type in (None, ""):
            return {
                "status": "error",
                "error": (
                    "Give at least one of name, gene_symbol or type. GtoPdb has "
                    "3392 targets and returning all of them is not a search."
                ),
            }

        spec = None
        if wanted_type not in (None, ""):
            spec = _TARGET_TYPE_SPECS.get(_norm_type(wanted_type))
            if spec is None:
                return _type_validation_error(
                    wanted_type, _TARGET_TYPE_SPECS, {}, "target"
                )

        needle = _norm(query) if query else None
        gene = _norm(gene_symbol) if gene_symbol else None
        matches = []
        for row in load_bulk(TARGETS_FILE, self.timeout):
            record = _target_record(row)
            if spec is not None and not spec.matches(record):
                continue
            if gene and _norm(record["geneSymbol"]) != gene:
                continue
            if needle and not any(
                needle in _norm(record[field])
                for field in ("name", "abbreviation", "systematicName", "synonyms")
            ):
                continue
            matches.append(record)

        if needle:
            matches.sort(
                key=lambda record: _relevance(
                    record,
                    needle,
                    "geneSymbol",
                    "abbreviation",
                    "name",
                    "systematicName",
                    "synonyms",
                )
            )

        limit = _limit(arguments)
        payload = {
            "source": f"{GTOPDB_BULK_BASE}/{TARGETS_FILE}",
            "total_matches": len(matches),
            "returned": min(len(matches), limit),
            "targets": matches[:limit],
        }
        if spec is not None and not matches and spec.canonical == "AccessoryProtein":
            payload["note"] = (
                "targets_and_families.csv carries no accessory proteins: every "
                "one of its 3392 rows has a Type, and accessory proteins were "
                "the records whose type was empty. The retired REST service "
                "returned 10 of them, so this is the one gap the bulk files "
                "leave in target search."
            )
        return {"status": "success", "data": payload}

    # ----------------------------------------------------------------- #
    # Ligands
    # ----------------------------------------------------------------- #
    def _search_ligands(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("name") or arguments.get("query")
        wanted_type = arguments.get("type")
        approved = arguments.get("approved")
        if approved is None:
            approved = arguments.get("approved_only")

        if not query and wanted_type in (None, "") and not approved:
            return {
                "status": "error",
                "error": (
                    "Give at least one of name, type or approved. GtoPdb has "
                    "13991 ligands and returning all of them is not a search."
                ),
            }

        spec = None
        if wanted_type not in (None, ""):
            spec = _LIGAND_TYPE_SPECS.get(_norm_type(wanted_type))
            if spec is None:
                return _type_validation_error(
                    wanted_type, _LIGAND_TYPE_SPECS, _LIGAND_TYPE_DEAD_VALUES, "ligand"
                )

        # approved is documented as "approved drugs only (true) or all ligands
        # (false/omit)", so false is not a filter for unapproved ligands.
        approved_only = bool(approved) is True

        needle = _norm(query) if query else None
        matches = []
        for row in load_bulk(LIGANDS_FILE, self.timeout):
            record = _ligand_record(row)
            if needle and needle not in _norm(record["name"]):
                continue
            if spec is not None and not spec.matches(record):
                continue
            if approved_only and not record["approved"]:
                continue
            matches.append(record)

        if needle:
            matches.sort(key=lambda record: _relevance(record, needle, "name"))

        limit = _limit(arguments)
        payload = {
            "source": f"{GTOPDB_BULK_BASE}/{LIGANDS_FILE}",
            "total_matches": len(matches),
            "returned": min(len(matches), limit),
            "ligands": matches[:limit],
        }
        if spec is not None and not matches:
            seen = {
                _plain(row.get("Type"))
                for row in load_bulk(LIGANDS_FILE, self.timeout)
                if (row.get("Type") or "").strip()
            }
            payload["note"] = (
                f"No ligand of type {wanted_type!r}. GtoPdb uses: "
                + ", ".join(sorted(seen))
            )
        return {"status": "success", "data": payload}

    # ----------------------------------------------------------------- #
    # Interactions
    # ----------------------------------------------------------------- #
    def _interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        target_id = _as_int(arguments.get("targetId") or arguments.get("target_id"))
        ligand_id = _as_int(arguments.get("ligandId") or arguments.get("ligand_id"))
        gene_symbol = arguments.get("gene_symbol")
        species = arguments.get("species")

        if target_id is None and ligand_id is None and not gene_symbol:
            return {
                "status": "error",
                "error": (
                    "Give one of targetId, ligandId or gene_symbol. GtoPdb has "
                    "24936 interactions and returning all of them is not a query."
                ),
            }

        # GtoPdb spells species "Human", "Mouse", "Rat", "SARS-CoV-2".
        species_needle = _norm(species) if species else None
        gene = _norm(gene_symbol) if gene_symbol else None

        matches = []
        for row in load_bulk(INTERACTIONS_FILE, self.timeout):
            record = _interaction_record(row)
            if target_id is not None and record["targetId"] != target_id:
                continue
            if ligand_id is not None and record["ligandId"] != ligand_id:
                continue
            if gene and _norm(record["targetGeneSymbol"]) != gene:
                continue
            if species_needle and _norm(record["targetSpecies"]) != species_needle:
                continue
            matches.append(record)

        limit = _limit(arguments)
        payload = {
            "source": f"{GTOPDB_BULK_BASE}/{INTERACTIONS_FILE}",
            "total_matches": len(matches),
            "returned": min(len(matches), limit),
            "interactions": matches[:limit],
        }
        if ligand_id is not None and not matches:
            payload["note"] = (
                f"GtoPdb records no interaction for ligand {ligand_id}. The bulk "
                "interactions file covers 11278 of the 13991 ligands -- an "
                "approved drug can be absent from it, oxycodone (7093) among "
                "them -- so this is 'nothing published here', not 'no such "
                "ligand'. GtoPdb_search_ligands confirms the ligand exists. Two "
                "things to try: GtoPdb sometimes files a drug's pharmacology "
                "under a related research-compound record, so check the ligand's "
                "activeDrugIds and prodrugIds and query those; and GtoPdb indexes "
                "interactions by target, so searching by targetId finds data that "
                "a ligand lookup misses."
            )
        if gene and not matches:
            payload["note"] = (
                f"No interaction lists {gene_symbol!r} as its target gene symbol. "
                "GtoPdb records interactions against curated targets, so a gene "
                "with no ligand in the database has none here. For approved drugs "
                "and clinical compounds, run "
                f"ChEMBL_search_targets(pref_name__contains='{gene_symbol}') to "
                "get a target_chembl_id, then "
                "ChEMBL_search_activities(target_chembl_id=...)."
            )
        elif matches and not any(item["approvedLigand"] for item in matches):
            # The retired implementation emitted this caveat on every non-empty
            # result, because the field it wanted to test was not on an
            # interaction object. interactions.csv carries Approved, so it can
            # be said only when it is true: 4576 of the 24936 rows involve an
            # approved ligand.
            target = gene_symbol or f"target {target_id}"
            payload["note"] = (
                "Every interaction here involves a research compound rather than "
                "an approved drug. For approved drugs and clinical compounds, run "
                f"ChEMBL_search_targets(pref_name__contains='{target}') to get a "
                "target_chembl_id, then "
                "ChEMBL_search_activities(target_chembl_id=...)."
            )
        return {"status": "success", "data": payload}

    # ----------------------------------------------------------------- #
    # Ligand properties
    # ----------------------------------------------------------------- #
    def _ligand_properties(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ligand_id = _as_int(arguments.get("ligand_id") or arguments.get("ligandId"))
        if ligand_id is None:
            return {
                "status": "error",
                "error": "ligand_id is required (GtoPdb ligand ID, e.g. 4139).",
            }

        properties = None
        for row in load_bulk(PHYSCHEM_FILE, self.timeout):
            if _as_int(row.get("Ligand ID")) == ligand_id:
                # Names and numeric types follow the retired
                # /molecularProperties response, not the CSV column headings,
                # so callers written against the REST shape keep working.
                properties = {
                    "hydrogenBondAcceptors": _as_number(row.get("HBond Acceptors")),
                    "hydrogenBondDonors": _as_number(row.get("HBond Donors")),
                    "rotatableBonds": _as_number(row.get("Rotatable Bonds")),
                    "topologicalPolarSurfaceArea": _as_number(row.get("TPSA")),
                    "molecularWeight": _as_number(row.get("Mol Weight")),
                    "logP": _as_number(row.get("XLogP")),
                    "lipinskisRuleOfFive": _as_number(row.get("LipinskiRO5")),
                }
                break

        identity = None
        for row in load_bulk(LIGANDS_FILE, self.timeout):
            if _as_int(row.get("Ligand ID")) == ligand_id:
                identity = _ligand_record(row)
                break

        if properties is None and identity is None:
            return {
                "status": "error",
                "error": f"GtoPdb has no ligand {ligand_id}.",
            }
        if properties is None:
            return {
                "status": "success",
                "data": {
                    "source": f"{GTOPDB_BULK_BASE}/{PHYSCHEM_FILE}",
                    "ligandId": ligand_id,
                    "ligand": identity,
                    "properties": None,
                    "note": (
                        "GtoPdb lists this ligand but publishes no "
                        "physicochemical properties for it. Of 13991 ligands, "
                        "11266 have a row in the properties file -- peptides "
                        "and antibodies mostly do not."
                    ),
                },
            }
        return {
            "status": "success",
            "data": {
                "source": f"{GTOPDB_BULK_BASE}/{PHYSCHEM_FILE}",
                "ligandId": ligand_id,
                "ligand": identity,
                "properties": properties,
            },
        }
