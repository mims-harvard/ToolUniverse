#!/usr/bin/env python3
"""Case 2: Is OXTR druggable, and does its chemistry fit the autism hypothesis?

Reproduces the second case study from
https://aiscientist.tools/posts/tooluniverse-case-studies

The steps below are the tool calls in the order the AI scientist made them.
Every number printed with a "(published: ...)" annotation is one that appears
either in the post or in the supplementary note it condenses (arXiv:2509.23426).
Intermediate values such as the 7QVM structure, the AlphaFold accession and the
PubChem CID come from the supplementary note.

The point of this case is the last step: a compound can clear every filter you
thought to apply (drug-like, brain-penetrant) and still be pharmacologically
wrong, because it acts in the opposite direction to the one the indication
needs.

Run:
    python case2_oxtr_druggability.py

Needs network access; no API keys. The ADMET-AI steps need the ``ml`` extra
(``pip install 'tooluniverse[ml]'``).
"""

from __future__ import annotations

from _common import (
    call,
    footer,
    header,
    is_error,
    load_universe,
    note_unavailable,
    report,
    step,
)

OXTR_ENSEMBL = "ENSG00000180914"
OXTR_UNIPROT = "P30559"


def main() -> None:
    header(
        "Case 2: OXTR druggability and whether the chemistry fits",
        "Is OXTR (the oxytocin receptor) a druggable target, and does its\n"
        "          pharmacology offer a credible chemical starting point for its\n"
        "          emerging autism association?",
    )
    tu = load_universe()

    # ------------------------------------------------------------------
    step(1, "Resolve, annotate, and obtain structure")
    search = call(
        tu,
        "OpenTargets_multi_entity_search_by_query_string",
        queryString="OXTR",
        entityNames=["target"],
    )
    hits = search.get("search", {}).get("hits", []) if not is_error(search) else []
    ensembl = next((h["id"] for h in hits if h.get("entity") == "target"), None)
    report("OXTR Ensembl gene", ensembl, OXTR_ENSEMBL)

    go = call(
        tu, "OpenTargets_get_target_gene_ontology_by_ensemblID", ensemblId=OXTR_ENSEMBL
    )
    if not is_error(go):
        labels = {
            (t.get("term", {}).get("label") or "")
            for t in go.get("target", {}).get("geneOntology", [])
        }
        gpcr = sorted(
            label
            for label in labels
            if "G protein-coupled" in label or "phospholipase C" in label
        )
        report("GO terms returned", len(labels))
        for label in gpcr[:3]:
            print(f"    - {label}")

    af = call(tu, "alphafold_get_summary", qualifier=OXTR_UNIPROT)
    if not is_error(af):
        entry = af.get("uniprot_entry", {})
        report("protein length", entry.get("sequence_length"), "389")
        structures = af.get("structures", []) or []
        if structures:
            report(
                "AlphaFold model",
                structures[0].get("summary", {}).get("model_identifier"),
                "AF-P30559-F1",
            )

    pdbe = call(tu, "PDBe_get_uniprot_structure_coverage", uniprot_id=OXTR_UNIPROT)
    if not is_error(pdbe):
        data = pdbe.get(OXTR_UNIPROT, {})
        pdb_ids = sorted(
            {e["name"].lower() for e in (data.get("data") or []) if e.get("name")}
        )
        report("experimental PDB entries", len(pdb_ids))
        report("active, agonist-bound 7RYC present", "7ryc" in pdb_ids, "yes")
        report("active 7QVM present", "7qvm" in pdb_ids, "yes")
        report("inactive 6TPK present", "6tpk" in pdb_ids, "yes")
        print("  Read: GPCR design needs state-specific, ligand-bound structures,")
        print("  and both states exist experimentally, so use these rather than")
        print("  the prediction.")

    # ------------------------------------------------------------------
    step(2, "Map the disease landscape")
    diseases = call(
        tu,
        "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
        ensemblId=OXTR_ENSEMBL,
    )
    if not is_error(diseases):
        associated = diseases.get("target", {}).get("associatedDiseases", {})
        # Expect drift here: Open Targets re-scores associations every release,
        # so this count moves. The published run saw 393.
        report("disease associations", associated.get("count"), "393, drifts upward")
        names = [
            r.get("disease", {}).get("name", "")
            for r in associated.get("rows", []) or []
        ]
        autism = [n for n in names if "autis" in n.lower()]
        report("autism-related terms in top rows", autism or "not in first page")
        print("  Reproductive and uterine indications have approved-drug precedent;")
        print("  the autism association is separate and still emerging.")

    # ------------------------------------------------------------------
    step(3, "Confirm tractability and enumerate drugs")
    tract = call(
        tu, "OpenTargets_get_target_tractability_by_ensemblID", ensemblId=OXTR_ENSEMBL
    )
    if not is_error(tract):
        buckets = [
            t
            for t in tract.get("target", {}).get("tractability", []) or []
            if t.get("value")
        ]
        sm = sorted({t["label"] for t in buckets if t.get("modality") == "SM"})
        report("small-molecule tractability buckets met", sm)

    drugs = call(
        tu,
        "OpenTargets_get_associated_drugs_by_target_ensemblID",
        ensemblId=OXTR_ENSEMBL,
    )
    known = {}
    if not is_error(drugs):
        block = drugs.get("target", {}).get("drugAndClinicalCandidates", {})
        report("known agents", block.get("count"), "9")
        for row in block.get("rows", []) or []:
            drug = row.get("drug", {}) or {}
            if drug.get("name"):
                known[drug["name"].lower()] = drug.get("id")
        for name in sorted(known):
            print(f"    - {name}")
        print("  Read: approved agents here are peptides, not small molecules.")

    # ------------------------------------------------------------------
    step(4, "Resolve mechanism")
    for name in ("oxytocin", "atosiban"):
        chembl_id = known.get(name)
        if not chembl_id:
            continue
        moa = call(
            tu,
            "OpenTargets_get_drug_mechanisms_of_action_by_chemblId",
            chemblId=chembl_id,
        )
        if not is_error(moa):
            rows = (
                moa.get("drug", {}).get("mechanismsOfAction", {}).get("rows", []) or []
            )
            actions = sorted({r.get("actionType") for r in rows if r.get("actionType")})
            report(f"{name} ({chembl_id}) action type", actions)
    print("  Read: the receptor is already drugged in both directions, so mechanism,")
    print("  not just affinity, is the thing to check next.")

    # ------------------------------------------------------------------
    step(5, "Confirm chemical matter with experimental data")
    targets = call(tu, "ChEMBL_search_targets", pref_name__contains="oxytocin receptor")
    if is_error(targets):
        note_unavailable("ChEMBL_search_targets", targets)
    else:
        rows = targets.get("targets", targets) or []
        target_id = None
        if isinstance(rows, list) and rows:
            target_id = rows[0].get("target_chembl_id")
        report("ChEMBL target", target_id, "CHEMBL2049")
        if target_id:
            acts = call(
                tu,
                "ChEMBL_get_target_activities",
                target_chembl_id__exact=target_id,
                limit=100,
            )
            if is_error(acts):
                note_unavailable("ChEMBL_get_target_activities", acts)
            else:
                rows = acts.get("activities", acts) or []
                affinities = [
                    float(a["standard_value"])
                    for a in rows
                    if isinstance(a, dict)
                    and a.get("standard_type") in {"Ki", "IC50", "Kd"}
                    and a.get("standard_units") == "nM"
                    and a.get("standard_value") is not None
                ]
                if affinities:
                    report(
                        "best measured affinity",
                        f"{min(affinities):.1f} nM",
                        "Ki as low as 3.2 nM",
                    )

    # ------------------------------------------------------------------
    step(6, "Reason about pharmacology and CNS druggability")
    lit = call(
        tu,
        "EuropePMC_search_articles",
        query="intranasal oxytocin autism spectrum disorder randomized placebo",
        limit=5,
    )
    if not is_error(lit) and isinstance(lit, list):
        report("articles returned", len(lit))
        for article in lit[:3]:
            print(f"    - {str(article.get('title'))[:88]}")
        print("  Read: the autism evidence for oxytocin itself is mixed, with large")
        print("  placebo responses; so look for a brain-penetrant non-peptide.")

    # Nolasiban is the non-peptide candidate: is central exposure even attainable?
    cid_payload = call(tu, "PubChem_get_CID_by_compound_name", name="nolasiban")
    cid = None
    if not is_error(cid_payload):
        cid = cid_payload.get("IdentifierList", {}).get("CID", [None])[0]
        report("nolasiban PubChem CID", cid, "52947354")

    smiles = None
    if cid:
        props = call(
            tu,
            "PubChem_get_compound_properties_by_CID",
            cid=cid,
            properties="MolecularWeight,SMILES,ConnectivitySMILES",
        )
        if not is_error(props):
            entry = props.get("PropertyTable", {}).get("Properties", [{}])[0]
            # Prefer the stereochemistry-bearing SMILES: nolasiban has a defined
            # stereocentre, and ADMET-AI scores the flat and stereo forms
            # differently (BBB 0.91 vs 0.93).
            smiles = entry.get("SMILES") or entry.get("ConnectivitySMILES")
            report("SMILES", smiles)

    if smiles:
        physchem = call(
            tu, "ADMETAI_predict_physicochemical_properties", smiles=[smiles]
        )
        if is_error(physchem):
            note_unavailable("ADMETAI_predict_physicochemical_properties", physchem)
        else:
            values = physchem.get(smiles, physchem)
            report(
                "QED (drug-likeness)", round(values.get("QED", float("nan")), 3), "0.87"
            )

        bbb = call(tu, "ADMETAI_predict_BBB_penetrance", smiles=[smiles])
        if is_error(bbb):
            note_unavailable("ADMETAI_predict_BBB_penetrance", bbb)
        else:
            values = bbb.get(smiles, bbb)
            score = next(
                (v for k, v in values.items() if "BBB" in k and "percentile" not in k),
                None,
            )
            report(
                "predicted BBB penetrance", round(score, 3) if score else None, "0.93"
            )

    # The mismatch that decides the case.
    nolasiban_id = known.get("nolasiban")
    if nolasiban_id:
        moa = call(
            tu,
            "OpenTargets_get_drug_mechanisms_of_action_by_chemblId",
            chemblId=nolasiban_id,
        )
        if not is_error(moa):
            rows = (
                moa.get("drug", {}).get("mechanismsOfAction", {}).get("rows", []) or []
            )
            actions = sorted({r.get("actionType") for r in rows if r.get("actionType")})
            report("nolasiban action type", actions, "ANTAGONIST")
            print("  Read: brain-penetrant non-peptide OXTR chemistry is attainable,")
            print("  but this chemotype BLOCKS the receptor, and the pro-social")
            print("  hypothesis needs it ACTIVATED. Wrong direction.")

    footer(
        {
            "Tractability": "OXTR is a druggable GPCR with active and inactive experimental "
            "structures and nanomolar ligands",
            "Mechanism": "already drugged both ways (oxytocin agonist, atosiban antagonist)",
            "The catch": "nolasiban is brain-penetrant but an ANTAGONIST, the opposite of what "
            "the autism hypothesis requires",
            "Conclusion": "the objective is a brain-penetrant agonist or positive allosteric "
            "modulator, selective over vasopressin receptors",
        }
    )


if __name__ == "__main__":
    main()
