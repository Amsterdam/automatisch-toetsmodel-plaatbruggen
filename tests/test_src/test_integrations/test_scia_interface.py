"""
Tests for SCIA interface module.

Tests for the main interface function that orchestrates SCIA model creation.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.integrations.scia_interface import create_bridge_scia_model


class TestSCIAInterface:
    """Test main SCIA interface function."""

    @patch("src.integrations.scia_interface.setup_bridge_analysis")
    def test_create_bridge_scia_model_success(self, mock_setup_analysis: Mock) -> None:
        """Test successful bridge SCIA model creation."""
        mock_params = Mock()
        mock_xml_file = Mock()
        mock_def_file = Mock()
        mock_scia_analysis = Mock()
        mock_setup_analysis.return_value = (mock_xml_file, mock_def_file, mock_scia_analysis)

        result = create_bridge_scia_model(mock_params, Path("test_template.esa"))

        # Verify delegation to analysis setup
        mock_setup_analysis.assert_called_once_with(mock_params, Path("test_template.esa"))

        # Verify return value
        assert result == (mock_xml_file, mock_def_file, mock_scia_analysis)

    @patch("src.integrations.scia_interface.setup_bridge_analysis")
    def test_create_bridge_scia_model_analysis_error(self, mock_setup_analysis: Mock) -> None:
        """Test error handling when analysis setup fails."""
        mock_params = Mock()
        mock_setup_analysis.side_effect = Exception("Analysis setup failed")

        with pytest.raises(Exception, match="Analysis setup failed"):
            create_bridge_scia_model(mock_params, Path("test_template.esa"))

        mock_setup_analysis.assert_called_once_with(mock_params, Path("test_template.esa"))

    @patch("src.integrations.scia_interface.setup_bridge_analysis")
    def test_create_bridge_scia_model_parameter_passing(self, mock_setup_analysis: Mock) -> None:
        """Test that parameters are correctly passed through."""
        mock_params = Mock()
        mock_params.special_attribute = "test_value"
        mock_xml_file = Mock()
        mock_def_file = Mock()
        mock_scia_analysis = Mock()
        mock_setup_analysis.return_value = (mock_xml_file, mock_def_file, mock_scia_analysis)

        create_bridge_scia_model(mock_params, Path("test_template.esa"))

        # Verify the exact same params object is passed
        mock_setup_analysis.assert_called_once_with(mock_params, Path("test_template.esa"))
        called_params = mock_setup_analysis.call_args[0][0]
        assert called_params.special_attribute == "test_value"

    @patch("src.integrations.scia_interface.setup_bridge_analysis")
    def test_create_bridge_scia_model_return_format(self, mock_setup_analysis: Mock) -> None:
        """Test that return format is maintained."""
        mock_params = Mock()
        mock_xml_file = Mock()
        mock_def_file = Mock()
        mock_scia_analysis = Mock()
        mock_setup_analysis.return_value = (mock_xml_file, mock_def_file, mock_scia_analysis)

        result = create_bridge_scia_model(mock_params, Path("test_template.esa"))

        # Verify return is tuple of XML, DEF, and analysis files
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert result[0] is mock_xml_file
        assert result[1] is mock_def_file


class TestSCIAInterfaceIntegration:
    """Test SCIA interface integration with other modules."""

    @patch("src.integrations.scia_interface.setup_bridge_analysis")
    def test_interface_delegates_to_analysis_module(self, mock_setup_analysis: Mock) -> None:
        """Test that interface properly delegates to analysis module."""
        mock_params = Mock()
        mock_xml_file = Mock()
        mock_def_file = Mock()
        mock_scia_analysis = Mock()
        mock_setup_analysis.return_value = (mock_xml_file, mock_def_file, mock_scia_analysis)

        # Call interface function
        result = create_bridge_scia_model(mock_params, Path("test_template.esa"))

        # Verify correct delegation
        mock_setup_analysis.assert_called_once_with(mock_params, Path("test_template.esa"))
        assert result == (mock_xml_file, mock_def_file, mock_scia_analysis)

    def test_interface_imports_correctly(self) -> None:
        """Test that interface imports all required modules correctly."""
        # Test that import doesn't fail
        from src.integrations.scia_interface import create_bridge_scia_model

        # Verify function is callable
        assert callable(create_bridge_scia_model)

    def test_interface_function_signature(self) -> None:
        """Test that interface function has correct signature."""
        import inspect

        from src.integrations.scia_interface import create_bridge_scia_model

        sig = inspect.signature(create_bridge_scia_model)
        params = list(sig.parameters.keys())

        # Should have exactly two parameters
        assert len(params) == 2
        assert params[0] == "params"
        assert params[1] == "template_path"


if __name__ == "__main__":
    pytest.main([__file__])
