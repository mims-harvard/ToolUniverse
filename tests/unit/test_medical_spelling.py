"""British to American medical spelling for literal-match searches (StatPearls FTS5, Europe PMC)."""

import pytest

from tooluniverse.medical_spelling import us_spelling

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "british, american",
    [
        ("tumour", "tumor"),
        ("Carcinoid tumours", "Carcinoid tumors"),
        ("X-linked hypophosphataemia", "X-linked hypophosphatemia"),
        ("anaemia", "anemia"),
        ("leukaemia", "leukemia"),
        ("ischaemic stroke", "ischemic stroke"),
        ("oesophageal atresia", "esophageal atresia"),
        ("oedema", "edema"),
        ("lymphoedema", "lymphedema"),
        ("haemorrhage", "hemorrhage"),
        ("paediatric orthopaedic surgery", "pediatric orthopedic surgery"),
        ("gynaecology", "gynecology"),
        ("caesarean section", "cesarean section"),
        ("coeliac disease", "celiac disease"),
        ("diarrhoea", "diarrhea"),
        ("dyspnoea", "dyspnea"),
        ("foetal", "fetal"),
        ("faecal incontinence", "fecal incontinence"),
        ("aetiology", "etiology"),
        ("anaesthesia", "anesthesia"),
        ("oestrogen", "estrogen"),
        ("sulphasalazine", "sulfasalazine"),
        ("Haemophilia", "Hemophilia"),
    ],
)
def test_british_medical_spellings_become_american(british, american):
    assert us_spelling(british) == american


@pytest.mark.parametrize(
    "text",
    ["tumor", "hour", "four", "aerobic", "Graham", "thyroidectomy", "MSI-H BRAF V600E", ""],
)
def test_american_and_unrelated_words_are_unchanged(text):
    assert us_spelling(text) == text
