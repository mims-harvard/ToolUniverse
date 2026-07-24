"""
ClinVar Submitted (per-submitter / SCV) Records Tool

The standard ClinVar tools (ClinVarSearchVariants / GetVariantDetails /
GetClinicalSignificance) use esearch/esummary and expose only the AGGREGATE
germline classification for a variant. They do NOT return the individual
submitter assertions (SCV / ClinicalAssertion records).

This tool fills that gap. It calls NCBI eutils efetch on the ``clinvar`` db
with ``rettype=vcv`` to retrieve the full ``VariationArchive`` XML, then parses
every ``ClinicalAssertion`` (SCV) so callers can see who submitted what
classification, with which review status and for which condition.

Keyless endpoint (verified live):
    https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
        ?db=clinvar&rettype=vcv&id=VCV000013961
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool


def _normalize_variant_id(raw: str) -> Optional[str]:
    """Normalize a user-supplied identifier to a VCV accession.

    Accepts:
      - A VCV accession (e.g. ``"VCV000013961"`` or lowercase ``"vcv13961"``)
      - A bare ClinVar variation id (e.g. ``"13961"`` or ``13961``)

    Bare numeric ids are zero-padded to the ``VCV%09d`` form. Returns ``None``
    when the input cannot be interpreted as either form.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None

    upper = text.upper()
    if upper.startswith("VCV"):
        digits = upper[3:]
        if digits.isdigit():
            return "VCV{:09d}".format(int(digits))
        return None

    if text.isdigit():
        return "VCV{:09d}".format(int(text))

    return None


def _first_preferred_condition(trait_set: Optional[ET.Element]) -> Optional[str]:
    """Extract the condition name from a ClinicalAssertion TraitSet.

    Prefers the ``Preferred`` ElementValue; falls back to the first available
    Name ElementValue. Returns ``None`` when no usable name is present (some
    traits carry only an XRef and no Name).
    """
    if trait_set is None:
        return None

    fallback = None
    for trait in trait_set.findall("Trait"):
        for name in trait.findall("Name"):
            element_value = name.find("ElementValue")
            if element_value is None or not (element_value.text or "").strip():
                continue
            value = element_value.text.strip()
            if element_value.get("Type") == "Preferred":
                return value
            if fallback is None:
                fallback = value
    return fallback


def _assertion_classification(
    classification: Optional[ET.Element],
) -> Dict[str, Optional[str]]:
    """Pull the classification value, type, review status and eval date from an SCV.

    A ClinicalAssertion carries exactly one of GermlineClassification,
    SomaticClinicalImpact or OncogenicityClassification. Note the SCV-level
    somatic tag is ``SomaticClinicalImpact`` (whose text is a tier such as
    "Tier I - Strong"), distinct from the aggregate-level
    ``SomaticClinicalImpactClassification`` tag.
    """
    empty = {
        "classification": None,
        "classification_type": None,
        "review_status": None,
        "last_evaluated": None,
    }
    if classification is None:
        return empty

    value = None
    classification_type = None
    for tag, label in (
        ("GermlineClassification", "germline"),
        ("SomaticClinicalImpact", "somatic_clinical_impact"),
        ("OncogenicityClassification", "oncogenicity"),
    ):
        element = classification.find(tag)
        if element is not None and (element.text or "").strip():
            value = element.text.strip()
            classification_type = label
            break

    return {
        "classification": value,
        "classification_type": classification_type,
        "review_status": classification.findtext("ReviewStatus"),
        "last_evaluated": classification.get("DateLastEvaluated"),
    }


def _aggregate_classification(
    classifications: Optional[ET.Element],
) -> Dict[str, Optional[str]]:
    """Pull the aggregate (record-level) classification from Classifications."""
    if classifications is None:
        return {"description": None, "review_status": None}

    for tag in (
        "GermlineClassification",
        "SomaticClinicalImpact",
        "OncogenicityClassification",
    ):
        block = classifications.find(tag)
        if block is not None:
            return {
                "description": block.findtext("Description"),
                "review_status": block.findtext("ReviewStatus"),
            }
    return {"description": None, "review_status": None}


