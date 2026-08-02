# Scanner-Discovered Cancer Evidence Qualification

## Objective

Test whether an exhaustive VSD catalog scan can identify exact missing operations, promote only candidates that pass representative live verification, and use the resulting tools in five cancer evidence workflows.

## Catalog scale

| Measure | Result |
| --- | ---: |
| Catalog records | 2,799 |
| Compatible records processed | 1,748 |
| Unique operations inventoried | 37,570 |
| Unique draft-ready candidates | 3,097 |
| Scientific draft-ready candidates | 309 |
| Blocked operations | 36,362 |

## Qualification results

Four exact registry gaps passed five representative calls each before approval and publication. Four other candidates were withheld after live response-schema verification failed.

| Decision | Operation | Evidence |
| --- | --- | --- |
| Accepted | `VSDScannerCOHDCancerConcepts` | 5 verification cases; publication `b49315f4494d` |
| Accepted | `VSDScannerGeneRelationships` | 5 verification cases; publication `f9fe2dc9a6fe` |
| Accepted | `VSDScannerGeneRegulationLinks` | 5 verification cases; publication `2731214c4658` |
| Accepted | `VSDScannerDrugHypotheses` | 5 verification cases; publication `f311fb9363b2` |
| Rejected | `VSDScannerRejectedEBIProtein` | The live accession value is scalar where the published response schema requires an array. |
| Rejected | `VSDScannerRejectedTranslatorAnnotation` | The live annotation response omits the identifier field required by the published response schema. |
| Rejected | `VSDScannerRejectedCOHDFrequency` | The live frequency is decimal while the published response schema declares an integer. |
| Rejected | `VSDScannerRejectedGeneDetail` | The live gene-detail response contains null where the published response schema requires an array. |

## Five evidence workflows

### Breast neoplasms: ESR1

Can a reproducible evidence packet preserve the ESR1 identity while retrieving terminology matches, gene relationships, regulatory-link counts, and bounded drug-repositioning hypotheses for breast neoplasms?

