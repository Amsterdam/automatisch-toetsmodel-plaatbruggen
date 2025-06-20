"""
Tests for SCIA integration module.

These tests verify the core SCIA functionality without requiring VIKTOR SDK or SCIA Worker.
"""

from pathlib import Path
from unittest.mock import Mock

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
