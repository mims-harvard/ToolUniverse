# Regulatory Pathway Notes: Drug vs Device

Ask which pathway applies before drafting Section 9 (and before choosing which tools to call in Sections 1, 5, and 8). Never assume — a combination product may need both.

## Drug / Biologic Pathway

1. **Identify the substance.** `FDAGSRS_search_substances` — resolve name/UNII/formula to a confirmed FDA substance record.
2. **Check existing approval status and generic landscape.** `FDA_OrangeBook_search_drug`, `FDA_OrangeBook_get_approval_history`, `FDA_OrangeBook_check_generic_availability`, `FDA_OrangeBook_get_exclusivity` — establishes whether this is a new molecular entity (505(b)(1)), a follow-on with a bridge to existing data (505(b)(2)), or a generic (ANDA — not applicable to a novel protocol).
3. **Confirm approval-history precedent for the class.** `OpenFDA_search_drug_approvals`, `OpenFDA_get_approval_history`, `OpenFDA_get_approved_products` — has anything in this mechanistic class been approved, on what evidence, and under what expedited program (breakthrough, fast track, accelerated approval, priority review)?
4. **Biologics** additionally check `FDAPurpleBook_search_products` for BLA/biosimilar precedent.

**Pathway decision:**
- New molecular entity, no prior approval in this indication or mechanism -> IND -> 505(b)(1) NDA (or BLA if biologic).
- Modification of a previously approved drug (new indication, formulation, dose) with literature/data bridging -> 505(b)(2) NDA.
- Note any FDA expedited program precedent found in Step 3 (breakthrough therapy, fast track, accelerated approval, priority review) — these change the acceptable endpoint and trial-size expectations; do not assume eligibility without a precedent match.

## Device Pathway

1. **Determine device classification.** `OpenFDADevice_get_classification` — Class I/II/III determines the pathway by default.
2. **Search for a predicate device (510(k)) or PMA precedent.** `OpenFDADevice_search_510k`, `OpenFDADevice_search_pma` — a substantially equivalent predicate supports 510(k); no predicate and Class III (or novel low-to-moderate-risk device with no predicate) points to De Novo or PMA.
3. **Check post-market signals for the device or its predicate.** `OpenFDADevice_search_recalls`, `OpenFDADevice_search_adverse_events` — informs the safety-monitoring section and risk framing.
4. **Confirm unique device identifier conventions if relevant to the protocol's data collection plan.** `OpenFDADevice_search_udi`.

**Pathway decision:**
- Class I or II with a valid predicate found in Step 2 -> 510(k).
- No predicate, but Class I/II risk profile -> De Novo.
- Class III, or a novel device with unresolved risk -> PMA (requires the most extensive clinical evidence — plan the protocol's population/duration accordingly).

## Combination Products

If the intervention has both a device and a drug/biologic constituent, run BOTH pathways above, identify the primary mode of action, and state which center would likely take lead review (informational only — this skill does not simulate a formal FDA Request for Designation determination).
