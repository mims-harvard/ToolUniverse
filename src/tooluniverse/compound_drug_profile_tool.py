"""Compound tool: assemble a drug profile from several databases in one call.

Answering "what is this drug, what does it do, what is it for, what is the risk"
currently means resolving the name to a ChEMBL id, a PubChem CID and an RxCUI,
then issuing a further call per question, because almost every drug tool is
keyed by one specific identifier. This does the resolution once and returns the
sections together.

The resolution is the part that can go quietly wrong. OpenTargets' drug search
is relevance-ranked, not exact: 'aspirin' returns ASPIRIN first but IMATINIB
second, so a hit chosen by rank alone can be a different drug entirely. A hit is
only taken as exact when its name matches the query; anything else is reported
as a substitution, with the name that was actually profiled.
"""

import re
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool


def _truncate_msg(msg: str, limit: int = 240) -> str:
    """Truncate an error message on a word boundary, never mid-word."""
    if len(msg) <= limit:
        return msg
    return msg[:limit].rsplit(" ", 1)[0] + "..."


def _as_number(value: Any) -> Any:
    """Coerce a numeric-looking value to a number, or return it untouched.

    ChEMBL reports max_phase as the string '4.0' and molecular weight as
    '180.16'. Passing those through would make `max_phase == 4` false for an
    approved drug, so the quantity is normalized rather than the caller being
    asked to know which fields arrive as text.
    """
    if value is None or isinstance(value, (int, float)):
        return value
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return value
    return int(number) if number.is_integer() else number


_NOT_FOUND = re.compile(r"\b404\b|not found|no record|no results", re.IGNORECASE)


def _is_not_found(message: str) -> bool:
    """Whether an upstream error says 'no such record' rather than 'I broke'."""
    return bool(_NOT_FOUND.search(message or ""))


# Which shared records each section reads. Kept as data so the fetch decision
# and the claim that an omitted section costs nothing cannot drift apart.
_NEEDS_CHEMBL_RECORD = frozenset({"identity", "structure", "safety"})
_NEEDS_PUBCHEM_RECORD = frozenset({"structure"})


def _records_needed(sections) -> tuple[bool, bool]:
    """Return (chembl record wanted, pubchem record wanted) for these sections."""
    wants = set(sections)
    return bool(wants & _NEEDS_CHEMBL_RECORD), bool(wants & _NEEDS_PUBCHEM_RECORD)


CHEMBL_ID = re.compile(r"^CHEMBL\d+$", re.IGNORECASE)

SECTIONS = ("identity", "structure", "mechanism", "indications", "safety")

# PubChem renamed several properties; 'CanonicalSMILES' now returns nothing and
# the current spelling is 'ConnectivitySMILES'.
_PUBCHEM_PROPERTIES = [
    "MolecularFormula",
    "MolecularWeight",
    "InChIKey",
    "ConnectivitySMILES",
    "IUPACName",
]


