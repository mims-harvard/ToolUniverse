"""openFDA's route vocabulary for drug labels, and the filter that selects one route.

One generic name often covers products of several routes -- atropine: injection,
eye drops, and the diphenoxylate/atropine tablets; budesonide: capsules, inhaler,
rectal foam -- and a label lookup by name used to return whichever labels openFDA
listed first. Both label tool families (``openfda_tool.FDADrugLabelTool`` and
``fda_label_tool.FDALabelTool``) take an optional ``route``, spelled as openFDA
spells it, and AND ``route_clause`` onto every query they send.
"""

# `openfda.route` values on drug/label, counted live on 2026-10-14 with
# `count=openfda.route.exact`: 71 values.
LABEL_ROUTES = frozenset(
    {
        "AURICULAR (OTIC)",
        "BUCCAL",
        "CONJUNCTIVAL",
        "CUTANEOUS",
        "DENTAL",
        "ENDOTRACHEAL",
        "ENTERAL",
        "EPIDURAL",
        "EXTRACORPOREAL",
        "HEMODIALYSIS",
        "INFILTRATION",
        "INTERSTITIAL",
        "INTRA-ARTERIAL",
        "INTRA-ARTICULAR",
        "INTRABRONCHIAL",
        "INTRACAMERAL",
        "INTRACANALICULAR",
        "INTRACARDIAC",
        "INTRACAUDAL",
        "INTRACAVERNOUS",
        "INTRACAVITARY",
        "INTRACEREBRAL",
        "INTRACOCHLEAR",
        "INTRACORONARY",
        "INTRADERMAL",
        "INTRAEPIDERMAL",
        "INTRAGASTRIC",
        "INTRALESIONAL",
        "INTRALUMINAL",
        "INTRALYMPHATIC",
        "INTRAMEDULLARY",
        "INTRAMUSCULAR",
        "INTRAOCULAR",
        "INTRAPERITONEAL",
        "INTRAPLEURAL",
        "INTRASINAL",
        "INTRASYNOVIAL",
        "INTRATHECAL",
        "INTRAUTERINE",
        "INTRAVASCULAR",
        "INTRAVENOUS",
        "INTRAVENTRICULAR",
        "INTRAVESICAL",
        "INTRAVITREAL",
        "IRRIGATION",
        "NASAL",
        "OPHTHALMIC",
        "ORAL",
        "OROPHARYNGEAL",
        "PARENTERAL",
        "PERCUTANEOUS",
        "PERINEURAL",
        "PERIODONTAL",
        "RECTAL",
        "RESPIRATORY (INHALATION)",
        "RETROBULBAR",
        "SOFT TISSUE",
        "SUBARACHNOID",
        "SUBCONJUNCTIVAL",
        "SUBCUTANEOUS",
        "SUBGINGIVAL",
        "SUBLINGUAL",
        "SUBMUCOSAL",
        "SUPRACHOROIDAL",
        "TOPICAL",
        "TRANSDERMAL",
        "TRANSMUCOSAL",
        "TRANSTRACHEAL",
        "URETERAL",
        "URETHRAL",
        "VAGINAL",
    }
)

# The two routes openFDA spells with a parenthesis, by the word a label's own text uses.
_SHORT_NAMES = {"INHALATION": "RESPIRATORY (INHALATION)", "OTIC": "AURICULAR (OTIC)"}
_TEXT_WORDS = {full: short.lower() for short, full in _SHORT_NAMES.items()}


def normalise_route(route):
    """(route, error): openFDA's spelling of ``route``, or an error listing every route.

    Case and surrounding space are ignored, and "inhalation" and "otic" name the
    two routes openFDA spells with a parenthesis. Nothing else is guessed.
    """
    value = " ".join(str(route).split()).upper()
    value = _SHORT_NAMES.get(value, value)
    if value in LABEL_ROUTES:
        return value, None
    return None, (
        f"Unknown route '{route}'. Use openFDA's route name (any case; 'inhalation' "
        f"and 'otic' are also accepted): " + ", ".join(sorted(LABEL_ROUTES)) + "."
    )


def route_clause(route):
    """openFDA query_string filter for the labels of ``route`` (a value of ``LABEL_ROUTES``).

    A label whose ``openfda`` block names a route is matched on it. Many labels
    have no ``openfda`` block at all (2026-10-14: 224 of the labels naming
    atropine, the atropine eye drops among them), so a label with no route is
    matched when its description or carton text names the route instead.
    Space-separated, for the caller to AND onto its own search.
    """
    word = _TEXT_WORDS.get(route, route.lower())
    return (
        f'(openfda.route:"{route}" OR (_missing_:openfda.route AND '
        f'(description:"{word}" OR package_label_principal_display_panel:"{word}")))'
    )
