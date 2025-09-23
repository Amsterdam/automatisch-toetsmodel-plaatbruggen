"""Tests for SCIA results units handling."""

import unittest
from typing import Any
from unittest.mock import Mock

from src.integrations.scia_integration.scia_results_creator import (
    build_units_mapping,
    extract_analysis_results,
)


class TestBuildUnitsMapping(unittest.TestCase):
    """Test the build_units_mapping function."""

    def test_units_mapping_2d_table(self) -> None:
        """Test units mapping for 2D plate forces."""
        results = {"internal_forces": {"table_name": "Internal Forces 2D"}}
        units = build_units_mapping(results)

        # Check 2D plate units (per unit length)
        assert units["internal_forces"]["Vy"] == "kN/m"
        assert units["internal_forces"]["Vz"] == "kN/m"
        assert units["internal_forces"]["N"] == "kN/m"
        assert units["internal_forces"]["Mxd+"] == "kNm/m"
        assert units["internal_forces"]["Mxd-"] == "kNm/m"
        assert units["internal_forces"]["Myd+"] == "kNm/m"
        assert units["internal_forces"]["Myd-"] == "kNm/m"

        # Check raw SCIA field keys for 2D
        assert units["internal_forces"]["m_x"] == "kNm/m"
        assert units["internal_forces"]["v_x"] == "kN/m"
        assert units["internal_forces"]["n_x"] == "kN/m"

    def test_units_mapping_1d_table(self) -> None:
        """Test units mapping for 1D beam forces."""
        results = {"internal_forces": {"table_name": "Internal Forces 1D"}}
        units = build_units_mapping(results)

        # Check 1D beam units (absolute values)
        assert units["internal_forces"]["Vy"] == "kN"
        assert units["internal_forces"]["Vz"] == "kN"
        assert units["internal_forces"]["N"] == "kN"
        assert units["internal_forces"]["Mxd+"] == "kNm"
        assert units["internal_forces"]["Mxd-"] == "kNm"
        assert units["internal_forces"]["Myd+"] == "kNm"
        assert units["internal_forces"]["Myd-"] == "kNm"

        # Check standard 1D beam force keys
        assert units["internal_forces"]["Mx"] == "kNm"
        assert units["internal_forces"]["My"] == "kNm"

    def test_units_mapping_case_insensitive(self) -> None:
        """Test that table name matching is case insensitive."""
        # Test lowercase 2d
        results = {"internal_forces": {"table_name": "internal forces 2d"}}
        units = build_units_mapping(results)
        assert units["internal_forces"]["Vy"] == "kN/m"

        # Test lowercase 1d
        results = {"internal_forces": {"table_name": "internal forces 1d"}}
        units = build_units_mapping(results)
        assert units["internal_forces"]["Vy"] == "kN"

    def test_units_mapping_unknown_table_defaults_to_1d(self) -> None:
        """Test that unknown table names default to 1D units."""
        results = {"internal_forces": {"table_name": "Unknown Table"}}
        units = build_units_mapping(results)

        # Should default to 1D units
        assert units["internal_forces"]["Vy"] == "kN"
        assert units["internal_forces"]["Mxd+"] == "kNm"

    def test_units_mapping_missing_table_name_defaults_to_1d(self) -> None:
        """Test that missing table name defaults to 1D units."""
        results: dict[str, Any] = {"internal_forces": {}}
        units = build_units_mapping(results)

        # Should default to 1D units
        assert units["internal_forces"]["Vy"] == "kN"
        assert units["internal_forces"]["Mxd+"] == "kNm"

    def test_units_mapping_missing_internal_forces_defaults_to_1d(self) -> None:
        """Test that missing internal_forces section defaults to 1D units."""
        results: dict[str, Any] = {}
        units = build_units_mapping(results)

        # Should default to 1D units
        assert units["internal_forces"]["Vy"] == "kN"
        assert units["internal_forces"]["Mxd+"] == "kNm"

    def test_units_mapping_non_dict_internal_forces_defaults_to_1d(self) -> None:
        """Test that non-dict internal_forces defaults to 1D units."""
        results = {"internal_forces": "not a dict"}
        units = build_units_mapping(results)

        # Should default to 1D units
        assert units["internal_forces"]["Vy"] == "kN"
        assert units["internal_forces"]["Mxd+"] == "kNm"

    def test_units_mapping_contains_all_envelope_components(self) -> None:
        """Test that units mapping contains all expected envelope components."""
        results = {"internal_forces": {"table_name": "Internal Forces 1D"}}
        units = build_units_mapping(results)

        # Check that all expected envelope components are present
        expected_components = ["N", "Vy", "Vz", "Mxd+", "Mxd-", "Myd+", "Myd-"]
        for component in expected_components:
            assert component in units["internal_forces"], f"Missing component: {component}"


