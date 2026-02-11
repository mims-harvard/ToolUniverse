# ODPHP Tools (MyHealthfinder + ItemList + TopicSearch + Outlink Fetch)

**What it is.** A fast, agent-aligned interface to the U.S. Office of Disease Prevention and Health Promotion (ODPHP) **MyHealthfinder API**:

* **Personalized preventive-care recommendations** (`odphp_myhealthfinder`) given demographics (age, sex, pregnancy status).
* **Catalog browsing** (`odphp_itemlist`) for all topics and categories.
* **Targeted topic lookup** (`odphp_topicsearch`) by keyword, topicId, or categoryId.
* **Full content dereferencing** (`odphp_outlink_fetch`) to retrieve the actual article text or PDF from AccessibleVersion/RelatedItems links.
* Exposed to ToolUniverse as **4 agent-visible tools** via JSON config.

---

## Files & flow

```text
odphp_tool.py           # runtime adapter classes: MyHealthfinder, ItemList, TopicSearch, OutlinkFetch
data/odphp_tools.json   # JSON configs with schema/fields/return_schema for all 4 tools
test_odphp_tool.py      # smoke & schema tests, edge cases, readable summaries
```

**Adapters**

* `ODPHPMyHealthfinder`: queries `/myhealthfinder.json` (demographic inputs to preventive care resources).
* `ODPHPItemList`: queries `/itemlist.json` (topics & categories).
* `ODPHPTopicSearch`: queries `/topicsearch.json` (keyword/IDs to detailed topic pages).
* `ODPHPOutlinkFetch`: dereferences article links (HTML/PDF to text + metadata).

---

## How to use (from Python)

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()  # or tu.load_tools(tool_type=["odphp"])

# Example: 35-year-old pregnant woman
rows = tu.run({
  "name": "odphp_myhealthfinder",
  "arguments": {"age": 35, "sex": "female", "pregnant": "yes", "lang": "en"}
})

# Pick AccessibleVersion URLs, then dereference
out = tu.run({
  "name": "odphp_outlink_fetch",
  "arguments": {
    "urls": [r["AccessibleVersion"] for r in rows["Resources"]["All"]["Resource"][:2]],
    "max_chars": 2000
  }
})
```

---

## When to use what

* Use **`odphp_myhealthfinder`** when the user gives **demographics** (age, sex, pregnant) or asks *“what screenings/vaccines/checkups do I need?”*.
* Use **`odphp_itemlist`** to **browse all topics or categories** (like a table of contents).
* Use **`odphp_topicsearch`** when the user says a **condition/keyword** (“folic acid”, “blood pressure”) or when you already have IDs.
* Use **`odphp_outlink_fetch`** when you need the **actual article text or PDF** (AccessibleVersion, RelatedItems).

---

## End-to-end pipeline (MyHealthfinder to Outlink Fetch)

The tools are designed to be chained:

1. **Demographic query** (`odphp_myhealthfinder`)

   * Input: demographics (age, sex, pregnant) + language.
   * Output: resources with metadata and AccessibleVersion links.

   ```javascript
   {
     "Total": 24,
     "MyHFHeading": "Here are important ways for a woman age 35 to stay healthy...",
     "Resources": {
       "All": {
         "Resource": [
           {
             "Id": "327",
             "Title": "Get Enough Folic Acid",
             "AccessibleVersion": "https://odphp.health.gov/myhealthfinder/topics/everyday-healthy-living/nutrition/get-enough-folic-acid",
             "RelatedItems": {...},
             "Sections": {...}
           },
           ...
         ]
       }
     }
   }
   ```

2. **Outlink dereference** (`odphp_outlink_fetch`)

   * Input: 1–3 URLs from AccessibleVersion or RelatedItems.
   * Output: cleaned article text, with metadata and PDF detection.

   ```javascript
   {
     "results": [
       {
         "url": "https://odphp.health.gov/myhealthfinder/.../get-enough-folic-acid",
         "status": 200,
         "content_type": "text/html",
         "title": "Get Enough Folic Acid",
         "text": "It's important for a woman who can get pregnant...",
       }
     ]
   }
   ```

   Content types:

   * `text/html`: text extracted via BeautifulSoup (or regex fallback).
   * `application/pdf`: metadata + link returned.
   * Other: link + best-effort handling.

3. **Next steps for an agent**

   * If user asked for “full details” then feed `text` into summarizer or directly quote.
   * If PDF returned then pass to PDF reader tool.
   * If broken/outdated link then fallback to RelatedItems or report unavailability.

---

## Tests (smoke & shape)

**src/tooluniverse/test/test\_odphp\_tool.py** includes:

* Valid demographic query (age 35 female pregnant=no).
* Keyword/topic search (e.g., “cancer”).
* Category browsing (topics vs categories).
* Outlink fetch for HTML and PDFs (Pregnancy Fact Sheet).
* Spanish topics (`lang="es"`).
* Edge cases: invalid params, schema compliance, HTML stripping.

---

## Agent rubric

* Start with **MyHealthfinder** when demographics are known.
* Use **TopicSearch** when keywords or IDs are given.
* Use **ItemList** to explore available topics/categories.
* Always use **OutlinkFetch** to **close the loop** from metadata to actionable content.