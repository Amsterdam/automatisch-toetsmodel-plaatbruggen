"""
Integration tests for load case selection in the bridge controller.

These tests verify that the load case selection table in the parametrization
actually controls which load cases are generated in the SCIA model through
the complete controller workflow.
"""

import unittest
from unittest.mock import Mock, patch

import pytest

from app.bridge.controller import BridgeController


class TestLoadCaseSelectionControllerIntegration(unittest.TestCase):
    """Integration tests for load case selection in the bridge controller."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.controller = BridgeController()

    def test_scia_model_generation_with_selective_load_cases(self) -> None:
        """Test that SCIA model generation respects load case selection."""
        # Create mock params with selective load case selection
        params = Mock()
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": False, "load_type": "Permanent", "load_case_count": 5},  # Disabled
            {"include": True, "load_type": "Temperatuur", "load_case_count": 4},
            {"include": False, "load_type": "UDL", "load_case_count": 3},  # Disabled
            {"include": True, "load_type": "Voetgangers", "load_case_count": 1},
            {"include": False, "load_type": "Dienstvoertuig", "load_case_count": 20},  # Disabled
            {"include": False, "load_type": "Onbedoeld voertuig", "load_case_count": 50},  # Disabled
            {"include": False, "load_type": "TS", "load_case_count": 30},  # Disabled
        ]

        # Mock the SCIA model creation function
        with patch("app.bridge.bridgeController.scia_integration.create_bridge_scia_model") as mock_create_model:
            # Mock the model creation to return a tuple (xml_file, def_file, analysis)
            mock_xml_file = Mock()
            mock_def_file = Mock()
            mock_analysis = Mock()
            mock_analysis.execute.return_value = None
            mock_analysis.get_updated_esa_model.return_value = b"mock_esa_content"
            mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

            # Execute the SCIA model creation through the controller
            self.controller._download_scia_esa_model_direct(params, "test_bridge")

            # Verify that create_bridge_scia_model was called with the params and template_path
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][0] == params  # First positional argument should be params
            assert len(call_args[0]) == 2  # Should have two positional arguments

    def test_scia_model_generation_with_all_load_cases_enabled(self) -> None:
        """Test that SCIA model generation works with all load cases enabled."""
        # Create mock params with all load types enabled
        params = Mock()
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": True, "load_type": "Permanent", "load_case_count": 5},
            {"include": True, "load_type": "Temperatuur", "load_case_count": 4},
            {"include": True, "load_type": "UDL", "load_case_count": 3},
            {"include": True, "load_type": "Voetgangers", "load_case_count": 1},
            {"include": True, "load_type": "Dienstvoertuig", "load_case_count": 20},
            {"include": True, "load_type": "Onbedoeld voertuig", "load_case_count": 50},
            {"include": True, "load_type": "TS", "load_case_count": 30},
        ]

        # Mock the SCIA model creation function
        with patch("app.bridge.bridgeController.scia_integration.create_bridge_scia_model") as mock_create_model:
            # Mock the model creation to return a tuple (xml_file, def_file, analysis)
            mock_xml_file = Mock()
            mock_def_file = Mock()
            mock_analysis = Mock()
            mock_analysis.execute.return_value = None
            mock_analysis.get_updated_esa_model.return_value = b"mock_esa_content"
            mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

            # Execute the SCIA model creation through the controller
            self.controller._download_scia_esa_model_direct(params, "test_bridge")

            # Verify that create_bridge_scia_model was called with the params and template_path
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][0] == params  # First positional argument should be params
            assert len(call_args[0]) == 2  # Should have two positional arguments

    def test_scia_model_generation_without_load_case_selection_table(self) -> None:
        """Test that SCIA model generation works without load case selection table (defaults to all enabled)."""
        # Create mock params without load_case_selection_table
        params = Mock()
        # Don't set load_case_selection_table attribute

        # Mock the SCIA model creation function
        with patch("app.bridge.bridgeController.scia_integration.create_bridge_scia_model") as mock_create_model:
            # Mock the model creation to return a tuple (xml_file, def_file, analysis)
            mock_xml_file = Mock()
            mock_def_file = Mock()
            mock_analysis = Mock()
            mock_analysis.execute.return_value = None
            mock_analysis.get_updated_esa_model.return_value = b"mock_esa_content"
            mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

            # Execute the SCIA model creation through the controller
            self.controller._download_scia_esa_model_direct(params, "test_bridge")

            # Verify that create_bridge_scia_model was called with the params and template_path
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][0] == params  # First positional argument should be params
            assert len(call_args[0]) == 2  # Should have two positional arguments

    def test_scia_model_generation_with_empty_load_case_selection_table(self) -> None:
        """Test that SCIA model generation works with empty load case selection table (defaults to all enabled)."""
        # Create mock params with empty load_case_selection_table
        params = Mock()
        params.load_case_selection_table = []

        # Mock the SCIA model creation function
        with patch("app.bridge.bridgeController.scia_integration.create_bridge_scia_model") as mock_create_model:
            # Mock the model creation to return a tuple (xml_file, def_file, analysis)
            mock_xml_file = Mock()
            mock_def_file = Mock()
            mock_analysis = Mock()
            mock_analysis.execute.return_value = None
            mock_analysis.get_updated_esa_model.return_value = b"mock_esa_content"
            mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

            # Execute the SCIA model creation through the controller
            self.controller._download_scia_esa_model_direct(params, "test_bridge")

            # Verify that create_bridge_scia_model was called with the params and template_path
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][0] == params  # First positional argument should be params
            assert len(call_args[0]) == 2  # Should have two positional arguments

    def test_scia_model_generation_with_mixed_load_case_selection(self) -> None:
        """Test that SCIA model generation works with mixed load case selection."""
        # Create mock params with mixed selection
        params = Mock()
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": True, "load_type": "Permanent", "load_case_count": 5},
            {"include": False, "load_type": "Temperatuur", "load_case_count": 4},  # Disabled
            {"include": True, "load_type": "UDL", "load_case_count": 3},
            {"include": False, "load_type": "Voetgangers", "load_case_count": 1},  # Disabled
            {"include": True, "load_type": "Dienstvoertuig", "load_case_count": 20},
            {"include": False, "load_type": "Onbedoeld voertuig", "load_case_count": 50},  # Disabled
            {"include": True, "load_type": "TS", "load_case_count": 30},
        ]

        # Mock the SCIA model creation function
        with patch("app.bridge.bridgeController.scia_integration.create_bridge_scia_model") as mock_create_model:
            # Mock the model creation to return a tuple (xml_file, def_file, analysis)
            mock_xml_file = Mock()
            mock_def_file = Mock()
            mock_analysis = Mock()
            mock_analysis.execute.return_value = None
            mock_analysis.get_updated_esa_model.return_value = b"mock_esa_content"
            mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

            # Execute the SCIA model creation through the controller
            self.controller._download_scia_esa_model_direct(params, "test_bridge")

            # Verify that create_bridge_scia_model was called with the params and template_path
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][0] == params  # First positional argument should be params
            assert len(call_args[0]) == 2  # Should have two positional arguments

    def test_scia_model_generation_with_invalid_load_types(self) -> None:
        """Test that SCIA model generation handles invalid load types gracefully."""
        # Create mock params with some invalid load types
        params = Mock()
        params.load_case_selection_table = [
            {"include": True, "load_type": "Eigen gewicht", "load_case_count": 1},
            {"include": True, "load_type": "Invalid Load Type", "load_case_count": 5},  # Invalid
            {"include": True, "load_type": "Temperatuur", "load_case_count": 4},
            {"include": False, "load_type": "Another Invalid Type", "load_case_count": 3},  # Invalid
        ]

        # Mock the SCIA model creation function
        with patch("app.bridge.bridgeController.scia_integration.create_bridge_scia_model") as mock_create_model:
            # Mock the model creation to return a tuple (xml_file, def_file, analysis)
            mock_xml_file = Mock()
            mock_def_file = Mock()
            mock_analysis = Mock()
            mock_analysis.execute.return_value = None
            mock_analysis.get_updated_esa_model.return_value = b"mock_esa_content"
            mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

            # Execute the SCIA model creation through the controller
            self.controller._download_scia_esa_model_direct(params, "test_bridge")

            # Verify that create_bridge_scia_model was called with the params and template_path
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][0] == params  # First positional argument should be params
            assert len(call_args[0]) == 2  # Should have two positional arguments

    def test_scia_model_generation_with_missing_include_field(self) -> None:
        """Test that SCIA model generation handles missing include field gracefully."""
        # Create mock params with missing include field
        params = Mock()
        params.load_case_selection_table = [
            {"load_type": "Eigen gewicht", "load_case_count": 1},  # Missing include field
            {"include": True, "load_type": "Permanent", "load_case_count": 5},
            {"include": False, "load_type": "Temperatuur", "load_case_count": 4},
        ]

        # Mock the SCIA model creation function
        with patch("app.bridge.bridgeController.scia_integration.create_bridge_scia_model") as mock_create_model:
            # Mock the model creation to return a tuple (xml_file, def_file, analysis)
            mock_xml_file = Mock()
            mock_def_file = Mock()
            mock_analysis = Mock()
            mock_analysis.execute.return_value = None
            mock_analysis.get_updated_esa_model.return_value = b"mock_esa_content"
            mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

            # Execute the SCIA model creation through the controller
            self.controller._download_scia_esa_model_direct(params, "test_bridge")

            # Verify that create_bridge_scia_model was called with the params and template_path
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][0] == params  # First positional argument should be params
            assert len(call_args[0]) == 2  # Should have two positional arguments

    def test_scia_model_generation_with_missing_load_type_field(self) -> None:
        """Test that SCIA model generation handles missing load_type field gracefully."""
        # Create mock params with missing load_type field
        params = Mock()
        params.load_case_selection_table = [
            {"include": True, "load_case_count": 1},  # Missing load_type field
            {"include": True, "load_type": "Permanent", "load_case_count": 5},
            {"include": False, "load_type": "Temperatuur", "load_case_count": 4},
        ]

        # Mock the SCIA model creation function
        with patch("app.bridge.bridgeController.scia_integration.create_bridge_scia_model") as mock_create_model:
            # Mock the model creation to return a tuple (xml_file, def_file, analysis)
            mock_xml_file = Mock()
            mock_def_file = Mock()
            mock_analysis = Mock()
            mock_analysis.execute.return_value = None
            mock_analysis.get_updated_esa_model.return_value = b"mock_esa_content"
            mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

            # Execute the SCIA model creation through the controller
            self.controller._download_scia_esa_model_direct(params, "test_bridge")

            # Verify that create_bridge_scia_model was called with the params and template_path
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][0] == params  # First positional argument should be params
            assert len(call_args[0]) == 2  # Should have two positional arguments

    def test_scia_model_generation_with_non_boolean_include_field(self) -> None:
        """Test that SCIA model generation handles non-boolean include field gracefully."""
        # Create mock params with non-boolean include field
        params = Mock()
        params.load_case_selection_table = [
            {"include": "yes", "load_type": "Eigen gewicht", "load_case_count": 1},  # Non-boolean include
            {"include": True, "load_type": "Permanent", "load_case_count": 5},
            {"include": False, "load_type": "Temperatuur", "load_case_count": 4},
        ]

        # Mock the SCIA model creation function
        with patch("app.bridge.bridgeController.scia_integration.create_bridge_scia_model") as mock_create_model:
            # Mock the model creation to return a tuple (xml_file, def_file, analysis)
            mock_xml_file = Mock()
            mock_def_file = Mock()
            mock_analysis = Mock()
            mock_analysis.execute.return_value = None
            mock_analysis.get_updated_esa_model.return_value = b"mock_esa_content"
            mock_create_model.return_value = (mock_xml_file, mock_def_file, mock_analysis)

            # Execute the SCIA model creation through the controller
            self.controller._download_scia_esa_model_direct(params, "test_bridge")

            # Verify that create_bridge_scia_model was called with the params and template_path
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][0] == params  # First positional argument should be params
            assert len(call_args[0]) == 2  # Should have two positional arguments


if __name__ == "__main__":
    pytest.main([__file__])
