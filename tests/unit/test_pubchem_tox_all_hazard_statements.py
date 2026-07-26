"""PubChemTox kept only the first string of each PubChem Information entry.

PubChem packs every statement of one notification group into a single
Information entry holding N StringWithMarkup elements. Reading ``sws[0]`` and
discarding the rest was not a random sample: GHS codes are ordered numerically
and physical hazards (H2xx) sort ahead of health hazards (H3xx), so the health
hazard was dropped whenever a physical one existed.

Confirmed live before the fix: benzene (CID 241) returned H225 and H401 only --
"highly flammable" and "toxic to aquatic life" -- while PubChem lists 16 codes
including H350 "May cause cancer", H340 and H372. Vinyl chloride, formaldehyde
and arsenic trioxide behaved the same way; all four are IARC Group 1 human
carcinogens. The same truncation made the carcinogen tool cite the withdrawn
1987 IARC monograph and drop the current 2012 one.
"""

from tooluniverse.pubchem_tox_tool import PubChemToxTool


def _make():
    return PubChemToxTool(
        {
            "name": "PubChemTox_get_ghs_classification",
            "type": "PubChemToxTool",
            "fields": {"operation": "get_ghs_classification"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _sections(strings, name="GHS Hazard Statements"):
    return [
        {
            "TOCHeading": "GHS Classification",
            "Information": [
                {
                    "Name": name,
                    "Value": {
                        "StringWithMarkup": [{"String": s} for s in strings]
                    },
                }
            ],
        }
    ]


_BENZENE = [
    "H225: Highly Flammable liquid and vapor",
    "H304: May be fatal if swallowed and enters airways",
    "H315: Causes skin irritation",
    "H340: May cause genetic defects",
    "H350: May cause cancer",
    "H372: Causes damage to organs",
]


def test_every_hazard_statement_is_returned():
    entries = _make()._extract_info_from_sections(
        _sections(_BENZENE), "GHS Classification"
    )

    assert [e["value"] for e in entries] == _BENZENE


def test_the_carcinogenicity_statement_survives():
    entries = _make()._extract_info_from_sections(
        _sections(_BENZENE), "GHS Classification"
    )
    values = " ".join(e["value"] for e in entries)

    assert "H350" in values
    assert "May cause cancer" in values
    assert "H340" in values


def test_health_hazards_are_not_lost_behind_a_physical_hazard():
    # H2xx sorts first, which is exactly why reading element 0 hid H3xx.
    entries = _make()._extract_info_from_sections(
        _sections(["H220: Extremely flammable gas", "H350: May cause cancer"]),
        "GHS Classification",
    )

    assert len(entries) == 2
    assert entries[0]["value"].startswith("H220")
    assert entries[1]["value"].startswith("H350")


def test_the_group_name_is_carried_onto_every_statement():
    entries = _make()._extract_info_from_sections(
        _sections(_BENZENE, name="GHS Hazard Statements"), "GHS Classification"
    )

    assert {e["name"] for e in entries} == {"GHS Hazard Statements"}


def test_multiple_iarc_monographs_are_all_kept():
    monographs = [
        "Volume Sup 7: Overall Evaluations, 1987 (out of print)",
        "Volume 62: (1995) Wood Dust and Formaldehyde",
        "Volume 88: (2006) Formaldehyde, 2-Butoxyethanol",
        "Volume 100F: (2012) Chemical Agents and Related Occupations",
    ]
    entries = _make()._extract_info_from_sections(
        _sections(monographs, name="IARC Monographs"), "GHS Classification"
    )

    assert len(entries) == 4
    assert any("100F" in e["value"] for e in entries)


def test_pictogram_markup_is_kept_per_statement():
    sections = [
        {
            "TOCHeading": "GHS Classification",
            "Information": [
                {
                    "Name": "Pictogram(s)",
                    "Value": {
                        "StringWithMarkup": [
                            {
                                "String": "Flammable",
                                "Markup": [{"Extra": "Flammable"}],
                            },
                            {
                                "String": "Health Hazard",
                                "Markup": [{"Extra": "Health Hazard"}],
                            },
                        ]
                    },
                }
            ],
        }
    ]
    entries = _make()._extract_info_from_sections(sections, "GHS Classification")

    assert [e["pictogram_labels"] for e in entries] == [
        ["Flammable"],
        ["Health Hazard"],
    ]


def test_entry_without_strings_is_skipped():
    sections = [
        {
            "TOCHeading": "GHS Classification",
            "Information": [{"Name": "Table pointer", "Value": {}}],
        }
    ]

    assert _make()._extract_info_from_sections(sections, "GHS Classification") == []
