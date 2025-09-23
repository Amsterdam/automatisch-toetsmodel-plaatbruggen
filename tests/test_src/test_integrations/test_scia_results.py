"""
Tests for SCIA results extraction and processing utilities.

This module tests the functions in src.integrations.scia_integration.scia_results_creator.
"""

import unittest
from unittest.mock import MagicMock

import pytest

from src.integrations.scia_integration.scia_results_creator import (
    extract_analysis_results,
    get_result_summary,
    validate_analysis_results,
)


class TestSciaResults(unittest.TestCase):
    """Test cases for SCIA results extraction functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_analysis = MagicMock()
        self.mock_builder = MagicMock()

        # Configure the mock builder's extract_analysis_results method
        self.mock_builder.extract_analysis_results.return_value = {
            "xml_output_file": MagicMock(),
            "displacements": {"status": "not_implemented"},
            "internal_forces": {"status": "not_implemented"},
            "reactions": {"status": "not_implemented"},
            "stresses": {"status": "not_implemented"},
            "analysis_status": {"executed": True, "has_results": True},
        }

    def test_extract_analysis_results_success(self) -> None:
        """Test successful extraction of analysis results."""
        # Call function
        results = extract_analysis_results(self.mock_builder, self.mock_analysis)

        # Verify that builder.extract_analysis_results was called
        self.mock_builder.extract_analysis_results.assert_called_once_with(self.mock_analysis)

        # Verify results structure
        assert "validation" in results
        assert "result_summary" in results
        assert results["validation"]["is_valid"] is True

    def test_extract_analysis_results_exception(self) -> None:
        """Test extraction when an exception occurs."""
        self.mock_builder.extract_analysis_results.side_effect = Exception("Test error")

        with pytest.raises(ValueError) as context:
            extract_analysis_results(self.mock_builder, self.mock_analysis)

        assert "Failed to extract SCIA analysis results" in str(context.value)

    def test_get_result_summary_success(self) -> None:
        """Test result summary generation for successful analysis."""
        results = {
            "analysis_status": {"executed": True, "error_message": None},
            "displacements": {"status": "not_implemented"},
            "internal_forces": {"status": "not_implemented"},
            "reactions": {"status": "not_implemented"},
            "stresses": {"status": "not_implemented"},
        }

        summary = get_result_summary(results)

        assert summary["analysis_successful"]
        assert not summary["has_displacements"]
        assert not summary["has_internal_forces"]
        assert not summary["has_reactions"]
        assert not summary["has_stresses"]
        assert "error_message" not in summary

    def test_get_result_summary_with_error(self) -> None:
        """Test result summary generation with analysis error."""
        results = {
            "analysis_status": {"executed": False, "error_message": "Analysis failed"},
            "displacements": {"status": "not_implemented"},
            "internal_forces": {"status": "not_implemented"},
            "reactions": {"status": "not_implemented"},
            "stresses": {"status": "not_implemented"},
        }

        summary = get_result_summary(results)

        assert not summary["analysis_successful"]
        assert summary["error_message"] == "Analysis failed"

    def test_validate_analysis_results_valid(self) -> None:
        """Test validation of valid analysis results."""
        results = {
            "analysis_status": {"executed": True, "error_message": None},
        }

        is_valid, messages = validate_analysis_results(results)

        assert is_valid
        assert len(messages) == 0

    def test_validate_analysis_results_not_executed(self) -> None:
        """Test validation when analysis was not executed."""
        results = {
            "analysis_status": {"executed": False, "error_message": None},
        }

        is_valid, messages = validate_analysis_results(results)

        assert not is_valid
        assert "Analysis was not executed successfully" in messages

    def test_validate_analysis_results_with_error(self) -> None:
        """Test validation when analysis has error."""
        results = {
            "analysis_status": {"executed": True, "error_message": "Analysis failed"},
        }

        is_valid, messages = validate_analysis_results(results)

        assert not is_valid
        assert "Analysis error: Analysis failed" in messages


if __name__ == "__main__":
    unittest.main()