@register_tool("CompoundDrugProfileTool")
class CompoundDrugProfileTool(BaseTool):
    """Resolve a drug once, then gather its profile from several databases."""

    # Caps, named so the slicing and the disclosure that restates what it cut
    # can never drift apart.
    INDICATIONS_CAP = 50
    SYNONYMS_CAP = 15
    MECHANISMS_CAP = 10

    def __init__(self, tool_config: dict[str, Any], **kwargs):
        super().__init__(tool_config)

    # --------------------------------------------------------------------- run

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw = arguments.get("drug")
        if not raw or not str(raw).strip():
            return {"status": "error", "error": "'drug' is required."}
        drug = str(raw).strip()

        requested = arguments.get("sections")
        if requested is not None and not requested:
            # An explicit empty list is a mistake, not a request for everything:
            # falling back to the default would hand back all five sections and
            # bill for all of them.
            return {
                "status": "error",
                "error": (
                    "'sections' was empty. Omit it for all sections, or name at "
                    f"least one of: {', '.join(SECTIONS)}."
                ),
            }
        sections = list(requested) if requested else list(SECTIONS)
        unknown = [s for s in sections if s not in SECTIONS]
        if unknown:
            return {
                "status": "error",
                "error": (
                    f"Unknown section(s): {', '.join(unknown)}. "
                    f"Available: {', '.join(SECTIONS)}."
                ),
            }

        from .execute_function import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        failed: list[str] = []
        skipped: list[str] = []
        queried: list[str] = []

        def note(source: str, reason: str) -> None:
            skipped.append(f"{source}: {reason}")

        def call(
            source: str,
            tool_name: str,
            args: dict[str, Any],
            absence: str | None = None,
        ) -> Any:
            """Call a sub-tool, sorting a real fault from a negative answer.

            `absence` names what a not-found response means for this lookup.
            PubChem answers a name it does not hold with HTTP 404, which is the
            expected reply for an antibody rather than a broken service; filing
            it under failures would inflate the count and imply the profile was
            degraded when nothing was missing.
            """
            queried.append(source)
            try:
                r = tu.run_one_function({"name": tool_name, "arguments": args})
            except Exception as e:  # never propagate out of run()
                failed.append(f"{source}: {_truncate_msg(str(e))}")
                return None
            if isinstance(r, dict) and r.get("status") == "error":
                message = str(r.get("error", "unknown error"))
                if absence and _is_not_found(message):
                    skipped.append(f"{source}: {absence}")
                else:
                    failed.append(f"{source}: {_truncate_msg(message)}")
                return None
            return r

        resolved = self._resolve(call, note, drug)
        if not resolved["chembl_id"] and not resolved["pubchem_cid"]:
            return {
                "status": "error",
                "error": (
                    f"Could not resolve '{drug}' to a ChEMBL id or PubChem CID. "
                    "Check the spelling, or pass a ChEMBL id directly."
                ),
            }

        data: dict[str, Any] = {
            "query": {"drug": drug, **resolved},
            "sources_queried": [],
            "sources_failed": failed,
            "sources_skipped": skipped,
        }

        # Fetch a record only when a requested section reads it. Fetching both
        # unconditionally meant asking for 'mechanism' alone still paid for the
        # ChEMBL molecule and the PubChem property lookup, neither of which it
        # uses.
        wants_chembl, wants_pubchem = _records_needed(sections)
        chembl = (
            self._chembl_record(call, resolved["chembl_id"])
            if resolved["chembl_id"] and wants_chembl
            else {}
        )
        pubchem = (
            self._pubchem_record(call, resolved["pubchem_cid"])
            if resolved["pubchem_cid"] and wants_pubchem
            else {}
        )

        if (
            resolved["name_match"] == "identifier"
            and wants_chembl
            and not chembl
            and not resolved["pubchem_cid"]
        ):
            # Every field would be null and every count zero, which reads as a
            # drug with no properties rather than an identifier nothing knows.
            return {
                "status": "error",
                "error": (
                    f"'{drug}' is not a ChEMBL id any of the databases hold. "
                    "Check the identifier, or pass the drug name instead."
                ),
            }

        if "identity" in sections:
            data["identity"] = self._identity(chembl, resolved)
        if "structure" in sections:
            data["structure"] = self._structure(chembl, pubchem)
        if "mechanism" in sections:
            data["mechanism"] = self._mechanism(call, note, resolved["chembl_id"])
        if "indications" in sections:
            data["indications"] = self._indications(call, note, resolved["chembl_id"])
        if "safety" in sections:
            data["safety"] = self._safety(call, note, chembl, resolved["chembl_id"])

        data["sources_queried"] = sorted(set(queried))
        data["disclosure_notes"] = self._notes(data, resolved, sections)
        return {"status": "success", "data": data}

    # -------------------------------------------------------------- resolution

    def _resolve(self, call, note, drug: str) -> dict[str, Any]:
        """Map the input to a ChEMBL id, a PubChem CID and an RxCUI."""
        out: dict[str, Any] = {
            "chembl_id": None,
            "pubchem_cid": None,
            "rxcui": None,
            "resolved_name": None,
            "name_match": None,
        }

        if CHEMBL_ID.match(drug):
            out["chembl_id"] = drug.upper()
            out["name_match"] = "identifier"
        else:
            r = call(
                "opentargets",
                "OpenTargets_get_drug_chembId_by_generic_name",
                {"drugName": drug},
            )
            hits = ((r or {}).get("data", {}).get("search", {}) or {}).get("hits", [])
            hits = [h for h in hits if isinstance(h, dict) and h.get("id")]
            # Relevance order is not identity: take a hit as exact only when its
            # name matches, otherwise say which drug was profiled instead.
            exact = [
                h
                for h in hits
                if str(h.get("name", "")).strip().lower() == drug.lower()
            ]
            chosen = exact[0] if exact else (hits[0] if hits else None)
            if chosen:
                out["chembl_id"] = chosen.get("id")
                out["resolved_name"] = chosen.get("name")
                out["name_match"] = "exact" if exact else "nearest"

            cid = call(
                "pubchem",
                "PubChem_get_CID_by_compound_name",
                {"name": drug},
                absence=(
                    "PubChem holds no compound under this name, which is the "
                    "normal answer for an antibody or other biologic"
                ),
            )
            cids = (
                ((cid or {}).get("data", {}) or {}).get("IdentifierList", {}) or {}
            ).get("CID", [])
            if cids:
                out["pubchem_cid"] = cids[0]

            # A nearest match with nothing to corroborate it is a guess, not a
            # substitution. OpenTargets always answers something: 'as"pirin'
            # returns FLUTICASONE PROPIONATE and '2244' — which a caller could
            # easily paste thinking it a PubChem CID — returns BI-224436. What
            # separates those from a real brand name is that Tylenol and
            # adrenaline also resolve in PubChem, and they do not.
            if out["name_match"] == "nearest" and not out["pubchem_cid"]:
                out["name_match"] = "unverified"

            rx = call(
                "rxnorm",
                "RxNorm_find_rxcui",
                {"drug_name": drug},
                absence="RxNorm holds no clinical drug under this name",
            )
            rxd = (rx or {}).get("data") or {}
            if rxd.get("primary_rxcui"):
                out["rxcui"] = str(rxd["primary_rxcui"])

        if CHEMBL_ID.match(drug):
            note(
                "pubchem",
                "a ChEMBL id was supplied, so no name was available to look up a "
                "PubChem CID; pass the drug name to include PubChem",
            )
            note(
                "rxnorm",
                "a ChEMBL id was supplied, so no name was available to look up an "
                "RxCUI; pass the drug name to include RxNorm",
            )
        return out

    # ------------------------------------------------------------------ record

    def _chembl_record(self, call, chembl_id: str) -> dict[str, Any]:
        r = call("chembl", "ChEMBL_get_molecule", {"chembl_id": chembl_id})
        return (r or {}).get("data") or {}

    def _pubchem_record(self, call, cid: Any) -> dict[str, Any]:
        r = call(
            "pubchem",
            "PubChem_get_compound_properties_by_CID",
            {"cid": int(cid), "properties": _PUBCHEM_PROPERTIES},
        )
        props = (((r or {}).get("data", {}) or {}).get("PropertyTable", {}) or {}).get(
            "Properties", []
        )
        return props[0] if props and isinstance(props[0], dict) else {}

    # ---------------------------------------------------------------- sections

    def _identity(self, chembl: dict, resolved: dict) -> dict[str, Any]:
        synonyms = [
            s.get("molecule_synonym")
            for s in (chembl.get("molecule_synonyms") or [])
            if isinstance(s, dict) and s.get("molecule_synonym")
        ]
        deduped = list(dict.fromkeys(synonyms))
        return {
            "preferred_name": chembl.get("pref_name") or resolved.get("resolved_name"),
            "molecule_type": chembl.get("molecule_type"),
            "first_approval": _as_number(chembl.get("first_approval")),
            "max_phase": _as_number(chembl.get("max_phase")),
            "withdrawn": chembl.get("withdrawn_flag"),
            "atc_classifications": chembl.get("atc_classifications") or [],
            "synonyms": deduped[: self.SYNONYMS_CAP],
            "synonyms_truncated": len(deduped) > self.SYNONYMS_CAP,
        }

    def _structure(self, chembl: dict, pubchem: dict) -> dict[str, Any]:
        structures = chembl.get("molecule_structures") or {}
        props = chembl.get("molecule_properties") or {}
        chembl_key = structures.get("standard_inchi_key")
        pubchem_key = pubchem.get("InChIKey")
        return {
            "formula": props.get("full_molformula") or pubchem.get("MolecularFormula"),
            "molecular_weight": _as_number(
                props.get("full_mwt") or pubchem.get("MolecularWeight")
            ),
            "smiles": structures.get("canonical_smiles")
            or pubchem.get("ConnectivitySMILES"),
            "inchikey": chembl_key or pubchem_key,
            "iupac_name": pubchem.get("IUPACName"),
            # The two resolutions are independent, so this is the check that they
            # landed on the same molecule rather than two different ones.
            "inchikey_agreement": (
                None if not (chembl_key and pubchem_key) else chembl_key == pubchem_key
            ),
        }

    def _mechanism(self, call, note, chembl_id: str | None) -> list[dict[str, Any]]:
        if not chembl_id:
            note("opentargets", "mechanism of action is keyed by ChEMBL id")
            return []
        r = call(
            "opentargets",
            "OpenTargets_get_drug_mechanisms_of_action_by_chemblId",
            {"chemblId": chembl_id},
        )
        rows = (((r or {}).get("data", {}) or {}).get("drug", {}) or {}).get(
            "mechanismsOfAction", {}
        ) or {}
        out = []
        for row in (rows.get("rows") or [])[: self.MECHANISMS_CAP]:
            if not isinstance(row, dict):
                continue
            out.append(
                {
                    "mechanism_of_action": row.get("mechanismOfAction"),
                    "action_type": row.get("actionType"),
                    "target_name": row.get("targetName"),
                    "targets": [
                        {
                            "ensembl_gene": t.get("id"),
                            "symbol": t.get("approvedSymbol"),
                        }
                        for t in (row.get("targets") or [])
                        if isinstance(t, dict)
                    ],
                }
            )
        return out

    @staticmethod
    def _indication_block(response) -> dict[str, Any]:
        return (((response or {}).get("data", {}) or {}).get("drug", {}) or {}).get(
            "indications", {}
        ) or {}

    def _indications(self, call, note, chembl_id: str | None) -> dict[str, Any]:
        """Lead with the approved uses, and count the rest.

        The all-indications endpoint returns every disease a drug has ever been
        studied in, in no particular order: aspirin's 186 rows begin with sudden
        sensorineural hearing loss, and myocardial infarction is second. Slicing
        that list yields an arbitrary subset, not the important ones. The
        approved endpoint answers the question a caller usually means — what is
        this drug actually for — and aspirin's begins with myocardial infarction.
        """
        if not chembl_id:
            note("opentargets", "indications are keyed by ChEMBL id")
            return {
                "approved_count": None,
                "approved": [],
                "truncated": False,
                "total_investigated_count": None,
            }

        approved = self._indication_block(
            call(
                "opentargets",
                "OpenTargets_get_approved_indications_by_drug_chemblId",
                {"chemblId": chembl_id},
            )
        )
        investigated = self._indication_block(
            call(
                "opentargets",
                "OpenTargets_get_drug_indications_by_chemblId",
                {"chemblId": chembl_id},
            )
        )

        rows = approved.get("rows") or []
        shown = []
        for row in rows[: self.INDICATIONS_CAP]:
            disease = (row or {}).get("disease") or {}
            if disease.get("name"):
                shown.append(
                    {"disease": disease.get("name"), "disease_id": disease.get("id")}
                )
        return {
            "approved_count": approved.get("count"),
            "approved": shown,
            "truncated": bool(approved.get("truncated")) or len(rows) > len(shown),
            # Everything the drug has been studied in, approved or not.
            "total_investigated_count": investigated.get("count"),
        }

    def _safety(
        self, call, note, chembl: dict, chembl_id: str | None
    ) -> dict[str, Any]:
        # ChEMBL carries a boxed-warning flag and OpenTargets the warning rows,
        # so the two can be compared rather than either taken on trust.
        flag = chembl.get("black_box_warning")
        chembl_flag = None if flag is None else bool(int(flag))

        warnings: list[dict[str, Any]] = []
        # Whether the warnings were actually looked up. An empty list means two
        # very different things — none recorded, or the lookup never answered —
        # and reporting a count of 0 for the second is an assertion about drug
        # safety that nothing supports.
        checked = False
        if chembl_id:
            r = call(
                "opentargets",
                "OpenTargets_get_drug_warnings_by_chemblId",
                {"chemblId": chembl_id},
            )
            checked = r is not None
            rows = (((r or {}).get("data", {}) or {}).get("drug", {}) or {}).get(
                "drugWarnings"
            )
            # Absent rather than empty when a drug has no recorded warning; that
            # is an answer, not a failure.
            for row in rows or []:
                if isinstance(row, dict):
                    warnings.append(
                        {
                            "warning_type": row.get("warningType"),
                            "toxicity_class": row.get("toxicityClass"),
                            "country": row.get("country"),
                        }
                    )
        else:
            note("opentargets", "drug warnings are keyed by ChEMBL id")

        boxed = [w for w in warnings if w.get("warning_type") == "Black Box Warning"]
        return {
            "chembl_black_box_flag": chembl_flag,
            "warnings_checked": checked,
            "opentargets_warnings": warnings,
            "boxed_warning_count": len(boxed) if checked else None,
            "withdrawn": chembl.get("withdrawn_flag"),
            "sources_agree_on_boxed_warning": (
                None
                if chembl_flag is None or not checked
                else chembl_flag == bool(boxed)
            ),
        }

    # ------------------------------------------------------------------ output

    def _notes(self, data: dict, resolved: dict, sections) -> list[str]:
        """State every reason the profile above could be misread."""
        notes: list[str] = []

        if resolved.get("name_match") == "nearest":
            notes.append(
                f"No drug is named exactly '{data['query']['drug']}' in OpenTargets; "
                f"this profile is for '{resolved.get('resolved_name')}' "
                f"({resolved.get('chembl_id')}), its closest match. PubChem "
                "independently resolved the same name, which supports the "
                "substitution, but confirm it is the drug you meant."
            )
        elif resolved.get("name_match") == "unverified":
            notes.append(
                f"'{data['query']['drug']}' matched no drug by name, and this "
                f"profile is for '{resolved.get('resolved_name')}' "
                f"({resolved.get('chembl_id')}) only because OpenTargets' "
                "relevance-ranked search returns a best guess for any string. "
                "PubChem found nothing under this name, so nothing corroborates "
                "the guess. Treat the whole profile as unidentified until you "
                "confirm it — a typo or a stray identifier resolves to an "
                "unrelated drug this way."
            )

        structure = data.get("structure") or {}
        if structure.get("inchikey_agreement") is False:
            notes.append(
                "ChEMBL and PubChem returned different InChIKeys, so the name "
                "resolved to two different molecules and this profile mixes them. "
                "Treat every field as unreliable and resolve the drug explicitly."
            )
        elif "structure" in sections and structure.get("inchikey_agreement") is None:
            notes.append(
                "Only one of ChEMBL and PubChem supplied an InChIKey, so there was "
                "no cross-check that both resolved to the same molecule."
            )

        safety = data.get("safety") or {}
        if safety.get("sources_agree_on_boxed_warning") is False:
            notes.append(
                f"ChEMBL's boxed-warning flag ({safety.get('chembl_black_box_flag')}) "
                f"disagrees with OpenTargets, which returned "
                f"{safety.get('boxed_warning_count')} boxed warning(s). The two "
                "curate from different label snapshots; check the label itself "
                "before relying on either."
            )
        if "safety" in sections and not safety.get("warnings_checked"):
            notes.append(
                "The warnings lookup did not answer, so nothing here says whether "
                "this drug carries a boxed warning. 'boxed_warning_count' is null "
                "rather than 0 for that reason; do not read the empty list as a "
                "clean safety record."
            )
        elif "safety" in sections and not safety.get("opentargets_warnings"):
            notes.append(
                "An empty warning list means OpenTargets records no warning for "
                "this drug, not that the lookup failed — a failed lookup appears "
                "in 'sources_failed'. It is not evidence the drug is safe."
            )

        indications = data.get("indications") or {}
        if indications.get("truncated"):
            notes.append(
                f"Approved indications were cut to {self.INDICATIONS_CAP}; "
                f"'approved_count' ({indications.get('approved_count')}) is "
                "upstream's own total, so absence from 'approved' is not evidence "
                "a use is not recorded."
            )
        approved_n = indications.get("approved_count")
        total_n = indications.get("total_investigated_count")
        if approved_n is not None and total_n is not None and total_n > approved_n:
            notes.append(
                f"'approved' lists the {approved_n} indication(s) that reached "
                f"approval. 'total_investigated_count' is {total_n}, which counts "
                "every disease the drug has been studied in at any phase — being "
                "in that larger set is not evidence of efficacy or of approval."
            )

        if data.get("sources_failed"):
            notes.append(
                f"{len(data['sources_failed'])} source(s) failed; the sections they "
                "feed are missing rather than empty. Read 'sources_failed' before "
                "reading an absent field as a negative finding."
            )
        return notes