class TestExtractAnalysisResults(unittest.TestCase):
    """Test the extract_analysis_results function with units attachment."""

    def test_extract_analysis_results_attaches_units_2d(self) -> None:
        """Test that extract_analysis_results attaches units for 2D tables."""
        # Mock builder and analysis
        mock_builder = Mock()
        mock_analysis = Mock()

        # Mock the builder's extract method to return 2D results
        mock_builder.extract_analysis_results.return_value = {
            "internal_forces": {"table_name": "Internal Forces 2D", "status": "success"},
            "analysis_status": {"executed": True},
        }

        # Call the function
        results = extract_analysis_results(mock_builder, mock_analysis)

        # Check that units are attached at top level
        assert "units" in results
        assert "internal_forces" in results["units"]
        assert results["units"]["internal_forces"]["N"] == "kN/m"
        assert results["units"]["internal_forces"]["Myd+"] == "kNm/m"

        # Check that units are also attached to internal_forces for convenience
        assert "units" in results["internal_forces"]
        assert results["internal_forces"]["units"]["N"] == "kN/m"
        assert results["internal_forces"]["units"]["Myd-"] == "kNm/m"

    def test_extract_analysis_results_attaches_units_1d(self) -> None:
        """Test that extract_analysis_results attaches units for 1D tables."""
        # Mock builder and analysis
        mock_builder = Mock()
        mock_analysis = Mock()

        # Mock the builder's extract method to return 1D results
        mock_builder.extract_analysis_results.return_value = {
            "internal_forces": {"table_name": "Internal Forces 1D", "status": "success"},
            "analysis_status": {"executed": True},
        }

        # Call the function
        results = extract_analysis_results(mock_builder, mock_analysis)

        # Check that units are attached with 1D values
        assert results["units"]["internal_forces"]["N"] == "kN"
        assert results["units"]["internal_forces"]["Myd+"] == "kNm"
        assert results["internal_forces"]["units"]["Vy"] == "kN"

    def test_extract_analysis_results_handles_missing_internal_forces(self) -> None:
        """Test that extract_analysis_results handles missing internal_forces gracefully."""
        # Mock builder and analysis
        mock_builder = Mock()
        mock_analysis = Mock()

        # Mock the builder's extract method to return results without internal_forces
        mock_builder.extract_analysis_results.return_value = {
            "analysis_status": {"executed": True},
        }

        # Call the function
        results = extract_analysis_results(mock_builder, mock_analysis)

        # Check that units are still attached (defaults to 1D)
        assert "units" in results
        assert "internal_forces" in results["units"]
        assert results["units"]["internal_forces"]["N"] == "kN"

        # internal_forces section should not have units added since it doesn't exist
        assert "internal_forces" not in results or "units" not in results.get("internal_forces", {})

    def test_extract_analysis_results_handles_non_dict_internal_forces(self) -> None:
        """Test that extract_analysis_results handles non-dict internal_forces."""
        # Mock builder and analysis
        mock_builder = Mock()
        mock_analysis = Mock()

        # Mock the builder's extract method to return non-dict internal_forces
        mock_builder.extract_analysis_results.return_value = {
            "internal_forces": "not a dict",
            "analysis_status": {"executed": True},
        }

        # Call the function
        results = extract_analysis_results(mock_builder, mock_analysis)

        # Check that units are still attached (defaults to 1D)
        assert "units" in results
        assert results["units"]["internal_forces"]["N"] == "kN"

        # internal_forces should remain unchanged since it's not a dict
        assert results["internal_forces"] == "not a dict"

    def test_extract_analysis_results_includes_validation_and_summary(self) -> None:
        """Test that extract_analysis_results includes validation and summary."""
        # Mock builder and analysis
        mock_builder = Mock()
        mock_analysis = Mock()

        # Mock the builder's extract method
        mock_builder.extract_analysis_results.return_value = {
            "internal_forces": {"table_name": "Internal Forces 1D", "status": "success"},
            "analysis_status": {"executed": True},
        }

        # Call the function
        results = extract_analysis_results(mock_builder, mock_analysis)

        # Check that validation and summary are included
        assert "validation" in results
        assert "result_summary" in results
        assert "units" in results

        # Check validation structure
        assert "is_valid" in results["validation"]
        assert "messages" in results["validation"]

        # Check summary structure
        assert "analysis_successful" in results["result_summary"]


if __name__ == "__main__":
    unittest.main()
