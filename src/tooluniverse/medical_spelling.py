"""British to American medical spelling, for searches that match words literally.

Neither SQLite FTS5 (porter stemming) nor Europe PMC's search folds British
spellings into American ones. Measured 2026-10-11: StatPearls has 33 sections
containing "tumour" against 8,831 containing "tumor", and Europe PMC case
reports number 908 for "carcinoid tumour" against 3,593 for "carcinoid tumor";
"hypophosphataemia" finds 262 against 1,476. A query written in British
spelling therefore misses most of the literature, and the StatPearls chapter
titles (all American) entirely.

``us_spelling`` rewrites the common British medical spellings; the searches
add the American form as an alternative rather than replacing the word, so a
term spelled the same way in both dialects is unaffected.
"""

import re

# Word-internal British forms and their American replacements, longest first
# so that e.g. "orthopaed" is not split by "paed".
_INFIXES = (
    ("orthopaed", "orthoped"),
    ("oesophag", "esophag"),
    ("manoeuvr", "maneuver"),
    ("aetiolog", "etiolog"),
    ("anaesthe", "anesthe"),
    ("behaviour", "behavior"),
    ("leukaem", "leukem"),
    ("ischaem", "ischem"),
    ("coeliac", "celiac"),
    ("caesar", "cesar"),
    ("gynaec", "gynec"),
    ("tumour", "tumor"),
    ("colour", "color"),
    ("humour", "humor"),
    ("labour", "labor"),
    ("oestr", "estr"),
    ("oedem", "edem"),
    ("haem", "hem"),
    ("paed", "ped"),
    ("foet", "fet"),
    ("faec", "fec"),
    ("sulph", "sulf"),
)
# Endings: anaemia, hypophosphataemia, diarrhoea, dyspnoea, fibre, centre ...
_SUFFIXES = (
    ("aemia", "emia"),
    ("aemic", "emic"),
    ("rrhoea", "rrhea"),
    ("rrhoeal", "rrheal"),
    ("noea", "nea"),
    ("fibre", "fiber"),
    ("fibres", "fibers"),
    ("centre", "center"),
    ("centres", "centers"),
    ("litre", "liter"),
    ("litres", "liters"),
)
_WORDS = {"ageing": "aging", "aluminium": "aluminum", "programme": "program"}

_LETTERS = re.compile(r"[A-Za-z]+")


def _us_word(word: str) -> str:
    lower = word.lower()
    if lower in _WORDS:
        out = _WORDS[lower]
    else:
        out = lower
        for british, american in _SUFFIXES:
            if out.endswith(british):
                out = out[: -len(british)] + american
                break
        for british, american in _INFIXES:
            out = out.replace(british, american)
    if out == lower:
        return word
    return out.capitalize() if word[:1].isupper() else out


def us_spelling(text: str) -> str:
    """``text`` with each British medical spelling replaced by the American one."""
    return _LETTERS.sub(lambda m: _us_word(m.group(0)), text or "")
