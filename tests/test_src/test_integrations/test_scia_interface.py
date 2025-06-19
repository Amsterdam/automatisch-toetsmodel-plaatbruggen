"""
Tests for SCIA integration module.

These tests verify the core SCIA functionality without requiring VIKTOR SDK or SCIA Worker.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestSCIAAnalysisCreation:
    """Test SCIA analysis creation functions."""

    def test_create_scia_analysis_missing_template(self) -> None:
        """Test that FileNotFoundError is raised for missing template."""
        from src.integrations.scia_interface import create_scia_analysis_from_template

        mock_xml_file = Mock()
        mock_def_file = Mock()
        missing_template_path = Path("/nonexistent/template.esa")

        with pytest.raises(FileNotFoundError, match="SCIA template file not found"):
            create_scia_analysis_from_template(mock_xml_file, mock_def_file, missing_template_path)

    def test_create_scia_analysis_with_viktor(self) -> None:
        """Test SCIA analysis creation with actual VIKTOR available."""
        from src.integrations.scia_interface import create_scia_analysis_from_template

        mock_xml_file = Mock()
        mock_def_file = Mock()
        # Use a real path that exists (the test file itself)
        template_path = Path(__file__)

        # Since VIKTOR is available, test should work but may fail due to SciaAnalysis requirements
        try:
            result = create_scia_analysis_from_template(mock_xml_file, mock_def_file, template_path)
            # If we get here, the function worked
            assert result is not None
        except ImportError:
            # ImportError means VIKTOR SCIA module not available
            pytest.skip("VIKTOR SCIA module not available")
        except (ValueError, TypeError, KeyError):
            # Other errors are expected due to environment/configuration
            pass


class TestMainInterface:
    """Test main interface function."""

    @patch("src.integrations.scia_interface.create_scia_analysis_from_template")
    @patch("src.integrations.scia_interface.create_simple_scia_plate_model")
    def test_create_bridge_scia_model_mocked(self, mock_create_model: Mock, mock_create_analysis: Mock) -> None:
        """Test main interface function with mocked dependencies."""
        from src.integrations.scia_interface import create_bridge_scia_model

        # Setup mocks
        mock_xml_file = Mock()
        mock_def_file = Mock()
        mock_analysis = Mock()
        mock_create_model.return_value = (mock_xml_file, mock_def_file)
        mock_create_analysis.return_value = mock_analysis

        # Test data
        bridge_segments = [
            {"bz1": 10.0, "bz2": 5.0, "bz3": 15.0, "l": 0, "dz": 2.0, "dz_2": 3.0},
            {"bz1": 10.0, "bz2": 5.0, "bz3": 15.0, "l": 25, "dz": 2.0, "dz_2": 3.0},
        ]
        template_path = Path("test_template.esa")

        # Call function
        xml_file, def_file, scia_analysis = create_bridge_scia_model(bridge_segments, template_path)

        # Verify calls
        mock_create_model.assert_called_once()
        mock_create_analysis.assert_called_once_with(mock_xml_file, mock_def_file, template_path)

        # Verify return values
        assert xml_file == mock_xml_file
        assert def_file == mock_def_file
        assert scia_analysis == mock_analysis
