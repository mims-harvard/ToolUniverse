import json
import os
import warnings
# Suppress RDKit warnings and pkg_resources warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="importlib._bootstrap")
warnings.filterwarnings("ignore", message=".*RDKit.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")

from tooluniverse import ToolUniverse
import pytest

# Skip schema validation for this example
schemas = {}

tooluni = ToolUniverse()
tooluni.load_tools()


def summarize_result(tool_name, res):
    if isinstance(res, str):
        return f"{tool_name}: INVALID Raw string response: {res[:200]}..."
    if isinstance(res, dict):
        if "error" in res:
            return f"{tool_name}: ERROR {res['error']}"
        data = res.get("data", {})
        total = data.get("Total") if isinstance(data, dict) else None
        msg = f"{tool_name}: SUCCESS"
        if isinstance(total, int):
            msg += f" | Total={total}"

        if tool_name == "odphp_myhealthfinder":
            heading = data.get("MyHFHeading", "")
            resources = (data.get("Resources", {}).get("All", {}).get("Resource", [])) or []
            first_title = resources[0].get("Title") if resources else None
            msg += f" | Heading='{heading[:60]}...'"
            if first_title:
                msg += f" | FirstResource='{first_title}'"
            callouts = (data.get("Callouts", {}).get("All", {}).get("Resource", [])) or []
            if callouts and callouts[0].get("MyHFTitle"):
                msg += f" | FirstCallout='{callouts[0].get('MyHFTitle')}'"

        elif tool_name == "odphp_itemlist":
            items = data.get("Items", {}).get("Item", []) or []
            titles = [i.get("Title") for i in items[:3]]
            if titles:
                msg += f" | ExampleItems={titles}"

        elif tool_name == "odphp_topicsearch":
            resources = data.get("Resources", {}).get("Resource", []) or []
            titles = [r.get("Title") for r in resources[:3]]
            if titles:
                msg += f" | ExampleTopics={titles}"

        elif tool_name.startswith("odphp_outlink_fetch"):
            results = res.get("results") or []
            if results:
                first = results[0]
                msg += f" | url={first.get('url')} status={first.get('status')} type={first.get('content_type')}"
                if first.get("title"):
                    msg += f" | Title='{first['title'][:50]}...'"
                if first.get("text"):
                    snippet = first["text"][:80].replace("\n", " ")
                    msg += f" | TextSnippet='{snippet}...'"

        expected_keys = schemas.get(tool_name, {}).get("properties", {}).keys()
        missing = [k for k in expected_keys if k not in data and k not in res]
        if missing:
            msg += f" | WARNING: Missing keys {missing}"
        else:
            msg += " | Schema OK"
        return msg
    return f"{tool_name}: INVALID Unexpected type {type(res)}"


def test_01_myhealthfinder_valid():
    res = tooluni.run({"name": "odphp_myhealthfinder",
                       "arguments": {"age": 35, "sex": "female", "pregnant": "no", "lang": "en"}})
    print(summarize_result("odphp_myhealthfinder", res))
    assert isinstance(res, dict) and not res.get("error")


def test_02_itemlist_valid():
    res = tooluni.run({"name": "odphp_itemlist", "arguments": {"type": "topic", "lang": "en"}})
    print(summarize_result("odphp_itemlist", res))
    assert isinstance(res, dict) and not res.get("error")


def test_03_topicsearch_keyword_valid():
    res = tooluni.run({"name": "odphp_topicsearch", "arguments": {"keyword": "cancer", "lang": "en"}})
    print(summarize_result("odphp_topicsearch", res))
    assert isinstance(res, dict) and not res.get("error")


def test_04_invalid_types_fail_fast():
    r1 = tooluni.run({"name": "odphp_myhealthfinder", "arguments": {"age": "banana"}})
    r2 = tooluni.run({"name": "odphp_topicsearch", "arguments": {"topicId": 123}})
    print("Expected type errors:", r1, r2)
    assert isinstance(r1, str) and "Type mismatches" in r1
    assert isinstance(r2, str) and "Type mismatches" in r2


def test_05_sections_case_and_strip_html():
    res = tooluni.run({"name": "odphp_topicsearch",
                       "arguments": {"keyword": "Keep Your Heart Healthy", "lang": "en", "strip_html": True}})
    print(summarize_result("odphp_topicsearch", res))
    assert isinstance(res, dict) and not res.get("error")
    data = res.get("data") or {}
    resources = (data.get("Resources") or {}).get("Resource") or []
    if resources:
        s_any = resources[0].get("Sections", {})
        arr = s_any.get("Section") or s_any.get("section") or []
        assert isinstance(arr, list)
        assert "PlainSections" in resources[0]


def test_06_outlink_fetch_accessible_version():
    url = "https://odphp.health.gov/myhealthfinder/health-conditions/heart-health/keep-your-heart-healthy"
    res = tooluni.run({"name": "odphp_outlink_fetch",
                       "arguments": {"urls": [url], "max_chars": 4000}})
    print(summarize_result("odphp_outlink_fetch", res))
    assert isinstance(res, dict) and not res.get("error")
    results = res.get("results") or []
    assert results and results[0].get("status") in (200, 301, 302)
    if "text/html" in (results[0].get("content_type") or ""):
        assert len(results[0].get("text", "")) > 100


def test_07_itemlist_spanish():
    res = tooluni.run({"name": "odphp_itemlist", "arguments": {"type": "topic", "lang": "es"}})
    print(summarize_result("odphp_itemlist", res))
    assert isinstance(res, dict) and not res.get("error")


def test_08_topicsearch_by_category():
    cats = tooluni.run({"name": "odphp_itemlist", "arguments": {"type": "category", "lang": "en"}})
    first_cat = (cats.get("data", {}).get("Items", {}).get("Item") or [])[0]
    cid = first_cat.get("Id")
    res = tooluni.run({"name": "odphp_topicsearch", "arguments": {"categoryId": cid, "lang": "en"}})
    print(summarize_result("odphp_topicsearch", res))
    assert isinstance(res, dict) and not res.get("error")

def test_09_outlink_fetch_pdf():
    url = "https://odphp.health.gov/sites/default/files/2021-12/DGA_Pregnancy_FactSheet-508.pdf"
    res = tooluni.run({"name": "odphp_outlink_fetch",
                       "arguments": {"urls": [url], "max_chars": 1000}})
    print(summarize_result("odphp_outlink_fetch_pdf", res))

    assert isinstance(res, dict) and not res.get("error")
    results = res.get("results") or []
    assert results, "No results returned for PDF URL"

    ctype = results[0].get("content_type", "")
    assert ctype.startswith("application/pdf"), f"Expected PDF but got {ctype}"

    # Ensure text extraction worked at least partially
    text = results[0].get("text", "")
    assert text and len(text) > 50, "Extracted PDF text too short"


if __name__ == "__main__":
    print("\nRunning ODPHP tool tests...\n")
    test_01_myhealthfinder_valid()
    test_02_itemlist_valid()
    test_03_topicsearch_keyword_valid()
    test_04_invalid_types_fail_fast()
    test_05_sections_case_and_strip_html()
    test_06_outlink_fetch_accessible_version()
    test_07_itemlist_spanish()
    test_08_topicsearch_by_category()
    test_09_outlink_fetch_pdf()
    print("\nAll ODPHP tests executed.\n")