@register_tool("ClinVarSubmittedRecordsTool")
class ClinVarSubmittedRecordsTool(BaseTool):
    """Return per-submitter (SCV / ClinicalAssertion) ClinVar records."""

    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.timeout = 30

    def run(
        self, arguments=None, stream_callback=None, use_cache=False, validate=True
    ) -> Dict[str, Any]:
        arguments = arguments or {}
        raw_id = arguments.get("variant_id")
        if raw_id is None or str(raw_id).strip() == "":
            return {
                "status": "error",
                "error": "Parameter 'variant_id' is required (a VCV accession "
                "like 'VCV000013961' or a bare ClinVar variation id like '13961').",
            }

        vcv = _normalize_variant_id(raw_id)
        if vcv is None:
            return {
                "status": "error",
                "error": (
                    f"Could not interpret variant_id={raw_id!r} as a VCV accession "
                    "or a numeric ClinVar variation id."
                ),
            }

        params = {"db": "clinvar", "rettype": "vcv", "id": vcv}
        try:
            response = requests.get(
                self.EFETCH_URL,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/1.0"},
            )
        except requests.exceptions.RequestException as exc:
            return {
                "status": "error",
                "error": f"Request to NCBI efetch failed: {exc}",
                "variant_id": vcv,
            }

        if response.status_code != 200:
            return {
                "status": "error",
                "error": (
                    f"NCBI efetch returned HTTP {response.status_code} for {vcv}."
                ),
                "variant_id": vcv,
            }

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            return {
                "status": "error",
                "error": f"Failed to parse ClinVar XML for {vcv}: {exc}",
                "variant_id": vcv,
            }

        variation_archive = root.find("VariationArchive")
        if variation_archive is None:
            return {
                "status": "error",
                "error": (
                    f"No VariationArchive found for {vcv}. The id may not exist "
                    "in ClinVar, or it may be a non-classified record."
                ),
                "variant_id": vcv,
            }

        return self._build_result(vcv, variation_archive)

    def _build_result(self, vcv: str, variation_archive: ET.Element) -> Dict[str, Any]:
        name = variation_archive.get("VariationName")
        variation_id = variation_archive.get("VariationID")

        # ClassifiedRecord holds the aggregate Classifications and the
        # per-submitter ClinicalAssertionList. IncludedRecord (sub-variants)
        # uses a different layout and has no ClinicalAssertionList.
        record = variation_archive.find("ClassifiedRecord")
        if record is None:
            record = variation_archive.find("IncludedRecord")

        aggregate = {"description": None, "review_status": None}
        submissions: List[Dict[str, Any]] = []
        if record is not None:
            aggregate = _aggregate_classification(record.find("Classifications"))
            submissions = self._parse_assertions(record.find("ClinicalAssertionList"))

        data = {
            "variation_id": variation_id,
            "vcv_accession": variation_archive.get("Accession") or vcv,
            "name": name,
            "aggregate_classification": aggregate["description"],
            "aggregate_review_status": aggregate["review_status"],
            "total_submissions": len(submissions),
            "submissions": submissions,
        }
        metadata = {
            "source": "NCBI ClinVar efetch (rettype=vcv)",
            "endpoint": self.EFETCH_URL,
            "queried_id": vcv,
            "number_of_submissions_reported": variation_archive.get(
                "NumberOfSubmissions"
            ),
            "number_of_submitters_reported": variation_archive.get(
                "NumberOfSubmitters"
            ),
            "date_last_updated": variation_archive.get("DateLastUpdated"),
        }
        return {"status": "success", "data": data, "metadata": metadata}

    @staticmethod
    def _parse_assertions(
        assertion_list: Optional[ET.Element],
    ) -> List[Dict[str, Any]]:
        if assertion_list is None:
            return []

        submissions: List[Dict[str, Any]] = []
        for assertion in assertion_list.findall("ClinicalAssertion"):
            accession = assertion.find("ClinVarAccession")
            classification = _assertion_classification(assertion.find("Classification"))
            scv_accession = None
            submitter = None
            if accession is not None:
                scv_accession = accession.get("Accession")
                version = accession.get("Version")
                if scv_accession and version:
                    scv_accession = f"{scv_accession}.{version}"
                submitter = accession.get("SubmitterName")

            submissions.append(
                {
                    "scv_accession": scv_accession,
                    "classification": classification["classification"],
                    "classification_type": classification["classification_type"],
                    "review_status": classification["review_status"],
                    "submitter": submitter,
                    "condition": _first_preferred_condition(assertion.find("TraitSet")),
                    "last_evaluated": classification["last_evaluated"],
                }
            )
        return submissions
