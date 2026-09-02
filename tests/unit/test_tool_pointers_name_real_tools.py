"""A note that says "use X instead" must name a tool that exists.

Round 55 swept every user-facing string in the config data and in the Python
tool modules for tool names that are not registered. Eleven remediation notes
pointed at tools that do not exist, each confirmed dead through the CLI:

    ChEMBL_search_compounds              gtopdb_tool.py (3 sites)
    ChEMBL_search_target                 bindingdb_tool.py, bindingdb_tools.json
    DGIdb_search_interactions            biogrid_tool.py (2), biogrid_tools.json
    CPIC_get_guidelines                  pharmgkb_tool.py
    ChEBI_get_compound_by_name           ctd_tool.py
    NCBIGene_search_genes                disgenet_tool.py
    CELLxGENE_query_cells                cellxgene_census_tool.py
    OpenTargets_get_associated_diseases  ctd_tools.json
    STRING_get_interactions              hpa_tool.py, hpa_tools.json
    ChEMBL_get_molecule_by_chembl_id     smcp_server.py (4 --help examples)
    UniProt_get_uniref_search            uniprot_tools.json

Every one of them is emitted at exactly the moment the caller is stuck -- an
empty result, a rejected parameter, a permanently unavailable tool -- so the
note is the caller's only route forward and it led to a second dead end.
GtoPdb's was the worst: `coverage_note` fires on EVERY successful call and
named both a tool that does not exist and a parameter (`target_name`) that
`ChEMBL_get_drug_mechanisms` rejects outright.

The replacements were each run through the CLI before being written in:
ChEMBL_search_molecules, ChEMBL_search_targets, ChEMBL_search_activities,
DGIdb_get_drug_gene_interactions, CPIC_list_guidelines, ChEBI_search,
NCBIGene_search, OpenTargets_get_diseases_phenotypes_by_target_ensembl,
STRING_get_protein_interactions, ChEMBL_get_molecule and UniProt_search_uniref
all returned real data.

Config/string-only assertions -- no network.
"""

import ast
import collections
import functools
import json
import re
from pathlib import Path

import pytest

import tooluniverse

pytestmark = pytest.mark.unit

PKG_DIR = Path(tooluniverse.__file__).parent
DATA_DIR = PKG_DIR / "data"

# A token that could be a tool name. Three or more underscore-separated
# segments, which is the shape every ToolUniverse tool name has and which a
# two-segment API field name (gnomAD's `gnomad_constraint`, `exac_constraint`)
# does not -- those are response keys, not tools, and are legitimately named in
# the same sentence that recommends a tool.
TOKEN = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+){2,}\b")
# Only strings that steer the caller somewhere are in scope; a bare mention in
# prose is not a broken pointer.
GUIDANCE = re.compile(r"\b(use|using|prefer|try|call|run|via|instead)\b", re.I)

DEAD_POINTERS_FIXED_IN_ROUND_55 = [
    "ChEMBL_search_compounds",
    "ChEMBL_search_target",
    "DGIdb_search_interactions",
    "CPIC_get_guidelines",
    "ChEBI_get_compound_by_name",
    "NCBIGene_search_genes",
    "CELLxGENE_query_cells",
    "OpenTargets_get_associated_diseases",
    "STRING_get_interactions",
    "ChEMBL_get_molecule_by_chembl_id",
    "UniProt_get_uniref_search",
]


