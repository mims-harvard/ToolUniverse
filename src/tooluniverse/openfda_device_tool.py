# openfda_device_tool.py
"""
openFDA medical device tool for ToolUniverse.

ToolUniverse's existing openFDA tools cover only the drug endpoints
(drug/event, drug/label, drug/drugsfda); the device side had no coverage
at all. Covers recalls, MAUDE (Manufacturer and User Facility Device
Experience) adverse event reports, the UDI (Unique Device Identifier)
database, regulatory classification, and both premarket pathways --
510(k) notification and PMA (premarket approval) for higher-risk
devices. These are a genuinely different record schema (device brand/
generic name, recall classification and root cause, patient problem
codes, regulatory clearance numbers) from the drug-adverse-event tools,
not a parameter variation of them.

A bare `search=<term>` full-text query was verified to discriminate
correctly (a nonsense term returns a clean 404 "no matches", not an
inflated count) before building this, given this exact codebase's own
git history documents prior openFDA quoting/exactness bugs.

API: https://api.fda.gov/device
No authentication required (optional api_key raises the rate limit).
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

RECALL_URL = "https://api.fda.gov/device/recall.json"
EVENT_URL = "https://api.fda.gov/device/event.json"
UDI_URL = "https://api.fda.gov/device/udi.json"
CLASSIFICATION_URL = "https://api.fda.gov/device/classification.json"
K510_URL = "https://api.fda.gov/device/510k.json"
PMA_URL = "https://api.fda.gov/device/pma.json"

# A MAUDE report's narrative is the report. Several of them can hang off one
# report -- the reporter's description, the manufacturer's additional
# narrative, the evaluation summary -- and they can run long, so the count is
# capped and the cut is disclosed per row.
NARRATIVES_PER_REPORT = 10
NARRATIVE_CHARACTERS = 4000


def _openfda_ids(record: Dict[str, Any]) -> Dict[str, Any]:
    """The clearance and registration numbers openFDA attaches to a record.

    These are the keys the device endpoints take as input, so a result
    without them cannot be followed: a recall names a firm and a reason, and
    the `k_number`/`pma_number` that say which clearance the recalled device
    was sold under, and the `registration_number`/`fei_number` that identify
    the establishment, were all in the same record and none of them reached
    the caller.
    """
    openfda = record.get("openfda") or {}
    return {
        "k_numbers": openfda.get("k_number") or record.get("k_numbers") or [],
        "pma_numbers": openfda.get("pma_number") or record.get("pma_numbers") or [],
        "registration_numbers": openfda.get("registration_number") or [],
        "fei_numbers": openfda.get("fei_number") or [],
        "device_name": openfda.get("device_name"),
        "device_class": openfda.get("device_class"),
        "regulation_number": openfda.get("regulation_number"),
        "medical_specialty_description": openfda.get("medical_specialty_description"),
    }


def _mdr_texts(record: Dict[str, Any]) -> tuple:
    """`(narratives, total, truncated)` for one MAUDE report.

    The narrative was dropped outright. A MAUDE row told the caller the brand
    name, the event type and a list of problem codes -- and not what happened,
    which is what the report was written to say.
    """
    rows = [t for t in (record.get("mdr_text") or []) if isinstance(t, dict)]
    kept = []
    for text in rows[:NARRATIVES_PER_REPORT]:
        body = text.get("text") or ""
        kept.append(
            {
                "text_type": text.get("text_type_code"),
                "text": body[:NARRATIVE_CHARACTERS],
                "text_truncated": len(body) > NARRATIVE_CHARACTERS,
                "text_length": len(body),
                "patient_sequence_number": text.get("patient_sequence_number"),
                "mdr_text_key": text.get("mdr_text_key"),
            }
        )
    return kept, len(rows), len(rows) > NARRATIVES_PER_REPORT


@register_tool("OpenFDADeviceTool")
class OpenFDADeviceTool(BaseTool):
    """
    Tool for querying openFDA's medical device recall and adverse event
    (MAUDE) data.

    Supports searching device recalls (reason, root cause, recalling
    firm), MAUDE adverse event reports (device, event type, patient
    problems), the UDI database, regulatory classification, and 510(k)/
    PMA premarket clearances, all by device name.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_recalls"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the openFDA device lookup."""
        try:
            if self.operation == "search_recalls":
                return self._search_recalls(arguments)
            if self.operation == "search_adverse_events":
                return self._search_adverse_events(arguments)
            if self.operation == "search_udi":
                return self._search_udi(arguments)
            if self.operation == "get_classification":
                return self._get_classification(arguments)
            if self.operation == "search_510k":
                return self._search_510k(arguments)
            if self.operation == "search_pma":
                return self._search_pma(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"openFDA request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to openFDA. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"openFDA returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "openFDA returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying openFDA: {str(e)}"}

    def _search_recalls(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search medical device recalls by device name or free text."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'pacemaker' or a "
                "recalling firm name.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            RECALL_URL, params={"search": query, "limit": limit}, timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No device recalls matching '{query}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = [
            {
                "product_description": r.get("product_description"),
                "recalling_firm": r.get("recalling_firm"),
                "reason_for_recall": r.get("reason_for_recall"),
                "root_cause_description": r.get("root_cause_description"),
                "recall_status": r.get("recall_status"),
                "event_date_initiated": r.get("event_date_initiated"),
                "action": r.get("action"),
                # Which units are affected. A recall that names the firm and
                # the reason and not the models and serial numbers cannot be
                # acted on -- "MODEL H170 SERIAL 364359 364362 ..." was in the
                # same record.
                "code_info": r.get("code_info"),
                "product_quantity": r.get("product_quantity"),
                "distribution_pattern": r.get("distribution_pattern"),
                # The dates that say whether this is live. `recall_status`
                # alone does not: a terminated recall and an ongoing one read
                # the same without the posted and terminated dates.
                "event_date_posted": r.get("event_date_posted"),
                "event_date_terminated": r.get("event_date_terminated"),
                # openFDA's own identifiers for the recall event, which is how
                # the several product records of one recall are recognised as
                # one event.
                "cfres_id": r.get("cfres_id"),
                "product_res_number": r.get("product_res_number"),
                "res_event_number": r.get("res_event_number"),
                "product_code": r.get("product_code"),
                "firm_fei_number": r.get("firm_fei_number"),
                "additional_info_contact": r.get("additional_info_contact"),
                "recalling_firm_address": {
                    "address_1": r.get("address_1"),
                    "city": r.get("city"),
                    "state": r.get("state"),
                    "postal_code": r.get("postal_code"),
                },
                "identifiers": _openfda_ids(r),
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "source": "openFDA device/recall",
            },
        }

    def _search_adverse_events(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search MAUDE device adverse event reports by device name."""
        device_name = (arguments.get("device_name") or "").strip()
        if not device_name:
            return {
                "status": "error",
                "error": "device_name is required, e.g. 'pacemaker' or "
                "'insulin pump'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            EVENT_URL,
            params={
                "search": f"device.generic_name:{device_name}",
                "limit": limit,
            },
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No MAUDE adverse event reports for device "
                f"'{device_name}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows: List[Dict[str, Any]] = []
        for r in results:
            devices = [d for d in (r.get("device") or []) if isinstance(d, dict)]
            device = devices[0] if devices else {}
            patients = [p for p in (r.get("patient") or []) if isinstance(p, dict)]
            patient_problems: List[str] = []
            for p in patients:
                patient_problems.extend(p.get("patient_problems") or [])
            narratives, narrative_total, narratives_cut = _mdr_texts(r)
            rows.append(
                {
                    "brand_name": device.get("brand_name"),
                    "generic_name": device.get("generic_name"),
                    "manufacturer": device.get("manufacturer_d_name"),
                    "event_type": r.get("event_type"),
                    "date_of_event": r.get("date_of_event"),
                    "product_problems": r.get("product_problems") or [],
                    "patient_problems": sorted(set(patient_problems)),
                    # What happened. The narratives are the report; the row
                    # used to carry the brand name, the event type and a list
                    # of problem codes and nothing of what was written.
                    "narratives": narratives,
                    "narrative_count": narrative_total,
                    "narratives_truncated": narratives_cut,
                    # The report's own identifiers, without which a MAUDE row
                    # cannot be looked up or cited, and the dates and
                    # provenance that say what kind of report it is: an
                    # initial submission from a physician is not a
                    # manufacturer's follow-up.
                    "report_number": r.get("report_number"),
                    "mdr_report_key": r.get("mdr_report_key"),
                    "date_received": r.get("date_received"),
                    "date_report": r.get("date_report"),
                    "date_manufacturer_received": r.get("date_manufacturer_received"),
                    "date_changed": r.get("date_changed"),
                    "date_added": r.get("date_added"),
                    "source_type": r.get("source_type") or [],
                    "type_of_report": r.get("type_of_report") or [],
                    "report_source_code": r.get("report_source_code"),
                    "reporter_occupation_code": r.get("reporter_occupation_code"),
                    "reporter_country_code": r.get("reporter_country_code"),
                    "reporter_state_code": r.get("reporter_state_code"),
                    "event_location": r.get("event_location"),
                    "remedial_action": r.get("remedial_action") or [],
                    "adverse_event_flag": r.get("adverse_event_flag"),
                    "product_problem_flag": r.get("product_problem_flag"),
                    "pma_pmn_number": r.get("pma_pmn_number"),
                    # Every device on the report, not only the first. A MAUDE
                    # report can name several, and `number_devices_in_event`
                    # is often blank, so the one that was reported looked like
                    # the only one.
                    "devices": [
                        {
                            "brand_name": d.get("brand_name"),
                            "generic_name": d.get("generic_name"),
                            "manufacturer": d.get("manufacturer_d_name"),
                            "model_number": d.get("model_number"),
                            "catalog_number": d.get("catalog_number"),
                            "lot_number": d.get("lot_number"),
                            "device_report_product_code": d.get(
                                "device_report_product_code"
                            ),
                            "device_sequence_number": d.get("device_sequence_number"),
                            "device_operator": d.get("device_operator"),
                            "device_age_text": d.get("device_age_text"),
                            "implant_flag": d.get("implant_flag"),
                            # When it was implanted, which with the event date
                            # is how long the device had been in service.
                            "implant_date_year": d.get("implant_date_year"),
                            "date_removed_year": d.get("date_removed_year"),
                            "manufacturer_address": {
                                "address_1": d.get("manufacturer_d_address_1"),
                                "address_2": d.get("manufacturer_d_address_2"),
                                "city": d.get("manufacturer_d_city"),
                                "state": d.get("manufacturer_d_state"),
                                "country": d.get("manufacturer_d_country"),
                                "postal_code": d.get("manufacturer_d_postal_code"),
                            },
                            "device_evaluated_by_manufacturer": d.get(
                                "device_evaluated_by_manufacturer"
                            ),
                            "device_availability": d.get("device_availability"),
                            "expiration_date_of_device": d.get(
                                "expiration_date_of_device"
                            ),
                            # The device's own clearance and establishment
                            # numbers, which is how a report is followed to
                            # the 510(k) or PMA the device was sold under.
                            "identifiers": _openfda_ids(d),
                        }
                        for d in devices
                    ],
                    "device_count": len(devices),
                    # And every patient, with the outcome and the treatment
                    # given -- which is the difference between a malfunction
                    # and an injury.
                    "patients": [
                        {
                            "patient_sequence_number": p.get(
                                "patient_sequence_number"
                            ),
                            "patient_age": p.get("patient_age"),
                            "patient_sex": p.get("patient_sex"),
                            "patient_weight": p.get("patient_weight"),
                            "patient_problems": p.get("patient_problems") or [],
                            "sequence_number_outcome": p.get(
                                "sequence_number_outcome"
                            )
                            or [],
                            "sequence_number_treatment": p.get(
                                "sequence_number_treatment"
                            )
                            or [],
                        }
                        for p in patients
                    ],
                    "patient_count": len(patients),
                }
            )

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "device_name": device_name,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "source": "openFDA device/event (MAUDE)",
            },
        }

    def _search_udi(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search the Unique Device Identifier (UDI) database."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'pacemaker' or a "
                "company name.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            UDI_URL, params={"search": query, "limit": limit}, timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No UDI records matching '{query}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = []
        for r in results:
            product_codes = r.get("product_codes") or [{}]
            first_code = product_codes[0] if product_codes else {}
            identifiers = r.get("identifiers") or []
            gmdn_terms = r.get("gmdn_terms") or []
            rows.append(
                {
                    "brand_name": r.get("brand_name"),
                    "company_name": r.get("company_name"),
                    "device_description": r.get("device_description"),
                    "primary_di": next(
                        (
                            i.get("id")
                            for i in identifiers
                            if i.get("type") == "Primary"
                        ),
                        None,
                    ),
                    # The GMDN term's name is what a reader wants and its
                    # code is what another system will match on; the
                    # definition is a paragraph saying what the class of
                    # device IS, and `code_status` says whether the term is
                    # still active. Only the name used to come back.
                    "gmdn_terms": [
                        {
                            "name": g.get("name"),
                            "code": g.get("code"),
                            "code_status": g.get("code_status"),
                            "definition": g.get("definition"),
                            "implantable": g.get("implantable"),
                        }
                        for g in gmdn_terms
                        if isinstance(g, dict)
                    ],
                    "device_class": (first_code.get("openfda") or {}).get(
                        "device_class"
                    ),
                    "commercial_distribution_status": r.get(
                        "commercial_distribution_status"
                    ),
                    # Every identifier, not only the Primary one. A package DI
                    # or a secondary DI is what a scanned barcode will match,
                    # and each carries the agency that issued it.
                    "identifiers": [
                        {
                            "id": i.get("id"),
                            "type": i.get("type"),
                            "issuing_agency": i.get("issuing_agency"),
                            "package_discontinue_date": i.get(
                                "package_discontinue_date"
                            ),
                            "package_status": i.get("package_status"),
                            "package_type": i.get("package_type"),
                            "quantity_per_package": i.get("quantity_per_package"),
                            "unit_of_use_id": i.get("unit_of_use_id"),
                        }
                        for i in identifiers
                        if isinstance(i, dict)
                    ],
                    "version_or_model_number": r.get("version_or_model_number"),
                    # The labelling flags. These are the questions asked of a
                    # device at the point of use, and the UDI record answers
                    # all of them: whether it is sterile, whether it is safe
                    # near an MRI, whether it contains natural rubber latex,
                    # whether it is prescription-only and single-use.
                    "sterilization": r.get("sterilization"),
                    "mri_safety": r.get("mri_safety"),
                    "is_labeled_as_nrl": r.get("is_labeled_as_nrl"),
                    "is_labeled_as_no_nrl": r.get("is_labeled_as_no_nrl"),
                    "is_rx": r.get("is_rx"),
                    "is_otc": r.get("is_otc"),
                    "is_single_use": r.get("is_single_use"),
                    "is_kit": r.get("is_kit"),
                    "is_combination_product": r.get("is_combination_product"),
                    "is_hct_p": r.get("is_hct_p"),
                    "is_pm_exempt": r.get("is_pm_exempt"),
                    "is_direct_marking_exempt": r.get("is_direct_marking_exempt"),
                    "has_lot_or_batch_number": r.get("has_lot_or_batch_number"),
                    "has_serial_number": r.get("has_serial_number"),
                    "has_expiration_date": r.get("has_expiration_date"),
                    "has_manufacturing_date": r.get("has_manufacturing_date"),
                    "has_donation_id_number": r.get("has_donation_id_number"),
                    "storage": r.get("storage") or [],
                    "device_sizes": r.get("device_sizes") or [],
                    "device_count_in_base_package": r.get(
                        "device_count_in_base_package"
                    ),
                    "customer_contacts": r.get("customer_contacts") or [],
                    "premarket_submissions": r.get("premarket_submissions") or [],
                    # Which version of the record this is, and whether it is
                    # the published one.
                    "record_status": r.get("record_status"),
                    "public_version_status": r.get("public_version_status"),
                    "public_version_number": r.get("public_version_number"),
                    "public_version_date": r.get("public_version_date"),
                    "public_device_record_key": r.get("public_device_record_key"),
                    "publish_date": r.get("publish_date"),
                    "labeler_duns_number": r.get("labeler_duns_number"),
                    "commercial_distribution_end_date": r.get(
                        "commercial_distribution_end_date"
                    ),
                    # All the product codes, each with its own classification,
                    # rather than the device class of whichever came first.
                    "product_codes": [
                        {
                            "code": c.get("code"),
                            "name": c.get("name"),
                            "openfda": _openfda_ids(c),
                        }
                        for c in (r.get("product_codes") or [])
                        if isinstance(c, dict)
                    ],
                }
            )

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "source": "openFDA device/udi",
            },
        }

    def _get_classification(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search device regulatory classification by device name."""
        device_name = (arguments.get("device_name") or "").strip()
        if not device_name:
            return {
                "status": "error",
                "error": "device_name is required, e.g. 'pacemaker'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            CLASSIFICATION_URL,
            params={"search": f"device_name:{device_name}", "limit": limit},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No device classification found for "
                f"'{device_name}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = [
            {
                "device_name": r.get("device_name"),
                "product_code": r.get("product_code"),
                "device_class": r.get("device_class"),
                "review_panel": r.get("review_panel"),
                "medical_specialty_description": r.get(
                    "medical_specialty_description"
                ),
                "regulation_number": r.get("regulation_number"),
                "third_party_flag": r.get("third_party_flag"),
                # What the classification actually says about the device, as
                # against which panel reviews it: whether it is implanted,
                # whether it is life-sustaining, whether GMP applies, and
                # what the regulation defines it as.
                "definition": r.get("definition"),
                "implant_flag": r.get("implant_flag"),
                "life_sustain_support_flag": r.get("life_sustain_support_flag"),
                "gmp_exempt_flag": r.get("gmp_exempt_flag"),
                "submission_type_id": r.get("submission_type_id"),
                "summary_malfunction_reporting": r.get(
                    "summary_malfunction_reporting"
                ),
                "unclassified_reason": r.get("unclassified_reason"),
                "medical_specialty": r.get("medical_specialty"),
                "device_id": r.get("device_id"),
                # The clearances and establishments registered under this
                # product code, which is how a classification is followed to
                # the devices that carry it.
                "identifiers": _openfda_ids(r),
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "device_name": device_name,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "note": "device_class: 1 = general controls, 2 = special "
                "controls, 3 = premarket approval.",
                "source": "openFDA device/classification",
            },
        }

    def _search_510k(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search 510(k) premarket notification clearances."""
        device_name = (arguments.get("device_name") or "").strip()
        if not device_name:
            return {
                "status": "error",
                "error": "device_name is required, e.g. 'pacemaker'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            K510_URL,
            params={"search": f"device_name:{device_name}", "limit": limit},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No 510(k) clearances found for '{device_name}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = [
            {
                "k_number": r.get("k_number"),
                "device_name": r.get("device_name"),
                "applicant": r.get("applicant"),
                "decision_date": r.get("decision_date"),
                "decision_description": r.get("decision_description"),
                "clearance_type": r.get("clearance_type"),
                "advisory_committee_description": r.get(
                    "advisory_committee_description"
                ),
                "decision_code": r.get("decision_code"),
                "date_received": r.get("date_received"),
                "product_code": r.get("product_code"),
                "advisory_committee": r.get("advisory_committee"),
                "review_advisory_committee": r.get("review_advisory_committee"),
                "third_party_flag": r.get("third_party_flag"),
                "expedited_review_flag": r.get("expedited_review_flag"),
                "statement_or_summary": r.get("statement_or_summary"),
                # Who the applicant is, which for a clearance search is part
                # of identifying the device: two firms can clear devices of
                # the same name.
                "applicant_address": {
                    "address_1": r.get("address_1"),
                    "address_2": r.get("address_2"),
                    "city": r.get("city"),
                    "state": r.get("state"),
                    "country_code": r.get("country_code"),
                    "zip_code": r.get("zip_code"),
                    "postal_code": r.get("postal_code"),
                    "contact": r.get("contact"),
                },
                "identifiers": _openfda_ids(r),
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "device_name": device_name,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "source": "openFDA device/510k",
            },
        }

    def _search_pma(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search premarket approval (PMA) applications for high-risk devices."""
        device_name = (arguments.get("device_name") or "").strip()
        if not device_name:
            return {
                "status": "error",
                "error": "device_name is required, e.g. 'defibrillator'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            PMA_URL,
            params={"search": f"trade_name:{device_name}", "limit": limit},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No PMA applications found for '{device_name}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = [
            {
                "pma_number": r.get("pma_number"),
                "trade_name": r.get("trade_name"),
                "applicant": r.get("applicant"),
                "decision_date": r.get("decision_date"),
                "ao_statement": r.get("ao_statement"),
                "advisory_committee_description": r.get(
                    "advisory_committee_description"
                ),
                # Which supplement this row is. A PMA number alone collapses
                # the original approval and every later change into one
                # answer, and `ao_statement` describes whichever row came
                # back; the supplement number, type and reason say which
                # decision is being read.
                "supplement_number": r.get("supplement_number"),
                "supplement_type": r.get("supplement_type"),
                "supplement_reason": r.get("supplement_reason"),
                "decision_code": r.get("decision_code"),
                "date_received": r.get("date_received"),
                "generic_name": r.get("generic_name"),
                "product_code": r.get("product_code"),
                "advisory_committee": r.get("advisory_committee"),
                "expedited_review_flag": r.get("expedited_review_flag"),
                "applicant_address": {
                    "street_1": r.get("street_1"),
                    "street_2": r.get("street_2"),
                    "city": r.get("city"),
                    "state": r.get("state"),
                    "zip": r.get("zip"),
                    "zip_ext": r.get("zip_ext"),
                },
                "identifiers": _openfda_ids(r),
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "device_name": device_name,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "note": "ao_statement summarizes the specific approval "
                "order/change, not the whole device history.",
                "source": "openFDA device/pma",
            },
        }
