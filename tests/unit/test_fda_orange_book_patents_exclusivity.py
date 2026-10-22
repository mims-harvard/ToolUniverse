"""Unit tests for FDA Orange Book patent and exclusivity lookups. No network.

``get_patent_info`` and ``get_exclusivity`` used to return ``status: success``
with a download link and no patent or exclusivity data. They now read a local
copy of FDA's Orange Book data files (TOOLUNIVERSE_ORANGE_BOOK_DATA). The
fixture rows below are copied from the September 2026 files.

The file lists one row per patent use code and one row per exclusivity date;
the tool has to return every one of them (openFDA's /drug/orangebook endpoint
keeps one use code per product-patent pair, FDA/openfda#225).
"""

import io
import json
import os
import zipfile
from importlib.resources import files
from unittest.mock import patch

import pytest

from tooluniverse import ToolUniverse, fda_orange_book_tool
from tooluniverse.fda_orange_book_tool import FDAOrangeBookTool

_PRODUCTS = [
    "Ingredient~DF;Route~Trade_Name~Applicant~Strength~Appl_Type~Appl_No~Product_No~TE_Code~Approval_Date~RLD~RS~Type~Applicant_Full_Name",
    "OLAPARIB~TABLET;ORAL~LYNPARZA~ASTRAZENECA~100MG~N~208558~001~~Aug 17, 2017~Yes~No~RX~ASTRAZENECA PHARMACEUTICALS LP",
    "OLAPARIB~TABLET;ORAL~LYNPARZA~ASTRAZENECA~150MG~N~208558~002~~Aug 17, 2017~Yes~Yes~RX~ASTRAZENECA PHARMACEUTICALS LP",
    "SELINEXOR~TABLET;ORAL~XPOVIO~KARYOPHARM THERAPS~40MG~N~212306~002~~Apr 15, 2021~Yes~No~RX~KARYOPHARM THERAPEUTICS INC",
    "IBUPROFEN~TABLET;ORAL~ADVIL~HALEON US HOLDINGS~200MG~N~018989~001~~Approved Prior to Jan 1, 1982~Yes~Yes~OTC~HALEON US HOLDINGS LLC",
]
_PATENTS = [
    "Appl_Type~Appl_No~Product_No~Patent_No~Patent_Expire_Date_Text~Drug_Substance_Flag~Drug_Product_Flag~Patent_Use_Code~Delist_Flag~Submission_Date",
    "N~208558~001~8143241~Aug 12, 2027~~~U-2482~~Sep 15, 2017",
    "N~208558~001~8143241~Aug 12, 2027~~~U-2480~~Sep 15, 2017",
    "N~208558~001~8143241~Aug 12, 2027~~~U-2819~~Sep 15, 2017",
    "N~208558~001~7449464~Sep 8, 2027~Y~Y~~~Sep 15, 2017",
    "N~208558~001~11970530~Oct 25, 2041~~~U-3929~~May 28, 2024",
    "N~212306~002~10519139~Aug 14, 2035~Y~Y~U-2584~~Jan 27, 2020",
]
_EXCLUSIVITY = [
    "Appl_Type~Appl_No~Product_No~Exclusivity_Code~Exclusivity_Date",
    "N~212306~002~ODE*~Jun 22, 2027",
    "N~212306~002~ODE*~Dec 18, 2027",
    "N~212306~002~ODE*~Jul 3, 2026",
    "N~208558~001~ODE-283~Dec 27, 2026",
]


def _zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, lines in (
            ("products.txt", _PRODUCTS),
            ("patent.txt", _PATENTS),
            ("exclusivity.txt", _EXCLUSIVITY),
        ):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 11, 4, 31, 0))
            zf.writestr(info, "\r\n".join(lines) + "\r\n")
    return buf.getvalue()


def _tool(name):
    configs = json.loads(
        (files("tooluniverse.data") / "fda_orange_book_tools.json").read_text()
    )
    return FDAOrangeBookTool(next(t for t in configs if t["name"] == name))


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.delenv(fda_orange_book_tool.ORANGE_BOOK_ENV, raising=False)
    fda_orange_book_tool._orange_book_cache.clear()
    # The tool never downloads the data files.
    with patch.object(
        fda_orange_book_tool.requests, "get", side_effect=AssertionError("network")
    ):
        yield
    fda_orange_book_tool._orange_book_cache.clear()


@pytest.fixture
def ob_zip(tmp_path, monkeypatch):
    path = tmp_path / "EOBZIP_2026_09.zip"
    path.write_bytes(_zip_bytes())
    monkeypatch.setenv(fda_orange_book_tool.ORANGE_BOOK_ENV, str(path))
    return path


def _patent(result, product_number, patent_number):
    product = next(
        p for p in result["data"]["products"] if p["product_number"] == product_number
    )
    return next(p for p in product["patents"] if p["patent_number"] == patent_number)


def test_patent_keeps_every_use_code(ob_zip):
    result = _tool("FDA_OrangeBook_get_patent_info").run({"brand_name": "Lynparza"})
    assert result["status"] == "success"
    assert result["data"]["count"] == 2
    patent = _patent(result, "001", "8143241")
    assert patent["use_codes"] == ["U-2482", "U-2480", "U-2819"]
    assert patent["expiration_date"] == "2027-08-12"
    assert patent["submission_date"] == "2017-09-15"
    substance = _patent(result, "001", "7449464")
    assert substance["drug_substance"] and substance["drug_product"]
    assert substance["use_codes"] == []
    assert result["data"]["source"]["files_dated"] == "2026-09-11"