@functools.lru_cache(maxsize=1)
def _registered_tool_names():
    names = set()
    for path in DATA_DIR.rglob("*.json"):
        if "broken_apis" in path.parts:
            continue
        try:
            configs = json.loads(path.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(configs, list):
            continue
        for config in configs:
            if isinstance(config, dict) and "type" in config:
                name = config.get("name")
                if isinstance(name, str):
                    names.add(name)
    return names


@functools.lru_cache(maxsize=1)
def _guidance_strings():
    """The caller-visible strings that steer someone somewhere, scanned once.

    Every test in this file needs the same sweep, and the sweep costs ~1.1s
    (652 config files parsed, 538 package modules AST-parsed, 269,003 strings
    walked). Caching only the ~4,200 strings that pass GUIDANCE takes the file
    from 16.5s to 3.9s and retains 2.2 MB; caching all 269,003 would retain
    34.8 MB for no extra benefit, since nothing here looks at the rest.

    Note the Python sweep is deliberately non-recursive: `src/tooluniverse/tools/`
    holds 2,738 generated wrappers whose docstrings are truncated mid-token by
    the generator (`CPIC_list_guide`, `ESM_get_sae_featu`), which no name-shape
    heuristic can tell from a genuine typo. Their prose is copied from the
    configs this already scans.
    """

    def walk(node, where):
        if isinstance(node, str):
            yield node, where
        elif isinstance(node, dict):
            for value in node.values():
                yield from walk(value, where)
        elif isinstance(node, list):
            for value in node:
                yield from walk(value, where)

    def sources():
        for path in DATA_DIR.rglob("*.json"):
            if "broken_apis" in path.parts:
                continue
            try:
                configs = json.loads(path.read_text())
            except (ValueError, UnicodeDecodeError):
                continue
            yield from walk(configs, path.name)

        for path in sorted(PKG_DIR.glob("*.py")):
            try:
                tree = ast.parse(path.read_text())
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    yield node.value, path.name

    return tuple((text, where) for text, where in sources() if GUIDANCE.search(text))


_MIN_VENDORS_PER_VERB = 10


def _tool_name_verbs(names):
    """Second-position segments shared across at least 10 vendor prefixes.

    This is the discriminator between a tool name and a response field:
    ToolUniverse tool names read `<Vendor>_<verb>_<what>`. Deriving the verbs
    from the registry means the rule cannot drift out of date, and requiring a
    verb to be used by many vendors keeps domain nouns out of the set -- `gene`
    and `disease` sit in second position often enough to look verb-like within
    one vendor, and admitting them flags ordinary prose like "call
    get_gene_info". Measured over the current registry this yields exactly
    {API, find, get, list, predict, query, search}, and all 9 pins below pass.

    It replaced a `difflib.get_close_matches(cutoff=0.85)` near-miss filter,
    which was measured to miss 5 of those 9 pins (DGIdb_search_interactions,
    ChEBI_get_compound_by_name, NCBIGene_search_genes, CELLxGENE_query_cells and
    OpenTargets_get_associated_diseases all score below 0.85 against every real
    name) while flagging genuine response-field names such as
    `ClinVar_clinical_significance`. Character overlap is not evidence of intent
    to name a tool; a shared verb in second position is. The dataset labels this
    must not flag -- `GO_Biological_Process_2023`, `KEGG_2021_Human`,
    `MSigDB_Hallmark_2020` -- all fail the verb rule.
    """
    vendors_per_verb = collections.defaultdict(set)
    for name in names:
        segments = name.split("_")
        if len(segments) >= 3:
            vendors_per_verb[segments[1]].add(segments[0])
    return frozenset(
        verb
        for verb, vendors in vendors_per_verb.items()
        if len(vendors) >= _MIN_VENDORS_PER_VERB
    )


def _dangling_pointers():
    names = _registered_tool_names()
    assert len(names) > 2000, "tool registry did not load"
    prefixes = {name.split("_")[0] for name in names if "_" in name}
    verbs = _tool_name_verbs(names)

    found = set()
    for text, where in _guidance_strings():
        for token in set(TOKEN.findall(text)):
            if token in names or token.upper() == token:
                continue
            vendor, verb = token.split("_")[:2]
            # A bare verb head ("call get_interactions with ...") is unqualified
            # shorthand in prose, not a claim that such a tool is registered.
            if vendor in verbs or vendor not in prefixes or verb not in verbs:
                continue
            found.add((token, where))
    return found


def test_no_user_facing_string_points_at_a_tool_that_does_not_exist():
    dangling = _dangling_pointers()

    assert not dangling, "\n".join(
        f"{token} (recommended in {where}) is not a registered tool"
        for token, where in sorted(dangling)
    )


@pytest.mark.parametrize("dead_name", DEAD_POINTERS_FIXED_IN_ROUND_55)
def test_each_specific_dead_pointer_is_gone(dead_name):
    """Per-name pins, so reverting any single fix fails its own assertion."""
    names = _registered_tool_names()
    assert dead_name not in names, f"{dead_name} now exists; drop it from this list"

    offenders = [
        where
        for text, where in _guidance_strings()
        if re.search(rf"\b{re.escape(dead_name)}\b", text)
    ]
    assert not offenders, f"{dead_name} still recommended in {sorted(set(offenders))}"


def test_the_replacements_named_in_those_notes_are_real_tools():
    """A fix that swapped one dead name for another would pass the test above."""
    names = _registered_tool_names()

    for replacement in (
        "ChEMBL_search_molecules",
        "ChEMBL_search_targets",
        "ChEMBL_search_activities",
        "DGIdb_get_drug_gene_interactions",
        "CPIC_list_guidelines",
        "ChEBI_search",
        "NCBIGene_search",
        "CELLxGENE_get_cell_metadata",
        "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
        "STRING_get_protein_interactions",
        "ChEMBL_get_molecule",
        "UniProt_search_uniref",
    ):
        assert replacement in names, replacement


def test_gtopdb_no_longer_advertises_a_parameter_chembl_rejects():
    """`ChEMBL_get_drug_mechanisms` accepts no `target_name`; the note said it did.

    Verified live: `ChEMBL_get_drug_mechanisms {"target_name": "FSH receptor"}`
    returns "Unrecognized parameter(s): 'target_name'. This tool accepts:
    chembl_id, drug_chembl_id, drug_name, limit, molecule_chembl_id, offset."
    """
    source = (PKG_DIR / "gtopdb_tool.py").read_text()

    assert "target_name=" not in source
    assert "ChEMBL_search_targets(pref_name__contains=" in source

    mechanisms = next(
        config
        for config in json.loads((DATA_DIR / "chembl_tools.json").read_text())
        if config["name"] == "ChEMBL_get_drug_mechanisms"
    )
    assert "target_name" not in mechanisms["parameter"]["properties"]
