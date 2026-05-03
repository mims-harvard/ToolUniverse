"""Tests for tool description discoverability improvements.

Validates that key search/discovery tools have descriptions that clearly
distinguish them from ID-lookup tools, making them more discoverable
via natural language queries in find_tools.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "data"
)


class TestClinicalTrialsSearchDiscoverability(unittest.TestCase):
    """search_clinical_trials should be clearly discoverable for keyword searches."""

    def setUp(self):
        with open(os.path.join(DATA_DIR, "clinicaltrials_gov_tools.json")) as f:
            self.tools = json.load(f)
        self.search_tool = next(
            t for t in self.tools if t["name"] == "search_clinical_trials"
        )

    def test_description_mentions_disease_condition(self):
        desc = self.search_tool["description"].lower()
        self.assertIn("disease", desc)
        self.assertIn("condition", desc)

    def test_description_mentions_drug_intervention(self):
        desc = self.search_tool["description"].lower()
        self.assertIn("drug", desc)
        self.assertIn("intervention", desc)

    def test_description_identifies_as_primary_search(self):
        desc = self.search_tool["description"].lower()
        self.assertIn("primary", desc)

    def test_description_includes_example_drugs(self):
        desc = self.search_tool["description"].lower()
        # Should mention at least one example drug name
        has_example = any(
            drug in desc
            for drug in ["olaparib", "pembrolizumab", "imatinib", "osimertinib"]
        )
        self.assertTrue(has_example, "Description should include example drug names")

    def test_description_includes_example_diseases(self):
        desc = self.search_tool["description"].lower()
        has_example = any(
            disease in desc
            for disease in ["lung cancer", "diabetes", "breast cancer"]
        )
        self.assertTrue(has_example, "Description should include example disease names")


class TestGWASSearchDiscoverability(unittest.TestCase):
    """gwas_search_associations should be discoverable for keyword trait searches."""

    def setUp(self):
        with open(os.path.join(DATA_DIR, "gwas_tools.json")) as f:
            self.tools = json.load(f)
        self.search_tool = next(
            t for t in self.tools if t["name"] == "gwas_search_associations"
        )

    def test_description_mentions_keyword_search(self):
        desc = self.search_tool["description"].lower()
        self.assertIn("keyword", desc)

    def test_description_includes_example_traits(self):
        desc = self.search_tool["description"].lower()
        has_example = any(
            trait in desc
            for trait in ["melanoma", "diabetes", "breast cancer"]
        )
        self.assertTrue(has_example, "Description should include example traits")

    def test_description_identifies_as_primary_tool(self):
        desc = self.search_tool["description"].lower()
        self.assertIn("primary", desc)

    def test_description_mentions_snp_rs_id(self):
        desc = self.search_tool["description"].lower()
        self.assertTrue(
            "rs id" in desc or "snp" in desc,
            "Description should mention SNP/rs ID capability",
        )


class TestGWASVariantsForTraitDiscoverability(unittest.TestCase):
    """gwas_get_variants_for_trait should be discoverable for trait-based variant search."""

    def setUp(self):
        with open(os.path.join(DATA_DIR, "gwas_tools.json")) as f:
            self.tools = json.load(f)
        self.search_tool = next(
            t for t in self.tools if t["name"] == "gwas_get_variants_for_trait"
        )

    def test_description_mentions_disease_trait(self):
        desc = self.search_tool["description"].lower()
        self.assertIn("disease", desc)
        self.assertIn("trait", desc)

    def test_description_mentions_variants_snps(self):
        desc = self.search_tool["description"].lower()
        self.assertTrue(
            "variant" in desc or "snp" in desc,
            "Description should mention variants or SNPs",
        )

    def test_description_includes_examples(self):
        desc = self.search_tool["description"].lower()
        has_example = any(
            ex in desc for ex in ["diabetes", "breast cancer", "melanoma"]
        )
        self.assertTrue(has_example, "Description should include example diseases")


class TestSearchToolsDistinctFromIDTools(unittest.TestCase):
    """Search tools should be clearly distinct from ID-lookup tools."""

    def test_clinical_trials_search_vs_get(self):
        with open(os.path.join(DATA_DIR, "clinicaltrials_gov_tools.json")) as f:
            tools = json.load(f)

        search_tool = next(t for t in tools if t["name"] == "search_clinical_trials")
        get_tools = [t for t in tools if t["name"].startswith("get_clinical_trial")]

        # Search tool description should NOT require NCT IDs
        self.assertNotIn("NCT ID", search_tool["description"].split(".")[0])

        # Get tools should mention NCT IDs
        for gt in get_tools:
            self.assertIn("NCT ID", gt["description"])

    def test_gwas_search_vs_get(self):
        with open(os.path.join(DATA_DIR, "gwas_tools.json")) as f:
            tools = json.load(f)

        search_tool = next(
            t for t in tools if t["name"] == "gwas_search_associations"
        )
        id_tools = [
            t
            for t in tools
            if t["name"]
            in ("gwas_get_association_by_id", "gwas_get_study_by_id", "gwas_get_snp_by_id")
        ]

        # Search tool should mention free-text/keyword
        desc_lower = search_tool["description"].lower()
        self.assertTrue(
            "keyword" in desc_lower or "free-text" in desc_lower,
            "Search tool should mention keyword/free-text search",
        )

        # ID tools should mention "identifier" or "ID" (require specific ID input)
        for idt in id_tools:
            desc_lower = idt["description"].lower()
            self.assertTrue(
                "identifier" in desc_lower or " id" in desc_lower,
                f"{idt['name']} should mention identifier or ID",
            )


if __name__ == "__main__":
    unittest.main()
