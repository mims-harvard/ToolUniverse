"""A category name is matched as a category, not as a filename substring.

load_all_tool_configs globbed `*<pattern>*.json` over config filenames, and
"ols" is inside "tools", so `test_new_tools.py ols` matched 647 of the 688
config files and tested most of the repository. The sweep asks for one category
per subprocess, so ols hit the per-pattern timeout on every weekly run --
measured: still running after 1500 s, having reached 22 of the repository's
tests. With an exact match it is 8 tests in 5.46 s, all passing.

The same over-matching quietly doubled the sweep's work. Every category whose
config filename is a prefix of a sibling's ran the siblings' tests too, and the
sweep then ran those siblings again under their own names:

    ensembl        81 tests -> 22    (12 sibling categories)
    core           50      ->  3
    kegg           51      ->  9
    uniprot        48      -> 18

Across the 647 categories with an exact config file: 10225 example runs for
4593 examples, so 5632 of them were duplicates, and a failure counted under
`ensembl` might belong to `ensembl_vep`.

The substring fallback stays for interactive use, where it is the documented
behaviour and there is no exact file to prefer: `test_new_tools.py fda` still
matches all 11 fda configs.
"""

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"


def _runner():
    spec = importlib.util.spec_from_file_location(
        "test_new_tools_matching", ROOT / "scripts" / "test_new_tools.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _loaded_files(pattern, tmp_path=None):
    configs = _runner().load_all_tool_configs(DATA, pattern)
    return [path.name for path, _tools in configs]


def test_ols_loads_only_its_own_config():
    """647 of 688 files before, because "ols" is inside "tools"."""
    files = _loaded_files("ols")

    assert files == ["ols_tools.json"], len(files)


def test_a_prefix_category_does_not_pull_in_its_siblings():
    files = _loaded_files("ensembl")

    assert files == ["ensembl_tools.json"]
    siblings = sorted(p.name for p in DATA.glob("ensembl_*_tools.json"))
    assert len(siblings) >= 8, "the siblings this used to absorb"
    for sibling in siblings:
        assert sibling not in files


@pytest.mark.parametrize("pattern", ["core", "kegg", "uniprot", "oma", "reactome"])
def test_the_other_prefix_categories_are_scoped_too(pattern):
    files = _loaded_files(pattern)

    assert files == [f"{pattern}_tools.json"], files


def test_the_substring_fallback_still_works_without_an_exact_file():
    """`fda` has no fda_tools.json, and matching 11 configs is documented."""
    assert not (DATA / "fda_tools.json").is_file()

    files = _loaded_files("fda")

    assert len(files) > 1
    assert all("fda" in name for name in files)


def test_every_category_with_a_config_file_resolves_to_exactly_one():
    """The invariant, rather than today's list of offenders."""
    runner = _runner()
    over_matched = []
    for path in sorted(DATA.glob("*_tools.json")):
        category = path.name[: -len("_tools.json")]
        loaded = [p.name for p, _ in runner.load_all_tool_configs(DATA, category)]
        if loaded != [path.name]:
            over_matched.append((category, len(loaded)))

    assert not over_matched, over_matched[:10]


def test_broken_api_configs_stay_excluded():
    """The exact path must not bypass the broken_apis filter."""
    runner = _runner()
    retired = sorted(p.stem for p in (DATA / "broken_apis").glob("*.json"))

    assert retired, "nothing retired, so this test checks nothing"
    for name in retired:
        loaded = [p for p, _ in runner.load_all_tool_configs(DATA, name)]
        assert all("broken_apis" not in p.parts for p in loaded), name


def test_a_pattern_with_no_match_still_falls_back_to_a_full_scan():
    """The tool-name fallback is how `test_new_tools.py SomeToolName` works."""
    runner = _runner()

    configs = runner.load_all_tool_configs(DATA, "zzz_no_such_category_zzz")

    assert len(configs) > 100, "a tool-name query has to scan everything"
