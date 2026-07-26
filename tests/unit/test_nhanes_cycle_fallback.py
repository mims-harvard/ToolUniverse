"""nhanes_get_dataset_info answered about a different survey cycle than asked.

An unrecognised ``year`` fell through to ``cycles[:2]``, so asking for the real
2021-2023 cycle returned rows labelled 2017-2018 and 2015-2016 under
``status: "success"`` -- the wrong years presented as the answer, with nothing
to signal the substitution. The hardcoded cycle list was also stale (it began
at 2007-2008 and stopped at 2017-2018, omitting six earlier published cycles
and the current one), and every ``download_url`` was assembled from a template
that does not exist: confirmed live,
``.../Nchs/Nhanes/2017-2018/laboratory_2017-2018.aspx`` redirects to CDC's
ErrorPage.aspx, while the datapage form now emitted returns HTTP 200.
"""

import pytest

from tooluniverse.nhanes_tool import NHANESTool


def _make():
    cfg = {
        "name": "nhanes_get_dataset_info",
        "type": "NHANESTool",
        "fields": {"endpoint": "dataset_info"},
        "parameter": {"type": "object", "properties": {}},
    }
    return NHANESTool(cfg)


def _info(**arguments):
    return _make()._get_dataset_info(arguments)


def test_unknown_cycle_is_rejected_not_silently_substituted():
    res = _info(year="2021-2022", component="Laboratory")

    assert res["status"] == "error"
    assert "2021-2022" in res["error"]
    # The caller is told what it can ask for instead of getting other years.
    assert "2017-2018" in res["error"]


def test_no_2019_2020_cycle_is_advertised():
    # Field work was cut short by COVID-19; those data ship as the
    # "2017-2020 pre-pandemic" files, and DEMO_K.XPT is a live 404.
    assert "2019-2020" not in NHANESTool._CYCLES
    assert _info(year="2019-2020")["status"] == "error"


def test_current_cycle_is_available():
    res = _info(year="2021-2023", component="Laboratory")

    assert res["status"] == "success"
    assert res["data"]["cycles_covered"] == ["2021-2023"]
    assert [d["year"] for d in res["data"]["datasets"]] == ["2021-2023"]


def test_earlier_published_cycles_are_available():
    for cycle in ("1999-2000", "2003-2004", "2005-2006"):
        res = _info(year=cycle, component="Demographics")
        assert res["status"] == "success", cycle
        assert res["data"]["datasets"][0]["year"] == cycle


def test_requested_year_is_the_year_returned():
    for cycle in NHANESTool._CYCLES:
        res = _info(year=cycle, component="Laboratory")
        assert res["status"] == "success", cycle
        assert {d["year"] for d in res["data"]["datasets"]} == {cycle}


def test_download_url_uses_the_live_cdc_datapage_form():
    res = _info(year="2017-2018", component="Laboratory")
    url = res["data"]["datasets"][0]["download_url"]

    assert url == (
        "https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx"
        "?Component=Laboratory&CycleBeginYear=2017"
    )
    # The old template pointed at a path CDC redirects to its error page.
    assert "laboratory_2017-2018.aspx" not in url


def test_omitting_year_covers_the_two_most_recent_cycles():
    res = _info(component="Demographics")

    assert res["data"]["cycles_covered"] == ["2021-2023", "2017-2018"]


def test_omitting_component_lists_every_component():
    res = _info(year="2017-2018")

    components = {d["component"] for d in res["data"]["datasets"]}
    assert components == set(NHANESTool._COMPONENTS)
    assert res["data"]["count"] == len(NHANESTool._COMPONENTS)


@pytest.mark.parametrize("cycle", NHANESTool._CYCLES)
def test_every_advertised_cycle_builds_a_datapage_url(cycle):
    res = _info(year=cycle, component="Examination")
    url = res["data"]["datasets"][0]["download_url"]

    assert url.endswith(f"CycleBeginYear={cycle.split('-')[0]}")