Controlled disease identifier: `MESH:D001943` ([NLM MeSH record](https://meshb.nlm.nih.gov/record/ui?ui=D001943)).

| Evidence role | Observation | Provider evidence |
| --- | --- | --- |
| `cohd_concepts` | candidate_concepts: concept_id=40664624, concept_name=Clinician diagnosed breast cancer preoperatively by a minimally invasive biopsy method, domain_id=Observation, concept_count=1056; concept_id=40664869, concept_name=Clinically node negative (t1n0m0 or t2n0m0) invasive breast cancer, domain_id=Observation, concept_count=629; concept_id=42742430, concept_name=Quantitative HER2 immunohistochemistry (IHC) evaluation of breast cancer consistent with the scoring system defined in the ASCO/CAP guidelines (PATH), domain_id=Observation, concept_count=274; concept_id=40664896, concept_name=Documentation of reason(s) sentinel lymph node biopsy not performed (e.g., reasons could include but not limited to; non-invasive cancer, incidental discovery of breast cancer on prophylactic mastectomy, incidental discovery of breast cancer on reduction, domain_id=Observation, concept_count=143; concept_id=42742290, concept_name=BRCA2 (breast cancer 2) (eg, hereditary breast and ovarian cancer) gene analysis; full sequence analysis, domain_id=Measurement, concept_count=137 | `cohd-api.transltr.io`; payload `fe2a8397e62f` |
| `gene_relationships` | approved_symbols: ESR1<br>alias_symbols: Era; ER-alpha; NR3A1; ER<br>previous_symbols: ESR | `ontology.api.hubmapconsortium.org`; payload `6bb1a5d6890e` |
| `gene_regulation` | gene_identifier: ESR1<br>linked_entity_counts: RegulatoryElement=216, xqtlEvidence=1204 | `genboree.org`; payload `a86b63cb1b68` |
| `drug_hypotheses` | ranked_hypotheses: id=DB00675, label=Tamoxifen, score=-0.0742775946855545; id=DB00515, label=Cisplatin, score=-0.079818494617939; id=DB00441, label=Gemcitabine, score=-0.08470036834478378; id=DB09107, label=Ro 50-3821, score=-0.0922989696264267; id=DB08894, label=hematide, score=-0.09347600489854813 | `openpredict.semanticscience.org`; payload `66e22fa34086` |

### Lung neoplasms: EGFR

Can the same reviewed tool set preserve the EGFR identity and assemble terminology, gene-regulation, and computational hypothesis evidence for lung neoplasms?

Controlled disease identifier: `MESH:D008175` ([NLM MeSH record](https://meshb.nlm.nih.gov/record/ui?ui=D008175)).

| Evidence role | Observation | Provider evidence |
| --- | --- | --- |
| `cohd_concepts` | candidate_concepts: concept_id=254591, concept_name=Secondary malignant neoplasm of lung, domain_id=Condition, concept_count=2448 | `cohd-api.transltr.io`; payload `0bee663d2992` |
| `gene_relationships` | approved_symbols: EGFR<br>alias_symbols: ERBB1; ERRP<br>previous_symbols: ERBB | `ontology.api.hubmapconsortium.org`; payload `fb3af14b09b6` |
| `gene_regulation` | gene_identifier: EGFR<br>linked_entity_counts: RegulatoryElement=380, xqtlEvidence=780 | `genboree.org`; payload `2c2a6bf1b3b3` |
| `drug_hypotheses` | ranked_hypotheses: id=DB00997, label=Doxorubicin, score=-0.0759170651435852; id=DB00515, label=Cisplatin, score=-0.08980945497751236; id=DB01229, label=Paclitaxel, score=-0.09799187630414963; id=DB00441, label=Gemcitabine, score=-0.09976809471845627; id=DB11672, label=Curcumin, score=-0.11312627792358398 | `openpredict.semanticscience.org`; payload `a7eea7c4fb86` |

### Colorectal neoplasms: TP53

Can the reviewed operations produce a provenance-linked terminology, TP53 identity, regulatory-link, and hypothesis packet for colorectal neoplasms?

Controlled disease identifier: `MESH:D015179` ([NLM MeSH record](https://meshb.nlm.nih.gov/record/ui?ui=D015179)).

| Evidence role | Observation | Provider evidence |
| --- | --- | --- |
| `cohd_concepts` | candidate_concepts: concept_id=197500, concept_name=Primary malignant neoplasm of colon, domain_id=Condition, concept_count=1807 | `cohd-api.transltr.io`; payload `382a71bd9d55` |
| `gene_relationships` | approved_symbols: TP53<br>alias_symbols: LFS1; p53<br>previous_symbols: No values returned | `ontology.api.hubmapconsortium.org`; payload `388cff120efa` |
| `gene_regulation` | gene_identifier: TP53<br>linked_entity_counts: RegulatoryElement=74, xqtlEvidence=1244 | `genboree.org`; payload `c2169264323e` |
| `drug_hypotheses` | ranked_hypotheses: id=DB00515, label=Cisplatin, score=-0.09734850376844406; id=DB08894, label=hematide, score=-0.10236989706754684; id=DB09107, label=Ro 50-3821, score=-0.10461752116680145; id=DB01229, label=Paclitaxel, score=-0.108942911028862; id=DB14765, label=Rivoceranib, score=-0.11314454674720764 | `openpredict.semanticscience.org`; payload `73ec942cddf3` |

### Melanoma: BRAF

Can a scanner-discovered workflow preserve the BRAF identity while retrieving melanoma terminology, regulatory-link counts, and bounded drug hypotheses?

Controlled disease identifier: `MESH:D008545` ([NLM MeSH record](https://meshb.nlm.nih.gov/record/ui?ui=D008545)).

| Evidence role | Observation | Provider evidence |
| --- | --- | --- |
| `cohd_concepts` | candidate_concepts: concept_id=141232, concept_name=Malignant melanoma of skin, domain_id=Condition, concept_count=2460; concept_id=133713, concept_name=Malignant melanoma of skin of face, domain_id=Condition, concept_count=1015; concept_id=133714, concept_name=Malignant melanoma of skin of trunk, domain_id=Condition, concept_count=896; concept_id=438983, concept_name=Malignant melanoma of skin of upper limb, domain_id=Condition, concept_count=849; concept_id=139757, concept_name=Malignant melanoma of skin of lower limb, domain_id=Condition, concept_count=681 | `cohd-api.transltr.io`; payload `e3900c0248a0` |
| `gene_relationships` | approved_symbols: BRAF<br>alias_symbols: BRAF-1; BRAF1<br>previous_symbols: No values returned | `ontology.api.hubmapconsortium.org`; payload `bb81fb5f336f` |
| `gene_regulation` | gene_identifier: BRAF<br>linked_entity_counts: RegulatoryElement=344, xqtlEvidence=508 | `genboree.org`; payload `4fa1f62a4cdf` |
| `drug_hypotheses` | ranked_hypotheses: id=DB00515, label=Cisplatin, score=-0.10456789284944534; id=DB09107, label=Ro 50-3821, score=-0.11128316819667816; id=DB08894, label=hematide, score=-0.11279206722974777; id=DB00441, label=Gemcitabine, score=-0.1150360181927681; id=DB00997, label=Doxorubicin, score=-0.11634187400341034 | `openpredict.semanticscience.org`; payload `c2cdf97af996` |

### Prostatic neoplasms: PTEN

Can the same governed workflow preserve the PTEN identity and assemble terminology, regulatory-link, and computational hypothesis evidence for prostatic neoplasms?

Controlled disease identifier: `MESH:D011471` ([NLM MeSH record](https://meshb.nlm.nih.gov/record/ui?ui=D011471)).

| Evidence role | Observation | Provider evidence |
| --- | --- | --- |
| `cohd_concepts` | candidate_concepts: concept_id=200962, concept_name=Primary malignant neoplasm of prostate, domain_id=Condition, concept_count=5957; concept_id=40481096, concept_name=Screening for malignant neoplasm of prostate, domain_id=Procedure, concept_count=2526 | `cohd-api.transltr.io`; payload `d1f0720870c2` |
| `gene_relationships` | approved_symbols: PTEN<br>alias_symbols: MMAC1; PTEN1; TEP1<br>previous_symbols: MHAM; BZS | `ontology.api.hubmapconsortium.org`; payload `f5740dfd4843` |
| `gene_regulation` | gene_identifier: PTEN<br>linked_entity_counts: RegulatoryElement=181, xqtlEvidence=265 | `genboree.org`; payload `f969963ba90f` |
| `drug_hypotheses` | ranked_hypotheses: id=DB00515, label=Cisplatin, score=-0.08556073904037476; id=DB00675, label=Tamoxifen, score=-0.09266618639230728; id=DB01229, label=Paclitaxel, score=-0.0977945327758789; id=DB00755, label=Tretinoin, score=-0.11763874441385269; id=DB00997, label=Doxorubicin, score=-0.12111058831214905 | `openpredict.semanticscience.org`; payload `a1ef54d5c507` |

## Comparison

**Without VSD.** The exact eight catalog operations were absent from the audited ToolUniverse registry. Using them would require separate HTTP integration, schema handling, provenance capture, and maintenance, and static contract inspection alone would not reveal the four live response failures.

**With VSD.** The scanner supplied a hashed candidate inventory; promotion gates accepted four operations, rejected four, loaded the accepted tools explicitly, and retained operation and payload hashes for every call.

**Measured contribution.** VSD closed four exact capability gaps for five reproducible workflows without weakening ToolUniverse's registry, verification, approval, or runtime boundaries. The result is broader governed access, not a claim of improved clinical truth.

## Scientific interpretation

These workflows evaluate source discovery, identifier-preserving retrieval, provenance, and promotion controls. They do not establish causality, validate biomarkers, recommend treatment, or support patient-level decisions.

COHD results are terminology matches from deidentified aggregate data, HuBMAP relationships support symbol normalization, CFDE values are linked-record counts, and OpenPredict outputs are computational hypotheses. These sources are not interchangeable and are not combined into a clinical score.

Study SHA-256: `cb5a36ae24abb4ccc6b7d98d7ab4aae0026e26b43aff709568e8c0a014e78a7e`.