def test_patents_sorted_by_expiry_and_product_without_patents(ob_zip):
    result = _tool("FDA_OrangeBook_get_patent_info").run(
        {"application_number": "NDA208558"}
    )
    first, second = result["data"]["products"]
    assert [p["patent_number"] for p in first["patents"]] == [
        "8143241",
        "7449464",
        "11970530",
    ]
    assert second["patents"] == []
    assert result["data"]["patent_count"] == 3


@pytest.mark.parametrize("number", ["NDA212306", "N212306", "212306", "nda 212306"])
def test_application_number_forms(ob_zip, number):
    result = _tool("FDA_OrangeBook_get_exclusivity").run({"application_number": number})
    assert result["status"] == "success"
    assert [p["application_number"] for p in result["data"]["products"]] == ["N212306"]


def test_exclusivity_keeps_every_date(ob_zip):
    result = _tool("FDA_OrangeBook_get_exclusivity").run(
        {"application_number": "NDA212306"}
    )
    (product,) = result["data"]["products"]
    assert product["exclusivity"] == [
        {"code": "ODE*", "expiration_date": "2026-07-03"},
        {"code": "ODE*", "expiration_date": "2027-06-22"},
        {"code": "ODE*", "expiration_date": "2027-12-18"},
    ]


def test_no_patents_is_success_with_note(ob_zip):
    result = _tool("FDA_OrangeBook_get_patent_info").run({"brand_name": "ADVIL"})
    assert result["status"] == "success"
    assert result["data"]["patent_count"] == 0
    assert "No patents" in result["data"]["note"]


def test_no_match_is_empty_success(ob_zip):
    result = _tool("FDA_OrangeBook_get_exclusivity").run({"brand_name": "NOSUCHDRUG"})
    assert result["status"] == "success"
    assert result["data"]["products"] == []
    assert "not biologics" in result["data"]["note"]


def test_missing_and_bad_arguments(ob_zip):
    tool = _tool("FDA_OrangeBook_get_patent_info")
    assert tool.run({})["status"] == "error"
    assert "Unrecognized" in tool.run({"application_number": "BLA125514"})["error"]


@pytest.mark.parametrize(
    "name", ["FDA_OrangeBook_get_patent_info", "FDA_OrangeBook_get_exclusivity"]
)
def test_not_configured_tool_loads_and_errors_not_empty_success(name):
    # A data path is not an API key: the tool stays in the catalog and the
    # call says what to set, rather than the tool silently not loading.
    tu = ToolUniverse()
    tu.load_tools(include_tools=[name])
    assert name in tu.all_tool_dict

    result = tu.run_one_function(
        {"name": name, "arguments": {"brand_name": "LYNPARZA"}}
    )
    assert result["status"] == "error"
    assert f"{fda_orange_book_tool.ORANGE_BOOK_ENV} is not set" in result["error"]
    assert fda_orange_book_tool.ORANGE_BOOK_PAGE_URL in result["error"]


def test_missing_path_is_error(tmp_path, monkeypatch):
    monkeypatch.setenv(fda_orange_book_tool.ORANGE_BOOK_ENV, str(tmp_path / "no.zip"))
    result = _tool("FDA_OrangeBook_get_exclusivity").run({"brand_name": "XPOVIO"})
    assert result["status"] == "error"
    assert "does not exist" in result["error"]


def test_extracted_folder_rebuilt_when_a_file_is_replaced(tmp_path, monkeypatch):
    with zipfile.ZipFile(io.BytesIO(_zip_bytes())) as zf:
        zf.extractall(tmp_path)
    monkeypatch.setenv(fda_orange_book_tool.ORANGE_BOOK_ENV, str(tmp_path))
    tool = _tool("FDA_OrangeBook_get_patent_info")
    result = tool.run({"brand_name": "LYNPARZA"})
    assert result["status"] == "success"
    assert _patent(result, "001", "8143241")["use_codes"] == [
        "U-2482",
        "U-2480",
        "U-2819",
    ]
    patent_file = tmp_path / "patent.txt"
    patent_file.write_text(_PATENTS[0] + "\r\n")
    stat = patent_file.stat()
    os.utime(patent_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    assert tool.run({"brand_name": "LYNPARZA"})["data"]["patent_count"] == 0


def test_index_built_once_and_rebuilt_when_file_changes(ob_zip):
    tool = FDAOrangeBookTool
    with patch.object(tool, "_read_ob_source", wraps=tool._read_ob_source) as read:
        _tool("FDA_OrangeBook_get_patent_info").run({"brand_name": "LYNPARZA"})
        _tool("FDA_OrangeBook_get_exclusivity").run({"brand_name": "XPOVIO"})
        assert read.call_count == 1
        stat = ob_zip.stat()
        os.utime(ob_zip, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
        _tool("FDA_OrangeBook_get_exclusivity").run({"brand_name": "XPOVIO"})
        assert read.call_count == 2
