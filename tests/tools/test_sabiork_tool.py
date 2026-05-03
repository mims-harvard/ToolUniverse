"""Unit tests for SABIO-RK tool."""

import json
import pytest
from unittest.mock import patch, MagicMock


ENTRY_IDS_XML = """<SabioEntryIDs>
  <SabioEntryID>11020</SabioEntryID>
  <SabioEntryID>11021</SabioEntryID>
  <SabioEntryID>11022</SabioEntryID>
</SabioEntryIDs>"""

SBML_XML = """<?xml version='1.0' encoding='UTF-8'?>
<sbml xmlns="http://www.sbml.org/sbml/level3/version1/core" level="3" version="1">
  <model name="test">
    <listOfSpecies>
      <species id="SPC_56_Cell" name="Ethanol" compartment="c" constant="false"
               hasOnlySubstanceUnits="false" boundaryCondition="false"/>
      <species id="SPC_37_Cell" name="NAD+" compartment="c" constant="false"
               hasOnlySubstanceUnits="false" boundaryCondition="false"/>
      <species id="SPC_1292_Cell" name="Acetaldehyde" compartment="c" constant="false"
               hasOnlySubstanceUnits="false" boundaryCondition="false"/>
    </listOfSpecies>
    <listOfReactions>
      <reaction id="REAC_0">
        <listOfReactants>
          <speciesReference species="SPC_56_Cell"/>
          <speciesReference species="SPC_37_Cell"/>
        </listOfReactants>
        <listOfProducts>
          <speciesReference species="SPC_1292_Cell"/>
        </listOfProducts>
        <kineticLaw>
          <listOfLocalParameters>
            <localParameter id="kcat" value="4.916667" units="swedgeone"
                            name="kcat" sboTerm="SBO:0000025"/>
            <localParameter id="Km_SPC_56_Cell" value="0.0041" units="M"
                            name="Km_Ethanol" sboTerm="SBO:0000027"/>
            <localParameter id="Ki_SPC_9941_Cell" value="4.3E-7" units="M"
                            name="Ki_Fomepizole" sboTerm="SBO:0000261"/>
          </listOfLocalParameters>
        </kineticLaw>
      </reaction>
    </listOfReactions>
  </model>
</sbml>"""


class TestSABIORKToolDirect:
    @pytest.fixture
    def tool_config(self):
        with open("src/tooluniverse/data/sabiork_tools.json") as f:
            return json.load(f)[0]

    @pytest.fixture
    def tool(self, tool_config):
        from tooluniverse.sabiork_tool import SABIORKTool

        return SABIORKTool(tool_config)

    def test_missing_query_params(self, tool):
        result = tool.run({"operation": "search_reactions"})
        assert result["status"] == "error"
        assert "At least one" in result["error"]

    def test_unknown_operation(self, tool):
        result = tool.run({"operation": "nonexistent"})
        assert result["status"] == "error"
        assert "Unknown operation" in result["error"]

    @patch("tooluniverse.sabiork_tool.requests.get")
    def test_search_by_ec_number(self, mock_get, tool):
        # Mock entry ID response then SBML response
        mock_ids_resp = MagicMock()
        mock_ids_resp.status_code = 200
        mock_ids_resp.text = ENTRY_IDS_XML

        mock_sbml_resp = MagicMock()
        mock_sbml_resp.status_code = 200
        mock_sbml_resp.text = SBML_XML

        mock_get.side_effect = [mock_ids_resp, mock_sbml_resp]

        result = tool.run(
            {"operation": "search_reactions", "ec_number": "1.1.1.1", "limit": 3}
        )
        assert result["status"] == "success"
        data = result["data"]
        assert data["total_count"] == 3
        assert len(data["kinetic_laws"]) >= 1

        law = data["kinetic_laws"][0]
        assert "Ethanol" in law["substrates"]
        assert "Acetaldehyde" in law["products"]
        assert len(law["parameters"]) == 3

        # Check parameter types
        ptypes = {p["type"] for p in law["parameters"]}
        assert "kcat" in ptypes
        assert "Km" in ptypes
        assert "Ki" in ptypes

    @patch("tooluniverse.sabiork_tool.requests.get")
    def test_no_results(self, mock_get, tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "no data found"
        mock_get.return_value = mock_resp

        result = tool.run(
            {"operation": "search_reactions", "enzyme_name": "nonexistent enzyme"}
        )
        assert result["status"] == "success"
        assert result["data"]["total_count"] == 0

    def test_build_query_combined(self, tool):
        q = tool._build_query(
            {
                "ec_number": "1.1.1.1",
                "organism": "Homo sapiens",
                "substrate": "ethanol",
            }
        )
        assert "ecnumber:1.1.1.1" in q
        assert 'Organism:"Homo sapiens"' in q
        assert 'Substrate:"ethanol"' in q
        assert " AND " in q


class TestSABIORKToolParsing:
    def test_parse_entry_ids(self):
        from tooluniverse.sabiork_tool import _parse_entry_ids

        ids = _parse_entry_ids(ENTRY_IDS_XML)
        assert ids == ["11020", "11021", "11022"]

    def test_parse_sbml_kinetics(self):
        from tooluniverse.sabiork_tool import _parse_sbml_kinetics

        records = _parse_sbml_kinetics(SBML_XML)
        assert len(records) == 1
        rec = records[0]
        assert "Ethanol" in rec["substrates"]
        assert "Acetaldehyde" in rec["products"]

        # Check kinetic parameters
        params = rec["parameters"]
        kcat = next(p for p in params if p["type"] == "kcat")
        assert kcat["value"] == pytest.approx(4.916667)
        assert kcat["unit"] == "s^{-1}"

        km = next(p for p in params if p["type"] == "Km")
        assert km["value"] == pytest.approx(0.0041)
        assert km["unit"] == "M"

        ki = next(p for p in params if p["type"] == "Ki")
        assert ki["value"] == pytest.approx(4.3e-7)


class TestSABIORKToolIntegration:
    """Integration tests that hit the real SABIO-RK API."""

    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()
        return tu

    @pytest.mark.integration
    def test_tool_registered(self, tu):
        assert "SABIO_RK_search_reactions" in tu.all_tool_dict

    @pytest.mark.integration
    def test_search_ec_number_real(self, tu):
        result = tu.run_one_function(
            {
                "name": "SABIO_RK_search_reactions",
                "arguments": {"ec_number": "1.1.1.1", "limit": 3},
            }
        )
        assert result["status"] == "success"
        data = result["data"]
        assert data["total_count"] > 0
        assert data["returned_count"] > 0
        assert len(data["kinetic_laws"]) > 0

    @pytest.mark.integration
    def test_search_substrate_real(self, tu):
        result = tu.run_one_function(
            {
                "name": "SABIO_RK_search_reactions",
                "arguments": {"substrate": "ethanol", "limit": 3},
            }
        )
        assert result["status"] == "success"
        assert result["data"]["total_count"] > 0
